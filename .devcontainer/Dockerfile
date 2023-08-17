FROM mcr.microsoft.com/vscode/devcontainers/python:3.11-bookworm

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"           \
 && unzip awscliv2.zip                                                                          \
 && ./aws/install                                                                               \
 && rm -rf awscliv2.zip aws

RUN echo "alias ll='ls -l --color=auto'" >> /etc/bash.bashrc

COPY setup.sh /home/vscode/
