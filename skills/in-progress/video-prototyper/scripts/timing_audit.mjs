#!/usr/bin/env node
// Timing audit (rule R5): runs a build's own inline script in a simulated page for every voice
// in its manifest and both modes, then checks R1 to R4 with assets/timing-audit.js.
//
// Dependencies: Node 18 or later, no packages. No browser, sockets or network needed.
//
// Usage:
//   node timing_audit.mjs --build <video-id>/<build-id> [--out <build>/qa/timing-audit.json]
//       [--voices all|id,id] [--modes light,dark] [--early 0.3] [--late 0.5] [--readable 0.5]
//       [--min-tagged 1] [--clear 1.0] [--strict] [--core <path to timing-audit.js>]
//
// The build folder holds index.html and cues.json. Voice and music manifests are found through
// cues.json (voices.manifest, music.manifest), relative to the build folder, as the page finds them.
// For No voice it also records each tagged element's visible span (visible_spans in the report,
// measured on the sample grid) and prints the shortest; that is a report, not a rule. When
// cues.json sets "loop": true, no scene or tagged element may be visible at t = duration.
//
// Limits: the page runs against a small DOM stand-in. It reads inline styles set by the page's
// script (opacity, display, visibility, the hidden attribute); stylesheet rules, layout, fonts,
// overlap, clipping and audio are not seen. The host checks those in a real browser.
//
// Exit codes: 0 every available voice passes in every mode, or the only gaps are unavailable
// manifest voices or a configured voices manifest whose file is missing (the final line is
// INCOMPLETE); 1 any failure, or an unavailable voice or that missing manifest when --strict
// is set; 2 bad arguments or the page could not load. A null manifest, and an explicit
// --voices none run, stay No voice only and do not treat a missing file as incomplete.

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

// ---------- arguments ----------
function parseArgs(argv) {
  const out = { voices: 'all', modes: 'light,dark', early: 0.3, late: 0.5, readable: 0.5, clear: 1.0, minTagged: 1, strict: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => { if (i + 1 >= argv.length) throw new Error(`${a} needs a value`); return argv[++i]; };
    if (a === '--build') out.build = next();
    else if (a === '--out') out.out = next();
    else if (a === '--voices') out.voices = next();
    else if (a === '--modes') out.modes = next();
    else if (a === '--early') out.early = Number(next());
    else if (a === '--late') out.late = Number(next());
    else if (a === '--readable') out.readable = Number(next());
    else if (a === '--clear') out.clear = Number(next());
    else if (a === '--min-tagged') out.minTagged = Number(next());
    else if (a === '--strict') out.strict = true;
    else if (a === '--core') out.core = next();
    else if (a === '-h' || a === '--help') out.help = true;
    else throw new Error(`unknown argument ${a}`);
  }
  return out;
}

// ---------- a small DOM stand-in ----------
const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
const RAW = new Set(['script', 'style', 'textarea', 'title']);
const kebab = s => s.replace(/[A-Z]/g, m => '-' + m.toLowerCase());
const camel = s => s.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
const decode = s => s.replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, (m, e) => {
  const k = e.toLowerCase();
  if (k[0] === '#') return String.fromCodePoint(k[1] === 'x' ? parseInt(k.slice(2), 16) : parseInt(k.slice(1), 10));
  return { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' }[k];
});

class TextNode {
  constructor(data) { this.nodeType = 3; this.data = data; this.parentNode = null; }
  get textContent() { return this.data; }
  set textContent(v) { this.data = String(v); }
  get parentElement() { return this.parentNode; }
}

function makeStyle(owner) {
  const style = {
    setProperty(name, value) { style[name.startsWith('--') ? name : camel(name)] = String(value); },
    getPropertyValue(name) { const v = style[name.startsWith('--') ? name : camel(name)]; return v === undefined ? '' : String(v); },
    removeProperty(name) { delete style[name.startsWith('--') ? name : camel(name)]; },
  };
  Object.defineProperty(style, 'cssText', {
    enumerable: false,
    get() { return ''; },
    set(v) { parseStyleInto(style, v); },
  });
  return style;
}
function parseStyleInto(style, text) {
  String(text).split(';').forEach(decl => {
    const i = decl.indexOf(':');
    if (i < 0) return;
    const name = decl.slice(0, i).trim(), value = decl.slice(i + 1).trim();
    if (name) style.setProperty(name, value);
  });
}

