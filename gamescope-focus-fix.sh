#!/usr/bin/env bash
# Watches for gamescope window gaining focus and toggles fullscreen
# to reset the cursor grab after workspace switching.

socat -u UNIX-CONNECT:"$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock" - 2>/dev/null | while read -r line; do
    if [[ "$line" == "activewindow>>"* ]]; then
        class="${line#activewindow>>}"
        class="${class%%,*}"
        if [[ "$class" == "gamescope" ]]; then
            sleep 0.15
            hyprctl dispatch fullscreen 0 >/dev/null 2>&1
            sleep 0.05
            hyprctl dispatch fullscreen 2 >/dev/null 2>&1
        fi
    fi
done
