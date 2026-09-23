# PLU-CALIBRAGE-8 — Combler les zones U sans règles · Rapport

Branche `feat/plu-calibrage-8` (worktree `~/Desktop/labuse-plu8`, base main `51c3cdfd`). Aucun merge.
Mesure sur la base PostGIS `labuse` (lecture) ; PDF des règlements retéléchargés du GPU (md5 = `meta`
de chaque YAML, vérifié). Sondage : `captures/plu-calibrage-8/SONDAGE-10.md`.

## 0. Résultat en une ligne

Sur l'échantillon **fixe** de 3 000 parcelles zone U (le même avant/après, tiré déterministe
`ORDER BY md5(idu)`), le taux servi passe de **79,0 % → 80,6 % (+49 servies, +1,6 pt)**. Au niveau du
**PLU**, le mandat lève le blocage de **~6 428 parcelles** en zone U (23 codes de zone), servies
end-to-end à ~80 % (le reste est bloqué par la géométrie par parcelle — limite non qualifiée /
multi-zone — hors périmètre PLU).

## 1. La découverte qui change le mandat : l'audit était périmé

L'audit de couverture (base `297b2dbd`) est **antérieur** à ma base (`51c3cdfd`). Rejoué au 23/09, l'état
réel diffère : **Salazie était déjà calibrée** (hauteur transcrite), **Sainte-Rose Uc était transcrite**
mais masquée par un bug, et les deux plus gros gisements annoncés (Saint-Benoît, Salazie) sont bloqués
par des causes **structurelles**, pas par un trou de transcription. Les vrais leviers :

| Cause du blocage | Zones | Levier appliqué |
|---|---|---|
| **Hauteur fixée à l'égout, sans faîtage** — le moteur du gabarit n'utilisait que le faîtage | Salazie (2 584), La Possession UAm/UE (372), Le Tampon Ue (106), Petite-Île UE (2) | **Moteur** : repli sur l'égout (validé par Vic) |
| **Collision de casse `Uc`/`UC`** — un renvoi `UC` masquait les règles de `Uc` et se renvoyait à lui-même | Sainte-Rose Uc (1 565) | **YAML** : retrait du renvoi masquant |
| **Secteurs U jamais transcrits** | Saint-Leu (961) | **YAML** : 6 blocs `regles` |
| **Reculs (art. 6/7) manquants** (faîtage/CES déjà là) | Saint-Denis (838) | **YAML** : reculs voie + limites |
| **Hauteur = table graphique par secteur** — non portable par le schéma | Saint-Benoît (14 528) | **Reculs remis au propre + reporté** (0 servi) |
| **Hauteur « Non réglementé » / renvoi OAP** dans le règlement | Le Port (876), La Possession UAv (172) | **Non servable — reporté** |

## 2. Le geste moteur (approuvé par Vic) : hauteur à l'égout

`src/labuse/gabarit/builder.py` — quand une zone a une **hauteur à l'égout validée** mais **aucun
faîtage réglementé**, le gabarit sert désormais cette valeur (au lieu de bloquer « hauteur non
validée »). Cohérent avec `_has_usable_height` de `zonage.py`, qui traitait déjà l'égout comme une
hauteur exploitable. **Deux garde-fous exigés par Vic, respectés** :

- l'écran affiche **« Hauteur réglementaire — à l'égout : 12 m »**, jamais un faîtage implicite
  (`ApplicableRule.label = "Hauteur réglementaire — à l'égout"`, détail `"12 m à l'égout — <citation>"`) ;
- la **source cite l'article tel quel** (`MaxHeight.source.article = "Art. U 10.2"`).

Le faîtage garde la priorité quand il est réglementé (test `test_hauteur_faitage_prioritaire_sur_egout`).
Couvert par `tests/gabarit/test_builder.py::test_hauteur_egout_sans_faitage_servie`.

## 3. Zones × 4 familles — avant / après

Légende : ✅ valeur chiffrée servie · `align` = à l'alignement/en limite (recul 0) · `abs` = silence
prouvé (non réglementé, servi) · `plage/tableau` = forme non portée (reste `propose`) · `—` = absente.
« Servi » = le gabarit rend un résultat (modulo géométrie par parcelle).

