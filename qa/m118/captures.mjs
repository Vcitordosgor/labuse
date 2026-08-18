import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const STAMP=new Date().toISOString().slice(0,16).replace(/[:T]/g,'-');
const OUT=`/Users/openclaw/Desktop/labuse/qa/m118/captures/${STAMP}`; mkdirSync(OUT,{recursive:true});
const b=await chromium.launch({channel:'chrome'}); const p=await b.newPage({viewport:{width:1120,height:980}}); p.setDefaultTimeout(40000);
const shot=async(n,t)=>{await p.screenshot({path:`${OUT}/${n}.png`});console.log(`📸 ${n} — ${t}`);};
const safe=async(n,t,f)=>{try{await f();await shot(n,t);}catch(e){console.log(`⚠️ ${n} ${String(e).slice(0,70)}`);}};
const go=async()=>{await p.goto('http://localhost:5173/',{waitUntil:'domcontentloaded'});await p.click('[data-rail="copilote"], text=IA').catch(()=>p.click('text=IA'));await p.waitForSelector('[data-accueil-intents]');};
await go();
await safe('01-accueil-4missions','accueil : 4 missions (grille)',async()=>{await p.waitForTimeout(300);});
await safe('02-expliquer','mission Expliquer : notion courte, aucun chiffre',async()=>{
  await p.click('[data-chip-cle="expliquer"]');await p.fill('textarea','Qu\'est-ce qu\'une zone AU ?');
  await p.click('[data-accueil-envoyer]');await p.waitForSelector('[data-reponse]',{timeout:40000});await p.waitForTimeout(400);});
await safe('03-refus-voie','refus-voie : « trouve un terrain » → carte warn + voie Projets',async()=>{
  await p.click('[data-fil-nouveau]');await p.waitForSelector('[data-accueil-intents]');
  await p.fill('textarea','trouve-moi un terrain à fort potentiel à Saint-Paul pour 15 logements');
  await p.click('[data-accueil-envoyer]');await p.waitForSelector('[data-reponse-voie]',{timeout:40000});await p.waitForTimeout(400);});
await b.close();console.log(`\n✅ ${OUT}`);
