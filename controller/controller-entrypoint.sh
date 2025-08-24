#!/usr/bin/env bash

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

# Generate SSH keypair once into the shared volume
mkdir -p /keys
[ -f /keys/id_rsa ] || ssh-keygen -t rsa -b 4096 -N '' -f /keys/id_rsa
chmod 600 /keys/id_rsa

# Make sure java is on PATH (belt & suspenders)
export PATH="$PATH:${JAVA_HOME:-/opt/java/openjdk}/bin"

if [ ! -f /keys/admin_password ]; then
  echo "[controller] Generating /keys/admin_password"
  head -c 32 /dev/urandom | base64 | tr -d '\n' > /keys/admin_password
  chmod 600 /keys/admin_password
  chown jenkins:jenkins /keys/admin_password || true
fi

# Hand off to official startup
exec /usr/local/bin/jenkins.sh
