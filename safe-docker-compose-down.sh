cat > safe-compose-down.sh <<'EOF'
#!/usr/bin/env bash

set -uo pipefail

TIMEOUT=10

echo "======================================"
echo "       Safe Docker Compose Down"
echo "======================================"

# Save container IDs before attempting shutdown.
mapfile -t CONTAINERS < <(docker compose ps -q -a)

if [[ ${#CONTAINERS[@]} -eq 0 ]]; then
    echo "[INFO] No containers found for this project."
    exit 0
fi

echo "[INFO] Found ${#CONTAINERS[@]} containers."

# First attempt: normal Docker shutdown.
echo
echo "[1/3] Trying normal docker compose down..."

if docker compose down; then
    echo "[SUCCESS] Containers stopped successfully."
    exit 0
fi

echo "[WARN] Normal shutdown failed."
echo "[INFO] Applying AppArmor workaround..."

# Second attempt: signal container init processes directly.
for ID in "${CONTAINERS[@]}"; do

    PID=$(docker inspect -f '{{.State.Pid}}' "$ID" 2>/dev/null || echo 0)
    NAME=$(docker inspect -f '{{.Name}}' "$ID" 2>/dev/null || echo "$ID")

    if ! [[ "$PID" =~ ^[0-9]+$ ]] || (( PID <= 1 )); then
        continue
    fi

    echo "[STOP] $NAME (PID: $PID)"

    if ! sudo kill -TERM "$PID" 2>/dev/null; then
        echo "[WARN] Could not send TERM to $PID"
        continue
    fi

    # Wait for graceful shutdown.
    for ((i=0; i<TIMEOUT; i++)); do
        if ! sudo kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 1
    done

    # Force stop only if the process is still alive.
    if sudo kill -0 "$PID" 2>/dev/null; then
        echo "[FORCE] Sending SIGKILL to $PID"
        sudo kill -KILL "$PID" 2>/dev/null || true
    fi

done

# Final attempt: let Docker clean up containers and networks.
echo
echo "[3/3] Retrying docker compose down..."

if docker compose down; then
    echo
    echo "[SUCCESS] Project containers stopped."
    echo "[INFO] Docker volumes and images were preserved."
    exit 0
else
    echo
    echo "[ERROR] Shutdown still failed."
    echo "[INFO] Check: docker ps -a"
    exit 1
fi
EOF

