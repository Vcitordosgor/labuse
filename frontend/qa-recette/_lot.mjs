import { ouvrir } from './harness.mjs';
import { allerFiche, parcourirTiroirs, entete, debordements, shot, clicBouton } from './_fiche_lib.mjs';
import { writeFileSync } from 'node:fs';
const LOT = JSON.parse(process.env.LOT);
const { browser, page, journal } = await ouvrir({});
for (const [idu,note] of LOT){
  const c0=journal.consoleErrors.length,h0=journal.httpErrors.length;
  const ms=await allerFiche(page,idu);
  const head=await entete(page);
  const tiroirs=await parcourirTiroirs(page);
  const deb=await debordements(page);
  const sh=await shot(page,'02-fiche',`${idu}`);
  // buttons react?
  const demande=await clicBouton(page, /^Demander à LABUSE/);
  await allerFiche(page,idu); // reset after click navigation
  const poser=await clicBouton(page, /^Poser une question/);
  const summary={idu,note,loadMs:ms,
    newConsole:journal.consoleErrors.length-c0,newHttp:journal.httpErrors.length-h0,
    deb:deb.length, demandeReact:demande.found&&demande.urlAfter!==demande.urlBefore, poserReact:poser.found,
    tiroirs:Object.fromEntries(Object.entries(tiroirs).map(([k,v])=>[k,v.clickable?(v.videSansExpl?'VIDE!':'ok'):'noclick']))};
  console.log('=====',idu,'=====');
  console.log(JSON.stringify(summary));
  if(deb.length) console.log('DEB:',JSON.stringify(deb.slice(0,6)));
  if(journal.httpErrors.length-h0>0) console.log('HTTP:',journal.httpErrors.slice(h0));
  if(journal.consoleErrors.length-c0>0) console.log('CONS:',journal.consoleErrors.slice(c0));
  // dump full content to file
  let dump=`HEAD:\n${head}\n\nDEMANDE btn: ${JSON.stringify(demande)}\nPOSER btn: ${JSON.stringify(poser)}\n`;
  for(const [k,v] of Object.entries(tiroirs)) dump+=`\n### ${k} [headVal=${v.headVal}]\n${v.content||'(vide)'}\n`;
  writeFileSync(`/tmp/f_${idu}.txt`,dump);
}
await browser.close();
