#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GOLD='\033[38;5;178m'
DIM='\033[2m'
GREEN='\033[32m'
RED='\033[31m'
RESET='\033[0m'

info()  { echo -e "${GOLD}[setup]${RESET} $1"; }
ok()    { echo -e "${GREEN}[  ok ]${RESET} $1"; }
warn()  { echo -e "${RED}[warn]${RESET} $1"; }
ask()   { echo -en "${GOLD}[  ? ]${RESET} $1"; }

echo ""
echo -e "${GOLD}╔══════════════════════════════════════╗${RESET}"
echo -e "${GOLD}║     NANCY DREW LAUNCHER — SETUP      ║${RESET}"
echo -e "${GOLD}╚══════════════════════════════════════╝${RESET}"
echo ""

info "Checking for multilib in pacman.conf..."
if grep -q '^\[multilib\]' /etc/pacman.conf; then
    ok "multilib is enabled"
else
    warn "multilib does not appear to be enabled in /etc/pacman.conf"
    echo "  Wine requires 32-bit libraries from multilib."
    echo "  Uncomment the [multilib] section in /etc/pacman.conf, then run: sudo pacman -Sy"
    ask "Continue anyway? [y/N] "
    read -r ans
    [[ "$ans" =~ ^[Yy] ]] || exit 1
fi

DEPS=(
    python python-gobject gtk4 libadwaita
    gstreamer gst-plugins-base gst-plugins-good
    wine-staging winetricks lib32-mesa lib32-vulkan-icd-loader
    gamescope ffmpeg
)

info "Installing dependencies via pacman..."
TO_INSTALL=()
for pkg in "${DEPS[@]}"; do
    if ! pacman -Qi "$pkg" &>/dev/null; then
        TO_INSTALL+=("$pkg")
    fi
done

