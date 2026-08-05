# M29 — DETTES #9 (mérite/héritage) & #11 (acquérabilité) — MESURE, POINT D'ARRÊT (05/08/2026)

> Base vérifiée : 394ee4a (M28) dans main (merge be3b5e0). Rien ne bascule. Le « run servi »
> du mandat (« q_v12_m28 ») est, au sens strict, le label servi `q_v8_calibre` dont le contenu
> ≡ q_v12_m28 + AK1442 — mesures faites sur le servi.

## 1 · État des lieux (définitions CITÉES, pas présumées)
### #9 — V8_DETTES_CONSIGNEES.md:79-88 (texte source)
« comparer, pour chaque parcelle qui gagne un tier, son contrib_d et son rang AVANT/APRÈS —
inchangés ⇒ héritage, en hausse ⇒ mérite. […] Préférence Vic (30/07) : ça relève de la FICHE,
pas du log. » → Ce N'EST PAS la succession (les mesures veille_succession sont rapportées en
annexe-contexte : 32 du top 1000, dont 6 brûlantes — définition code : PM SIREN ∧ dirigeant
≥ 70 ans OU SCI dormante, computed 2026-07-12, source RNE/INPI).
- Existant : contrib_d + rang persistés PAR RUN + archives de bascule (pre_pond/pre_regle/
  pre_m28) → l'instrument du texte est ENTIÈREMENT calculable. **Sourcé.**
- Manquant : le champ de fiche (« montée par héritage de place le JJ/MM » vs « par mérite »)
  et son calcul au geste de bascule.

### #11 — V8_DETTES_CONSIGNEES.md:103-113 (texte source)
« la contiguïté est GÉOMÉTRIQUE — elle ne dit rien de l'acquérabilité. […] croiser les
voisines avec la PROPRIÉTÉ (DGFiP / personnes morales). MÊME propriétaire (division simple)
vs propriétaires DISTINCTS (assemblage à négocier). »
- Existant : voisines contiguës (au_ouverture.voisins_assemblables, servies en mention) ;
  parcelle_personne_morale (82 701 lignes, 12 605 SIREN — DGFiP/Cerema via ODS Région,
  **sync non tracée** → spec millésime) ; owner_type ; copro (0 en tête par construction).
- Manquant structurel : la propriété des PERSONNES PHYSIQUES (anonymisée à la source) —
  **Absent, non contournable.**

## 2 · Mesures #9 (servi vs archive pre_m28)
**288 gagnants de tier à la bascule M28 → 288/288 « héritage de place »** (contrib_d
strictement inchangé — attendu : bascule à features constantes, les places libérées par les
296 saturées). 0 « mérite ». CSV : dette9_gagnants_m28.csv. En généralisant sur la chaîne
d'archives du 04-05/08 : même mécanique (toutes les bascules du train étaient à signal
constant). Le distinguo ne devient discriminant qu'aux re-runs à features rafraîchies —
exactement le cas d'usage du texte.
**Règle vs signal — distribution :** en règle (ex. « héritage n'entre pas en tête »), les 288
sortiraient : la tête tomberait à ~750 SANS recomposition possible (toute recomposition est
elle-même un héritage) — une règle est LOGIQUEMENT INCOHÉRENTE avec le mécanisme de quota.
En signal : 0 mouvement, information servie.

## 3 · Mesures #11 (les 1 069 au_sous_plancher servies)
| classe (parcelles avec ≥1 voisine contiguë même zone : 1 060) | n | étiquette |
|---|---:|---|
| **division simple** (≥1 voisine MÊME SIREN) | **329 (31 %)** | Sourcé (SIREN DGFiP) |
| assemblage à négocier (PM distinctes, aucune même-SIREN) | 46 | Sourcé |
| indéterminé (PP anonymisées d'un côté ou de l'autre) | 685 (65 %) | **Absent** |

Couverture propriétaire top 1000 servi : PM connue 297/1000 (29,7 %) ; PP ~70 % = angle
mort structurel de la source.

## 4 · Recommandations (arbitrage Vic)
**#9 → (b) SIGNAL DE FICHE** — conforme à ta préférence 30/07 (« fiche, pas log »), conforme
doctrine (la lignée d'un score n'est pas un état de parcelle ; en règle elle serait
incohérente avec le quota — démontré §2). Population : les gagnants de chaque geste (288 au
M28) ; mouvements en tête : 0 (signal). Données : contrib_d/rang archivés — **Sourcé** ;
implémentation : comparaison à l'archive au geste de bascule + champ fiche.
**#11 → (b) SIGNAL DE FICHE enrichissant la mention assemblage**, en 3 états étiquetés :
« division simple (même propriétaire, Sourcé SIREN) » (329) · « à négocier (propriétaires
distincts, Sourcé) » (46) · « propriété non déterminable (personnes physiques anonymisées —
Absent) » (685). PAS une règle : l'acquérabilité PP est Absente pour 65 % — une règle sur
35 % de couverture violerait « le doute ne profite jamais au classement » dans les deux sens.
La part PP reste dette maintenue, manquant nommé : source de propriété PP inexistante en
open data (structurel, pas un chantier).

## Livrables (ls -la)
total 160
drwxr-xr-x   5 openclaw  staff    160  5 aoû 13:05 .
drwxr-xr-x  48 openclaw  staff   1536  5 aoû 13:04 ..
-rw-r--r--   1 openclaw  staff   4542  5 aoû 13:05 M29_MESURE.md
-rw-r--r--   1 openclaw  staff  45705  5 aoû 13:05 dette11_acquerabilite.csv
-rw-r--r--   1 openclaw  staff  21389  5 aoû 13:04 dette9_gagnants_m28.csv
