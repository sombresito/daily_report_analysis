#!/usr/bin/env bash
set -e

if [ "$1" = "serve-uuid" ]; then
  exec python uuid_service.py
else
  exec python daily_report.py "$@"
fi
