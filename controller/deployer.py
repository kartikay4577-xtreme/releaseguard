import logging
from datetime import datetime

from docker_manager import get_container, is_running
from health import check_health
from nginx_manager import switch_to
from state_manager import get_state, save_state


SLOTS = {
    "blue": {
        "container": "releaseguard-blue",
        "health_url": "http://127.0.0.1:8000/health"
    },
    "green": {
        "container": "releaseguard-green",
        "health_url": "http://127.0.0.1:8001/health"
    }
}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("releaseguard")


def get_inactive_slot():
    state = get_state()

    if state["active"] == "blue":
        return "green"

    return "blue"


def validate_slot(slot):
    container = get_container(SLOTS[slot]["container"])

    if container is None:
        logger.error(f"Container not found: {SLOTS[slot]['container']}")
        return False

    if not is_running(container.name):
        logger.error(f"Container is not running: {container.name}")
        return False

    return check_health(SLOTS[slot]["health_url"])

def record_deployment(active, target, success):
    with open("../state/history/deployments.log", "a") as file:
        file.write(
            f"{datetime.now().isoformat()} "
            f"from={active} "
            f"to={target} "
            f"success={success}\n"
        )


def deploy():
    state = get_state()

    active = state["active"]
    target = get_inactive_slot()

    logger.info(f"Active slot: {active}")
    logger.info(f"Target slot: {target}")

    logger.info("Checking target health...")

    if not validate_slot(target):
        record_deployment(active, target, False)
        logger.error("Deployment failed: target is unhealthy")
        return False

    logger.info("Target is healthy")
    logger.info(f"Switching traffic to {target}...")

    try:
        switch_to(target)

        logger.info("Verifying traffic after switch...")

        if not check_health("http://127.0.0.1:8080/health"):
            raise RuntimeError("Traffic verification failed")

        record_deployment(active, target, True)

        version = "v2" if target == "green" else "v1"
        save_state(target, version)

        logger.info(f"Deployment successful: {target}")

        return True

    except Exception as error:
        logger.error(f"Deployment failed after traffic switch: {error}")

        logger.info(f"Rolling back traffic to {active}...")

        switch_to(active)

        record_deployment(active, target, False)

        return False
