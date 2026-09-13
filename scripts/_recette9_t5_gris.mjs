import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
const OUT = '/Users/openclaw/Desktop/labuse-recette6/docs/audit-2026-09/RECETTE-9-preuves/captures/'
const b = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const p = await b.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1.5 })
await p.goto('http://localhost:5199/socle/', { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse_map, { timeout: 20000 })
await p.waitForTimeout(1200)
const diag = async (tag) => p.evaluate((tag) => { const m=window.__labuse_map
  const info=(id)=>{ if(!m.getLayer(id))return{id,layer:'absent'}
    const g=(f)=>{try{return JSON.stringify(m.getPaintProperty(id,f))}catch{return'?'}}
    let vis;try{vis=m.getLayoutProperty(id,'visibility')??'visible'}catch{vis='?'}
    return{id,vis,color:(g('fill-color')||'').slice(0,26),op:g('fill-opacity'),rendered:m.queryRenderedFeatures({layers:[id]}).length} }
  return{tag,zoom:+m.getZoom().toFixed(1),parcels_fill:info('parcels-fill')} }, tag)
const shot=async(n)=>{await p.screenshot({path:OUT+n+'.png'});console.log('CAP',n)}
const setBasemap=async(label)=>{await p.click('button[title="Fond de plan"]');await p.waitForTimeout(250);await p.getByRole('button',{name:label,exact:true}).click({force:true});await p.waitForTimeout(2000)}
// A île sombre
console.log(JSON.stringify(await diag('A_ile_sombre'))); await shot('T5-A-ile-sombre')
// commune Saint-Denis (NOM) + zoom sur une parcelle chargée
await p.evaluate(() => window.__labuse.setCommune('Saint-Denis'))
try{await p.waitForFunction(()=>{const s=window.__labuse_map.getSource('parcels');return s&&s._data&&(s._data.features||[]).length>0},{timeout:25000})}catch{console.log('geojson lente')}
await p.evaluate(()=>{const s=window.__labuse_map.getSource('parcels');const fs=s._data.features;const f=fs[Math.floor(fs.length/2)];const flat=(a)=>Array.isArray(a[0])?flat(a[0]):a;const ll=flat(f.geometry.coordinates);window.__labuse_map.jumpTo({center:[ll[0],ll[1]],zoom:17})})
await p.waitForTimeout(2500)
console.log(JSON.stringify(await diag('B_commune_sombre_OFF'))); await shot('T5-B-commune-sombre-analyseOFF')
await p.evaluate(()=>window.__labuse.setVerdict(true)); await p.waitForTimeout(2500)
console.log(JSON.stringify(await diag('C_commune_sombre_ON'))); await shot('T5-C-commune-sombre-analyseON')
await p.evaluate(()=>window.__labuse.setVerdict(false)); await p.waitForTimeout(800)
await setBasemap('Ortho IGN'); console.log(JSON.stringify(await diag('D_commune_ortho_OFF'))); await shot('T5-D-commune-ortho-analyseOFF')
await setBasemap('Clair'); console.log(JSON.stringify(await diag('E_commune_clair_OFF'))); await shot('T5-E-commune-clair-analyseOFF')
await b.close()
