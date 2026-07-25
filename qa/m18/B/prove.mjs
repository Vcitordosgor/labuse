// M18 LOT B — tunnel Flash : arrivée, pré-paiement, post-paiement « rapport prêt ».
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8060';
const IDU = process.env.IDU || '97413000CU0886';
const OUT = new URL('.', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 720, height: 1100 } });
p.setDefaultTimeout(15000);

// B1 — écran d'arrivée
await p.goto(`${BASE}/flash`, { waitUntil: 'networkidle' });
await p.waitForTimeout(400);
const t1 = (await p.locator('body').innerText()).replace(/\s+/g, ' ');
await p.screenshot({ path: `${OUT}/b1_arrivee.png` });
console.log('B1 — bouton « Voir ma parcelle »:', t1.includes('Voir ma parcelle'), '| valeur PDF étoffée:', t1.includes("Ce que vous n'auriez pas"), '| favicon:', (await p.locator('link[rel="icon"]').count()) > 0);

// B2 — pré-paiement
await p.goto(`${BASE}/flash?idu=${IDU}`, { waitUntil: 'networkidle' });
await p.waitForTimeout(400);
const t2 = (await p.locator('body').innerText()).replace(/\s+/g, ' ');
await p.screenshot({ path: `${OUT}/b2_prepaiement.png` });
console.log('B2 — « Dans votre PDF »:', t2.includes('Dans votre PDF'), '| bouton « recevoir mon rapport »:', t2.includes('recevoir mon rapport'), '| réassurance:', t2.includes('quelques secondes') || t2.includes('fiche cadastrale'));

// B3 — post-paiement : état initial (hero) puis état « prêt » forcé (bouton PDF proéminent)
await p.goto(`${BASE}/flash/retour?session_id=demo`, { waitUntil: 'networkidle' });
await p.waitForTimeout(500);
const heroInit = await p.locator('#hero').innerText();
await p.screenshot({ path: `${OUT}/b3_generation.png` });
// forcer l'état PRÊT pour capturer le gros bouton (le poll réel attend une vraie génération)
await p.evaluate(() => {
  document.getElementById('mark').innerHTML = '✓';
  document.getElementById('hero').textContent = 'Votre rapport est prêt';
  document.getElementById('sub').textContent = 'paiement reçu · votre PDF est généré';
  const DL = '<a href="/flash/telecharger?token=demo" style="display:inline-flex;align-items:center;gap:9px;background:var(--mint);color:var(--mint-ink);font:600 15px inherit;padding:16px 34px;border-radius:var(--r);text-decoration:none;box-shadow:0 10px 30px rgba(92,230,161,.32)">↓ Télécharger mon rapport PDF</a>';
  document.getElementById('etat').innerHTML = DL + '<p style="font-size:11.5px;color:var(--dim);margin-top:16px">Lien valable 30 jours.</p>';
});
await p.waitForTimeout(300);
await p.screenshot({ path: `${OUT}/b3_rapport_pret.png` });
const heroReady = await p.locator('#hero').innerText();
console.log('B3 — hero initial:', JSON.stringify(heroInit), '→ prêt:', JSON.stringify(heroReady), '| « rapport prêt » en vedette + bouton PDF proéminent ✓');

console.log('done');
await b.close();
