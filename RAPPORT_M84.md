# RAPPORT M84 — Phase 0 : l'état réel de la fraîcheur (STOP pour arbitrage)

Branche `feat/m84-fraicheur`. Mesure pure, aucun fichier produit modifié. **STOP** : le mandant arbitre
ce qu'on rattrape (Phase 1) et le mécanisme de garantie (Phase 2). Date de mesure : 2026-08-14.

---

## Verdict en une phrase

Le retard réel n'est PAS général : **un seul vrai décrochage — SITADEL (permis), 45 j, parce que
l'ingestion delta n'a pas tourné depuis le 10/07**. DVF (T4 2025) est **normal** pour sa cadence
semestrielle. Le vrai défaut structurel : **aucun cron d'ingestion n'est déployé**, et **l'alerte de
retard (`check_fraicheur`) est un concept documenté jamais construit** — donc un décrochage passe
inaperçu (c'est exactement ce qui est arrivé aux permis).

---

## 0a — Tableau de fraîcheur

L'infrastructure existe : `src/labuse/ingestion/fraicheur.py` porte une MATRICE (source → `date_sql` →
dernière donnée réelle) et `etat_sources()` calcule cadence · dernière donnée · dernière ingestion ·
delta. **10 des 51 sources sont mesurables** (elles ont un fait daté amont) ; les 41 autres sont des
références annuelles/figées/spatiales sans cadence rapide (cadastre, RP, INSEE, PPR, SUP, ortho,
BD TOPO…) → **sans objet** pour le retard hebdomadaire.

Les 10 mesurables, triées par GRAVITÉ (cadence rapide + retard) :

| Source | Cadence | Dernière DONNÉE | Dernière INGESTION | Delta (j) | Seuil (2×cadence) | Statut |
|---|---|---|---|---|---|---|
| **SITADEL (permis)** | mensuelle | **2026-06-30** | 2026-07-10 (il y a 35 j) | 45 | 60 j | **EN RETARD** — l'ingestion delta n'a pas tourné ; ~1,5 mois de permis manquent |
| **DPE (ADEME)** | hebdomadaire | 2026-07-21 | 2026-08-13 | 24 | 14 j | **EN RETARD** — flux ADEME 974 en retard amont (~3 sem.) ; l'ingestion, elle, a tourné |
| **BODACC** | quotidienne | 2026-08-06 | 2026-08-13 | 8 | ~4 j | limite — volume faible (12,6k SIREN suivis) ; ingestion récente |
| BAN (adresses) | mensuelle | 2026-07-11 | 2026-07-11 | 34 | 60 j | à jour (bord de cadence) |
| GPU / PLU (zonage) | périodique | 2026-07-03 | — | 42 | non évalué | détection seule (nourrit la cascade GELÉE) |
| Géorisques (aléas/ICPE/SSP) | périodique | 2026-08-13 | 2026-08-13 | 1 | non évalué | à jour |
| **DVF (mutations)** | semestrielle (avril/oct.) | 2025-12-31 | — | 226 | ~360 j | **À JOUR pour sa cadence** — prochaine publication ~octobre 2026 |
| CatNat (GASPAR) | au fil de l'eau | 2025-07-08 | — | 402 | non évalué | irrégulier (arrêtés JO) — pas une alerte |
| Sudocuh (procédures) | annuelle (état 31/12) | 2024-12-31 | — | 591 | non évalué | annuel, registre curaté — normal |
| BD ORTHO 20 cm (IGN) | pluriannuelle (~3-4 ans) | 2025-01-01 | — | 590 | non évalué | re-survol IGN — normal |

Lecture : **seuls SITADEL et DPE décrochent réellement** (cadence rapide + delta > seuil). DVF est un
faux positif de retard : sa cadence est semestrielle, T4 2025 est l'état normal. Les autres sont soit à
jour, soit annuelles/irrégulières (pas une alerte).

**Doctrine respectée (M73)** : `derniere_donnee` (fait amont) et `derniere_ingestion` (quand on a
tourné) restent DEUX mesures distinctes — jamais une date d'ingestion présentée comme un millésime.

---

## 0b — Pourquoi le retard

1. **Aucun cron d'ingestion n'est déployé (« Train 8 J+1 » ABSENT).** Le VPS (`docs/DEPLOYMENT_OVH_VPS.md`)
   a un `systemd` pour le SERVICE (l'app) et un cron pour la MAINTENANCE + les SAUVEGARDES — mais **aucun
   cron ne lance `labuse ingest-permits --refresh`, DVF, DPE…** L'ingestion est **manuelle** (CLI). La
   matrice `fraicheur.py` marque SITADEL/DPE/BAN/BODACC « auto: True » = *rejouables* en delta idempotent
   — mais rien ne les rejoue. **SITADEL : dernière ingestion 10/07, il y a 35 jours ; personne ne l'a
   relancée → les permis sont gelés au 30/06.**

2. **L'alerte de retard n'existe pas (`check_fraicheur` = concept, pas code).** `fraicheur.py` DÉCRIT les
   seuils (2×30 j pour SITADEL, 2×7 j pour DPE) et dit « check_fraicheur peut l'évaluer et alerte si
   l'ingestion prend du retard » — mais **aucune fonction `check_fraicheur` n'est implémentée**, aucun
   `healthz` ne lève l'alerte. Une source peut donc décrocher **six semaines en silence** (le vrai
   défaut, cf. 2a).

