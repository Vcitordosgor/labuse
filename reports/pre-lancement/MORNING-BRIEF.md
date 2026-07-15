# MORNING BRIEF — batch autonome de nuit (2026-07-16)

Lis **ce seul fichier**, regarde les captures des ✅, et merge. **Rien n'est mergé, rien n'est poussé
sur main** (règle n°1 respectée : `main` intacte). Chaque item vit sur sa branche `feat/nuit-*`.
**Zéro touche scoring/cascade/étage 0/run q_v6_m8** sur tous les items (git diff par branche le prouve).
**Privacy** respectée partout (jamais un particulier nommé). **IA/synthèses groundées** (faits réels only).

## Vue d'ensemble

| # | Item | Branche | État | Capture(s) |
|---|------|---------|------|-----------|
| 1 | **Courrier** (43) | `feat/nuit-courrier` | ✅ prêt | `nuit-courrier-1..5-*.png` |
| 3 | **Mode bailleur** (33) | `feat/nuit-bailleur` | ✅ prêt | `nuit-bailleur-sru.png` |
| 5 | **Due diligence** (42) | `feat/nuit-diligence` | ✅ prêt | `nuit-diligence-checklist.png` |
| 7 | **Vélocité admin** (39) | `feat/nuit-velocite` | ✅ prêt | `nuit-velocite-classement.png` |
| 2 | **Simulateur ZAN** (41) | — | ⚠️ constat rendu, **non construit** | — |
| 4 | **Assemblage** (35) | — | ⚠️ constat rendu, **non construit** | — |
| 6 | **Matching promoteur** (34) | — | ⚠️ constat rendu, **non construit** | — |
| 8 | **Page sources** (2) | — | ⚠️ **déjà fait** (existant) | — |

**Priorité tenue** (1→8), **arrêt propre** : 4 items construits solidement + 4 documentés plutôt que
8 bâclés (règle « mieux vaut 4 solides »). Détail + commandes de merge ci-dessous.

---

## ✅ 1 — COURRIER (`feat/nuit-courrier`)
**Parcours guidé 4 étapes** : Parcelle (IDU) → Motif → **Rédaction (brouillon groundé éditable)** →
Demande. `POST /courrier/demande` (table `courrier_demandes`) **enregistre une DEMANDE** (pas d'envoi
auto) → « notre équipe prépare l'envoi et reviendra vers vous ». **Privacy** : adressage générique,
aucun particulier nommé/stocké. tsc/build verts, endpoint testé. Détail : `NUIT-courrier.md`.
```
git checkout main && git merge --no-ff feat/nuit-courrier
```

## ✅ 3 — MODE BAILLEUR (`feat/nuit-bailleur`)
`/modules/bailleur` : **contexte SRU** (statut, taux/objectif LLS, **déficit LLS dérivé** des chiffres
sourcés `commune_contexte_sru`), marquage `carencee` par parcelle, **priorisation carencées**, compte
communes carencées (île). M06 : carte SRU + badge. Testé Saint-Leu (**déficit 1 814**), Saint-Denis
(conforme). Grounded (aucune invention). Détail : `NUIT-bailleur.md`.
```
git checkout main && git merge --no-ff feat/nuit-bailleur
```

## ✅ 5 — DUE DILIGENCE (`feat/nuit-diligence`)
`/modules/duediligence` : par parcelle, **checklist** (points cascade à vérifier : couche+sévérité+
détail) + **score de risque consolidé 0-100** (déterministe depuis les facteurs existants ; HARD_EXCLUDE
→100) + **propriétaire** (PM nommée / particulier masqué). M10 : badge risque + checklist. Testé
(risque 80/40). Détail : `NUIT-diligence.md`.
```
git checkout main && git merge --no-ff feat/nuit-diligence
```

