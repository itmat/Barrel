import json
import os
import subprocess

users = json.loads(os.environ.get("USERS", "[]"))

for user in users:
    subprocess.run(
        f"""
            adduser --gecos '' --uid {user["id"]} --disabled-password {user["name"]}
            echo "{user["name"]} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/administrators

            runuser --login {user["name"]} --command 'mkdir -m 700 .ssh'
            runuser --login {user["name"]} --command 'echo "{user["key"]}" > .ssh/authorized_keys'
            runuser --login {user["name"]} --command 'chmod 600 .ssh/authorized_keys'
        """,
        shell=True,
        check=True,
    )
