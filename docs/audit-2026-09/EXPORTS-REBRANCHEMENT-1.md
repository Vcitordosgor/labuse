# EXPORTS-REBRANCHEMENT-1 — Les documents lisent la fiche (compte rendu)

20/09/2026 · branche `feat/exports-rebranchement-1` depuis main `85ac26a5` · un commit par lot ·
aucun merge, run servi intact. Sessions : backend :8075, base locale.

## Le principe livré

**Le Dossier est le miroir de la fiche parcelle.** Il ne collecte plus rien : les 11 sections
(mêmes noms, même ordre — `declarations/fiche/sections.yaml`), chaque ligne, chaque libellé,
chaque phrase d'absence viennent des déclarations de la fiche ; chaque valeur vient du robinet
unique (`exports/robinet_fiche.py`, le payload `/parcels/{idu}` — celui de l'écran) ; chaque
nature vient du registre. **Flash = Dossier** : un nom commercial, rendu identique, même numéro.
La maquette v4 validée par Vic (`EXPORTS/maquettes-v4/`, commit `3ab86a63` en cours de session)
suit la même structure §1→§11 « fiche ① → ⑪ » — la colonne « source par ligne » de la maquette
est l'itération suivante du rendu.

## Lot 0 — les 5 anomalies de l'audit, corrigées à la source (`658b8456`)

1. **54 %/100 % même zone rouge** : l'arbitrage servi (`risques_arbitrage`, point unique M73)
   ne garde qu'UNE exclusion « PPR zone rouge » (part max) — les verdicts stockés au run ne
   nomment pas leur plan, deux rouges côte à côte se lisaient comme une contradiction. Couvre
   fiche + 4 documents + pré-dossier (tous lisent `served_cascade_lines`).
2. **« Zone Nerl » vs « N 100 % »** : `_reglement_plu_block` groupait par `subtype` et
   `max(libelle)` faisait GAGNER le libellé du liseré (Nerl 0,2 %) sur la dominante (N 99,8 %) —
   le Dossier servait le nom et les règles de la mauvaise zone. Groupé par CODE de zone réel
   (même token que `zone_servie`) ; le tableau du Pré-dossier filtre les liserés < 2 %.
3. **NPNRU « ƒ dérivé »** : la nature lit le drapeau `derive` du producteur (ANRU/QPV = sourcé).
4. **Millésimes / « à jour du GPU » côté client** (doctrine PAGE-SOURCES-1 18/09) :
   `plu_fraicheur` dit « Document opposable — il fait foi à ce jour » ; taxe sans « source
   DGFiP/DELTA, relevé le … » ; fenêtre DVF servie « 2021-2025 » (normalisée au service).
5. **`emprise_max_m2`** : ligne morte du pré-dossier retirée.

## Lot 1 — débranché (`d3365621`)

- `declarations/fiche/sections.yaml` + `fiche_section` par surface (surcharge par ligne) ;
  **74 lignes déclarées** (+2 que l'écran montrait déjà : dernière vente DVF, fraîcheur PLU).
- `exports/miroir.py` : rendu générique des 11 sections — bandeaux verdicts (mêmes moteurs que
  l'écran), groupes déclarés, « **Vérifié, sans objet** » en petit (phrases d'absence déclarées,
  repliés-dépliés du PDF), chaque ligne tamponnée `data-quoi`.
- `exports/robinet_fiche.py` remplace `collecte.py` (supprimée) : **69 extracteurs** id→payload.
  5 ids déclarés restent non câblés (dits) : `charge_fonciere_eur`, `divisible_classe`,
  `parcelle_geometrie`, `population_zone`, `verdict_icd`.
- **V5d étendu** : le verrou rend le miroir sur une fiche synthétique et vérifie chaque
  `data-quoi` ⊆ déclarations — « toute ligne du Dossier est une ligne de la fiche ».

## Lot 2 (`35bc79b9`) — §11 = renvoi au Financier ; sources = des NOMS (aucun millésime,
aucune date) dans la clôture, les pieds de section (tous documents) et l'encart fiscalité du
Financier. Millésime DANS un nom de produit (INSEE RP2022, QPV 2024) = le nom du jeu, gardé.

## Lot 3 (`4c5789ea`) — le Pré-dossier PC au circuit : la route ZIP lit LA FICHE une fois ;
surface/emprise de PCMI2/PCMI4 = les robinets de l'écran ; zonage déjà `zone_dominante` ;
3 verrous de non-contradiction (`tests/test_rebranchement1_lot3.py`), verts sur base réelle.

## Lot 4 (`0becad57`) — Apporteur : 14/14 ids déclarés, abréviation PLU au niveau du lot 0,
cohérence croisée AN0347 (Zone N, 4 501 m², 337 m², une seule rouge) — fond v3 inchangé.

## Lot 5 (`871206fb`) — audit du questionnaire Financier (rapport seul,
`EXPORTS-REBRANCHEMENT-1-LOT5.md`) : 19+3 champs, aucun mort ; indispensables stricts = 2 ;
chemin vers UNE question bloquante (TVA) via le pré-remplissage du prix de sortie depuis
`prix_sortie_bati_eur_m2` ; **assiette VRD démontrée fausse** (terrain entier × 90 € = 405 k€
pour 4 logements sur AN0347) — reco : SDP du projet. Vic tranche.

