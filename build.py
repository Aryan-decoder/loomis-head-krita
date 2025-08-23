#!/usr/bin/env python3
import os
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[0]
PLUGIN_NAME = "loomis_head"
DESKTOP_FILE = "loomis_head.desktop"
ZIP_FILE_NAME = "loomis_head"
PLUGIN_SRC = ROOT / PLUGIN_NAME

BUILD_DIR = ROOT / "build"
BUILD_PLUGIN_DIR = BUILD_DIR / PLUGIN_NAME
DIST_DIR = ROOT / "dist"


def main():
    if not BUILD_DIR.exists():
        os.mkdir(BUILD_DIR)
    else:
        shutil.rmtree(BUILD_DIR)

    shutil.copytree(PLUGIN_SRC, BUILD_PLUGIN_DIR)
    shutil.copy(ROOT / DESKTOP_FILE, BUILD_DIR)

    if not DIST_DIR.exists():
        os.mkdir(DIST_DIR)
    else:
        shutil.rmtree(DIST_DIR)

    shutil.make_archive(DIST_DIR / ZIP_FILE_NAME, "zip", BUILD_DIR)

if __name__ == "__main__":
    main()
