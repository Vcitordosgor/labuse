# OUTILS-P0-2 — la cohérence du marché

Branche `fix/outils-p0-2` (depuis `origin/main` à jour). Source : revue d'Astra du livret des outils.
Ports de recette 10800 (vite) / 7280 (uvicorn). Aucun merge, aucune prod.

> **RECETTE (2e passe)** — 8 points mesurés + testés, captures `recette-*.png`. Voir § RECETTE en bas.

**Étape 0** — `88bfb6e11` (Estimer 3) est bien ancêtre d'`origin/main` ✓ (vérifié `git merge-base --is-ancestor`).

---

## P1 — Estimer : le PDF reprend EXACTEMENT le scénario affiché

Avant, l'export PDF ne transmettait que la surface ; les pièces saisies et les ventes décochées étaient
perdues → le document divergeait de l'écran.

- Endpoint `GET /analyse-annonce/{idu}.pdf` : ajout de `pieces` et `ecartees` (liste) en query params
  (`src/labuse/api/documents.py`).
- Threading `pieces` + `ecartees` : `construire_analyse_annonce_parc` → `rapport_parcelle` →
  `_est_bloc_depuis_estimer3` → `estimer3.rapport3` (déjà paramétré). Même méthode, même montant, mêmes
  fourchettes, mêmes ventes retenues qu'à l'écran — aucun recalcul divergent.
- Front : `docAnalyseAnnonceUrl(idu, surfaceHab, {pieces, ecartees})` + le bouton PDF d'Estimer transmet
  `{ pieces, ecartees: ecartList }` (le scénario affiché).