### Lot A — Saint-Benoît (97410), 6 zones U, 14 528 parcelles — **0 servi (structurel)**

| Zone | voie | limites | hauteur | CES | Avant → Après |
|---|---|---|---|---|---|
| Ua/Ub/Ue/Up/Ut | `abs` ✅ | `align` ✅ | **table graphique** (`propose`) | 80 % ✅ | non calibré → **toujours non calibré** |

Le chapitre unique « ZONES U » fixe la hauteur **secteur par secteur au document graphique** (Art. U-4 :
4/7/10/13/15 m à l'égout « selon les secteurs repérés »). **Aucune valeur unique par code de zone** →
forme « tableau » non portée par le schéma, laissée `propose` (voir §7). Les reculs ont été remis au
propre (voie = silence prouvé « non réglementé sauf rues nommées » ; limites = `alignement`, « sur limite
OU ≥ 1 m ») et le tableau de hauteur consigné. **Gain servi = 0** tant que la hauteur reste un tableau
graphique — c'est un mandat d'extension de schéma, pas de transcription.

### Lot B — Salazie (97421) 2 584 p. + Sainte-Rose Uc (97419) 1 565 p.

| Commune / zone | voie | limites | hauteur | CES | Avant → Après |
|---|---|---|---|---|---|
| **Salazie** UA/UB/UC/UA1/UT | 3 ✅ | 3 ✅ | **12/9/7 m à l'égout** ✅ (repli moteur) | `abs` | 0 % servi → **~96 %** (éch. 0→24/25) |
| **Sainte-Rose Uc** | 4 ✅ | 3 ✅ | 9 m faît. / 6 m égout ✅ | 50 % ✅ | non calibrée → **calibrée** |

Salazie : la transcription était déjà complète et correcte (l'article U 10 ne fixe QUE l'égout, pas de
faîtage) ; le repli moteur du §2 la débloque. Sainte-Rose Uc : la zone était **entièrement transcrite**
(UC 6/7/9/10, citations vérifiées p.31-33) mais un bloc `UC: renvoi: Uc` la masquait (les clés de zone
sont normalisées sans casse → `UC` écrasait `Uc` et se renvoyait à lui-même = 0 règle). Renvoi retiré.

### Lot C — Saint-Leu, Le Port, La Possession, Saint-Denis

**Saint-Leu (97413)** — 6 secteurs transcrits (blocs `regles` ajoutés), tous `non calibrée → calibrée` :

| Secteur | p. | voie | limites | faîtage / égout | CES | Article (p. PDF) |
|---|---|---|---|---|---|---|
| UCA (UCa) | 842 | 3 | 3 | 9 / 6 | 50 % | UC 6/7/9/10 · p.41-44 |
| UCC (UCc) | 27 | 3 | 3 | 6 / 4 | 50 % | UC 6/7/9 · 10.3 p.44 |
| UAA (UAa) | 57 | 4 | 3 | 15 / 12 | 80 % | UA 6/7/9 · 10.3 p.24 |
| UAT (UAt) | 8 | 4 | 3 | 13 / 9 | 70 % | UA 6/7/9/10.2 · p.22-24 |
| UDP (UDp) | 20 | `align` | 3 | 6 / 4 | 40 % | UD 6.2/7/9/10 · p.52-54 |
| UDB (UDb) | 7 | 3 | 3 | 6 / 4 | 40 % | UD 6/7/9/10 · p.51-54 |

(UFe = **secteur « toute construction interdite »**, Art. UF 1.10 — laissé non transcrit.)

**Saint-Denis (97411)** — 7 secteurs, reculs (art. 6/7) ajoutés (faîtage/CES déjà présents) :

| Secteur | p. | voie | limites | (hauteur déjà là) | Article recul (p.) |
|---|---|---|---|---|---|
| Udp | 343 | 4 | 4 (4≤L≥h/2) | faît. 18 / CES 70 | Ud.6 p.42 · Ud.7 p.43 |
| Uva | 221 | 4 | 4 | faît. 4 | Uv.6/7 p.83 |
| Uvl | 179 | 4 | 4 | faît. 10 | Uv.6/7 p.83 |
| Udop | 55 | 4 | 4 | faît. 18 / CES 70 | Ud.6 p.41 · Ud.7 p.43 |
| Uvac | 23 | 4 | 4 | faît. 10 | Uv.6/7 p.83 |
| Upi | 11 | 3 | 3 | faît. 11 / égout 6,5 / CES 80 | Up.6 p.32 · Up.7 p.33 |
| Upr | 6 | 4 | 4 (+ 6 m falaise) | faît. 16 / égout 12 / CES 70 | Up.6/7 p.32-33 |

Note Saint-Denis : **Ud (3 435 p.) était DÉJÀ servi** (hauteur en prospect `hauteur_mode`), l'audit le
comptait à tort bloqué. Uip/Uma/Udo restent non calibrés (hauteur absente/non exploitable dans le PLU).

**Le Port (97407)** — **0 servable** : le règlement ne fixe **aucune hauteur** pour les zones cibles.
Ue (voie 5 m, limites `align`, CES 60 %) n'a de hauteur que pour le sous-secteur Uem (18 m) ; Uv/Up/Uppp
= tout « Non réglementé » ; Uoap = **renvoi OAP « Portes de l'Océan »** (valeurs hors règlement). Sans
hauteur, le gabarit ne peut pas servir → **non transcrit, reporté**.

**La Possession (97408)** — UAm/UE (372 p.) **débloquées par le repli égout** (§2). UAv (172 p.) :
hauteur **par îlot opérationnel** (tableau, Art. UA 10.2) = même cas que Saint-Benoît → non servable.
**« Up » n'existe pas** dans ce PLU (vérifié : sommaire + extraction texte). Reporté.

## 4. Mesure — avant / après (échantillon fixe 3 000, zone U)

| | Servies | Bloquées | Taux |
|---|---|---|---|
| **Avant** (base `51c3cdfd`) | 2 370 | 630 | **79,0 %** |
| **Après** | 2 419 | 581 | **80,6 %** |
| **Δ** | **+49** | −49 | **+1,6 pt** |

Δ par commune (échantillon) : **Salazie 0→24/25** · Saint-Denis +8 · Saint-Leu +6 · **Sainte-Rose +6** ·
La Possession +4 · Le Tampon +1 · Saint-Benoît **0** (structurel) · Le Port **0** (structurel). Méthode :
`scripts/gabcouv_ile.py` (copié dans ce worktree) + variante à échantillon fixe reproductible.

**Débloqué au niveau PLU (capacité, avant plafonnement géométrique) : ~6 428 parcelles / 23 zones** —
Salazie 2 584 · Sainte-Rose Uc 1 565 · Saint-Leu 961 · Saint-Denis 838 · La Possession UAm/UE 372 ·
Le Tampon 106 · Petite-Île UE 2.

Zones passées **`non calibrée` → `calibrée`** (bascule stricte du drapeau) : **7** (Sainte-Rose Uc +
Saint-Leu ×6). Zones **calibrées mais débloquées** (repli égout ou reculs ajoutés) : **16** (Salazie ×5,
Saint-Denis ×7, La Possession ×2, Le Tampon ×1, Petite-Île ×1).

## 5. Verdict Uavap (Saint-Denis, 3 507 p. — lecture seule)

Les articles **Uavap.6 (voies), Uavap.7 (limites séparatives), Uavap.9 (emprise), Uavap.10 (hauteur)**
disent tous, mot pour mot (p.28-29) : *« Il sera fait application des prescriptions mentionnées dans
l'AVAP annexé au PLU, en son article … de son chapitre "Prescriptions particulières par secteur" sur
chacun de ses 6 secteurs. »* → **le règlement du PLU ne fixe AUCUN recul, hauteur ni emprise chiffrés
pour Uavap** ; tout est délégué à l'AVAP annexée (document patrimonial séparé, prescriptions
architecturales par secteur, hors schéma actuel). **Rien à transcrire depuis le règlement** ; une
calibration exigerait de lire l'AVAP et d'étendre le schéma (secteurs patrimoniaux).

