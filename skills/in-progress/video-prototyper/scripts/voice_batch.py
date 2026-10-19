#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Run the full take pipeline for several voices: generate, check, regenerate, join, align.

Per voice: tts_generate.py (scene by scene) -> check_takes.py -> regenerate the scenes that
leaked a tag (plain) or lost their ending, up to --max-regens rounds -> join_scenes.py ->
transcribe the joined take for word times -> align_words.py -> a voices.json entry with
the take's integrated loudness (loudness_lufs, measured by join_scenes.py).
Join, transcription and alignment write under <take>/.pending and replace the previous
take only when alignment exits 0, so a failed rerun keeps the earlier audio and timing.
One voice failing prints "GEN FAIL <id>" and the batch moves on. Reruns resume, because
existing scene files are kept. A spend cap or request cap (generate.max_requests) reached in generation or regeneration stops the whole batch.
Pass --merge-manifest so each finished take lands in voices.json; without it the entries
are only printed. A cap stop (exit 3) keeps the voices.json entries of the voices that finished before it. A merge keeps the fields the run does not write (a design_prompt, a hand-written note, a dated model for a command voice); a note the run writes replaces the old one, and a kept note is printed so it can be checked; the run's own `endings unchecked: no transcriber` note is dropped when a later run checks the endings with the transcriber. regenerated_plain lists the scenes whose current files were sent plain, read from each scene's s<N>.json record; regenerated adds this run's ending-only regenerations to the earlier ones. A full example config: assets/voice-batch.example.json.

Config (JSON):
  {"scenes": "script/scenes.json", "script": "script/script.txt", "voices_dir": "voices",
   "manifest": "voices/voices.json",
   "stt_quick": "<transcriber> -m <model-file> -f {in} -np -nt",
   "stt_words": "<transcriber> -m <model-file> -f {in} -ml 1 -sow -ojf -np -of {out}",
   "words_format": "whisper-cpp", "aligner_label": "<transcriber, version, model>", "gap": 0.6,
   "generate": {"min_interval": 7, "max_requests": 60, "ledger": "media/ledger.jsonl",
                "est_usd_per_request": 0.01, "cap_usd_day": 1.0, "cap_usd_project": 5.0},
   "voices": [
     {"id": "scratch", "label": "Scratch voice", "kind": "local", "vendor": "local",
      "adapter": "command", "voice_id": "<local voice name>",
      "command": "say -v {voice} -o {out} -f {text_file}", "command_ext": "aiff"},
     {"id": "narrator", "label": "Narrator", "kind": "designed", "vendor": "<vendor>",
      "adapter": "gemini-interactions", "voice_id": "<voice id>", "model": "<model id>",
      "key_env": "<VARIABLE_NAME>", "design_prompt": "<one or two sentences, permanent traits only>"}]}
An openai-speech voice may add "instructions_file": "script/openai-instructions.txt", a path relative to the project. tts_generate.py sends that file as instructions, with the scene's style line after it.
The scratch voice's say command is macOS only; on Linux or Windows use "espeak-ng -v {voice} -w {out} -f {text_file}" with command_ext "wav".
The generate caps apply to every API voice, and to a command voice marked "paid": true
(a paid speech tool wrapped in the command adapter); tts_generate.py refuses a live paid
run without a ledger, an explicit estimate and a cap.
max_requests applies to each generation call, and each regeneration round is a new call, so one voice can make up to (1 + --max-regens) x max_requests attempts; the USD caps bound the whole batch through the ledger.
Working transcriber commands: references/example-local-tools.md.
Paths in the config are relative to the current folder (run it from <project>/).
For stt_words, {out} is a path base; the word JSON is read from {out}.json, or from
standard output when the template has no {out}.

Usage:
  python3 voice_batch.py --config voices/batch.json [--only-voices a,b] [--max-regens 2]
      [--merge-manifest] [--dry-run] [--no-stt]

