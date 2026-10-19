export const meta = {
  name: 'video-prototyper',
  description: 'Fan out the agent-heavy stages of the video-prototyper skill (look round, builds, take checks, audits, review) and stop at each gate with a summary for the owner',
  whenToUse: 'In Claude Code, when a video-prototyper project has its PLAN.md and briefs written and the owner has said go for one stage. Run one stage per call: looks, build, takes, audit or review.',
  phases: [
    { title: 'Looks', detail: 'one builder per look, then static check and timing audit per look' },
    { title: 'Compare', detail: 'fill looks.json and the compare page' },
    { title: 'Build', detail: 'one builder per shortlisted look, then checks per build' },
    { title: 'Takes', detail: 'check, join and align each voice whose scene files exist' },
    { title: 'Manifest', detail: 'merge take entries into voices.json and sync the builds' },
    { title: 'Audit', detail: 'timing audit, static check and frame list per build' },
    { title: 'Review', detail: 'one read-only reviewer; one fixer only when it finds something' },
    { title: 'Report', detail: 'what to show the owner and what the host checks in a browser' },
  ],
}

// Runs only inside Claude Code's Workflow tool, which supplies args and agent(); it is not a Node script,
// and `node prototype.js` stops with a SyntaxError. Every other agent tool, and Claude Code without the Workflow tool,
// follows workflows/by-hand.md.

// ---------- args ----------
// {
//   stage: 'looks' | 'build' | 'takes' | 'audit' | 'review',
//   project: '/abs/path/<project>',              // the project folder (PLAN.md, script/, looks/, voices/, music/)
//   skill_dir: '/abs/path/video-prototyper',     // this skill's folder (scripts/, assets/, references/)
//   video_id: 'three-bins',                      // build, takes, audit and review stages
//   looks: [{ id, concept, model, mode }],       // looks stage; model is optional; mode is light or dark when set
//   builds: [{ id, from_look, model }],          // build, audit and review stages
//   voices: [{ id }],                            // takes stage: voices whose scene files already exist
//   stt_quick: '<transcriber> -m <model-file> -f {in} -np -nt',
//   stt_words: '<transcriber> -m <model-file> -f {in} -ml 1 -sow -ojf -np -of {out}',
//   copy_rules: { ban: ['...'], require: ['...'] }, // require: checked on full builds only, never on a one-scene look
//   base_url: 'http://127.0.0.1:8770',          // for frame lists; the host runs the server
//   strict: false,                               // audit stage: true after a new take, a timing fix or a script change
//   cue_flags: { look: '', build: '' },          // extra make_cues.py flags from PLAN.md's picks (SKILL.md, the list under Stages at a glance that starts "Flags each make_cues.py call adds"),
//                                                  // e.g. '--captions off', '--no-music', '--title-card 0 --target-seconds 20 --loop'
//   owner_notes: 'notes the owner gave while agents were busy',
//   fixer_model: 'optional model id for the final fixer in the review stage',
//   script_dir: 'script',                        // optional, relative to project; a later video in a series: 'script/<video-id>'
//   voices_dir: 'voices',                        // optional, relative to project; a later video in a series: 'voices/<video-id>'
// }
// The workflow never makes paid calls, never picks for the owner and never waits for input.
// Paid generation, gate decisions and real-browser checks stay with the owner and the host.

const A = args || {}
const STAGE = A.stage
const P = A.project
const S = A.skill_dir
if (!STAGE || !P || !S) throw new Error('args need stage, project and skill_dir')
const SD = String(A.script_dir || 'script').replace(/^\/+|\/+$/g, '')
const VD = String(A.voices_dir || 'voices').replace(/^\/+|\/+$/g, '')
const SCRIPT = `${P}/${SD}`
const VOICES = `${P}/${VD}`

