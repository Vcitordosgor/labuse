# RADAR-4 — compte-rendu

**Branche** `fix/radar-4` · worktree `~/Desktop/labuse-radar4` · ports 9180/6380
**Périmètre** : `pige/` (back) + écrans **Radar** et **Veille** + écran **admin Radar** (le retrait du
rattachement touche explicitement écrans/PDF/aide/compte-rendus de passe). Aucun accès prod, aucune
modification de l'extension Chrome. Pas de merge.
**Registre lu d'abord** : `docs/audit-2026-11/nu-1/` lots E (`audit/nu-1-e`) et F (`audit/nu-1-f`).

Décision de Vic appliquée : **le rattachement automatique d'une annonce à une parcelle est retiré, pour
toutes les sources** (trop peu d'annonces rattachables). Le rattachement **manuel** (« C'est cette
parcelle ») reste.

---

## 1. Retrait du rattachement automatique (E-039, E-042)

**Décision** : tout retirer — pistes + cascade + rayons. L'admin reste inclus.

### Code mort supprimé
- `src/labuse/pige/rattachement_html.py` — **supprimé** (cascade V2 : rayons 60/150 m, critères
  surface/emprise/DVF/DPE/piscine, convergence ≥2, pistes, `niveau_preuve`, `criteres_pour_idu`).
- `src/labuse/pige/rattachement.py` — **supprimé** (cascade V1 du chemin capture-vision).
- `intake.py` : `deposer()` n'appelle plus aucune cascade → le bien entre **non rattaché** (`idu NULL`,
  niveau `absent`) ; `_proposer_rattachement()` et `_adresse_du_bien()` **supprimés** ; `valider()` ne
  propose plus de rattachement.
- `api.py` : endpoints du rattachement automatique **supprimés** — `POST /admin/radar/instruire`
  (relance de cascade + candidates enrichies), `GET /admin/radar/ortho/{idu}`, helper `_candidate_fiche`.
  `GET /admin/radar/a-instruire` (file des **pistes**) devient `GET /admin/radar/a-rattacher` : simple
  liste des biens validés, en vente, **non rattachés** (plus de pistes, confiance, ortho).
- `api.py` (`/admin/radar/reverif`) : plus de `rattachable_forte` / `piste_idu` (suggestion automatique).

### Réglages retirés
- Constantes **rayon 60 m / 150 m** (`RAYON_M`, `RAYON_M_ADRESSE`) et leur verrou de test
  (`test_rattachement_rayon_source.py` supprimé) : plus de réglage de rayon, puisque plus de cascade.

### Textes qui le promettaient, retirés / corrigés
- `client.py` : le niveau de preuve servi n'est plus `certain/probable/quartier` mais **`certain`**
  (rattaché = à la main) ou **`quartier`** (non rattaché). Plus d'import `niveau_preuve`.
- `html_ingest._rattacher` : docstring mise à jour (plus de « pistes pour l'écran d'instruction »).
- `registre/lectures.py` : 7 arêtes de lecture vers les modules supprimés retirées ; 1 arête périmée
  `adresses ← pige/api.py` retirée (le helper qui la lisait est parti) ; libellés `a-instruire` →
  `a-rattacher`. **Verrou G6 vert** (0 réservoir muet, 0 dette, 0 périmée) après correction.
