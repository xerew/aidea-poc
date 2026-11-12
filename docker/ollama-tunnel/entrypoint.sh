#!/bin/sh
# SSH tunnel to Ollama on the NTUA machine. The machine changes address when it
# moves, so try each address in turn and stay on the first that connects; when
# that connection drops (ServerAlive notices within ~90 s), move on to the next.
# The address in use goes to STATUS_FILE, which Django admin shows.
HOSTS="${SSH_REMOTE_HOSTS:-147.102.17.66 147.102.23.222}"
STATUS_FILE="${STATUS_FILE:-/status/ollama-tunnel.json}"
RETRY_PAUSE="${RETRY_PAUSE:-5}"

write_status() {
  mkdir -p "$(dirname "$STATUS_FILE")" 2>/dev/null
  printf '{"host": "%s", "since": "%s"}\n' "$1" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATUS_FILE.tmp" \
    && mv "$STATUS_FILE.tmp" "$STATUS_FILE"
}

while true; do
  for host in $HOSTS; do
    write_status "$host"
    ssh -N \
      -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
      -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=accept-new \
      -o UserKnownHostsFile=/dev/null -o BatchMode=yes \
      -i /keys/id_ed25519 \
      -L 0.0.0.0:11434:127.0.0.1:11434 \
      "${SSH_REMOTE_USER}@${host}"
    echo "ollama-tunnel: connection to ${host} ended (exit $?); trying the next address" >&2
    sleep "$RETRY_PAUSE"
  done
done
