# PLU-CALIBRAGE-8 (oct. 2026) — Rapport

Branche `feat/plu-calibrage-8` (worktree `~/Desktop/labuse-plu8`, base main `3f473aa3`). Aucun merge,
rien sur le VPS, aucune écriture en base. Règlements retéléchargés du GPU, **md5 vérifié = `meta` de
chaque YAML** avant toute lecture. Mesures en lecture sur la base `labuse`. Un commit par lot.

## Verdict (5 lignes)

1. **22 zones débloquées** (111 → 89 zones U/AU non servables), couvrant **2 647 parcelles dont
   1 654 à potentiel** — gabarit `incomplete` → `ok`, sans aucun run.
2. **~43 feuilles de règles validées** (citation + article + page, relues au PDF) sur **8 zones**
   transcrites (Saint-Denis AUm/AUh/AUj, Saint-Leu AUa–e) ; **3 feuilles `propose` fermées**
   (U1pru, U5cvd, Uep → feuille_propose 3→0).
3. **Un seul geste moteur** (B.1) : une zone AU qui tire ses règles d'un `renvoi:` est désormais
   reconnue **calibrée via renvoi** (+ zones AU phasées `1AU/2AU`) → débloque Saint-André et
   Saint-Louis **sans recopier une seule valeur** (renvois portés comme renvois).
4. **0 régression** : dry-run 88 parcelles (70 débloquées / 0 régression), 220 parcelles témoins
   hors zones touchées **byte-identiques** avant/après, témoins PLU-CALIBRAGE-4 + CHASSE-CALCULS-1 B1
   verts, V6a + validées-only verts, `registre.verifier()` = 0.
5. **Le reste (89 zones, ~13 200 pot.) est STRUCTUREL** — hauteur en table graphique (Saint-Benoît),
   emprise en m² absolus (Usdu), renvoi AVAP (Uavap), hauteur en niveaux (UBm) ou par îlot (UAv),
   silence du règlement (Le Port), OAP — **hors du schéma actuel** : non calibrable sans extension
   de schéma (décision Vic séparée) ou lecture de pièces annexes (AVAP/OAP).

## Lot A — inventaire (commit Lot A)

`scripts/plu8_inventaire.py` reproduit la décision de blocage AU NIVEAU ZONE de `gabarit/builder.py`
sur toutes les zones U/AU : **111 zones non servables** (25 207 parcelles, 17 474 à potentiel q_v18),
classées par cause (mandat) et par nature (calibrable / structurel / AVAP). Liste > 60 →
**STOP**. Vic a tranché : **« calibrables avec le schéma actuel, par potentiel décroissant »**.
Détail : `INVENTAIRE.md`.

## Lot C — U1pru (commit Lot C)

