#!/bin/bash
# Watches for Game.exe and throttles its CPU via SIGSTOP/SIGCONT.
# This prevents the 2005-era busy-loop from pegging 100% CPU.
# Target: ~40% CPU usage (sleep 15ms, run 10ms per cycle)

sleep 3  # wait for game to start

while true; do
    PID=$(pgrep -f "Game.exe" | head -1)
    if [ -z "$PID" ]; then
        sleep 1
        continue
    fi
    
    # Throttle loop: stop for 15ms, run for 10ms
    while kill -0 "$PID" 2>/dev/null; do
        kill -STOP "$PID" 2>/dev/null
        sleep 0.015
        kill -CONT "$PID" 2>/dev/null
        sleep 0.010
    done
    break
done
