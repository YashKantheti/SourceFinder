"""
One-time setup: downloads the Enterprise ATT&CK STIX bundle (~10MB).
Run this before starting the app for the first time.

Usage: python setup.py
"""
import urllib.request
import os
import sys

BUNDLE_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data"
    "/master/enterprise-attack/enterprise-attack.json"
)
BUNDLE_PATH = "enterprise-attack.json"


def download():
    if os.path.exists(BUNDLE_PATH):
        print(f"Bundle already exists at {BUNDLE_PATH} — skipping download.")
        return
    print("Downloading Enterprise ATT&CK STIX bundle (~10MB)...")
    try:
        urllib.request.urlretrieve(BUNDLE_URL, BUNDLE_PATH)
        print(f"Done. Saved to {BUNDLE_PATH}")
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    download()
