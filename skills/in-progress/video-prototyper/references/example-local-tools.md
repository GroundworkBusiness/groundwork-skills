# Worked examples: local tools

Commands for the local tools the scripts call. Each block is dated; flags change between versions, so check `--help` on your install.

On Windows, put paths with spaces in double quotes; forward slashes also work. Inside a command template, single or double quotes around a path both work.

## Contents

- [whisper.cpp transcription](#worked-example-whispercpp-transcription)
- [ffmpeg and ffprobe](#worked-example-ffmpeg-and-ffprobe)
- [A range request against the server](#worked-example-curl-range-request)
- [Headless Chrome frame capture](#worked-example-headless-chrome-frame-capture)
- [HTTPS from a python.org Python on macOS](#worked-example-python-https-on-macos)

## Worked example: whisper.cpp transcription

Checked 2026-10-15; re-check the tool's current docs before relying on it.

Install (the owner's yes; checked 2026-10-16): on macOS, `brew install whisper.cpp` (`brew install whisper-cpp` also works); elsewhere, build it as https://github.com/ggml-org/whisper.cpp describes. The model in these commands is `ggml-base.en.bin`. Homebrew installs the binary only. Download the model directly from https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin (147,964,211 bytes, about 148 MB; checked 2026-10-16) into a folder of your choice and use that path as `<model-dir>/ggml-base.en.bin`. With a clone of the repository, `sh ./models/download-ggml-model.sh base.en` fetches the same file (on Windows, run `download-ggml-model.cmd base.en` from the repository's `models` folder). Name that file, its source and its size when asking the owner.

```sh
# 16 kHz mono input
ffmpeg -i take.wav -ar 16000 -ac 1 take-16k.wav

# Word timestamps: one word per segment (-ml 1), split on words (-sow), full JSON (-ojf), no progress (-np)
whisper-cli -m <model-dir>/ggml-base.en.bin -f take-16k.wav -ml 1 -sow -ojf -np -of take-words
# writes take-words.json for: align_words.py --format whisper-cpp

# A quick transcript for tag-leak and ending checks
whisper-cli -m <model-dir>/ggml-base.en.bin -f scene-16k.wav -np -nt
```

As templates for the scripts:

```sh
--stt-cmd "whisper-cli -m <model-dir>/ggml-base.en.bin -f {in} -np -nt"                      # check_takes.py, make_bed.py
"stt_words": "whisper-cli -m <model-dir>/ggml-base.en.bin -f {in} -ml 1 -sow -ojf -np -of {out}"  # voice_batch.py
```

Word times can be contiguous (no gaps between words), so pauses get absorbed into neighbouring words, and the first segment can be empty, covering leading silence. Clean takes usually match nearly every script word.

Inside some agent sandboxes, whisper-cli can abort while loading the model (`GGML_ASSERT(buffer) failed`, exit code 134) and write no `{out}.json`. Add `-ng` (`--no-gpu`) to both commands and both templates there; it then runs on the CPU. Compare its word times with a run outside the sandbox before relying on them.

## Worked example: ffmpeg and ffprobe

Checked 2026-10-15; re-check the tool's current docs before relying on it.

Install (the owner's yes; checked 2026-10-16): on macOS, `brew install ffmpeg`; elsewhere, use a build from https://ffmpeg.org/download.html.

```sh
# Duration
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 bed.mp3

# Integrated loudness and true peak (read the Summary block)
ffmpeg -hide_banner -nostats -i src.wav -filter_complex ebur128=peak=true -f null - 2>&1 | grep -A14 'Summary:'

# Loudness of the last 8 s (does the track fade out?)
ffmpeg -hide_banner -nostats -sseof -8 -i src.wav -filter_complex ebur128 -f null - 2>&1 | grep -A6 'Summary:'

# Two plays joined by a 6 s equal-power crossfade, then a static gain (<gain> = -30 minus the joined file's integrated loudness; make_bed.py computes it), metadata and cover art dropped
ffmpeg -i src.wav -i src.wav -filter_complex "[0:a][1:a]acrossfade=d=6:c1=qsin:c2=qsin[j];[j]volume=<gain>dB[out]" \
  -map "[out]" -map_metadata -1 -vn -c:a libmp3lame -b:a 192k bed.mp3

# Where are the pauses? (for tighter sync than contiguous word times allow)
ffmpeg -hide_banner -i take.wav -af silencedetect=noise=-35dB:d=0.25 -f null - 2>&1 | grep silence_

# Strip a clip's audio track
ffmpeg -i clip.mp4 -c:v copy -an clip-silent.mp4

# A placeholder bed for offline tests: a soft chord with a fade at each end
ffmpeg -f lavfi -i "sine=f=220:d=40" -f lavfi -i "sine=f=277:d=40" -f lavfi -i "sine=f=330:d=40" \
  -filter_complex "[0][1][2]amix=inputs=3,volume=0.6,afade=t=in:d=1,afade=t=out:st=34:d=6,aformat=channel_layouts=stereo" placeholder.wav
```

Level check: a bed at -30 LUFS played at half gain (-6 dB) sits about 14 dB under a take at -22 LUFS; measure each take rather than assuming its level.

## Worked example: curl range request

Checked 2026-10-15; re-check the tool's current docs before relying on it.

```sh
curl -s -o /dev/null -w '%{http_code} %header{content-range}\n' -H 'Range: bytes=0-99' \
  http://127.0.0.1:8770/music/bright-acoustic-bed.mp3
# 206 bytes 0-99/<size> means the server supports seeking; 200 means it ignores ranges
```

Python's built-in `http.server` answers 200 (ranges ignored); `serve_range.py` answers 206. `python3 <skill>/scripts/serve_range.py --self-test` checks every case without a browser.

## Worked example: headless Chrome frame capture

Checked 2026-10-15; re-check the tool's current docs before relying on it.

```sh
mkdir -p <video-id>/<build-id>/frames/<voice>
"<chrome binary>" --headless=new --hide-scrollbars --window-size=1920,1080 \
  --screenshot=<video-id>/<build-id>/frames/<voice>/light-t009.50.png \
  "http://127.0.0.1:8770/<video-id>/<build-id>/index.html?voice=<voice>&music=off&render=1&mode=light&t=9.5"
```

For a look, put `looks/<id>/` in place of `<video-id>/<build-id>/` in all three places and `none` in place of `<voice>`.

On macOS the binary is inside the app bundle (`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`); on Linux it is usually `google-chrome` or `chromium`. As a template for `frame_review.py --capture-cmd`, put the binary first and use `{png}` and `{url}`. The script splits the template like a shell, so a path with spaces goes in single quotes inside the double-quoted template. This works the same on Windows, in cmd.exe, PowerShell and Git Bash.

```sh
python3 <skill>/scripts/frame_review.py --build <video-id>/<build-id> \
  --base-url http://127.0.0.1:8770/<video-id>/<build-id>/index.html \
  --capture-cmd "'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' --headless=new --hide-scrollbars --window-size=1920,1080 --screenshot={png} {url}"
```

One process per frame is slow but needs no packages; a browser automation library is faster for long exports (see [export.md](export.md)).

Some agent sandboxes cannot launch Chrome (it can exit with code 134 before opening); the host then captures the frames.

`--window-size=375,812` with `--headless=new` can lay the page out wider than 375 px, so a narrow screenshot can show false clipping; for a narrow check, capture the 375 px iframe page in [look-prototypes.md](look-prototypes.md#the-compare-page) instead.

## Worked example: Python HTTPS on macOS

Checked 2026-10-15; re-check the tool's current docs before relying on it.

A Python installed from python.org on macOS can fail HTTPS calls with certificate errors until it is pointed at the system bundle:

```sh
SSL_CERT_FILE=/etc/ssl/cert.pem python3 <skill>/scripts/tts_generate.py ...
```

Running the bundled "Install Certificates" command once is the alternative.
