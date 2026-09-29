#!/usr/bin/env node
/*
 * Graman signer minter - runs the gramsnap-family link.chunk signer offline (no browser).
 * serve mode: reads JSON lines from stdin {id, payload}, writes JSON lines {id, ok, signed|error}
 * one-shot mode: GM_INPUT env -> prints one JSON result
 * Usage: node minter.js <app.js> <link.chunk.js> [--serve]
 */
'use strict';
const fs = require('fs');

const path = require('path');
const GM_DOMAIN = process.env.GM_DOMAIN || path.basename(path.dirname(path.resolve(process.argv[2] || process.env.GM_APP || '.'))) || 'gramsnap.com';
const GM_ORIGIN = 'https://' + GM_DOMAIN + '/';

/* ---------- browser-shaped globals ---------- */
const _cls = (n) => { if (!globalThis[n]) globalThis[n] = class {}; };
['Element','Document','Window','Node','Text','Comment','HTMLInputElement','HTMLTextAreaElement','HTMLSelectElement','HTMLFormElement','HTMLIFrameElement','HTMLCanvasElement','HTMLMediaElement','HTMLVideoElement','HTMLImageElement','HTMLAudioElement','HTMLScriptElement','HTMLStyleElement','HTMLLinkElement','HTMLDivElement','HTMLSpanElement','HTMLBodyElement','HTMLHtmlElement','HTMLHeadElement','HTMLAnchorElement','HTMLButtonElement','File','FileReader','Image','Option','DOMParser','SVGElement','SVGSVGElement','SVGPathElement','DataTransfer','ClipboardEvent','StorageEvent','HashChangeEvent','PopStateEvent','PageTransitionEvent','BeforeUnloadEvent','AnimationEvent','TransitionEvent','PointerEvent','DragEvent','TouchEvent','WheelEvent','MessageEvent','ProgressEvent','ErrorEvent','UIEvent','InputEvent','FocusEvent','KeyboardEvent','MouseEvent','Event','NodeList','HTMLCollection','DocumentType','ProcessingInstruction','CDATASection','Attr','NamedNodeMap','MediaQueryList','CSSStyleDeclaration','StyleSheet','ShadowRoot','DocumentFragment','Storage','Screen','Worker','SharedWorker','BroadcastChannel','MessageChannel','Notification','Credential','DOMException'].forEach(_cls);
if (!globalThis.AbortSignal) globalThis.AbortSignal = { timeout: () => ({ aborted: false, addEventListener(){} }), any: () => ({ aborted: false }) };
if (!globalThis.AbortController) globalThis.AbortController = class { constructor(){ this.signal = { aborted: false, addEventListener(){}, removeEventListener(){} }; } abort(){} };
if (!globalThis.TextEncoder) globalThis.TextEncoder = class { encode(s){ return Buffer.from(s, 'utf8'); } };
if (!globalThis.TextDecoder) globalThis.TextDecoder = class { decode(b){ return Buffer.from(b).toString('utf8'); } };
if (!globalThis.btoa) globalThis.btoa = (s) => Buffer.from(s, 'binary').toString('base64');
if (!globalThis.atob) globalThis.atob = (s) => Buffer.from(s, 'base64').toString('binary');
globalThis.self = globalThis;
if (!globalThis.window) globalThis.window = globalThis;
globalThis.top = globalThis; globalThis.parent = globalThis; // signer env check: window === window.top
if (!globalThis.navigator) globalThis.navigator = { userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', language: 'en-US', platform: 'Win32', hardwareConcurrency: 8, maxTouchPoints: 0, webdriver: false };
if (!globalThis.location) globalThis.location = { href: GM_ORIGIN + 'en/', protocol: 'https:', host: GM_DOMAIN, hostname: GM_DOMAIN, origin: 'https://' + GM_DOMAIN, pathname: '/en/', search: '', hash: '', assign(){}, replace(){}, reload(){} };
if (!globalThis.document) globalThis.document = {
  createElement: (t) => ({ tagName: String(t).toUpperCase(), style: {}, setAttribute(){}, getAttribute(){ return null; }, appendChild(){}, removeChild(){}, addEventListener(){}, attachShadow: () => ({ appendChild(){} }), classList: { add(){}, remove(){}, contains(){ return false; } }, textContent: '', innerHTML: '', firstChild: null, parentNode: null }),
  createTextNode: () => ({ textContent: '' }), createDocumentFragment: () => ({ appendChild(){}, childNodes: [] }),
  querySelector: () => null, querySelectorAll: () => [], getElementById: () => null,
  addEventListener(){}, removeEventListener(){}, dispatchEvent(){ return true; },
  head: { appendChild(){} }, body: { appendChild(){} }, documentElement: { style: {}, setAttribute(){} },
  cookie: '', currentScript: null, readyState: 'complete', title: '',
};
if (!globalThis.localStorage) { const d = {}; globalThis.localStorage = { getItem: k => (k in d ? d[k] : null), setItem: (k,v)=>{d[k]=String(v)}, removeItem: k=>{delete d[k]}, clear: ()=>{ for (const k in d) delete d[k]; } }; }
if (!globalThis.sessionStorage) globalThis.sessionStorage = { getItem: () => null, setItem(){}, removeItem(){} };
if (!globalThis.CustomEvent) globalThis.CustomEvent = class { constructor(t,o){ this.type=t; Object.assign(this,o||{}); } };
if (!globalThis.MutationObserver) globalThis.MutationObserver = class { observe(){} disconnect(){} };
if (!globalThis.getComputedStyle) globalThis.getComputedStyle = () => ({ getPropertyValue: () => '' });
if (!globalThis.history) globalThis.history = { pushState(){}, replaceState(){}, state: null, back(){}, forward(){} };
if (!globalThis.XMLHttpRequest) globalThis.XMLHttpRequest = class { open(){} send(){} setRequestHeader(){} addEventListener(){} };
if (!globalThis.IntersectionObserver) globalThis.IntersectionObserver = class { observe(){} unobserve(){} disconnect(){} };
if (!globalThis.ResizeObserver) globalThis.ResizeObserver = class { observe(){} disconnect(){} };
if (!globalThis.matchMedia) globalThis.matchMedia = () => ({ matches: false, media: '', addEventListener(){}, removeEventListener(){}, addListener(){}, removeListener(){} });
if (!globalThis.requestAnimationFrame) globalThis.requestAnimationFrame = f => setTimeout(() => f(Date.now()), 16);
if (!globalThis.cancelAnimationFrame) globalThis.cancelAnimationFrame = () => {};
if (!globalThis.scrollTo) globalThis.scrollTo = () => {};
globalThis.addEventListener = globalThis.addEventListener || function(){};
globalThis.removeEventListener = globalThis.removeEventListener || function(){};
globalThis.dispatchEvent = globalThis.dispatchEvent || function(){ return true; };

/* ---------- network shims ---------- */
/* bash sandbox 호환용: dns 오버라이드 + geo 스텁. 일반 머신에서는 실네트워크로 동작. */
try {
  const dns = require('dns');
  const _lookup = dns.lookup;
  const GM_IP = process.env.GM_IP || '';
  if (GM_IP) {
    dns.lookup = function (host, opts, cb) {
      if (typeof host === 'string' && /(^|\.)gramsnap\.com$/i.test(host)) {
        if (typeof opts === 'function') { cb = opts; opts = {}; }
        if (opts && opts.all) return cb(null, [{ address: GM_IP, family: 4 }]);
        return cb(null, GM_IP, 4);
      }
      return _lookup.call(dns, host, opts, cb);
    };
  }
} catch {}
const _f = globalThis.fetch;
globalThis.fetch = async (u, o) => {
  const s = String(u);
  if (s.includes('get_country_code')) {
    if (process.env.GM_ONLINE === '1' && _f) {
      try { return await _f(new URL(s, GM_ORIGIN).href, o); } catch {}
    }
    return new Response('kr', { status: 200, headers: { 'content-type': 'text/plain' } });
  }
  if (_f) return _f(new URL(s, GM_ORIGIN).href, o);
  return new Response('{}', { status: 200 });
};

process.on('uncaughtException', (e) => { console.error('[uncaught] ' + String(e && e.message).slice(0, 200)); });
process.on('unhandledRejection', (e) => { console.error('[unhandledRejection] ' + String(e && (e.message || e)).slice(0, 200)); });

/* ---------- webpack boot ---------- */
const appTxt = fs.readFileSync((process.argv[2] || process.env.GM_APP), 'utf8');
const chunkTxt = fs.readFileSync((process.argv[3] || process.env.GM_CHUNK), 'utf8');
self.webpackChunk = [];
let R = null;
try { eval(appTxt); } catch (e) { console.error('[boot] app: ' + e.message); }
try { (0, eval)(chunkTxt); } // indirect eval: non-strict (igram.world chunk uses `with`)
 catch (e) { console.error('[boot] chunk: ' + e.message); }
try { self.webpackChunk.push([['__probe'], { __probe(){} }, function (w) { R = w; }]); } catch (e) { console.error('[probe] ' + e.message); }
if (!R) { console.log(JSON.stringify({ ok: false, error: 'no webpack require' })); process.exit(1); }

(async () => {
  // 서명 모듈 ID는 사이트 빌드마다 바뀜(27 → 7027 등) — 청크(54)가 등록한 모듈 중 default export를 가진 것을 탐색
  const ids = [];
  for (const e of self.webpackChunk) if (e && e[0] && e[0][0] !== '__probe' && e[1]) ids.push(...Object.keys(e[1]));
  const mods = [];
  for (const id of ids) { try { const m = R(id); if (m && 'default' in m) mods.push([id, m]); } catch {} }
  let signer = null, lastErr = null;
  const deadline = Date.now() + 20000;
  while (!signer && Date.now() < deadline) {
    for (const [id, m] of mods) {
      let d = m.default;
      if (d && typeof d.then === 'function') { try { d = await d; } catch (e) { lastErr = String(e && e.message || e); continue; } }
      if (typeof d === 'function') { signer = d; break; }
    }
    if (!signer) await new Promise(r => setTimeout(r, 300));
  }
  if (!signer) {
    console.log(JSON.stringify({ ok: false, error: 'signer never resolved: ' + (lastErr || 'no default export'), modules: ids }));
    process.exit(1);
  }
  console.log(JSON.stringify({ ok: true, ready: true }));
  if (process.argv.includes('--serve')) {
    const readline = require('readline');
    const rl = readline.createInterface({ input: process.stdin });
    for await (const line of rl) {
      if (!line.trim()) continue;
      let id = null, payload = null;
      try { const j = JSON.parse(line); id = j.id; payload = j.payload; } catch { continue; }
      try {
        const signed = await signer(payload);
        console.log(JSON.stringify({ id, ok: true, signed }));
      } catch (e) {
        console.log(JSON.stringify({ id, ok: false, error: String(e && e.message || e).slice(0, 200) }));
      }
    }
  } else {
    const input = process.env.GM_INPUT ? JSON.parse(process.env.GM_INPUT) : { username: 'instagram', maxId: '' };
    const signed = await signer(input);
    console.log(JSON.stringify({ id: 0, ok: true, signed }));
    process.exit(0);
  }
})().catch(e => { console.log(JSON.stringify({ ok: false, error: String((e && e.stack) || e).slice(0, 400) })); process.exit(1); });
