import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PROJECT_ROOT / "state" / "deployment.json"


def get_state():
    with STATE_FILE.open("r", encoding="utf-8") as file:
        state = json.load(file)

    if state.get("active") not in ("blue", "green"):
        raise ValueError("Deployment state has an invalid active slot")

    if not state.get("version"):
        raise ValueError("Deployment state is missing its version")

    return state


def save_state(active, version):
    if active not in ("blue", "green"):
        raise ValueError(f"Invalid active slot: {active}")

    if not version:
        raise ValueError("Version cannot be empty")

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = STATE_FILE.with_suffix(".tmp")

    try:
        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(
                {"active": active, "version": version},
                file,
                indent=2,
            )
            file.write("\n")

        temp_file.replace(STATE_FILE)
    finally:
        if temp_file.exists():
            temp_file.unlink()
