#!/usr/bin/env bash
# Collects everything needed to explain stutter, freezes and download problems
# into one text file:  ~/chapter-diagnose.txt
#
#   curl -fsSL https://raw.githubusercontent.com/Mgns55/chapter-ger/main/scripts/chapter-diagnose.sh | bash
#
# Read-only except for one thing: it makes the system journal persistent, so the
# logs of a freeze survive the reboot that follows it.
set -u
OUT="${HOME}/chapter-diagnose.txt"
CACHE_DIR="/home/chapter/.cache/chapter/audio"
SERVICES="audiobookshelf-player-oled audiobookshelf-player-setup-system audiobookshelf-player-mqtt audiobookshelf-player-update"

section() { printf '\n===== %s =====\n' "$1"; }
run() { printf '$ %s\n' "$*"; "$@" 2>&1; }

{
  section "Basics"
  run date
  run uptime
  run hostname
  sudo grep -h "__version__" /home/*/audiobookshelf-player/abs_kids_player/__init__.py 2>/dev/null
  run cat /proc/device-tree/model; echo

  section "Power and temperature"
  run vcgencmd get_throttled
  echo "(0x0 = all good; 0x50000/0x50005 = under-voltage happened -> power supply/cable too weak)"
  run vcgencmd measure_temp

  section "Memory and disk"
  run free -m
  run swapon --show
  run df -h /
  grep -E "Dirty|Writeback" /proc/meminfo
  run cat /proc/sys/vm/dirty_ratio /proc/sys/vm/dirty_background_ratio
  echo "Offline books: $(sudo find "$CACHE_DIR" -name manifest.json 2>/dev/null | wc -l)"
  run sudo du -sh "$CACHE_DIR"
  echo "Unfinished downloads (.part):"; sudo find "$CACHE_DIR" -name '*.part' -printf '%s bytes  %p\n' 2>/dev/null

  section "Wi-Fi"
  run iw dev wlan0 link
  run nmcli -f GENERAL.CONNECTION,IP4.ADDRESS,IP4.DNS device show wlan0

  section "Reachability (web page, Audiobookshelf, DNS)"
  run nmcli -t -f NAME,DEVICE connection show --active
  run ip -4 addr show wlan0
  run iw dev wlan0 get power_save
  for s in audiobookshelf-player-setup audiobookshelf-player-setup-system audiobookshelf-player-port80-forward; do
    printf '%s: %s\n' "$s" "$(systemctl is-active "$s" 2>/dev/null)"
  done
  echo "listening ports:"; ss -ltn 2>/dev/null | grep -E ':(80|47831) ' || echo "  nothing on 80/47831"
  printf 'setup page (localhost:47831/health): '; curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://localhost:47831/health || echo failed
  printf 'setup page via port 80: '; curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://localhost/ || echo failed
  printf 'router ping: '; ping -c 2 -W 2 "$(ip route | awk '/default/ {print $3; exit}')" >/dev/null 2>&1 && echo ok || echo FAILED
  ABS_HOST=$(sudo python3 -c 'import json,glob,urllib.parse as u
for p in glob.glob("/home/*/.config/*/config.json")+glob.glob("/home/*/.local/share/*/config.json"):
    try:
        d=json.load(open(p)); print(u.urlparse(d["server_url"]).hostname); break
    except Exception: pass' 2>/dev/null)
  echo "Audiobookshelf host: ${ABS_HOST:-unknown}"
  if [ -n "${ABS_HOST:-}" ]; then
    run getent hosts "$ABS_HOST"
    printf 'Audiobookshelf /ping: '; curl -s -m 10 "https://${ABS_HOST}/ping" || echo FAILED; echo
  fi

  section "Setup page log (this boot)"
  journalctl -u audiobookshelf-player-setup -u audiobookshelf-player-setup-system -u audiobookshelf-player-port80-forward -b --no-pager -o short-iso 2>/dev/null | tail -n 60

  section "Top processes"
  top -b -n 1 -o %CPU | head -n 20
  ps -eo pid,rss,pcpu,etime,comm --sort=-rss | head -n 12

  section "Service state"
  for s in $SERVICES; do
    printf '%s: %s, restarts=%s, since %s\n' "$s" \
      "$(systemctl is-active "$s" 2>/dev/null)" \
      "$(systemctl show -p NRestarts --value "$s" 2>/dev/null)" \
      "$(systemctl show -p ActiveEnterTimestamp --value "$s" 2>/dev/null)"
  done

  section "Boots (a freeze usually ends in a reboot)"
  run journalctl --list-boots --no-pager | tail -n 8

  section "Kernel warnings, this boot and the previous one"
  for b in -1 0; do
    echo "--- boot $b"
    journalctl -k -b "$b" --no-pager 2>/dev/null \
      | grep -iE "voltage|oom|out of memory|killed process|blocked for more than|mmc|i/o error|ext4|brcmf|watchdog|hung" \
      | tail -n 40
  done

  section "Desktop (not needed for the player, costs RAM and CPU)"
  echo "default target: $(systemctl get-default)"
  pgrep -l -x 'labwc|wayfire|lxsession|pcmanfm' || echo "no desktop running"

  LOG=/home/chapter/audiobookshelf-player-oled.log
  section "Player log, important lines"
  sudo grep -aE "Health|stalled|Audio cache|Playback|playback|Could not|failed|Failed|Error|error|Traceback|Exception|underrun|Offline|offline|Stack|Thread|File \"" "$LOG" 2>/dev/null | tail -n 300

  section "Player log, last 150 lines"
  sudo tail -n 150 "$LOG" 2>/dev/null

  section "Service events"
  journalctl -u audiobookshelf-player-oled --since "-24h" --no-pager -o short-iso 2>/dev/null | tail -n 40
} > "$OUT" 2>&1

# Keep logs across reboots from now on (needed to see what happened right before a freeze).
if [ ! -d /var/log/journal ]; then
  sudo mkdir -p /var/log/journal && sudo systemd-tmpfiles --create --prefix /var/log/journal >/dev/null 2>&1
  sudo systemctl restart systemd-journald && echo "Journal is now kept across reboots." >> "$OUT"
fi

echo "Done. Report written to: $OUT  ($(wc -l < "$OUT") lines)"
echo "Copy it to your Mac with:  scp $(whoami)@$(hostname).local:$OUT ~/Downloads/"
