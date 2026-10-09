#!/usr/bin/env python3
"""List / download raw videos from a PUBLIC Google Drive folder with gdown.

usage:
  drive_download.py list  FOLDER_URL                      # list files (no download), skips finished subfolders
  drive_download.py fetch FOLDER_URL -d raw/ [--only ID ...] [--skip-existing]
  drive_download.py id    FILE_ID -d raw/ [-n name.mp4]

Subfolders whose path contains any --skip word (default: 'Hoàn thiện', 'Hoan thien', 'Done', 'Final')
are ignored = already finished videos. Output names are slugified (lowercase ascii, '_').
Install: pip install --break-system-packages gdown   (or use the venv from setup.sh)
"""
import argparse
import os
import re
import sys
import unicodedata

import gdown

SKIP = ["Hoàn thiện", "Hoan thien", "Done", "Final"]


def slug(s):
    base, ext = os.path.splitext(s)
    base = unicodedata.normalize("NFD", base.replace("đ", "d").replace("Đ", "D"))
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_").lower()
    return base + (ext.lower() or ".mp4")


def listing(url, skip):
    files = gdown.download_folder(url, skip_download=True, quiet=True, remaining_ok=True) or []
    out = []
    for f in files:
        parts = f.path.split(os.sep)
        if any(k.lower() in p.lower() for p in parts[:-1] for k in skip):
            continue
        out.append(f)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "fetch", "id"])
    ap.add_argument("target")
    ap.add_argument("-d", "--dir", default="raw")
    ap.add_argument("-n", "--name")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--skip", nargs="*", default=SKIP)
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()

    if a.cmd == "id":
        os.makedirs(a.dir, exist_ok=True)
        out = os.path.join(a.dir, a.name or "")
        print(gdown.download(id=a.target, output=out if a.name else a.dir + os.sep, quiet=False))
        return
    files = listing(a.target, a.skip)
    if a.cmd == "list":
        for f in files:
            print(f"{f.id}\t{f.path}\t-> {slug(os.path.basename(f.path))}")
        print(f"# {len(files)} file(s)", file=sys.stderr)
        return
    os.makedirs(a.dir, exist_ok=True)
    for f in files:
        if a.only and f.id not in a.only:
            continue
        out = os.path.join(a.dir, slug(os.path.basename(f.path)))
        if a.skip_existing and os.path.exists(out) and os.path.getsize(out) > 0:
            print(f"skip {out}")
            continue
        try:
            print(f.id, gdown.download(id=f.id, output=out, quiet=True), flush=True)
        except Exception as e:  # keep going on the batch
            print(f.id, "FAIL", e, flush=True)


if __name__ == "__main__":
    main()
