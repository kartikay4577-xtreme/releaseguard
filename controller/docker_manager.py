import docker
from docker.errors import NotFound


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

    return container.status == "running"