## 6. Contrôles

- **Sondage 10/10 concordent** (valeur servie = texte du PDF, image relue) — `captures/plu-calibrage-8/SONDAGE-10.md`.
- **`registre.verifier()` → 0 anomalie.**
- **Verrou V6a** (aucune feuille `valide` sans citation, sur les 5 communes touchées) → **0**.
- **Toutes les citations transcrites relues sur l'image du PDF** : Saint-Leu UA p.22-24 / UC p.41-44 /
  UD p.51-54 ; Saint-Denis Up p.32-33 / Uv p.83 ; Sainte-Rose Uc p.31-33 ; Salazie p.15 ; Saint-Benoît
  p.9-13. **0 divergence.**
- **`tests/gabarit` : 16/16** (dont 2 nouveaux pour le repli égout).
- **`pytest tests/` complet : 3266 passed, 7 failed, 64 skipped (19 min).** Les **7 rouges sont tous
  pré-existants / dépendants de l'environnement** (aucun ne touche le gabarit ni la calibration) :
  `test_module_unique_aucune_autre_lecture` (grep la chaîne `plu_destinations`, présente à
  `builder.py:42` `PLU_PROVIDER` **avant** ce mandat) · `test_deps_declared` (import `matplotlib`
  non déclaré, ailleurs) · `test_reparations1_lot2` (connu, cf. mémoire TESTS-0) · `test_front_reliquats`
  · `test_retours17_permis` · `test_scoring6_score_labuse` · `verrous/test_lot1_tables` (base réelle
  absente de `labuse_test`). **0 régression introduite.**

