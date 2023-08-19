FROM python:3.11

RUN apt-get update                                                      \
 && apt-get install -y sudo

ARG USERS

COPY add_users.py add_users.py

RUN python3 add_users.py && rm add_users.py

RUN echo "alias ll='ls -l --color=auto'" >> /etc/bash.bashrc

CMD ["/bin/bash", "-c", "sleep infinity"]
