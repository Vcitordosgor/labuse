// Crawl CARTE + FICHE : couches, verdict, liseré Brûlantes, clic parcelle → bonne fiche,
// omnibox, « Pourquoi ce score » (cohérence points/total + liens BODACC), PDF fiche,
// pré-dossier PC, états limites (offline / lent / commune sans résultats).
//   node qa/audit/crawl_carte_fiche.mjs
import { BASE, boot, bilan, chromium, collecte, setCtx, shot, state, sauveJson, pushAnomalie } from './harness.mjs';

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
const page = await ctx.newPage();
collecte(page);
state.viewport = '1440';
const constats = [];
const note = (vue, n) => { constats.push({ vue, note: n }); console.log(` · ${vue} — ${n}`); };

await boot(page);

// ── C-1 : les 9 couches, une par une (toggle ON puis OFF) ──
setCtx('carte', 'toggle couches');
const couches = await page.$$eval('[data-hint-couche]', (els) => els.map((e) => e.getAttribute('data-hint-couche')));
note('carte:couches', `${couches.length} couches : ${couches.join(', ')}`);
for (const c of couches) {
  setCtx('carte', `couche ${c}`);
  const el = page.locator(`[data-hint-couche="${c}"]`);
  await el.click().catch(() => pushAnomalie('carte.couche', `${c} : inclickable`));
  await page.waitForTimeout(700);
  await el.click().catch(() => {});
  await page.waitForTimeout(300);
}
await shot(page, 'carte_couches');

// ── C-2 : verdict ON + liseré Brûlantes ──
setCtx('carte', 'verdict ON');
await page.evaluate(() => window.__labuse.setVerdict(true));
await page.waitForTimeout(2000);
const nbResultats = await page.locator('[data-results-scroll] a, [data-results-scroll] button, [data-results-scroll] [role="button"]').count();
note('carte:verdict', `liste résultats : ${nbResultats} éléments interactifs`);
await shot(page, 'carte_verdict');

// ── C-3 : clic parcelle sur la carte → la BONNE fiche ──
setCtx('carte', 'clic parcelle (flyTo puis clic centre)');
await page.evaluate(() => window.__labuse.setFlyTo({ center: [55.424918, -21.242211], zoom: 17.5 }));
await page.waitForTimeout(3500);
const canvas = page.locator('canvas').first();
const bb = await canvas.boundingBox();
await page.mouse.click(bb.x + bb.width / 2, bb.y + bb.height / 2);
await page.waitForTimeout(2500);
const iduOuvert = await page.evaluate(() => document.body.innerText.match(/97\d{3}000?[0-9A-Z]{6,9}/)?.[0] ?? null);
note('carte:clic-parcelle', `fiche ouverte : ${iduOuvert} (attendu 97414000CV0907 ou voisine immédiate)`);
if (!iduOuvert) pushAnomalie('carte.clic', 'clic au centre : aucune fiche ouverte');
await shot(page, 'carte_clic_fiche');

// ── C-4 : fiche brûlante — « Pourquoi ce score » : cohérence points vs total + BODACC ──
setCtx('fiche', 'pourquoi ce score');
await page.evaluate(() => window.__labuse.select('97414000CV0907'));
await page.waitForTimeout(2500);
const sv = page.locator('[data-score-v]');
await sv.locator('button').first().click().catch(() => {});   // déplier
await page.waitForTimeout(800);
const svTxt = (await sv.textContent().catch(() => '')) || '';
const total = parseInt(svTxt.match(/(\d+)\s*\/\s*100/)?.[1] ?? svTxt.match(/\b(\d+)\b/)?.[1], 10);
const points = [...svTxt.matchAll(/\+\s?(\d+)/g)].map((m) => +m[1]);
const somme = points.reduce((a, b) => a + b, 0);
note('fiche:score-v', `total affiché=${total} ; points listés=[${points.join(',')}] somme=${somme} (attendu total 77 = somme si plafonds non tronqués)`);
if (Number.isFinite(total) && points.length && somme !== total)
  note('fiche:score-v', `⚠ somme (${somme}) ≠ total (${total}) — vérifier plafonds affichés`);
const liensBodacc = await page.$$eval('[data-score-v] a[href]', (as) => as.map((a) => a.href));
note('fiche:bodacc', `liens signaux : ${liensBodacc.join(' | ') || '(aucun)'}`);
if (!liensBodacc.some((h) => h.includes('bodacc.fr') && h.includes('A202501112392')))
  pushAnomalie('fiche.bodacc', `lien BODACC attendu (avis A202501112392) absent/incorrect : ${liensBodacc.join(',')}`);
await shot(page, 'fiche_pourquoi_score');

