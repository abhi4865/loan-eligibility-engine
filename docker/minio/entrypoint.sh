#!/bin/sh
set -eu
mkdir -p /data /home/minio
chown -R minio:minio /data /home/minio
if [ "$#" -eq 0 ]; then
  set -- server /data --console-address :9001
fi
if [ "$1" = "server" ]; then
  exec su-exec minio minio "$@"
fi
exec su-exec minio "$@"
