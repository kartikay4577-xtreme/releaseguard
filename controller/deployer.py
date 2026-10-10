import argparse
import logging
import re
import time
from datetime import datetime
from pathlib import Path

from .docker_manager import (
    create_or_replace_slot,
    get_container,
    is_running,
)
from .health import check_health
from .nginx_manager import switch_to
from .state_manager import get_state, save_state
from .deployment_lock import deployment_lock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = PROJECT_ROOT / "state" / "history" / "deployments.log"
TRAFFIC_HEALTH_URL = "http://127.0.0.1:8080/health"

SLOTS = {
    "blue": {
        "container": "releaseguard-blue",
        "health_url": "http://127.0.0.1:8000/health",
    },
    "green": {
        "container": "releaseguard-green",
        "health_url": "http://127.0.0.1:8001/health",
    },
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("releaseguard")


def get_inactive_slot(active):
    if active not in SLOTS:
        raise ValueError(f"Invalid active slot: {active}")
    return "green" if active == "blue" else "blue"


def record_deployment(active, target, version, success, detail=""):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = (
        f"{datetime.now().astimezone().isoformat()} "
        f"from={active} to={target} version={version} "
        f"success={success} detail={detail!r}\n"
    )
    with HISTORY_FILE.open("a", encoding="utf-8") as file:
        file.write(entry)


def validate_slot(slot, expected_version, wait_seconds=30):
    url = SLOTS[slot]["health_url"]
    deadline = time.monotonic() + wait_seconds

    while time.monotonic() < deadline:
        container = get_container(SLOTS[slot]["container"])

        if container is not None and is_running(container.name):
            if check_health(url, expected_version=expected_version):
                return True

        time.sleep(1)

    logger.error(
        "Slot %s did not become healthy with version %s",
        slot,
        expected_version,
    )
    return False


def deploy(image_tag):
    match = re.fullmatch(r"(.+):([A-Za-z0-9_.-]+)", image_tag)
    if not match or any(character.isspace() for character in image_tag):
        raise ValueError("Use a tagged image, e.g. releaseguard-app:v2")

    version = match.group(2)

    # Serialize deployments. State must be read AFTER acquiring the lock.
    with deployment_lock():
        return _deploy_locked(image_tag, version)


def preflight_deployment(image_tag, version):
    """Check deployment prerequisites without changing containers or traffic."""
    import subprocess

    try:
        state = get_state()
    except Exception as error:
        raise RuntimeError(f"Cannot read valid deployment state: {error}") from error

    if state.get("active") not in SLOTS or not state.get("version"):
        raise RuntimeError("Deployment state has an invalid active slot or version")

    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Could not check Docker image: {error}") from error

    if result.returncode != 0:
        raise ValueError(
            f"Docker image '{image_tag}' is not available locally. "
            "Build or pull it before deploying."
        )

    return state


def _deploy_locked(image_tag, version):
    state = preflight_deployment(image_tag, version)
    active = state["active"]
    target = get_inactive_slot(active)
    switch_attempted = False

    logger.info(
        "Active slot: %s (recorded version %s)",
        active,
        state["version"],
    )
    logger.info("Target slot: %s", target)
    logger.info("Requested image: %s", image_tag)

    try:
        create_or_replace_slot(target, image_tag, version)

        logger.info("Waiting for target health and version verification...")
        if not validate_slot(target, version):
            raise RuntimeError("Target failed health/version validation")

        # Set this before switching because Nginx may change partially.
        switch_attempted = True
        logger.info("Target validated; switching Nginx traffic")
        switch_to(target)

        if not check_health(
            TRAFFIC_HEALTH_URL,
            expected_version=version,
        ):
            raise RuntimeError("Traffic verification failed")

        save_state(target, version)

        try:
            record_deployment(
                active, target, version, True, "deployment successful"
            )
        except OSError as error:
            logger.warning("Could not record success history: %s", error)

        logger.info("Deployment successful: %s (%s)", target, version)
        return True

    except Exception as error:
        logger.error("Deployment failed: %s", error)

        if switch_attempted:
            try:
                logger.info("Restoring traffic to %s", active)
                switch_to(active)

                if not check_health(
                    TRAFFIC_HEALTH_URL,
                    expected_version=state["version"],
                ):
                    raise RuntimeError(
                        "Traffic did not return to the previous version "
                        f"{state['version']}"
                    )

                logger.info(
                    "Previous traffic restored and verified: %s (%s)",
                    active,
                    state["version"],
                )

            except Exception as rollback_error:
                logger.critical(
                    "Traffic restoration could not be verified: %s",
                    rollback_error,
                )

        try:
            record_deployment(active, target, version, False, str(error))
        except OSError as history_error:
            logger.error(
                "Could not record failure history: %s", history_error
            )

        return False

def main():
    parser = argparse.ArgumentParser(
        description="Deploy a versioned ReleaseGuard Docker image"
    )
    parser.add_argument(
        "image",
        help="Tagged Docker image, e.g. releaseguard-app:v2",
    )
    args = parser.parse_args()

    try:
        success = deploy(args.image)
    except Exception as error:
        logger.error("Could not start deployment: %s", error)
        raise SystemExit(1)

    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
