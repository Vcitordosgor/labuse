# BRIEF commun — RECETTE-GENERALE-1 (agents de famille)

Tu es un agent de recette d'une app web immobilière (LABUSE, foncier Réunion). Tu pilotes
un vrai navigateur sur l'app qui tourne en local et tu RELÈVES les anomalies. **LECTURE
SEULE : tu ne corriges AUCUN code applicatif, tu ne touches PAS à la base, rien sur le VPS,
aucun mail réellement envoyé, aucun paiement réel (Stripe mode test uniquement).**

## Ce qui tourne déjà (ne (re)démarre rien)
- Backend : http://127.0.0.1:8798  (API, run servi q_v18, PDF activés)
- Frontend : http://localhost:5998/socle/  (base path `/socle/` OBLIGATOIRE)
- Auth désactivée en local (tu es un visiteur anonyme sauf parcours compte).

## MOBILE : l'app cliente est volontairement bloquée (acquis Famille 1)
L'app cliente affiche un écran « disponible sur ordinateur » (`EcranOrdinateur.tsx`,
décision produit CHARGEMENT-1) sous 390px — aucun panneau/carte/fiche, même en deep-link.
Donc **ne refais PAS le parcours mobile** pour les familles client (fiche, commune, outils,
copilote, exports, courrier). Teste en DESKTOP uniquement. (Le barrage lui-même est propre :
0 débordement, 0 erreur.) Admin/compte : idem desktop.

## Outil : Playwright via le Chrome du système
macOS 13 → pas de binaire Playwright ; on pilote Google Chrome (`channel:'chrome'`).
Un harnais partagé est fourni : `frontend/qa-recette/harness.mjs`. Écris tes scripts
dans `frontend/qa-recette/` (pour que `import './harness.mjs'` résolve node_modules), et
lance-les avec `node` depuis ce dossier. Exports du harnais :
- `ouvrir({mobile})` → `{browser, context, page, journal}`. `journal` accumule
  `consoleErrors`, `httpErrors` (4xx/5xx avec URL, bruit connu filtré), `pageErrors`.
- `aller(page, hash)` → navigue vers BASE+hash, attend networkidle, renvoie le temps (ms).
- `lien.fiche(idu)` `.commune(nom)` `.outil(key)` `.outilSurParcelle(key,idu)` `.admin()`
  `.radar()` `.surveillance(vue)` — construisent le hash (voir deep-links ci-dessous).
- `shot(page, famille, nom, {full})` → capture PNG dans `captures/<famille>/`, renvoie le chemin.
- `debordements(page)` → liste des éléments qui débordent horizontalement (texte coupé/overflow).
- `estBruit(url)`, `BASE`, `API`.

Modèle de script :
```js
import { ouvrir, aller, shot, lien, debordements } from './harness.mjs';
const { browser, page, journal } = await ouvrir({});
const ms = await aller(page, lien.fiche('97401000AC0428'));
// … clique, vérifie, capture …
console.log('loadMs', ms, 'err', journal.consoleErrors.length, 'http', journal.httpErrors.length);
await browser.close();
```
La 1re navigation peut prendre ~10 s (dev server froid) : mets des timeouts généreux.

## Deep-links (hash sur /socle/)
- `#idu=<IDU>` ouvre la fiche parcelle · `#c=<Commune>` pose le contexte commune
- `#m=<cléOutil>` ouvre un outil · `#admin=1` ouvre la Tour de contrôle (admin)
- `#radar=1` ouvre le Radar · `#surveillance=parcelles|secteurs|criteres`
- On peut cumuler : `#idu=<IDU>&m=<cléOutil>`.
Mais TESTE AUSSI les vrais clics (boutons, rail de gauche, recherche) — pas seulement les
deep-links — puisque le but est de vérifier que les boutons marchent.

## Clés d'outils (menu Outils)
trouver, instruire, agir, marche, temps, plu, permis, communes, calculette-fonciere,
mon-secteur, patrimoine, assemblage, comparer, risques, etude-zone, temps, programme,
gabarit, taxe-amenagement, prospection-solaire, blocs-fonciers, successions, courriers.

## Ce qu'on traque sur chaque écran et chaque action
Erreurs console JS · réponses réseau 4xx/5xx · temps d'affichage anormal · chargement sans
fin (spinner qui ne finit pas) · écran/panneau vide sans explication · bouton sans effet ·
texte coupé ou qui déborde. **Une capture pour chaque anomalie** (et des captures de
référence des écrans OK).

## Livrables (tu ÉCRIS dedans, en APPENDANT — ne réécris jamais l'existant)
Dossier : `docs/audit-2026-10/recette-generale-1/`
1. `PARCOURS.md` : ajoute une section `## <Nom de ta famille>` listant chaque écran/action
   testé avec `OK` ou `ANOMALIE (voir ANOMALIES.md #id)`.
2. `ANOMALIES.md` : pour CHAQUE anomalie, un bloc :
   ```
   ### A-<famille>-<n> — <titre court>
   - **Gravité** : bloquant | gênant | cosmétique
   - **Où** : écran + URL/hash
   - **Reproduire** : étapes numérotées
   - **Observé** : ce qui se passe (message, code HTTP, capture)
   - **Capture** : captures/<famille>/xxx.png
   - **Cause probable** : fichier:ligne si tu la trouves (grep le code en lecture seule), sinon hypothèse
   ```
   Échelle de gravité : **bloquant** (empêche l'usage / plante / chiffre faux servi) ·
   **gênant** (gêne réelle sans bloquer) · **cosmétique** (visuel mineur).
3. Captures dans `captures/<famille>/` (via `shot`).

Tu peux lire le code source (`frontend/src`, `src/labuse`) en LECTURE SEULE pour diagnostiquer
une cause probable. Tu peux requêter la base en lecture (`psql -d labuse -tAc "…"`) et l'API
pour comparer un chiffre affiché à la source.

## À la fin
Ferme le navigateur. Renvoie en texte : nombre d'écrans OK, nombre d'anomalies par gravité,
les 3 plus graves en une ligne chacune, et ce qui reste non testé si tu as dû t'arrêter.