const q = s => `'${String(s).replace(/'/g, `'\\''`)}'`
const RULES = (A.copy_rules && A.copy_rules.ban || []).map(b => `--ban=${q(b)}`).join(' ')
const REQUIRE = (A.copy_rules && A.copy_rules.require || []).map(r => `--require=${q(r)}`).join(' ')
const CUE_LOOK = (A.cue_flags && A.cue_flags.look) ? ' ' + A.cue_flags.look : ''
const CUE_BUILD = (A.cue_flags && A.cue_flags.build) ? ' ' + A.cue_flags.build : ''
const NOTES = A.owner_notes ? `\nOwner notes to apply (also for the reviewer): ${A.owner_notes}` : ''
const COMMON = `You are working on a video-prototyper project at ${P}, using the skill at ${S}.
Read ${S}/SKILL.md, then the reference files this task names. Read ${P}/PLAN.md for the goal, picks, copy rules, design rules and decision log.
Run commands from ${P}/. Never type, print or copy a key. Make no paid calls. Never edit the shared folders ${VOICES} or ${P}/music from a build folder.
When you cannot open a browser, bind a port, play audio or reach the network, say so in your return; the host checks those.${NOTES}`

const CHECKED = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    status: { type: 'string', enum: ['done', 'partial', 'failed'] },
    files: { type: 'array', items: { type: 'string' } },
    checks: { type: 'array', items: { type: 'object', properties: { check: { type: 'string' }, result: { type: 'string' } }, required: ['check', 'result'] } },
    not_covered: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['id', 'status', 'files', 'checks', 'not_covered', 'open_questions'],
}
const FINDINGS = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['clean', 'issues'] },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: { build: { type: 'string' }, rule: { type: 'string' }, issue: { type: 'string' }, fix: { type: 'string' } },
        required: ['build', 'rule', 'issue', 'fix'],
      },
    },
  },
  required: ['verdict', 'findings'],
}
const REPORT = {
  type: 'object',
  properties: {
    for_owner: { type: 'string' },
    host_checks: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['for_owner', 'host_checks', 'open_questions'],
}

function opts(label, phaseName, schema, model) {
  const o = { label, phase: phaseName, schema }
  if (model) o.model = model
  return o
}

function checkBuild(dir, id, level, phaseName, strict) {
  const steps = []
  if (level === 'build') steps.push(`python3 ${q(S + '/scripts/cue_check.py')} --script ${q(SCRIPT + '/script.txt')} --scenes ${q(SCRIPT + '/scenes.json')} --cues ${q(dir + '/cues.json')} ${RULES}`)
  steps.push(`python3 ${q(S + '/scripts/sync_embed.py')} --build ${q(dir)}`)
  steps.push(`python3 ${q(S + '/scripts/static_check.py')} --page ${q(dir + '/index.html')} --level ${level} ${RULES}${level === 'build' ? ' ' + REQUIRE : ''}`)
  steps.push(`node ${q(S + '/scripts/timing_audit.mjs')} --build ${q(dir)}${strict ? ' --strict' : ''}`)
  const incomplete = strict
    ? 'Under --strict an unavailable voice fails; report it under checks.'
    : 'An INCOMPLETE final line with no FAIL lines counts as pass; list the unavailable voice ids under not_covered.'
  return agent(`${COMMON}
Run these commands for ${dir} and report each result exactly as printed. Make no other edits: sync_embed.py only rewrites the embedded data blocks in index.html, and timing_audit.mjs writes qa/timing-audit.json.
${steps.map((s, i) => `${i + 1}. ${s}`).join('\n')}
Return status "done" when all pass, "failed" otherwise; list the failures under checks.
${incomplete}`,
    opts(`check ${id}`, phaseName, CHECKED))
}

async function report(stageName, results) {
  phase('Report')
  return agent(`${COMMON}
