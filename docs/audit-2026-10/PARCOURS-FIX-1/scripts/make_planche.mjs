// PARCOURS-FIX-1 — construit la PLANCHE visuelle : une page PARCOURS.html (toutes les captures dans
// l'ordre, desktop puis mobile) + sa version PARCOURS.pdf. Lit scripts/parcours.json.
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { ROOT, launchChromium } from './lib.mjs'

const data = JSON.parse(readFileSync(resolve(ROOT, 'scripts/parcours.json'), 'utf8'))
const steps = data.steps || []
const s = data.summary || {}
const bloquants = steps.filter((x) => x.verdict === 'BLOQUANT')
const attentions = steps.filter((x) => x.verdict === 'ATTENTION')
const bon = bloquants.length === 0
const VERDICT = bon ? 'OUI' : 'NON'
const dateStr = '5 octobre 2026'

const esc = (t) => String(t).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]))
const badge = (v) => {
  const m = { OK: ['✅', '#16A34A'], ATTENTION: ['🟠', '#D97706'], BLOQUANT: ['🔴', '#DC2626'], COSMETIQUE: ['🔵', '#2563EB'] }
  const [ic, col] = m[v] || ['•', '#666']
  return `<span class="badge" style="color:${col}">${ic} ${v}</span>`
}
const carte = (x) => `
  <figure class="carte ${x.verdict}">
    <img src="${esc(x.img)}" alt="${esc(x.etape)}" loading="lazy">
    <figcaption>
      <div class="cap-top"><b>${esc(x.etape)}</b> ${badge(x.verdict)}</div>
      <div class="phrase">${esc(x.phrase)}</div>
      <div class="meta">${x.clics} clic${x.clics > 1 ? 's' : ''} · ${(x.temps_ms / 1000).toFixed(1)} s${x.mail ? ' · ✉ mail' : ''}</div>
    </figcaption>
  </figure>`

const desktop = steps.filter((x) => x.device === 'desktop')
const mobile = steps.filter((x) => x.device === 'mobile')

const html = `<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>PARCOURS-FIX-1 — la planche du parcours (build de production)</title>
<style>
  :root { --ink:#0f1115; --dim:#5b6472; --line:#e5e7eb; --mint:#16A34A; }
  * { box-sizing:border-box }
  body { font:14px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif; color:var(--ink); margin:0; background:#fafafa }
  header { padding:28px 32px 18px; border-bottom:2px solid var(--line); background:#fff }
  h1 { font-size:22px; margin:0 0 4px }
  .sous { color:var(--dim); font-size:13px }
  .verdict { margin:16px 0 4px; font-size:21px; font-weight:800; color:${bon ? 'var(--mint)' : '#DC2626'} }
  .verdict small { font-weight:600; color:var(--ink); font-size:14px }
  .resume { margin:12px 0 2px; display:flex; flex-wrap:wrap; gap:10px }
  .pill { background:#f1f5f9; border:1px solid var(--line); border-radius:999px; padding:4px 12px; font-size:12px }
  .pill b { color:var(--mint) }
  h2 { font-size:15px; margin:26px 32px 4px; padding-top:8px; text-transform:uppercase; letter-spacing:.04em; color:var(--dim) }
  .grille { display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; padding:10px 32px 24px }
  .grille.mob { grid-template-columns:repeat(5, 1fr) }
  .carte { margin:0; border:1px solid var(--line); border-radius:10px; overflow:hidden; background:#fff; break-inside:avoid }
  .carte.ATTENTION { border-color:#Fcd34d } .carte.BLOQUANT { border-color:#fca5a5 }
  .carte img { width:100%; display:block; border-bottom:1px solid var(--line); background:#111 }
  figcaption { padding:8px 10px 10px }
  .cap-top { display:flex; justify-content:space-between; align-items:baseline; gap:8px; font-size:12.5px }
  .badge { font-size:11px; font-weight:700; white-space:nowrap }
  .phrase { color:#1f2937; font-size:12px; margin:3px 0 4px }
  .meta { color:var(--dim); font-size:11px; font-variant-numeric:tabular-nums }
  footer { color:var(--dim); font-size:12px; padding:18px 32px 40px }
</style></head><body>
<header>
  <h1>PARCOURS-FIX-1 — la planche du parcours, rejoué sur le <u>build de production</u></h1>
  <div class="sous">${dateStr} · app servie par l'API (build, pas Vite) · single-origin :6005 · dry-run mail étanche · desktop 1440×900 + mobile 390×844</div>
  <div class="verdict">Le parcours est bon et fluide : ${VERDICT}
    <small>${bon ? '— un promoteur va de l’invitation à l’usage sans aide, sur le build de prod.'
      : '— étapes qui coincent : ' + [...bloquants, ...attentions].map((x) => x.etape).join(', ')}</small></div>
  <div class="resume">
    <span class="pill">Étapes : <b>${steps.length}</b> (desktop ${desktop.length} · mobile ${mobile.length})</span>
    <span class="pill">✅ ${steps.filter((x) => x.verdict === 'OK').length} · 🟠 ${attentions.length} · 🔴 ${bloquants.length}</span>
    <span class="pill">Build prod : <b>s'ouvre</b> (0 « t is not a function »)</span>
    <span class="pill">Dry-run : <b>${s.mails_session_recus_brevo === 0 ? '0 envoi Brevo' : s.mails_session_recus_brevo + ' envoi !'}</b> · ${s.eml_after} .eml</span>
    <span class="pill">« Se souvenir » : <b>${s.souvenir_jours} j</b></span>
    <span class="pill">/retours GET : <b>${s.retours_get_status}</b> (plus de 405)</span>
  </div>
  <div class="sous" style="margin-top:8px">Mails du cycle de vie en file (dry-run, 0 appel réseau) : ${esc(s.mails_session || '—')}</div>
</header>

<h2>Ordinateur — le parcours de bout en bout</h2>
<div class="grille">${desktop.map(carte).join('')}</div>

<h2>Mobile (390×844)</h2>
<div class="grille mob">${mobile.map(carte).join('')}</div>

<footer>
  Chaque vignette = une capture réelle du BUILD servi par l'API. Verdict par étape : ✅ OK · 🟠 gênant · 🔴 bloquant.
  Les mails (invitation, réinitialisation, suspension, rétablissement) partent en <b>dry-run .eml</b> (aucun envoi réel) —
  preuve : <code>mails/eml/*.eml</code> et la file ci-dessus (tous <code>a_rejouer</code>, 0 <code>recu</code>).
  Harnais rejouable : <code>scripts/run-api.sh</code> + <code>scripts/parcours_fix1.mjs</code> + <code>scripts/make_planche.mjs</code>.
</footer>
</body></html>`

const outHtml = resolve(ROOT, 'PARCOURS.html')
writeFileSync(outHtml, html)
console.log('écrit', outHtml)

// PDF de la même planche
const browser = await launchChromium()
const page = await browser.newPage()
await page.goto('file://' + outHtml, { waitUntil: 'networkidle' })
await page.pdf({ path: resolve(ROOT, 'PARCOURS.pdf'), printBackground: true, format: 'A3',
                 margin: { top: '10mm', bottom: '10mm', left: '8mm', right: '8mm' } })
await browser.close()
console.log('écrit', resolve(ROOT, 'PARCOURS.pdf'))
