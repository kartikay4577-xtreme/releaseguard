from state_manager import get_state
from docker_manager import get_container


state = get_state()

print("ReleaseGuard Status")
print("-------------------")
print("Active slot:", state["active"])
print("Version:", state["version"])

for slot in ["blue", "green"]:
    container = get_container(f"releaseguard-{slot}")
    print(f"{slot.capitalize()} container:", container.status)
