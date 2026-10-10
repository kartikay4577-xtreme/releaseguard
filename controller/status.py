from .docker_manager import get_container, is_running
from .state_manager import get_state


def main():
    state = get_state()

    print("ReleaseGuard Status")
    print("-------------------")
    print("Active slot:", state["active"])
    print("Recorded version:", state["version"])

    for slot in ("blue", "green"):
        name = f"releaseguard-{slot}"
        container = get_container(name)

        if container is None:
            status = "not found"
        else:
            container.reload()
            status = container.status

        running = is_running(name) if container is not None else False
        print(f"{slot.capitalize()} container: {status}")
        print(f"{slot.capitalize()} running: {running}")


if __name__ == "__main__":
    main()
