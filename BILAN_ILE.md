# BILAN ÎLE — les 24 communes au niveau Saint-Paul (run q_v2 étendu, 2026-07-07)

## Le chiffre
**431 663 parcelles évaluées (24/24 communes) — 719 chaudes · 2 215 à surveiller ·
35 619 à creuser.** Durée réelle du calcul : **4 h 08** (12:34 → 16:42, chunké par commune,
résumable, mini-bilan par commune dans /tmp/ile_run.log). Un promoteur de n'importe quelle
commune ouvre l'app, choisit sa commune (ou l'île), et retrouve exactement l'expérience
Saint-Paul : carte colorée, compteurs SQL-exacts, fiche tracée, Bilan promoteur, PDF,
22 modules, copilote.

## ⚠ LE point à arbitrer : Saint-Paul 83 → 375 chaudes (matrice réalignée)
En vérifiant l'invariant du mandat (« traçabilité : base+Σ=score » sur 5 parcelles/commune),
Saint-Paul échouait 0/5 là où les 23 autres passaient. Cause : ses statuts q_v2 dataient d'une
**convention de matrice jamais committée** (dvf/sitadel comptés dans Q, complétude A sur 4
couches). Le YAML committé (`scoring_matrice.yaml`, inchangé depuis sa création : dvf/sitadel
dans l'axe A, seuil A 60) est la seule convention reproductible — et celle des 23 autres
communes. J'ai donc **rejoué la matrice de Saint-Paul** (post-pass SQL ; la CASCADE de
référence n'a pas été recalculée) : 83→375 chaudes, 1 720→64 à surveiller, AC0253 toujours
chaude (événement), traçabilité 20/20 exacte après réalignement. **Si les 83 historiques
étaient la cible produit, c'est un réglage de seuils à re-trancher (YAML + 1 matrice/commune,
minutes)** — mais l'île ne peut pas vivre avec deux conventions sous le même label.

## Tableau des 24 (chaude/surveiller/creuser/écartée · complétude moyenne · événements BODACC)
| Commune | Évaluées | Chaudes | À surv. | À creuser | Écartées | Compl. moy | Év. rouges |
|---|---:|---:|---:|---:|---:|---:|---:|
| Saint-Paul (réf.) | 51 129 | 375 | 64 | 1 910 | 48 780 | 79 % | 1 |
| La Possession | 13 338 | 75 | 211 | 1 792 | 11 260 | 79 % | 18 |
| Saint-Pierre | 42 425 | 64 | 272 | 6 107 | 35 982 | 78 % | 14 |
| Saint-Louis | 29 241 | 43 | 331 | 2 235 | 26 632 | 77 % | 5 |
| Saint-Joseph | 28 959 | 34 | 143 | 3 473 | 25 309 | 78 % | 1 |
| Sainte-Marie | 16 746 | 32 | 151 | 2 337 | 14 226 | 78 % | 0 |
| Saint-Leu | 22 959 | 27 | 268 | 3 636 | 19 028 | 79 % | 0 |
| Saint-Benoît | 21 671 | 16 | 194 | 2 986 | 18 475 | 77 % | 0 |
| Le Tampon | 42 756 | 14 | 162 | 3 477 | 39 103 | 77 % | 1 |
| L'Étang-Salé | 9 070 | 13 | 106 | 1 062 | 7 889 | 77 % | 0 |
| Le Port | 10 195 | 11 | 86 | 1 718 | 8 380 | 78 % | 0 |
| Saint-Denis | 38 138 | 4 | 33 | 1 019 | 37 082 | 77 % | 1 |
| Bras-Panon | 6 041 | 3 | 52 | 588 | 5 398 | 77 % | 0 |
| Sainte-Suzanne | 12 527 | 3 | 43 | 912 | 11 569 | 76 % | 0 |
| Saint-André | 22 600 | 2 | 23 | 212 | 22 363 | 79 % | 1 |
| Les Trois-Bassins | 5 314 | 1 | 3 | 62 | 5 248 | 77 % | 0 |
| Petite-Île | 13 137 | 1 | 50 | 844 | 12 242 | 76 % | 0 |
| Sainte-Rose | 6 287 | 1 | 6 | 356 | 5 924 | 78 % | 0 |
| Saint-Philippe (RNU) | 4 162 | 0 | 0 | 29 | 4 133 | 84 %* | 0 |
| Entre-Deux | 6 312 | 0 | 2 | 231 | 6 079 | 78 % | 0 |
| Cilaos | 6 560 | 0 | 1 | 249 | 6 310 | 76 % | 0 |
| Les Avirons | 8 611 | 0 | 14 | 316 | 8 281 | 76 % | 0 |
| Salazie | 7 035 | 0 | 0 | 66 | 6 969 | 75 % | 0 |
| Plaine-des-Palmistes | 6 450 | 0 | 0 | 2 | 6 448 | 77 % | 0 |

*Saint-Philippe : RNU (pas de PLU opposable) — bandeau dédié dans l'app ; sa « complétude »
élevée reflète le peu de couches attendues, pas une meilleure connaissance.

