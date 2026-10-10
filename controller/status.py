"""Read-only deployment status and history commands."""

import subprocess
from pathlib import Path

from controller.state_manager import get_state

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = PROJECT_ROOT / "state" / "history" / "deployments.log"

CONTAINERS = (
    "releaseguard-blue",
    "releaseguard-green",
    "releaseguard-nginx",
)


def show_status():
    """Display saved deployment state and current container status."""
    print("========== RELEASEGUARD STATUS ==========")

    try:
        state = get_state()
        print(f"Active slot : {state['active']}")
        print(f"Version     : {state['version']}")
    except Exception as error:
        print(f"Deployment state unavailable: {error}")
        return 1

    print("\n========== CONTAINER STATUS ==========")

    try:
        result = subprocess.run(
            [
                "docker", "ps", "-a",
                "--filter", "name=releaseguard-",
                "--format", "{{.Names}} | {{.Status}} | {{.Image}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            print(result.stdout.strip() or "No ReleaseGuard containers found.")
        else:
            print(f"Docker query failed: {result.stderr.strip()}")
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"Could not query Docker: {error}")

    return 0


def show_history(limit=10):
    """Display the most recent deployment history entries."""
    print("========== RELEASEGUARD DEPLOYMENT HISTORY ==========")

    if limit < 1:
        print("History limit must be at least 1.")
        return 1

    try:
        if not HISTORY_FILE.exists():
            print("No deployment history file found yet.")
            return 0

        with HISTORY_FILE.open("r", encoding="utf-8") as history:
            entries = history.readlines()

        if not entries:
            print("Deployment history is empty.")
            return 0

        for entry in entries[-limit:]:
            print(entry.rstrip())

        return 0
    except OSError as error:
        print(f"Could not read deployment history: {error}")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ReleaseGuard read-only inspection")
    parser.add_argument(
        "command",
        choices=("status", "history"),
        help="Show current status or deployment history",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum history entries to display (default: 10)",
    )
    args = parser.parse_args()

    if args.command == "status":
        raise SystemExit(show_status())

    raise SystemExit(show_history(args.limit))
