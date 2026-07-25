// M18 LOT A — tunnel Intégral : arrivée, CGV (bug), paiement, post-paiement, reset, favicon.
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8060';
const INV = process.env.INV, PAY = process.env.PAY, RST = process.env.RST;
const OUT = new URL('.', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 720, height: 1000 } });
p.setDefaultTimeout(15000);
const favicon = async () => p.locator('link[rel="icon"][type="image/svg+xml"]').count();

// A1/A2/A5 — écran d'arrivée + bug CGV
await p.goto(`${BASE}/invitation?token=${INV}`, { waitUntil: 'networkidle' });
await p.waitForTimeout(500);
const ctaDisabled = await p.locator('#cta').isDisabled();
const errVisible = await p.locator('#cgverr').isVisible();
await p.screenshot({ path: `${OUT}/a1_arrivee_cgv_bloque.png` });
console.log('A2 — CTA désactivé (CGV non cochées):', ctaDisabled, '| message visible:', errVisible, '| favicon SVG:', (await favicon()) > 0);
// cocher les CGV → bouton actif, message masqué
await p.locator('#cgv').check();
await p.locator('#password').fill('MotDePasse2026!');
await p.waitForTimeout(300);
console.log('A2 — après coche : CTA actif:', !(await p.locator('#cta').isDisabled()), '| message masqué:', !(await p.locator('#cgverr').isVisible()));
await p.screenshot({ path: `${OUT}/a2_cgv_cochees_cta_actif.png` });

// A3 — page paiement (flux réel : on soumet → jeton de paiement valide)
await p.locator('#cta').click();
await p.waitForLoadState('networkidle');
await p.waitForTimeout(400);
const payTxt = (await p.locator('body').innerText()).replace(/\s+/g, ' ');
await p.screenshot({ path: `${OUT}/a3_paiement.png` });
console.log('A3 — « Engagement 12 mois »:', payTxt.includes('Engagement 12 mois'), '| « en toute sécurité » retiré:', !payTxt.includes('en toute sécurité'), '| bouton « Payer 349 € »:', /Payer 349 €(?!\w)/.test(payTxt));

// A4 — post-paiement
await p.goto(`${BASE}/onboarding/retour?ok=1`, { waitUntil: 'networkidle' });
await p.waitForTimeout(400);
const retTxt = (await p.locator('body').innerText()).replace(/\s+/g, ' ');
await p.screenshot({ path: `${OUT}/a4_bienvenue.png` });
console.log('A4 — « Bienvenue chez LABUSE »:', retTxt.includes('Bienvenue chez LABUSE'), '| bouton accès:', retTxt.includes('Entrer dans LABUSE'));

// A6 — mot de passe oublié (formulaire + page reset)
await p.goto(`${BASE}/reset`, { waitUntil: 'networkidle' });
await p.waitForTimeout(300);
await p.screenshot({ path: `${OUT}/a6_oublie_formulaire.png` });
const hasEmail = await p.locator('#email').count();
await p.goto(`${BASE}/reset?token=${RST}`, { waitUntil: 'networkidle' });
await p.waitForTimeout(300);
await p.screenshot({ path: `${OUT}/a6_nouveau_mdp.png` });
const hasPwd = await p.locator('#password').count();
console.log('A6 — formulaire e-mail:', hasEmail > 0, '| page nouveau mot de passe (token valide):', hasPwd > 0, '| favicon SVG:', (await favicon()) > 0);

console.log('done');
await b.close();
