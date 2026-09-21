// DASHBOARD-4 Lot 5 — preuve Comptes : K1 deux entrées (essai 48h · créer client), K2 page créer
// (email/prénom/nom + 2 gestes), K3 5 statuts + colonne abonnement + segment À toucher, K5 fiche
// (ariane, gestes haut-droite, phrase calculée), K6 ton-email@test.com signalé.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-dash4/captures/dashboard4/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1400,1700'] })
const p = await (await br.newContext({ viewport:{width:1400,height:1700} })).newPage(); p.on('pageerror',(e)=>console.log('ERR',e.message))
await p.goto('http://localhost:5335/socle/#admin=1',{waitUntil:'domcontentloaded',timeout:60000})
await p.waitForFunction(()=>!!window.__labuse,{timeout:60000}); await sleep(1500)
await p.evaluate(()=>document.querySelector('aside button[data-admin-section="licences"]')?.click())
await p.waitForFunction(()=>/Comptes/.test(document.body.innerText||''),{timeout:20000}).catch(()=>{})
await sleep(800)
// segment « Tous » pour voir les lignes (le défaut « À toucher » peut être vide)
await p.evaluate(()=>{const b=[...document.querySelectorAll('button')].find(x=>/^Tous\b/.test(x.textContent.trim())); if(b)b.click()})
await p.waitForFunction(()=>document.querySelectorAll('[data-licence]').length>0,{timeout:15000}).catch(()=>{})
await sleep(500)
const liste = await p.evaluate(()=>{
  const t=document.body.innerText||''
  return {
    boutons:['Ouvrir un essai 48 h','Créer un client'].filter(x=>t.includes(x)),
    entetes:['statut','abonnement','dernière visite','à faire'].filter(x=>t.toLowerCase().includes(x)),
    tonEmail:/ton-email@test\.com est présent et masqué/.test(t),
    segments:['À toucher','Actifs','Essais','Invités','Suspendus','Tous'].filter(x=>t.includes(x)),
    nLignes:document.querySelectorAll('[data-licence]').length,
  }
})
console.log('K1 boutons:',liste.boutons.join(' · '))
console.log('K3 en-têtes:',liste.entetes.join(' · '),'| segments:',liste.segments.length)
console.log('K6 ton-email signalé:',liste.tonEmail)
await p.screenshot({ path: OUT+'lot5-comptes-apres.png', fullPage:true }); console.log('capté liste')
// K1/K2 — page Créer un client
await p.evaluate(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Créer un client'); if(b)b.click()})
await sleep(800)
const creer = await p.evaluate(()=>{
  const t=document.body.innerText||''
  return { titre:/Créer un client/.test(t), champs:['E-mail','Prénom','Nom'].filter(x=>t.includes(x)),
    gestes:["Créer et envoyer l'invitation",'créer sans envoyer'].filter(x=>t.includes(x)), dryrun:/dry-run/.test(t) }
})
console.log('K2 champs:',creer.champs.join(' · '),'| gestes:',creer.gestes.join(' · '),'| dry-run dit:',creer.dryrun)
await p.screenshot({ path: OUT+'lot5-creer-apres.png', fullPage:true }); console.log('capté créer')
// K5 — fiche client : RELOAD propre (goto même hash = no-op SPA) puis ouverture d'une ligne
await p.reload({waitUntil:'domcontentloaded',timeout:60000})
await p.waitForFunction(()=>!!window.__labuse,{timeout:60000}); await sleep(1800)
await p.evaluate(()=>document.querySelector('aside button[data-admin-section="licences"]')?.click())
await sleep(1500)
await p.evaluate(()=>{const b=[...document.querySelectorAll('button')].find(x=>/^Tous\b/.test(x.textContent.trim())); if(b)b.click()})
await p.waitForFunction(()=>document.querySelectorAll('[data-licence]').length>0,{timeout:15000}).catch(()=>{})
await sleep(400)
await p.evaluate(()=>document.querySelector('[data-licence]')?.click())
await p.waitForFunction(()=>/Comptes\s*›/.test(document.body.innerText||''),{timeout:15000}).catch(()=>{})
await sleep(800)
const fiche = await p.evaluate(()=>{
  const t=document.body.innerText||''
  return { ariane:/Comptes\s*›/.test(t), onglets:['Aperçu','Activité','Facturation','IA'].filter(x=>t.includes(x)),
    gestes:["Renvoyer l'invitation",'Suspendre','Rétablir','Transformer en client'].filter(x=>t.includes(x)),
    phrase:/paie depuis|n'est jamais entré|en essai|connecté au moins|actif /.test(t) }
})
console.log('K5 ariane:',fiche.ariane,'| onglets:',fiche.onglets.join(','),'| gestes:',fiche.gestes.join(' · '),'| phrase calculée:',fiche.phrase)
await p.screenshot({ path: OUT+'lot5-fiche-apres.png', fullPage:true }); console.log('capté fiche')
await br.close(); console.log('DONE lot5')
