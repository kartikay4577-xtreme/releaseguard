from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = PROJECT_ROOT / "state" / "history" / "deployments.log"


def main():
    print("ReleaseGuard Deployment History")
    print("--------------------------------")

    if not HISTORY_FILE.exists():
        print("No deployment history found.")
        return

    history = HISTORY_FILE.read_text(encoding="utf-8")

    if not history.strip():
        print("Deployment history is empty.")
        return

    print(history, end="" if history.endswith("\n") else "\n")


if __name__ == "__main__":
    main()
