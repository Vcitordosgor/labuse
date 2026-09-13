// SOURCES-AUDIT-1 — click-test navigateur : 30 sources, page /sources (transparence) + fraîcheur/i.
// Rejouable : node docs/audit-2026-09/SOURCES/scripts/clictest_30.mjs
import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs';
import { writeFileSync, mkdirSync } from 'node:fs';
const EXE = process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell';
const OUT='/Users/openclaw/Desktop/labuse-etat/docs/audit-2026-09/SOURCES/captures/sources30';
mkdirSync(OUT,{recursive:true});
// 30 sources (id, aiguille de recherche sur /sources)
const S=[
 [1,"Cadastre (API Carto"],[71,"parcelles des personnes morales"],[132,"DFI — documents"],
 [3,"Urbanisme PLU/GPU"],[44,"SUP — assiettes"],[107,"droit de préemption"],[62,"Sudocuh"],
 [4,"Géorisques"],[97,"CatNat"],[36,"mouvements de terrain"],[76,"ZNIEFF (INPN/MNHN)"],[24,"ABF / Monuments"],
 [5,"DVF / valeurs"],[16,"SITADEL"],[100,"RNIC"],[129,"Loyers OLL"],[84,"Radar (pige"],[119,"DVF Réunion (Région"],
 [48,"PVGIS"],[93,"lignes moyenne tension"],[126,"Fibre Arcep"],[68,"Office de l'eau"],
 [21,"SIRENE"],[20,"BPE INSEE"],[52,"Filosofi"],[74,"Transport public — GTFS"],
 [17,"BD TOPO IGN"],[83,"CoSIA"],[70,"LiDAR HD"],[141,"LOVAC"],
];
const b = await chromium.launch({ executablePath: EXE });
const p = await b.newPage({ viewport:{width:1440,height:950} }); p.setDefaultTimeout(12000);
await p.goto('http://localhost:5200/socle/',{waitUntil:'networkidle'}); await p.waitForTimeout(1500);
await p.locator('text=/^Sources$/').first().click(); await p.waitForTimeout(2000);
const rows=[];
for (const [id,needle] of S){
  try{
    const loc = p.locator(`text=${JSON.stringify(needle)}`).first();
    await loc.scrollIntoViewIfNeeded({timeout:5000});
    await p.waitForTimeout(250);
    // texte du bloc parent (source + licence + fraîcheur)
    const info = await loc.evaluate(el=>{ let n=el; for(let i=0;i<4&&n.parentElement;i++)n=n.parentElement; return (n.innerText||'').replace(/\s+/g,' ').slice(0,300); }).catch(()=> '');
    await loc.screenshot({path:`${OUT}/${id}.png`}).catch(async()=>{ await p.screenshot({path:`${OUT}/${id}.png`}); });
    const dit_source = /·|↗|Licence|INSEE|IGN|DGFiP|DEAL|Cerema|OpenStreetMap/i.test(info);
    const dit_millesime = /Publié le|millésime|\d{2}\/\d{2}\/\d{4}|202\d/.test(info);
    const flag = (info.match(/FIABILITÉ À CONFIRMER|PROXY|ACCÈS SOUS CONVENTION|MISE À JOUR EN COURS/gi)||[]).join(',');
    rows.push({id, trouve:true, dit_source, dit_millesime, flag, info});
    console.log(`✓ ${id} ${needle} | source=${dit_source} millésime=${dit_millesime} ${flag}`);
  }catch(e){ rows.push({id,trouve:false,err:e.message}); console.log(`✗ ${id} ${needle} — ${e.message.slice(0,60)}`); }
}
writeFileSync(OUT+'/_rows.json', JSON.stringify(rows,null,1));
await b.close();