## Les preuves

- **Écran = PDF, ligne à ligne, par section** (`captures/rebranchement1/*-preuve.txt`) :
  chaque ligne déclarée confrontée au fragment `data-quoi` du PDF —
  **AN0347 : 35 identiques · 34 absences dites · 5 non câblées · 0 écart** ;
  **BO0852 (parcelle simple) : 42 identiques · 27 absences dites · 5 non câblées · 0 écart**.
  (Preuve DOM/JSON — précédent des sessions carte : la capture pixel reste l'œil de Vic.)
- **pdftotext diff Dossier/Flash = VIDE** (même numéro DP) — prouvé au builder ET rejoué par la
  recette sur chaque témoin (« Flash = Dossier (pdftotext identiques) »).
- **Pré-dossier : zonage identique au Dossier** — `[N 100 %]` = `zone_dominante` (AN0347),
  liseré Nerl filtré ; une seule exclusion rouge partout.
- **V5d prouvé cassé puis vert** : ligne inventée `ligne_inventee_pdf` →
  `casse — « ligne du Dossier hors déclaration fiche »` ; retirée → `ok — 66 données … · 63
  lignes du Dossier miroir, toutes déclarées`.
- **Recette rejouée** (`scripts/recette_exports1.py`, mise au niveau : Résumé supprimé
  RECETTE-3 retiré du script, Pré-dossier ZIP ajouté, Financier 422 « non établissable » =
  comportement V18b documenté, contrôle Flash=Dossier ajouté) — **RECETTE VERTE** sur les
  4 témoins : dossier/apporteur/flash rendus + archives, ZIP pré-dossier servi, surfaces et
  prix ancien écran=PDF, « Flash = Dossier (pdftotext identiques) » ×4, 0 mot interdit.
  (Un premier passage concurrent du pytest complet était tombé sur un idle-in-transaction —
  relancée seule, verte.)
- **tsc -b vert** · **pytest tests/ complet : 3125 verts · 5 échecs TOUS pré-existants sur
  main `85ac26a5`** (circuit2_lot16, circuit2_lot5, retours11f4 ×2, garanties G4 — chacun
  rejoué ROUGE dans le worktree labuse-merge sur main ; la branche n'ajoute aucun rouge) ·
  62 skips · 19 min 22 ·
  **`labuse circuit verrous -w G8`** : 28 joués (20 verrous + 8 garanties), tout va bien,
  **G8 en avertissement NON bloquant** — 15 sources vitrine sans sonde amont (« l'agent est à
  0 € ») + rappels manuels échus : état d'EXPLOITATION pré-existant, indépendant de la branche
  (le rendre vert = débloquer le budget agent ou pointer les rappels — gestes Vic).

## Hors périmètre, constaté

- `test_circuit2_lot16` (exposition_versant passe-plat sans table) et `test_circuit2_lot5`
  (`<Trace id=…>` attendu dans Fiche.tsx) échouent AUSSI sur main `85ac26a5` (vérifié dans le
  worktree labuse-merge) — pré-existants.
- Le front (Fiche.tsx) reste codé en dur : les déclarations décrivent l'écran mais ne le
  RENDENT pas encore — le raccordement de l'écran aux déclarations est le chantier
  RACCORDEMENT (hors mandat). Le PDF, lui, est désormais 100 % déclaré.
