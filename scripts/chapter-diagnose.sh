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
  run df -h / "$CACHE_DIR"
  grep -E "Dirty|Writeback" /proc/meminfo
  run cat /proc/sys/vm/dirty_ratio /proc/sys/vm/dirty_background_ratio
  echo "Offline books: $(sudo find "$CACHE_DIR" -name manifest.json 2>/dev/null | wc -l)"
  run sudo du -sh "$CACHE_DIR"
  echo "Unfinished downloads (.part):"; sudo find "$CACHE_DIR" -name '*.part' -printf '%s bytes  %p\n' 2>/dev/null

  section "Wi-Fi"
  run iw dev wlan0 link
  run nmcli -f GENERAL.CONNECTION,IP4.ADDRESS,IP4.DNS device show wlan0

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

  section "Player log, important lines (last 12 h)"
  journalctl -u audiobookshelf-player-oled --since "-12h" --no-pager -o short-iso 2>/dev/null \
    | grep -E "Health|stalled|Audio cache|Playback|playback|Could not|failed|Failed|Error|error|Traceback|Exception|underrun|Offline|offline|Stack|Thread|File \"" \
    | tail -n 300

  section "Player log, previous boot (last 150 lines before the freeze)"
  journalctl -u audiobookshelf-player-oled -b -1 --no-pager -o short-iso 2>/dev/null | tail -n 150

  section "Player log, last 120 lines"
  journalctl -u audiobookshelf-player-oled --no-pager -o short-iso -n 120 2>/dev/null
} > "$OUT" 2>&1

# Keep logs across reboots from now on (needed to see what happened right before a freeze).
if [ ! -d /var/log/journal ]; then
  sudo mkdir -p /var/log/journal && sudo systemd-tmpfiles --create --prefix /var/log/journal >/dev/null 2>&1
  sudo systemctl restart systemd-journald && echo "Journal is now kept across reboots." >> "$OUT"
fi

echo "Done. Report written to: $OUT  ($(wc -l < "$OUT") lines)"
echo "Copy it to your Mac with:  scp $(whoami)@$(hostname).local:$OUT ~/Downloads/"
