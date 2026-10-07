import requests


def check_health(url, timeout=5):
    try:
        response = requests.get(url, timeout=timeout)

        if response.status_code != 200:
            return False

        data = response.json()

        return data.get("status") == "healthy"

    except requests.RequestException:
        return False
    
