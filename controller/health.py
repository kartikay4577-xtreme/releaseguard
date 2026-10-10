import requests


def check_health(url, expected_version=None, timeout=5):
    try:
        response = requests.get(url, timeout=timeout)

        if response.status_code != 200:
            return False

        data = response.json()

        if data.get("status") != "healthy":
            return False

        if (
            expected_version is not None
            and data.get("version") != expected_version
        ):
            return False

        return True

    except (requests.RequestException, ValueError):
        return False
