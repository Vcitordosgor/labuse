# SDP-VERIF-1 phase 2 — libellés avant → après

Reformulation en **« surface de plancher constructible restante (bâti conservé) »** (longueur
adaptée à la place : phrase pleine en PDF/verdict, « · bâti conservé » en ligne, sous-ligne
« bâti conservé » en tuile). Le vocabulaire **« bâti conservé »** réutilise la DA existante
(`frontend/src/lib/perimetres.ts` : `PERIM_RESIDUEL_COURT = 'bâti conservé'`). **Aucun calcul
touché** — la SDP servie reste 5 050 m² (dump fiche avant/après identiques sur la valeur).

| # | Fichier:ligne | Avant | Après | Surface |
|---|---------------|-------|-------|---------|
| 1 | `scoring/score_labuse.py:256` | `{sdp} m² de droits à construire restants` | `{sdp} m² de surface de plancher constructible restante (bâti conservé)` | Analyse LABUSE (contribution) — **la phrase exacte citée par Vic** |
| 2 | `api/app.py:5886` | `Potentiel modéré — droits à bâtir partiellement dormants` | `Potentiel modéré — surface de plancher constructible restante, bâti conservé` | verdict §10 fiche (libellé servi) |
| 3 | `exports/verdicts.py:100` | `SDP résiduelle (droits à bâtir non consommés) ≈ …` | `surface de plancher constructible restante (bâti conservé) ≈ …` | Dossier PDF §10 |
| 4 | `cascade/layers/etage0_ext.py:174` | `… — droits à construire inconnus …` | `… — surface constructible restante (bâti conservé) inconnue …` | Analyse LABUSE (socle, cas non calculé) |
| 5 | `frontend/.../fiche/Fiche.tsx:935` | tuile `SDP restante` (sans qualif.) | tuile `SDP restante` + sous-ligne **`bâti conservé`** + infobulle « …ce n'est pas du terrain libre… » | bandeau 6 tuiles de la fiche |
| 6 | `frontend/.../fiche/Fiche.tsx:1291`+`:1914` | tuile `SDP restante` (§10) | idem sous-ligne `bâti conservé` + infobulle | §10 Potentiel (ChiffreDissous) |
| 7 | `frontend/.../fiche/Fiche.tsx:1912` | `{n} m² de SDP résiduelle` | `{n} m² de SDP constructible restante · bâti conservé` | encadré Verdict §10 |
| 8 | `copilote_v2/resume_fiche.py:34` | tuile `SDP restante` | tuile `SDP restante (bâti conservé)` | bandeau Analyse LABUSE / Copilote |
| 9 | `exports/miroir.py:1037` | tuile `SDP restante` | tuile `SDP restante (bâti conservé)` | bandeau de garde du Dossier PDF |

**Correctif du « 29 % » (libellé, pas le calcul) :**

| # | Fichier:ligne | Avant | Après |
|---|---------------|-------|-------|
| 10 | `frontend/.../panel/FiltreLabuse.tsx:354` | `Part **de la parcelle** déjà couverte par du bâti (run servi) — la même que « État du sol ».` | `Part **de l'emprise constructible** déjà couverte par du bâti (run servi) — **pas « de la parcelle »** : sur un grand terrain la part du sol bâti est plus faible. La même que « État du sol ».` |

`taux_emprise_pct` = emprise bâtie ÷ **emprise constructible** (backend `etat_sol`/filtre emprise :
app.py:1623/1818, `residuel.py:215`). Sur AT1066 : **29 %** de l'emprise constructible = **20,5 %
de la parcelle** (1 858 m² ÷ 9 054 m²). Le filtre disait « de la parcelle » à tort.

**Déjà correct (DA existante, laissé tel quel) :**
- `frontend/.../compare/ComparePanel.tsx:63` — « SDP résiduelle · **bâti conservé** » (PERIM_RESIDUEL_COURT) ✔
- `ComparePanel.tsx:70` — « Taux d'occupation du gabarit · bâti existant ÷ emprise constructible » ✔
- `bati.py:68/78` — « couvrant X % **de la parcelle** » = vraie part de la parcelle (bati_ratio), correct, NON touché.

## Captures
- `filtre_emprise_avant.png` / `_apres.png` — le « 29 % » : « de la parcelle » → « de l'emprise constructible ».
- `fiche_bandeau_avant.png` / `_apres.png` — tuile « SDP RESTANTE · 5 050 m² » → + sous-ligne « bâti conservé ».
- `fiche_potentiel_avant.png` / `_apres.png` — §10 : « 5 050 m² de SDP résiduelle » → « …de SDP constructible restante · bâti conservé ».
- Mock : `fiche_AT1066_avant.json` / `_apres.json` (dump réel de `_q_v2_fiche`) — `pt.sdp_residuelle_m2 = 5050` **inchangé** ; seul `pt.libelle` change.
- Harnais : `capture_sdpverif.mjs` (Playwright ; mock `/parcels/{idu}` → le dump, rend le vrai composant sans booter l'API).

Vérifs : tsc 0 · vitest 243/243 · pytest ciblé 231 passed/5 skipped (env) · 0 idle-in-transaction.