--no-stt skips transcription and automated ending checks, aligns from scene durations,
and marks the manifest note "endings unchecked: no transcriber". Listen to every scene's
ending before using the take.

A dry run prints each API or paid voice's requests in full; the temporary request file tts_generate.py names is removed afterwards.

Dependencies: Python 3.9 or later, standard library only; the scripts beside this one;
ffmpeg and ffprobe; a speech-to-text command unless --no-stt.
Exit codes: 0 every voice finished (in a dry run: every dry run passed); 1 at least one
voice failed; 2 bad arguments (an --only-voices id that is not in the config, a selected
voice with no adapter, or, without --no-stt, stt_quick, stt_words or aligner_label still
holding a <placeholder>); 3 a spend
cap or request cap stopped the batch (in a dry run: the caps would refuse the combined
estimate of every selected paid voice, or a cap or max_requests would stop one voice's
own run).
"""
import argparse
import datetime
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

NO_STT_NOTE = "endings unchecked: no transcriber"

HERE = os.path.dirname(os.path.abspath(__file__))


def script(name):
    return [sys.executable, os.path.join(HERE, name)]


def run(cmd):
    print("  $ " + " ".join(shlex.quote(c) for c in cmd[1:3]) + " ...", flush=True)
    return subprocess.run(cmd).returncode


def gen_cmd(cfg, v, extra):
    g = cfg.get("generate", {})
    cmd = script("tts_generate.py") + ["--scenes", cfg["scenes"], "--voice-id", v["voice_id"],
                                       "--out-dir", os.path.join(cfg["voices_dir"], v["id"]), "--adapter", v["adapter"]]
    guarded = v["adapter"] != "command" or bool(v.get("paid"))
    if v["adapter"] == "command":
        cmd += ["--command", v["command"], "--command-ext", v.get("command_ext", "wav")]
        if v.get("paid"):
            cmd += ["--paid"]
    else:
        cmd += ["--model", v["model"], "--key-env", v["key_env"]]
        if v.get("endpoint"):
            cmd += ["--endpoint", v["endpoint"]]
        if v.get("instructions_file"):
            cmd += ["--instructions-file", v["instructions_file"]]
        elif v.get("instructions"):
            cmd += ["--instructions"]
    if cfg.get("script"):
        cmd += ["--script", cfg["script"]]
    if guarded:
        for key, flag in (("min_interval", "--min-interval"), ("max_requests", "--max-requests"), ("ledger", "--ledger"),
                          ("est_usd_per_request", "--est-usd-per-request"), ("cap_usd_request", "--cap-usd-request"),
                          ("cap_usd_day", "--cap-usd-day"), ("cap_usd_project", "--cap-usd-project")):
            if g.get(key) is not None:
                cmd += [flag, str(g[key])]
    return cmd + extra


def transcribe_words(cfg, wav, workdir):
    wav16 = os.path.join(workdir, "take-16k.wav")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", wav, "-ar", "16000", "-ac", "1", wav16], check=True)
    base = os.path.join(workdir, "words")
    argv = [p.format(**{"in": wav16, "out": base}) for p in split_cmd(cfg["stt_words"])]
    proc = subprocess.run(argv, capture_output=True, text=True, check=True)
    out = os.path.join(workdir, "words.json")
    if "{out}" in cfg["stt_words"]:
        if not os.path.exists(base + ".json"):
            raise RuntimeError("the transcriber wrote no {out}.json")
        os.replace(base + ".json", out)
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(proc.stdout)
    return out


def split_cmd(t):
    posix = os.name != "nt"
    parts = shlex.split(t, posix=posix)
    if posix:
        return parts
    cleaned = []
    for p in parts:
        if len(p) > 1 and p[0] == p[-1] and p[0] in ("'", '"'):
            p = p[1:-1]
        cleaned.append(p)
    return cleaned


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def transcriber_detail(err):
    """Stderr lines worth showing, and whether they name a missing model file."""
    text = getattr(err, "stderr", "") or ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    matched = [ln for ln in lines if re.search(r"error|not found|no such file|failed|cannot|unable", ln, re.I)]
    return (matched[:5] if matched else lines[-5:]), bool(re.search(r"model file", text, re.I))


def merge_into_manifest(path, entries):
    manifest = {"schema": 1, "default": "none", "voices": [{"id": "none", "label": "No voice", "kind": "none", "audio": None, "timing": None}]}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    by_id = {e["id"]: e for e in entries}
    merged = []
    for old in manifest["voices"]:
        new = by_id.pop(old["id"], None)
        if new is None:
            merged.append(old)
            continue
        entry = dict(old, **{k: v for k, v in new.items() if v not in (None, "")})
        stale_no_stt = old.get("note") == NO_STT_NOTE and new.get("note") == ""
        if stale_no_stt:
            entry["note"] = ""  # this run checked the endings with the transcriber
        entry["regenerated"] = sorted((set(old.get("regenerated") or []) | set(new.get("regenerated") or []))
                                      - set(new.get("regenerated_plain") or []))
        merged.append(entry)
        if stale_no_stt:
            print(f"{old['id']}: dropped the earlier note \"{NO_STT_NOTE}\"; this run checked the endings")
        elif old.get("note") and not new.get("note"):
            print(f"{old['id']}: kept the existing note; check it still applies: {old['note']}")
    manifest["voices"] = merged + list(by_id.values())
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"merged {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} into {path}; run sync_embed.py for use from disk")
    ids = {e["id"] for e in entries}
    return [e for e in manifest["voices"] if e["id"] in ids]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--only-voices")
    ap.add_argument("--max-regens", type=int, default=2)
    ap.add_argument("--merge-manifest", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-stt", action="store_true")
    args = ap.parse_args()
    with open(args.config, encoding="utf-8") as fh:
        cfg = json.load(fh)
    wanted = set(args.only_voices.split(",")) if args.only_voices else None
    if wanted:
        config_ids = [v["id"] for v in cfg["voices"]]
        unknown = sorted(i for i in wanted - set(config_ids) if i)
        if unknown:
            print(f"FAIL: --only-voices names {', '.join(unknown)}, not in {args.config}; add the entry first "
                  f"(copy an existing voice; a local voice needs command and command_ext). Config voices: {', '.join(config_ids)}")
            return 2
    selected = [v for v in cfg["voices"] if not wanted or v["id"] in wanted]
    no_adapter = [v["id"] for v in selected if not v.get("adapter")]
    if no_adapter:
        print(f"FAIL: voice {', '.join(no_adapter)} has no adapter; a take made by hand (the owner's recording or web-app audio) "
              f"follows SKILL.md stage 5, step 4c. Keep it out of {args.config}.")
        return 2
    if not args.no_stt:
        unfilled = [k for k in ("stt_quick", "stt_words", "aligner_label") if re.search(r"<[^<>]+>", str(cfg.get(k) or ""))]
        if unfilled:
            print(f"FAIL: {', '.join(unfilled)} in {args.config} still hold{'s' if len(unfilled) == 1 else ''} a placeholder; fill in the transcriber commands "
                  "and aligner_label (references/example-local-tools.md), or pass --no-stt")
            return 2
    entries, failed = [], []
    g = cfg.get("generate") or {}
    planned = 0.0
    paid = []

    for v in cfg["voices"]:
        if wanted and v["id"] not in wanted:
            continue
        take_dir = os.path.join(cfg["voices_dir"], v["id"])
        print(f"== {v['id']}")
        if v["adapter"] != "command" or bool(v.get("paid")):
            bad = None
            for key in ("min_interval", "max_requests", "est_usd_per_request",
                        "cap_usd_request", "cap_usd_day", "cap_usd_project"):
                val = g.get(key)
                if val is None:
                    continue
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val < 0:
                    bad = (key, val)
                    break
            if bad is not None:
                print(f"GEN FAIL {v['id']}: generate.{bad[0]} in {args.config} is not a number (still a placeholder?): {bad[1]}")
                failed.append(v["id"])
                continue
        if args.dry_run and (v["adapter"] != "command" or v.get("paid")):
            fd, request_path = tempfile.mkstemp(suffix=".jsonl")
            os.close(fd)
            try:
                rc = run(gen_cmd(cfg, v, ["--dry-run", "--dry-run-out", request_path]))
                if rc == 0:
                    with open(request_path, encoding="utf-8") as fh:
                        count = sum(1 for line in fh if line.strip())
                    paid.append(v["id"])
                    if g.get("est_usd_per_request") is not None:
                        planned += count * float(g["est_usd_per_request"])
            finally:
                os.remove(request_path)
            # tts_generate.py can print "wrote N request(s) to <path>" before exit 0, 1, 2 or 3; the file is gone now
            print(f"NOTE: {request_path} was a temporary copy and has been removed; the requests the dry run reached are printed above "
                  "(tts_generate.py --dry-run --dry-run-out <file> keeps one voice's requests)")
        else:
            rc = run(gen_cmd(cfg, v, ["--dry-run"] if args.dry_run else []))
        if rc == 3:
            print(f"STOP: a spend cap or request cap {'would stop' if args.dry_run else 'stopped'} generation at {v['id']}")
            return 3
        if rc != 0:
            print(f"GEN FAIL {v['id']}: generation" + (f" dry run (exit {rc})" if args.dry_run else ""))
            failed.append(v["id"])
            continue
        if args.dry_run:
            continue
        regenerated, plain_scenes = set(), set()
        clean = args.no_stt
        check_failed = False
        same_audio = set()
        if args.no_stt:
            print("no transcriber: listen to every scene's ending before using this take")
        for round_n in range(0 if args.no_stt else args.max_regens + 1):
            report_path = os.path.join(take_dir, "check.json")
            check_cmd = script("check_takes.py") + ["--scenes", cfg["scenes"], "--take-dir", take_dir,
                                                     "--stt-cmd", cfg["stt_quick"], "--report", report_path]
            if round_n < args.max_regens:
                check_cmd += ["--move-leaks"]
            rc = run(check_cmd)
            if rc == 0:
                clean = True
                break
            if rc == 1:
                check_failed = True
                break
            if rc != 2 or round_n == args.max_regens:
                break
            with open(report_path, encoding="utf-8") as fh:
                report = json.load(fh)
            by_scene = {s["scene"]: s for s in report.get("scenes", [])}
            leaks = [s["scene"] for s in report["scenes"] if s.get("inserted_tag_words")]
            other = [s["scene"] for s in report["scenes"]
                     if s.get("needs_regen") and not s.get("inserted_tag_words") and s["scene"] not in same_audio]
            prior_hash = {}
            for n in other:
                src = os.path.join(take_dir, f"s{n}.wav")
                if os.path.exists(src):
                    prior_hash[n] = file_sha256(src)
                    os.replace(src, os.path.join(take_dir, f"s{n}-rejected-{round_n + 1}.wav"))
            redo = sorted(set(leaks + other))
            plain_scenes.update(leaks)
            regenerated.update(other)
            if not redo:
                break
            extra = ["--only", ",".join(map(str, redo))]
            plain_redo = sorted(plain_scenes & set(redo))
            if plain_redo:
                extra += ["--plain-scenes", ",".join(map(str, plain_redo))]
            rc = run(gen_cmd(cfg, v, extra))
            if rc == 3:
                print(f"STOP: a spend cap or request cap stopped regeneration at {v['id']}")
                return 3
            for n in list(other):
                src = os.path.join(take_dir, f"s{n}.wav")
                if n in prior_hash and os.path.exists(src) and file_sha256(src) == prior_hash[n]:
                    same_audio.add(n)
                    rate = by_scene.get(n, {}).get("match_rate")
                    print(
                        f"SAME AUDIO: {v['id']} scene {n} came back byte-identical; this voice gives the same audio "
                        f"for the same text, so regenerating cannot change it. Listen to s{n}-rejected-final.wav: "
                        f"if it reads the script correctly, the transcriber misheard it (match rate {rate}, floor 0.85); "
                        "otherwise pick another voice."
                    )
            if not leaks and other and set(other) <= same_audio:
                # Regeneration exits 0. The fail path below moves the scene only when the check returned 2.
                rc = 2
                break
        if check_failed:
            print(f"GEN FAIL {v['id']}: the take check could not run (check_takes.py exit 1): add -ng (--no-gpu) to both transcriber commands in batch.json (stt_quick and stt_words; references/example-local-tools.md, whisper.cpp example); it runs on the CPU and keeps word times. Use --no-stt only when no transcriber can run, and listen to every ending")
            failed.append(v["id"])
            continue
        if not clean:
            report_path = os.path.join(take_dir, "check.json")
            if rc == 2 and os.path.exists(report_path):
                with open(report_path, encoding="utf-8") as fh:
                    report = json.load(fh)
                for s in report.get("scenes", []):
                    if s.get("needs_regen") or s.get("inserted_tag_words"):
                        src = os.path.join(take_dir, f"s{s['scene']}.wav")
                        if os.path.exists(src):
                            os.replace(src, os.path.join(take_dir, f"s{s['scene']}-rejected-final.wav"))
            price = ""
            if v.get("adapter") != "command" or v.get("paid"):
                price = "; a dry run now prices their regeneration"
            print(f"GEN FAIL {v['id']}: scenes still need attention after {args.max_regens} regeneration round(s); see {take_dir}/check.json; the failing scenes were moved to s<N>-rejected-final.wav for the owner to listen to{price}")
            failed.append(v["id"])
            continue
        pending = os.path.join(take_dir, ".pending")
        if os.path.isdir(pending):
            shutil.rmtree(pending)
        os.makedirs(pending, exist_ok=True)
        final_wav = os.path.join(take_dir, f"{v['id']}.wav")
        pending_wav = os.path.join(pending, f"{v['id']}.wav")
        pending_scenes = pending_wav[:-4] + "-scenes.json"
        final_timing = os.path.join(take_dir, f"{v['id']}-timing.json")
        pending_timing = os.path.join(pending, f"{v['id']}-timing.json")

        def abandon(why, err=None):
            shutil.rmtree(pending, ignore_errors=True)
            print(f"GEN FAIL {v['id']}: {why}; the previous take was kept")
            if err is not None:
                picked, mentions_model = transcriber_detail(err)
                for ln in picked:
                    print(ln)
                code = getattr(err, "returncode", None)
                if code is None:
                    code = getattr(err, "code", None)
                stderr = getattr(err, "stderr", "") or ""
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", "replace")
                aborted = code in (-6, 134) or "GGML_ASSERT" in stderr
                if aborted or mentions_model:
                    print("add -ng (--no-gpu) to both transcriber commands in batch.json (stt_quick and stt_words; references/example-local-tools.md, whisper.cpp example); it runs on the CPU and keeps word times.")
                if mentions_model:
                    print("check the model path (`probe_tools.py --stt-model <path>`), or rerun with `--no-stt` and listen to every ending")
                elif aborted:
                    print("Use --no-stt only when no transcriber can run.")
            failed.append(v["id"])

        join = script("join_scenes.py") + ["--take-dir", take_dir, "--out", pending_wav, "--gap", str(cfg.get("gap", 0.6)),
                                           "--scenes", cfg["scenes"]]
        if run(join) != 0:
            abandon("join")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            try:
                words = None if args.no_stt else transcribe_words(cfg, pending_wav, tmp)
            except (subprocess.CalledProcessError, RuntimeError, OSError) as err:
                abandon(f"transcription ({type(err).__name__})", err)
                continue
            align = script("align_words.py") + ["--script", cfg["script"], "--voice", v["id"], "--audio", pending_wav,
                                                "--out", pending_timing, "--scene-offsets", pending_scenes]
            if args.no_stt:
                align += ["--no-stt"]
            else:
                align += ["--words", words, "--format", cfg.get("words_format", "whisper-cpp"),
                          "--aligner-label", cfg.get("aligner_label", "a speech-to-text tool")]
            rc = run(align)
        if rc != 0:
            abandon(f"alignment (exit {rc}); listen to the take's ending")
            continue
        os.replace(pending_wav, final_wav)
        os.replace(pending_scenes, final_wav[:-4] + "-scenes.json")
        os.replace(pending_timing, final_timing)
        shutil.rmtree(pending, ignore_errors=True)
        wav = final_wav
        timing = final_timing
        manifest_dir = os.path.dirname(os.path.abspath(cfg["manifest"]))
        loudness = None
        try:
            with open(wav[:-4] + "-scenes.json", encoding="utf-8") as fh:
                loudness = json.load(fh).get("loudness_lufs")
        except (OSError, ValueError):
            pass
        plain_on_disk = set()
        for name in os.listdir(take_dir):
            m = re.fullmatch(r"s(\d+)\.json", name)
            if m:
                try:
                    with open(os.path.join(take_dir, name), encoding="utf-8") as fh:
                        if json.load(fh).get("plain"):
                            plain_on_disk.add(int(m.group(1)))
                except (OSError, ValueError):
                    pass
        plain_scenes = plain_on_disk
        entry = {"id": v["id"], "label": v.get("label", v["id"]), "kind": v.get("kind", "prebuilt"), "vendor": v.get("vendor"),
                 "model": v.get("model"), "voice": v["voice_id"],
                 "audio": os.path.relpath(os.path.abspath(wav), manifest_dir).replace(os.sep, "/"),
                 "timing": os.path.relpath(os.path.abspath(timing), manifest_dir).replace(os.sep, "/"),
                 "created": datetime.date.today().isoformat(), "regenerated_plain": sorted(plain_scenes),
                 "regenerated": sorted(regenerated - plain_scenes), "loudness_lufs": loudness,
                 "note": NO_STT_NOTE if args.no_stt else ""}
        if v.get("design_prompt"):
            entry["design_prompt"] = v["design_prompt"]
        entries.append(entry)
        if args.merge_manifest:
            entry = merge_into_manifest(cfg["manifest"], [entry])[0]  # print what voices.json now holds
        print(json.dumps(entry))

    if args.dry_run and paid:
        if g.get("est_usd_per_request") is None:
            print("batch estimate: unknown; a live run needs generate.est_usd_per_request")
        else:
            sys.path.insert(0, HERE)
            sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
            import spend_ledger  # noqa: E402
            try:
                rows = spend_ledger.read(g["ledger"]) if g.get("ledger") else []
            except spend_ledger.LedgerError as err:
                print(f"FAIL: {err}")
                return 2
            reasons = spend_ledger.check_caps(round(planned, 6), rows,
                                              spend_ledger.utc_now().date().isoformat(), None,
                                              g.get("cap_usd_day"), g.get("cap_usd_project"))
            print(f"batch estimate: {len(paid)} paid voice(s), ${planned:.4f} before retries and regenerations")
            if reasons:
                print("REFUSED (dry run): the batch together: " + "; ".join(reasons)
                      + "; raise a cap only with the owner's explicit yes")
                return 3
    if failed:
        print("failed voices: " + ", ".join(failed))
        return 1
    print("batch done" + (" (dry run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
