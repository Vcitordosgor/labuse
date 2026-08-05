# M34 — Phase 0 : CONSTAT (dette #14, double-rail verdict/tier)

**Branche `m34-dette14-verdict-fiche` · base `main` post-M32 (f39d010) · LECTURE SEULE — aucun code
modifié, aucune écriture DB.** Run servi `q_v8_calibre` intouché.

> ⚠ **DÉCLENCHEMENT DE LA CLAUSE STOP DU MANDAT (Phase 0.4).** Le constat révèle autre chose que la
> logique attendue : `score_e` n'est PAS le moteur du verdict divergent, il y a DEUX rails parallèles
> avec chacun son writer, et le périmètre réel dépasse largement le bâti marginal (263 cas sur 3 251
> déclassements silencieux, + 2 263 divergences MONTANTES). Remonté à Vic avant tout code.

---

## 1 · Localisation du moteur verdict — ce n'est pas `score_e`

**`score_e` (`src/labuse/ingestion/score_e.py`) n'émet aucun verdict.** C'est la table additive
« Marge estimée en € » (chip fiche `libelle_court` : « Marge estimée : +N k€ · Estimé »). Elle ne
produit jamais « À creuser ». (Dette distincte déjà consignée train 3 : son défaut `run="q_v7_defisc"`
en dur, `score_e.py:158`.)

Le verdict qui contredit le tier vit sur **deux rails parallèles**, chacun avec son writer :

| Rail | Table / colonne | Writer | Logique |
|---|---|---|---|
| **Legacy live** | `parcel_evaluations.status` (dernière éval. par parcelle, `_latest_eval` app.py:651) | `cascade/pipeline.py:118` → `scoring/declassement.py::apply_declassement` → `bati.py::classify` | Cascade pré-M28 : statut `opportunite / a_creuser / faux_positif_probable / exclue` ; déclassement non-franc par seuils R1 (bâti 15–30 % → a_creuser ; surface < 250 m² ; pente > 40 % ; accès > 6 m ; OSM ≥ 30 %) |
| **Matrice run servi** | `dryrun_parcel_evaluations.matrice_statut` (+ `status`) | `scoring/dryrun.py::compute_matrice` (post-pass Q×A) | Seuils Q/A (`scoring_matrice.yaml`) sur les poids de la cascade dryrun — même ère pré-M28 |

Le **tier servi** (`parcel_p_score_v2.tier`, run `q_v8_calibre`) est le troisième rail — le seul
légitime post-M28/M32 (filtre 3 étages `faisabilite/filtre_bati.py`).

## 2 · Qui sert quoi (surfaces contaminées vs déjà alignées)

**Déjà aligné (correctif M5)** : la fiche web (`getFiche` → `/parcels/{idu}?source=q_v8_calibre` →
`_q_v2_fiche`) — la bannière suit `verdictMeta(statut, tier_v2, etage0)` (`frontend/src/lib/status.ts`),
le tier pilote. La matrice n'y apparaît que comme chip « Statut matrice (historique) » étiquetée
(`Fiche.tsx:1457`), dans le tiroir Confiance.

**Contaminées (rail legacy `ev.status` + `resume.synthese`)** — toutes passent par `_build_fiche`
(app.py:2539, `verdict_block.status = ev.status`, synthèse `api/resume.py::_synthese`) :

- `GET /parcels/{idu}` **sans** `?source=` (app.py:2136) — repli legacy servi tel quel ;
- `GET /parcels/{idu}/export` md / html / **one-pager comité D1** (app.py:2819) — le document
  montrable en comité porte le verdict legacy ;
- comparateur de parcelles (app.py:3033, `_compare_row` : `status` + `synthese`) ;
- assistant IA (`api/assistant.py:113` — les « facts » donnés au modèle citent le verdict legacy) ;
- shortlist (app.py:2355, `_build_fiche(..., with_assistant=False)`).

## 3 · Mesure à blanc (SQL, lecture seule) — l'ampleur réelle

Univers : parcelles du run servi `q_v8_calibre`, tiers actifs (`brulante`, `chaude`,
`reserve_fonciere`, `a_creuser`), croisées avec le dernier `parcel_evaluations.status`.

### 3.1 Rail legacy × tier servi

| Tier servi | opportunite | a_creuser | faux_positif_probable |
|---|---|---|---|
| brûlante (119) | 22 | **97** | 0 |
| chaude (1 041) | 149 | **892** | 0 |
| réserve foncière (2 964) | 702 | **2 260** | **2** |
| à creuser (29 974) | **2 263** ↑ | 27 693 | **18** |

- **3 251 déclassements silencieux** (tier haut servi → verdict legacy déclassé), dont **97 des 119
  brûlantes** — l'ancre golden **AT2542 comprise** (a_creuser, motif accès ~12 m).
- **2 263 divergences MONTANTES** : servies `a_creuser` affichées « Opportunité vérifiée » —
  violation directe de « le doute ne profite jamais au classement », pire face client que le symptôme.
- 20 « faux positif probable » sur des parcelles servies.
- **Total divergences rail legacy : 5 534.**

### 3.2 Ventilation des 3 251 déclassements silencieux par famille de motif

