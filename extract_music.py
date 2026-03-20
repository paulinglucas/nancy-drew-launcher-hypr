#!/usr/bin/env python3
"""Extract background music from Nancy Drew .HIS files and convert to MP3.

Usage: python3 extract_music.py <games_dir> <assets_dir>
"""

import os
import subprocess
import sys
import tempfile

MUSIC_MAP = [
    # (output_id, game_folder, sound_subdir, his_filename, format)
    # format: "v2" = OggS embedded in HIS, "v1" = raw PCM offset 28, "oldest" = raw PCM offset 40

    ("nancy-drew-theme", "Secret of the Scarlet Hand", "CDSound", "Ndsig.his", "v2"),

    ("secrets-can-kill", "Secrets Can Kill", "CDSound", "Ndsig.his", "oldest"),
    ("stay-tuned-for-danger", "Stay Tuned For Danger", "CDSound", "stfd.his", "oldest"),
    ("message-in-a-haunted-mansion", "Message in a Haunted Mansion", "CDSound", "entry.his", "v1"),
    ("treasure-in-the-royal-tower", "Treasure in the Royal Tower", "CDSound", "trt.his", "v1"),
    ("the-final-scene", "The Final Scene", "CDSound", "maya.his", "v1"),
    ("secret-of-the-scarlet-hand", "Secret of the Scarlet Hand", "CDSound", "exotic.his", "v2"),
    ("ghost-dogs-of-moon-lake", "Ghost Dogs of Moon Lake", "CDSound", "Malone.HIS", "v2"),
    ("the-haunted-carousel", "The Haunted Carousel", "CDSound", "prowl.HIS", "v2"),
    ("danger-on-deception-island", "Danger on Deception Island", "CDSound", "Music_Cowboy.HIS", "v2"),
    ("secret-of-shadow-ranch", "Secret of Shadow Ranch", "CDSound", "BanjoTune02.HIS", "v2"),
    ("the-curse-of-blackmoor-manor", "The Curse of Blackmoor Manor", "CDSound", "Brigitte.HIS", "v2"),
    ("secret-of-the-old-clock", "Secret of the Old Clock", "HDSound", "Mystery.HIS", "v2"),
    ("last-train-to-blue-moon-canyon", "Last Train to Blue Moon Canyon", "CDSound", "Society.HIS", "v2"),
    ("danger-by-design", "Danger by Design", "HDSound", "Ndsig.his", "v2"),
    ("the-creature-of-kapu-cave", "The Creature of Kapu Cave", "HDSound", "Immersion.HIS", "v2"),
    ("the-creature-of-kapu-cave-canopy", "The Creature of Kapu Cave", "HDSound", "Canopy.HIS", "v2"),
    ("the-creature-of-kapu-cave-drums", "The Creature of Kapu Cave", "HDSound", "Drum_Upbeat_Music01.his", "v2"),
    ("the-white-wolf-of-icicle-creek", "The White Wolf of Icicle Creek", "Sound", "CRY_Teaser_Music.HIS", "v2"),
    ("legend-of-the-crystal-skull", "Legend of the Crystal Skull", "Sound", "Hoodoo.his", "v2"),
    ("the-phantom-of-venice", "The Phantom of Venice", "Sound", "VEN_Gondola.HIS", "v2"),
    ("the-haunting-of-castle-malloy", "The Haunting of Castle Malloy", "Sound", "DropsOfBrandy_Edit.HIS", "v2"),
    ("ransom-of-the-seven-ships", "Ransom of the Seven Ships", "Sound", "Ndsig.his", "v2"),
    ("warnings-at-waverly-academy", "Warnings at Waverly Academy", "Sound", "Piano_SFX.HIS", "v2"),
    ("warnings-at-waverly-academy-cello", "Warnings at Waverly Academy", "Sound", "Cello2_SFX.HIS", "v2"),
    ("trail-of-the-twister", "Trail of the Twister", "Sound", "Ndsig.his", "v2"),
    ("shadow-at-the-waters-edge", "Shadow at the Waters Edge", "Sound", "Traditional_sfx.HIS", "v2"),
    ("the-captive-curse", "The Captive Curse", "Sound", "Ndsig.his", "v2"),
    ("alibi-in-ashes", "Alibi in Ashes", "Sound", "Ndsig.his", "v2"),
    ("tomb-of-the-lost-queen", "Tomb of the Lost Queen", "Sound", "Ndsig.his", "v2"),
    ("the-deadly-device", "The Deadly Device", "Sound", "Ndsig.his", "v2"),
    ("ghost-of-thornton-hall", "Ghost of Thornton Hall", "Sound", "Wander_SFX.his", "v2"),
    ("the-silent-spy", "The Silent Spy", "Sound", "Ndsig.his", "v2"),
    ("the-shattered-medallion", "The Shattered Medallion", "Sound", "Ndsig.his", "v2"),
    ("sea-of-darkness", "Sea of Darkness", "Sound", "Ndsig.his", "v2"),
    ("midnight-in-salem", "Midnight in Salem", "Sound", "Ndsig.his", "v2"),
    ("secrets-can-kill-remastered", "Secrets Can Kill Remastered", "Sound", "Ndsig.his", "v2"),

    ("gondolier-rob-01", "The Phantom of Venice", "Sound", "song_italian_muffled_Rob01.HIS", "v2"),
    ("gondolier-rob-02", "The Phantom of Venice", "Sound", "song_italian_cls_eco_Rob02.HIS", "v2"),
    ("gondolier-rob-03", "The Phantom of Venice", "Sound", "song_italian_muffled_Rob03.HIS", "v2"),
    ("gondolier-andrew-03", "The Phantom of Venice", "Sound", "song_italian_echo_andrew03.HIS", "v2"),
    ("gondolier-andrew-04", "The Phantom of Venice", "Sound", "song_italian_muffled_And04.HIS", "v2"),
    ("gondolier-andrew-05", "The Phantom of Venice", "Sound", "song_italian_cls_eco_And05.HIS", "v2"),
    ("gondolier-tim-01", "The Phantom of Venice", "Sound", "song_italian_echo_cls_Tim01.HIS", "v2"),
    ("gondolier-tim-03", "The Phantom of Venice", "Sound", "song_italian_echo_Tim03.HIS", "v2"),
    ("gondolier-bob-05", "The Phantom of Venice", "Sound", "song_italian_eco_mfld_Bob05.HIS", "v2"),
    ("gondolier-brand", "The Phantom of Venice", "Sound", "song_italian_eco_cls_Brand_A.HIS", "v2"),

    ("punchy-arcade", "The Final Scene", "CDSound", "arcade.his", "v1"),
    ("punchy-partner-dance", "The Final Scene", "CDSound", "partneranimationsound.his", "v1"),
    ("punchy-sfx-bell", "The Final Scene", "CDSound", "BGM01.his", "v1"),
    ("punchy-sfx-clap", "The Final Scene", "CDSound", "BGM02.his", "v1"),
    ("punchy-sfx-whistle", "The Final Scene", "CDSound", "BGM03.his", "v1"),
    ("punchy-sfx-buzzer", "The Final Scene", "CDSound", "BGM04.his", "v1"),
    ("punchy-sfx-zap", "The Final Scene", "CDSound", "BGM05.his", "v1"),
    ("punchy-sfx-beeend", "The Final Scene", "CDSound", "beeend.his", "v1"),
    ("punchy-sfx-zapped", "The Final Scene", "CDSound", "ZAPPED.his", "v2"),
    ("punchy-sfx-beetheme", "The Final Scene", "CDSound", "beetheme.his", "v1"),
]