if [ ${#TO_INSTALL[@]} -gt 0 ]; then
    info "Installing: ${TO_INSTALL[*]}"
    sudo pacman -S --needed --noconfirm "${TO_INSTALL[@]}"
    ok "Dependencies installed"
else
    ok "All dependencies already installed"
fi

DEFAULT_GAMES_DIR="$HOME/Games/NancyDrew"
ask "Games directory [${DEFAULT_GAMES_DIR}]: "
read -r GAMES_DIR
GAMES_DIR="${GAMES_DIR:-$DEFAULT_GAMES_DIR}"
GAMES_DIR="${GAMES_DIR/#\~/$HOME}"

if [ -d "$GAMES_DIR" ]; then
    OWNER=$(stat -c '%U' "$GAMES_DIR")
    if [ "$OWNER" != "$USER" ]; then
        warn "Games directory is owned by $OWNER, not $USER"
        ask "Fix ownership with sudo? [Y/n] "
        read -r ans
        if [[ ! "$ans" =~ ^[Nn] ]]; then
            sudo chown -R "$USER:$USER" "$GAMES_DIR"
            ok "Fixed ownership"
        fi
    fi
fi

if [ ! -d "$GAMES_DIR" ]; then
    warn "Directory does not exist: $GAMES_DIR"
    ask "Create it? [Y/n] "
    read -r ans
    if [[ ! "$ans" =~ ^[Nn] ]]; then
        mkdir -p "$GAMES_DIR"
        ok "Created $GAMES_DIR"
    else
        warn "Games directory not found — config will be generated but games won't launch until the directory exists."
    fi
fi

ok "Output resolution: 1280x960 (optimized for thermals)"

WINEPREFIX="$GAMES_DIR/wineprefix"
info "Setting up 32-bit Wine prefix at $WINEPREFIX..."
if [ -d "$WINEPREFIX" ]; then
    ok "Wine prefix already exists"
else
    WINEPREFIX="$WINEPREFIX" WINEARCH=win32 wineboot --init
    ok "Wine prefix created"
fi

info "Installing common winetricks dependencies..."
WINEPREFIX="$WINEPREFIX" winetricks -q d3dx9 quartz wmp9 vcrun6 || {
    warn "Some winetricks installations failed — this is sometimes expected. Games may still work."
}
ok "Winetricks done"

ask "Install QuickTime 7.2 for older titles (games 1-7)? [y/N] "
read -r ans
if [[ "$ans" =~ ^[Yy] ]]; then
    info "Installing quicktime72..."
    WINEPREFIX="$WINEPREFIX" winetricks -q quicktime72 || {
        warn "QuickTime install had issues — older games may still have problems."
    }
    ok "QuickTime installed"
fi

FONT_DIR="$HOME/.local/share/fonts"
mkdir -p "$FONT_DIR"

install_google_font() {
    local family="$1"
    local url_family="${family// /+}"
    local dest="$FONT_DIR/${family}"

    if [ -d "$dest" ] && [ "$(ls -A "$dest" 2>/dev/null)" ]; then
        ok "Font already installed: $family"
        return
    fi

    info "Downloading font: $family..."
    mkdir -p "$dest"

    local zip_url="https://fonts.google.com/download?family=${url_family}"
    local tmpfile
    tmpfile=$(mktemp /tmp/font-XXXXXX.zip)

    if curl -fsSL -o "$tmpfile" "$zip_url"; then
        unzip -qo "$tmpfile" -d "$dest" '*.ttf' 2>/dev/null || \
        unzip -qo "$tmpfile" -d "$dest" '*.otf' 2>/dev/null || true
        rm -f "$tmpfile"
        ok "Installed: $family"
    else
        warn "Could not download font: $family (non-critical, GTK will use fallback)"
        rm -f "$tmpfile"
    fi
}

install_google_font "Playfair Display"
install_google_font "DM Sans"
install_google_font "Special Elite"

fc-cache -f "$FONT_DIR" 2>/dev/null
ok "Font cache updated"

info "Generating config.json..."

GAMES_DB="${SCRIPT_DIR}/games.json"
if [ ! -f "$GAMES_DB" ]; then
    warn "games.json not found — cannot generate config"
    exit 1
fi

GAMES_JSON=$(python3 << PYEOF
import json, os, subprocess

with open("${GAMES_DB}") as f:
    db = json.load(f)

games_dir = "${GAMES_DIR}"
entries = []

for g in db:
    folder_path = os.path.join(games_dir, g["folder"])
    found = os.path.isdir(folder_path)
    exe = "Game.exe"

    if found:
        result = subprocess.run(
            ["find", folder_path, "-maxdepth", "2", "-iname", "*.exe",
             "!", "-iname", "unins*", "!", "-iname", "setup*", "!", "-iname", "_*"],
            capture_output=True, text=True
        )
        exes = [l for l in result.stdout.strip().split("\n") if l]
        if exes:
            exes.sort(key=lambda p: (p.count("/"), p))
            exe = os.path.relpath(exes[0], folder_path)

    title = g["title"]
    game_id = title.lower()
    for ch in "'":
        game_id = game_id.replace(ch, "")
    game_id = "-".join(game_id.split())

    res = g.get("resolution", [1024, 768])
    settings = {}
    if res != [1024, 768]:
        settings["game_width"] = res[0]
        settings["game_height"] = res[1]

    entries.append({
        "id": game_id,
        "title": title,
        "folder": g["folder"],
        "exe": exe,
        "number": g["number"],
        "year": g["year"],
        "found": found,
        "status": "untested",
        "settings": settings,
    })

print(json.dumps(entries, indent=2))
PYEOF
)

cat > "$SCRIPT_DIR/config.json" << CONFIGEOF
{
  "games_dir": "${GAMES_DIR}",
  "wineprefix": "${WINEPREFIX}",
  "music_selection": "random",
  "default_settings": {
    "game_width": 1024,
    "game_height": 768,
    "output_width": 1280,
    "output_height": 960,
    "use_gamescope": true,
    "env_vars": {}
  },
  "games": ${GAMES_JSON}
}
CONFIGEOF

ok "config.json generated"

FOUND_COUNT=$(python3 -c "import json;d=json.load(open('${SCRIPT_DIR}/config.json'));print(sum(1 for g in d['games'] if g['found']))")
TOTAL_COUNT=$(python3 -c "import json;print(len(json.load(open('${GAMES_DB}'))))")
info "Found $FOUND_COUNT / $TOTAL_COUNT game directories on disk"

info "Extracting background music from game files..."
if command -v ffmpeg &>/dev/null; then
    python3 "${SCRIPT_DIR}/extract_music.py" "$GAMES_DIR" "${SCRIPT_DIR}/assets"
    ok "Music extraction complete"
else
    warn "ffmpeg not found — skipping music extraction. Install ffmpeg and re-run setup."
fi

info "Creating game save directories..."
python3 -c "
import json, os
docs = os.path.join('${WINEPREFIX}', 'drive_c', 'users', os.environ['USER'], 'Documents')
with open('${GAMES_DB}') as f:
    games = json.load(f)
for g in games:
    os.makedirs(os.path.join(docs, g['title']), exist_ok=True)
"
ok "Save directories created"

info "Installing .desktop file..."
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/nancy-drew-launcher.desktop" << DESKTOPEOF
[Desktop Entry]
Name=Nancy Drew Launcher
Comment=Launch Nancy Drew games via Wine
Exec=python3 ${SCRIPT_DIR}/launcher.py
Icon=${SCRIPT_DIR}/assets/icon.svg
Terminal=false
Type=Application
Categories=Game;
DESKTOPEOF

cp "$DESKTOP_DIR/nancy-drew-launcher.desktop" "$SCRIPT_DIR/nancy-drew-launcher.desktop"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
ok ".desktop file installed"

echo ""
echo -e "${GOLD}╔══════════════════════════════════════╗${RESET}"
echo -e "${GOLD}║           SETUP COMPLETE             ║${RESET}"
echo -e "${GOLD}╚══════════════════════════════════════╝${RESET}"
echo ""
echo -e "  Games directory:  ${DIM}${GAMES_DIR}${RESET}"
echo -e "  Wine prefix:      ${DIM}${WINEPREFIX}${RESET}"
echo -e "  Games found:      ${GREEN}${FOUND_COUNT}${RESET} / ${TOTAL_COUNT}"
echo -e "  Config:           ${DIM}${SCRIPT_DIR}/config.json${RESET}"
echo ""
echo -e "  ${GOLD}To launch:${RESET}"
echo -e "    python3 ${SCRIPT_DIR}/launcher.py"
echo -e "    ${DIM}— or use your app launcher (search 'Nancy Drew')${RESET}"
echo ""