| Famille (couche `declassement`) | n |
|---|---|
| **aucun motif — score legacy seul sous seuil** | **2 195** |
| accès non identifié | 497 |
| **bâti marginal 15–30 % (le cas du mandat)** | **263** |
| surface réduite (< 250 m²) | 135 |
| pente > 40 % | 110 |
| surface + accès | 41 |
| autre | 10 |

Le cas nominal du mandat (bâti marginal) = **8 %** de la divergence. Les 2/3 divergent sans aucun
motif de déclassement : c'est l'ancien seuil d'opportunité qui parle, pas une nuance terrain.

### 3.3 Rail matrice (run servi) × tier — encore plus divergent

101/119 brûlantes ont `matrice_statut='ecartee'` (706/1 041 chaudes). Ce rail est déjà étiqueté
« historique » à l'écran, mais il reste servi dans le payload (`statut`) et lu par `score_v.py:595`.

### 3.4 Ancre CY0197 (97422000CY0197, Saint-Pierre) — au rendez-vous

tier servi **brûlante rang 163** · legacy `a_creuser` (rules 9ac600517abc, éval. 04/07) · matrice
`ecartee` · motif présent sur les deux rails, au mot près le symptôme de la dette :
« bâti significatif : 22 % de la surface intersecte des bâtiments (BD TOPO) — occupation à vérifier ».

### 3.5 Échantillon 20 IDU (tiers hauts, rail legacy divergent, tri rang)

| IDU | tier | rang | verdict legacy | motif |
|---|---|---|---|---|
| 97411000KA0296 | brûlante | 5 | a_creuser | — (score seul) |
| 97410000CD0905 | brûlante | 6 | a_creuser | — |
| 97418000AT2379 | brûlante | 7 | a_creuser | — |
| 97408000AP1603 | brûlante | 13 | a_creuser | accès ~9 m |
| **97418000AT2542** (ancre golden) | brûlante | 14 | a_creuser | accès ~12 m |
| 97416000ET2164 | brûlante | 24 | a_creuser | surface 245 m² |
| 97416000ET2243 | brûlante | 26 | a_creuser | — |
| 97416000ET2167 | brûlante | 27 | a_creuser | — |
| 97416000ET2166 | brûlante | 28 | a_creuser | — |
| 97412000CP0462 | brûlante | 29 | a_creuser | — |
| 97422000BX1123 | brûlante | 30 | a_creuser | surface 123 m² + accès |
| 97411000CE1132 | brûlante | 31 | a_creuser | — |
| 97411000CE1133 | brûlante | 32 | a_creuser | — |
| 97415000AX1100 | brûlante | 33 | a_creuser | surface 209 m² |
| 97413000AV2297 | brûlante | 34 | a_creuser | surface 164 m² |
| 97412000CE2776 | brûlante | 37 | a_creuser | — |
| 97411000EL0665 | brûlante | 38 | a_creuser | — |
| 97416000ET2242 | brûlante | 39 | a_creuser | — |
| 97415000AY1587 | brûlante | 40 | a_creuser | surface 106 m² |
| **97422000CY0197** (ancre mandat) | brûlante | 163 | a_creuser | bâti significatif 22 % — occupation à vérifier |

## 4 · Pourquoi STOP (Phase 0.4) — les trois écarts au mandat

1. **`score_e` n'est pas le coupable** : le moteur divergent = cascade legacy
   (`parcel_evaluations.status`) + matrice Q×A — deux writers, pas un.
2. **Le périmètre réel n'est pas « les bâtis marginaux/divisibles »** : bâti marginal = 263 cas ;
   la divergence est structurelle (2 195 sans motif) et **bidirectionnelle** (2 263 montantes,
   jamais mentionnées par la dette).
3. **La correction « aligner sur le filtre 3 étages » ne suffit pas** : aligner le seul cas bâti
   laisserait 92 % de la divergence en place, y compris sur le one-pager comité et l'assistant IA.

## 5 · Options pour l'arbitrage (aucune implémentée)

- **(a) Dérivation totale** — le verdict de fiche legacy devient une TRADUCTION du tier servi
  (+ badge « bâtie + division possible » pour les divisibles étage 3, + motifs du registre) ;
  `_build_fiche`/`resume.py` lisent `parcel_p_score_v2` via le point de vérité unique. Les surfaces
  legacy (export, compare, assistant, `/parcels/{idu}` nu) racontent alors le même run que la fiche
  web. Rail matrice : inchangé (déjà étiqueté historique) ou retiré du payload. **Recommandée** —
  c'est l'esprit du mandat (« un seul point de calcul »), appliqué au vrai moteur.
- **(b) Périmètre strict du mandat** — n'aligner que les 263 bâtis marginaux : minimal, mais laisse
  2 988 déclassements silencieux + 2 263 divergences montantes sur les surfaces client.
- **(c) Extinction du rail legacy** — `_build_fiche` bascule sur `_q_v2_fiche` partout : plus
  invasif (payloads différents, PDF/exports/compare à adapter), à chiffrer avant d'ouvrir.

**Vérifs communes à toute option** (déjà cadrées par le mandat) : golden 117/117 inchangé, 0 écriture
sur le run servi, re-mesure = 0 divergence, screenshots des 6 fiches de contrôle.
