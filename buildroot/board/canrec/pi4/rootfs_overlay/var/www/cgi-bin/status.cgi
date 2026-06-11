#!/bin/sh
printf 'Content-Type: text/plain\r\nConnection: close\r\n\r\n'
printf 'hostname : %s\n' "$(hostname)"
printf 'uptime   : %s\n' "$(cut -d. -f1 /proc/uptime) seconds"
printf 'eth0 ip  : %s\n' "$(ip addr show eth0 2>/dev/null | awk '/inet /{print $2; exit}')"
printf 'memory   : %s\n' "$(awk '/MemTotal/{t=$2}/MemAvailable/{a=$2}END{printf "%dMB used / %dMB total",(t-a)/1024,t/1024}' /proc/meminfo)"
printf 'load     : %s\n' "$(cut -d' ' -f1-3 /proc/loadavg)"
printf 'time     : %s\n' "$(date)"
