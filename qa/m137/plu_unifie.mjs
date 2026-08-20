import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE='http://localhost:5173/socle/'; const OUT=new URL('./captures',import.meta.url).pathname;
const b=await chromium.launch({channel:'chrome'}); const page=await b.newPage({viewport:{width:1440,height:1024}});
const shot=(n)=>page.screenshot({path:`${OUT}/${n}.png`, clip:{x:0,y:0,width:430,height:940}});
const soft=async(fn,w)=>{try{return await fn()}catch(e){console.log('WARN',w,String(e).slice(0,130))}};
const has=(sel)=>page.locator(sel).count();
await page.goto(BASE,{waitUntil:'domcontentloaded'}); await page.waitForTimeout(3500);
// ouvrir Outils → carte PLU
await soft(async()=>{ await page.locator('button[title="Outils"]').click(); await page.waitForTimeout(700); },'outils');
await soft(async()=>{ await page.locator('[data-outil="plu"]').click(); await page.waitForTimeout(1500); },'carte plu');

// 1) ACCUEIL — 3 voies
console.log('voies accueil:', await has('[data-plu-voie]'));
await shot('plu_accueil');

// 2) PROCÉDURE
await soft(async()=>{ await page.locator('[data-plu-voie="procedure"]').click(); await page.waitForTimeout(600); },'voie procedure');
await soft(async()=>{ const inp=page.locator('[data-verif-idu]'); await inp.fill('97410000BV0120'); await inp.press('Enter'); },'idu');
await page.waitForTimeout(2500);
await shot('plu_procedure');
await soft(async()=>{ await page.locator('[data-plu-hub-retour]').click(); await page.waitForTimeout(500); },'retour hub');

// 3) CHANGEMENT (M15, lent ~12s)
await soft(async()=>{ await page.locator('[data-plu-voie="changement"]').click(); await page.waitForTimeout(1500); },'voie changement');
await soft(async()=>{ await page.getByText('→ U',{exact:false}).first().click(); },'zone');
await page.waitForFunction(()=>/parcelles en|ratio analogie/.test(document.body.innerText),{timeout:35000}).catch(()=>console.log('WARN changement lent'));
await page.waitForTimeout(800);
await shot('plu_changement');
await soft(async()=>{ await page.locator('[data-plu-hub-retour]').click(); await page.waitForTimeout(500); },'retour hub 2');

// 4a) ANNUAIRE étape 1 — les 24 communes
await soft(async()=>{ await page.locator('[data-plu-voie="annuaire"]').click(); await page.waitForTimeout(1500); },'voie annuaire');
console.log('communes grille:', await has('[data-plu-commune]'));
console.log('heading étape1:', /Cliquez sur la commune/.test(await page.evaluate(()=>document.body.innerText)));
await shot('plu_annuaire_e1');

// 4b) ANNUAIRE étape 2 — Saint-Paul : PLU intégral + Rechercher
await soft(async()=>{ await page.locator('[data-plu-commune="97415"]').click(); await page.waitForTimeout(900); },'commune Saint-Paul');
const integralHref=await soft(async()=>page.locator('[data-plu-integral]').getAttribute('href'),'href');
console.log('étape2 → PLU intégral présent:', await has('[data-plu-integral]'), '| Rechercher:', await has('[data-plu-rechercher]'));
console.log('href .zip:', (integralHref||'').slice(0,60));
await shot('plu_annuaire_e2');

// 4c) ANNUAIRE — commune RNU (Saint-Philippe 97442) dit son statut, pas de bouton mort
await soft(async()=>{ await page.locator('[data-plu-retour]').click(); await page.waitForTimeout(500); },'retour grille');
await soft(async()=>{ await page.locator('[data-plu-commune="97442"]').click(); await page.waitForTimeout(700); },'commune RNU');
console.log('RNU dit son statut:', await has('[data-plu-indispo]'), '| bouton intégral (doit être 0):', await has('[data-plu-integral]'));
await shot('plu_annuaire_rnu');

// 5) ALLER-RETOUR complet → accueil
await soft(async()=>{ await page.locator('[data-plu-retour]').click(); await page.waitForTimeout(400); },'retour grille 2');
await soft(async()=>{ await page.locator('[data-plu-hub-retour]').click(); await page.waitForTimeout(500); },'retour accueil');
console.log('retour accueil OK (3 voies):', await has('[data-plu-voie]'));

await b.close();
console.log('CAPTURES OK');
