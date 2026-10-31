#!/bin/sh
set -eu
# Explicit sandbox reset: destroys this Compose project's lab/demo evidence volumes.
docker compose down --volumes
docker compose up --build -d
