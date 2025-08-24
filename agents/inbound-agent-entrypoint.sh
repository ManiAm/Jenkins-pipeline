#!/usr/bin/env sh

set -eu

for i in $(seq 1 30); do
  [ -s "$JENKINS_SECRET_FILE" ] && break
  echo "Waiting for $JENKINS_SECRET_FILE... ($i/30)"
  sleep 3
done
[ -s "$JENKINS_SECRET_FILE" ] || { echo "Timeout waiting for $JENKINS_SECRET_FILE"; exit 1; }

export JENKINS_SECRET="$(cat "$JENKINS_SECRET_FILE")"
exec /usr/local/bin/jenkins-agent