U1pru (Saint-Paul) était non calculable depuis PLU-CALIBRAGE-6 : sa feuille
`retraits.limites_separatives` portait une valeur `min_m 3 m` **inventée** (PLU-VERIF-1 l'avait, à
juste titre, dégradée en `propose` → `regle_non_validee` → « capacité non calculable »). Le règlement
en vigueur (md5 `0aee7298…`, Art. 7 p.21) dit : *« Chaque construction pourra s'implanter sur une
limite séparative sans limitation de longueur. En cas de retrait, celui-ci ne pourra excéder 5
mètres. »* → implantation **EN LIMITE** = recul 0 = `forme: alignement` (forme du schéma existant,
PLU-CALIBRAGE-7) ; le « ≤ 5 m » est un plafond permissif, non modélisé. Idem la voie (Art. 6 p.19,
« à l'alignement »). Les deux feuilles passent `forme: alignement` / `valide`. U1pru résout :
he 30 / hf 34 / reculs alignement / stationnement exempt / R+9 borné par le plafond de densité.
**Les 2 tests xfail de `tests/test_faisabilite.py` redeviennent des tests verts** (xfail retiré).

## Lot B — calibration (commits B.1 / B.2 / B.3)

### B.1 — moteur : renvoi AU→U reconnu, zones AU phasées
`regles_zone` suivait déjà le `renvoi:` pour les VALEURS (overlay), mais `_resolve_zone_base` laissait
la zone `calibree=False` → le gabarit la bloquait « PLU non calibré (estimation générique) ». Ajout :
- `destinations.renvois_commune()` : `{zone: cible}` des zones renvoi-only ;
- `zonage._resolve_zone_base` : ces zones sont résolvables et **calibrées via renvoi** (`via_renvoi` porté) ;
- repli **zone AU phasée** `<n>AU<indice>` → `AU<indice>` (1AU/2AU = phasage, mêmes règles par indice),
  cohérent dans `zonage` et `destinations._zone_regles_brut`.

Additif (ces codes ne trouvaient aucun hit avant). **Débloque Saint-André** (AUb/AUc/AUd + 1AUc/1AUb/
1AUd/2AUc/2AUd + 2AUb/2AUe/1AUe) **et Saint-Louis** (1AUb1/1AUb2/2AUb1/2AUb2, renvoi `UB` déjà au YAML)
— **sans toucher au YAML ni recopier une valeur**.

### B.2 — transcription AU à chapitre propre (propose/relecteur)
Méthode PLU-CALIBRAGE-5 : agent proposeur lit le règlement md5-vérifié, **chaque citation est relue
à la page PDF citée** avant insertion (`scripts/plu8_appliquer_regles.py`, insertion sans reparse).
- **Saint-Denis** (md5 `43426a8f…`) : AUm (faîtage 10 / égout 7 / CES 50 %), AUj (13/10/60 %),
  AUh (7/4,5/30 %) — reculs voie 4 m + limites alignement. Art. AU*.6/.7/.9/.10, p.92-103.
- **Saint-Leu** (md5 `d74416f9…`) : AUa (12/9/80 %), AUb (10/7/60 %), AUc (9/6/50 %), AUd (6/4/40 %),
  AUe (égout 10, faîtage complété par UE / 60 %). Art. AU 6/7/9/10, p.87-91.

### B.3 — feuilles `propose` validées + Usdu corrigée
- **Saint-Joseph U5cvd** : `min_m 5 m` (inventé) → **3 m valide** + formule H/2 (Art. U5 7.2 p.78,
  « minimum de 3 mètres », identique à la zone sœur U5cv).
- **Saint-Pierre Uep** : emprise **0,2 % valide** = conversion exacte de « 20 m² par ha » (Art. Ue3.4
  p.192).
- **Saint-Paul Usdu** : citation « INTROUVABLE » corrigée → Art. 9 (emprise en **m² ABSOLUS par
  destination** : 150 m² habitation, 200 m² équipements…) ; forme hors schéma CES % → **reste
  `propose` à juste titre** (la servir en % surestimerait).

## Lot D — preuve

- **D1 — dry-run** (88 parcelles, lecture seule, avant=`main` / après=branche) : **70 débloquées
  (incomplet → calculé), 0 régression** ; les 18 restantes bloquent sur la **géométrie** (limites non
  qualifiées, multi-zone), hors PLU. `DRY-RUN.md`.
- **D2 — non-régression** : 220 parcelles témoins hors zones touchées → **0 différence avant/après
  (byte-identique)** ; témoins PLU-CALIBRAGE-4 + CHASSE-CALCULS-1 B1 verts.
- **D3 — sondage 10/10** concordent (valeur servie = texte du règlement, extrait relu à la page).
  `SONDAGE-10.md`.
- **D4 — bancs & gardes** : **V6a** (aucune feuille `valide` sans citation) vert sur le registre réel ;
  **base validées-only** (PLU-CALIBRAGE-6) verte ; `banc_chasse_calculs` **✓ 10/10** ; `banc_calcul`
  **✓ 1 025 comparaisons, 1 seul écart TOLERABLE** (`pipeline.mult_base` 0,86 vs 0,85 sur
  `97415000CL0181` — arrondi de score PRÉ-EXISTANT, hors périmètre PLU : ce mandat ne touche ni la
  géométrie, ni DVF, ni la taxe, ni le signal/bandes) ; `registre.verifier()` → **0 anomalie** ;
  suites zonage / destinations / faisabilité / gabarit (`tests/gabarit` 16/16) / calibrage4-6-7 vertes.

## Ce qui reste (89 zones, hors schéma actuel)

| Cas | Zones (pot.) | Pourquoi | Piste (hors mandat) |
|---|---|---|---|
| Hauteur en table graphique | Saint-Benoît Ua/Ub/Ue… (~13 000) | 4-15 m à l'égout « selon le document graphique », pas de valeur unique par code de zone | Étendre le schéma (hauteur par secteur graphique) + digitaliser les secteurs |
| Emprise en m² absolus | Saint-Paul Usdu (845) | Art. 9 = plafonds m² par destination, pas de CES % | Extension schéma (plafond emprise absolu) |
| Renvoi AVAP | Saint-Denis Uavap (790) | Renvoi intégral à l'AVAP annexée | Lire l'AVAP + schéma patrimonial |
| Hauteur en niveaux / par îlot | La Possession UBm (R+3) / UAv (table îlot) | Pas de hauteur métrique → gabarit 3D indisponible | Conversion niveaux→m (décision) / digitaliser les îlots |
| Silence / OAP / secteur technique | Le Port Uv/Up/Uoap, Saint-Leu AUS… | Le règlement ne fixe rien, ou renvoie à l'OAP, ou secteur exclusivement technique | Décision d'urbanisme / ingestion OAP |

## Pour Vic

- **Merge** (aucun fait ; 5 commits : Lot A / Lot C / B.1 moteur / B.2 transcription / B.3 propose).
- **Run** : les 1 654 parcelles à potentiel débloquées migreront `residuel_legacy → gabarit` au
  **prochain run** (recalcul `compute_residuel` + score) — ce mandat n'a **rien recalculé** ni servi.
- **Décision d'extension de schéma** pour le gisement structurel restant (Saint-Benoît ~13 000 p.,
  le plus gros), si souhaité — mandat séparé.

## Commandes clés

```
# inventaire (lecture seule) :
LABUSE_DATABASE_URL=postgresql+psycopg://<user>@/labuse PYTHONPATH=src <venv>/python scripts/plu8_inventaire.py [--md]
# dry-run avant/après (répété dans chaque worktree) : /tmp/plu8_dryrun.py (cf. DRY-RUN.md)
# gardes :
PYTHONPATH=src <venv>/python -c "from labuse import registre; print(registre.verifier())"   # -> []
PYTHONPATH=src <venv>/python -m pytest tests/test_faisabilite.py tests/gabarit tests/verrous/test_lot6a_regles_citations.py -q
PYTHONPATH=src <venv>/python -m scripts.coherence.recalcul.banc_calcul
PYTHONPATH=src <venv>/python docs/audit-2026-10/chasse-calculs-1/banc_chasse_calculs.py
```