Write the summary of the "${stageName}" stage for the owner and the host from these results:
${JSON.stringify(results)}
for_owner: what is ready to look at and where (paths and the URL to open through the host's server), in plain words, with no pick made for the owner.
host_checks: what the host must still check in a real browser with sound (from each result's not_covered, including a look or build result's builder and check parts, plus the opening frame, narrow width and audio checks in ${S}/assets/templates/review-checklist.md).
open_questions: every open question, deduplicated.`,
    opts(`report ${stageName}`, 'Report', REPORT))
}

// ---------- stages ----------
if (STAGE === 'looks') {
  const looks = A.looks || []
  if (!looks.length) throw new Error('looks stage needs args.looks')
  phase('Looks')
  const built = await pipeline(looks,
    look => agent(`${COMMON}
Build one look prototype: "${look.id}", concept: ${look.concept}.
Read ${P}/looks/BRIEF.md (the shared brief) and ${S}/references/look-prototypes.md and ${S}/references/stage-contract.md.
Copy ${S}/assets/build-template/ into ${P}/looks/${look.id}/ and make the look your own; keep the runtime contract. Write only inside ${P}/looks/${look.id}/.
Delete the copied cues.json and write a new one with python3 ${q(S + '/scripts/make_cues.py')} --script ${q(P + '/looks/sample-script.txt')} --scenes ${q(P + '/looks/sample-scenes.json')} --out ${q(P + '/looks/' + look.id + '/cues.json')} --no-voices --no-music${CUE_LOOK} with --title set to the sample scene's title (from looks/sample-scenes.json or looks/BRIEF.md) and --label and --kicker from the Title card line of PLAN.md when it has them${(look.mode === 'light' || look.mode === 'dark') ? ` and --default-mode ${q(look.mode)}` : ' and --default-mode light or dark for this look'}; key every beat to it.
Ship index.html, cues.json, LOOK.md (template ${S}/assets/templates/LOOK.md) and image-requests.json with drawn stand-ins. Generate no images.
If a headless browser works for you, add frames/ named frames/<voice>/<mode>-t<SSS.SS>.png (voice "none" for a look); otherwise say so.`,
      opts(`look ${look.id}`, 'Looks', CHECKED, look.model)),
    (res, look) => res
      ? checkBuild(`${P}/looks/${look.id}`, look.id, 'look', 'Looks').then(check => ({ id: look.id, builder: res, check }))
      : (log(`look ${look.id}: the builder returned nothing (skipped or failed); not checked`),
         { id: look.id, status: 'failed', note: 'the builder returned nothing (skipped or failed); not built or checked' }))
  phase('Compare')
  const compare = await agent(`${COMMON}
Copy ${S}/assets/compare.html into ${P}/looks/ (keep an existing copy) and write ${P}/looks/looks.json with a title naming the sample scene (from looks/BRIEF.md), listing these looks with id, label, folder and builder: ${JSON.stringify(looks.map(l => ({ id: l.id, concept: l.concept, builder: l.model || 'unspecified' })))}.
Report the files written.`,
    opts('compare page', 'Compare', CHECKED))
  return report('looks', { built: built.filter(Boolean), compare })
}

if (STAGE === 'build') {
  const builds = A.builds || []
  if (!builds.length || !A.video_id) throw new Error('build stage needs args.video_id and args.builds')
  phase('Build')
  const done = await pipeline(builds,
    b => agent(`${COMMON}
Build the full video in one look. Build id "${b.id}", starting from the shortlisted look ${P}/looks/${b.from_look}/.
Read ${P}/${A.video_id}/BRIEF.md, ${S}/references/build.md, ${S}/references/stage-contract.md, ${S}/references/viewer.md and ${S}/references/timing-check.md.
Copy the look into ${P}/${A.video_id}/${b.id}/ (never edit the prototype), delete the copied frames/ and qa/ folders, and grow it: every scene from the brief, beats as anchors A(scene, k, f) on the active timing, data-cue on every narration-tied element, the title card, captions, the viewer API.
Delete the cues.json copied from the look, then write ${P}/${A.video_id}/${b.id}/cues.json with python3 ${q(S + '/scripts/make_cues.py')} --script ${q(SCRIPT + '/script.txt')} --scenes ${q(SCRIPT + '/scenes.json')} --out ${q(P + '/' + A.video_id + '/' + b.id + '/cues.json')}${VD !== 'voices' ? ' --voices-manifest ' + q('../../' + VD + '/voices.json') : ''}${CUE_BUILD} and this build's --title, --label, --kicker and --default-mode.
Write only inside ${P}/${A.video_id}/${b.id}/. Keep SCENES-NOTES.md current (template ${S}/assets/templates/SCENES-NOTES.md).`,
      opts(`build ${b.id}`, 'Build', CHECKED, b.model)),
    (res, b) => res
      ? checkBuild(`${P}/${A.video_id}/${b.id}`, b.id, 'build', 'Build').then(check => ({ id: b.id, builder: res, check }))
      : (log(`build ${b.id}: the builder returned nothing (skipped or failed); not checked`),
         { id: b.id, status: 'failed', note: 'the builder returned nothing (skipped or failed); not built or checked' }))
  const viewer = await agent(`${COMMON}
Copy ${S}/assets/viewer.html into ${P}/${A.video_id}/, keeping an existing copy. Write ${P}/${A.video_id}/viewer.json with this video's title, default_build set to the first build, listing these builds with id, label and path (relative to the viewer): ${JSON.stringify(builds.map(b => ({ id: b.id, label: b.id, path: b.id + '/index.html' })))}.
Read ${S}/assets/viewer.json for the shape and ${S}/references/viewer.md for the contract. Check that message_type matches every build's cues.json; keep existing viewer choices when possible. Write only viewer.html and viewer.json in ${P}/${A.video_id}/ and report the files and checks.`,
    opts('viewer page', 'Build', CHECKED))
  return report('build', { builds: done.filter(Boolean), viewer })
}

