# Spend and credentials

How keys reach the tools without the agent ever handling them, and how paid generation stays inside the owner's budget. The ledger is [spend_ledger.py](../scripts/spend_ledger.py); the guarded call is [api_media.py](../scripts/api_media.py).

## Contents

- [Keys](#keys)
- [The spend guard](#the-spend-guard)
- [The ledger](#the-ledger)
- [Billing preflight](#billing-preflight)
- [Options to show the owner early](#options-to-show-the-owner-early)

## Keys

The owner places every key. The agent never types, prints, copies, logs or commits one.

The owner runs these in their own terminal; a sandboxed agent usually cannot write outside the project.

An owner-placed key file:

```sh
mkdir -p ~/.config/<app>
touch ~/.config/<app>/<tool>.env && chmod 600 ~/.config/<app>/<tool>.env
# open it in a text editor for the owner; the owner pastes VARIABLE_NAME=<key> and saves
grep -c '^VARIABLE_NAME=' ~/.config/<app>/<tool>.env   # prints 1; never cat the file
```

On Windows (PowerShell):

```powershell
$f = "$HOME/.config/<app>/<tool>.env"
New-Item -ItemType Directory -Force -Path (Split-Path $f) | Out-Null
if (-not (Test-Path $f)) { New-Item -ItemType File -Path $f | Out-Null }
icacls $f /inheritance:r /grant:r "${env:USERNAME}:M"   # only your account; check the switch names with icacls /? first
# open it in a text editor for the owner; the owner pastes VARIABLE_NAME=<key> and saves
(Select-String -Path $f -Pattern '^VARIABLE_NAME=').Count   # prints 1; never print the file
```

Load it in the same command as the run, because many agent tools start a fresh shell for each command: `set -a; . <file>; set +a; python3 <skill>/scripts/tts_generate.py ... --key-env VARIABLE_NAME`. In PowerShell: `Get-Content <file> | ForEach-Object { $n,$v = $_ -split '=',2; Set-Item "env:$n" $v }; python <skill>/scripts/tts_generate.py ...`. Pass only the variable's name to the scripts (`--key-env VARIABLE_NAME`). The scripts send the key in a request header, never in a URL, never to a different origin after a redirect, and never print request headers. On an HTTP error they print the status and reason plus the error's status and message from the response body, cut to 300 characters, with any copy of the key replaced by `<redacted>` (`tts_generate.py` also writes that line to its `generate.log`); `api_media.py` also saves the redacted body as `<out-dir>/<name>-error.json`.

For a service-account key file, the owner downloads it and moves it into place; the agent runs only `chmod 600` and `ls -l` on it. Some organisations block key creation by policy, and the vendor may warn that such keys are a risk; prefer the simplest credential that works.

[probe_tools.py](../scripts/probe_tools.py) `--key-env NAME` reports whether a variable is set, never its value.

## The spend guard

Every paid call goes through the same rules:

- **Dry run first.** `--dry-run` validates limits, prints the request and the estimated list cost, reads no key, and writes no output or ledger line.
- **The owner's yes per batch,** with a cap. Approval for one batch does not carry to the next.
- **Per-request caps** (for example at most 8 s and 720p per clip, one track per music request). Refuse NaN and infinity.
- **Daily and project caps** sized to the budget the owner states. A cap that would spend a month's credit in two weeks is too loose.
- **Reserve before sending.** The estimate is written to the ledger under a file lock, with a second cap check, before the request goes out.
- **Retries.** `tts_generate.py` retries a speech request only when it returns 429, 500 or 503, with growing waits and a new reservation for each attempt. No other paid call or failure is retried automatically, because a retried generation can bill twice. A request that never connected is marked not_sent and does not count toward a cap; every other outcome keeps its reservation, because it may have billed.
- **Raise caps only with the owner's explicit yes.** Never delete ledger lines to get under a cap.

## The ledger

`media/ledger.jsonl`, append-only, shared by every tool. One reservation per paid request:

```json
{"at": "2026-01-31T12:00:00Z", "day": "2026-01-31", "id": "a1b2c3d4e5f6", "tool": "api_media", "kind": "video",
 "model": "<model id>", "units": 6, "unit": "second", "est_usd": 0.9, "status": "reserved", "note": "pool-loop"}
```

followed by an outcome line (`{"ref": "<id>", "status": "completed|failed|uncertain|pending|not_sent"}`). A malformed ledger is refused, never reset; fix the bad line by hand. `python3 <skill>/scripts/spend_ledger.py --summary media/ledger.jsonl` prints totals by day. For a paid item made outside the scripts (the agent tool's own generator, or a web app), `--reserve` records it before it is made, with the same cap check, and `--outcome` records the result; see [generated media](generated-media.md#without-an-api-a-built-in-generator-or-a-web-app).

Estimates are list prices before credits. The billing page is the real record.

## Billing preflight

Before the first paid call:

1. Which account and billing account hold any credits; which credit type; the monthly amount; the expiry.
2. Is the API on prepaid billing? If so, does a paid balance above zero have to exist before credits apply? Is auto-reload off?
3. Which products the credit covers. Coverage of media models is often undocumented; only a small test plus the next day's billing line proves it.
4. Is there a hard stop (a prepaid balance, a per-project spend cap)? Budgets that only send alerts stop nothing. Spend caps can lag and count list price before credits; set them slightly below the real limit.
5. Do other projects on the same billing account draw the same credits?
6. Take a baseline: record the credits and month-to-date spend (a screenshot of what loads) before the first paid call.
7. Make one smallest-possible paid test on the owner's yes.
8. Read billing the next day (usage data can lag from minutes to a day). Confirm the credits paid and nothing else was charged. Only then raise caps or batch.

Consumer-app credits and API credits are usually separate systems, and trial or welcome credits may exclude the API.

## Options to show the owner early

When a vendor gates credits behind a small prepaid balance, show both routes at once, each with its setup time and worst-case spend: a small deposit that unlocks the API within minutes, or a longer setup on another platform that avoids the deposit. Let the owner choose early; an hour of setup can cost more than the deposit. The owner pays and creates keys; the agent never does.
