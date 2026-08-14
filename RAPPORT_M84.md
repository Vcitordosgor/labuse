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
**NE PAS MERGER.**

---

# PHASE 1 — Rejeu SITADEL (arbitrage Vic : SITADEL seul ; DVF/Sudocuh/CatNat/DPE laissés)

Séquence M81 appliquée : rejouer → mesurer le NET → mesurer le delta de classement AVANT toute
bascule → golden. Commande : `labuse ingest-permits --refresh` (delta, recouvrement 3 mois, idempotent).

## Le chiffre exact (Vic : « tu annonces 300-400, je veux le chiffre exact »)

| Mesure | AVANT | APRÈS | Net |
|---|---|---|---|
| Total `sitadel_permits` | 50 292 | 50 292 | **0** |
| max(`date`) autorisation | 2026-06-30 | 2026-06-30 | inchangé |
| Permis déposés après 30/06 | — | — | **0** |
| Lignes récupérées / upserts | — | 691 / 662 | 662 = **corrections** aux permis mars→juin (recouvrement) |

**Le chiffre exact des permis rattrapables = 0.** Le rejeu a interrogé SDES/Sitadel3 : **l'amont ne
publie RIEN après le 30/06**. Les ~300-400 permis « manquants » estimés en Phase 0 **n'existent pas
encore chez SDES** — ils supposaient à tort que SDES avait des dépôts juillet/août qu'on n'aurait pas
ingérés. La latence de 45 j est la **cadence de publication de Sitadel3** (~1,5-2 mois de délai
administratif), exactement comme DVF est semestriel. Notre base était **déjà à jour avec la source**.

Les 662 upserts sont des corrections idempotentes sur mars→juin (dates/statuts affinés en amont), pas
de nouveaux permis : le max(date) n'a pas bougé.

## Delta de classement (M81 — mesuré AVANT bascule)

0 permis nouveau → **0 nouveau signal** (offre engagée, PC caducs, mutation). Le run servi `q_v9_m81`
est gelé et n'est pas recalculé (doctrine). **Golden : 119/119 PASS, 0 FAIL, 0 incohérence base↔API.**
Delta de classement = **nul**. Aucune bascule, aucun rejeu de run nécessaire. Golden diff = **0**.

## Ce que Phase 1 corrige de Phase 0

La séquence M81 a fait son travail : **mesurer a renversé l'hypothèse**. SITADEL n'est PAS en retard
de notre fait — son delta de 45 j est **< son seuil de 60 j (2×cadence mensuelle)**, donc DANS la
tolérance. Il rejoint DVF dans la catégorie « faux positif de retard » : la cadence amont est lente,
pas notre ingestion. **Le coût client actionnable du retard = 0.** Le bloc « cette semaine » (M83)
disait donc la vérité : 0 permis récent parce qu'il n'en existe aucun, nulle part.

Le vrai défaut, lui, reste entier et c'est le sujet de Phase 2 : **on ne pouvait pas SAVOIR** qu'on
était (ou non) en retard — pas d'alerte, pas de cron, journal partiel. On a ASSUMÉ un retard. La
garantie doit rendre l'état visible, pas rejouer à l'aveugle.

## Garde-fous (Phase 1)
Rejeu idempotent (delta, recouvrement 3 mois). Aucune table de run touchée. golden 119/119 PASS.
**NE PAS MERGER.**

---

# PHASE 2 — La garantie (le vrai sujet : un décrochage ne peut plus passer en silence)

## Correction d'une erreur de Phase 0 (assumée)

Phase 0 déclarait `check_fraicheur` « concept documenté jamais construit ». **C'était faux** : la
fonction EXISTE — dans `bascule_gardes.check_fraicheur` (garde de rebuild, testée, seuil 2× cadence,
non-bornables jamais alarmés). J'avais lu les commentaires de `fraicheur.py` sans trouver la fonction
dans `bascule_gardes.py`. Le VRAI défaut n'était donc pas « la fonction manque » mais : **elle imprime
dans un log au moment du rebuild et n'est JAMAIS remontée** à une surface vivante (healthz / page
Sources) ; + `ingestion_runs` partiel ; + le cron d'ingestion jamais déployé. La garantie porte là.

## 1 — check_fraicheur rendu VISIBLE, sur un seuil unique (le plus important)

- **Seuil unique** : `fraicheur.CADENCE_JOURS` + `seuil_jours()` deviennent la source de vérité du
  barème (2× la cadence normée). `bascule_gardes.check_fraicheur` l'importe désormais (fin de la table
  dupliquée qui pouvait diverger). Deux surfaces (garde de rebuild + statut live), un seul seuil.
