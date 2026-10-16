import { ouvrir, aller, shot, lien, debordements } from './harness.mjs';
const FAM = '09-admin';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const { browser, page, journal } = await ouvrir({});
await aller(page, lien.admin());
// attendre que le heros charge (endpoint /admin/pilotage)
await page.waitForResponse((r) => /\/admin\/pilotage/.test(r.url()), { timeout: 20000 }).catch(() => {});
await sleep(2500);
const tuiles = await page.$$eval('[data-tuile]', (els) => els.map((e) => ({ label: e.getAttribute('data-tuile'), txt: (e.textContent||'').replace(/\s+/g,' ').trim() })));
const todos = await page.$$eval('[data-todo]', (els) => els.map((e) => ({ cle: e.getAttribute('data-todo'), tone: e.getAttribute('data-tone'), txt: (e.textContent||'').replace(/\s+/g,' ').trim() })));
// LED santé en pied
const body = await page.locator('body').innerText();
console.log('TUILES', JSON.stringify(tuiles, null, 1));
console.log('TODOS', JSON.stringify(todos, null, 1));
// chercher sections de pilotage (jauges, journal)
const h = await page.$$eval('h1,h2,h3', (els) => els.map((e)=> (e.textContent||'').trim()).filter(Boolean).slice(0,30));
console.log('HEADINGS', JSON.stringify(h));
// Journal 3j
const jour = body.match(/Journal[\s\S]{0,400}/);
console.log('JOURNAL SNIP', jour ? jour[0].replace(/\s+/g,' ').slice(0,300) : 'none');
await shot(page, FAM, 'pilotage_detail', { full: true });
const deb = await debordements(page);
console.log('DEBORD', JSON.stringify(deb));
console.log('badTokens?', /NaN|undefined/.test(body));
await browser.close();
