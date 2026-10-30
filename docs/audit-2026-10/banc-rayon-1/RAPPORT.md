# BANC-RAYON-1 — Rejeu du banc d'estimation (Lot A) & rayon de rattachement par source (Lot B)

Branche `feat/banc-rayon-1` · worktree `labuse-bancrayon` · 30/10/2026 · **aucun accès prod, pas de merge**.
Base servie Mac `postgresql:///labuse` (PROD = LOCAL), lecture seule, aucune session créée.
Interdits respectés : rien touché aux Études ni à `api/documents.py`.

---

## Tableau 1 — Lot A : précision de l'estimateur, banc 1 (ancien) contre banc 2 (actuel)

Même univers (**5 592 ventes DVF 2025** des 24 communes), même règle **SANS FUITE** qu'au banc 1
(estimation reconstruite avec `date_mutation < date_vente` + exclusion de la mutation jugée). Les deux
estimateurs sont calculés **dans le même passage** → comparaison apples-to-apples.
Écart = médiane de `|estimé / réel − 1|` sur le €/m². Contrôle de fuite : **0 violation / 5 592** des deux côtés.

| Segment | N | **banc 1** médian \|écart\| | ±10 % | ±20 % | non est. | **banc 2** médian \|écart\| | ±10 % | ±20 % | non est. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Toutes ventes** | 5 592 | 27,9 % | 19,6 % | 38,3 % | 1,7 % | **26,4 %** | 20,8 % | 40,4 % | 1,7 % |
| **Appartement** | 2 076 | 17,1 % | 30,9 % | 57,9 % | 1,1 % | **17,3 %** | 30,3 % | 56,8 % | 1,1 % |
| **Maison** | 2 292 | 31,8 % | 15,5 % | 31,6 % | 0,3 % | **28,0 %** | 19,3 % | 37,9 % | 0,3 % |
| **Terrain nu** | 1 224 | 633 % ⚠ | 7,5 % | 16,9 % | 5,3 % | **712,8 %** ⚠ | 7,2 % | 16,4 % | 5,3 % |
| **Copropriété** (parcelle) | 2 130 | 17,1 % | 30,7 % | 57,5 % | 1,0 % | **17,4 %** | 29,9 % | 56,4 % | 1,0 % |

> **Le seul mouvement net et voulu : la MAISON passe de 31,8 % à 28,0 %** (−3,8 pts, et ±20 % de 31,6 % → 37,9 %).
> C'est l'effet direct du comparateur **maisons↔maisons** : 1 558 des 2 292 maisons (68 %) sont désormais
> estimées sur des **maisons** (médian 25,6 %, biais quasi nul −1,4 %) au lieu d'appartements (33 %). Les
> 574 maisons restantes tombent dans un secteur réellement dominé par les appartements → encore pricées
> appartement (33,5 %) : le résiduel du biais maison. Appartement et copropriété sont **stables** (le
> comparateur appartements est le même) ; **terrain nu inchangé en logique** (voir l'alerte ci-dessous).

**⚠ Terrain nu — à ne surtout pas lire comme une régression.** La logique terrain est **identique** entre
les deux bancs (médiane de secteur cadastral, `_terrain_section`). Le chiffre « 633 % → 713 % » ne vient
PAS du terrain mais du **défaut de nature déjà documenté au banc 1 (§5-①)** : **67 % des ventes de terrain
2025 portent sur une parcelle que l'outil croit bâtie** (emprise ≥ 5 %) → elles passent au comparateur
**bâti** et reçoivent un €/m² de bâti pour un terrain. Comme le comparateur bâti a changé (banc 2 =
`comparateur_bien`), ces cas faux reçoivent une **valeur fausse différente**. Sur le périmètre où l'outil
estime le terrain **correctement** (parcelle vraiment nue, N = 346), l'écart est **18,8 %, identique aux
deux bancs**. Le défaut de nature reste ouvert — hors périmètre de ce mandat.

### Précisions affichées mises à jour (`_ECART_SEGMENT`, `src/labuse/pige/api.py`)

Le badge et la mention « ±XX % » servis à l'écran et au PDF lisent `precision_pct`, piloté par
`_ECART_SEGMENT` (médian |écart| par segment, convention du banc 1). Valeurs recalibrées sur le banc 2,
**seuils de badge inchangés** (< 15 % → Élevée, < 25 % → Moyenne, au-delà → Limitée) :

| type servi | banc 1 (ancien) | **banc 2 (nouveau)** | badge au seuil |
|---|---:|---:|---|
| appartement | 17 % | **17 %** (inchangé) | Moyenne |
| **maison** | **32 %** | **28 %** | Limitée |
| terrain nu | 19 % | **19 %** (inchangé, logique terrain inchangée) | Moyenne |
| bâti combiné | 28 % | **26 %** | Limitée |

Seul changement d'affichage : **« ±32 % » → « ±28 % »** sur la maison et **« ±28 % » → « ±26 % »** sur le
bâti combiné. Aucun libellé de badge ne change (la maison reste « Limitée », au-dessus de 25 %).

**Fidélité du réplica banc 2 (preuve que banc = prod − coupe de date).** En rejouant le réplica
`comparateur_bien` **sans coupe** (fenêtre pleine, ancre = max global DVF) contre la fonction de
production appelée en direct, sur 80 parcelles bâties jugées : **77/80 même type de bien déduit**,
écart médian de médiane **0,55 %**, **69/80 à ±4 %** (`FIDELITE_V2.txt`). Le réplica = la production, à la
seule coupe de date près (ce qui supprime la fuite) ; le résiduel vient de l'ancre de fenêtre (prod =
max global DVF, réplica = max local commune) et des cas-limites du seuil de dominance de type (55 %).

