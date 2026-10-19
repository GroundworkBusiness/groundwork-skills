/*
  Timing audit core for the video-prototyper skill (rules R1 to R4, checked per voice and mode).

  It measures what is painted after each seek, never the scheduled reveal times.
  scripts/timing_audit.mjs loads this file and runs it against a simulated page for every voice.
  In a real browser, paste this file into the console of a build, then run:

    videoTimingAudit.inBrowser().then(r => console.log(r.status, r.failures))

  The browser helper takes sentence times from the page's own __video.timeline(), so it checks
  the reveals against the page's reading of the timing; the Node runner checks against the
  timing files directly.

  videoTimingAudit(o) takes:
    o.seek(t)             sets the page to the state it has at time t (video time)
    o.tagged()            [{node, cue, at, scene}] every element with data-cue
    o.opacity(node)       effective opacity: product through ancestors, 0 when display none or hidden
    o.caption()           the caption text currently shown ('' when none)
    o.titleCard()         effective opacity of the title card
    o.scenesShown()       optional: numbers of the scenes ([data-scene]) currently visible
    o.sentences           [{id, scene, start, end}] in video time
    o.scenes              [{n, vstart, vend}] in video time
    o.preRoll, o.duration
    o.tol                 {early: 0.3, late: 0.5, readable: 0.5, clear: 1.0}
    o.sceneSections       optional: scene numbers that have a [data-scene] section
    o.seed                integer for the shuffled determinism pass
    o.loop                optional: true for a loop (cues.json "loop"); at t = duration no scene
                          and no tagged element may be visible, so the end matches the start
    o.spans               optional: true to report each tagged element's visible span
  It returns {status, failures, warnings, worst_early_offset, worst_late_offset,
  worst_readable_offset, tagged, samples, determinism_mismatches}, plus visible_spans
  ([{element, cue, first_visible, gone_at, span}], measured on the sample grid) and
  shortest_visible_span when o.spans is set.
*/
(function (root) {
  'use strict';

  function round(x, d) { var m = Math.pow(10, d || 3); return Math.round(x * m) / m; }

  function videoTimingAudit(o) {
    var tol = o.tol || {};
    var EARLY = tol.early === undefined ? 0.3 : tol.early;
    var LATE = tol.late === undefined ? 0.5 : tol.late;
    var READ = tol.readable === undefined ? 0.5 : tol.readable;
    var CLEAR = tol.clear === undefined ? 1.0 : tol.clear;
    var VISIBLE = 0.01, READABLE = 0.5, EPS = 1e-6;
    var failures = [], warnings = [];
    var byId = {};
    o.sentences.forEach(function (s) { byId[s.id] = s; });

    var tagged = o.tagged().map(function (t) {
      var s = byId[t.cue];
      if (!s) { failures.push('R5 ' + describe(t) + ': data-cue "' + t.cue + '" matches no sentence'); return null; }
      var at = isFinite(t.at) ? Math.max(0, Math.min(1, t.at)) : 0;
      return { t: t, s: s, expected: s.start + at * (s.end - s.start), firstVisible: null, firstReadable: null };
    }).filter(Boolean);

    function describe(t) { return (t.node && (t.node.id || t.node.getAttribute && t.node.getAttribute('id'))) ? '#' + (t.node.id || t.node.getAttribute('id')) : (t.cue || 'element'); }

    if (Array.isArray(o.sceneSections)) {
      var present = {};
      o.sceneSections.forEach(function (n) { present[String(n)] = true; });
      var taggedScenes = {};
      tagged.forEach(function (x) { if (x.t.scene !== null && x.t.scene !== undefined) taggedScenes[String(x.t.scene)] = true; });
      o.scenes.forEach(function (sc) {
        if (!present[String(sc.n)]) failures.push('R3 scene ' + sc.n + ' has no [data-scene="' + sc.n + '"] section');
        else if (!taggedScenes[String(sc.n)]) failures.push('R5 scene ' + sc.n + ' has no tagged element');
      });
    }
    var haveCue = {};
    tagged.forEach(function (x) { haveCue[x.t.cue] = true; });
    o.sentences.forEach(function (s) { if (!haveCue[s.id]) warnings.push('cue ' + s.id + ' has no data-cue element'); });

    // Sampling plan: a 0.25 s grid, scene edges, clear deadlines, and 0.01 s steps around every expected time.
    var times = {};
    function add(t) { if (t >= 0 && t <= o.duration) times[round(t, 4)] = true; }
    for (var g = 0; g <= o.duration; g += 0.25) add(g);
    add(o.duration);
    o.scenes.forEach(function (sc) {
      add(sc.vstart); add(sc.vstart + 0.01); add(sc.vend - 0.01);
      if (sc.vend + CLEAR <= o.duration + EPS) add(sc.vend + CLEAR);
    });
    tagged.forEach(function (x) {
      for (var d = -0.35; d <= 0.6 + EPS; d += 0.01) add(x.expected + d);
      add(x.s.end - 0.001);
    });
    o.sentences.forEach(function (s) { add(s.end - 0.001); });
    add(o.preRoll / 2);
    add(o.preRoll + 0.5);
    var list = Object.keys(times).map(Number).sort(function (a, b) { return a - b; });

    var scenesByN = {};
    o.scenes.forEach(function (sc) { scenesByN[sc.n] = sc; });
    var firstSentenceOfScene = {};
    o.sentences.forEach(function (s) { if (!firstSentenceOfScene[s.scene] || s.start < firstSentenceOfScene[s.scene].start) firstSentenceOfScene[s.scene] = s; });

    var r1Tagged = false, r1Caption = false, r1Scene = false;
    list.forEach(function (t) {
      o.seek(t);
      var cap = (o.caption() || '').trim();
      tagged.forEach(function (x) {
        var op = o.opacity(x.t.node);
        if (op >= VISIBLE && x.firstVisible === null) x.firstVisible = t;
        if (op >= READABLE && x.firstReadable === null) x.firstReadable = t;
        if (x.firstVisible !== null && x.goneAt === undefined && t > x.firstVisible && op < VISIBLE) x.goneAt = t;
        // R4: once it appears, it stays up until the sentence ends. One failure per element.
        if (!x.r4Gone && x.firstVisible !== null && t + EPS >= x.firstVisible && t <= x.s.end - 0.001 + 0.00005 && op < VISIBLE) {
          x.r4Gone = true;
          failures.push('R4 ' + describe(x.t) + ': disappears at ' + round(t, 2) + ' s, before its sentence ends at ' + round(x.s.end, 2) + ' s');
        }
        // R1: nothing narration-tied during the title card.
        if (t < o.preRoll - 0.001 && op >= VISIBLE && !r1Tagged) {
          r1Tagged = true;
          failures.push('R1 ' + describe(x.t) + ': visible at ' + round(t, 2) + ' s, during the title card');
        }
      });
      if (t < o.preRoll - 0.001 && cap && !r1Caption) { r1Caption = true; failures.push('R1 caption shown at ' + round(t, 2) + ' s, during the title card'); }
      if (t < o.preRoll - 0.001 && o.scenesShown && !r1Scene) {
        var shown = o.scenesShown();
        if (shown.length) { r1Scene = true; failures.push('R1 scene ' + shown.join(', ') + ' visible at ' + round(t, 2) + ' s, during the title card'); }
      }
      if (o.preRoll > 0 && Math.abs(t - (o.preRoll + 0.5)) < 0.00005 && o.titleCard() >= VISIBLE) failures.push('R1 title card still visible 0.5 s after it should end (' + round(t, 2) + ' s)');
      if (o.preRoll > 0 && Math.abs(t - o.preRoll / 2) < 0.00005 && o.titleCard() < READABLE) failures.push('R1 title card not visible at ' + round(t, 2) + ' s');
      // R3: scenes open nearly empty.
      o.scenes.forEach(function (sc) {
        if (Math.abs(t - (sc.vstart + 0.01)) > 0.00005) return;
        tagged.forEach(function (x) {
          if (x.t.scene !== sc.n) return;
          if (x.expected - EARLY > t + EPS && o.opacity(x.t.node) >= VISIBLE) failures.push('R3 scene ' + sc.n + ': ' + describe(x.t) + ' already on screen at the scene start (' + round(t, 2) + ' s)');
        });
        var first = firstSentenceOfScene[sc.n];
        if (cap && first && first.start > t + EPS) failures.push('R3 scene ' + sc.n + ': a caption shows at the scene start (' + round(t, 2) + ' s)');
      });
      // R4: a scene and its tagged elements have cleared by vend + clear. The last scene's
      // deadline sits past the duration, so it is not sampled.
      o.scenes.forEach(function (sc) {
        var deadline = sc.vend + CLEAR;
        if (deadline > o.duration + EPS) return;
        if (Math.abs(t - deadline) > 0.00005) return;
        var still = false;
        tagged.forEach(function (x) {
          if (String(x.t.scene) === String(sc.n) && o.opacity(x.t.node) >= VISIBLE) still = true;
        });
        if (!still && o.scenesShown) {
          var shown = o.scenesShown().map(String);
          if (shown.indexOf(String(sc.n)) !== -1) still = true;
        }
        if (still) failures.push('R4 scene ' + sc.n + ': still visible at ' + round(t, 2) + ' s, after the scene should have cleared');
      });
    });

    var worstEarly = 0, worstLate = 0, worstRead = 0;
    tagged.forEach(function (x) {
      var name = describe(x.t) + ' (' + x.t.cue + ')';
      if (x.firstVisible === null) { failures.push('R2 ' + name + ': never visible'); return; }
      var early = x.expected - x.firstVisible, late = x.firstVisible - x.expected;
      worstEarly = Math.max(worstEarly, early); worstLate = Math.max(worstLate, late);
      if (early > EARLY + EPS) failures.push('R2 ' + name + ': visible ' + round(early, 2) + ' s before its words (at ' + round(x.firstVisible, 2) + ' s, words at ' + round(x.expected, 2) + ' s)');
      if (late > LATE + EPS) failures.push('R2 ' + name + ': visible ' + round(late, 2) + ' s after its words');
      if (x.firstReadable === null) failures.push('R2 ' + name + ': never readable (opacity below 0.5)');
      else {
        var rl = x.firstReadable - x.expected;
        worstRead = Math.max(worstRead, rl);
        if (rl > READ + EPS) failures.push('R2 ' + name + ': readable ' + round(rl, 2) + ' s after its words');
      }
    });

    // R4 for a loop: the end state equals the start, so nothing from the last scene is left at t = duration.
    if (o.loop) {
      o.seek(o.duration);
      var left = {};
      if (o.scenesShown) o.scenesShown().forEach(function (n) { left['scene ' + n] = true; });
      tagged.forEach(function (x) {
        if (o.opacity(x.t.node) >= VISIBLE) left[x.t.scene !== null && x.t.scene !== undefined ? 'scene ' + x.t.scene : describe(x.t)] = true;
      });
      Object.keys(left).forEach(function (k) { failures.push('R4 loop: ' + k + ' still visible at the end (' + round(o.duration, 2) + ' s)'); });
    }

    // Visible spans: from first visible to first sample where the element is gone (or the end).
    var spans = null, shortest = null;
    if (o.spans) {
      spans = tagged.filter(function (x) { return x.firstVisible !== null; }).map(function (x) {
        var gone = x.goneAt === undefined ? o.duration : x.goneAt;
        return { element: describe(x.t), cue: x.t.cue, first_visible: round(x.firstVisible, 2), gone_at: round(gone, 2), span: round(gone - x.firstVisible, 2) };
      });
      spans.forEach(function (sp) { if (!shortest || sp.span < shortest.span) shortest = sp; });
    }

    // Determinism: forward, reverse and shuffled seeks give the same painted state.
    var probe = [];
    o.scenes.forEach(function (sc) { probe.push(sc.vstart + 0.2, (sc.vstart + sc.vend) / 2); });
    o.sentences.forEach(function (s) { probe.push(s.start + 0.1); });
    for (var k = 1; k <= 24; k++) probe.push(o.duration * k / 25);
    probe = probe.filter(function (t) { return t >= 0 && t <= o.duration; });
    function signature(t) {
      o.seek(t);
      return tagged.map(function (x) { return round(o.opacity(x.t.node), 3); }).join(',') + '|' + (o.caption() || '') + '|' + round(o.titleCard(), 3);
    }
    var forward = {};
    probe.forEach(function (t) { forward[t] = signature(t); });
    var reverse = probe.slice().reverse();
    var seed = (o.seed || 7) >>> 0;
    function rand() { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }
    var shuffled = probe.slice();
    for (var i = shuffled.length - 1; i > 0; i--) { var j = Math.floor(rand() * (i + 1)); var tmp = shuffled[i]; shuffled[i] = shuffled[j]; shuffled[j] = tmp; }
    var mismatches = 0;
    reverse.concat(shuffled).forEach(function (t) { if (signature(t) !== forward[t]) mismatches++; });
    if (mismatches) failures.push('determinism: ' + mismatches + ' of ' + (reverse.length + shuffled.length) + ' re-seeks painted a different state');

    var result = {
      status: failures.length ? 'fail' : 'pass',
      failures: failures,
      warnings: warnings,
      worst_early_offset: round(worstEarly, 3),
      worst_late_offset: round(worstLate, 3),
      worst_readable_offset: round(worstRead, 3),
      tagged: tagged.length,
      samples: list.length,
      determinism_mismatches: mismatches
    };
    if (spans) { result.visible_spans = spans; result.shortest_visible_span = shortest; }
    return result;
  }

  // Browser helper: real computed styles, sentence times from the page's own timeline().
  videoTimingAudit.inBrowser = function (opts) {
    opts = opts || {};
    var v = window.__video;
    return Promise.resolve(v.ready).then(function () {
      if (typeof v.timeline !== 'function') {
        return { status: 'fail', failures: ['page has no timeline(); run timing_audit.mjs instead'] };
      }
      var tl = v.timeline();
      var wasT = v.time;
      v.pause();
      function opacity(node) {
        var o = 1;
        for (var n = node; n && n.nodeType === 1; n = n.parentElement) {
          var cs = getComputedStyle(n);
          if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
          o *= parseFloat(cs.opacity);
        }
        return o;
      }
      var capNode = document.querySelector('[data-captions]') || document.getElementById('captions');
      var card = document.querySelector('[data-title-card]') || document.getElementById('title-card');
      var report = videoTimingAudit({
        seek: function (t) { v.seek(t); },
        tagged: function () {
          return Array.prototype.map.call(document.querySelectorAll('[data-cue]'), function (n) {
            var sc = n.closest('[data-scene]');
            return { node: n, cue: n.getAttribute('data-cue'), at: parseFloat(n.getAttribute('data-cue-at') || '0'), scene: sc ? Number(sc.getAttribute('data-scene')) : null };
          });
        },
        opacity: opacity,
        caption: function () { return capNode && opacity(capNode) >= 0.01 ? capNode.textContent : ''; },
        titleCard: function () { return card ? opacity(card) : 0; },
        scenesShown: function () {
          return Array.prototype.filter.call(document.querySelectorAll('[data-scene]'), function (n) { return opacity(n) >= 0.01; })
            .map(function (n) { return n.getAttribute('data-scene'); });
        },
        sentences: tl.sentences,
        scenes: tl.scenes,
        sceneSections: Array.prototype.map.call(document.querySelectorAll('[data-scene]'), function (n) { return Number(n.getAttribute('data-scene')); }),
        preRoll: tl.preRoll,
        duration: tl.duration,
        loop: !!tl.loop,
        spans: tl.voice === 'none',
        tol: opts.tol,
        seed: opts.seed
      });
      v.seek(wasT);
      return report;
    });
  };

  root.videoTimingAudit = videoTimingAudit;
  if (typeof module === 'object' && module && module.exports) module.exports = videoTimingAudit;
})(typeof globalThis !== 'undefined' ? globalThis : this);
