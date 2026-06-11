#!/bin/sh
printf 'Content-Type: application/json\r\nConnection: close\r\n\r\n'

# Phase 1+ will list actual H.264 segments from /data/clips/
# Each entry: {"name":"...","date":"...","duration":"...","size":"...","locked":false}
printf '{"clips":[]}\n'
