#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Embed a build's cues and manifests into its index.html, for opening from disk.

A page opened from file:// cannot read its neighbours, so the build keeps copies in
<script type="application/json" id="cue-data|voice-data|music-data"> blocks. Served
over HTTP, the page reads the live files instead. Run this after any change to
cues.json, voices.json, tracks.json or a take.

What it embeds:
  cue-data    cues.json as is.
  voice-data  voices.json with every take checked: available only when its audio and
              timing exist, the timing has the right scene and sentence counts, and its
              source_words_sha256 matches cues.json when both record one.
              Available takes carry their timing inline (timing_data) and a path
              relative to the build (audio_from_page).
  music-data  tracks.json with tracks whose file exists, each with file_from_page.
              Rights starting with "pending", or rights not recorded (null, empty or
              missing), disable the track and reset its default to Off.

When a music manifest exists, checks available beds against the longest video across
No voice and all available takes, measured as the page plays them (after the same
repairs, such as silent slots for a kept take's missing last lines); a short bed fails
after writing the embed (or --check).

Usage:
  python3 sync_embed.py --build <video-id>/<build-id> [--check]

The manifest paths come from cues.json (voices.manifest, music.manifest), relative to the
build folder. --check compares the embedded blocks against cues.json and the manifests
and writes nothing.

Dependencies: Python 3.9 or later, standard library only.
Exit codes: 0 written (or current under --check); 1 a required block id is missing, cues.json is invalid, or --check found stale embedded blocks, or a bed is shorter than the longest video.
"""
import argparse
import json
import math
import os
import re
import sys

BLOCK = '<script type="application/json" id="{id}">'


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def rel_from_build(build, path):
    return os.path.relpath(path, build).replace(os.sep, "/")


def embed(html, block_id, data):
    opener = BLOCK.format(id=block_id)
    start = html.find(opener)
    if start < 0:
        raise SystemExit(f"FAIL: index.html has no {opener}...</script> block")
    body_start = start + len(opener)
    end = html.find("</script>", body_start)
    if end < 0:
        raise SystemExit(f"FAIL: block {block_id} is not closed")
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return html[:body_start] + text + html[end:]


def repaired_sentences(cue_sentences, take_sentences):
    """Keep in step with buildTiming in assets/build-template/index.html."""
    if len(cue_sentences) != len(take_sentences):
        raise ValueError("timing does not match the cues; re-run alignment")
    flat = [dict(c, start=float(t.get("start", 0)), end=float(t.get("end", 0)),
                 text=t.get("text") or c["text"]) for c, t in zip(cue_sentences, take_sentences)]
    for i, sentence in enumerate(flat):
        if i and sentence["start"] < flat[i - 1]["start"]:
            sentence["start"] = flat[i - 1]["start"]
            print(f"WARNING: {sentence['id']}: start clamped to the previous sentence")
        if sentence["end"] < sentence["start"]:
            sentence["end"] = sentence["start"]
            print(f"WARNING: {sentence['id']}: end clamped to its start")
    for j, sentence in enumerate(flat):
        if sentence["end"] - sentence["start"] >= 0.05:
            continue
        prev_end = flat[j - 1]["end"] if j else 0
        slot = max(0.6, len(sentence["text"].split()) / 2.4)
        if all(s["end"] - s["start"] < 0.05 for s in flat[j:]):
            sentence["start"] = prev_end + 0.3
            sentence["end"] = sentence["start"] + slot
            sentence["silent"] = True
            print(f"WARNING: {sentence['id']}: last line not in the audio; shown in a silent slot")
        else:
            sentence["end"] = max(sentence["start"] + 0.05,
                                  min(flat[j + 1]["start"], sentence["start"] + slot))
            print(f"WARNING: {sentence['id']}: zero-length sentence widened")
    return flat


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", required=True, help="build folder holding index.html and cues.json")
    ap.add_argument("--check", action="store_true", help="check whether embedded blocks are current; write nothing")
    args = ap.parse_args()

    build = os.path.abspath(args.build)
    page = os.path.join(build, "index.html")
    cues = load(os.path.join(build, "cues.json"))
    scenes = cues.get("scenes") or []
    if not scenes:
        print("FAIL: cues.json has no scenes")
        return 1
    cue_count = sum(len(s.get("cues", [])) for s in scenes)

    voice_data = {"schema": 1, "default": "none", "voices": [{"id": "none", "label": "No voice", "kind": "none", "available": True}]}
    vrel = (cues.get("voices") or {}).get("manifest")
    if not vrel:
        print("no voices manifest in cues.json; embedding No voice only")
    elif os.path.exists(os.path.join(build, vrel)):
        vpath = os.path.normpath(os.path.join(build, vrel))
        vdir = os.path.dirname(vpath)
        manifest = load(vpath)
        voice_data = {"schema": manifest.get("schema", 1), "default": manifest.get("default", "none"), "voices": []}
        for v in manifest.get("voices", []):
            entry = dict(v)
            if v.get("id") == "none":
                entry["available"] = True
                voice_data["voices"].append(entry)
                continue
            audio_listed = isinstance(v.get("audio"), str) and v.get("audio").strip()
            timing_listed = isinstance(v.get("timing"), str) and v.get("timing").strip()
            if not audio_listed or not timing_listed:
                reason = "no audio file listed" if not audio_listed else "no timing file listed"
                entry["available"] = False
                entry["reason"] = reason
                voice_data["voices"].append(entry)
                print(f"voice {v['id']}: not ready: {reason}")
                continue
            audio = os.path.join(vdir, v["audio"])
            timing = os.path.join(vdir, v["timing"])
            reason = ""
            td = None
            if not audio or not os.path.exists(audio):
                reason = "audio file missing"
            elif not os.path.exists(timing):
                reason = "timing file missing"
            else:
                td = load(timing)
                if not td.get("sentences"):
                    reason = "timing has no sentences"
                elif len(td.get("scenes", [])) != len(scenes):
                    reason = f"timing has {len(td.get('scenes', []))} scenes; cues have {len(scenes)}"
                elif len(td["sentences"]) != cue_count:
                    reason = f"timing has {len(td['sentences'])} sentences; cues have {cue_count}; re-run alignment"
                elif (cues.get("source_words_sha256") and td.get("source_words_sha256")
                      and cues.get("source_words_sha256") != td.get("source_words_sha256")):
                    reason = "stale: the script changed after this take was aligned"
            entry["available"] = not reason
            if reason:
                entry["reason"] = reason
            else:
                entry["timing_data"] = td
                entry["audio_from_page"] = rel_from_build(build, audio)
            voice_data["voices"].append(entry)
            print(f"voice {v['id']}: {'available' if not reason else 'not ready: ' + reason}")
    else:
        print(f"WARN: voices manifest {vrel} not found; embedding No voice only (the timing audit reports this as incomplete)")

    short_bed = False
    music_data = {"schema": 1, "default": "off", "tracks": []}
    mrel = (cues.get("music") or {}).get("manifest")
    if not mrel:
        print("no music manifest in cues.json; embedding Off only")
    elif os.path.exists(os.path.join(build, mrel)):
        mpath = os.path.normpath(os.path.join(build, mrel))
        mdir = os.path.dirname(mpath)
        manifest = load(mpath)
        music_data = {k: v for k, v in manifest.items() if k != "tracks"}
        music_data["tracks"] = []
        longest, longest_voice = float(cues.get("duration", 0)), "none"
        pre = float((cues.get("title_card") or {}).get("duration_s", 3.5))
        tail = float(cues.get("tail_s", 6))
        cue_sentences = [c for scene in scenes for c in scene.get("cues", [])]
        for voice in voice_data["voices"]:
            td = voice.get("timing_data")
            if voice.get("available") and td and td.get("sentences"):
                # The page repairs collapsed sentences at load (a kept take with a missing ending
                # shows its last lines in silent slots), so measure the repaired timeline.
                sents = repaired_sentences(cue_sentences, td["sentences"])
                duration = pre + max(sents[-1]["end"] + tail, float(td.get("duration", 0)))
                if duration > longest:
                    longest, longest_voice = duration, voice["id"]
        print(f"longest video: {longest:g} s ({longest_voice})")
        for tr in manifest.get("tracks", []):
            f = os.path.join(mdir, tr.get("file", ""))
            rights = tr.get("rights")
            unrecorded = not (isinstance(rights, str) and rights.strip())
            pending = not unrecorded and rights.strip().lower().startswith("pending")
            if pending or unrecorded:
                reason = "rights pending" if pending else "rights not recorded"
                entry = dict(tr, available=False, reason=reason)
                entry.pop("file_from_page", None)
                music_data["tracks"].append(entry)
                if pending:
                    print(f"track {tr['id']}: not ready: rights pending ({rights})")
                else:
                    print(f"track {tr['id']}: not ready: rights not recorded; record the owner's answer in tracks.json")
                if manifest.get("default") == tr.get("id"):
                    music_data["default"] = "off"
                    print(f"default {tr['id']} has {reason}; the embedded default is off")
            elif tr.get("file") and os.path.exists(f):
                entry = dict(tr)
                entry["file_from_page"] = rel_from_build(build, f)
                music_data["tracks"].append(entry)
                print(f"track {tr['id']}: available")
                seconds = tr.get("seconds")
                if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) and math.isfinite(seconds):
                    if seconds < longest:
                        print(f"FAIL: track {tr['id']} is {seconds:g} s, shorter than the longest video ({longest:g} s, voice {longest_voice}); rebuild it from its source with make_bed.py --min-seconds {math.ceil(longest + 10)}")
                        short_bed = True
                else:
                    print(f"NOTE: track {tr['id']} has no seconds; its length was not checked")
            else:
                music_data["tracks"].append(dict(tr, available=False, reason="file missing"))
                print(f"track {tr.get('id')}: not ready: file missing")
    else:
        print("music manifest not found; embedding no tracks")

    with open(page, encoding="utf-8") as fh:
        raw_html = fh.read()
    html = raw_html
    for block_id, data in (("cue-data", cues), ("voice-data", voice_data), ("music-data", music_data)):
        html = embed(html, block_id, data)
    if args.check:
        if html != raw_html:
            print("STALE: the embedded blocks differ from cues.json or the manifests; run without --check")
            return 1
        print("embedded blocks are current")
        return 1 if short_bed else 0
    with open(page, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"embedded cue-data, voice-data and music-data into {page}")
    return 1 if short_bed else 0


if __name__ == "__main__":
    sys.exit(main())
