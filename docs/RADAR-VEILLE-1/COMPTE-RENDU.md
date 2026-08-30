# RADAR-VEILLE-1 — Design et ergonomie du Radar et de la Veille

Branche `feat/outils-1`. Référence : `docs/maquettes/RADAR-maquette-logique-v3.html` (§01 écran, §02 notifications,
§05 dépôt agence). **Règle transversale** : un seul moteur, une seule donnée, rien en dur au front.
Postgres en lecture ; écritures = migrations propres (schéma dépôt R3, migration V3). Golden non touché.

> Note de départ : la maquette n'était pas dans le repo au chemin cité. Elle existait dans `~/Downloads/`
> en deux versions ; celle dont le **§05 est bien « le parcours agence »** (celle que le mandat décrit) a
> été installée à `docs/maquettes/RADAR-maquette-logique-v3.html` (comme les maquettes précédentes).

---

## R1 — La fiche d'une annonce redevient lisible

**Bug** : le panneau était **semi-transparent** (`bg-surface-1/97`, 97 % d'opacité) — la carte transparaissait
à travers le texte. **Correctif** : `bg-surface-1` (opaque, comme tous les autres panneaux latéraux ;
`RadarView.tsx:124`). Hiérarchie confirmée : **prix → comparaison marché → lien portail → LES FAITS
(étiquettes SOURCÉ / ABSENT conservées) → PARCELLE RATTACHÉE + critères de convergence → actions**. Aucune
donnée retirée. Capture `01-radar-fiche.png` (fond opaque, faits étiquetés, marché reformulé).

## R2 — La comparaison au marché : les trois défauts corrigés (mesuré)

Le moteur unique `pige/signaux.py::_badge` (badge liste + fiche + mails — un seul point de calcul).

**a) Référence du MÊME type** (`SEUIL_REF_TYPE = 30`) — `_dvf_bati_type` sert la médiane DVF maisons pour
une maison, appartements pour un appartement ; repli sur la référence mixte à défaut, périmètre écrit tel
quel. Mesuré : comparer au mixte donnait un écart médian **+34,8 %** (la référence mixte, tirée vers le bas
par les appartements sans terrain, sur-évalue les maisons) → **+5,4 %** en médiane maisons seule.

**b) Le biais du terrain** (le plus important). Le €/m² d'une maison est calculé sur l'habitable seul, mais
le prix inclut le terrain → toute maison à grand terrain est mécaniquement « au-dessus du marché ».
**Correction mesurée, pas au hasard** : on calcule la **part foncière** = `surface_terrain × réf. terrain nu
/ prix`. Distribution sur le corpus (25 maisons à deux surfaces) : médiane **0,54**, p75 0,82 — **16 maisons
sur 25 ont une valeur MAJORITAIREMENT foncière**. Choix : au-delà de `SEUIL_PART_FONCIERE = 0,5` (« la valeur
est majoritairement le terrain »), **aucun verdict** « sous/au-dessus » — le €/m² reste affiché avec la
mention « valeur surtout foncière — le prix au m² habitable n'est pas comparable au bâti ». (On ne décompose
PAS contre une référence incohérente, ce qui sur-corrigerait ; on refuse de trancher quand la base est
faussée.)

**Distribution AVANT → APRÈS** (écarts calculables) :

| | n | médiane | p90 |
|---|---|---|---|
| Avant (mixte, sans garde) | 102 | +25,2 % | +100,5 % |
| Après (même type + garde terrain) | 86 | +12,7 % | +69,6 % |

Maisons (54) : 38 gardent un verdict (toutes réf. same-type), **16 basculent en « valeur surtout foncière »**
(les faux positifs structurels retirés). L'exemple de Vic (Saint-Denis, 4 756 €/m², part foncière 0,82) :
**avant « +104,4 % au-dessus »** → **après verdict supprimé** (« valeur surtout foncière »).

**c) Formulation non ambiguë** (`_libelle_ecart`) : « au-dessus du marché acté (104,4 %) » (qui se lit « à
104,4 % du marché ») devient **« +104,4 % (2,04× le marché acté) »** ; sous le seuil, **« −20,9 % »** signé.
Vérifié à l'écran : « 2949 €/m² · sous le marché · **−20,9 %** · réf. **maisons** 3726 €/m² · 2025 ».

## R3 — « Publier une annonce » : le parcours agence (derrière un drapeau)

Construit d'après la maquette §05. **Drapeau `radar_depot_agence_actif` FERMÉ par défaut** (question Hoguet
en attente chez l'avocat) : endpoints → 404, UI admin invisible, rien côté client. Documenté EXPLOITATION §13.

- **Étape 1-2** — l'agence colle sa page ; `depot_agence.analyser` réutilise le parseur RADAR-DEPOT-2
  (`html_next.analyser`) — **aucun nouveau code d'extraction** ; champs pré-remplis, l'agence corrige.
- **Étape 3** — adresse exacte (seul champ ajouté) → parcelle identifiée, **rattachement CERTAIN**
  (`source`/`rattachee`, critère « adresse déclarée par l'agence », pas de cascade). L'écran montre ce que
  LABUSE ajoute (zone PLU, risques, marché, potentiel).
- **Étape 4** — publication : badge « **déposée par l'agence** », bouton « **Intéressé** » côté abonné qui
  transmet les coordonnées à l'agence (`pige_interets_agence` ; LABUSE ne s'interpose pas).

