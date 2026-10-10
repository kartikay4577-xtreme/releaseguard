import docker
from docker.errors import NotFound

NETWORK_NAME = "releaseguard_default"

SLOTS = {
    "blue": {"container": "releaseguard-blue", "host_port": 8000},
    "green": {"container": "releaseguard-green", "host_port": 8001},
}


def get_docker_client():
    return docker.from_env()


def get_container(name):
    client = get_docker_client()
    try:
        return client.containers.get(name)
    except NotFound:
        return None


def is_running(name):
    container = get_container(name)
    if container is None:
        return False

    container.reload()
    return container.status == "running"


def create_or_replace_slot(slot, image, version):
    if slot not in SLOTS:
        raise ValueError(f"Invalid slot: {slot}")

    client = get_docker_client()
    config = SLOTS[slot]

    # Check prerequisites before removing the old inactive container.
    client.images.get(image)
    network = client.networks.get(NETWORK_NAME)

    old_container = get_container(config["container"])
    if old_container is not None:
        old_container.remove(force=True)

    new_container = None
    try:
        new_container = client.containers.create(
            image=image,
            name=config["container"],
            environment={"APP_VERSION": version},
            ports={"8000/tcp": config["host_port"]},
            labels={
                "com.releaseguard.managed": "true",
                "com.releaseguard.slot": slot,
                "com.releaseguard.version": version,
            },
        )

        network.connect(new_container, aliases=[slot])
        new_container.start()
        return new_container

    except Exception:
        if new_container is not None:
            try:
                new_container.remove(force=True)
            except docker.errors.NotFound:
                pass
        raise
