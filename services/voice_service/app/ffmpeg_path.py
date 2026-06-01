import os
import shutil
import subprocess


def ensure_ffmpeg_on_path() -> None:
    """Ensure ffmpeg and ffprobe are available on the current PATH."""
    for cmd in ["ffmpeg", "ffprobe"]:
        if shutil.which(cmd):
            continue

        # If ffmpeg is installed under a known user path, add it to PATH.
        local_ffmpeg_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Microsoft",
            "WinGet",
            "Packages",
            "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
            "ffmpeg-8.1.1-full_build",
            "bin",
        )
        if os.path.isdir(local_ffmpeg_dir):
            os.environ["PATH"] = f"{local_ffmpeg_dir};{os.environ.get('PATH', '')}"

        if shutil.which(cmd):
            continue

        raise FileNotFoundError(
            f"Could not find {cmd} on PATH. Install FFmpeg and ensure it is available in the environment."
        )

    # Validate both commands are executable
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        subprocess.run(["ffprobe", "-version"], check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"FFmpeg check failed: {exc}") from exc