---

## Tableau 2 — Lot B : rayon de rattachement propre à la source (recette Bien'ici, fixture RADAR-SOURCES-2)

`qa/radar-bienici/ECH-BIENICI-1.json` — 100 annonces Bien'ici réelles, **66 rattachables** (maison / terrain /
immeuble), dont **59 à position « à l'adresse »** (floutée ~50 m). Lecture seule sur les 434 582 parcelles.
**AVANT** = rayon 150 m partout (l'ancien comportement) ; **APRÈS** = **60 m** pour les positions à l'adresse,
**150 m** pour les positions de quartier (Leboncoin, inchangé).

| | **AVANT** (150 m partout) | **APRÈS** (60 m à l'adresse) |
|---|---:|---:|
| rattachée (auto) | 1 | **11** |
| piste (à instruire) | 48 | 43 |
| non rattachée | 17 | 12 |
| **ambigus** (≥ 2 candidates) | 47 | **41** |
| **auto-rattachés** | **1** | **11** |

> Le rayon serré fait **fondre l'univers** de candidates autour du point flouté : les cas « une seule
> parcelle candidate » deviennent atteignables → **l'auto-rattachement passe de 1 à 11** (tous par
> convergence **emprise + surface**, confiance 0,75), et les ambigus reculent (47 → 41). **Leboncoin ne
> bouge pas** : `RAYON_M` reste 150 m, verrouillé par `test_rattachement_rayon_source.py`.

**Règle d'auto-rattachement (inchangée, désormais réellement utile).** Rattachement automatique **seulement
s'il reste une seule parcelle candidate** : une parcelle à ≥ 2 critères convergents uniques (niveau
`source`) ou, pour un terrain, une parcelle unique à ±1 % de surface (niveau `estime`). Sinon → **piste à
instruire**. Le resserrement du rayon ne touche pas cette garde ; il lui donne de la matière.

### Vérification ortho des 11 auto-rattachements (10 parcelles distinctes — CM0143 listée 2×)

Chaque parcelle rattachée a été superposée à l'**orthophoto IGN** avec son contour, le point flouté de
l'annonce et le disque de floutage 50 m (`ortho/NN_<idu>.png`). **10 / 10 plausibles, 0 faux** :