// ── C-5 : PDF fiche + pré-dossier PC ──
setCtx('fiche', 'export PDF');
const pdfBtn = page.locator('a[href*="export.pdf"]').first();
const pdfHref = await pdfBtn.getAttribute('href').catch(() => null);
if (pdfHref) {
  const r = await ctx.request.get(new URL(pdfHref, BASE).href);
  note('fiche:pdf', `GET ${pdfHref} → ${r.status()} ${r.headers()['content-type']}`);
  if (r.status() !== 200) pushAnomalie('fiche.pdf', `export PDF → ${r.status()}`);
} else note('fiche:pdf', 'aucun lien export.pdf visible sur la fiche');
const preD = await ctx.request.get('http://127.0.0.1:8000/pre-dossier/97414000CV0907');
const prePdf = preD.status() === 200 ? Buffer.from(await preD.body()) : null;
note('fiche:pre-dossier', `GET /pre-dossier → ${preD.status()} (${prePdf ? prePdf.length + ' o' : '—'})`);

// ── C-6 : omnibox — recherche commune puis IDU ──
setCtx('header', 'omnibox commune');
await page.evaluate(() => window.__labuse.select(null));
const box = page.locator('[data-omnibox]');
await box.fill('Saint-Pierre');
await box.press('Enter');
await page.waitForTimeout(2000);
const communeActive = await page.locator('[data-commune-select]').textContent().catch(() => '');
note('header:omnibox', `« Saint-Pierre » → sélecteur commune : « ${(communeActive || '').trim()} »`);
setCtx('header', 'omnibox IDU');
await box.fill('97414000CV0907');
await box.press('Enter');
await page.waitForTimeout(2500);
const ficheViaIdu = await page.evaluate(() => document.body.innerText.includes('97414000CV0907'));
note('header:omnibox', `IDU direct → fiche ouverte : ${ficheViaIdu}`);
if (!ficheViaIdu) pushAnomalie('header.omnibox', 'IDU valide saisi : fiche non ouverte');
await page.keyboard.press('Escape');

// omnibox valeurs limites
setCtx('header', 'omnibox valeurs limites');
for (const q of ['', '   ', '<script>alert(1)</script>', 'zzzzzzz-commune-inexistante', '0']) {
  await box.fill(q); await box.press('Enter'); await page.waitForTimeout(900);
}
note('header:omnibox', 'valeurs limites saisies (vide, espaces, script, inexistant, 0) — voir anomalies auto');

// ── C-7 : commune sans résultats (état vide) ──
setCtx('carte', 'commune sans résultats');
await page.evaluate(() => { window.__labuse.setCommune('Cilaos'); window.__labuse.setVerdict(true) });
await page.waitForTimeout(2500);
const txtVide = await page.evaluate(() => document.querySelector('[data-results-scroll]')?.innerText?.slice(0, 200) ?? document.body.innerText.slice(0, 100));
note('carte:etat-vide', `Cilaos verdict ON → « ${(txtVide || '').replace(/\n/g, ' ⏎ ').slice(0, 140)} »`);
await shot(page, 'carte_cilaos_vide');
await page.evaluate(() => window.__labuse.setCommune(null));

// ── C-8 : réponse lente (loader ?) puis offline (abort) ──
setCtx('etats-limites', 'réponse lente 4s');
await page.route('**/parcels/97412000CE0989**', async (r) => { await new Promise((s) => setTimeout(s, 4000)); r.continue(); });
await page.evaluate(() => window.__labuse.select('97412000CE0989'));
await page.waitForTimeout(1200);
const loaderVisible = await page.evaluate(() => /Chargement de la fiche/.test(document.body.innerText));
note('etats-limites:lent', `pendant 4 s d'attente : loader visible = ${loaderVisible}`);
await page.waitForTimeout(4000);
await page.keyboard.press('Escape');
await page.unroute('**/parcels/97412000CE0989**');

setCtx('etats-limites', 'offline (abort réseau API)');
await page.route('**://127.0.0.1:8000/parcels/**', (r) => r.abort());
await page.evaluate(() => window.__labuse.select('97411000KE0316'));
await page.waitForTimeout(4000);
const offlineTxt = await page.evaluate(() => {
  const f = document.body.innerText;
  return /Impossible de charger la fiche/.test(f) ? 'message d’erreur propre + bouton Réessayer'
    : /Chargement de la fiche/.test(f) ? 'BLOQUÉ sur le loader' : 'aucun feedback visible';
});
note('etats-limites:offline', offlineTxt);
if (offlineTxt !== 'message d’erreur propre + bouton Réessayer')
  pushAnomalie('etat.offline', `abort réseau : ${offlineTxt}`);
await shot(page, 'etat_offline');

sauveJson('crawl_carte_fiche_constats', constats);
bilan('crawl_carte_fiche');
await browser.close();
