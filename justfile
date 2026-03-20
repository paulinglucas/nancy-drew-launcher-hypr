# Nancy Drew Launcher — task runner

# Kill ALL Nancy Drew processes (launcher, games, audio)
nuke:
    #!/usr/bin/env bash
    echo "Nuking Nancy Drew processes..."
    pkill -f "launcher.py" 2>/dev/null || true
    WINEPREFIX="$HOME/Games/NancyDrew/wineprefix" wineserver -k9 2>/dev/null || true
    killall -9 gamescope gamescopereaper Game.exe winedevice.exe 2>/dev/null || true
    pkill -9 -f "Game.exe" 2>/dev/null || true
    pkill -f "throttle-game" 2>/dev/null || true
    pkill -f "gamescope-focus-fix" 2>/dev/null || true
    # Kill only wine-labeled audio streams
    for sink in $(pactl list sink-inputs 2>/dev/null | grep -B20 "wine-preloader\|Nancy Drew" | grep "Sink Input" | grep -o '#[0-9]*' | tr -d '#'); do
        pactl kill-sink-input "$sink" 2>/dev/null
    done
    sleep 1
    echo "Done."

# Launch the app (full nuke first to prevent zombie accumulation)
run: nuke
    python3 launcher.py

# Kill and relaunch
restart: nuke
    sleep 1
    python3 launcher.py

# Show status of running game processes
status:
    #!/usr/bin/env bash
    echo "=== Launcher ==="
    pgrep -af "launcher.py" 2>/dev/null || echo "  (none)"
    echo "=== Wine ==="
    pgrep -a wine 2>/dev/null || echo "  (none)"
    echo "=== Audio ==="
    pactl list sink-inputs 2>/dev/null | grep "application.name" || echo "  (none)"
    echo "=== Thermals ==="
    cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf "  %.0f°C\n", $1/1000}'
    echo "=== CPU Top 5 ==="
    ps -eo %cpu,comm --sort=-%cpu | head -6

# Extract music from game directories (requires games at ~/Games/NancyDrew/)
extract-music:
    python3 extract_music.py
