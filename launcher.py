#!/usr/bin/env python3
"""Nancy Drew Launcher — GTK4 native app for running Nancy Drew games via Wine on Hyprland"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Adw, Gst, Gio, GLib, Gdk
import json
import subprocess
import os
import sys
import random
import threading

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
STYLE_PATH = os.path.join(APP_DIR, "style.css")

_TRACK_DISPLAY_NAMES = {
    "nancy-drew-theme": "Nancy Drew Theme (Classic)",
    "shadow-at-the-waters-edge": "Shadow at the Water's Edge",
    "venice-matinatta": "Venice \u2014 Matinatta",
    "venice-pigeon": "Venice \u2014 Pigeon",
    "venice-tourist": "Venice \u2014 Tourist",
    "punchy-indira": "Punchy \u2014 Indira",
    "punchy-tablaesque": "Punchy \u2014 Tablaesque",
    "gondolier-rob-01": "Gondolier \u2014 Rob",
    "gondolier-andrew-03": "Gondolier \u2014 Andrew",
    "gondolier-bob-05": "Gondolier \u2014 Bob",
}

PUNCHY_SFX = [
    "punchy-sfx-bell",
    "punchy-sfx-buzzer",
    "punchy-sfx-clap",
    "punchy-sfx-laser",
    "punchy-sfx-ocarina",
    "punchy-sfx-siren",
    "punchy-sfx-whistle",
    "punchy-sfx-whistle-police-3",
    "punchy-sfx-whistle-police-4",
]

_VARIANT_SUFFIXES = {
    "-canopy": "Canopy", "-drums": "Drums", "-immersion": "Immersion",
    "-cello": "Cello", "-piano": "Piano",
}


def _track_display_name(track_id):
    if track_id in _TRACK_DISPLAY_NAMES:
        return _TRACK_DISPLAY_NAMES[track_id]

    name = track_id
    suffix = ""
    for var_suffix, var_label in _VARIANT_SUFFIXES.items():
        if name.endswith(var_suffix):
            name = name[: -len(var_suffix)]
            suffix = f" ({var_label})"
            break

    words = name.replace("-", " ").split()
    small = {"of", "the", "in", "a", "at", "on", "to", "by", "for", "and"}
    parts = []
    for i, w in enumerate(words):
        parts.append(w.capitalize() if (i == 0 or w not in small) else w)
    return " ".join(parts) + suffix


def discover_music_tracks():
    assets_dir = os.path.join(APP_DIR, "assets")
    tracks = {}
    if not os.path.isdir(assets_dir):
        return tracks
    for fname in sorted(os.listdir(assets_dir)):
        if fname.lower().endswith(".mp3"):
            track_id = fname[:-4]
            if track_id.startswith("punchy-sfx-"):
                continue
            tracks[track_id] = _track_display_name(track_id)
    venice = {k: v for k, v in sorted(tracks.items()) if k.startswith("venice-")}
    punchy = {k: v for k, v in sorted(tracks.items()) if k.startswith("punchy-") and not k.startswith("punchy-sfx-")}
    gondolier = {k: v for k, v in sorted(tracks.items()) if k.startswith("gondolier-")}
    for k in {**venice, **punchy, **gondolier}:
        del tracks[k]
    # Game music (alphabetical), then Venice, Punchy, Gondolier
    result = dict(sorted(tracks.items(), key=lambda x: x[1].lower()))
    result.update(venice)
    result.update(punchy)
    result.update(gondolier)
    tracks = result
    return tracks


MUSIC_TRACKS = discover_music_tracks()
RANDOMIZE_KEY = "random"


class NancyDrewLauncher(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.nancydrew.launcher')
        self.config = None
        self.player = None
        self.listbox = None
        Gst.init(None)

    def do_activate(self):
        self.config = self.load_config()
        if self.config is None:
            dialog = Gtk.AlertDialog()
            dialog.set_message("config.json not found. Run setup.sh first.")
            dialog.show(None)
            return

        self.load_css()

        win = Adw.ApplicationWindow(application=self)
        win.set_title("Nancy Drew \u2014 Case Files")
        win.set_default_size(420, 720)
        win.set_resizable(True)
        self._win = win

        outer_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer_frame.add_css_class("outer-frame")
        win.set_content(outer_frame)

        inner_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner_frame.add_css_class("inner-frame")
        outer_frame.append(inner_frame)

        header_handle = Gtk.WindowHandle()
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header_box.add_css_class("header-box")

        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        top_bar.add_css_class("top-bar")

        nd_btn = Gtk.Button(label="ND")
        nd_btn.add_css_class("nd-monogram")
        nd_btn.connect("clicked", self.on_punchy_click)
        top_bar.append(nd_btn)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_bar.append(spacer)

        close_btn = Gtk.Button(label="\u2715")
        close_btn.add_css_class("close-button")
        close_btn.connect("clicked", lambda btn: win.close())
        top_bar.append(close_btn)

        header_box.append(top_bar)

        title_label = Gtk.Label(label="NANCY DREW")
        title_label.set_halign(Gtk.Align.CENTER)
        title_label.add_css_class("app-title")
        header_box.append(title_label)

        subtitle_label = Gtk.Label(label="\u2500\u2500\u2500  CASE FILES  \u2500\u2500\u2500")
        subtitle_label.set_halign(Gtk.Align.CENTER)
        subtitle_label.add_css_class("app-subtitle")
        header_box.append(subtitle_label)

        divider_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        divider_box.set_halign(Gtk.Align.CENTER)
        divider_box.set_margin_top(8)
        divider_box.set_margin_bottom(4)

        left_flourish = Gtk.Label(label="\u2E31\u2E31\u2E31\u2500\u2500\u2500")
        left_flourish.add_css_class("flourish")
        divider_box.append(left_flourish)

        diamond = Gtk.Label(label="\u25C6")
        diamond.add_css_class("ornament-diamond")
        divider_box.append(diamond)

        right_flourish = Gtk.Label(label="\u2500\u2500\u2500\u2E31\u2E31\u2E31")
        right_flourish.add_css_class("flourish")
        divider_box.append(right_flourish)

        header_box.append(divider_box)

        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search cases...")
        search_entry.add_css_class("search-entry")
        search_entry.set_margin_top(6)
        search_entry.connect("search-changed", self.on_search_changed)
        header_box.append(search_entry)

        header_handle.set_child(header_box)
        inner_frame.append(header_handle)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add_css_class("scrolled-area")

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.add_css_class("game-list")
        self.listbox.set_filter_func(self.filter_func)

        games = sorted(self.config.get("games", []), key=lambda g: (not g.get("found", False), g.get("number", 0)))
        for game in games:
            self.listbox.append(self.build_game_row(game))

        scrolled.set_child(self.listbox)
        inner_frame.append(scrolled)

        footer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        footer_box.add_css_class("footer-box")

        footer_divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        footer_divider.add_css_class("ornate-divider")
        footer_box.append(footer_divider)

        music_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        music_row.set_margin_top(8)
        music_row.set_margin_bottom(6)
        music_row.add_css_class("music-row")

        music_icon = Gtk.Label(label="\u266B")
        music_icon.add_css_class("music-icon")
        music_row.append(music_icon)

        self.music_dropdown = Gtk.DropDown()
        music_choices = [RANDOMIZE_KEY, "none"] + list(MUSIC_TRACKS.keys())
        display_names = ["\u2728 Randomize", "\u2014 No Music"] + list(MUSIC_TRACKS.values())
        string_list = Gtk.StringList.new(display_names)
        self.music_dropdown.set_model(string_list)
        self.music_dropdown.set_expression(Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
        self.music_dropdown.add_css_class("music-dropdown")
        self.music_dropdown.set_hexpand(True)
        self.music_dropdown.set_enable_search(True)
        self.music_dropdown.set_search_match_mode(Gtk.StringFilterMatchMode.SUBSTRING)
        self._music_choices = music_choices

        current = self.config.get("music_selection", RANDOMIZE_KEY)
        if current in music_choices:
            self.music_dropdown.set_selected(music_choices.index(current))

        self.music_dropdown.connect("notify::selected", self.on_music_changed)
        music_row.append(self.music_dropdown)

        footer_box.append(music_row)

        inner_frame.append(footer_box)

        win.present()
        self.play_theme_music()

    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            return None
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)

    def save_config(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=2)

    def load_css(self):
        if not os.path.exists(STYLE_PATH):
            return
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(STYLE_PATH)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def build_game_row(self, game):
        row = Gtk.ListBoxRow()
        row.add_css_class("game-row")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.add_css_class("game-row-inner")

        case_num = Gtk.Label(label=f"#{game.get('number', '?'):02d}")
        case_num.set_valign(Gtk.Align.CENTER)
        case_num.add_css_class("case-number")
        box.append(case_num)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info_box.set_hexpand(True)
        info_box.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label(label=game.get("title", "Unknown"))
        title.set_halign(Gtk.Align.START)
        title.set_ellipsize(3)
        title.add_css_class("case-title")
        info_box.append(title)

        year = Gtk.Label(label=str(game.get("year", "")))
        year.set_halign(Gtk.Align.START)
        year.add_css_class("case-year")
        info_box.append(year)

        box.append(info_box)

        launch_btn = Gtk.Button(label="\u25B6")
        launch_btn.add_css_class("launch-button")
        launch_btn.set_valign(Gtk.Align.CENTER)
        launch_btn.connect("clicked", lambda btn, g=game: self.launch_game(g))
        box.append(launch_btn)

        row.set_child(box)

        if not game.get("found", True):
            row.add_css_class("game-not-found")
            launch_btn.set_sensitive(False)

        row._game_title = game.get("title", "").lower()
        row._game_number = str(game.get("number", ""))

        return row

    def on_search_changed(self, entry):
        self._search_text = entry.get_text().lower()
        self.listbox.invalidate_filter()

    def filter_func(self, row):
        search = getattr(self, "_search_text", "")
        if not search:
            return True
        if hasattr(row, "_game_title"):
            return search in row._game_title or search == row._game_number
        return True

    def _kill_active_game(self):
        """Kill any currently running game before launching a new one."""
        if hasattr(self, '_game_proc') and self._game_proc and self._game_proc.poll() is None:
            self._game_proc.kill()
            self._game_proc.wait()
        # Kill wineserver to clean up all wine children
        wineprefix = os.path.expanduser(self.config.get("wineprefix", ""))
        if wineprefix:
            subprocess.run(
                ["wineserver", "-k9"],
                env={**os.environ, "WINEPREFIX": wineprefix},
                timeout=5, capture_output=True,
            )
        # Kill wine audio streams
        try:
            result = subprocess.run(
                ["pactl", "list", "short", "sink-inputs"],
                capture_output=True, text=True, timeout=3,
            )
            for line in result.stdout.splitlines():
                if "wine" in line.lower() or "Nancy Drew" in line:
                    parts = line.split('\t')
                    if parts:
                        subprocess.run(["pactl", "kill-sink-input", parts[0]],
                                       capture_output=True)
        except Exception:
            pass

    def launch_game(self, game):
        self.stop_theme_music()
        self._kill_active_game()

        config = self.config
        env = os.environ.copy()
        env["WINEPREFIX"] = os.path.expanduser(config["wineprefix"])

        games_dir = os.path.expanduser(config["games_dir"])
        exe_path = os.path.join(games_dir, game["folder"], game["exe"])
        work_dir = os.path.dirname(exe_path)

        if not os.path.exists(exe_path):
            self.play_theme_music()
            return

        defaults = config.get("default_settings", {})
        overrides = game.get("settings", {})
        settings = {**defaults, **overrides}

        for k, v in settings.get("env_vars", {}).items():
            env[k] = v

        # Wine Staging optimizations for old DirectDraw games
        env["WINE_FSYNC"] = "1"
        env["STAGING_WRITECOPY"] = "1"
        env["PULSE_LATENCY_MSEC"] = "200"

        gw = settings.get("game_width", 1024)
        gh = settings.get("game_height", 768)
        ow = settings.get("output_width")
        oh = settings.get("output_height")

        gamescope_cmd = ["gamescope", "-w", str(gw), "-h", str(gh)]
        if ow and oh:
            gamescope_cmd += ["-W", str(ow), "-H", str(oh)]
        gamescope_cmd += ["-f", "-r", "30", "--", "wine", exe_path]

        # Launch via systemd-run with CPU quota to prevent overheating.
        # Uses kernel CFS bandwidth throttling (not SIGSTOP) so audio
        # stays smooth via the PULSE_LATENCY_MSEC buffer.
        cmd = [
            "systemd-run", "--user", "--scope",
            "-p", "CPUQuota=80%",
            "--",
        ] + gamescope_cmd

        proc = subprocess.Popen(
            cmd, env=env, cwd=work_dir,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self._game_proc = proc

        self._win.set_visible(False)

        def _reap(p):
            p.wait()
            self._kill_active_game()
            GLib.idle_add(self._win.set_visible, True)
            GLib.idle_add(self.play_theme_music)

        threading.Thread(target=_reap, args=(proc,), daemon=True).start()

    def update_status(self, game_id, new_status):
        for game in self.config.get("games", []):
            if game["id"] == game_id:
                game["status"] = new_status
                break
        self.save_config()

    def get_music_track_path(self):
        selection = self.config.get("music_selection", RANDOMIZE_KEY)

        if selection == "none":
            return None
        if selection == RANDOMIZE_KEY:
            available = []
            for track_id in MUSIC_TRACKS:
                path = os.path.join(APP_DIR, "assets", f"{track_id}.mp3")
                if os.path.exists(path):
                    available.append(path)
            return random.choice(available) if available else None
        else:
            path = os.path.join(APP_DIR, "assets", f"{selection}.mp3")
            return path if os.path.exists(path) else None

    def play_theme_music(self):
        theme_path = self.get_music_track_path()
        if not theme_path:
            return

        self.player = Gst.ElementFactory.make("playbin", "player")
        if self.player is None:
            return

        self.player.set_property("uri", GLib.filename_to_uri(theme_path, None))

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.on_music_eos)

        self.player.set_state(Gst.State.PLAYING)

    def on_music_eos(self, bus, message):
        if self.player:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)

    def on_music_changed(self, dropdown, _pspec):
        idx = dropdown.get_selected()
        selection = self._music_choices[idx]
        self.config["music_selection"] = selection
        self.save_config()

        self.stop_theme_music()
        self.play_theme_music()

    def on_punchy_click(self, btn):
        available = [s for s in PUNCHY_SFX if os.path.exists(os.path.join(APP_DIR, "assets", f"{s}.mp3"))]
        if not available:
            return
        sfx_path = os.path.join(APP_DIR, "assets", f"{random.choice(available)}.mp3")
        sfx_player = Gst.ElementFactory.make("playbin", None)
        if sfx_player is None:
            return
        sfx_player.set_property("uri", GLib.filename_to_uri(sfx_path, None))
        bus = sfx_player.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", lambda b, m: sfx_player.set_state(Gst.State.NULL))
        sfx_player.set_state(Gst.State.PLAYING)

    def stop_theme_music(self):
        if self.player:
            self.player.set_state(Gst.State.NULL)
            self.player = None


if __name__ == '__main__':
    app = NancyDrewLauncher()
    app.run(sys.argv)
