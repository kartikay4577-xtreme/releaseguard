import json


STATE_FILE = "../state/deployment.json"


def get_state():
    with open(STATE_FILE, "r") as file:
        return json.load(file)


def save_state(active, version):
    state = {
        "active": active,
        "version": version
    }

    with open(STATE_FILE, "w") as file:
        json.dump(state, file, indent=2)

