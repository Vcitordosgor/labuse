# FRONT-CHIFFRES-2 — les 420 occurrences, jusqu'à la dernière

**Branche** `fix/front-chiffres-2` (depuis `origin/main` `3a0f9b5a`, = main APRÈS merge de COHERENCE-FIX-1 + FRONT-CHIFFRES-1) · worktree `~/Desktop/labuse-frontchiffres` · 8615/5815 · **plusieurs sessions**.

**Règle d'or.** Après ce mandat, le front **ne décide plus aucun chiffre, seuil, plafond,
conversion ni libellé dérivé d'un nombre** : il rend ce que le back sert, sous un id du registre,
avec un format de `lib/format.ts`. Les valeurs affichées ne changent pas — sauf quand l'ancienne
était fausse (listé dans `CHANGEMENTS.csv`).

**Base.** `docs/audit-2026-09/FRONT-CHIFFRES-1/INVENTAIRE.csv` : 966 occurrences. On ne touche
NI les 525 `legitime`, NI les 21 `supprimer` (déjà traités en FC-1). Restent **420 actionnables**
= 213 `remonter_back` + 207 `declarer_registre`.

---

## Instruments en place (hérités de COHERENCE-FIX-1, vérifiés au démarrage)
- **Banc** : `labuse coherence` (= `python -m scripts.coherence.banc --echantillon`), DSN via
  `LABUSE_COHERENCE_DSN`/`LABUSE_DATABASE_URL`, API via `LABUSE_COHERENCE_API`. Écrit `ECARTS.csv`,
  journalise `coherence_runs`.
- **Verrou V6b** : `tests/verrous/test_v6b_coherence.py` (le banc en test).
- **Vocabulaire d'absence** (lot D) : `src/labuse/registre/absences.py` — CINQ formes
  (non_disponible / aucun / hors_perimetre / sans_objet / non_calculable). Toute phrase d'absence
  déclarée doit matcher une forme, sinon V6 échoue. Rendu compact = « — » (format.ts).
- **Verrou front** : `tests/test_front_chiffres_orphelins.py` (FC-1, réconcilié au merge).

**Baseline (Étape 0)** : servers 8615/5815 up ; `test_v6b_coherence` + `test_front_chiffres_orphelins`
**verts (4/4)** ; banc `--echantillon` rejoué → `<!-- BANC_BASELINE -->`.

---

## Plan — 159 familles (`FAMILLES.csv`), ordre = gravité

| priorité | type | familles | lignes | traitement |
|---|---|---|---|---|
| P1 | **seuil / plafond** | F01–F32 (32) | ~75 | remonter le seuil au moteur qui porte la notion, servi sous un id ; le composant lit |
| P2 | **calcul** | F33–F68 (36) | ~130 | le calcul passe au back sous un id ; conversions d'unité comprises |
| P3 | **texte chiffré / defaut** | F69–F113 (45) | ~95 | nombre en dur dans la prose → interpolé depuis l'id servi ; `?? 0` → vocabulaire d'absence |
| P4 | **format** | F114–F159 (46) | ~120 | `toLocaleString`/`toFixed` bruts → formateur partagé + `chiffreId` (déclaration) |

`INVENTAIRE.csv` (ce dossier) = l'inventaire FC-1 **rejoué** avec deux colonnes ajoutées :
`famille` et `etat` (a_faire · remonté · déclaré · fusionné · arrêté_pour_décision).

### Le patron d'une famille (un commit)
1. **Remonter** (`remonter_back`) : la règle/seuil/calcul va dans le moteur back qui porte déjà la
   notion (jamais un moteur parallèle), servi sous un id du registre ; le composant lit l'id.
2. **Déclarer** (`declarer_registre`) : l'id existe côté back → déclaré au registre (fiche V5d,
   commune V5e, outils V5f) avec lecteur front, tolérance, phrase d'absence ; `sync` base faite ici.
3. **Tolérance** dans `NOTIONS.csv` (dérivée par unité) ; banc `--echantillon` rejoué : la notion
   apparaît, 0 écart nouveau.
4. **Même valeur partout** : `grep` avant/après — tout lecteur (autre composant, PDF, Copilote) lit l'id.
5. **Capture** avant/après (sauf déclaration pure sans effet visible).
6. `tsc` 0, `vitest` vert, V6 vert, tests back de la famille verts.

### Garde-fous
- Toute valeur affichée modifiée → `CHANGEMENTS.csv` (id · ancienne · nouvelle · pourquoi l'ancienne
  était fausse). Non listé = régression.
- Aucun seuil inventé : un seuil remonté garde sa valeur, sauf s'il contredit un seuil déjà servi
  (le back gagne, noté dans `CHANGEMENTS.csv`).
- Aucun run île / bascule. Une famille exigeant un recalcul de table est isolée en fin de mandat et
  **arrêtée pour décision de Vic** (`etat=arrêté_pour_décision`).
- Un id = une notion ; deux lignes qui décrivent la même chose → un seul id (`etat=fusionné`).

---

## Journal des sessions

### Session 1 (Étape 0 + planification)
- Worktree recréé sur `fix/front-chiffres-2` depuis `origin/main` `3a0f9b5a` (l'ancien worktree
  FC-1 avait été supprimé ; travail FC-1 sauf sur `origin/main`). `.env` + `node_modules` (symlink).
- Baseline verrous verts, banc lancé.
- `FAMILLES.csv` (159) + `INVENTAIRE.csv` rejoué (colonnes famille/etat) produits.
- **Familles traitées : voir `FAMILLES.csv` colonne `etat` + `CHANGEMENTS.csv`.**

<!-- PROGRESSION -->

---

## Sortie visée
- 0 occurrence `remonter_back` / `declarer_registre` restante (toutes `remonté`/`déclaré`/`fusionné`,
  ou `arrêté_pour_décision` avec justification).
- `test_front_chiffres_orphelins.py` étendu : liste blanche = les 525 `legitime` commentés ; toute
  occurrence des motifs du lot A hors liste fait échouer la suite.
</content>
