
FROM jenkins/jenkins:lts-jdk21

USER root

# git, curl, etc. for pipelines
RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl openssh-client ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY controller-entrypoint.sh /usr/local/bin/controller-entrypoint.sh
RUN chmod +x /usr/local/bin/controller-entrypoint.sh

USER jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt

RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Seed JCasC and init scripts
COPY casc/ /usr/share/jenkins/ref/casc/
COPY init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/controller-entrypoint.sh"]
