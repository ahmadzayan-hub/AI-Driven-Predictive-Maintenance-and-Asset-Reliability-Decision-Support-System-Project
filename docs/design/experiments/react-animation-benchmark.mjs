// Isolated build experiment. Run with a prepared scratch directory as argv[2].
// No imports or dependencies are added to the production frontend.
import { mkdir, readFile, writeFile, readdir } from 'node:fs/promises'
import { resolve, join } from 'node:path'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'
import { gzipSync } from 'node:zlib'
import { createHash } from 'node:crypto'

if (!process.argv[2]) throw new Error('Supply an isolated scratch directory with installed dependencies.')
const root = resolve(process.argv[2])
const require = createRequire(join(root, 'package.json'))
const { build } = await import(pathToFileURL(require.resolve('vite')).href)
const expected = { react: '19.2.8', 'react-dom': '19.2.8', '@xyflow/react': '12.12.0', motion: '14.4.0', vite: '8.2.1' }
const versions = {}
for (const [name, version] of Object.entries(expected)) {
  versions[name] = JSON.parse(await readFile(join(root, 'node_modules', name, 'package.json'), 'utf8')).version
  if (versions[name] !== version) throw new Error(`Expected ${name}@${version}, found ${versions[name]}`)
}

const common = `
import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Canvas, Details } from './variant.js';
import './style.css';
const h = React.createElement;
export const labels = ['Hermes', 'Data / البيانات', 'Analytics / التحليلات', 'Assurance / التحقق', 'Publish / النشر'];
export function NativeCanvas({ selected, active, event, onSelect }) {
  return h('div', { className: 'native-canvas' },
    h('svg', { viewBox: '0 0 800 260', 'aria-hidden': true },
      h('path', { d: 'M400 70V115M100 115H700M100 115V180M300 115V180M500 115V180M700 115V180' }),
      h('path', { key: event, className: event ? 'signal' : '', d: 'M400 70V115H'+(100+200*(active-1))+'V180' })),
    labels.map((label, i) => h('button', { key: i, className: 'agent agent-'+i, 'aria-pressed': selected===i, onClick: () => onSelect(i) }, label)));
}
function App() {
  const [selected, setSelected] = useState(0);
  const [active, setActive] = useState(1);
  const [event, setEvent] = useState(0);
  const [paused, setPaused] = useState(false);
  return h('main', { 'data-paused': paused },
    h('header', null, h('p', null, 'REACT TECHNOLOGY STUDY / دراسة تقنية'), h('h1', null, document.title),
      h('p', null, 'Synthetic comparison only. No API, real agent messages or approvals. / نموذج تجريبي فقط.')),
    h('div', { className: 'toolbar' },
      h('button', { disabled: paused, onClick: () => { setActive(active%4+1); setEvent(event+1); } }, 'Simulate handoff / محاكاة انتقال'),
      h('button', { 'aria-pressed': paused, onClick: () => setPaused(!paused) }, paused ? 'Resume demo / متابعة العرض' : 'Pause demo / إيقاف العرض'),
      h('span', { role: 'status' }, 'Simulated destination: '+labels[active])),
    h('section', { className: 'canvas', 'aria-label': 'Synthetic agent connections' }, h(Canvas, { selected, active, event, onSelect: setSelected })),
    h(Details, { selected, paused }, h('h2', null, labels[selected]), h('p', null, 'Selected workflow node. Details are synthetic. / تفاصيل تجريبية للعقدة المحددة.')),
    h('p', null, 'Selection does not change workflow order. / الاختيار لا يغير ترتيب العمل.'));
}
createRoot(document.getElementById('root')).render(h(App));
`
const styles = `
:root { font: 16px system-ui,sans-serif; color: #18313b; background:#edf3f5; }
* { box-sizing:border-box; } body { margin:0; } main { max-width:1100px; margin:32px auto; padding:24px; }
header>p:first-child { color:#47616c; font-size:12px; letter-spacing:.1em; } h1 { font-size:28px; }
button { min-height:44px; padding:10px 16px; background:white; border:1px solid #557883; border-radius:10px; color:inherit; font:inherit; cursor:pointer; }
button[aria-pressed=true] { background:#d2f2ed; border-color:#00685d; } button:focus-visible { outline:3px solid #00685d; outline-offset:3px; }
.toolbar { display:flex; flex-wrap:wrap; align-items:center; gap:12px; margin:20px 0; } .toolbar span { flex-basis:100%; }
.canvas { height:360px; border:1px solid #99b1ba; border-radius:16px; background:white; overflow:hidden; }
.native-canvas { position:relative; height:100%; } .native-canvas svg { width:100%; height:100%; fill:none; stroke:#829da8; stroke-width:1.5; }
.native-canvas .agent { position:absolute; transform:translate(-50%,-50%); width:19%; font-size:14px; }
.agent-0 { left:50%; top:23%; } .agent-1 { left:12.5%; top:72%; } .agent-2 { left:37.5%; top:72%; } .agent-3 { left:62.5%; top:72%; } .agent-4 { left:87.5%; top:72%; }
.signal { stroke:#00685d; stroke-width:3; stroke-dasharray:6 10; animation:signal 900ms ease-out 1; }
.react-flow__edge.signal path { stroke:#00685d; stroke-width:3; stroke-dasharray:6 10; }
.details { margin-top:20px; padding:20px; border:1px solid #99b1ba; border-radius:14px; background:white; }
.details h2 { margin-top:0; } .react-flow__node { font:14px system-ui,sans-serif; color:#18313b; border-color:#557883; }
@keyframes signal { from { stroke-dashoffset:32; } to { stroke-dashoffset:0; } }
[data-paused=true] * { animation:none !important; } @media(prefers-reduced-motion:reduce) { * { animation:none !important; transition:none !important; } }
`
const native = `
import React from 'react'; import { NativeCanvas } from './app.js';
export const Canvas = NativeCanvas;
export function Details({children}) { return React.createElement('section', {className:'details'}, children); }
`
const variants = {
  native: { title: 'React + SVG / CSS', source: native },
  'react-flow': { title: 'React Flow + CSS', source: `
import React from 'react';
import { ReactFlow, Controls, Background } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { labels } from './app.js';
export function Canvas({selected,active,event,onSelect}) {
  const nodes=labels.map((label,i)=>({id:String(i), position:i ? {x:200*(i-1), y:200}:{x:300,y:20}, data:{label}, selected:selected===i}));
  const edges=labels.slice(1).map((label,i)=>({id:'edge-'+i,source:'0',target:String(i+1), className: event && active===i+1 ? 'signal' : ''}));
  return React.createElement(ReactFlow,{nodes,edges,fitView:true,nodesDraggable:false,nodesConnectable:false,edgesReconnectable:false,deleteKeyCode:null,onNodeClick:(_,node)=>onSelect(Number(node.id)),nodesFocusable:true,edgesFocusable:true},React.createElement(Controls,{showInteractive:false}),React.createElement(Background));
}
export function Details({children}) { return React.createElement('section',{className:'details'},children); }
` },
  'motion-mini': { title: 'React SVG + Motion mini', source: `
import React,{useEffect} from 'react'; import {useAnimate} from 'motion/react-mini'; import {NativeCanvas} from './app.js';
export const Canvas=NativeCanvas;
export function Details({selected,paused,children}) {
  const [scope,animate]=useAnimate();
  useEffect(()=>{ if(paused || matchMedia('(prefers-reduced-motion: reduce)').matches)return; const playback=animate(scope.current,{opacity:[0.6,1]},{duration:0.22}); return ()=>playback.stop(); },[selected,paused,animate,scope]);
  return React.createElement('section',{ref:scope,className:'details'},children);
}
` },
  'motion-lazy': { title: 'React SVG + LazyMotion', source: `
import React from 'react'; import {LazyMotion,domAnimation,MotionConfig,useReducedMotion} from 'motion/react'; import * as m from 'motion/react-m'; import {NativeCanvas} from './app.js';
export const Canvas=NativeCanvas;
export function Details({selected,paused,children}) {
  const reduced=useReducedMotion() || paused;
  return React.createElement(LazyMotion,{features:domAnimation},React.createElement(MotionConfig,{reducedMotion:'user'},React.createElement(m.section,{key:selected,className:'details',initial:reduced ? false : {opacity:0.6},animate:{opacity:1},transition:{duration:reduced ? 0 : 0.22}},children)));
}
` },
}
const result = { date: '2026-10-21', node: process.version, versions, units: 'decimal KB; sum of individual gzip level-9 JS/CSS assets', variants: {} }
for (const [name, variant] of Object.entries(variants)) {
  const folder = join(root, 'entries', name)
  await mkdir(folder, { recursive: true })
  await writeFile(join(folder, 'index.html'), `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${variant.title}</title></head><body><div id="root"></div><script type="module" src="/app.js"></script></body></html>`)
  await writeFile(join(folder, 'app.js'), common)
  await writeFile(join(folder, 'style.css'), styles)
  await writeFile(join(folder, 'variant.js'), variant.source)
  await build({ configFile: false, root: folder, base: './', logLevel: 'warn', build: { outDir: join(root, 'dist', name), emptyOutDir: true, target: 'es2022', minify: true, sourcemap: false } })
  const files = await readdir(join(root, 'dist', name, 'assets'))
  const sizes = { js: 0, css: 0 }
  for (const file of files) {
    const kind = file.endsWith('.js') ? 'js' : file.endsWith('.css') ? 'css' : null
    if (kind) sizes[kind] += gzipSync(await readFile(join(root, 'dist', name, 'assets', file)), { level: 9 }).length / 1000
  }
  result.variants[name] = { ...sizes, jsDelta: sizes.js - (result.variants.native?.js ?? sizes.js), cssDelta: sizes.css - (result.variants.native?.css ?? sizes.css) }
}
result.lockSha256 = createHash('sha256').update(await readFile(join(root, 'package-lock.json'))).digest('hex')
await writeFile(join(root, 'results.json'), JSON.stringify(result, null, 2)+'\n')
console.log(JSON.stringify(result, null, 2))
