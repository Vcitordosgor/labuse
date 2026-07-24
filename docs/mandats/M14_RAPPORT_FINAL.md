# M14 — CORRECTION VAGUE 2 : RAPPORT DE VAGUE

**Mode** : autonome. **CC n'a rien mergé** — 6 branches poussées + ce rapport. Filet : `avant-m14`.
**Base** : `main` (M12+M13 mergées, `35febbb`). **Golden** : 116/116 (`LABUSE_DEV_MODE=1`, `PYTHONPATH=src`) sur chaque branche.
**Preuve** : chaque point corrigé a une capture de l'app en marche, ouverte et **regardée par CC** (pas seulement le rapport d'agent).

---

## 1. TABLEAU A1 — Fraîcheur des sources (ce qui justifie l'affichage E)

**Le recheck existe = le RADAR** (`labuse radar-sources`, table `source_radar`, dernier passage réel **2026-07-22**), **cron HEBDOMADAIRE** (lundi 02:40, `deploy/cron.d/radar`) — **pas 48 h**. Sonde HEAD/métadonnées (« as-tu changé ? »), zéro téléchargement. `source_checks` (contrôle manuel) = **vide** (0 ligne).

| Régime | Nb | Sources | Contrôle auto | Ce que E affiche |
|---|---|---|---|---|
| **Sondable** | **9** | BODACC, Base Adresse Nationale, Cadastre Etalab, DEAL trait de côte, DPE ADEME, DVF, Inventaire SRU, QPV 2024, SITADEL | **OUI** (radar sonde une date amont) | version + **« vérifié il y a X »** (date réelle) |
| **Non sondable** | **43** | INSEE (BPE/Filosofi/RP), SAFER, Géorisques, PLU/GPU, RGE ALTI, Parc National, Cerema… | **NON** (pas d'URL datée) | version + **cadence producteur**, aucune date |

**Le « 48 h » de Vic** : le mécanisme existe (radar) mais tourne hebdo → passer à 48 h = **éditer le cron** (`40 2 * * 1` → `40 2 */2 * *`), modification d'**infra** hors code applicatif. Ne couvrira **jamais** les 43 non sondables. **Rien de fictif n'est affiché.**

**A2 — outil « Zone »** : barre carte = distance / surface / altitude (mesures) + **zone** (dessine un polygone qui **filtre réellement** la liste + la carte aux parcelles dans la zone, `setZone`→`pointInPolygon`). Actif en mode commune, désactivé en « Toute l'île ». Le résultat EST exploité. Décision d'usage à Vic (rien modifié).

---

## 2. PREUVES PAR POINT (tous prouvés — 0 non livré)

| Point | Preuve (`qa/m14/…`) | Vérifié par CC |
|---|---|---|
| **B1** bulle « i » entière | `B/b1_bulle_i_entiere.png` | ✅ texte complet, bord droit 465 px ≤ 1440, portal |
| **B2** icônes équip. ×1,5 | `B/b2_equipements_actives.png` | ✅ rampe littérale ×1,5, seule définition (rampe identique prouvée avant/après par M13-D3) |
| **B3** Couches ouvert défaut | `B/b3_couches_ouvert_defaut.png` | ✅ `[data-couches-drawer]` présent au load |
| **C1** bouton Projet multi + grisé | `C/c1_liste_grise_et_active.png`, `c2_les_deux_grises.png` | ✅ Alpha grisé « ✓ dedans », Beta actif ; ajout au 2e projet OK |
| **D1** placeholder | `D/d1_placeholder.png` | ✅ « Rechercher : IDU, adresse exacte, commune… » |
| **D2** barre cliquable bord à bord | `D/d2_clic_droite.png` | ✅ clic extrême droite → focus input (`w-full` manquant = cause) |
| **E1** Sources deux régimes | `E/e1_sources_deux_regimes.png` | ✅ « vérifié il y a X » (sondable), « Cadence producteur » (non), 0 « — » nu |
| **F1** verdicts sans « v2 » | `F/f1_verdicts_sans_v2.png` | ✅ « Brûlante/Chaude » partout, clés `brulante`/`chaude` intactes |
| **F2** « + Chercher plus » retiré | `F/f2_sans_chercher_plus.png` | ✅ bouton parti, phrase posée |

---

## 3. ATTENTION RÉGRESSIONS — pourquoi la correction M13 n'avait pas tenu

**Cause unique et vérifiée** : les trois fixes (bulle, icônes, Couches) étaient dans **M13 LOT D (`fix/m13-d-couches`)**, une branche **JAMAIS mergée** sur `main`. Vic n'avait mergé que `fix/m13-c-scroll` et `fix/m13-f-lisibilite` (+ leurs embarquées A et B). Vérifié : `git merge-base --is-ancestor origin/fix/m13-d-couches main` = **NON**. Les captures M13 étaient **réelles mais prises sur la branche D isolée**, jamais sur `main`. (Idem M13-E « projets grisés » — LOT E jamais mergé — d'où le M14-C.)

