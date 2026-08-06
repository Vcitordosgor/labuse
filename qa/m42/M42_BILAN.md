# M42 — BILAN (voisinage hyper-local & historique des permis du site)

**Branche `m42-voisinage-historique`** · base `main` 65f5f314 (M41 mergé) · commits atomiques
`[M42-Px]`. **0 tier, 0 verdict, 0 bascule, 0 merge.** Deux blocs de CONTEXTE en fiche, jamais fusionnés.

---

## Sort des branches antérieures (P0)

`feat/algo3-voisinage` (+ `-v2`) = **même travail « ALGO-3 »** : voisinage exploré comme **feature de
scoring** (challenger ML, centroïde-à-centroïde, anti-fuite, as-of). **Verdict final : NE PAS
PROMOUVOIR.** Non applicable à M42 (contexte fiche, 0 tier). **Repris = la technique de requête**
(linkage `sitadel_permits.idu_codes`, buffer métrique 2975) ; **pas** le cadrage ML (sémantique fiche
inverse : l'historique INCLUT le site, le voisinage regarde le RÉCENT 36 mois). On a emprunté, pas
mergé. ⚠ Résidu consigné : 7 tables `algo3_*` en base (branche non mergée) — **à nettoyer, hors
périmètre servi** (je ne m'appuie sur aucune en code servi).

---

## PHASE 1 — Moteur (`src/labuse/api/site_voisinage.py`, point de calcul unique par bloc)

- **`historique_permis(db, idu)`** — « Sur cette parcelle » : permis rattachés (`idu_codes ? idu`,
  M38 dépôts datés) + caducité (`pc_caducs`, rattaché parcelle). Liste datée, un caduc DIT caduc.
- **`voisinage_proche(db, idu)`** — « Autour, à moins de 100 m » : ventes DVF + permis récents
  (36 mois) dans le buffer 100 m **polygone-à-polygone** (meilleure sémantique que centroïde), la
  parcelle EXCLUE. Prix médian seulement si n≥3, sinon « échantillon insuffisant ». None si vide.

**Perf** (`scripts/m42_indexes.py`, écriture hors scoring, idempotent) : **GIN sur `idu_codes`**
(historique 10 ms → **0,25 ms**) + **colonne générée `geom_2975` indexée** sur les permis (voisinage
48 ms → **16,8 ms**, plus de `ST_Transform` live). **Contribution M42 ≈ 17 ms/fiche.** Temps de
réponse fiche mesuré (endpoint premium, blocs inclus) : caduc+dense **51 ms**, dense **82 ms**, rural
**17 ms** — bien sous la dette GeoJSON commune (2,2 s). Aucune dégradation servie.

---

## PHASE 2 — Fiche

- **« Sur cette parcelle »** : liste (type, date de dépôt, date d'autorisation) + caducité si
  applicable. Étiquette Sourcé Sitadel. **Honnêteté M38** : « autorisations et dépôts uniquement —
  refus et dossiers en cours non publiés ». Un caduc **dit caduc, pas masqué**.
- **« Autour, à moins de 100 m »** : compte de ventes DVF (36 mois) + prix médian si n≥3 (sinon
  « échantillon insuffisant ») + compte de permis (datés au dépôt, cohérent M38), **maille affichée
  explicitement**. Honnêteté M38.
- Rendu **one-pager** (`export.py`) + **front** (`Fiche.tsx` + `types.ts`, `tsc -b` 0). Deux blocs
  DISTINCTS. **Parcelle sans matière → aucun bloc** (doctrine M38, vérifié rural). **0 tier, 0 verdict.**

---

## VÉRIFICATION (2026-08-06)

| Contrôle | Résultat |
|---|---|
| **Golden** | **117/117 PASS, 0 FAIL** (historique_site + voisinage_proche = clés fiche golden-invisibles) |
| **Re-mesure M34/M35** | **0 divergence — PASS** |
| **SHA256 vigilances M37** | `482da6f6…e9abe9` — **INCHANGÉ** |
| **Tiers servis** | **0 tier modifié** (119 brûlante / 1041 chaude) |
| **pytest** | verts — 5 échecs pré-existants (residuel×4, au_ouverture×1) |
| **tsc -b (front)** | exit 0 |
| **Perf fiche** | +~17 ms (mesuré) ; total 17–82 ms selon densité |

**Écritures DB, hors scoring, tracées** : index GIN + colonne `geom_2975` sur `sitadel_permits`.
Aucune écriture `parcel_p_score_v2` / run / cache / cascade.

### Captures (`qa/m42/screens/`)
1. `1_historique_permis_riche_caduc.png` — historique riche (2 permis + PC caduc **dit caduc**) +
   voisinage 40 ventes ~97 k€.
2. `2_voisinage_dense_urbain.png` — voisinage dense (78 ventes <100 m).
3. `3_rural_aucun_bloc.png` — zone rurale sans matière : **aucun bloc** (libellé honnête = absence).

### Maille retenue & justification (P0)
**100 m FIXE.** Distribution <100 m/36 mois : DVF médiane 2 (max 125), permis médiane 0 ; **22 % sans
voisin** ; dense 4,4 vs rural 1,2 (×3-4). Le libellé « à moins de 100 m » reste exact ; le contraste
dense/rural est une information vraie (tissu actif vs calme), pas un défaut. Écartés : rayon adaptatif
(libellé flou), N-plus-proches (fausse la distance). Digests : `historique_permis_par_tier_p0.csv`,
`voisinage_distribution_p0.csv`.

---

## Doctrine respectée
- **Sourcé + millésime** partout ; **honnêteté M38** (autorisations-seules, jamais « refusé »).
- **Rien affiché si vide** (doctrine M38) ; deux blocs jamais fusionnés (un promoteur ne les confond pas).
- **Contexte pur** : aucun impact tier/verdict. Le verdict ALGO-3 « NE PAS PROMOUVOIR » (feature de
  scoring) reste respecté — M42 n'en fait PAS un signal de score.