**Test de parité** (`test_pdf_parite_pieces_et_ventes_ecartees`, reel) : surface 60 + 3 pièces + 1 vente
décochée → le montant imprimé (`valeur_indicative.valeur_eur`) ÉGALE celui de l'écran
(`rapport3(...).estimation.valeur_eur`) ; le PDF ne retient que les ventes actives (comme l'écran).

---

## P2 — Estimer : les terrains nus hors gamme

Un terrain nu était estimé par `prix médian du secteur × TOUTE sa surface`, sans vérifier qu'il ressemble
aux ventes de référence (témoin `97409000AK0804` : parcelle 27 862 m² × 278 €/m² ≫ gamme).

### Le test de comparabilité, mesuré au banc

`docs/audit-2026-11/outils-p0-2/mesure_terrain_gamme.py` (no-leak, 951 terrains) mesure l'écart
|estimé−réel| en fonction de la position de la surface du sujet vis-à-vis des ventes de référence :

| surface sujet / p90(surfaces de référence) | écart médian | n |
|---|---|---|
| ≤ 0,5 | 31 % | 648 |
| 0,5–1,0 | 30 % | 208 |
| **1,0–1,5** | **87 %** | 46 |
| 1,5–2,0 | 70 % | 20 |
| > 10 | 156 % | 3 |

**Falaise nette à ratio = 1,0** : dès que la surface du sujet dépasse le **p90 des surfaces des ventes de
référence**, l'écart médian passe de ~30 % à ~86 %. Seuil retenu : **hors gamme = surface du sujet > p90
des surfaces des ventes de référence** (borne haute robuste de la gamme, 9e décile). Au-delà : 9,8 % des
terrains, écart médian 85,5 % contre 30,7 % dans la gamme.

### Le comportement servi

- `comparateur_terrain` renvoie `surface_gamme` (min / médiane / **p90** / max / n des ventes retenues).
- **Hors gamme** (`surface_parc > p90`) : PAS de total (`valeur_indicative = None`) ; le repère au m² et les
  ventes de référence RESTENT affichés, avec « **Terrain hors gamme des ventes de référence** (parcelle
  X m², ventes de référence jusqu'à ~Y m²) — surface trop grande pour un total fiable ».
- **Non constructible** (verdict `potentiel_batir`) : PAS de valeur de terrain à bâtir ; la raison (le motif)
  est dite — « Zone non constructible (A) — pas de valeur de terrain à bâtir ».
- Écran (`AnalyserAnnonce` → `ValeurEstimee`, branche `[data-estimer-terrain-sans-total]`) ET PDF
  (`blocs/annonce.py`, note terrain) servent la même raison — écran == PDF.

### Témoins mesurés (base locale)

| parcelle | avant | après |
|---|---|---|
| `97409000AK0804` (hors gamme) | total ≈ surface × 278 €/m² | **pas de total** ; 278 €/m² + 8 ventes + raison (27 862 m² vs p90 706 m²) |
| `97422000BN2939` (ordinaire, 680 m²) | total | **total 145 000 €** (dans la gamme, p90 1 065 m²) |
| `97409000AK1204` (zone A) | total | **pas de valeur à bâtir** ; 276 €/m² + raison « Zone non constructible (A) » |

---

## P3 — Étude de zone : le prix du cercle dessiné

Le prix en tête était ÉCRASÉ par celui du secteur de la fiche (`marche_dvf`, un autre périmètre).

- `app.py` endpoint `/outils/etude-zone` : SUPPRESSION de l'écrasement. Le « Prix médian du bâti » reste
  celui du **cercle** (`marche.prix_m2_median_bati`, calculé dans le périmètre). Le prix du secteur de la
  fiche est servi À PART : `prix_secteur_fiche` (médiane + rayon réel + effectif).
- `zone.marche_zone` porte désormais l'effectif et la période de la médiane DU CERCLE
  (`prix_m2_median_n`, `prix_m2_median_periode`, fenêtre 36 mois via `mediane_bati`).
- `annonces_actives` : `None` quand la source Radar n'est pas ingérée → l'écran affiche « — », jamais 0.
- Front (`EtudeZone`) : en-tête « **Dans un rayon de X km à vol d'oiseau** » puis « **Prix médian du bâti
  dans le cercle · N ventes · période** » ; secteur de la fiche affiché à part ; « annonces actives » →
  « **annonces suivies par LABUSE** ».
- PDF (`blocs/etude_zone.py`) : même périmètre, même prix, même effectif que l'écran ; plus d'injection
  `prix_ancien` (secteur) à la place du cercle.

**Test** (`test_prix_median_decrit_le_cercle_et_change_avec_le_rayon`, reel, `97411000BZ1065`) : le prix et
l'effectif de tête ÉGALENT une requête DVF directe (`mediane_bati`) sur CHAQUE cercle, et changer de rayon
change le prix. Mesuré :

| rayon | prix du cercle | n | période | secteur de la fiche (à part) |
|---|---|---|---|---|
| 0,5 km | 3 144 €/m² | 24 | 10/2023–04/2026 | 3 821 €/m² · 30 ventes · 500 m |
| 2 km | 3 011 €/m² | 410 | 06/2023–06/2026 | 3 821 €/m² · 30 ventes · 500 m |

Le prix du cercle change avec le rayon ; le secteur de la fiche (3 821) ne se confond plus avec lui.

---

## P4 — Phrase sous les fourchettes d'Estimer

Sous les deux fourchettes (`ValeurEstimee`) : « **Fourchettes mesurées sur des ventes passées de biens
comparables.** »

---

## Captures WebKit (webkit-2104, playwright 1.49.1)

`docs/audit-2026-11/outils-p0-2/capture_webkit.mjs` (le playwright 1.62 du front ne supporte pas WebKit
sur macOS 13 arm64 → playwright 1.49.1 épinglé dans /tmp/pwwk, navigateur webkit-2104 déjà installé) :

- `p1-p4-estimer-appartement.png` — surface 62 + 3 pièces + 1 vente décochée, valeur 139 000 € + fourchettes + phrase P4.
- `p2-terrain-hors-gamme.png` — AK0804 : 278 €/m², pas de total, raison + ventes de référence.
- `p2-terrain-non-constructible.png` — AK1204 : 276 €/m², pas de valeur à bâtir, raison.
- `p3-etude-zone-cercle.png` — BZ1065 à 2 km : 3 011 €/m² (cercle) + secteur 3 821 à part + « annonces suivies par LABUSE ».

## Hook

- `tsc -b` 0 · `vitest` 326 · `vite build` OK.
- `pytest` estimer3 21 (18 + 3 nouveaux), zone 28, tous verts. Les 22 autres échecs du run CI complet sont
  PRÉ-EXISTANTS (profil pass/échec identique à `origin/main`, base locale partielle) — mes seules régressions
  étaient 2 assertions de clés `marche` (zone), corrigées.

---

## RECETTE (2e passe) — la cohérence des ventes et des libellés

Revue d'Astra du livret. 8 points, chacun mesuré au texte DOM (WebKit) et/ou testé.

1. **Ventes de terrains.** Date « MM/YYYY » (bug corrigé : `_vente_retenue` re-formatait « 05/2022 » en
   « 22/05/2 » — `_mois_annee` détecte le format déjà posé). Surface = celle du **terrain** (« 472 m² de
   terrain »), jamais « hab. » ni « terrain non renseigné ». Distance = la vraie (ST_Distance), **« — »**
   si inconnue/0, jamais « 0 m » par défaut. (`VentesRetenues` type-aware.)
2. **Ventes d'appartements.** Aucune mention de terrain (« 86 m² habitable · 56 m »).
3. **Fourchettes d'un terrain.** « 1 fois sur 2 » / « 3 fois sur 4 » = deux bandes distinctes mesurées au
   banc. Si le banc n'en donne qu'une (repli régional, écart médian == Q3), **une seule ligne** « Fourchette
   estimée » (helper `_fourchettes`). Témoins : terrain Tampon → une bande ; appartement BH0309 → deux.
4. **Terrain non constructible.** AUCUNE estimation : pas de prix au m² en tête, aucune vente de terrain à
   bâtir listée. L'écran dit **« Pas d'estimation : zone non constructible (A) »** (code zone via
   `_zone_code`) + la dernière vente de la parcelle. (Change le P2 initial qui gardait le repère.)
5. **Appartement en immeuble à plusieurs logements** (RNIC `nb_lots_habitation > 1`, `_multi_logement`) :
   champ surface **vide**, indication **« Dernière vente dans l'immeuble : 24 m² (2025) »**, badge « connue »
   réservé au mono-logement (la dernière vente DVF n'est qu'un lot). Read déclaré au registre des lectures.
6. **Dernière mutation à prix symbolique (< 100 €)** : **« Dernière mutation : 12/2025 · cession à 1 €, hors
   marché »** (pas « vente », pas de surface). Témoin 97413000DD1534.
7. **Étude de zone.** « **0,5 km** » avec virgule. La ligne du secteur dit ce qu'elle mesure : **« Secteur de
   la fiche, maisons, 2022–2026 : 3 821 €/m² · 30 ventes à moins de 500 m »** (type + fenêtre réelle en
   années — PAS un « 24 mois » inventé : le prix de secteur agrège un segment de 5 ans). La période du cercle
   est la **fenêtre demandée (36 mois)**, pas les dates extrêmes des ventes. Section **Immobilier dépliée** à
   l'ouverture.
8. **Noms de communes** : **« au Tampon », « au Port », « aux Avirons »**, jamais « à Le Tampon » (helper
   `aCommune`, test vitest). Vérifié live : « mesuré sur les ventes réelles de terrains au Tampon ».

**Captures WebKit** (`recette-*.png`, webkit-2104 / playwright 1.49.1, `capture_recette.mjs`) : terrain
Tampon (1/3/8), appartement (2 + deux bandes + P4), non-constructible (4), multi-logement (5), symbolique
(6), maison au Port (8), zone 0,5 km (7).

**Hook** : tsc0 · vitest **327** · pytest estimer3 (purs 10 dont `_mois_annee`/`_fourchettes`/`_zone_code`,
+ reel hors-gamme/non-constructible/parité/zone) + lectures graph (read RNIC déclaré) verts. Les ~22 autres
échecs du run CI complet restent PRÉ-EXISTANTS (profil identique à `origin/main`).
