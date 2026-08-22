"""Build script: packages the app into a standalone Windows .exe using PyInstaller."""

import shutil
from pathlib import Path

import PyInstaller.__main__

BASE_DIR = Path(__file__).parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"


def clean_build_artifacts():
    """Remove old build artifacts to ensure a clean build."""
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
    spec_file = BASE_DIR / "main.spec"
    if spec_file.exists():
        spec_file.unlink()


def build_exe():
    """Build the .exe using PyInstaller."""
    data_files = [
        (str(BASE_DIR / "data"), "data"),
    ]

    PyInstaller.__main__.run(
        [
            str(BASE_DIR / "main.py"),
            "--name=دمج_بيانات_الحيازات_الزراعية",
            "--onefile",
            "--windowed",
            "--noconfirm",
            f"--distpath={DIST_DIR}",
            f"--workpath={BUILD_DIR}",
            f"--specpath={BASE_DIR}",
        ]
        + [f"--add-data={src};{dst}" for src, dst in data_files],
    )


if __name__ == "__main__":
    print("Cleaning old build artifacts...")
    clean_build_artifacts()

    print("Building .exe with PyInstaller...")
    build_exe()

    exe_path = DIST_DIR / "دمج_بيانات_الحيازات_الزراعية.exe"
    if exe_path.exists():
        print(f"Build complete: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / 1_000_000:.1f} MB")
    else:
        print("Build failed — .exe not found")