**Pour éviter la récidive** : le **LOT G** (§7) re-capture ces points **sur `main` après merge** — c'est le seul endroit où la vérité de l'utilisateur se lit.

---

## 4. TEXTES PRODUITS (à relire par Vic)

**F1 — labels de verdict** (`lib/status.ts` `TIER_V2_META`) : « Brûlante v2 » → **« Brûlante »**, « Chaude v2 » → **« Chaude »**. Affichage seulement — clés `brulante`/`chaude`, `tier_v2`, endpoints `/v2/*`, `model_version` **inchangés**.

**F2 — phrase de remplacement** (`CLIENT.projet.ajouterDepuisFiche`, recopiée par l'agent) : incite à enrichir le projet depuis la fiche parcelle via le bouton « Projet » (le peuplement au lancement marche déjà sur main — M13-E1 observé fonctionnel).

**E1 — Sources** : intro reformulée (deux régimes) + pied de page (« radar hebdomadaire, couvre les sources à date interrogeable »). Filosofi = « millésime 2021 ». Repli honnête « millésime non tracé en base » pour BPE/SAFER.

---

## 5. DÉCISIONS ET RÉVERSIBILITÉ

| Point | Choix | Alternative écartée | Revenir |
|---|---|---|---|
| B1 | Tip en **portal** (`createPortal` sur body) | tooltip absolu (rogné) | rétablir l'ancien Tip |
| B2 | rampe ×1,5 | garder rampe M12 | rediviser par 1,5 |
| B3 | Couches défaut `true`, repli sur bascule verdict | replié + auto-close 10 s | `useState(false)` |
| C1 | menu toujours ouvert, grisé sélectif | saut direct au projet (bug) | — |
| E1 | 2 régimes selon `radar.statut` | date manuelle (supprimée) | — |
| E2 Filosofi | « 2021 » (Vic) | vide | retirer de `MILLESIME_VERIFIE` |
| E3 48 h | **non fait** (édition cron = infra) | fabriquer un faux 48 h | éditer `deploy/cron.d/radar` |
| F1 | labels sans v2, clés intactes | renommer les clés (risqué) | `TIER_V2_META` labels |

---

## 6. NON FAIT / BLOQUÉ

- **Recheck 48 h** : le mécanisme (radar) **existe** et est **branché** (E1 affiche `derniere_verif`), mais il tourne **hebdo**. Le passer à 48 h = **1 ligne de cron** (`deploy/cron.d/radar`) — **modification d'infra hors périmètre de ce lot**, laissée à Vic. Ne couvrira jamais les 43 sources non sondables. **Aucun contrôle 48 h fictif n'a été simulé.**
- **BPE INSEE / SAFER (DAAF) « Version en service »** : millésime **non tracé en base localement** → repli honnête, **non inventé** (boussole).

---

## 7. BRANCHES, ORDRE DE MERGE, ET LOT G

CC ne merge pas. Vic merge en `git merge --no-ff`. Les 6 branches partent de `main` (`35febbb`) — **indépendantes** (aucune n'en embarque une autre, contrairement à M13).

| Ordre | Branche | Lot | Note conflit |
|---|---|---|---|
| 1 | `audit/m14-a` | A + **ce rapport** | docs seuls |
| 2 | `fix/m14-b-regressions` | B | `Tip.tsx`, `MapView.tsx`, `LeftPanel.tsx` — vs personne (D non mergée) : propre |
| 3 | `fix/m14-c-projet-multi` | C | `Fiche.tsx` |
| 4 | `fix/m14-d-recherche` | D | `Header.tsx` (1 ligne) |
| 5 | `fix/m14-e-sources` | E | `SourcesPage.tsx` |
| 6 | `fix/m14-f-vocab` | F | `status.ts` + surfaces v2 — vs B (LeftPanel) et E (SourcesPage) : zones différentes, propre |

### LOT G — re-vérification SUR `main` APRÈS MERGE (le point du mandat)
**À exécuter une fois A→F mergées.** CC (ou Vic) reboote `main` mergée et re-capture. Checklist :
- [ ] Bulle « i » entière (B1) — **sur main**
- [ ] Icônes équipements ×1,5 (B2) — **sur main**
- [ ] Couches ouvert par défaut (B3) — **sur main**
- [ ] Bouton Projet multi + grisé sélectif (C1) — **sur main**
- [ ] Placeholder + barre cliquable bord à bord (D1, D2) — **sur main**
- [ ] Sources deux régimes, aucun « — » nu (E1, E2) — **sur main**
- [ ] Plus aucun « v2 » (F1) — **sur main**
- [ ] « Chercher plus » disparu (F2) — **sur main**

Un point absent sur `main` alors qu'il était présent sur sa branche = **conflit de merge mal résolu** → à re-corriger. **C'est la garantie que « corrigé » = « corrigé sur ce que voit l'utilisateur ».**

> CC peut exécuter le LOT G immédiatement si Vic autorise un merge local de A→F (comme aux vagues précédentes) — dis-le et je reboote `main` mergée + recapture les 8 points.
