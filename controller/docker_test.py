import docker
import requests


def check_health(url):
    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()

            if data.get("status") == "healthy":
                return True

        return False

    except requests.RequestException:
        return False


client = docker.from_env()

container = client.containers.get("releaseguard-green")

print("Container:", container.name)
print("Status:", container.status)

healthy = check_health("http://127.0.0.1:8001/health")

print("Healthy:", healthy)

