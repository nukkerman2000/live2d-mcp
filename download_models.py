#!/usr/bin/env python3
"""Auto-download Piper voice models and (optionally) Windows binaries.

Usage:
    python download_models.py            # voices only
    python download_models.py --piper    # voices + piper binaries
"""
import os
import sys
import zipfile
import argparse
import urllib.request
import urllib.error
import shutil
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOICES_DIR = os.path.join(BASE_DIR, "voices")
PIPER_DIR = os.path.join(BASE_DIR, "piper")

VOICES = [
    # lang, code, file name
    ("ru/ru_RU/irina/medium", "ru_RU-irina-medium"),
    ("ru/ru_RU/denis/medium", "ru_RU-denis-medium"),
    ("ru/ru_RU/ruslan/medium", "ru_RU-ruslan-medium"),
]

HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/{path}/{name}.onnx"
HF_CFG = "https://huggingface.co/rhasspy/piper-voices/resolve/main/{path}/{name}.onnx.json"

PIPER_RELEASE = "2023.11.14-2"
PIPER_URL = (
    "https://github.com/rhasspy/piper/releases/download/"
    f"{PIPER_RELEASE}/piper_windows_amd64.zip"
)


def human(n: int) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def download(url: str, dest: str, label: str):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length", 0))
            copied = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                copied += len(chunk)
                pct = f"  {copied / total * 100:.0f}%" if total else ""
                print(f"\r{label}: {human(copied)}{pct}  ", end="", flush=True)
        print()
        if os.path.getsize(tmp) == 0:
            raise RuntimeError("empty download")
        os.replace(tmp, dest)
        print(f"[OK] {label}: {human(os.path.getsize(dest))} -> {dest}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def download_voices():
    os.makedirs(VOICES_DIR, exist_ok=True)
    print("=== Voice models ===")
    ok, fail = 0, 0
    for path, name in VOICES:
        for label, url, dest in (
            (f"{name}.onnx", HF_BASE.format(path=path, name=name),
             os.path.join(VOICES_DIR, name + ".onnx")),
            (name + ".onnx.json", HF_CFG.format(path=path, name=name),
             os.path.join(VOICES_DIR, name + ".onnx.json")),
        ):
            try:
                download(url, dest, label)
                ok += 1
            except Exception as e:
                print(f"[FAIL] {label}: {e}")
                fail += 1
    print(f"Voices done: {ok} ok, {fail} failed (dir: {VOICES_DIR})")
    return fail == 0


def download_piper_binaries():
    print("\n=== Piper Windows binaries ===")
    target = os.path.join(PIPER_DIR, "piper.exe")
    if os.path.exists(target) and os.path.getsize(target) > 0:
        print("[SKIP] piper.exe already present")
        return True
    if sys.platform != "win32":
        print("[SKIP] non-Windows platform, binary not needed")
        return True
    os.makedirs(PIPER_DIR, exist_ok=True)
    tmp_zip = os.path.join(tempfile.gettempdir(), "piper_windows_amd64.zip")
    try:
        download(PIPER_URL, tmp_zip, "piper_windows_amd64.zip")
        with zipfile.ZipFile(tmp_zip) as z:
            for member in z.namelist():
                # flatten: piper/piper.exe -> piper/piper.exe
                dest = os.path.join(PIPER_DIR, os.path.basename(member))
                if not dest.startswith(PIPER_DIR + os.sep) and dest != PIPER_DIR:
                    continue
                if member.endswith("/"):
                    os.makedirs(dest, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with z.open(member) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
        print(f"[OK] piper binaries extracted to {PIPER_DIR}")
    finally:
        if os.path.exists(tmp_zip):
            os.remove(tmp_zip)
    return os.path.exists(target)


def main():
    ap = argparse.ArgumentParser(description="Download Piper voice models")
    ap.add_argument("--piper", action="store_true",
                    help="also download Piper Windows binaries (piper.exe + espeak-ng-data)")
    args = ap.parse_args()

    v_ok = download_voices()
    p_ok = True
    if args.piper:
        p_ok = download_piper_binaries()

    if v_ok and p_ok:
        print("\nDone! Run start.bat")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()