| # | commune | hab / terr annoncés | parcelle surf. / emprise | point→centroïde | verdict ortho |
|---|---|---|---|---:|---|
| 01 | Saint-André | 125 / 596 | 597 / 147 | 31 m | ✔ maison sur la parcelle |
| 02 | Saint-Denis | 165 / 476 | 454 / 79 | 34 m | ✔ maison sur la parcelle |
| 03 | Saint-Denis | 155 / 458 | 448 / 225 | 76 m | ✔ maison sur la parcelle |
| 04 | Saint-Louis | 77 / 587 | 583 / 136 | 39 m | ✔ maison sur la parcelle |
| 05 | Saint-Paul | 220 / 1 480 | 1 445 / 327 | 25 m | ✔ grande maison/terrain |
| 06 | Saint-Paul | 125 / 425 | 413 / 187 | 57 m | ✔ maison sur la parcelle |
| 07 | Saint-Pierre | 130 / 1 019 | 998 / 194 | 79 m | ✔ maison sur la parcelle |
| 08 | Saint-Pierre | 100 / 180 | 178 / 120 | 63 m | ✔ maison (+ piscine) |
| 09 | Saint-Pierre | 125 / 275 | 275 / 187 | 9 m | ✔ maison sur la parcelle |
| 10 | Saint-Pierre | 155 / 1 480 | 1 474 / 254 | 41 m | ✔ maison sur la parcelle |

Dans les 10 cas, la **surface cadastrale colle au terrain annoncé (≤ 5 %)**, la parcelle **porte un bâti**
(emprise BD TOPO) et le **point flouté tombe sur ou immédiatement à côté** de la parcelle (9–79 m, dans le
rayon de floutage + recherche). **Aucun rattachement faux** → la règle n'a pas eu besoin d'être durcie.

---

## Ce qui a changé dans le code servi

- `src/labuse/pige/rattachement_html.py` — **rayon par source** : `RAYON_M_ADRESSE = 60` (positions à
  l'adresse), `RAYON_M = 150` inchangé (quartier / Leboncoin) ; helper `_rayon(rec)` branché sur
  `source_position` (jamais sur le nom du portail, doctrine §2) ; threadé dans `_crit_surface` /
  `_crit_emprise` et la règle terrain stricte. Règle « une seule candidate » inchangée.
- `src/labuse/pige/api.py` — `_ECART_SEGMENT` recalibré (maison 32→28, bâti 28→26 ; appartement 17 et
  terrain 19 inchangés). Le badge et le « ±XX % » servis en découlent (seuils < 15 / < 25 inchangés).
- `tests/test_rattachement_rayon_source.py` — **verrou Leboncoin** (RAYON_M = 150) + comportement 60 m vs
  150 m + auto-rattachement « une seule candidate ».

## Reproduire

```bash
# Lot A — banc 1 vs banc 2 (≈ 3 min)
~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/banc-rayon-1/backtest_banc2.py
# Lot A — fidélité du réplica (appelle la vraie comparateur_bien)
PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/banc-rayon-1/fidelite_v2.py
# Lot B — recette rayon (avant/après) + auto-rattachés
PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/banc-rayon-1/recette_rayon_bienici.py
# Lot B — images ortho
PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/banc-rayon-1/ortho_check.py
# tests (base de test openclaw)
LABUSE_TEST_DATABASE_URL=postgresql+psycopg:///labuse_test PYTHONPATH=src \
  ~/Desktop/labuse/.venv/bin/python -m pytest tests/test_rattachement_rayon_source.py -q
```

**Livrables** (`docs/audit-2026-10/banc-rayon-1/`) : `backtest_banc2.py` · `fidelite_v2.py` ·
`recette_rayon_bienici.py` · `ortho_check.py` · `PAR-VENTE.csv` (5 592 lignes, banc 1 & banc 2) ·
`METRIQUES.json` · `RESULTATS.txt` · `FIDELITE_V2.txt` · `AUTO_RATTACHES.json` · `ortho_index.json`
(mesures des 10 vérifs) · ce `RAPPORT.md`.

> Les 10 images `ortho/NN_<idu>.png` sont **gitignorées** (politique anti-bloat MENAGE-1
> `docs/audit-*/**/*.png`) : elles restent sur disque et se **régénèrent** via `ortho_check.py`. Les
> verdicts et mesures de la vérification à l'œil sont gravés dans `ortho_index.json` et la table ci-dessus.