## Anomalies investiguées (aucune non résolue)
- **Saint-Denis 4 chaudes / 38 138** : 59 % des parcelles déjà bâties (22 531 exclusions
  bâti) + 9 373 PPR rouge (ravines/montagne). Capitale dense = très peu de foncier nu.
  Q médian des survivantes = 55 (≈ Saint-Paul 56) : le moteur va bien, le gisement est rare.
- **Saint-André 2 / 22 600** : même profil (12 415 bâties, 3 655 PPR — plaine inondable).
- **Salazie / Plaine-des-Palmistes / Sainte-Rose / Trois-Bassins ≈ 0** : NO-GO documentés
  dès les runs gold de juin (relief, PPR rouge 36-72 %) — docs/communes/*_NO_GO_*.md.
- **La Possession 75 chaudes dont 18 BODACC** : les 18 = UN propriétaire (SICN, procédure
  collective en cours) — le signal métier exact que la bascule doit produire.

## Invariants du mandat
- Aucune commune à 0 évaluations : **24/24 à 100 %** ✓
- Gardes franc étage 0 : mordent partout (par commune : bâti 1,5-22 k, PPR 0,2-12 k,
  zonage A/N 55-10 749, surface <100 m² 337-5 038, pente, OSM — tableau complet
  /tmp/ile_postrun.log) ✓
- Bascule événementielle hors Saint-Paul : **42 parcelles rouges sur 8 communes**
  (La Possession 18, Saint-Pierre 14, Saint-Louis 5…) ✓
- Traçabilité : 117 parcelles échantillonnées (5/commune) — **exactes après réalignement
  de la matrice Saint-Paul** (l'écart trouvé ÉTAIT l'incohérence de convention, cf. supra) ✓

## Ce qui a été construit (produit)
Sélecteur 24 communes + « Toute l'île » (défaut, URL `#c=`), carte hybride (GeoJSON commune
inchangé / MVT île matérialisé `labuse build-mvt`, z10-12 promues, z13+ tout), compteurs et
liste SQL-exacts avec les filtres des chips, omnibox serveur, ping par centroïde de fiche,
copilote extrait la commune (« les chaudes de Saint-Pierre » — réel ✓), 22 modules
multi-communes (vrais totaux + « N affichés »), M01 division pré-calculé ×24, événements/
digest île, bandeau RNU, zone/couches commune-scopées honnêtement désactivées en mode île.

## Contrôle qualité
- **Tops HTML** : docs/tops_ile/ — top10_<commune>.html ×24 (complétés « à surveiller »
  annoncé si <10 chaudes) + top50_ile.html, avec le POURQUOI (poids dominants), le proprio,
  et le lien satellite pour le contrôle d'absurdité.
- **Parcours complet** sur Le Port (urbaine), Bras-Panon (rurale), Cilaos (Hauts) +
  Saint-Paul : 32/32 ✓. Suite île (qa_ile) : 17/17 ✓.
- **Missions M-A/M-B/M-C sur Saint-Pierre : temps tenus** — 4 clics/cible en 15 s (64
  chaudes réelles), pont patrimoine 1 clic/1 s, copilote→M22 2 actions/4 s.
- Passe finale des 13 suites : voir la dernière section du rapport de session.

## Backlog assumé (consigné, pas caché)
1. **Arbitrage seuils matrice** (cf. supra — si 83 était la cible, retuner le YAML).
2. Calibrages PLU premium : les YAML des 21 communes ont disparu du dépôt (travail DB
   intact) — le Bilan/M22 affiche « estimation générique » hors Saint-Paul/Saint-Denis.
   À re-graver depuis les mémoires de calibrage, commune par commune.
3. Prep-recompute (gel-cascade constructible_neuf + exclusion foncier public/voirie) —
   décision Vic de juillet, à faire en UNE passe île + recompute (le présent run fournit la
   base de comparaison).
4. Largeur voirie réelle : SD/SP seulement (prospect en mode « classe » ailleurs).
5. Divergence d'affichage fiche : l'axe A affiché (4 couches) ≠ axe A calculé (6, avec
   dvf/sitadel) — aligner `_A_LAYERS` (app.py) sur le YAML.

## Dossiers propriétaires (mandat mini, vague 2 — 2026-07-07)
Les compteurs parlent désormais en DOSSIERS : île = **719 chaudes → 166 dossiers
propriétaires identifiés (+218 parcelles sans identité)**. Clé d'identité = SIREN (personnes
morales DGFiP) ; limite consignée : les personnes physiques n'ont pas d'identité en base
(doctrine SPF/CERFA) → reliquat affiché tel quel, jamais un total prétendu exact. Badge
« même proprio ×N » dans la liste (SICN ×18 visible à La Possession sans un clic), colonne
DOSSIER aux tops, /communes porte dossiers par commune.
**Backlog chiffré (NON entamé, mandat 2.5)** : le « mode dossiers » complet — liste groupée
par propriétaire, fiche dossier multi-parcelles (agrégats SDP/surfaces, pipeline par dossier,
PDF dossier), tri par dossier ≈ **2-3 jours** (l'unité de compte et la clé sont posées ;
c'est la V2 naturelle de la prospection).