- **Statut live** : `etat_sources()` porte maintenant `seuil_jours` + `statut` ∈ {`en_retard`,
  `a_jour`, `cadence_libre`, `sans_donnee`}, **dérivé du MÊME delta que la date affichée** (cohérence
  M73 : millésime amont et date d'ingestion restent deux colonnes distinctes).
- **Trois surfaces vivantes** : page Sources (chip ROUGE « ⚠ en retard », `data-source-decroche`) ·
  `/healthz/crons` (champ `retards`) · CLI `labuse check-fraicheur` (**code de sortie 1** si décrochage
  — la sentinelle que le cron appelle).
- **Anti-faux-positif prouvé (mesuré)** : DVF 226 j < 364 j → `a_jour` ; SITADEL 45 j < 60 j →
  `a_jour` ; Sudocuh 591 j, ortho 590 j, BODACC, CatNat, GPU, Géorisques → `cadence_libre` (jamais une
  alerte, quel que soit l'âge). Le piège qu'on a évité sur DVF ne revient pas dans le mécanisme.
- **Le seul retard live** : **DPE, 24 j > seuil 14 j** (hebdomadaire). C'est un VRAI retard (amont
  ADEME, comme tu l'as toi-même qualifié) — **surfacé, jamais masqué**. Je n'ai PAS retouché sa
  cadence pour éteindre l'alarme (ce serait masquer). Décision ouverte pour toi : soit on l'accepte
  comme signal honnête, soit la cadence effective ADEME (établissement→publication ~3 sem.) justifie
  un desserrage du seuil DPE — **à toi**, pas un geste silencieux de ma part.

## 2 — Le cron d'ingestion : il EXISTAIT, il n'était pas DÉPLOYÉ

Découverte : `deploy/cron.d/{sitadel,bodacc,dpe,dvf,ban,radar}` **existent** (bien datés). Le défaut
n'était pas leur absence mais que **`docs/DEPLOYMENT_OVH_VPS.md` n'installait QUE maintenance+backup**,
jamais ces crons-là. C'est le « Train J+1 » jamais posé. Ajouté à la doc : une section **« Les crons
d'ingestion — le Train J+1 (OBLIGATOIRE) »** avec la procédure d'installation (`install … /etc/cron.d`),
la création de `/var/log/labuse`, la **sentinelle** (`check-fraicheur` en cron, code 1 = mail), un
**tableau quoi/fréquence/coût machine** (quotidien cumulé ~10 min, pic hebdo ~30 min), et la
vérification (`curl /healthz/crons`). **Le déploiement VPS sort de mon périmètre — la procédure est
écrite pour que tu l'exécutes.**

## 3 — ingestion_runs complété + statut « décroche » sur la page Sources

- **`trace_ingestion`** (nouveau, `fraicheur.py`) : contexte `running → ok | error` qui journalise
  TOUTE ingestion dans `ingestion_runs` ET pose `last_sync_at` au succès. Branché sur **bodacc, dpe,
  georisques** (qui n'y laissaient AUCUNE trace). Un échec est désormais ÉCRIT (`status='error'`) puis
  remonté — **jamais avalé**.
- **`_source_pour_run`** (app.py) : les nouveaux libellés de trace sont câblés explicitement — sinon
  le `else` cadastre se serait approprié leur date d'ingestion (faux positif évité).
- **Chip « en retard »** sur la page Sources (livré au point 1).

## L'exigence de fond : un échec doit le DIRE

Une ingestion qui échoue est maintenant visible sur **quatre** surfaces : `ingestion_runs.status='error'`
· la liveness `crons` de `/healthz/crons` (dernier passage OK trop vieux) · le champ `retards` · le code
de sortie 1 de `labuse check-fraicheur`. **Décision de conception assumée** : `retards` (fraîcheur
donnée) est SÉPARÉ du bit `ok` (santé process/cron). Un job mort dégrade `ok` (liveness) ; un retard
amont chronique (DPE) alimente `retards` + la sentinelle dédiée, sans faire sonner en boucle la sonde
uptime — la fatigue d'alerte, c'est le silence inversé. C'est le même motif que le golden qui prenait
un quota dépassé pour une régression : distinguer la panne du bruit.

## 2d — Le bloc « cette semaine »

Phase 1 a montré que **0 permis récent est la vérité** (SDES n'a rien après le 30/06). Le bloc M83
dit donc déjà juste (il affiche la dernière donnée + un drapeau de fraîcheur, jamais un « 0 » nu).
**Aucune retouche** : fabriquer une fenêtre « vraie » sur une donnée qui n'existe pas serait masquer.

## Garde-fous (Phase 2)
tsc 0 · vitest 36/36 · build vert · pytest 113 passed (0 régression ; `test_pdf_premium` = échec de
collection PRÉ-EXISTANT, fichier non touché) · **golden 119/119 PASS, diff 0** · exports md/html/
onepager/pdf → 200 · `/sources` + `/healthz/crons` → 200 · page Sources : **0 erreur console**, chip
décroche rendu (DPE). Aucune table de run touchée. Aucune bascule. **NE PAS MERGER.**