GOLD = "\033[38;5;178m"
GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"


def extract_his(his_path, fmt):
    with open(his_path, "rb") as f:
        data = f.read()

    if fmt == "v2":
        pos = data.find(b"OggS")
        if pos < 0:
            return None, None
        tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        tmp.write(data[pos:])
        tmp.close()
        return tmp.name, ["-i", tmp.name]

    offset = 28 if fmt == "v1" else 40
    tmp = tempfile.NamedTemporaryFile(suffix=".raw", delete=False)
    tmp.write(data[offset:])
    tmp.close()
    return tmp.name, ["-f", "u8", "-ar", "22050", "-ac", "1", "-i", tmp.name]


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <games_dir> <assets_dir>")
        sys.exit(1)

    games_dir = sys.argv[1]
    assets_dir = sys.argv[2]
    os.makedirs(assets_dir, exist_ok=True)

    ok_count = 0
    skip_count = 0
    fail_count = 0

    for out_id, game_folder, sound_subdir, his_name, fmt in MUSIC_MAP:
        out_path = os.path.join(assets_dir, f"{out_id}.mp3")
        his_path = os.path.join(games_dir, game_folder, sound_subdir, his_name)

        if os.path.exists(out_path):
            skip_count += 1
            continue

        if not os.path.exists(his_path):
            fail_count += 1
            continue

        tmp_path, input_args = extract_his(his_path, fmt)
        if tmp_path is None:
            print(f"  {RED}[fail]{RESET} {out_id}")
            fail_count += 1
            continue

        try:
            cmd = ["ffmpeg", "-y"] + input_args + ["-codec:a", "libmp3lame", "-qscale:a", "4", out_path]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                print(f"  {GREEN}[  ok]{RESET} {out_id}")
                ok_count += 1
            else:
                print(f"  {RED}[fail]{RESET} {out_id}")
                fail_count += 1
        finally:
            os.unlink(tmp_path)

    print(f"\n  Extracted: {GREEN}{ok_count}{RESET}  Skipped: {DIM}{skip_count}{RESET}  Missing: {RED}{fail_count}{RESET}")


if __name__ == "__main__":
    main()
