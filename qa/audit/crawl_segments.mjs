// Crawl SEGMENTS : galerie (5 presets), compteurs vs réel, builder — filtres du registry
// UN PAR UN, valeurs limites, combinaisons, tris, filtres grisés, exports CSV (RGPD),
// duplication admin TEST_AUDIT_, inclure_inactifs + réactivation PUT, publipostage.
//   node qa/audit/crawl_segments.mjs      (app :8000, LABUSE_DEV_MODE=1)
import { readFileSync } from 'node:fs';
import { BASE, boot, bilan, chromium, collecte, setCtx, shot, state, sauveJson, pushAnomalie } from './harness.mjs';

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
const page = await ctx.newPage();
collecte(page);
state.viewport = '1440';
const constats = [];
const note = (vue, n) => { constats.push({ vue, note: n }); console.log(` · ${vue} — ${n}`); };

await boot(page);
setCtx('segments', 'ouverture vue');
await page.evaluate(() => window.__labuse.setView('segments'));
await page.waitForTimeout(2500);

// ── B-SEG-1 : galerie = exactement 5 presets, compteurs affichés ──
const presets = await page.$$eval('[data-seg-preset]', (els) => els.map((e) => ({
  slug: e.getAttribute('data-seg-preset'),
  count: e.querySelector('[data-seg-preset-count]')?.textContent?.trim() ?? null,
})));
note('segments:galerie', `${presets.length} presets : ${presets.map((p) => `${p.slug}=${p.count}`).join(', ')}`);
if (presets.length !== 5) pushAnomalie('seg.galerie', `attendu 5 presets actifs, vu ${presets.length}`);
await shot(page, 'seg_galerie');

// ── B-SEG-2 : chaque preset — ouverture, compteur galerie vs count réel, export CSV ──
const attendreCount = async () => {
  await page.waitForFunction(() => {
    const el = document.querySelector('[data-seg-count]');
    return el && el.textContent.trim() !== '—' && el.textContent.trim() !== '';
  }, null, { timeout: 20000 }).catch(() => pushAnomalie('seg.count', 'compteur jamais rempli'));
  await page.waitForFunction(() => !document.body.innerText.includes('calcul…'), null, { timeout: 20000 }).catch(() => {});
  const t = await page.locator('[data-seg-count]').textContent();
  return parseInt((t || '').replace(/[^\d]/g, ''), 10);
};

const exportsRGPD = [];
for (const p of presets) {
  setCtx(`segments:${p.slug}`, 'ouverture preset');
  await page.locator(`[data-seg-preset="${p.slug}"] [data-seg-preset-open]`).click();
  const live = await attendreCount();
  const galerie = parseInt((p.count || '').replace(/[^\d]/g, ''), 10);
  if (Number.isFinite(galerie) && Number.isFinite(live) && galerie !== live)
    note(`segments:${p.slug}`, `compteur galerie ${galerie} ≠ résultat réel ${live}`);
  await shot(page, `seg_${p.slug}`);

  // export CSV → contenu vérifié (en-têtes FR, adresses, ZÉRO nom de personne physique)
  setCtx(`segments:${p.slug}`, 'export CSV');
  const dl = page.waitForEvent('download', { timeout: 25000 }).catch(() => null);
  await page.locator('[data-seg-export]').click();
  const d = await dl;
  if (!d) { pushAnomalie('seg.export', `${p.slug} : aucun téléchargement reçu`); }
  else {
    const path = await d.path();
    const csv = readFileSync(path, 'utf-8');
    const lignes = csv.split('\n').filter(Boolean);
    const head = lignes[0] || '';
    const verdictRGPD = {
      slug: p.slug, lignes: lignes.length - 1, entetes: head,
      entetes_fr: /Adresse|Commune|Parcelle|Surface/i.test(head),
      colonne_nominative: /propri[ée]taire|\bnom\b|denomination/i.test(head),
      civilite_dans_contenu: /(^|[;,])\s*(M\.|Mme|Monsieur|Madame)\s+[A-ZÉÈ]/m.test(csv),
      ref_watermark: /(^|[;,])ref($|[;,\r])/m.test(head),
    };
    exportsRGPD.push(verdictRGPD);
    if (verdictRGPD.colonne_nominative || verdictRGPD.civilite_dans_contenu)
      pushAnomalie('seg.rgpd', `${p.slug} : export contient du nominatif — ${head}`);
  }
  await page.waitForTimeout(600);
  setCtx(`segments:${p.slug}`, 'retour galerie');
  await page.locator('[data-seg-retour]').click();
  await page.waitForTimeout(800);
}
sauveJson('seg_exports_rgpd', exportsRGPD);

