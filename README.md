# Nancy Drew Launcher for Hyprland

*NOTE: This project was made for Arch Linux users who happen to also be Nancy Drew fans. This likely means this project is for me and for me only. But if anyone out there finds any enjoyment out of it, you have automatically become my best friend.*

A GTK4 game launcher for running Her Interactive's Nancy Drew PC games under Wine on Arch Linux with Hyprland. Noir-themed UI with background music extracted from the games, one-click launching via Gamescope, and automatic CPU throttling to keep your laptop cool.

## Requirements

- **Arch Linux** (or Arch-based distro) with **multilib** enabled
- **Hyprland** window manager
- **just** task runner (optional but recommended)
- **socat** (for the cursor focus-fix script)

Everything else (Wine, Gamescope, GTK4, GStreamer, fonts, etc.) is installed by `setup.sh`.

## Quick Start

```bash
git clone <repo-url>
cd nancy-drew-launcher-hypr

# First-time setup — installs deps, creates Wine prefix, extracts music
./setup.sh

# Launch
just run
# or: python3 launcher.py
```

`setup.sh` is idempotent and safe to re-run.

## Hyprland Window Rules

Add to `~/.config/hypr/hyprland.conf`:

```ini
windowrule = float, class:^(com.nancydrew.launcher)$
windowrule = opacity 0.95 override 0.92 override, class:^(com.nancydrew.launcher)$
windowrule = fullscreen, class:^(gamescope)$
```

## Game Files

Place each game in its own folder under `~/Games/NancyDrew/` (or wherever you point setup). Folders can be copied directly from a Windows install or disc image.

```
~/Games/NancyDrew/
├── wineprefix/
├── Secrets Can Kill/
├── Stay Tuned For Danger/
├── Message in a Haunted Mansion/
└── ...
```

If your game files are owned by root, setup will offer to fix that. Otherwise:

```bash
sudo chown -R $USER:$USER ~/Games/NancyDrew/
```

### Game-Specific Fixes

**Stay Tuned for Danger (#2)** expects `C:\STFD`. Create a symlink:

```bash
ln -s ~/Games/NancyDrew/Stay\ Tuned\ For\ Danger \
    ~/Games/NancyDrew/wineprefix/drive_c/STFD
```

**Kapu Cave (#15) & Blue Moon Canyon (#13)** need `RunInWindowedMode=1` in their `Game.INI` files under `~/Documents/<game>/Game.INI`.

## Thermal Management

These 2000s-era games use busy-loop rendering with no frame sleep, which will cook modern laptops. The launcher handles this automatically:

- **Gamescope** upscales from native res to 1280x960 instead of your full display resolution
- **`-r 30`** caps frames to 30fps (plenty for point-and-click)
- **`systemd-run` with `CPUQuota=80%`** throttles the entire game process tree at the kernel scheduler level — no audio stutter, no frame drops
- **`PULSE_LATENCY_MSEC=200`** gives the audio buffer headroom under CPU throttling

If things still get hot, check for zombie processes:

```bash
just status    # show running processes + thermals
just nuke      # kill everything cleanly
```

## Cursor Fix

If the cursor freezes after switching Hyprland workspaces mid-game, either press your fullscreen toggle keybind twice (e.g. `Super+Shift+F` x2), or run the included fix script in a separate terminal:

```bash
./gamescope-focus-fix.sh
```

This uses `socat` to watch Hyprland's event socket and automatically resets the cursor grab when gamescope regains focus.

## Just Commands

```bash
just run        # nuke old processes + launch
just nuke       # kill all game/wine/audio processes
just restart    # nuke + relaunch
just status     # show running processes and thermals
```

## License

MIT
