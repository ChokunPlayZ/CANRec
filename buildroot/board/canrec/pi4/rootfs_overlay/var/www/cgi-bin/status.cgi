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

# ── Dummy telemetry (remove once real sources land in Phase 1+) ───────────────
t=$((uptime % 60))

# Speed: triangle wave 60–100 km/h
if [ "$t" -lt 30 ]; then
    speed=$((60 + t * 4 / 3))
else
    speed=$((100 - (t - 30) * 4 / 3))
fi

# Throttle: triangle wave 20–60%, offset 15 s
tp=$(( (uptime + 15) % 60 ))
if [ "$tp" -lt 30 ]; then
    throttle=$((20 + tp * 4 / 3))
else
    throttle=$((60 - (tp - 30) * 4 / 3))
fi

# Brake: spike 0–56% for 8 s each minute
if [ "$t" -gt 43 ] && [ "$t" -lt 51 ]; then
    brake=$(( (t - 43) * 8 ))
else
    brake=0
fi

# Engine temp: slow triangle wave 88–102 °C
te=$(( (uptime + 20) % 120 ))
if [ "$te" -lt 60 ]; then engine_temp=$((88 + te / 4))
else                      engine_temp=$((103 - (te - 60) / 4))
fi

# RPM proportional to speed + throttle
rpm=$((800 + speed * 42 + throttle * 12))
[ "$rpm" -gt 7500 ] && rpm=7500

# Gear from speed
if   [ "$speed" -lt 20  ]; then gear=1
elif [ "$speed" -lt 45  ]; then gear=2
elif [ "$speed" -lt 70  ]; then gear=3
elif [ "$speed" -lt 95  ]; then gear=4
elif [ "$speed" -lt 125 ]; then gear=5
else gear=6
fi

# G-force: integer×10 so we can format as X.Y without awk
lon_x10=$(( throttle * 4 / 10 - brake * 8 / 10 ))
lat_x10=$(( (t % 20 - 10) * speed / 300 ))

fmt() {
    [ "$1" -lt 0 ] && { abs=$((-$1)); printf -- '-%d.%d' $((abs/10)) $((abs%10)); }  \
                   || printf '%d.%d' $(($1/10)) $(($1%10))
}
glon=$(fmt "$lon_x10")
glat=$(fmt "$lat_x10")

seg="clip_$(printf '%04d' $((uptime / 300 + 1))).h264"

printf '{"hostname":"%s","uptime":%d,"memory":{"used_mb":%d,"total_mb":%d},"load":[%s,%s,%s],"storage":{"used_mb":%d,"total_mb":%d},"recording":{"active":true,"duration":%d,"segment":"%s"},"camera":{"connected":true},"gps":{"fix":true,"speed_kmh":%d,"throttle":%d,"brake":%d},"engine":{"temp_c":%d,"rpm":%d,"gear":%d},"gforce":{"lon":%s,"lat":%s}}\n' \
  "$(hostname)" "$uptime" "$mem_used" "$mem_total" \
  "$load1" "$load5" "$load15" \
  "$stor_used" "$stor_total" \
  "$uptime" "$seg" \
  "$speed" "$throttle" "$brake" \
  "$engine_temp" "$rpm" "$gear" \
  "$glon" "$glat"