// ── B-SEG-3 : builder — TOUS les filtres du registry UN PAR UN (preset 1 vidé) ──
setCtx('segments:builder', 'ouverture + purge des filtres du preset');
await page.locator(`[data-seg-preset="${presets[0].slug}"] [data-seg-preset-open]`).click();
await attendreCount();
// retirer tous les filtres existants (l'✕ de chaque row)
for (let g = 0; g < 12; g++) {
  const x = page.locator('[data-seg-filtre] button[title^="Retirer"]').first();
  if (!(await x.isVisible().catch(() => false))) break;
  await x.click();
  await page.waitForTimeout(250);
}
const base = await attendreCount();
note('segments:builder', `baseline sans filtre : ${base} parcelles`);

const options = await page.$$eval('select[data-seg-ajout] option', (os) => os
  .filter((o) => o.value)
  .map((o) => ({ cle: o.value, libelle: o.textContent.trim(), off: o.disabled })));
note('segments:builder', `${options.length} filtres au registre, dont ${options.filter((o) => o.off).length} grisés`);
const grises = options.filter((o) => o.off);
for (const g of grises) {
  if (!/prochainement.*mandat|à venir/i.test(g.libelle))
    pushAnomalie('seg.grise', `${g.cle} grisé sans mention de mandat : « ${g.libelle} »`);
}

const parFiltre = [];
for (const o of options.filter((x) => !x.off)) {
  setCtx('segments:builder', `filtre ${o.cle}`);
  await page.selectOption('select[data-seg-ajout]', o.cle);
  await page.waitForTimeout(350);
  const row = page.locator('[data-seg-filtre]').last();
  // renseigner selon le type
  const minInput = row.locator('input[placeholder="min"]');
  const enumBtns = row.locator('button:not([title])');
  if (await minInput.isVisible().catch(() => false)) {
    await minInput.fill('1');
  } else if ((await enumBtns.count()) > 2) {
    await enumBtns.nth(2).click().catch(() => {});   // 1re valeur enum (après oui/non éventuels)
  } // bool : value=true posée à l'ajout
  await page.waitForTimeout(900);
  const n = await attendreCount();
  parFiltre.push({ cle: o.cle, count: n, base });
  if (!Number.isFinite(n)) pushAnomalie('seg.filtre', `${o.cle} : compteur illisible après activation`);
  // désactiver
  await row.locator('button[title^="Retirer"]').click().catch(async () => {
    await page.locator('[data-seg-filtre] button[title^="Retirer"]').last().click().catch(() => pushAnomalie('seg.filtre', `${o.cle} : impossible de retirer`));
  });
  await page.waitForTimeout(400);
}
sauveJson('seg_filtres_un_par_un', parFiltre);
note('segments:builder', `${parFiltre.length} filtres exercés un par un`);

// ── B-SEG-4 : valeurs limites sur un range (vide/0/négatif/énorme/spéciaux) ──
setCtx('segments:builder', 'valeurs limites surface');
const rangeCle = options.find((x) => !x.off && /surface/i.test(x.cle))?.cle || options.find((x) => !x.off)?.cle;
await page.selectOption('select[data-seg-ajout]', rangeCle);
await page.waitForTimeout(300);
const row = page.locator('[data-seg-filtre]').last();
const lim = [];
for (const v of ['0', '-50', '999999999', '1e3']) {
  await row.locator('input[placeholder="min"]').fill(v).catch(() => {});
  await page.waitForTimeout(900);
  lim.push({ v, count: await attendreCount() });
}
sauveJson('seg_valeurs_limites', lim);
note('segments:builder', `limites : ${lim.map((l) => `${l.v}→${l.count}`).join(' ; ')}`);
await row.locator('button[title^="Retirer"]').click().catch(() => {});

// ── B-SEG-5 : combinaison de 3 filtres croisés ──
setCtx('segments:builder', 'combo 3 filtres');
const troisCles = options.filter((x) => !x.off).slice(0, 3).map((x) => x.cle);
const counts1 = [];
for (const cle of troisCles) {
  await page.selectOption('select[data-seg-ajout]', cle);
  await page.waitForTimeout(300);
  const r = page.locator('[data-seg-filtre]').last();
  const mi = r.locator('input[placeholder="min"]');
  if (await mi.isVisible().catch(() => false)) await mi.fill('1');
  else { const eb = r.locator('button:not([title])'); if ((await eb.count()) > 2) await eb.nth(2).click().catch(() => {}); }
  await page.waitForTimeout(800);
  counts1.push(await attendreCount());
}
const combo = counts1[counts1.length - 1];
if (Number.isFinite(combo) && counts1.some((c) => combo > c))
  pushAnomalie('seg.combo', `le combo (${combo}) dépasse un de ses filtres seuls (${counts1.join(',')})`);
