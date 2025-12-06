#!/usr/bin/env bash
set -euo pipefail

: "${PUID:=1000}"
: "${PGID:=1000}"
: "${TZ:=UTC}"
: "${UMASK:=002}"
: "${STOCKWORKS_DATA_DIR:=/data}"

# Ensure permissions for any newly-created files mirror user expectations.
umask "${UMASK}"

# Configure timezone if the requested zone exists.
if [ -f "/usr/share/zoneinfo/${TZ}" ]; then
    ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime
    echo "${TZ}" > /etc/timezone
fi

# Ensure the data directory exists and is owned by the requested user/group.
mkdir -p "${STOCKWORKS_DATA_DIR}"
chown -R "${PUID}:${PGID}" "${STOCKWORKS_DATA_DIR}"

# Run the application as the requested non-root user.
exec gosu "${PUID}:${PGID}" "$@"
