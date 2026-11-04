'use strict';
const $ = id => document.getElementById(id);
const filters = ['search', 'browser-filter', 'status-filter', 'secure-filter', 'http-filter', 'same-filter'];
let dataset = null, page = 1, filtered = [], busy = false;
const pageSize = 12;
const fmt = n => new Intl.NumberFormat('es-EC').format(n);
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function notice(text, error = false) {
  $('notice').textContent = text;
  $('notice').className = error ? 'notice error' : 'notice';
  $('notice').hidden = !text;
}
function flagLabel(value) { return value === true ? 'Sí' : value === false ? 'No' : '—'; }
function matchesFlag(value, selected) { return !selected || String(value) === selected; }
function domainKey(r) { return r.domain.toLowerCase().replace(/^\.+/, ''); }
function clearFilters() {
  filters.forEach(id => { $(id).value = ''; });
  page = 1;
}
function applyFilters() {
  if (!dataset) return;
  const search = $('search').value.trim().toLowerCase();
  filtered = dataset.cookies.filter(r =>
    (!search || `${r.domain} ${r.name}`.toLowerCase().includes(search)) &&
    (!$('browser-filter').value || r.browser === $('browser-filter').value) &&
    (!$('status-filter').value || r.status === $('status-filter').value) &&
    matchesFlag(r.secure, $('secure-filter').value) &&
    matchesFlag(r.httpOnly, $('http-filter').value) &&
    (!$('same-filter').value || r.sameSite === $('same-filter').value));
  renderSummary();
  renderTable();
}
function renderSummary() {
  const total = filtered.length;
  const secure = filtered.filter(r => r.secure === true).length;
  const knownSecure = filtered.filter(r => r.secure !== null).length;
  $('metric-total').textContent = fmt(total);
  $('metric-domains').textContent = fmt(new Set(filtered.map(domainKey)).size);
  $('metric-secure').textContent = fmt(secure);
  $('metric-expired').textContent = fmt(filtered.filter(r => r.status === 'Vencida').length);
  $('secure-detail').textContent = `${knownSecure ? Math.round(100 * secure / knownSecure) : 0}% de ${fmt(knownSecure)} con dato conocido`;
  const counts = new Map();
  filtered.forEach(r => counts.set(domainKey(r), (counts.get(domainKey(r)) || 0) + 1));
  const top = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 6);
  $('domain-chart').replaceChildren();
  if (!top.length) $('domain-chart').append(el('p', 'Sin datos para los filtros actuales.', 'subtle'));
  top.forEach(([name, count]) => {
    const row = el('div', undefined, 'bar-row');
    const label = el('span', name, 'bar-label'); label.title = name;
    const track = el('span', undefined, 'bar-track');
    const bar = el('span', undefined, 'bar-fill'); bar.style.width = `${100 * count / top[0][1]}%`;
    track.append(bar); row.append(label, track, el('strong', fmt(count))); $('domain-chart').append(row);
  });
  const attributes = [
    ['Con HttpOnly', filtered.filter(r => r.httpOnly === true).length],
    ['SameSite: Strict / Lax', filtered.filter(r => ['Strict', 'Lax'].includes(r.sameSite)).length],
    ['De sesión confirmadas', filtered.filter(r => r.session === true).length],
    ['Sesión sin determinar', filtered.filter(r => r.session === null).length],
  ];
  $('attribute-list').replaceChildren();
  attributes.forEach(([label, value]) => {
    const row = el('div'); row.append(el('dt', label), el('dd', fmt(value))); $('attribute-list').append(row);
  });
}
function renderTable() {
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize)); page = Math.min(page, pages);
  const start = (page - 1) * pageSize;
  $('cookie-rows').replaceChildren();
  filtered.slice(start, start + pageSize).forEach(r => {
    const tr = el('tr');
    const identity = el('td'); identity.append(el('strong', r.domain), el('small', `${r.name} · ${r.path}`));
    tr.append(identity, el('td', r.browser));
    for (const attribute of ['secure', 'httpOnly']) {
      const td = el('td'); td.append(el('span', flagLabel(r[attribute]), r[attribute] === true ? 'flag yes' : 'flag neutral')); tr.append(td);
    }
    tr.append(el('td', r.sameSite));
    const status = el('td'); status.append(el('span', r.status, `status ${r.status === 'Vencida' ? 'expired' : r.status === 'Sesión' ? 'session' : 'neutral'}`)); tr.append(status);
    const date = r.expires ? new Date(r.expires) : null;
    tr.append(el('td', date && !Number.isNaN(date.getTime()) ? date.toISOString().slice(0, 19).replace('T', ' ') : '—', 'date-cell'));
    $('cookie-rows').append(tr);
  });
  $('empty-state').hidden = filtered.length > 0;
  $('record-count').textContent = `${fmt(filtered.length)} de ${fmt(dataset.cookies.length)} registros · valores de cookies excluidos`;
  $('page-info').textContent = filtered.length ? `${start + 1}–${Math.min(start + pageSize, filtered.length)} de ${fmt(filtered.length)} · página ${page}/${pages}` : '0 registros';
  $('prev-page').disabled = page <= 1; $('next-page').disabled = page >= pages;
  $('export-csv').disabled = !filtered.length; $('export-json').disabled = !filtered.length;
}
function acceptDataset(data) {
  dataset = data; clearFilters();
  $('mode-label').textContent = data.mode === 'demo' ? 'MODO DEMO' : 'COPIA SQLITE';
  $('source-label').textContent = data.mode === 'demo' ? '36 cookies ficticias. Ningún dato personal.' : `${data.sources.length} copia(s) procesada(s) · metadatos únicamente`;
  $('source-detail').textContent = `Análisis: ${new Date(data.analyzedAt).toLocaleString('es-EC')} · las fechas de expiración se muestran en UTC`;
  notice(data.warnings.join(' '));
  $('provenance').replaceChildren();
  data.sources.forEach(source => {
    const box = el('div', undefined, 'source-item');
    box.append(el('strong', `${source.browser} · ${fmt(source.rows)} registros${source.truncated ? ' · muestra parcial' : ''}`));
    if (source.sha256) box.append(el('code', `SHA-256: ${source.sha256}`));
    else box.append(el('span', 'Ejemplo sintético generado para esta sesión.'));
    $('provenance').append(box);
  });
  applyFilters();
}
async function loadDemo() {
  if (busy) return;
  try {
    acceptDataset(makeDemo());
  } catch (error) { notice(error.message, true); }
}
function download(content, type, extension) {
  const blob = new Blob([content], {type}); const url = URL.createObjectURL(blob);
  const link = el('a'); link.href = url; link.download = `cookie-metadata-${dataset.mode}.${extension}`;
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function filterState() { return Object.fromEntries(filters.map(id => [id, $(id).value])); }
$('export-csv').addEventListener('click', () => {
  if (!dataset) return;
  download(CookieReports.csv(filtered), 'text/csv;charset=utf-8', 'csv');
  notice('CSV exportado: solo los registros filtrados. Revisa sus dominios y nombres antes de compartirlo.');
});
$('export-json').addEventListener('click', () => {
  if (!dataset) return;
  download(JSON.stringify({formatVersion: 1, mode: dataset.mode, analyzedAt: dataset.analyzedAt, exportedAt: new Date().toISOString(), filters: filterState(), sources: dataset.sources, warnings: dataset.warnings, count: filtered.length, cookies: CookieReports.metadata(filtered)}, null, 2), 'application/json', 'json');
  notice('JSON exportado con procedencia y filtros. No contiene valores de cookies.');
});
filters.forEach(id => $(id).addEventListener(id === 'search' ? 'input' : 'change', () => { page = 1; applyFilters(); }));
$('clear-filters').addEventListener('click', () => { clearFilters(); applyFilters(); });
$('prev-page').addEventListener('click', () => { page = Math.max(1, page - 1); renderTable(); });
$('next-page').addEventListener('click', () => { page++; renderTable(); });
$('reset-demo').addEventListener('click', loadDemo);
function view(guide) {
  $('analysis-view').hidden = guide; $('guide-view').hidden = !guide;
  for (const [id, active] of [['nav-analysis', !guide], ['nav-guide', guide]]) {
    $(id).classList.toggle('active', active);
    if (active) $(id).setAttribute('aria-current', 'page'); else $(id).removeAttribute('aria-current');
  }
}
$('nav-analysis').addEventListener('click', () => view(false));
$('nav-guide').addEventListener('click', () => view(true));

function makeDemo(){
 const now=new Date(),domains=['.tienda.example','cuenta.example','.noticias.example','video.example','metricas.example','campus.example'],names=['session_demo','preferencias','idioma','tema','carrito_demo','consentimiento'],weight=[0,0,0,0,1,1,1,2,2,3,4,5];
 const cookies=Array.from({length:36},(_,i)=>{const browser=i%3?'Chrome / Chromium':'Firefox',session=i%5===0?true:browser==='Firefox'?null:false,expires=new Date(+now+(i%7===0?-2:30+i)*86400000);return {browser,domain:domains[weight[i%12]],name:names[i%6],path:'/',secure:i%4!==0,httpOnly:i%3===0,sameSite:['Lax','Strict','None','No especificado','Desconocido'][i%5],session,status:session?'Sesión':expires<now?'Vencida':'Vigente',expires:session?null:expires.toISOString()}});
 return {mode:'demo',analyzedAt:now.toISOString(),cookies,sources:[{browser:'Datos ficticios',rows:36,truncated:false,sha256:null}],warnings:['Demo pública con datos sintéticos. Para analizar copias SQLite utiliza la versión local del repositorio.']};
}
loadDemo();
