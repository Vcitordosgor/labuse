# FRR-MOUFIA-1 — HR0025 (Moufia) est-elle vraiment « dans les Hauts » (FRR) ?

**Branche** `fix/frr-moufia-1` (depuis `origin/main` `c664f467`, worktree `~/Desktop/labuse-frr`, ports 8830/6030). Pas de merge.

## Verdict (une ligne)

**FAUX à la parcelle** : HR0025 (Moufia, campus, ~150 m, en ville) était marquée « DANS la ZSAR les Hauts »
alors que LABUSE teste l'intersection avec un **polygone de COMMUNE** (pas le contour infra-communal). Le
**classement de commune** « partie », lui, est **JUSTE** (conforme à la liste Région ZRR 2017). Corrigé : la
position parcellaire passe à **« non déterminée »** (le périmètre « les Hauts » n'existe pas dans la donnée).

---

## 1. Source exacte du contour FRR/ZSAR utilisé par LABUSE

| Élément | Valeur |
|---|---|
| **Géométrie du « polygone FRR »** | `frontend/public/communes974.geojson` — **limites communales IGN** (`build_zfang_frr` dans `src/labuse/ingestion/dispositifs.py` : un polygone = **toute la commune**, `attrs.maille = "commune"`). **Il n'y a AUCUN tracé « les Hauts ».** |
| **Classement (totalité / partie / hors)** | SEED versionné `data/fiscal/territoire_fiscal.csv`, colonne `frr_classement`. Saint-Denis (97411) = **`partie`**. |
| **Millésime / référence (`attrs`, `data_sources`)** | `FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)` · provider *Légifrance / Région Réunion* · **« ZSAR 1978 · FRR 01/07/2024 · réf. ZRR 2017 (Région) »**. |
| **Lien** | <https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049746820> (arrêté FRR 19/06/2024). |
| **Texte réglementaire fondateur** | **CGI art. 44 quindecies A** (FRR, en vigueur 01/07/2024) : *« Sont classées en zone France ruralités revitalisation les communes de La Réunion comprises dans la **zone spéciale d'action rurale délimitée par décret**. »* — ZSAR = **décret n° 78-690 du 23 juin 1978** (« les Hauts »), délimitation **INFRA-COMMUNALE**. |

**Mesuré en base :** la couche `spatial_layers kind='frr'` = **23 polygones, tous `attrs.maille='commune'`**. Celui de
Saint-Denis fait **141,8 km²** = **99,8 %** des 134,5 km² de la commune → c'est la **commune entière**, pas les Hauts.
Note du module lui-même : *« on sert l'état honnête (« en partie » ≠ « classée »), **jamais une conclusion
parcellaire** »* — ce que `frr_position` violait.

## 2. Capture — HR0025 superposée au polygone

`captures/hr0025-polygone-frr-overlay.png` (dézoomée sur toute la commune) : le polygone « frr » (rouge) **épouse
la limite communale** (tireté) ; HR0025 (point bleu) est au **nord, sur le littoral** (Moufia, campus) — il y tombe
**comme n'importe quelle parcelle de Saint-Denis**. Les Hauts (La Montagne / Le Brûlé / La Roche Écrite, > 1 000 m)
sont au sud **sans aucun contour dans la donnée**.

## 3. Comparaison à la liste officielle

**Région Réunion — Open Data, « Communes classées en ZRR 2017 »** (= la référence de LABUSE) :

| État | Communes |
|---|---|
| **Classée** (totalité) | La Plaine-des-Palmistes, Salazie, Cilaos |
| **Non classée** (hors) | Le Port |
| **Partiellement classée** (partie) | **les 20 autres, dont Saint-Denis (97411)** |

→ La classification LABUSE (`territoire_fiscal.csv`) est **identique** à la liste Région. **Saint-Denis EST bien
« partiellement classée »** — et cette source confirme que, pour les communes partiellement classées, *« la
classification est **infra-communale** »* (les Hauts). Donc :
- La **commune** est **bien classée** (FRR en partie) — ✅ juste.
- Le **périmètre** est **les Hauts (infra-communal)** ; LABUSE n'en a **pas le tracé**, donc il ne peut PAS
  conclure « cette parcelle est dans les Hauts ». Moufia (littoral) en est, de fait, **hors**.

*Aucun contour GIS de la ZSAR « les Hauts » n'est diffusé en open data (le décret 78-690 la délimite par texte) ;
on ne fabrique donc pas un faux contour — on corrige le test.*

## 4. Le bug & la correction

**Bug** (`territoire_fiscal.frr_position`, origin/main) : `ST_Intersects(parcelle, polygone frr)` contre le
polygone de **commune** → « dans » pour **toute** parcelle d'une commune « partie » (Moufia inclus).

**Correctif** : on ne tranche `'dans'`/`'hors'` **que** si un vrai contour infra-communal est servi
(`attrs.maille <> 'commune'`) ; sinon `None` → **« position de la parcelle non déterminée »**. Les 23 polygones
étant `maille='commune'`, toutes les communes « partie » passent en non déterminé (fin du faux « dans »). Si un
tracé ZSAR réel est ingéré un jour, le test reprend automatiquement. **Rien d'autre n'est touché** (le classement
de commune, la pastille commune, ZFANG, QPV, etc. restent).

## 5. Avant / après (section Fiscalité)

| Parcelle | Avant | Après |
|---|---|---|
| **HR0025** (Moufia, Saint-Denis, *partie*) | `position = "dans"` → *« Parcelle **DANS** la zone spéciale d'action rurale (les Hauts) — commune classée FRR en partie »* | `position = "non_determine"` → *« Commune classée FRR en partie seulement (les Hauts, délimitation infra-communale) — **position de la parcelle non déterminée** (périmètre non disponible) »* |
| **Cilaos** `97424000AE2288` (*totalité*, **réellement les Hauts**) | *« Commune classée **en totalité** (zone spéciale d'action rurale — décret n° 78-690 ; FRR depuis le 1er juillet 2024) »* | **inchangé** (le fix ne concerne que les communes « partie ») |

Captures : `captures/hr0025-fiscalite-avant.png`, `captures/hr0025-fiscalite-apres.png`,
`captures/cilaos-fiscalite-leshauts.png`. Le haut de la section (pastille « FRR » sous *Dispositifs de la commune*,
verdict) est **identique avant/après** — c'est voulu : le fait **de commune** (Saint-Denis FRR en partie) est
exact ; seul le **détail à la parcelle** (dans le repli « détail des dispositifs ») est corrigé.

**Vérifié API (port 8830) :** HR0025 `partie / dans → partie / non_determine` ; Cilaos `totalite` inchangé.
Tests `test_recette11` + `test_commune_fix1` : **20 verts** (`frr_libelle_partie` et le seed inchangés).

Sources : [CGI art. 44 quindecies A](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000051217832) ·
[Arrêté FRR 19/06/2024](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049746820) ·
[Décret n° 78-690 (ZSAR les Hauts)](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000000338374) ·
[Région Réunion — ZRR 2017](https://data.regionreunion.com/explore/dataset/communes-classees-en-zones-de-revitalisation-rurale-zrr-2017/).
