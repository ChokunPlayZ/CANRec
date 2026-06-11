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

# ── Dummy telemetry (remove once real sources are wired in Phase 1+) ─────────
t=$((uptime % 60))

# Speed: triangle wave 60–100 km/h, period 60 s
if [ "$t" -lt 30 ]; then
    speed=$((60 + t * 4 / 3))
else
    speed=$((100 - (t - 30) * 4 / 3))
fi

# Throttle: triangle wave 20–60%, offset by 15 s
tp=$(( (uptime + 15) % 60 ))
if [ "$tp" -lt 30 ]; then
    throttle=$((20 + tp * 4 / 3))
else
    throttle=$((60 - (tp - 30) * 4 / 3))
fi

# Brake: spikes 0–56% for ~8 s each minute
if [ "$t" -gt 43 ] && [ "$t" -lt 51 ]; then
    brake=$(( (t - 43) * 8 ))
else
    brake=0
fi

seg="clip_$(printf '%04d' $((uptime / 300 + 1))).h264"

printf '{"hostname":"%s","uptime":%d,"memory":{"used_mb":%d,"total_mb":%d},"load":[%s,%s,%s],"storage":{"used_mb":%d,"total_mb":%d},"recording":{"active":true,"duration":%d,"segment":"%s"},"camera":{"connected":true},"gps":{"fix":true,"speed_kmh":%d,"throttle":%d,"brake":%d}}\n' \
  "$(hostname)" "$uptime" "$mem_used" "$mem_total" \
  "$load1" "$load5" "$load15" \
  "$stor_used" "$stor_total" \
  "$uptime" "$seg" \
  "$speed" "$throttle" "$brake"
