#!/bin/sh
set -e

# Capture runtime UID/GID from environment variables, defaulting to 1000
PUID=${USER_UID:-1000}
PGID=${USER_GID:-1000}

# Adjust the node user's UID/GID if they differ from the runtime request
# and fix volume ownership only when a remap is needed
changed=0

if [ "$(id -u node)" -ne "$PUID" ]; then
    echo "Updating node UID to $PUID"
    usermod -o -u "$PUID" node
    changed=1
fi

if [ "$(id -g node)" -ne "$PGID" ]; then
    echo "Updating node GID to $PGID"
    groupmod -o -g "$PGID" node
    usermod -g "$PGID" node
    changed=1
fi

if [ "$changed" = "1" ]; then
    chown -R node:node /paperclip
fi

# Always fix .claude ownership — docker cp creates files as root,
# and the node process needs write access to session-env subdirs.
if [ -d /paperclip/.claude ]; then
    chown -R node:node /paperclip/.claude
fi

# Fix OpenCode data/state dir ownership — opencode.db (SQLite) and lock files must be
# writable by node. These dirs are created by root on first run; node needs write access.
if [ -d /paperclip/.local ]; then
    chown -R node:node /paperclip/.local
fi

# Seed OpenCode config from image default if not already present in volume.
# HOME=/paperclip, so OpenCode looks for config at /paperclip/.config/opencode/config.json.
if [ ! -f /paperclip/.config/opencode/config.json ]; then
    mkdir -p /paperclip/.config/opencode
    cp /etc/opencode/config.json /paperclip/.config/opencode/config.json
    chown -R node:node /paperclip/.config
fi

# Sync agent instructions from external AGENTS.md files into Paperclip's managed
# instruction paths so the UI shows the correct content rather than the generic
# placeholder created at agent setup time.
python3 /usr/local/bin/sync-agent-instructions.py || true

exec gosu node "$@"
