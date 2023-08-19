FROM python:3.11

RUN apt-get update                                                                              \
 && apt-get install -y openssh-server sudo

ARG USERS

COPY add_users.py add_users.py
COPY run_server.sh run_server.sh

RUN python3 add_users.py && rm add_users.py

RUN echo "AllowTcpForwarding no"                >> /etc/ssh/sshd_config.d/configuration.conf    \
 && echo "ChallengeResponseAuthentication no"   >> /etc/ssh/sshd_config.d/configuration.conf    \
 && echo "PasswordAuthentication no"            >> /etc/ssh/sshd_config.d/configuration.conf    \
 && echo "PrintMotd no"                         >> /etc/ssh/sshd_config.d/configuration.conf    \
 && echo "X11Forwarding no"                     >> /etc/ssh/sshd_config.d/configuration.conf

RUN echo "alias ll='ls -l --color=auto'" >> /etc/bash.bashrc

CMD ["/bin/bash", "run_server.sh"]