class Element {
  constructor(tag, doc) {
    this.nodeType = 1;
    this.localName = tag.toLowerCase();
    this.tagName = tag.toUpperCase();
    this.nodeName = this.tagName;
    this.ownerDocument = doc;
    this.attrs = new Map();
    this.childNodes = [];
    this.parentNode = null;
    this._listeners = {};
    this.style = makeStyle(this);
    const self = this;
    this.dataset = new Proxy({}, {
      get(_, p) { return typeof p === 'string' ? (self.getAttribute('data-' + kebab(p)) ?? undefined) : undefined; },
      set(_, p, v) { self.setAttribute('data-' + kebab(p), v); return true; },
      has(_, p) { return self.hasAttribute('data-' + kebab(String(p))); },
      deleteProperty(_, p) { self.removeAttribute('data-' + kebab(String(p))); return true; },
    });
    this.classList = {
      _list() { return (self.getAttribute('class') || '').split(/\s+/).filter(Boolean); },
      contains(c) { return this._list().includes(c); },
      add(...cs) { const l = this._list(); cs.forEach(c => { if (!l.includes(c)) l.push(c); }); self.setAttribute('class', l.join(' ')); },
      remove(...cs) { self.setAttribute('class', this._list().filter(c => !cs.includes(c)).join(' ')); },
      toggle(c, force) { const on = force === undefined ? !this.contains(c) : !!force; if (on) this.add(c); else this.remove(c); return on; },
    };
    if (this.localName === 'audio' || this.localName === 'video') {
      Object.assign(this, { paused: true, currentTime: 0, duration: NaN, volume: 1, muted: false, seeking: false, readyState: 4, preload: 'auto', onerror: null });
      this.play = () => { this.paused = false; return Promise.resolve(); };
      this.pause = () => { this.paused = true; };
      this.load = () => {};
      this.canPlayType = () => 'maybe';
    }
    this.value = '';
    this.checked = false;
    this.disabled = false;
  }
  get id() { return this.getAttribute('id') || ''; }
  set id(v) { this.setAttribute('id', v); }
  get className() { return this.getAttribute('class') || ''; }
  set className(v) { this.setAttribute('class', v); }
  get src() { return this.getAttribute('src') || ''; }
  set src(v) { this.setAttribute('src', v); }
  get type() { return this.getAttribute('type') || ''; }
  set type(v) { this.setAttribute('type', v); }
  get hidden() { return this.hasAttribute('hidden'); }
  set hidden(v) { if (v) this.setAttribute('hidden', ''); else this.removeAttribute('hidden'); }
  getAttribute(n) { n = n.toLowerCase(); return this.attrs.has(n) ? this.attrs.get(n) : null; }
  setAttribute(n, v) {
    n = n.toLowerCase(); v = String(v); this.attrs.set(n, v);
    if (n === 'style') { for (const k of Object.keys(this.style)) if (typeof this.style[k] !== 'function') delete this.style[k]; parseStyleInto(this.style, v); }
    if (n === 'value' && (this.localName === 'input' || this.localName === 'option')) this.value = v;
  }
  removeAttribute(n) { this.attrs.delete(n.toLowerCase()); }
  hasAttribute(n) { return this.attrs.has(n.toLowerCase()); }
  get children() { return this.childNodes.filter(n => n.nodeType === 1); }
  get firstChild() { return this.childNodes[0] || null; }
  get lastChild() { return this.childNodes[this.childNodes.length - 1] || null; }
  get firstElementChild() { return this.children[0] || null; }
  get parentElement() { return this.parentNode && this.parentNode.nodeType === 1 ? this.parentNode : null; }
  get nextElementSibling() { const p = this.parentNode; if (!p) return null; const k = p.children; return k[k.indexOf(this) + 1] || null; }
  appendChild(n) { if (n.parentNode) n.parentNode.removeChild(n); n.parentNode = this; this.childNodes.push(n); return n; }
  append(...ns) { ns.forEach(n => this.appendChild(typeof n === 'string' ? new TextNode(n) : n)); }
  insertBefore(n, ref) { if (!ref) return this.appendChild(n); if (n.parentNode) n.parentNode.removeChild(n); n.parentNode = this; this.childNodes.splice(this.childNodes.indexOf(ref), 0, n); return n; }
  removeChild(n) { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; return n; }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
  replaceChildren(...ns) { this.childNodes.slice().forEach(n => this.removeChild(n)); this.append(...ns); }
  get textContent() { return this.childNodes.map(c => c.textContent).join(''); }
  set textContent(v) { this.childNodes.slice().forEach(n => this.removeChild(n)); if (v !== '' && v !== null && v !== undefined) this.appendChild(new TextNode(String(v))); }
  get innerText() { return this.textContent; }
  set innerText(v) { this.textContent = v; }
  set innerHTML(v) { this.childNodes.slice().forEach(n => this.removeChild(n)); if (String(v).trim()) parseInto(this, String(v), this.ownerDocument); }
  get innerHTML() { return ''; }
  get options() { return this.querySelectorAll('option'); }
  querySelectorAll(sel) { const out = []; const groups = parseSelector(sel); walk(this, n => { if (n !== this && groups.some(g => matchChain(n, g))) out.push(n); }); return out; }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  matches(sel) { return parseSelector(sel).some(g => matchChain(this, g)); }
  closest(sel) { for (let n = this; n && n.nodeType === 1; n = n.parentNode) if (n.matches(sel)) return n; return null; }
  contains(n) { for (; n; n = n.parentNode) if (n === this) return true; return false; }
  addEventListener(t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); }
  removeEventListener(t, fn) { this._listeners[t] = (this._listeners[t] || []).filter(f => f !== fn); }
  dispatchEvent(e) { (this._listeners[e.type] || []).slice().forEach(fn => fn.call(this, e)); return true; }
  click() { this.dispatchEvent({ type: 'click', target: this, preventDefault() {} }); }
  focus() {} blur() {}
  getBoundingClientRect() { return { x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  get offsetWidth() { return 0; } get offsetHeight() { return 0; }
  get clientWidth() { return 0; } get clientHeight() { return 0; }
  getContext() { return null; }
}

function walk(node, fn) { for (const c of node.childNodes) { if (c.nodeType === 1) { fn(c); walk(c, fn); } } }

// Selectors: tag, #id, .class, [attr], [attr=value], descendant (space) and child (>) combinators, commas.
function parseSelector(sel) {
  return String(sel).split(',').map(part => {
    const tokens = part.trim().replace(/\s*>\s*/g, ' > ').split(/\s+/).filter(Boolean);
    const chain = [];
    let combinator = ' ';
    for (const tok of tokens) {
      if (tok === '>') { combinator = '>'; continue; }
      chain.push({ combinator, compound: parseCompound(tok) });
      combinator = ' ';
    }
    return chain;
  });
}
function parseCompound(tok) {
  const c = { tag: null, id: null, classes: [], attrs: [] };
  const re = /([a-zA-Z][\w-]*)|#([\w-]+)|\.([\w-]+)|\[\s*([\w-]+)\s*(?:=\s*(?:"([^"]*)"|'([^']*)'|([^\]\s]+)))?\s*\]|(\*)/g;
  let m;
  while ((m = re.exec(tok))) {
    if (m[1]) c.tag = m[1].toLowerCase();
    else if (m[2]) c.id = m[2];
    else if (m[3]) c.classes.push(m[3]);
    else if (m[4]) c.attrs.push({ name: m[4].toLowerCase(), value: m[5] ?? m[6] ?? m[7] ?? null });
  }
  return c;
}
function matchCompound(n, c) {
  if (n.nodeType !== 1) return false;
  if (c.tag && n.localName !== c.tag) return false;
  if (c.id && n.getAttribute('id') !== c.id) return false;
  for (const cl of c.classes) if (!n.classList.contains(cl)) return false;
  for (const a of c.attrs) { if (!n.hasAttribute(a.name)) return false; if (a.value !== null && n.getAttribute(a.name) !== a.value) return false; }
  return true;
}
function matchChain(n, chain) {
  let i = chain.length - 1;
  if (!matchCompound(n, chain[i].compound)) return false;
  let cur = n;
  while (i > 0) {
    const comb = chain[i].combinator;
    i--;
    if (comb === '>') { cur = cur.parentElement; if (!cur || !matchCompound(cur, chain[i].compound)) return false; }
    else { cur = cur.parentElement; while (cur && !matchCompound(cur, chain[i].compound)) cur = cur.parentElement; if (!cur) return false; }
  }
  return true;
}

function parseInto(root, html, doc) {
  const stack = [root];
  let i = 0;
  const top = () => stack[stack.length - 1];
  while (i < html.length) {
    if (html.startsWith('<!--', i)) { const e = html.indexOf('-->', i + 4); i = e < 0 ? html.length : e + 3; continue; }
    if (html.startsWith('<!', i) || html.startsWith('<?', i)) { const e = html.indexOf('>', i); i = e < 0 ? html.length : e + 1; continue; }
    if (html.startsWith('</', i)) {
      const e = html.indexOf('>', i); const name = html.slice(i + 2, e).trim().toLowerCase(); i = e + 1;
      for (let k = stack.length - 1; k > 0; k--) if (stack[k].localName === name) { stack.length = k; break; }
      continue;
    }
    if (html[i] === '<' && /[a-zA-Z]/.test(html[i + 1] || '')) {
      let j = i + 1, quote = null;
      while (j < html.length) { const ch = html[j]; if (quote) { if (ch === quote) quote = null; } else if (ch === '"' || ch === "'") quote = ch; else if (ch === '>') break; j++; }
      const inner = html.slice(i + 1, j); i = j + 1;
      const nameMatch = /^([a-zA-Z][\w-]*)/.exec(inner);
      const el = new Element(nameMatch[1], doc);
      const attrText = inner.slice(nameMatch[1].length);
      const are = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let m;
      while ((m = are.exec(attrText))) el.setAttribute(m[1], decode(m[2] ?? m[3] ?? m[4] ?? ''));
      top().appendChild(el);
      if (RAW.has(el.localName)) {
        const close = html.toLowerCase().indexOf('</' + el.localName, i);
        const end = close < 0 ? html.length : close;
        const raw = html.slice(i, end);
        if (raw) el.appendChild(new TextNode(el.localName === 'textarea' || el.localName === 'title' ? decode(raw) : raw));
        const gt = html.indexOf('>', end); i = gt < 0 ? html.length : gt + 1;
        continue;
      }
      if (!VOID.has(el.localName) && !/\/\s*$/.test(inner)) stack.push(el);
      continue;
    }
    const next = html.indexOf('<', i + 1);
    const end = next < 0 ? html.length : next;
    const text = html.slice(i, end);
    if (text) top().appendChild(new TextNode(decode(text)));
    i = end;
  }
}

class Doc extends Element {
  constructor() {
    super('#document', null);
    this.nodeType = 9;
    this.ownerDocument = this;
    this.fonts = { ready: Promise.resolve() };
    this.readyState = 'complete';
    this.visibilityState = 'visible';
    this.hidden = false;
  }
  get hidden() { return false; }
  set hidden(v) {}
  get documentElement() { return this.children[0] || null; }
  get head() { return this.querySelector('head'); }
  get body() { return this.querySelector('body'); }
  get activeElement() { return this.body; }
  getElementById(id) { let found = null; walk(this, n => { if (!found && n.getAttribute('id') === id) found = n; }); return found; }
  createElement(tag) { return new Element(tag, this); }
  createTextNode(t) { return new TextNode(String(t)); }
}

// ---------- page runner ----------
function effectiveOpacity(node) {
  let o = 1;
  for (let n = node; n && n.nodeType === 1; n = n.parentNode) {
    if (n.hasAttribute('hidden')) return 0;
    if (n.style.display === 'none' || n.style.visibility === 'hidden') return 0;
    const v = parseFloat(n.style.opacity);
    if (!Number.isNaN(v)) o *= v;
  }
  return o;
}

function makeFetch(buildDir) {
  return async (url, init = {}) => {
    const clean = String(url).split(/[?#]/)[0];
    const file = path.resolve(buildDir, decodeURIComponent(clean));
    const ok = fs.existsSync(file) && fs.statSync(file).isFile();
    const method = (init.method || 'GET').toUpperCase();
    const body = ok && method !== 'HEAD' ? fs.readFileSync(file, 'utf8') : '';
    return {
      ok, status: ok ? 200 : 404,
      json: async () => JSON.parse(body),
      text: async () => body,
    };
  };
}

async function bootPage(html, buildDir, search, consoleErrors) {
  const doc = new Doc();
  parseInto(doc, html, doc);
  if (!doc.body) throw new Error('index.html has no <body>');
  const listeners = {};
  let now = 0;
  const sandbox = {
    document: doc,
    location: { protocol: 'http:', host: '127.0.0.1:8770', hostname: '127.0.0.1', origin: 'http://127.0.0.1:8770', pathname: '/build/index.html', search, href: 'http://127.0.0.1:8770/build/index.html' + search },
    history: { replaceState() {}, pushState() {} },
    navigator: { userAgent: 'timing-audit' },
    performance: { now: () => now },
    requestAnimationFrame: () => 0,
    cancelAnimationFrame: () => {},
    setTimeout, clearTimeout,
    setInterval: () => 0, clearInterval: () => {},
    URLSearchParams, URL, TextEncoder, TextDecoder,
    fetch: makeFetch(buildDir),
    console: {
      log() {}, info() {}, debug() {},
      warn() {},
      error: (...a) => consoleErrors.push(a.map(String).join(' ')),
    },
    innerWidth: 1920, innerHeight: 1192, devicePixelRatio: 1,
    matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }),
    getComputedStyle: n => n.style,
    addEventListener: (t, fn) => { (listeners[t] = listeners[t] || []).push(fn); },
    removeEventListener: () => {},
    dispatchEvent: () => true,
    postMessage: () => {},
    Audio: function () { return doc.createElement('audio'); },
  };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  sandbox.parent = sandbox;
  sandbox.top = sandbox;
  const ctx = vm.createContext(sandbox);
  const scripts = doc.querySelectorAll('script');
  let n = 0;
  for (const s of scripts) {
    const type = (s.getAttribute('type') || '').toLowerCase();
    if (s.hasAttribute('src')) continue;
    if (type && type !== 'text/javascript' && type !== 'application/javascript') {
      if (type === 'module') throw new Error('inline module scripts are not supported by the audit; use a classic <script>');
      continue;
    }
    n++;
    vm.runInContext(s.textContent, ctx, { filename: `index.html#script${n}`, timeout: 10000 });
  }
  doc.dispatchEvent({ type: 'DOMContentLoaded' });
  (listeners.load || []).forEach(fn => fn({ type: 'load' }));
  const video = sandbox.__video;
  if (!video) throw new Error('the page did not define window.__video');
  await Promise.race([
    Promise.resolve(video.ready),
    new Promise((_, rej) => setTimeout(() => rej(new Error('__video.ready did not resolve within 10 s')), 10000)),
  ]);
  return { doc, video, ctx };
}

// ---------- independent timing (same documented repairs as the build contract) ----------
const words = t => String(t || '').split(/\s+/).filter(Boolean).length;
function expectedTiming(cues, take) {
  const pre = Number(cues.title_card?.duration_s ?? 3.5), tail = Number(cues.tail_s ?? 6);
  let flat = [];
  for (const sc of cues.scenes) sc.cues.forEach(c => flat.push({ id: c.id, scene: sc.n, text: c.text, start: Number(c.start), end: Number(c.end) }));
  const warnings = [];
  let audioDur = null;
  if (take) {
    audioDur = Number(take.duration);
    flat = flat.map((c, i) => ({ ...c, start: Number(take.sentences[i].start), end: Number(take.sentences[i].end), text: take.sentences[i].text || c.text }));
    for (let i = 0; i < flat.length; i++) {
      if (i > 0 && flat[i].start < flat[i - 1].start) { flat[i].start = flat[i - 1].start; warnings.push(`${flat[i].id}: start clamped`); }
      if (flat[i].end < flat[i].start) flat[i].end = flat[i].start;
    }
    for (let j = 0; j < flat.length; j++) {
      if (flat[j].end - flat[j].start >= 0.05) continue;
      const prevEnd = j > 0 ? flat[j - 1].end : 0, slot = Math.max(0.6, words(flat[j].text) / 2.4);
      if (flat.slice(j).every(x => x.end - x.start < 0.05)) { flat[j].start = prevEnd + 0.3; flat[j].end = flat[j].start + slot; warnings.push(`${flat[j].id}: last line not in the audio`); }
      else { flat[j].end = Math.max(flat[j].start + 0.05, Math.min(flat[j + 1].start, flat[j].start + slot)); warnings.push(`${flat[j].id}: zero-length sentence`); }
    }
  }
  const lastEnd = flat[flat.length - 1].end;
  const duration = pre + Math.max(lastEnd + tail, audioDur || 0);
  const sentences = flat.map(s => ({ id: s.id, scene: s.scene, start: pre + s.start, end: pre + s.end }));
  const lead = Number(cues.pace?.scene_lead_s ?? 0.6);
  const scenes = cues.scenes.map(sc => ({ n: sc.n, sentences: sentences.filter(s => s.scene === sc.n) }));
  scenes.forEach((sc, i) => {
    sc.vstart = i === 0 ? pre : Math.max(scenes[i - 1].sentences.at(-1).end, sc.sentences[0].start - lead);
  });
  scenes.forEach((sc, i) => { sc.vend = i === scenes.length - 1 ? duration : scenes[i + 1].vstart; });
  return {
    preRoll: pre,
    duration,
    sentences,
    scenes,
    warnings,
  };
}

function readJSON(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }

function listedPath(value) {
  return value != null && String(value).trim() !== '';
}

function voiceEntries(cues, buildDir) {
  const list = [{ id: 'none', label: 'No voice', available: true, take: null }];
  const rel = cues.voices && cues.voices.manifest;
  if (!rel) return { list, missingManifest: null };
  const manifest = path.resolve(buildDir, rel);
  if (!fs.existsSync(manifest)) return { list, missingManifest: rel };
  const dir = path.dirname(manifest);
  const cueCount = cues.scenes.reduce((n, s) => n + s.cues.length, 0);
  for (const v of readJSON(manifest).voices || []) {
    if (v.id === 'none') continue;
    if (!listedPath(v.audio)) {
      list.push({ id: v.id, label: v.label || v.id, available: false, reason: 'no audio file listed', take: null });
      continue;
    }
    if (!listedPath(v.timing)) {
      list.push({ id: v.id, label: v.label || v.id, available: false, reason: 'no timing file listed', take: null });
      continue;
    }
    const audio = path.resolve(dir, v.audio), timing = path.resolve(dir, v.timing);
    let reason = '', take = null;
    if (!audio || !fs.existsSync(audio)) reason = 'audio file missing';
    else if (!fs.existsSync(timing)) reason = 'timing file missing';
    else {
      take = readJSON(timing);
      if (!take.sentences || !take.sentences.length) reason = 'timing has no sentences';
      else if ((take.scenes || []).length !== cues.scenes.length) reason = `timing has ${(take.scenes || []).length} scenes; cues have ${cues.scenes.length}`;
      else if (take.sentences.length !== cueCount) reason = `timing has ${take.sentences.length} sentences; cues have ${cueCount}`;
      else if (cues.source_words_sha256 && take.source_words_sha256 && cues.source_words_sha256 !== take.source_words_sha256) reason = 'stale: the script changed after this take was aligned';
    }
    list.push({ id: v.id, label: v.label || v.id, available: !reason, reason, take });
  }
  return { list, missingManifest: null };
}

// ---------- main ----------
async function main() {
  let args;
  try { args = parseArgs(process.argv.slice(2)); } catch (e) { console.error(e.message); return 2; }
  if (args.help || !args.build) { console.log('usage: node timing_audit.mjs --build <video-id>/<build-id> [--out <build>/qa/timing-audit.json] [--voices all|id,id] [--modes light,dark] [--early 0.3] [--late 0.5] [--readable 0.5] [--min-tagged 1] [--clear 1.0] [--strict] [--core <path to timing-audit.js>]'); return args.help ? 0 : 2; }
  const buildDir = path.resolve(args.build);
  const htmlPath = path.join(buildDir, 'index.html'), cuesPath = path.join(buildDir, 'cues.json');
  if (!fs.existsSync(htmlPath) || !fs.existsSync(cuesPath)) { console.error(`need index.html and cues.json in ${buildDir}`); return 2; }
  const html = fs.readFileSync(htmlPath, 'utf8');
  const cues = readJSON(cuesPath);
  const corePath = args.core ? path.resolve(args.core) : path.resolve(HERE, '..', 'assets', 'timing-audit.js');
  const coreCtx = vm.createContext({});
  vm.runInContext(fs.readFileSync(corePath, 'utf8'), coreCtx, { filename: 'timing-audit.js' });
  const audit = coreCtx.videoTimingAudit;
  const modes = args.modes.split(',').map(s => s.trim()).filter(Boolean);
  const foundVoices = voiceEntries(cues, buildDir);
  let voices = foundVoices.list;
  const missingManifest = foundVoices.missingManifest;
  if (args.voices !== 'all') { const want = new Set(args.voices.split(',')); voices = voices.filter(v => want.has(v.id)); }

  const report = {
    tool: 'timing_audit.mjs',
    build: path.basename(buildDir),
    rules: { early_s: args.early, late_s: args.late, readable_s: args.readable, clear_s: args.clear, visible_opacity: 0.01, readable_opacity: 0.5 },
    limits: 'Simulated DOM: checks the inline styles the page script sets after each seek. Layout, stylesheet rules, fonts, overlap, clipping and audio need a real browser.',
    voices: [],
    failures: [],
    status: 'pass',
  };
  if (args.voices === 'all' && missingManifest) report.voices_manifest_missing = missingManifest;

  for (const v of voices) {
    const rec = { id: v.id, label: v.label, available: v.available, modes: {} };
    if (!v.available) { rec.reason = v.reason; report.voices.push(rec); continue; }
    const exp = expectedTiming(cues, v.take);
    rec.take_warnings = exp.warnings;
    for (const mode of modes) {
      const errors = [];
      const search = `?voice=${encodeURIComponent(v.id)}&mode=${mode}&render=1&music=off`;
      let page;
      try { page = await bootPage(html, buildDir, search, errors); }
      catch (e) { rec.modes[mode] = { status: 'fail', failures: [`page did not load: ${e.message}`] }; continue; }
      const { doc, video } = page;
      const failures = [];
      const notes = [];
      if (typeof video.state === 'function') {
        const st = video.state();
        if (st.voice !== v.id) failures.push(`page selected voice "${st.voice}" instead of "${v.id}"`);
      } else notes.push('base API only: voice selection not checked');
      if (Math.abs(video.duration - exp.duration) > 0.05) failures.push(`duration ${video.duration.toFixed(2)} s; expected ${exp.duration.toFixed(2)} s (pre-roll + last sentence + tail, or the audio length)`);
      const tl = typeof video.timeline === 'function' ? video.timeline() : null;
      if (tl) {
        if (Math.abs(tl.preRoll - exp.preRoll) > 0.001) failures.push(`pre-roll ${tl.preRoll} s; cues.json title card is ${exp.preRoll} s`);
        exp.sentences.forEach((s, i) => {
          const p = tl.sentences[i];
          if (!p || p.id !== s.id || Math.abs(p.start - s.start) > 0.011 || Math.abs(p.end - s.end) > 0.011) failures.push(`page timing for ${s.id} differs from the timing file`);
        });
      }
      const scenes = exp.scenes;
      if (tl) {
        if (!Array.isArray(tl.scenes) || tl.scenes.length !== scenes.length || scenes.some((s, i) => {
          const p = tl.scenes[i];
          return !p || p.n !== s.n || Math.abs(p.vstart - s.vstart) > 0.011 || Math.abs(p.vend - s.vend) > 0.011;
        })) failures.push('page scene windows differ');
      }
      const tagged = () => doc.querySelectorAll('[data-cue]').map(n => {
        const sc = n.closest('[data-scene]');
        return { node: n, cue: n.getAttribute('data-cue'), at: parseFloat(n.getAttribute('data-cue-at') || '0'), scene: sc ? Number(sc.getAttribute('data-scene')) : null };
      });
      // Coverage: teaching text sits under data-cue (or data-label); tags match their sentence's scene.
      const bySentence = Object.fromEntries(exp.sentences.map(s => [s.id, s]));
      const checkCoverage = () => {
        doc.querySelectorAll('[data-scene], [data-scene] *').forEach(n => {
          const own = n.childNodes.filter(c => c.nodeType === 3).map(c => c.data).join('').trim();
          if (!own) return;
          if (!n.closest('[data-cue]') && !n.closest('[data-label]')) failures.push(`R5 untagged text in scene ${n.closest('[data-scene]').getAttribute('data-scene')}: "${own.slice(0, 40)}"`);
        });
      };
      video.seek(0); checkCoverage(); video.seek(exp.duration - 0.01); checkCoverage();
      const tags = tagged();
      if (tags.length < args.minTagged) failures.push(`R5 only ${tags.length} tagged elements (minimum ${args.minTagged})`);
      tags.forEach(t => { const s = bySentence[t.cue]; if (s && t.scene !== s.scene) failures.push(`R5 #${t.node.id || t.cue} sits in scene ${t.scene} but its sentence is in scene ${s.scene}`); });
      const sceneSections = doc.querySelectorAll('[data-scene]').map(n => Number(n.getAttribute('data-scene')));
      const sectionSet = new Set(sceneSections.map(String));
      const taggedByScene = {};
      tags.forEach(t => { if (t.scene !== null && t.scene !== undefined) taggedByScene[String(t.scene)] = true; });
      scenes.forEach(sc => {
        if (!sectionSet.has(String(sc.n))) failures.push(`R3 scene ${sc.n} has no [data-scene="${sc.n}"] section`);
        else if (!taggedByScene[String(sc.n)]) failures.push(`R5 scene ${sc.n} has no tagged element`);
      });
      const capNode = doc.querySelector('[data-captions]') || doc.getElementById('captions');
      const card = doc.querySelector('[data-title-card]') || doc.getElementById('title-card');
      if (!card) failures.push('R1 no title card element (data-title-card)');
      const result = audit({
        seek: t => video.seek(t),
        tagged,
        opacity: effectiveOpacity,
        caption: () => (capNode && effectiveOpacity(capNode) >= 0.01 ? capNode.textContent : ''),
        titleCard: () => (card ? effectiveOpacity(card) : 0),
        scenesShown: () => doc.querySelectorAll('[data-scene]').filter(n => effectiveOpacity(n) >= 0.01).map(n => n.getAttribute('data-scene')),
        sentences: exp.sentences,
        scenes,
        sceneSections,
        preRoll: exp.preRoll,
        duration: video.duration,
        loop: !!cues.loop,
        spans: v.id === 'none',
        tol: { early: args.early, late: args.late, readable: args.readable, clear: args.clear },
        seed: 7,
      });
      const all = [...new Set(failures.concat(result.failures).concat(errors.map(e => `console error: ${e}`)))];
      rec.modes[mode] = { ...result, notes, failures: all, status: all.length ? 'fail' : 'pass' };
    }
    const modeRecs = Object.values(rec.modes);
    rec.worst_early_offset = Math.max(0, ...modeRecs.map(m => m.worst_early_offset || 0));
    rec.worst_late_offset = Math.max(0, ...modeRecs.map(m => m.worst_late_offset || 0));
    rec.worst_readable_offset = Math.max(0, ...modeRecs.map(m => m.worst_readable_offset || 0));
    rec.status = modeRecs.every(m => m.status === 'pass') ? 'pass' : 'fail';
    for (const [mode, m] of Object.entries(rec.modes)) m.failures.forEach(f => report.failures.push(`${v.id} ${mode}: ${f}`));
    report.voices.push(rec);
  }
  if (report.voices.every(v => !v.available)) report.failures.push('no available voice to audit');
  const unavailable = report.voices.filter(v => v.id !== 'none' && !v.available);
  report.status = report.failures.length ? 'fail' : (unavailable.length ? 'incomplete' : 'pass');
  if (args.voices === 'all' && missingManifest && report.status !== 'fail') report.status = 'incomplete';
  const out = args.out ? path.resolve(args.out) : path.join(buildDir, 'qa', 'timing-audit.json');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
  for (const v of report.voices) {
    if (!v.available) { console.log(`${v.id}: not available (${v.reason})`); continue; }
    console.log(`${v.id}: ${v.status}  worst early ${v.worst_early_offset.toFixed(2)} s, late ${v.worst_late_offset.toFixed(2)} s, readable ${v.worst_readable_offset.toFixed(2)} s`);
    let shortest = null;
    for (const [mode, m] of Object.entries(v.modes)) {
      const sp = m.shortest_visible_span;
      if (sp && (!shortest || sp.span < shortest.span)) shortest = { ...sp, mode };
    }
    if (shortest) console.log(`  shortest visible span: ${shortest.span.toFixed(2)} s, ${shortest.element} (${shortest.cue}), ${shortest.mode}; every span is in the report`);
  }
  report.failures.slice(0, 20).forEach(f => console.log(`  FAIL ${f}`));
  if (report.failures.length > 20) console.log(`  ... ${report.failures.length - 20} more in ${out}`);
  if (report.status !== 'incomplete') console.log(`${report.status.toUpperCase()}: wrote ${out}`);
  console.log('Not covered: layout, overlap, clipping, fonts and audio. Check those in a real browser.');
  if (report.status === 'incomplete' && report.voices_manifest_missing) console.log(`INCOMPLETE: voices manifest ${report.voices_manifest_missing} not found; only No voice was audited`);
  else if (report.status === 'incomplete') console.log(`INCOMPLETE: ${unavailable.length} voice(s) not available: ${unavailable.map(v => v.id).join(', ')}`);
  if (report.status === 'fail') return 1;
  if (report.status === 'incomplete' && args.strict) return 1;
  return 0;
}

main().then(code => process.exit(code), e => { console.error(e && e.stack || String(e)); process.exit(2); });
