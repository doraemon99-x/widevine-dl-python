#!/usr/bin/env python3

import os
import shutil
import glob
import pathlib
import platform
import time
import subprocess
import re

FILE_DIRECTORY = str(pathlib.Path(__file__).parent.absolute())
TEMPORARY_PATH = os.path.join(FILE_DIRECTORY, "cache")
OUTPUT_PATH = os.path.join(FILE_DIRECTORY, "output")

# ==========================
# Utility
# ==========================

def osinfo():
    global PLATFORM
    PLATFORM = platform.system()

def divider():
    print('-' * shutil.get_terminal_size().columns)

def empty_folder(folder):
    files = glob.glob(os.path.join(folder, "*"))
    for f in files:
        os.remove(f)
    print("Emptied Temporary Files!")
    divider()
    quit()

def extract_key(prompt):
    global key, kid, keys
    key = prompt[30:62]
    kid = prompt[68:100]
    keys = f"{kid}:{key}"
    return key, kid, keys

# ==========================
# Download
# ==========================

def download_drm_content(mpd_url):
    divider()
    print("Processing Video Info..")

    subprocess.run([
        "yt-dlp",
        "--external-downloader", "aria2c",
        "--no-warnings",
        "--allow-unplayable-formats",
        "--no-check-certificate",
        "-F", mpd_url
    ])

    divider()

    VIDEO_ID = input("ENTER VIDEO_ID (Press Enter for Best): ").strip()
    if VIDEO_ID == "":
        VIDEO_ID = "bv"

    AUDIO_ID = input("ENTER AUDIO_ID (Press Enter for Best): ").strip()
    if AUDIO_ID == "":
        AUDIO_ID = "ba"

    divider()
    print("Downloading Encrypted Video from CDN..")

    subprocess.run([
        "yt-dlp",
        "-f", VIDEO_ID,
        "-o", os.path.join(TEMPORARY_PATH, "encrypted_video.%(ext)s"),
        "--no-warnings",
        "--external-downloader", "aria2c",
        "--allow-unplayable-formats",
        "--no-check-certificate",
        mpd_url
    ])

    print("Downloading Encrypted Audio from CDN..")

    subprocess.run([
        "yt-dlp",
        "-f", AUDIO_ID,
        "-o", os.path.join(TEMPORARY_PATH, "encrypted_audio.%(ext)s"),
        "--no-warnings",
        "--external-downloader", "aria2c",
        "--allow-unplayable-formats",
        "--no-check-certificate",
        mpd_url
    ])

# ==========================
# Decrypt
# ==========================

def decrypt_content():
    extract_key(KEY_PROMPT)
    divider()
    print("Decrypting WideVine DRM.. (Takes some time)")
    osinfo()

    if PLATFORM == "Windows":
        mp4decrypt_path = os.path.join(FILE_DIRECTORY, "mp4decrypt", "mp4decrypt_win.exe")
    elif PLATFORM == "Darwin":
        mp4decrypt_path = os.path.join(FILE_DIRECTORY, "mp4decrypt", "mp4decrypt_mac")
    elif PLATFORM == "Linux":
        mp4decrypt_path = os.path.join(FILE_DIRECTORY, "mp4decrypt", "mp4decrypt_linux")
    else:
        mp4decrypt_path = "mp4decrypt"

    if not os.path.exists(mp4decrypt_path):
        print("ERROR: mp4decrypt not found!")
        return

    video_files = glob.glob(os.path.join(TEMPORARY_PATH, "encrypted_video.*"))
    audio_files = glob.glob(os.path.join(TEMPORARY_PATH, "encrypted_audio.*"))

    if not video_files or not audio_files:
        print("ERROR: Encrypted files not found!")
        return

    video_in = video_files[0]
    audio_in = audio_files[0]

    video_out = os.path.join(TEMPORARY_PATH, "decrypted_video.mp4")
    audio_out = os.path.join(TEMPORARY_PATH, "decrypted_audio.m4a")

    try:
        subprocess.run(
            [mp4decrypt_path, video_in, video_out, "--key", keys],
            check=True
        )

        subprocess.run(
            [mp4decrypt_path, audio_in, audio_out, "--key", keys],
            check=True
        )

        print("Decryption Complete!")

    except subprocess.CalledProcessError:
        print("ERROR: Decryption failed!")

# ==========================
# Detect Audio Offset
# ==========================

def get_audio_offset(audio_path):
    result = subprocess.run(
        ["ffmpeg", "-i", audio_path],
        stderr=subprocess.PIPE,
        text=True
    )

    match = re.search(r"start:\s*([0-9\.]+)", result.stderr)
    if match:
        return float(match.group(1))
    return 0.0

# ==========================
# Merge (Correct DASH Handling)
# ==========================

def merge_content():
    divider()
    FILENAME = input("Enter File Name (with extension): \n> ").strip()
    divider()
    print(f"Merging Files with Correct DASH Offset for {FILENAME}..")
    time.sleep(1)

    video_path = os.path.join(TEMPORARY_PATH, "decrypted_video.mp4")
    audio_path = os.path.join(TEMPORARY_PATH, "decrypted_audio.m4a")
    output_file = os.path.join(OUTPUT_PATH, FILENAME)

    if not os.path.exists(video_path) or not os.path.exists(audio_path):
        print("ERROR: Decrypted files not found!")
        return

    offset = get_audio_offset(audio_path)
    print(f"Detected audio start offset: {offset} seconds")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-itsoffset", str(offset),
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c", "copy",
        output_file
    ])

    print("Merge Complete (DASH Offset Preserved)!")

# ==========================
# MAIN
# ==========================

divider()
print("**** Widevine-DL (DASH Correct Version) ****")
divider()

MPD_URL = input("Enter MPD URL: \n> ").strip()
KEY_PROMPT = input("Enter WideVineDecryptor Prompt: \n> ").strip()

download_drm_content(MPD_URL)
decrypt_content()
merge_content()

divider()
print("Process Finished. Final Video File is saved in /output directory.")
divider()

delete_choice = input("Delete cache files? (y/n)\ny) Yes (default)\nn) No\ny/n> ").strip().lower()

if delete_choice != "n":
    empty_folder(TEMPORARY_PATH)