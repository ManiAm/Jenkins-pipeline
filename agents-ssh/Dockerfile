
FROM ubuntu:22.04

USER root

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y \
      git \
 && rm -rf /var/lib/apt/lists/*

COPY agent-ssh-entrypoint.sh /usr/local/bin/agent-ssh-entrypoint.sh
RUN chmod +x /usr/local/bin/agent-ssh-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/agent-ssh-entrypoint.sh"]
