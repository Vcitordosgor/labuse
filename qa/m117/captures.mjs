// M117 · Phase 4 — captures des gabarits refondus (DA-COPILOTE-v2, surface IA mauve).
import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const STAMP = new Date().toISOString().slice(0,16).replace(/[:T]/g,'-');
const OUT = `/Users/openclaw/Desktop/labuse/qa/m117/captures/${STAMP}`; mkdirSync(OUT,{recursive:true});
const b = await chromium.launch({channel:'chrome'});
const p = await b.newPage({viewport:{width:1160,height:1000}}); p.setDefaultTimeout(40000);
const shot=async(n,note)=>{await p.screenshot({path:`${OUT}/${n}.png`}); console.log(`📸 ${n} — ${note}`);};
const safe=async(n,note,fn)=>{try{await fn();await shot(n,note);}catch(e){console.log(`⚠️ ${n} SAUTÉ ${String(e).slice(0,70)}`);}};
const go=async()=>{await p.goto('http://localhost:5173/',{waitUntil:'domcontentloaded'}); await p.click('[data-rail="copilote"], text=IA').catch(()=>p.click('text=IA')); await p.waitForSelector('[data-accueil-intents]');};

await go();
await safe('01-accueil','accueil v2 : six intentions + sous-titres, brief sous le point d\'entrée',async()=>{await p.waitForTimeout(300);});
await safe('02-donnees','réponse données : carte mauve, récap M109, source du critère (BODACC), porte',async()=>{
  await p.click('[data-chip-cle="donnees"]');
  await p.fill('textarea','Combien de parcelles en procédure judiciaire à Saint-Denis ?');
  await p.click('[data-accueil-envoyer]'); await p.waitForSelector('[data-reponse]'); await p.waitForTimeout(500);});
await safe('03-nouveau-fil-web','réponse web COURTE (carte mauve) + Nouveau fil',async()=>{
  await p.click('[data-fil-nouveau]'); await p.waitForSelector('[data-accueil-intents]');
  await p.click('[data-chip-cle="web"]'); await p.fill('textarea','Qui est le maire de La Possession ?');
  await p.click('[data-accueil-envoyer]'); await p.waitForSelector('[data-reponse]',{timeout:40000}); await p.waitForTimeout(500);});
await safe('04-refus-outil','refus/voie : chip outil vague → carte warn + « Voir les outils »',async()=>{
  await p.click('[data-fil-nouveau]'); await p.waitForSelector('[data-accueil-intents]');
  await p.click('[data-chip-cle="outil"]'); await p.fill('textarea','ouvre un outil');
  await p.click('[data-accueil-envoyer]'); await p.waitForSelector('[data-reponse]'); await p.waitForTimeout(400);});
await safe('05-precision','précision (gabarit unique) : kicker PRÉCISION + champ du fil',async()=>{
  await p.click('[data-fil-nouveau]'); await p.waitForSelector('[data-accueil-intents]');
  await p.click('[data-chip-cle="donnees"]'); await p.fill('textarea','combien de parcelles');
  await p.click('[data-accueil-envoyer]'); await p.waitForSelector('[data-reponse]'); await p.waitForTimeout(400);});
await b.close(); console.log(`\n✅ ${OUT}`);
