
FROM jenkins/inbound-agent:latest-jdk21

USER root

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y \
      git \
 && rm -rf /var/lib/apt/lists/*

COPY inbound-agent-entrypoint.sh /usr/local/bin/inbound-agent-entrypoint.sh
RUN chmod +x /usr/local/bin/inbound-agent-entrypoint.sh

USER jenkins

ENTRYPOINT ["/usr/local/bin/inbound-agent-entrypoint.sh"]