- Front `admin/Radar.tsx` : le bouton « Rattacher » (1 clic, confiance auto) devient **« C'est cette
  parcelle »** (saisie manuelle de l'IDU) ; affiché sur toute annonce non rattachée.
- Front `lib/api.ts` : types `RadarPiste`, `RadarCandidateFiche`, `RadarAInstruire` et fonctions
  `getRadarAInstruire`, `radarInstruire` supprimés ; `RadarReverif` perd `rattachable_forte`/`piste_idu` ;
  `RadarBienDetail` perd `pistes` ; état de rattachement réduit à `rattachee | non_rattachee`.

**Ce qui reste** : `POST /admin/radar/rattacher-humain` (« C'est cette parcelle », admin seulement,
vérifie que l'IDU est une parcelle réelle de la commune) — inchangé. Un bien rattaché à la main n'est
jamais écrasé par une republication (`rattachement_humain = true`).

---

## 2. Dédoublonnage des biens « à qualifier » (E-040)

À l'ingestion (`html_ingest._ingester_annonce`), le **dédoublonnage exact** (même commune ∧ type ∧
surface EXACTE ∧ prix EXACT) s'exécute désormais **AVANT la garde à-qualifier** : deux annonces du même
bien physique ne font plus deux biens — y compris le même bien sur **deux portails** (Leboncoin ↔
Bien'ici) ou une annonce **à qualifier** (champs contradictoires). L'ancien garde
`if not degrade and not motifs` les laissait filer (constat E-040, biens #284/#332).

La variante **dégradée** (vignettes DOM, faits trop pauvres) reste **exclue** de la fusion exacte (garde
anti-faux-positif) — chacune reste son propre bien. La fusion **tolérante** (±2 %/±3 % + quartier) reste
réservée aux annonces **riches ET cohérentes**.

**Preuve** (`tests/test_radar4_dedup.py`, 3/3 verts) :
- Leboncoin + Bien'ici, même maison exacte → **1 bien, 2 annonces** (`r2 == "fusion"`) ;
- deux annonces à qualifier (terrain portant des pièces → motif) → **1 bien** (marqué à qualifier) ;
- deux dégradées identiques → **2 biens** (pas de faux positif).

> La base **dev locale** ne contient que des annonces Leboncoin (0 Bien'ici) — la preuve inter-portails
> est donc portée par la recette sur données façonnées, pas par la base locale.

---

## 3. Un seul fuseau — heure de La Réunion (F-014)

« En vente depuis N j » est calculé **une seule fois, côté serveur, en heure de La Réunion** :
- liste Radar (`client.py`) : nouvelle colonne servie `anciennete_j` (plus de `Date.now()` au front) ;
- bloc « Ce bien » (`marche.bien_vs_marche`) : déjà en Réunion, repli retiré (cf. §4).

Front `RadarEcran.tsx` : fonctions `joursDepuis` / `ancienneteJ` **supprimées** (et leur test
`RadarEcran.joursDepuis.test.ts`) ; la carte affiche `b.anciennete_j` tel quel. Plus d'off-by-one
(l'écart Paris↔Réunion ne peut plus décaler la durée d'un jour).

---

## 4. Durée de repli supprimée (plus de « 913 j »)

Le repli `COALESCE(date_publication, date_premiere_saisie)` est retiré partout où une **durée est
affichée** : liste Radar, bloc « Ce bien », médiane d'ancienneté de la commune. Un bien **sans vraie date
de publication** (NULL ou sentinelle < 2005) **n'affiche aucune durée** (`anciennete_j = NULL`) au lieu
de retomber sur la date de 1ʳᵉ saisie (qui gonflait en « 913 j »).

Mesure base dev : **77 / 416 biens** affichaient une durée de repli — désormais **0** (ils n'affichent
plus rien). La durée de repli maximale observée localement était **62 j** (le « 913 j » du mandat venait
du corpus prod semé en bloc ; le mécanisme fautif — le repli — est supprimé à la racine).

---

## 5. Compteurs de la Veille justes (F-015, F-016)

Les **comptes étaient déjà exacts** ; c'étaient les **libellés** qui mentaient sur la fenêtre.
- **F-015** — badge d'alerte `a.nouveaux` = annonces tombées **depuis hier** (début d'hier, Réunion).
  Le libellé « N annonces **depuis votre dernier passage** » (aucun suivi de visite n'existe) et l'état
  vide « **Rien cette semaine** » (7 jours) → corrigés en **« depuis hier »** / **« Rien depuis hier »**.
  Sous-titre de page « N événements **depuis votre dernier passage** » → **« N événements récents sur vos
  secteurs »** (le compte mêle parcelles suivies 7 j + alertes depuis hier : aucune fenêtre fausse promise).
- **F-016** — la phrase « fenêtres 30 j/90 j comptées **à partir de la dernière collecte** » n'existe
  **plus** dans l'UI actuelle (`RadarMarcheColonne.tsx` : libellé honnête « Ce qui a bougé · 30 jours »,
  compté jusqu'à aujourd'hui). Vérifié : 0 occurrence de « se comptent à partir » / « dernière collecte ».

Le badge **« Rien de nouveau »** d'une parcelle suivie reste piloté par la présence réelle d'un dernier
événement — fidèle à la réalité.

---

## 6. Garde légal

`tests/test_pige_socle.py` — **vert** (collecte 100 % humaine : aucun nom de portail sur une ligne
d'appel réseau, aucun crawler dans `pige/`). Les noms de portails cités dans la recette vivent dans
`tests/` (hors du périmètre scanné par le socle) et en commentaire/affichage.

---

## 7. Recette — avant / après (base dev locale `labuse`, lecture seule)

| Mesure | Avant | Après |
|---|---|---|
| Biens / annonces | 416 / 428 | 416 / 428 |
| Biens affichant une durée | 416 (dont 77 via repli) | 339 (vraie date pub seule) |
| Biens sans durée affichée | 0 | **77** (repli supprimé) |
| Durée de repli max affichée | 62 j | **0** |
| Doublons fusionnables (dry-run sur toute la base) | — | 1 groupe / 1 bien |
| Dédoublonnage inter-portails | bloqué par la garde | **actif** (preuve recette) |

> 1 seul doublon résiduel fusionnable localement (base 100 % Leboncoin, déjà largement dédoublonnée) ;
> le levier réel est le **dédoublonnage à l'ingestion** (prévient les futurs doublons, dont inter-portails).

**Captures** (stack local dev, auth désactivée en local, ports 9180/6380) :
- `capture-radar-liste.png` — liste Radar : durées servies par le serveur (« Pro · 9 j », « · 47 j »,
  « · 30 j ») ; marché « 71 biens, dont 3 depuis plus de 90 j ».
- `capture-veille.png` — Veille : badge d'alerte **« Rien depuis hier »** (ex-« Rien cette semaine »),
  badges parcelles « Rien de nouveau ».

## 8. Tests

- **Hook / pre-push** :
  - Front `tsc -b` : **RC 0**. `vitest run` : **301 passés / 63 fichiers**.
  - Python : suite pige ciblée **verte** après nettoyage de la pollution de `labuse_test`
    (voir note). Recette dédoublonnage `test_radar4_dedup.py` **3/3**. Verrou G6 **vert**.
- **Tests retirés / ajustés** (comportement supprimé) : `test_rattachement_rayon_source.py`,
  `test_radar_rattachement_s5.py`, `test_pige_rattachement.py` supprimés ; cascade/`niveau_preuve`
  retirés de `test_radar_auto1.py` et `test_veille2_lot2.py` ; `test_pige_html` perd
  `criteres_pour_idu` ; `test_pige_depot2` et `test_radar_onglets_r8` réécrits pour le rattachement
  **manuel** (file « à rattacher », `rattacher-humain` admin-only).
- **Note environnement** : `labuse_test` contenait 73 biens résiduels (pollution de runs antérieurs).
  Trois échecs (`test_pige_client::test_filtres_et_compteur`, `test_pige_marche` ×2) sont dus à cette
  pollution — **reproduits à l'identique sur `main` pristine**, donc **pré-existants, non liés à
  RADAR-4** ; ils passent sur base nettoyée.

## 9. Fichiers

Back `pige/` : `html_ingest.py`, `intake.py`, `client.py`, `marche.py`, `api.py` ; `registre/lectures.py`.
Supprimés : `pige/rattachement.py`, `pige/rattachement_html.py`.
Front : `radar/RadarEcran.tsx`, `radar/VeilleEcrans.tsx`, `admin/Radar.tsx`, `lib/api.ts`
(supprimé `radar/RadarEcran.joursDepuis.test.ts`).
Tests : `tests/test_radar4_dedup.py` (neuf) + ajustements ci-dessus.