note('segments:builder', `combo 3 filtres : ${counts1.join(' → ')}`);
await shot(page, 'seg_combo3');

// ── B-SEG-6 : tris ──
setCtx('segments:builder', 'tris');
const tris = await page.$$eval('select:not([data-seg-ajout])', (sels) => {
  const s = sels.find((x) => x.closest('div')?.textContent?.includes('Tri')) || sels[sels.length - 1];
  return Array.from(s.options).map((o) => o.value).filter(Boolean);
});
for (const t of tris) {
  const sel = page.locator('select').filter({ has: page.locator(`option[value="${t}"]`) }).last();
  await sel.selectOption(t).catch(() => pushAnomalie('seg.tri', `tri ${t} insélectionnable`));
  await page.waitForTimeout(700);
  await attendreCount();
}
note('segments:builder', `${tris.length} tris exercés`);

// ── B-SEG-7 : duplication admin → TEST_AUDIT_, puis inactifs + PUT + nettoyage (API) ──
setCtx('segments:builder', 'duplication TEST_AUDIT_');
const SLUG = 'test-audit-preset';
page.on('dialog', (d) => d.accept(d.message().includes('Slug') ? SLUG : 'TEST_AUDIT_ preset (à nettoyer)'));
await page.locator('[data-seg-dupliquer]').click();
await page.waitForTimeout(1500);
const toast = await page.locator('[data-toast]').textContent().catch(() => '');
note('segments:duplication', `toast : ${toast || '(aucun)'}`);

const api = ctx.request;
const inactifs = await (await api.get('http://127.0.0.1:8000/segments?inclure_inactifs=true')).json();
const tousSlugs = (inactifs.presets ?? []).map((p) => p.slug);
const nInactifs = (inactifs.presets ?? []).filter((p) => p.actif === false).length;
note('segments:inactifs', `inclure_inactifs=true → ${tousSlugs.length} presets dont ${nInactifs} inactifs ; TEST présent=${tousSlugs.includes(SLUG)}`);
if (!tousSlugs.includes(SLUG)) pushAnomalie('seg.dup', 'preset TEST_AUDIT_ absent après duplication');
else {
  // désactivation puis RÉACTIVATION PUT (le flux du mandat), sur le preset TEST uniquement
  const put1 = await api.put(`http://127.0.0.1:8000/segments/presets/${SLUG}`, { data: { actif: false } });
  const put2 = await api.put(`http://127.0.0.1:8000/segments/presets/${SLUG}`, { data: { actif: true } });
  const apres = await (await api.get('http://127.0.0.1:8000/segments')).json();
  const revenu = (apres.presets ?? []).some((p) => p.slug === SLUG);
  note('segments:reactivation', `PUT actif=false→${put1.status()} puis true→${put2.status()} ; visible dans la galerie=${revenu}`);
  if (!revenu) pushAnomalie('seg.put', 'preset TEST réactivé mais absent de la galerie');
  // nettoyage
  const del = await api.delete(`http://127.0.0.1:8000/segments/presets/${SLUG}`);
  note('segments:nettoyage', `DELETE ${SLUG} → ${del.status()}`);
}

// ── B-SEG-8 : publipostage (ZIP) sur le 1er preset ──
setCtx('segments:builder', 'publipostage');
const dl2 = page.waitForEvent('download', { timeout: 30000 }).catch(() => null);
await page.locator('[data-seg-publipostage]').click();
const z = await dl2;
note('segments:publipostage', z ? `ZIP reçu : ${z.suggestedFilename()}` : 'AUCUN ZIP reçu');
if (!z) pushAnomalie('seg.publipostage', 'aucun téléchargement publipostage');
else {
  const path = await z.path();
  const { execSync } = await import('node:child_process');
  const liste = execSync(`unzip -l "${path}"`).toString();
  note('segments:publipostage', `contenu : ${liste.split('\n').slice(3, 8).map((l) => l.trim().split(/\s+/).pop()).join(' · ')}`);
}

sauveJson('crawl_segments_constats', constats);
bilan('crawl_segments');
await browser.close();
