// Sitio de documentación: carga los .md de /docs y los muestra. Sin dependencias externas salvo marked.
const NAV = [
  { title: 'Inicio', path: 'docs/README.md' },
  { title: 'Sistema', children: [
    { title: 'Diagrama Top-Level', path: 'docs/sistema/top-level.md' },
    { title: 'Funcionamiento del sistema', path: 'docs/sistema/funcionamiento.md' },
  ]},
  { title: 'Hardware', children: [
    { title: 'Recorrido de la placa', path: 'docs/hardware/README.md' },
    { title: 'Componentes principales', path: 'docs/hardware/componentes.md' },
    { title: 'Esquemático', path: 'docs/hardware/esquematico.md' },
    { title: 'Diseño de la PCB', path: 'docs/hardware/pcb.md' },
    { title: 'Alimentación', path: 'docs/hardware/alimentacion.md' },
    { title: 'Pinout', path: 'docs/hardware/pinout.md' },
    { title: 'Conectividad (USB y Bluetooth)', path: 'docs/hardware/conectividad.md' },
    { title: 'BOM completo', path: 'docs/hardware/bom.md' },
    { title: 'Archivos de diseño', path: 'docs/hardware/archivos.md' },
  ]},
  { title: 'Guía de usuario', children: [
    { title: 'Puesta en marcha', path: 'docs/guia/README.md' },
    { title: 'Programar el ESP32', path: 'docs/guia/programar.md' },
    { title: 'Firmware y plan de pruebas', path: 'docs/guia/pruebas.md' },
  ]},
  { title: 'Resultado final', path: 'docs/resultado.md' },
  { title: 'Plataforma de documentación', path: 'docs/plataforma.md' },
  { title: 'Preguntas frecuentes', path: 'docs/faq.md' },
];
const HOME = 'docs/README.md';
const $ = s => document.querySelector(s);
const flat = [];
NAV.forEach(g => g.children ? g.children.forEach(c => flat.push({ ...c, group: g.title })) : flat.push({ ...g, group: null }));

function resolve(base, rel) {
  if (/^(https?:|mailto:|#|data:)/.test(rel)) return rel;
  const parts = base.split('/').slice(0, -1);
  rel.split('/').forEach(p => { if (p === '..') parts.pop(); else if (p !== '.' && p !== '') parts.push(p); });
  return parts.join('/');
}
function slug(t) {
  return t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}
function esc(s) { return s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

function buildNav(current, heads) {
  $('#tabs').innerHTML = NAV.map(g => {
    const p = g.path || g.children[0].path;
    const on = g.path ? g.path === current : g.children.some(c => c.path === current);
    return `<a href="#${p}" class="${on ? 'on' : ''}">${esc(g.title)}</a>`;
  }).join('');
  $('#side').innerHTML = NAV.map(g => {
    if (!g.children) return `<a class="lvl1 ${g.path === current ? 'on' : ''}" href="#${g.path}">${esc(g.title)}</a>`;
    return `<div class="grp">${esc(g.title)}</div>` + g.children.map(c => {
      let h = `<a class="lvl2 ${c.path === current ? 'on' : ''}" href="#${c.path}">${esc(c.title)}</a>`;
      if (c.path === current && heads.length) h += heads.map(x => `<a class="lvl3" href="#${current}?${x.id}">${esc(x.text)}</a>`).join('');
      return h;
    }).join('');
  }).join('');
}

async function load() {
  let [path, anchor] = decodeURIComponent(location.hash.slice(1)).split('?');
  if (!path) path = HOME;
  const el = $('#content');
  let md;
  try {
    const r = await fetch(path);
    if (!r.ok) throw new Error(r.status);
    md = await r.text();
  } catch (e) {
    el.innerHTML = `<h1>No se encontró la página</h1><p>No se pudo abrir <code>${esc(path)}</code>. <a href="#${HOME}">Volver al inicio</a>.</p>`;
    buildNav(path, []);
    return;
  }
  el.innerHTML = marked.parse(md, { gfm: true });
  // rutas relativas al .md
  el.querySelectorAll('img').forEach(i => { i.src = resolve(path, i.getAttribute('src')); i.loading = 'lazy'; });
  el.querySelectorAll('a').forEach(a => {
    const h = a.getAttribute('href') || '';
    if (/^(https?:|mailto:)/.test(h)) { a.target = '_blank'; a.rel = 'noopener'; return; }
    if (h.startsWith('#')) { a.href = `#${path}?${h.slice(1)}`; return; }
    const [file, hash] = h.split('#');
    const full = resolve(path, file);
    if (full.endsWith('.md')) a.href = `#${full}${hash ? '?' + hash : ''}`;
    else { a.href = full; if (!/\.(png|jpg|svg)$/.test(full)) a.setAttribute('download', ''); }
  });
  // tablas con scroll, figuras con pie
  el.querySelectorAll('table').forEach(t => { const w = document.createElement('div'); w.className = 'tablewrap'; t.replaceWith(w); w.appendChild(t); });
  el.querySelectorAll('p > img:only-child').forEach(i => {
    const p = i.parentElement, f = document.createElement('figure');
    f.appendChild(i);
    if (i.title) { const c = document.createElement('figcaption'); c.textContent = i.title; f.appendChild(c); i.removeAttribute('title'); }
    p.replaceWith(f);
    i.addEventListener('click', () => { const lb = $('#lightbox'); lb.querySelector('img').src = i.src; lb.hidden = false; });
  });
  const heads = [...el.querySelectorAll('h2')].map(h => { h.id = slug(h.textContent); return { id: h.id, text: h.textContent }; });
  el.querySelectorAll('h3').forEach(h => { h.id = slug(h.textContent); });
  const item = flat.find(f => f.path === path);
  const h1 = el.querySelector('h1');
  document.title = `${h1 ? h1.textContent : 'Documentación'} · PCB Autonomo_V2`;
  $('#crumbs').textContent = item ? [item.group, item.title].filter(Boolean).join(' › ') : '';
  buildNav(path, heads);
  $('#side').classList.remove('open');
  if (anchor && document.getElementById(anchor)) document.getElementById(anchor).scrollIntoView();
  else window.scrollTo(0, 0);
}
window.addEventListener('hashchange', load);
$('#menu').addEventListener('click', () => $('#side').classList.toggle('open'));
$('#lightbox').addEventListener('click', () => { $('#lightbox').hidden = true; });
document.addEventListener('keydown', e => { if (e.key === 'Escape') $('#lightbox').hidden = true; });
load();