## 7. Ce qui reste `propose` / non servable — et pourquoi

| Cas | Zones | Raison | Piste (hors mandat) |
|---|---|---|---|
| **Hauteur = table graphique par secteur** | Saint-Benoît Ua/Ub/Ue/Up/Ut (14 528), La Possession UAv (172) | 4-15 m à l'égout (ou par îlot) « selon le document graphique » — pas de valeur unique par code de zone | Étendre le schéma (hauteur par secteur graphique / par îlot) + digitaliser les secteurs |
| **Hauteur « Non réglementé »** | Le Port Uv/Up/Uppp/Ue-base (≈765) | Le règlement ne fixe aucune hauteur → gabarit incalculable | Décision d'urbanisme (le PLU ne borne pas la hauteur) |
| **Renvoi OAP** | Le Port Uoap (111) | Valeurs dans l'OAP « Portes de l'Océan » (pièce n°4), hors règlement | Ingestion de l'OAP |
| **Uavap** | Saint-Denis (3 507) | Renvoi intégral à l'AVAP annexée (prescriptions par secteur) | Lire l'AVAP + schéma patrimonial |
| **Hauteur absente / non exploitable** | Saint-Denis Uip/Uma/Udo (145) | Faîtage absent (silence) sans égout, ou prospect non métré | — |

## 8. Commandes clés

```
# PDF (md5 vérifié = meta YAML) : packs GPU dézippés dans /tmp/plu8/
# état par zone U (calibree / hauteur / reculs) :
PYTHONPATH=src <venv>/python scripts/gabcouv_zoneU_regles.py
# mesure échantillon fixe avant/après (repli fichiers base via cp+git checkout, jamais git stash) :
PYTHONPATH=src <venv>/python scripts/gabcouv_ile.py 7 3000 U
# contrôles :
python -c "from labuse import registre; print(registre.verifier())"     # -> []
python -m pytest tests/gabarit -q                                        # 16 passed
```

## 9. Reste pour Vic

- **Merge** (aucun fait ; un commit par lot : moteur repli-égout / Lot A / Lot B / Lot C / Lot D).
- **`residuel-serve` + recalcul `parcel_residuel`** — hors mandat (rien de servi n'a été recalculé).
- Décider s'il faut **étendre le schéma** pour la hauteur en table graphique (Saint-Benoît 14 528 p.,
  le plus gros gisement restant) et pour l'AVAP de Saint-Denis Uavap (3 507 p.).
