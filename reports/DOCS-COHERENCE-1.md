# DOCS-COHERENCE-1 — les 8 documents de Docs disent la même chose

Branche `feat/docs-coherence-1` (worktree `labuse-docs2`, ports 8830/6030). Témoins :
**97415000BY0083** (Saint-Paul, U4c, 2 458 m², 11 bâtiments, SUCCESSION CHAMCIRKAN
ARCHABY PHILIPPE) et **97408000BL0020** (La Possession, UAa). Comparatif sur
BY0083 + BY0361 + BY0272. **Pas de merge.**

## REPRISE — dernier point traité

> **Lot 0 FAIT (commité).** Reprendre au **Lot A** (une vérité par donnée, transverse).
> Le harnais `scripts/docs_coherence.py` mesure 10 écarts sur BY0083 (état « avant »
> ci-dessous) ; objectif final = 0. Serveur API local : voir « Lancer » en bas.

---

## Lancer (rappel environnement)

```
# API (PDF-capable via le venv de labuse-main, PYTHONPATH forcé sur CE worktree) :
PYTHONPATH=$PWD/src PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  LABUSE_ENV=local DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  ~/Desktop/labuse/.venv/bin/labuse api --port 8830

# Harnais de cohérence (après fin de lot) :
PYTHONPATH=$PWD/src … ~/Desktop/labuse/.venv/bin/python -m scripts.docs_coherence 97415000BY0083
```

Gotcha : le venv `~/Desktop/labuse/.venv` est un editable qui pointe sur
`labuse-main/src`. **Sans `PYTHONPATH=$PWD/src` l'API sert le code de labuse-main, pas
ce worktree.** Le Bilan se rend EN PROCESS (sa route d'écriture exige une session
compte, absente en mode local) — même chemin que la route (`bilan.pdf.construire_pdf`).

---

## Lot 0 — harnais — FAIT

| pt | statut | preuve | note |
|----|--------|--------|------|
| 0.1 | ✅ | `scripts/docs_coherence.py` ; CSV `reports/DOCS-COHERENCE-1/before/dc-before-97415000BY0083.csv` | génère les 8 documents, extrait le texte, confronte 18 données partagées → tableau document × donnée, écart marqué `/!\`. Bilan rendu en process. |
| 0.2 | ✅ | `config/mots_interdits.yaml` v2026-10-26 (24 → 30) ; `tests/test_circuit2_lot0bis.py::test_mots_interdits_liste_versionnee` vert | +6 : « Excel », « comme dans », « dont bâti », « à confirmer — à confirmer », `&#x27;`, « parcelle(s) ». La sonde `recette_exports1` rejoue la liste la nuit (verdict distinct). |

### État « avant » (BY0083) — 10 écarts mesurés

```
donnée                 Dossier   Apporteur Prédossier ÉtudeZone Gabarit  Comparatif Faisabilité Bilan
/!\ surface terrain    2458      2458      2405       —         —        —          2458        2405
    emprise bâtie      900       —         —          —         —        —          —           —
/!\ zone impl. libérée 869       —         1699       —         869      —          1691        —
    zone impl. déduite —         —         —          —         867      —          —           —
/!\ pente              9,7°      —         —          —         —        —          14,6 %      —
/!\ hauteur faît/égout 9/6       —         9/?        —         9/?      —          9/6         —
    recul voie         4         —         —          —         4        —          4           —
/!\ stationnement      2 pl/log  —         imposés    —         non chif —          art.12.2    —
    pleine terre       40        —         —          —         —        —          40          —
/!\ prix bâti €/m²     3602      —         —          —         —        2687       —           —
/!\ prix terrain €/m²  250       —         —          —         —        479        —           —
    prix neuf VEFA     4745      —         —          —         —        —          —           —
    SDP résiduelle     —         —         —          —         —        453        —           —
    SDP max régl.      —         —         —          —         —        1327       —           —
/!\ contraintes        oui       oui       oui        —         oui      oui        AUCUNE      oui
/!\ propriétaire       pers.mor. pers.mor. particulier succession —      pers.mor.  —           —
/!\ date des données   21/10     21/10     —          21/10     21/10    21/10      27/10       —
```

**Diagnostic des 10 écarts et lot cible :**

1. **surface 2458 vs 2405** — le Dossier/Étude servent la **contenance cadastrale**
   (`parcels.contenance_m2` = 2458, doctrine « surface = contenance ») ; le **Bilan** et
   le **CERFA** servent la **surface géométrique** (`parcels.surface_m2` = 2404,9 → 2405).
   → **Lot A (surface) + G2 (terrain du Bilan)**.
2. **zone d'implantation 869 (Gabarit/Dossier §10) vs 1 691 (Étude) vs 1 699 (CERFA)** —
   aucune des deux valeurs n'est nommée (terrain libéré / bâti déduit). → **Lot A3 / D2 / F1**.
3. **pente 9,7° (Dossier) vs 14,6 % (Étude, LiDAR)** — deux sources, deux unités, jamais
   réconciliées. → **Lot A4 / F3**.
4. **hauteur** — Dossier « 9 m faîtage · 6 m égout » ; Gabarit « 9,0 m » seul ; Étude
   « 6 m » (égout) en page 1. → **Lot A7 / D2**.
5. **stationnement** — Dossier « 2 places / logement » (Sourcé) ; Gabarit « Règle connue,
   non chiffrée » ; Étude « 2 place/logt art. 12.2 » + bandeau « non modélisé ». Et sur
   résidence étudiante, 2 pl/log est **faux** (L151-35). → **Lot A6 / D2 / F6**.
6. **prix bâti 3 602 (Dossier §8) vs 2 687 (Comparatif)** ; **prix terrain 250 (Dossier,
   13 ventes « puis échantillon insuffisant ») vs 479 (Comparatif)**. Trois prix, aucun
   partagé. → **Lot A8**.
7. **contraintes** — Dossier §5 relève aléa mouvement de terrain + DPU + Parc national ;
   l'**Étude affirme « Aucune contrainte cartographiée ne touche le terrain »**. → **Lot A5 / F2**.
8. **propriétaire** — Dossier/Apporteur/Comparatif « Personne morale » ; CERFA
   « particulier » (case cochée) ; la vérité DGFiP = **SUCCESSION**. → **Lot A1 / B1 / C1**.
9. **date des données** — tous « LABUSE au 21/10/2026 » sauf l'**Étude « Généré via
   LABUSE le 27/10/2026 »** (date de génération, pas du run). → **Lot A10**.

Preuves « avant » : `reports/DOCS-COHERENCE-1/before/*.txt` (pdftotext des 8 documents),
PDF dans `reports/DOCS-COHERENCE-1/pdf/` (gitignoré).

---

## Lots A → H — à faire

(Statuts mis à jour à chaque lot ; un commit + une régénération des PDF par lot.)

- **Lot A** — une vérité par donnée (A1 propriétaire · A2 emprise · A3 zone impl. ×2 ·
  A4 pente · A5 contraintes · A6 PLU chiffré · A7 hauteur · A8 prix · A9 SDP ×3 · A10 date).
- **Lot B** — Dossier (B1..B9). **Lot C** — Apporteur (C1..C3). **Lot D** — Gabarit (D1..D2).
- **Lot E** — Étude de zone (E1..E5). **Lot F** — Étude de faisabilité (F1..F9).
- **Lot G** — Bilan (G1..G6). **Lot H** — clôture (0 écart BY0083 + BL0020, hook vert, pas de merge).
