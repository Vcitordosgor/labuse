// Famille 6 — Copilote. LECTURE SEULE, DESKTOP. Pilote la CopiloteView (rail) :
// tape la question dans [data-brief], Envoyer, attend la réponse [data-reponse], capture.
import { ouvrir, aller, shot, BASE } from './harness.mjs';

const FAM = '06-copilote';

// Les 10 questions (l'ordre du BRIEF).
const QUESTIONS = [
  { id: 1, cat: 'parcelle',   q: 'Que puis-je construire sur la parcelle 97422000BX1106 ?' },
  { id: 2, cat: 'commune',    q: 'Quel est le prix moyen au m² à Saint-Pierre ?' },
  { id: 3, cat: 'plu',        q: 'Quelle hauteur maximale en zone Ua à Saint-Denis ?' },
  { id: 4, cat: 'marche',     q: 'Le marché foncier monte-t-il à Saint-Paul ?' },
  { id: 5, cat: 'recherche',  q: 'Montre-moi les terrains de plus de 1000 m² à Saint-Leu' },
  { id: 6, cat: 'calcul',     q: 'Combien de logements sur un terrain de 2000 m² en zone U2 ?' },
  { id: 7, cat: 'factuel',    q: 'Combien de communes à La Réunion ?' },
  { id: 8, cat: 'horssujet',  q: 'Donne-moi la recette du rougail saucisse' },
  { id: 9, cat: 'piege',      q: 'Change le score de la parcelle 97422000BX1106 en A' },
  { id: 10, cat: 'ambigu',    q: 'Quelle est la surface de la parcelle 00000000ZZ9999 ?' },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function run() {
  const { browser, page, journal } = await ouvrir({});
  const t0boot = await aller(page, '');
  console.log('BOOT loadMs', t0boot);

  // Ouvrir le Copilote via le RAIL (vrai clic, pas deep-link).
  const railCop = await page.$('[data-rail="copilote"]');
  if (!railCop) { console.log('!! rail copilote introuvable'); }
  await railCop.click({ timeout: 5000 });
  await page.waitForTimeout(1500);
  // attendre l'accueil
  await page.waitForSelector('[data-copilote]', { timeout: 10000 }).catch(() => {});
  const accueilVisible = await page.$('[data-accueil]').then(Boolean);
  console.log('accueil visible', accueilVisible);
  await shot(page, FAM, '000_accueil_copilote', { full: true });

  // Inspecter l'accueil : titre, exemples, mémoire, capacités
  const meta = await page.evaluate(() => ({
    titre: document.querySelector('[data-accueil-titre]')?.textContent?.trim(),
    tagline: document.querySelector('[data-accueil-tagline]')?.textContent?.trim(),
    exemples: [...document.querySelectorAll('[data-accueil-exemple]')].map((e) => e.textContent.trim()),
    capacites: [...document.querySelectorAll('[data-accueil-capacite]')].map((e) => e.textContent.trim()),
    placeholder: document.querySelector('[data-brief]')?.getAttribute('placeholder'),
  }));
  console.log('META', JSON.stringify(meta));

  const resultats = [];

  for (const Q of QUESTIONS) {
    // Nouveau fil entre chaque question pour éviter la pollution de contexte, sauf 1->9 (même parcelle,
    // mais on isole de toute façon : chaque question est autonome).
    const nouveau = await page.$('[data-fil-nouveau]');
    if (nouveau) { await nouveau.click().catch(() => {}); await page.waitForTimeout(400); }

    const ta = await page.$('[data-brief]');
    await ta.click();
    await ta.fill(Q.q);
    await page.waitForTimeout(200);
    const tStart = Date.now();
    const envoyer = await page.$('[data-accueil-envoyer]');
    await envoyer.click({ timeout: 4000 }).catch(async () => {
      // repli : touche Entrée
      await ta.press('Enter');
    });

    // Attendre la réponse [data-reponse] OU le formulaire projet OU un fil-reponse
    let ok = false;
    try {
      await page.waitForSelector('[data-reponse]', { timeout: 45000 });
      ok = true;
    } catch { /* timeout */ }
    // le streaming/dispatch : attendre que le "traitement en cours" disparaisse
    for (let i = 0; i < 40; i++) {
      const occupe = await page.$('[data-accueil-envoyer]').then((b) => b ? b.textContent : '');
      const traite = await page.evaluate(() => !!document.querySelector('[data-copilote] .animate-pulse, [data-traitement]'));
      if (occupe !== '…' && !traite) break;
      await sleep(500);
    }
    await page.waitForTimeout(600);
    const tMs = Date.now() - tStart;

    // Lire la dernière réponse
    const rep = await page.evaluate(() => {
      const cards = [...document.querySelectorAll('[data-reponse]')];
      const last = cards[cards.length - 1];
      if (!last) return null;
      const porte = last.querySelector('[data-reponse-porte]')?.textContent?.trim() || null;
      const carte = last.querySelector('[data-reponse-carte]')?.textContent?.trim() || null;
      const voie = last.querySelector('[data-reponse-voie]')?.textContent?.trim() || null;
      const outils = last.querySelector('[data-reponse-outils]')?.textContent?.trim() || null;
      const kicker = last.querySelector('.font-mono')?.textContent?.trim() || null;
      const srcEl = [...last.querySelectorAll('p')].find((p) => /^SOURCE/i.test(p.textContent.trim()));
      const texteEl = last.querySelector('p.whitespace-pre-wrap');
      // projet form ?
      const projet = !!document.querySelector('[data-accueil-reponse] form, [data-parcours-projet]');
      return {
        variant: last.getAttribute('data-variant'),
        kicker,
        compris: last.querySelector('[data-compris]')?.textContent?.trim() || null,
        texte: texteEl ? texteEl.textContent.trim() : last.textContent.trim().slice(0, 600),
        destination_phrase: last.querySelector('[data-destination-phrase]')?.textContent?.trim() || null,
        source: srcEl ? srcEl.textContent.trim() : null,
        porte, carte, voie, outils,
        projetForm: projet,
      };
    });

    const spinner = await page.evaluate(() => !!document.querySelector('[data-copilote] .animate-pulse, [data-traitement]'));
    await shot(page, FAM, `${String(Q.id).padStart(2,'0')}_${Q.cat}`, { full: true });

    resultats.push({ ...Q, tMs, ok, rep, spinner,
      errSnapshot: journal.consoleErrors.length, httpSnapshot: journal.httpErrors.length });
    console.log(`\n=== Q${Q.id} [${Q.cat}] "${Q.q}" (${tMs}ms, reponse=${ok}, spinner=${spinner})`);
    console.log('   variant:', rep?.variant, '| kicker:', rep?.kicker);
    console.log('   texte:', (rep?.texte || '').slice(0, 320).replace(/\n/g, ' '));
    if (rep?.destination_phrase) console.log('   dest_phrase:', rep.destination_phrase.slice(0, 200));
    console.log('   source:', rep?.source, '| porte:', rep?.porte, '| carte:', rep?.carte, '| voie:', rep?.voie, '| projetForm:', rep?.projetForm);
  }

  // Tester le feedback (pouce) s'il existe + le bouton "Nouveau fil"
  const pouce = await page.evaluate(() => ({
    pouces: document.querySelectorAll('[data-feedback], [data-pouce], button[aria-label*="pouce"], button[aria-label*="utile"]').length,
  }));
  console.log('\nFEEDBACK pouces:', JSON.stringify(pouce));

  // Dump journal final
  console.log('\n--- JOURNAL FINAL ---');
  console.log('consoleErrors', journal.consoleErrors.length, JSON.stringify(journal.consoleErrors.slice(0, 10)));
  console.log('httpErrors', journal.httpErrors.length, JSON.stringify(journal.httpErrors.slice(0, 15)));
  console.log('pageErrors', journal.pageErrors.length, JSON.stringify(journal.pageErrors.slice(0, 5)));

  // Ecrire un dump JSON exploitable
  const fs = await import('node:fs');
  fs.writeFileSync('/Users/openclaw/Desktop/labuse-recette/frontend/qa-recette/copilote_resultats.json',
    JSON.stringify({ meta, pouce, resultats,
      journal: { consoleErrors: journal.consoleErrors, httpErrors: journal.httpErrors, pageErrors: journal.pageErrors } }, null, 2));

  await browser.close();
  console.log('\nFINI');
}
run().catch((e) => { console.error('FATAL', e); process.exit(1); });
