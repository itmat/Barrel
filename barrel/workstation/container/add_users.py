import json
import os
import subprocess

users = json.loads(os.environ.get("USERS", "[]"))

for user in users:
    subprocess.run(
        f"""
            adduser --gecos '' --uid {user["id"]} --disabled-password {user["name"]}
            echo "{user["name"]} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/administrators
        """,
        shell=True,
        check=True,
    )
