# SOUS LE CAPOT — SIMPLIFICATION-AUDIT-1

*12 novembre 2026 — lecture seule, prod `ssh labuse-vps` en lecture. Chiffres = traces réelles des 30 derniers jours (`job_runs`, `ops_incidents`, `ia_log`, tailles `pg_class`). Chaque tableau se termine par « proposition » : garder / ralentir / fusionner / supprimer + risque.*

But : trouver où l'on dépense de l'énergie pour rien. La synthèse chiffrée est dans `SIMPLIFICATIONS.md`.

> **T1 (inventaire des sources de la vitrine)** : voir section en bas — construite à partir du code (`sources_catalog.py`, `autonomie.py`, `controle_millesime.py`, `fraicheur.py`).

---

## T2 — Les tâches automatiques (jobs)

Rythme actuel + passages/échecs sur 30 j + durée moyenne/max (prod `job_runs`). « Lu par » = qui consomme le résultat.

| Job | Fait quoi (1 phrase) | Rythme | 30 j (n / échecs) | Durée moy / max | Écrit | Lu par | Proposition (risque) |
|---|---|---|---|---|---|---|---|
| **calcul-nuit** | recalcule le classement (candidat) | quot 02:00 | 9 / **4** | **67 min / 239 min** | runs q_v21→q_v24, mail | Vic (promotion) | **Ralentir** : ne calcule déjà que si entrée change (abstention <1 min la plupart des nuits) ; plafonner à **1×/semaine** max + réparer (T3). Risque faible (la promotion reste manuelle). |
| backup-postgres | dump PostgreSQL + rotation | quot 13:30 | 32 / 5 | 17 min / 20 min | dumps | pull Mac, restore-test | **Garder** (ne jamais ralentir). |
| coherence-robinets | fuites entre robinets + eau ancienne | quot 07:25 | 29 / 0 | 16 min / 18 min | état cohérence | Tableau de bord | **Ralentir** à 2-3×/sem. Risque faible (fuites rares). |
| fiche-commune-cache | précalcul contexte 24 communes | quot 03:00 | **54** / 0 | 13 min / 22 min | cache communes | fiche commune | **Ralentir** à 1×/jour (54 passages = ~2/j) ou après injection. Risque faible. |
| coherence-banc | banc de cohérence (tous lecteurs, île) | quot 03:45 | 35 / **9** | 12 min / 23 min | `coherence_runs` | Tableau de bord | **Ralentir** à 2-3×/sem (a attrapé peu — T6). Risque : détection régression plus lente. |
| ingest-bodacc | procédures collectives J+2 | quot 06:40 | 29 / 0 | 7 min / 10 min | bodacc | outil Successions/Radar | **Garder** (léger, quotidien justifié). |
| verite-permanente | rejoue harnais NU-5 (régression) | quot 06:00 | 10 / **6** | 4 min / 13 min | résultats | Vic/CI | **Ralentir** à hebdo (6 échecs = flakes connus). Risque faible. |
| sonde-sources | détecte nouvelles versions amont | quot 07:00 | 29 / 0 | 2,6 min / 7 min | `source_veille` | fraîcheur, injection | **Garder** (surveillance). |
| filtres-sources | contrôles qualité versions servies | quot 07:05 | 29 / 0 | 50 s / 56 s | état | Tableau de bord | **Garder** (léger). |
| estimer-banc-precision | rétro-test Estimer | quot 04:30 | 1 / 0 | 17 s | banc | Vic | **Ralentir** à hebdo. Risque faible. |
| john-veille | veille IA (réglementaire/sources/concurrence) | quot 03:00 | 7 / 0 | 15 s | `john_veille` | onglet John | **Ralentir** à 2-3×/sem (coût + peu lu — T7). |
| resume-matin | **un mail/jour** état exploitation | quot 07:30 | 8 / 0 | 10 s | mail | **Vic** | **Garder** (c'est le bon canal — y replier les incidents, T8). |
| sante-endpoints | sonde endpoints métier | /30 min | 1382 / 4 | 8,5 s / 302 s | métriques | surveillance | **Garder** (ne pas ralentir). |
| detect-events | bascules marché (diff run) | quot 07:04 | 29 / 0 | 6 s | événements | veille clients | **Garder**. |
| copilote-purge | purge conversations | quot 03:30 | 28 / 0 | 6 s | — | — | **Garder** (trivial). |
| ingest-dvf | recharge DVF (livraison Etalab) | hebdo mar 05:00 | 4 / 0 | 5 s / 11 s | dvf | classement, écrans | **Garder** rythme ; **réparer** (n'avance pas, EXP-004). |
| fraicheur-nuit | rejoue fraîcheur 99 sources | quot 07:50 | 1 / 0 | 3 s | `fraicheur_controle_nuit` | Tableau/incidents | **Garder** (surveillance). |
| healthcheck | /health + disque | /15 min | 2763 / 0 | 2,8 s / 120 s | état | alertes | **Garder** (ne pas ralentir). |
| abuse-scan | usage anormal / partage compte | quot 10:00 | 28 / 0 | 2 s | — | sécurité | **Garder**. |
| **recap-matin** | (ancien résumé matin) | — | 15 / 0 | 2 s | — | **personne** (remplacé par resume-matin) | **Supprimer** du registre (mort depuis 27/10). Risque nul. |
| purge-sessions | sessions expirées | quot 08:00 | 29 / 0 | 1,5 s | — | — | **Garder**. |
| mail-queue-consommer | envoie mails dus | /5 min | **8256** / 17 | 0,8 s / 300 s | mails | clients/Vic | **Ralentir** à /15 min (≈0 mail client, T8). Risque : mail transactionnel plus lent. |
| injection-nuit | injection classe A auto | quot 01:00 | 10 / 0 | 0,8 s | tables A | classement | **Garder** (léger). |
| evaluer-suivis | alertes parcelles suivies | quot 07:02 | 29 / 0 | 0,6 s | — | clients | **Garder**. |
| radar-cycle / -dvf | cycle de vie Radar / rapprochement DVF | quot 04:00 / 04:30 | 13 / 0 | 0,3 s | radar | Radar | **Garder** (triviaux). |
| pg-maintenance | VACUUM ANALYZE | hebdo dim 04:00 | 4 / 0 | 1 s | — | base | **Garder**. |
| ingest-sirene / -dpe | concurrents / DPE | mensuel | 1 / 2 | ~5 min | tables | écrans | **Garder** (mensuel). |
| ingest-sitadel / -inpi-rne | permis / dirigeants | mensuel | **0** / — | — | tables | Successions/veille | **Garder le rythme, RÉPARER** (jamais exécutés, EXP-005). |
| sync-gpu | diff PLU 24 communes | mensuel 15 | 1 / 0 | 0,2 s | événements PLU | bandeau PLU | **Garder**. |
| verite-sources | 20 parcelles vs sources en ligne | mensuel 15 | 1 / 0 | 4 min | rapport | Vic | **Garder** (mensuel, utile). |
| signal-instantane / radar-cycle-mensuel | instantané Signal / cible Courrier | mensuel 1 | 1 / 0 | ~5 s | snapshot | Signal/Courrier | **Garder**. |
| restore-test | test de restauration | mensuel 5 | 1 / 0 | 0,2 s* | `.restore-test.json` | Vic | **Garder** (ne jamais supprimer). |
| agents-sources | veille IA des sources | dim /2 sem | 3 / 1 | 4 min / 11 min | événements | Vic | **Évaluer** : vérifier que la sortie est lue (sinon supprimer). |
| **purge-runs** | purge vieux runs | hebdo dim 04:30 — **GELÉ** | 0 | — | — | disque | **Dégeler** (c'est l'inverse d'une dépense : ça libère le disque, EXP-013). |
| radar-cloche / digest | notifications clients — **GELÉS** | — | 0 | — | — | clients | Décision produit (D8 audit précédent). |

\* restore-test 0,2 s = **confirmé** : le job serveur ne restaure RIEN, il lit seulement la table des matières du dump (`pg_restore --list`). La vraie restauration est mensuelle sur le Mac. Voir **Compléments C2** en bas.

**Doublons repérés** : `recap-matin` ↔ `resume-matin` (le premier est mort). `coherence-banc` (nuit, île) ↔ `coherence-robinets` ↔ `filtres-sources` ↔ `verite-permanente` : quatre contrôles de cohérence/qualité quotidiens qui se recoupent partiellement (T6). `healthcheck` (/15 min) ↔ `sante-endpoints` (/30 min) : deux sondes de santé (une locale, une métier) — complémentaires, pas doublon.

---

## T3 — Le calcul du classement et les runs

**Ce qui entre dans le classement** (détail des sources en T1) : essentiellement des sources **classe B qui changent rarement** — PLU/zonage (diff mensuel `sync-gpu`), cadastre (socle, construit sur Mac), risques/PPR, DVF (hebdo, mais figé), SITADEL (mensuel). Les livraisons quotidiennes (BODACC) nourrissent surtout Radar/Successions, **pas** le cœur du classement.

**Durée d'un calcul complet** : `calcul-nuit` **≈ 179 min (3 h)** quand il tourne vraiment (prod `job_runs` 04/11 et 05/11 = 178,9 min). Les autres nuits : **abstention en <1 min** (rien de structurant n'a changé → il ne recalcule pas — c'est déjà le bon réflexe) ou **échec** (q_v23 plante en 1-4 min depuis le 10/11).

**Taille d'un candidat sur le disque** : la table `dryrun_cascade_results` (21 Go, 106 M lignes) contient **5 runs complets** (q_v18_sources, q_v19_sources, q_v21, q_v22, q_v23 ≈ 21 M lignes chacun) + q_v24 en cours (715 k). → **un candidat complet ≈ 21 M lignes ≈ ~4 Go** rien que dans cette table, + sa part de `parcel_p_score_v2` (5,3 Go au total), `score_labuse` (7,5 Go), `parcel_scenario_v2_runs` (1,1 Go). **Ordre de grandeur : ~4 à 6 Go par candidat.**

**Candidats créés par mois aujourd'hui** : q_v21 (06/11), q_v22 (08/11), q_v23 (10/11), q_v24 (en cours 12/11) → **~1 tous les 2 jours** (≈ 15/mois au rythme actuel), **dont aucun n'est purgé** (`purge-runs` gelé). Served reste q_v20 : **ces candidats ne servent à rien tant qu'ils ne sont pas promus.**

**Proposition chiffrée.**
| Levier | Aujourd'hui | Proposé | Gain |
|---|---|---|---|
| Fréquence du calcul complet | jusqu'à ~15 candidats/mois (quot si entrée change) | **1×/mois max** (ou seulement si une source classe-B du classement change — liste en T1) | ~3 h × 14 nuits économisées/mois ≈ **~40 h de calcul/mois** ; ~**50-80 Go/mois** de croissance évitée |
| Nombre de candidats gardés | 5+ runs complets accumulés (21 Go) | **1 candidat à la fois** ; l'ancien supprimé quand le nouveau est promu (dégeler `purge-runs` + rétention servi+précédent) | **~16 Go** récupérables tout de suite |
| Table obsolète `cascade_results` | 1,4 Go morts (plus lue que par `gabarit/builder.py:413`) | supprimer après correction EXP-007 | **1,4 Go** |

Risque : **faible**. Le classement ne change réellement que quand une donnée structurante change (rare) ; promotion déjà manuelle. Seul risque = un retard d'intégration d'une nouvelle version PLU → mitigé en déclenchant le calcul **à l'injection** d'une source du classement, pas sur une horloge.

---

## T4 — Les sauvegardes

| Élément | Rythme | Taille | Durée | Lieu | Conservation | Proposition (risque) |
|---|---|---|---|---|---|---|
| Dump quotidien « lean » | quot 13:30 | ~6,3 Go | ~17 min | `/var/backups/labuse` (VPS) | 2 quotidiens | **Garder** (jamais ralentir). Réparer la garde anti-rétrécissement (EXP-003). |
| Dump hebdo (hardlink) | dim | 6,2 Go (0 octet copié) | — | idem | 1 | **Garder**. |
| Rapatriement Mac | quot (launchd) | 6 Go | var. | `~/labuse-backups/vps` | ~2 | **Garder** ; débloquer le volume (<15 Go, EXP-003). |
| Copie disque externe | dim + au montage | 6 Go | var. | TOSHIBA EXT | — | **Garder**. |
| Test de restauration | mensuel 5 | — | — | base à part | marqueur | **Garder** ; vérifier qu'il restaure vraiment (durée 0,2 s suspecte). |

**Tables EXCLUES du dump allégé** (schéma gardé, données rebâties) et coût de reconstruction :
| Table exclue | Taille | Reconstruite par | Temps de reconstruction |
|---|---|---|---|
| `dryrun_cascade_results` | 21 Go (106 M l.) | le scoring (cascade) d'un run | **~3 h** (= un calcul complet) |
| `p_model_ext_dataset` | 1,5 Go | build features/ML | dizaines de min |
| `cascade_results` | 1,4 Go | **obsolète — à NE PAS reconstruire** (EXP-007) | — (supprimer) |
| `p_model_candidates` | 862 Mo | build ML | dizaines de min |
| `p_model_dataset` | 781 Mo | build ML | dizaines de min |
| `score_snapshot_parcelles` | 476 Mo | le scoring | inclus dans le calcul |
| `p_model_dataset_v2` | ~0 | — | — |

**Proposition** : garder l'exclusion (elle évite ~25 Go de dump), mais **retirer `cascade_results` de la liste et la supprimer** (morte). Risque nul. **Ne rien ralentir** sur les sauvegardes elles-mêmes.

---

## T5 — Ce qui demande ton accord

| Action (touche clients / données servies) | Aujourd'hui | Qui peut la déclencher | Proposition (risque) |
|---|---|---|---|
| **Promouvoir un run** (bascule) | **ton accord** (manuel) | page Circuit, `golden promote`, John Taylor (**confirmation**) | **Garder** manuel. Risque si relâché : classement faux servi. |
| **Injecter une source classe B** (PLU, DVF, SITADEL…) | **ton clic** | bouton Injecter, John Taylor | **Garder**. |
| Injecter une source classe A | **auto la nuit** (contrôles + retour arrière) | `injection-nuit`, John Taylor | **Garder auto** (faible risque, réversible). |
| Déployer le code | **manuel** (`deploy.sh`) | Mac (toi) | **Garder** ; ajouter le garde-fou « SHA ancêtre de main » (EXP-001). |
| Accepter un incident / un écart | manuel | bouton, John Taylor | **Garder**. |
| Retirer une source | **confirmation** | John Taylor | **Garder**. |
| Relancer un job / lancer une sauvegarde / diagnostiquer | sans confirmation | bouton, John Taylor | **Garder** (lecture/relance sûres). |

**Proposition globale** : l'équilibre est bon. Rien à relâcher sur ce qui change le classement ou les données servies. Seul resserrement utile : le **garde-fou de déploiement** (refuser un SHA hors `main`).

---

## T6 — Les contrôles et les alertes

Ce qu'ils ont RÉELLEMENT attrapé en 30 j (prod `ops_incidents` par préfixe, et bancs) :

| Contrôle | Rythme | Durée | Vrais problèmes attrapés / bruit (30 j) | Doublon | Proposition (risque) |
|---|---|---|---|---|---|
| `healthcheck` | /15 min | 3 s | disque (6), readyz (3), sauvegarde (3) = **vrais** | — | **Garder**. |
| `coherence-banc` | quot | 12 min | `chasse` (2) | recoupe robinets/filtres | **Ralentir à 2-3×/sem**. Risque : détection + lente. |
| `coherence-robinets` | quot | 16 min | ~0 | recoupe banc | **Ralentir à 2-3×/sem**. |
| `filtres-sources` | quot | 50 s | ~0 | recoupe banc | **Garder** (léger) ou fusionner dans le banc. |
| `verite-permanente` | quot | 4 min | 0 (6 échecs = flakes) | — | **Ralentir à hebdo**. |
| `verite-sources` | mensuel | 4 min | 1 (faux positif oracle, cf. audits) | — | **Garder**. |
| `fraicheur-nuit` | quot | 3 s | `fraicheur-retard` (2 : DVF, SITADEL) = **vrais** | — | **Garder**. |
| `sante-endpoints` | /30 min | 8 s | job-bloqué (2) | — | **Garder**. |
| Escalade incidents >3 j | quot | — | 12 escalades (surtout disque/calcul-nuit) | — | **Garder** mais dédupliquer (T8). |

**Constat** : les **bancs lourds quotidiens (coherence-banc, coherence-robinets, verite-permanente) ont attrapé ~2 vrais écarts en 30 j** pour ~**14 h de calcul cumulées/mois**. Les vrais problèmes viennent de `healthcheck`/`fraicheur-nuit`/`sante-endpoints` (légers). → **gros gisement de ralentissement sans perte réelle de surveillance.** Risque : une régression de cohérence serait vue en 2-3 jours au lieu d'1.

---

## T7 — L'IA et ses coûts

30 j (prod `ia_log`) :

| Usage | Rythme | Coût 30 j | Produit | Réellement utilisé ? | Proposition (risque) |
|---|---|---|---|---|---|
| **john-chat** | à la demande (41 appels) | **8,52 €** | réponses admin | oui (toi) | **Garder**. |
| john-resume (matin) | quot | 0,68 € | mail du matin | oui | **Garder**. |
| john-veille | quot 03:00 | 0,44 € | items onglet John | **à vérifier** (peu consulté ?) | **Ralentir à 2-3×/sem**. Risque faible. |
| agent_source | dim /2 sem | 0,39 € | événements sources | **à vérifier** | **Évaluer** ; supprimer si non lu. |
| john-enquete | à la demande | 0,31 € | cause + mandat | oui | **Garder**. |
| john-lecture | à la demande | 0,23 € | chat lecture | oui | **Garder**. |
| copilote-* (clients) | à la demande | ~0,11 € | réponses copilote | oui | **Garder**. |
| **Total** | | **≈ 10,2 €/mois** | | | Plafond 50 € — **très loin**. |

**Proposition** : l'IA ne coûte quasi rien (10 €/mois). Le seul gisement = ralentir `john-veille` et vérifier que `agents-sources` sert à quelque chose. **Ne pas sur-optimiser** : le gain € est négligeable, le gain est surtout en bruit (T8).

---

## T8 — Les mails que tu reçois

30 j (prod) :

| Type de mail | Rythme | Nombre 30 j | Proposition (risque) |
|---|---|---|---|
| **Incidents ops** (job-retard, job-echec, escalade, disque…) | à chaque incident (dédup/jour) | **108** | **Fusionner** dans le résumé du matin (sauf `[URGENT]` réel). Risque : une urgence noyée → garder l'envoi immédiat pour URGENT seulement. |
| dont `job-retard` | — | 43 (bruit du déploiement 10/11 + mensuels) | **Réduire** : seuil de retard plus tolérant, pas de mail pour un retard court. |
| dont `escalade` | — | 12 | **Dédupliquer** (une escalade = 1 mail, pas 1/jour). |
| Résumé du matin | quot 07:30 | 8 (job récent) | **Garder** (le bon canal unique). |
| Digest clients / cloche | **gelés** | 0 | décision produit. |
| Courrier (envois) | — | **0** | — (fonction inutilisée récemment). |
| Licence/essai clients | — | 1 | **Garder**. |

**Constat** : ta boîte reçoit **~116 mails d'exploitation/mois, ~0 mail client**, et **l'essentiel est du bruit d'incidents** (retards/escalades). → **le résumé du matin existe déjà** (OPS-NUIT-1) ; il suffit d'y **replier les incidents non urgents** au lieu de les mailer un par un.

---

## T1 — Les données de la vitrine

Source : lecture du code (`autonomie.py:44-94` classe A/B ; `circuit_garanties.py:259-314` sources du score ; `ingestion/fraicheur.py:36-137` cadences ; `controle_millesime.py:80-96` sondes ; `config/cascade_v2.yaml` couches A/B/C/D). **Versions servies en prod** : seules DVF/SITADEL/INPI ont été relevées en base cette fois (voir ETAT) ; le recensement millésime complet des ~99 sources est dans l'audit FRAICHEUR-1 (non rejoué ici pour rester léger). « Contrôle » = notre sonde (quotidienne pour toutes via `sonde-sources`).

### A — Sources qui ENTRENT dans le classement (une injection peut déclencher un recalcul)

| Source | Sert à | Rythme producteur | Servi prod | Injection | Déclenche | Proposition (risque) |
|---|---|---|---|---|---|---|
| **Cadastre (PCI)** | socle parcelles, surface, exclusion eau | stable (rare) | — (socle Mac→prod) | **classe B / Mac** | recalcul complet | **Garder** ; recalcul seulement à son changement (rare). |
| **PLU / GPU (zonage)** | exclusions dures A/N, ER, EBC | diff mensuel (`sync-gpu` le 15) | — | **classe B / clic** | recalcul complet | **Garder** ; **recalcul déclenché par le diff PLU**, pas par une horloge nocturne. Risque faible. |
| **PPR / aléas (DEAL)** | exclusion dure PPR rouge | rare | — | **classe B / clic** | recalcul complet | **Garder** ; recalcul à l'injection. |
| **DVF** | prix (rot_nu, med_pm2…) | semestriel (avr/oct) | **31/12/2025** (figé, EXP-004) | auto A nuit | recalcul | **Garder rythme** ; recalc semestriel suffit ; **réparer** la donnée figée. |
| **SITADEL** (permis) | permis_24m, Signal | mensuel | **31/08** (job KO) | auto A nuit | recalcul léger | **Garder** ; réparer (EXP-005). |
| **RGE ALTI** (pente) | pente_moy, exclusion >100 % | pluriannuel (~3-4 ans) | — | classe B | recalcul | **Garder** ; change tous les 3-4 ans → jamais urgent. |
| **BD TOPO** (bâti) | densité bâti, nu constructible | pluriannuel | — | classe B | recalcul | **Garder** ; rare. |
| **OCS GE / CoSIA** (occupation IA) | dormance droits, sous-densité | pluriannuel | — | détection + **à la main** | recalcul | **Garder** ; rare. |
| **BD ORTHO / IRC** | piscine, PV, canopée/NDVI | pluriannuel | — | A (IRC) / manuel (ortho) | recalcul | **Garder** ; rare. |
| **Filosofi / BPE / RP IRIS / QPV (INSEE/ANCT)** | revenus, équipements, population | annuel | — | auto A | recalcul | **Garder** ; annuel. |
| 50 pas géométriques (DEAL) | bande littorale (SDP) | stable | — | auto A | recalcul partiel (géom) | **Garder** ; rare. |
| Parc National / Forêts publiques (ONF/INPN) | exclusions dures | stable | — | auto A | recalcul | **Garder** ; rare. |

### B — Sources LUES DIRECTEMENT (aucune injection ne déclenche de recalcul — visibles le lendemain)

| Groupe de sources | Sert à | Rythme producteur | Injection | Proposition (risque) |
|---|---|---|---|---|
| **BODACC** (procédures collectives) | Radar, Successions, Signal | quotidien | auto A nuit | **Garder** quotidien (léger) ; **ne déclenche PAS de recalcul** → ne doit jamais tirer le classement. |
| Couches « info » cascade C : SUP, ZNIEFF, ABF/MH, Cartofriches, bruit route, GéoMCE, EnR-toiture | surcouches réglementaires fiche | périodique (rare) | auto A | **Garder** ; rythme bas, lues directement. |
| Référentiels : Population légale, IRIS contours, BAN, BD NYME, Annuaire admin, Recherche entreprises | géocodage, contexte, concurrents | annuel à continu | auto A | **Garder** ; aucun recalcul. |
| SIRENE / SIRENE étab. | concurrents géolocalisés | continu (mensuel chez nous) | auto A (mensuel) | **Garder**. |
| INPI RNE (dirigeants) | outil Successions | mensuel | **à la main** (job KO) | **Réparer** (EXP-005) ; lu directement, pas de recalcul. |
| Transport GTFS, MOBPRO, Trafic RN, GéoLittoral, CatNat, DGFiP foncier public, Fichiers fonciers | contexte fiche / Signal | périodique à continu | auto A / B | **Garder** ; aucun recalcul. |
| ~19 sources internes (DOUBLON / DORMANT / RETIRÉ) | — | — | jamais | déjà cachées de la vitrine — **rien à faire**. |

**Les SEULES sources dont un changement justifie vraiment un recalcul du classement** : **Cadastre, PLU/GPU, PPR** (classe B, changent rarement) + les classe-A du score (DVF semestriel, SITADEL mensuel, INSEE annuel, IGN pluriannuel). → **aucune ne change assez souvent pour justifier un recalcul chaque nuit.** C'est le cœur de la proposition T3.

---

## Compléments (13/11) — deux points tranchés sur la ligne de code

### C1 — Classe A/B : qui s'injecte seul, qui attend ton clic (la vérité du code)

**La contradiction entre mes deux audits venait d'une confusion : « classe » (doctrine A/B) ≠ « mode d'injection réel ».**
La **classe** (`src/labuse/autonomie.py:60-104`, dict `SOURCES_CLASSE`) décide seulement si la source est balayée par le job générique `injection-nuit`. Mais **plusieurs sources de classe B ont leur PROPRE job cron dédié** (`ingest-dvf`, `ingest-sitadel`…) qui les recharge automatiquement — **sans attendre ton clic**. C'est ce que T1 avait vu (« auto ») mais mal étiqueté « classe A ».

**Tranché par le code** : `DVF`, `SITADEL`, `DPE` sont **classe B** (`autonomie.py:73,74,75` : « marché… servi au client », « permis — nourrit le scoring », « DPE — features du bâti »). → **ETAT.md avait raison sur la classe, T1 avait tort.** Mais en pratique elles s'injectent seules **par leur cron dédié**, pas par `injection-nuit` (qui ne prend que la classe A : `jobs.py:803-810`, `jobs_impl.py:1653,1699`).

Liste exacte, une ligne par source, par **mode d'injection réel** (classe entre parenthèses ; « classement » = entre-t-elle dans le scoring/cascade) :

**① Injectées seules la nuit par `injection-nuit`** (classe A, contrôles + retour arrière ; seulement si « sûre », sinon listée « à décider ») :
| Source | Classe | Classement ? |
|---|---|---|
| Contours IRIS (IGN/INSEE) | A | non (contexte) |
| INSEE RP Logement 2023 | A | non |
| Population légale (INSEE) | A | non |
| Annuaire administration (DILA) | A | non |
| Ramsar / sites classés (DEAL Carmen) | A | non (info) |
| Transport GTFS (7 réseaux) | A | non |
| **Filosofi (carreaux 200 m)** | A | **OUI** (features revenus) |
| MOBPRO (mobilités) | A | non |
| **BPE INSEE** | A | **OUI** (accès équipements) |
| SIRENE / SIRENE étab. / Recherche entreprises | A | non (concurrents) |
| SUP — assiettes GPU | A | non (info) |
| Zones / contraintes EnR | A | non |
| **Parc National / Forêts publiques (ONF)** | A | **OUI** (exclusion dure, mais source stable) |
| ZNIEFF / INPN patrinat / GéoMCE | A | non (info) |
| **QPV 2024 (ANCT)** | A | **OUI** (feature) |
| ABF / Monuments hist. / bruit ITT / Cartofriches | A | non (surcouches info) |
| BD NYME lieux-dits / CatNat GASPAR / Trafic RN / GéoLittoral | A | non |
| Base Adresse Nationale | A | non (géocodage) |
| 50 pas géométriques (limite haute) | A | partiel (géométrie SDP) |

**② Classe B mais injectées seules par un CRON DÉDIÉ** (automatiques, **pas** d'attente de clic) :
| Source | Classe | Cron | Classement ? |
|---|---|---|---|
| **DVF** | B | `ingest-dvf` hebdo (mar) → `refresh-dvf` | **OUI** (marché) |
| **SITADEL** | B | `ingest-sitadel` mensuel → `ingest-permits --refresh` | **OUI** (permis) |
| **DPE ADEME** | B | `ingest-dpe` mensuel | **OUI** (features bâti) |
| BODACC | B (défaut) | `ingest-bodacc` quotidien | non (Radar/Successions/Signal) |
| INPI RNE (dirigeants) | B (défaut) | `ingest-inpi-rne` mensuel | non (outil Successions) |

**③ Classe B, DÉTECTION seule — attend ton geste** :
| Source | Classe | Cron | Classement ? |
|---|---|---|---|
| **PLU / GPU (urbanisme)** | B | `sync-gpu` mensuel = **diff/veille seulement**, n'injecte PAS le zonage (`jobs_impl.sync_gpu`) | **OUI** (zonage opposable) |

**④ Classe B, chargées à la MAIN / socle Mac→prod** (aucun cron auto) :
| Source | Classe | Classement ? |
|---|---|---|
| Cadastre PCI / Cadastre Etalab | B | **OUI** (assiette, socle) |
| PPR / aléas (DEAL) | B | **OUI** (exclusion rouge) |
| GPU — assainissement | B | OUI (cascade ANC) |
| RGE ALTI (altimétrie) | B | **OUI** (pente) |
| BD TOPO IGN / RNB | B | **OUI** (emprise/densité) |
| OCS GE / IGN BD CARTO V5 | B | OUI / contexte |
| CoSIA / BD ORTHO (+IRC) | B (défaut) | OUI (piscine, canopée, dormance) |
| DGFiP personnes morales / Fichiers fonciers | B | non (foncier public / propriété) |

**⑤ Jamais chargées (en pratique)** — le mécanisme existe mais 0 exécution réelle (EXP-005) :
| Source | Classe | État |
|---|---|---|
| SITADEL | B | cron jamais abouti → figé **31/08** |
| INPI RNE | B | cron jamais abouti → figé **05/07** |

**À retenir** : rien de ce qui **entre dans le classement** ne s'injecte « tout seul sans trace de décision » de façon dangereuse — Cadastre/PLU/PPR (le cœur) sont classe B à ta main ; DVF/SITADEL/DPE entrent dans le classement et sont **auto** (cron dédié), mais la **promotion** du run reste ton geste, donc une mauvaise version ne part pas chez le client sans toi.

### C2 — restore-test : lit-il vraiment la base, et depuis quand une vraie restauration ?

**Il y a DEUX restore-test, et seul celui du Mac restaure vraiment.**

- **Serveur (`restore-test`, le 5 du mois, 0,2 s)** : ne restaure RIEN. Il fait seulement `pg_restore --list` (lit la **table des matières** du dump, compte les objets — 1814 le 05/11, vérifie ≥ 50 et la taille). `src/labuse/jobs_impl.py:2031-2069` : *« sur le VPS, on ne restaure PLUS un dump complet : il n'y a pas la place… vérifie seulement que le dump est RESTAURABLE sans le restaurer »*. D'où les 0,2 s. Une vraie restauration côté serveur n'a lieu que si `LABUSE_RESTORE_TEST_REEL=1` **et** disque libre ≥ 4× le dump (≈ 25 Go) — **impossible aujourd'hui** (7,8 Go libres). Le marqueur dit honnêtement lequel des deux a tourné (« lisibilité OK » = TOC seulement).
- **Mac (`deploy/mac/restore_test.sh`, mensuel, launchd)** : LE vrai test. Rapatrie le dump → **crée une base jetable `labuse_restore_test` → `pg_restore` COMPLET → compte les tables clés (parcels, data_sources, score_labuse, veilles, comptes) et les compare à la prod + compte le run servi → DROP**. Garde-fou : refuse si < 20 Go libres.

**Dernière vraie restauration complète prouvée** (marqueur Mac `~/labuse-backups/.restore-test.json`) : **28/10/2026** — dump du 27/10, statut ok, `parcels` restauré 434 582 = prod 434 582, run servi q_v20 (433 229 lignes). **→ ~16 jours sans vraie restauration vérifiée (28/10 → 13/11).**

Pourquoi pas depuis ? Le journal `~/.labuse/restore_test.log` montre que le dernier essai journalisé (27/10) a été **REFUSÉ faute de place** (« 12 Go libres < 20 Go requis — reporté »), et aucun essai réussi n'est enregistré depuis le 28/10. **Même cause racine que le blocage du rapatriement (EXP-003) : le manque de place gèle la preuve de restauration.** Nuance : même le vrai test restaure la base et l'interroge (comptages) — il ne **démarre pas l'application** (uvicorn) dessus ; « la base démarre et répond aux requêtes » est prouvé, « l'app démarre sur une base restaurée » ne l'est pas.