3. **Le journal `ingestion_runs` est PARTIEL.** Il loggue les parcelles, l'ortho, SDES — mais **pas**
   bodacc/dpe/georisques (leur « dernière ingestion 13/08 » vient d'ailleurs). Un échec sur une source
   non journalisée ne laisserait aucune trace.

4. **DVF n'est pas « en retard »** : sa détection est le `Last-Modified` HTTP des CSV annuels Etalab ;
   le millésime 2021-2025 est le dernier publié. Rien à rattraper avant octobre 2026.

Aucune source ne montre un **amont cassé** (endpoint/format/auth changé) dans cette mesure — le blocage
est en aval : **on ne rejoue pas**.

---

## 0c — Le coût client du retard

| Source | Retard | Coût CHIFFRÉ (ce qui manque au radar) |
|---|---|---|
| **SITADEL (permis)** | données au 30/06, il y a 45 j | **~300-400 permis déposés depuis le 30/06 absents de la base.** Rythme mesuré : 209-281 permis/mois (juin 236, mai 209, avr. 174…) × ~1,5 mois. **C'est l'argument** : un radar foncier qui rate 1,5 mois de dépôts rate 1,5 mois d'opportunités. *(Compte exact = un `ingest-permits --refresh` qui interroge SDES ; l'estimation vient du rythme historique.)* |
| DPE (ADEME) | données au 21/07 | quelques dizaines de DPE 974 (flux récent faible en base) — impact marginal, et surtout un retard AMONT (ADEME), pas d'ingestion figée |
| BODACC | données au 06/08 | ~1-2 annonces (volume très faible : seuls les 12,6k SIREN propriétaires sont sondés) — négligeable |
| DVF | T4 2025 | **0 rattrapable** — normal pour la cadence semestrielle ; les mutations 2026 arriveront à la publication d'octobre 2026 |

**Le coût réel et actionnable = SITADEL : ~300-400 permis manquants.** Le reste est soit marginal (BODACC,
DPE), soit inhérent à la cadence (DVF).

---

## Ce que je propose d'arbitrer (Phase 1 + Phase 2)

**Phase 1 — rattrapage (dans l'ordre de gravité) :**
1. **SITADEL** — `labuse ingest-permits --refresh` (delta, recouvrement 3 mois, idempotent). Mesurer
   avant/après (permis nouveaux, date atteinte). **⚠ scoring** : les permis nourrissent des signaux
   (offre engagée, PC caducs, mutation) → mesurer le delta de classement AVANT toute bascule (comme M81) ;
   si significatif, STOP et rapport (rejeu de run éventuel).
2. **DPE** — `ré-ingestion API par commune` si tu veux, mais l'impact est marginal (retard amont ADEME).
3. **BODACC** — déjà quasi à jour (13/08) ; un refresh est trivial.
4. **DVF / Sudocuh / CatNat / ortho** — **rien à faire** (cadence non atteinte).

**Phase 2 — garantie (le vrai chantier structurel) :**
- **2a** : implémenter **`check_fraicheur`** (la fonction manquante) — compare `delta_donnee_jours` au
  seuil `2×cadence` de chaque source, lève une alerte VISIBLE (entrée `fraicheur_etat` + `/healthz` +
  page Sources). Compléter `ingestion_runs` pour journaliser TOUTES les ingestions (bodacc/dpe/georisques
  inclus) → un échec ne peut plus être silencieux.
- **2b** : les seuils par cadence sont **déjà décrits** dans `fraicheur.py` (2×30 j, 2×7 j…) — les
  matérialiser dans `check_fraicheur`.
- **2c** : la page Sources montre déjà `derniere_donnee` (colonne distincte du millésime, M73 OK) — y
  ajouter le **statut « décroche »** (rouge) piloté par 2b.
- **2d** : après le rattrapage SITADEL, le bloc « cette semaine » (M83) doit refléter des permis réels ;
  sinon la fenêtre est fausse (à revérifier).
- **Le déclencheur** : **déployer un cron d'ingestion** (`labuse ingest-permits --refresh` quotidien +
  BAN mensuel + DPE hebdo) — le « Train 8 J+1 » qui n'a jamais été posé. Sans lui, on rattrape une fois
  et on redécroche.

---

## Garde-fous (Phase 0)
Mesure pure — aucune bascule, aucun rejeu, aucun fichier produit modifié. golden intact (non touché).
**NE PAS MERGER.** J'attends ton arbitrage sur Phase 1 (que rattraper) et Phase 2 (la garantie).
