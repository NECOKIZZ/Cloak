"""Builds the teaser: python3 build.py  →  build/cloak-teaser.mp4

  --frames 0:240   render only part of the picture (fast checks)
  --audio-only     re-mix the sound and lay it under the last rendered picture
"""
import argparse
import os
import subprocess
from multiprocessing import get_context

import audio
import edit

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
WORKERS = 4


def render_range(job):
    a, b, path = job
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{edit.W}x{edit.H}", "-r", str(edit.FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", path],
                           stdin=subprocess.PIPE)
    for f in range(a, b):
        enc.stdin.write(edit.render(f).tobytes())
    enc.stdin.close()
    enc.wait()
    return path


def picture(a, b):
    edit.load_clips()      # loaded once; the forked workers share it
    edit.place_events()
    os.makedirs(os.path.join(BUILD, "parts"), exist_ok=True)
    step = (b - a + WORKERS - 1) // WORKERS
    jobs = [(i, min(i + step, b), os.path.join(BUILD, "parts", f"part{k}.mp4")) for k, i in enumerate(range(a, b, step))]
    with get_context("fork").Pool(WORKERS) as pool:
        parts = pool.map(render_range, jobs)
    lst = os.path.join(BUILD, "parts", "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
    out = os.path.join(BUILD, "picture.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=f"0:{edit.N_FRAMES}")
    ap.add_argument("--audio-only", action="store_true")
    args = ap.parse_args()
    os.makedirs(BUILD, exist_ok=True)
    wav = os.path.join(BUILD, "mix.wav")
    used = audio.mix(wav)
    print("sound effects:", ", ".join(f"{k}{'' if v else ' (stand-in)'}" for k, v in used.items()))
    a, b = map(int, args.frames.split(":"))
    pic = os.path.join(BUILD, "picture.mp4") if args.audio_only else picture(a, b)
    final = os.path.join(BUILD, "cloak-teaser.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pic, "-ss", str(a / edit.FPS), "-i", wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", final],
                   check=True)
    # a lighter copy for sharing (grain is expensive to encode)
    share = os.path.join(BUILD, "cloak-teaser-share.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", final, "-c:v", "libx264", "-preset", "slow", "-b:v", "9M",
                    "-maxrate", "12M", "-bufsize", "18M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                    share], check=True)
    print("→", os.path.relpath(final, HERE), "and", os.path.relpath(share, HERE))


if __name__ == "__main__":
    main()
