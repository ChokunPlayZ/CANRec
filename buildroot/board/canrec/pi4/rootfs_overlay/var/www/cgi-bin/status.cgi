#!/bin/sh
printf 'Content-Type: application/json\r\nConnection: close\r\n\r\n'

uptime=$(cut -d. -f1 /proc/uptime)
mem_total=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
mem_avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
mem_used=$((mem_total - mem_avail))
load1=$(cut -d' ' -f1 /proc/loadavg)
load5=$(cut -d' ' -f2 /proc/loadavg)
load15=$(cut -d' ' -f3 /proc/loadavg)

stor_used=0; stor_total=0
if mountpoint -q /data 2>/dev/null; then
  read -r _ stor_total stor_used _ <<EOF
$(df -m /data | awk 'NR==2{print $2,$3,$4}')
EOF
fi

# ── Dummy telemetry (remove once real sources are wired up) ──────────────────
# Values cycle on a ~60 s period so the UI looks alive during demos.
t=$((uptime % 60))
speed=$(awk "BEGIN{printf \"%d\", 60 + 40*sin($t * 3.14159/30)}")
throttle=$(awk "BEGIN{printf \"%d\", 30 + 25*sin($t * 3.14159/20 + 1)}")
brake=$(awk "BEGIN{printf \"%d\", t=$t; if(t>40&&t<50) print 35+int(t-40)*3; else print 0}")
rec_duration=$uptime
seg="clip_$(printf '%04d' $((uptime/300 + 1))).h264"

printf '{"hostname":"%s","uptime":%s,"memory":{"used_mb":%s,"total_mb":%s},"load":[%s,%s,%s],"storage":{"used_mb":%s,"total_mb":%s},"recording":{"active":true,"duration":%s,"segment":"%s"},"camera":{"connected":true},"gps":{"fix":true,"speed_kmh":%s,"throttle":%s,"brake":%s}}\n' \
  "$(hostname)" "$uptime" "$mem_used" "$mem_total" \
  "$load1" "$load5" "$load15" \
  "$stor_used" "$stor_total" \
  "$rec_duration" "$seg" \
  "$speed" "$throttle" "$brake"
