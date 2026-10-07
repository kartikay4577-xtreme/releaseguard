import subprocess


NGINX_CONTAINER = "releaseguard-nginx"


def switch_to(slot):
    if slot == "blue":
        upstream = "blue"
    elif slot == "green":
        upstream = "green"
    else:
        raise ValueError("Slot must be blue or green")

    config = f"""events {{}}

http {{
    upstream backend {{
        server {upstream}:8000;
    }}

    server {{
        listen 80;

        location / {{
            proxy_pass http://backend;
        }}
    }}
}}
"""

    with open("../nginx/nginx.conf", "w") as file:
        file.write(config)

    subprocess.run(
        ["docker", "exec", NGINX_CONTAINER, "nginx", "-t"],
        check=True
    )

    subprocess.run(
        ["docker", "exec", NGINX_CONTAINER, "nginx", "-s", "reload"],
        check=True
    )