if (STAGE === 'takes') {
  const voices = A.voices || []
  if (!A.video_id || !voices.length || !A.stt_quick || !A.stt_words) throw new Error('takes stage needs args.video_id, args.voices, args.stt_quick and args.stt_words')
  phase('Takes')
  const takes = await parallel(voices.map(v => () => agent(`${COMMON}
Process the take for voice "${v.id}". Its scene files are ${VOICES}/${v.id}/s<N>.wav; they are already generated. Read ${S}/references/voices.md and ${S}/references/alignment.md.
1. python3 ${q(S + '/scripts/check_takes.py')} --scenes ${q(SCRIPT + '/scenes.json')} --take-dir ${q(VOICES + '/' + v.id)} --stt-cmd ${q(A.stt_quick)} --move-leaks
   Continue only when it exits 0. If it exits 2, stop here: report the scenes to regenerate and why (leak, ending, match rate); regeneration may cost money and is the host's step. If it exits 1 or any other code, the scene checks did not finish: stop here and report what it printed. After any stop at this step, leave the earlier take's files as they are, report "the previous take was kept", propose no manifest entry, and return status "failed".
   Delete ${VOICES}/${v.id}/.pending/ if it exists and create it empty.
2. python3 ${q(S + '/scripts/join_scenes.py')} --take-dir ${q(VOICES + '/' + v.id)} --out ${q(VOICES + '/' + v.id + '/.pending/' + v.id + '.wav')} --scenes ${q(SCRIPT + '/scenes.json')}
3. Resample the pending take to 16 kHz mono with ffmpeg inside .pending/, transcribe that copy with this word-timestamp command template: ${A.stt_words} (fill {in} with the 16 kHz file and {out} with ${VOICES}/${v.id}/.pending/${v.id}-words; the words are in {out}.json).
4. python3 ${q(S + '/scripts/align_words.py')} --script ${q(SCRIPT + '/script.txt')} --words ${q(VOICES + '/' + v.id + '/.pending/' + v.id + '-words.json')} --format whisper-cpp --voice ${q(v.id)} --audio ${q(VOICES + '/' + v.id + '/.pending/' + v.id + '.wav')} --scene-offsets ${q(VOICES + '/' + v.id + '/.pending/' + v.id + '-scenes.json')} --out ${q(VOICES + '/' + v.id + '/.pending/' + v.id + '-timing.json')} --aligner-label "<the transcriber's name, version and model>"
   (Change --format if the template above writes another format.) If it exits 3, report the missing ending; do not pass --allow-missing-ending (that is the owner's call).
5. Only when step 4 exits 0, move .pending/${v.id}.wav, .pending/${v.id}-scenes.json, .pending/${v.id}-timing.json and .pending/${v.id}-words.json over the take's files and delete .pending/. When step 2, 3 or 4 fails, delete .pending/, leave the earlier files as they are, and report "the previous take was kept". Propose a manifest entry only after promotion; its audio and timing paths name the final files outside .pending/.
Write only inside ${VOICES}/${v.id}/. Return the voices.json entry you propose in checks (check "manifest entry").`,
    opts(`take ${v.id}`, 'Takes', CHECKED))))
  phase('Manifest')
  const merged = await agent(`${COMMON}
When voices.json does not exist, create it with only the No voice entry (id none), never from the skill's template examples. Merge the ready takes into ${VOICES}/voices.json (keep the No voice entry and every existing entry; for an entry with the same id, update the fields the proposed entry sets and keep the rest, such as design_prompt, a hand-written note and a dated model, and report any note you kept so the host can check it still applies). Use only results with status "done":
${JSON.stringify(takes.filter(Boolean))}
Then, for each folder under ${P}/${A.video_id}/ that holds a cues.json, run python3 ${q(S + '/scripts/sync_embed.py')} --build <that folder> once, and report what each run printed.`,
    opts('merge manifest', 'Manifest', CHECKED))
  return report('takes', { takes: takes.filter(Boolean), merged })
}