**Doctrine respectée** : adresse exacte servie aux **abonnés seuls** (jamais publique) ; **contenu confié ≠
collecté** — le déposé affiche photos + texte (`pige_faits.photos/description`), le collecté reste « faits +
lien » (`photos=[]`/`description=NULL`, jamais peuplés) ; chaque dépôt **écrit la mémoire foncière**
(`journaliser` sur l'idu). Testé en direct de bout en bout (parse 35 → publication → intérêt). Captures des
4 étapes : `05`→`08` (étape 4 : « ✓ Rattachée — déposée par l'agence · bien #… · parcelle … »).

## V1 — Veille : l'écran d'entrée sans titre

Le titre « Deux veilles » est retiré de l'écran d'entrée (`SurveillancePanel.tsx` : le `<h3>` n'est rendu
qu'une fois une porte choisie). Les deux entrées « Le foncier » / « Les annonces » inchangées. Capture `02`
(en-tête sans titre). Vérifié : `[data-surveillance-panel] h3` = `[]` sur l'accueil.

## V2 — Veille annonces alignée sur la veille parcelles

L'écran ouvre désormais sur ce que le client a déjà créé : **« + Créer une veille »** en tête, puis **« Vos
critères enregistrés »** (liste, résumé, suppression). **Les filtres n'apparaissent qu'après le clic** (dans
le formulaire de création, avec « annuler »). Captures `03` (bouton + liste) et `04` (formulaire).

## V3 — Retrait des filtres d'événement (+ migration)

Les cases « nouvelle annonce / baisse de prix / retour en ligne » sont retirées. **Conséquence assumée** :
une veille annonces notifie sur **TOUT événement** d'un bien correspondant — c'était déjà le comportement
(`veille.matche` n'a jamais filtré sur `evenements` ; le champ était inerte). Le mail (template 13) dit
l'événement. **Migration idempotente** (`copilote_v2/veilles.py::ensure_tables`) : `criteria - 'evenements'`
sur les veilles radar → celles à un seul type cochent passent à « tous les événements ». Vérifié : **0 veille
orpheline** (0 radar portant encore la clé). `VeilleIn.evenements` retiré du contrat API.

---

## Vérif finale

| Contrôle | Résultat |
|---|---|
| `tsc` (noUnusedLocals) | **0 erreur** |
| `vitest` | **108 passed** |
| `vite build` | **vert** |
| `pytest tests/` | **1999 passed, 43 skipped, 0 failed** |
| Golden | **intact** — 0 fichier `scoring/` / golden modifié |
| Écritures Postgres | schéma dépôt R3 (ALTER IF NOT EXISTS) + migration V3 (idempotentes) |
| R2 distribution | avant/après chiffrée (ci-dessus) |
| R3 flag off client | endpoints 404, UI admin masquée quand `radar_depot_agence_actif=false` |
| Veille orpheline | **aucune** |

**Fichiers**
```
 M src/labuse/pige/signaux.py        (R2 — réf. same-type + garde biais terrain + formulation)
 M src/labuse/pige/client.py         (R2 — sert la mention biais terrain ; R3 — champs déposé)
 M src/labuse/pige/api.py            (R3 — endpoints dépôt/intérêt flag-gated ; V3 — VeilleIn)
 M src/labuse/pige/tables.py         (R3 — colonnes dépôt + table pige_interets_agence)
?? src/labuse/pige/depot_agence.py   (R3 — analyser (parseur réutilisé) + publier + intérêt)
 M src/labuse/copilote_v2/veilles.py (V3 — migration idempotente criteria - 'evenements')
 M src/labuse/config.py              (R3 — drapeau radar_depot_agence_actif)
 M frontend/src/components/outils/RadarView.tsx        (R1 — opaque + hiérarchie ; R2/R3 rendu)
 M frontend/src/components/surveillance/SurveillancePanel.tsx (V1/V2/V3)
 M frontend/src/components/admin/Radar.tsx             (R3 — wizard 4 étapes, flag)
 M frontend/src/lib/api.ts                             (types R2/R3 + fonctions dépôt)
 M tests/test_pige_depot2.py         (badge : nouvelle signature _badge)
 M docs/EXPLOITATION.md              (§13 — drapeau dépôt agence)
?? frontend/qa/rv1_captures.mjs, frontend/qa/rv1_wizard.mjs  (scripts de recette)
?? docs/RADAR-VEILLE-1/, docs/maquettes/RADAR-maquette-logique-v3.html
```

**Captures** (`docs/RADAR-VEILLE-1/captures/`) — API (uvicorn :8000, flag R3 ON pour la recette) + front
(build /socle/) redémarrés : `01` fiche opaque · `02` veille entrée sans titre · `03` veille annonces
(Créer + critères, sans événements) · `04` formulaire de création · `05`-`08` les 4 étapes du dépôt agence.

**Provenance** — lectures Postgres ; migrations idempotentes ; golden non touché ; le drapeau R3 reste
**fermé** en prod jusqu'à l'arbitrage juridique.
