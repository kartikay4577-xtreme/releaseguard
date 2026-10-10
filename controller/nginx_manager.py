import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NGINX_CONFIG = PROJECT_ROOT / "nginx" / "nginx.conf"
NGINX_CONTAINER = "releaseguard-nginx"


def run_docker_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=15,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip()
            or "Docker command failed"
        )

    return result


def switch_to(slot):
    if slot not in ("blue", "green"):
        raise ValueError("Slot must be blue or green")

    previous_config = NGINX_CONFIG.read_text(encoding="utf-8")

    new_config = f"""events {{}}

http {{
    upstream backend {{
        server {slot}:8000;
    }}

    server {{
        listen 80;

        location / {{
            proxy_pass http://backend;
        }}
    }}
}}
"""

    try:
        NGINX_CONFIG.write_text(new_config, encoding="utf-8")

        run_docker_command([
            "docker", "exec", NGINX_CONTAINER, "nginx", "-t"
        ])
        run_docker_command([
            "docker", "exec", NGINX_CONTAINER, "nginx", "-s", "reload"
        ])

    except Exception as error:
        try:
            NGINX_CONFIG.write_text(
                previous_config, encoding="utf-8"
            )
            run_docker_command([
                "docker", "exec", NGINX_CONTAINER, "nginx", "-t"
            ])
            run_docker_command([
                "docker", "exec", NGINX_CONTAINER, "nginx", "-s", "reload"
            ])
        except Exception:
            pass

        raise RuntimeError(
            f"Could not switch traffic to {slot}: {error}"
        ) from error
