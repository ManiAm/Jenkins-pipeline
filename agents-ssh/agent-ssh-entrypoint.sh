#!/usr/bin/env bash

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends openssh-server openjdk-21-jdk ca-certificates

mkdir -p /run/sshd

# Harden sshd a bit
sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

id -u jenkins >/dev/null 2>&1 || useradd -m -s /bin/bash jenkins

# Wait for controller to create /keys/id_rsa.pub
for i in $(seq 1 30); do
  [ -f "${AUTH_KEY_FILE}" ] && break || sleep 3
done

mkdir -p /home/jenkins/.ssh
cat "${AUTH_KEY_FILE}" >> /home/jenkins/.ssh/authorized_keys

chown -R jenkins:jenkins /home/jenkins/.ssh
chmod 700 /home/jenkins/.ssh

mkdir -p "${AGENT_WORKDIR}"
chown -R jenkins:jenkins "${AGENT_WORKDIR}"

exec /usr/sbin/sshd -D -e