if (STAGE === 'audit') {
  const builds = A.builds || []
  if (!builds.length || !A.video_id) throw new Error('audit stage needs args.video_id and args.builds')
  phase('Audit')
  const audits = await parallel(builds.map(b => () => agent(`${COMMON}
Audit ${P}/${A.video_id}/${b.id}. Make no edits beyond the reports these commands write under qa/. Report each result as printed.
1. python3 ${q(S + '/scripts/static_check.py')} --page ${q(P + '/' + A.video_id + '/' + b.id + '/index.html')} ${RULES} ${REQUIRE}
2. node ${q(S + '/scripts/timing_audit.mjs')} --build ${q(P + '/' + A.video_id + '/' + b.id)}${A.strict ? ' --strict' : ''}
3. python3 ${q(S + '/scripts/frame_review.py')} --build ${q(P + '/' + A.video_id + '/' + b.id)} --base-url ${q((A.base_url || 'http://127.0.0.1:8770') + '/' + A.video_id + '/' + b.id + '/index.html')}
List every failure from qa/timing-audit.json under checks, and the frame list path under files.
${A.strict ? 'Under --strict an unavailable voice fails; report it under checks.' : 'An INCOMPLETE final line with no FAIL lines counts as pass; list the unavailable voice ids under not_covered.'}`,
    opts(`audit ${b.id}`, 'Audit', CHECKED))))
  return report('audit', { audits: audits.filter(Boolean) })
}

if (STAGE === 'review') {
  const builds = A.builds || []
  if (!builds.length || !A.video_id) throw new Error('review stage needs args.video_id and args.builds')
  phase('Review')
  const review = await agent(`${COMMON}
You are the read-only reviewer. Write nothing.
Check every build in ${P}/${A.video_id}/ (${builds.map(b => b.id).join(', ')}) against ${S}/assets/templates/review-checklist.md (the Reviewer sections), ${S}/references/timing-check.md, ${S}/references/stage-contract.md and ${S}/references/viewer.md.
Read each build's index.html, cues.json, SCENES-NOTES.md, qa/timing-audit.json and ${P}/${A.video_id}/BRIEF.md. Read each build's qa/timing-audit.json; when it is missing, report that as a finding (run the audit stage first) rather than running the audit.
Report each finding with the build, the rule, the issue and the fix. Verdict "clean" only when nothing needs a change.`,
    opts('review', 'Review', FINDINGS))
  if (!review || (review.verdict !== 'clean' && review.verdict !== 'issues') || !Array.isArray(review.findings)
      || (review.verdict === 'clean') !== (review.findings.length === 0)) {
    log('review incomplete: the reviewer returned no usable result; no fixer ran')
    return { stage: 'review', status: 'incomplete', review, next: 'Run the review stage again; nothing was fixed.' }
  }
  let fixed = null
  let recheck = []
  if (review.verdict === 'issues') {
    log(`${review.findings.length} finding(s); one fixer applies them to every build`)
    fixed = await agent(`${COMMON}
Apply these review findings to every live build in ${P}/${A.video_id}/ (${builds.map(b => b.id).join(', ')}):
${JSON.stringify(review.findings)}
Fix timing by moving anchors, never by writing seconds. Keep the stage and viewer contracts working. Update each SCENES-NOTES.md.`,
      opts('final fixes', 'Review', CHECKED, A.fixer_model))
    recheck = await parallel(builds.map(b => () => checkBuild(`${P}/${A.video_id}/${b.id}`, b.id, 'build', 'Review', true)))
  } else {
    log('review clean: no fixer needed')
  }
  return report('review', { review, fixed, recheck: recheck.filter(Boolean) })
}

throw new Error(`unknown stage "${STAGE}"; use looks, build, takes, audit or review`)