## ✅ 7 — VÉLOCITÉ ADMIN (`feat/nuit-velocite`)
`/modules/velocite` : **rang** (1 = commune la plus rapide, par délai médian) + **tendance** (médiane
cohortes anciennes vs récentes). M05 : badge `#rang` + délai coloré (rapide/lent) + flèche tendance.
Testé (#1 Saint-Pierre 8 m, stable). Grounded (agrégats réels). Détail : `NUIT-velocite.md`.
```
git checkout main && git merge --no-ff feat/nuit-velocite
```

---

## ⚠️ NON CONSTRUITS — constat rendu, prêts à bâtir (raison : temps du batch)

### 2 — SIMULATEUR ZAN (41)
**Constat** : `/moteurs/zan` montre l'artificialisation OCS-GE par commune + parcelles ZAN-compatibles.
- **Enveloppe ZAN restante par commune (hectares avant 2031) = DONNÉE ABSENTE** : les quotas SAR/SCOT /
  ENAF (CEREMA/DGALN) **ne sont pas en base**. Le bandeau le dit déjà (« quotas en attente »). **NE PAS
  FABRIQUER** — c'est une donnée réglementaire à ingérer (tâche data, pas nuit).
- **Faisable sans nouvelle donnée** (prêt à bâtir) : marquer chaque parcelle **« dans les clous ZAN »**
  (sol déjà `artificialise` = zéro dette) vs **« à risque »** (`naturel`/`agricole` = artificialisation à
  justifier), via `spatial_layers kind='ocs_ge'` + la cascade `ocs_ge` existante. ~½ journée.
**Recommandation Vic** : décider l'ingestion des quotas CEREMA (débloque l'enveloppe restante).

### 4 — ASSEMBLAGE (35)
**Constat** : `/moteurs/assemblage` calcule contiguïté + SDP cumulée (somme des résiduels) + score.
- **Prêt à bâtir** (données présentes) : (a) **classer le type de propriétaire** (PM publique/SCI via
  `parcelle_personne_morale` — privacy OK) et **prioriser les assemblages 100 % personnes morales**
  (plus approchables) ; (b) **gain SDP combiné** = `compute_residuel(ST_Union(geoms))` vs somme des
  résiduels (même moteur `faisabilite/residuel.py`). ~1 journée.

### 6 — MATCHING PROMOTEUR (34)
**Constat** : `partners.match_run` = match binaire sur 2 **profils démo étiquetés** (fictifs, assumés).
- **Prêt à bâtir** : **score de compatibilité 0-100** (au lieu de oui/non) + **« pourquoi »** (critères
  qui collent : commune/surface/SDP/zonage/statut). Données présentes (q/a scores, cascade, zonage).
  Rester honnête sur le côté démo des profils. ~1 journée.

### 8 — PAGE SOURCES (2) — **DÉJÀ FAIT**
`SourcesPage.tsx` affiche **déjà** par source : **date de dernière donnée** (via `ingestion_runs` réel +
millésime), **cadence** (`CADENCE_PAR_SOURCE` : DVF semestriel, SITADEL mensuel, BODACC quotidien, PLU à
la révision…) et **prochaine MAJ attendue** (calculée), avec badges À JOUR / MAJ ATTENDUE / À VÉRIFIER —
exactement l'argument de confiance demandé. **Rien à construire.** Polissage possible (déporter la cadence
du front vers `config/sources_cadence.yaml` + l'exposer via `/sources`) — cosmétique, non prioritaire.

---

## Merge en un coup (les 4 ✅, après revue des captures)
```
cd /Users/openclaw/Desktop/labuse && git checkout main
git merge --no-ff feat/nuit-courrier && git merge --no-ff feat/nuit-bailleur \
 && git merge --no-ff feat/nuit-diligence && git merge --no-ff feat/nuit-velocite
```
Puis redémarrer l'API (`labuse api --port 8010`) et rebuild le front (`cd frontend && npm run build`).

## Garanties transverses
- **Aucun merge, aucun push** par CC. `main` = inchangée (`b43ae36`).
- **Zéro scoring** : chaque `git diff main..feat/nuit-*` = endpoints modules + composants front + QA.
  Aucun fichier scoring/cascade/étage 0/run. Pas de re-golden nécessaire.
- **Privacy** : courrier (adressage générique), bailleur/diligence (PM nommée, particulier masqué).
- **Données manquantes NOTÉES, pas inventées** : enveloppe ZAN (quotas CEREMA) explicitement absente.
- **Hors périmètre non touché** : M7 (VPS/auth), point 5 (mails opérateur), 7/16 (notifs), spin-off.

*Reste : ZAN per-parcelle (½ j), Assemblage (1 j), Matching (1 j) — constats prêts. Sources = déjà fait.*
