#!/bin/sh
printf 'Content-Type: application/json\r\nConnection: close\r\n\r\n'

uptime=$(cut -d. -f1 /proc/uptime)
mem_total=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
mem_avail=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
mem_used=$((mem_total - mem_avail))
load1=$(cut -d' ' -f1 /proc/loadavg)
load5=$(cut -d' ' -f2 /proc/loadavg)
load15=$(cut -d' ' -f3 /proc/loadavg)

# Storage: look for the data partition mount at /data (Phase 1+)
stor_used=0
stor_total=0
if mountpoint -q /data 2>/dev/null; then
  read -r _ stor_total stor_used _ <<EOF
$(df -m /data | awk 'NR==2{print $2,$3,$4}')
EOF
fi

printf '{"hostname":"%s","uptime":%s,"memory":{"used_mb":%s,"total_mb":%s},"load":[%s,%s,%s],"storage":{"used_mb":%s,"total_mb":%s},"recording":{"active":false,"duration":0,"segment":null},"camera":{"connected":false},"gps":{"fix":false}}\n' \
  "$(hostname)" "$uptime" "$mem_used" "$mem_total" \
  "$load1" "$load5" "$load15" \
  "$stor_used" "$stor_total"
