#!/bin/sh
set -e
exec autossh -M 0 -N \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile=/dev/null \
  -i /keys/id_ed25519 \
  -L 0.0.0.0:11434:127.0.0.1:11434 \
  "${SSH_REMOTE_USER}@${SSH_REMOTE_HOST}"
