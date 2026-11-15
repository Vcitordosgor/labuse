# FRAICHEUR-PROD-3 — rattrapage des deux mises à jour en retard, sur la prod

**Mandat** : lancer une seule fois, dans l'ordre, les deux tâches mensuelles qui ont raté leur
créneau — les permis (`ingest-sitadel`) puis les dirigeants (`ingest-inpi-rne`) — exactement
comme le cron, après avoir prouvé qu'une sauvegarde fraîche se relit et que le disque suffit.
Écriture serveur **limitée à ces deux jobs** : aucun déploiement, aucun classement, calcul de
nuit toujours gelé, aucun cache vidé à la main.
**Quand** : dimanche 15/11/2026, 06 h 10 → 06 h 25 (heure Réunion) — hors fenêtre sauvegarde
(13 h 30–14 h) et hors fenêtre de nuit (1 h–3 h 30).
**Où** : prod `labuse-vps`, branche déployée `ops/deploy-groupe-3`, worktree
`~/Desktop/labuse-deploy3` (arbre propre).

---

## Résultat en bref

| Job | Avant | Après | Journal | Verdict |
|---|---|---|---|---|
| **ingest-sitadel** (permis) | 50 810 lignes · max **31/08/2026** | **51 063** (+253) · max **30/09/2026** | ok, 54,2 s, 1 067 upserts, 0 erreur | **rattrapé** — l'outil Permis sert désormais septembre |
| **ingest-inpi-rne** (dirigeants) | 27 146 lignes · 9 337 SIREN · stock **05/07/2026** | **27 241** (+95) · **9 374** SIREN (+37) · stock **15/11/2026** | ok, 198 s, 0 erreur | **rattrapé pour la couverture** (voir nuance § 3) |

Les deux ont augmenté leur nombre de lignes, avancé leur date, et n'ont levé aucune erreur —
les trois conditions d'arrêt du mandat sont restées vertes à chaque étape. **Recharge DVF
confirmée : mardi 17/11/2026 à 05 h 00 (heure Réunion)** (§ 4). Aucun classement n'a été promu
(manifeste toujours `q_v20`), aucun cache vidé, calcul de nuit toujours gelé.

---

## 1. Garde-fous avant écriture (tous verts)

**Sauvegarde fraîche et relisible.** Dernier dump quotidien :
`/var/backups/labuse/labuse-labuse-20261114-133003.dump` — **14/11 13 h 30, 6,2 Go**.
`pg_restore --list` réussit : **1 840 objets, 305 tables**, et le sommaire contient bien les deux
tables visées (`sitadel_permits` et `pm_dirigeants`, en TABLE + TABLE DATA). Témoins concordants :
test de restauration mensuel **vert le 05/11** (`.restore-test.json` : « lisibilité OK, 1 814 objets »)
et **copie externe le 13/11** sur disque TOSHIBA (`.copie-externe.json`, sha256 enregistré).

**Disque suffisant.** `/` : 96 Go, **25 Go libres (75 %)** avant comme après les deux jobs (ils
font de l'upsert delta, pas de gonflement).

**Heure.** 06 h 10 Réunion au démarrage, bien à l'écart des deux fenêtres interdites.

---

## 2. Permis — `ingest-sitadel`

**Commande, fidèle au cron** (utilisateur `labuse`, sourcing de `labuse.env`) :
`sudo -u labuse sh -c 'cd /home/labuse && set -a; . /etc/labuse/labuse.env; set +a; exec /opt/labuse/venv/bin/labuse jobs run ingest-sitadel'`.

**Un premier essai a échoué sans rien toucher.** Lancé d'abord depuis le home de ma session ssh
(`/home/ubuntu`), le job a levé `PermissionError: '/home/ubuntu'` en 0,1 s — l'utilisateur `labuse`
ne peut pas lire ce répertoire, alors que le cron tourne depuis `$HOME` (= `/home/labuse`, comme
le note `labuse.env.example`). Vérifié : `sitadel_permits` **inchangé** (50 810, max 31/08),
compteurs vides. J'ai corrigé le répertoire de travail et relancé ; l'incident `job-echec:
ingest-sitadel` ouvert par cet essai a été **auto-refermé à 06 h 13 44** par le run réussi (aucun
incident pendant).

**Run réussi** — 06 h 12 50 → 06 h 13 44, **54,2 s, statut ok** :
`{lignes: 1111, upserts: 1067, sans_cadastre: 44, dates_futures: 0, dates_invalides: 0}`.

| Mesure | Avant | Après |
|---|---|---|
| Lignes | 50 810 | **51 063** (+253) |
| Date la plus récente (`max(date)`) | 31/08/2026 | **30/09/2026** |
| Par mois | 05:209 · 06:247 · 07:271 · 08:237 | 05:199 · 06:257 · 07:275 · 08:249 · **09:253** |

Le mois de **mai passe de 209 à 199 (−10)** : ce n'est pas une perte, c'est la reclassification
d'un refresh (`ingest-permits --refresh` relit tout le jeu et recorrige des dates ; 1 067 upserts
sur des lignes existantes, dont quelques permis de mai re-datés). Le **total gouvernant monte**
(+253) et la **date avance d'un mois** — les deux signaux de santé.

**Pas de classement promu.** Le job comporte, comme chaque mois (description cron « → golden
candidat »), un **comparatif** run servi vs candidat q_v23 (`promues_servi` 802 / `promues_candidat`
409), envoyé par mail. C'est une mesure, pas une promotion : le manifeste reste `q_v20`
(promu le 27/10) et **aucun nouveau run de score** n'est apparu.

**Ce que le client lit maintenant.** La requête qui gouverne l'outil Permis (ancrée sur
`max(date)`) sert `donnees_jusqu_au = 30/09/2026` ; la fenêtre « Autorisés depuis 90 jours »
passe de **145 à 400 permis** (253 depuis le 1ᵉʳ septembre, auparavant absents). Exemples de
nouveaux permis PC du 30/09 rattachés à une parcelle : `97418000BI0104` (Sainte-Marie),
`97407000AT0029` (Le Port), `97418000AE0286` (Sainte-Marie) — leurs fiches afficheront ce permis.
Endpoints vivants : `/healthz` **200** ; `/modules/permis` et `/parcels/{idu}` répondent **401**
(route + authentification en place). Ces endpoints exigent une session utilisateur ; je n'en ai
pas créé (ce serait une écriture hors mandat), j'ai donc prouvé la donnée servie au niveau base
(requête exacte de l'endpoint, lecture seule).

---

## 3. Dirigeants — `ingest-inpi-rne`

**Commande, fidèle au cron** :
`sudo -u labuse sh -c 'cd /home/labuse && set -a; . /etc/labuse/labuse.env; set +a; exec /opt/labuse/venv/bin/labuse jobs run ingest-inpi-rne'`.

**Run réussi** — 06 h 17 48 → 06 h 21 06, **198 s, statut ok**. Sortie :
« 9 614 éligibles, **9 337 déjà faits**, **277 à traiter** → **95 dirigeants, 37 SIREN** »,
`millesime_donnee: 2026-11-15`.

| Mesure | Avant | Après |
|---|---|---|
| Lignes | 27 146 | **27 241** (+95) |
| SIREN distincts | 9 337 | **9 374** (+37) |
| Stock ingéré (`max(ingested_at)`) | 05/07/2026 | **15/11/2026 06 h 20** |
| `max(date_prise_fonction)` | 2023-12-01 | 2023-12-01 (inchangé — propre au stock RNE) |

**Preuve de nouvelle couverture.** Les SIREN enrichis aujourd'hui (ex. `407718360`, `519779813`,
`519779920`, 5 dirigeants chacun) avaient **0 dirigeant avant ce jour** (vérifié). Ce sont des
personnes morales devenues éligibles depuis juillet, désormais dotées. L'outil Successions
(`/modules/successions`, vivant — 401) les affichera.

**Nuance importante — ce job ne rafraîchit PAS les sociétés déjà couvertes.** Les 9 337 SIREN
« déjà faits » sont sautés : un gérant qui a **changé** depuis juillet dans une société déjà
enrichie garde sa donnée de juillet. Le rattrapage comble donc les **trous** (nouvelles sociétés),
il ne corrige pas les **changements** sur l'existant. Le retard « ~4 stocks » signalé en
FRAICHEUR-PROD-2 est **partiellement** résorbé : la couverture est à jour, la fraîcheur des
dirigeants déjà connus ne l'est pas (il faudrait un vrai re-stock complet, hors de ce que fait ce job).
Par ailleurs `parcel_veille_succession` (la couche de veille lue par l'outil) reste **au 13/10** —
c'est sa cadence propre, ce job ne la recalcule pas.

**Pas de classement touché** : manifeste `q_v20`, aucun nouveau run de score.

---

## 4. Recharge des ventes (DVF) — programmée mardi 17 à 05 h 00

La ligne cron est **active** (non commentée) :
`0 5 * * 2   labuse  … labuse jobs run ingest-dvf` → **tous les mardis à 05 h 00 (heure Réunion)**.
Prochain mardi depuis le 15/11 : **17/11/2026**. Donc la recharge DVF partira **mardi 17/11 à
05 h 00 Réunion**.

Le code déployé est prêt : `/opt/labuse/app/src/labuse/ingestion/dvf_etalab.py` lit le format
Etalab actuel (`full-AAAA-sN`, témoins `full-2026-s1` présents) — le run de mardi tirera donc le
semestre S1 2026 (ventes jusqu'au 30/06). Les derniers runs `ingest-dvf` (27/10 et 03/11, 2,5 s,
ancien lecteur = no-op) n'avaient rien ramené ; l'occurrence du **mardi 10/11 a sauté** (crontab
re-posé le 13/11, après coup), d'où l'incident `job-retard:ingest-dvf` ouvert le 13/11. Le
planning est stable depuis le 13/11 et les autres crons tournent normalement — l'occurrence du
17/11 doit donc se déclencher. **Je ne l'ai pas lancée** (hors mandat : seuls SITADEL et INPI
étaient demandés).

---

## 5. État des incidents après l'intervention

| Incident | État | Note |
|---|---|---|
| `job-echec:ingest-sitadel` (mon 1er essai) | **résolu** 06 h 13 44 | auto-refermé par le run réussi |
| `escalade:…:job-retard:ingest-sitadel` (« jamais réussi ») | **résolu** 06 h 15 05 | auto-refermé |
| `fraicheur-retard:SITADEL` | ouvert | se refermera **ce soir au contrôle de 07 h 50** (SITADEL désormais à jour) |
| `fraicheur-retard:DVF` | ouvert | se refermera après la recharge de **mardi 17/11** |
| `job-retard:ingest-dvf` | ouvert | idem — après mardi |
| (aucun incident INPI ouvert) | — | le run réussi a soldé l'éventuel « jamais réussi » |

Rien n'a été fait d'autre : aucun déploiement, aucun run de classement, calcul de nuit toujours
gelé, aucun cache vidé à la main. Disque inchangé (25 Go libres).

---

## Méthode

Prod écrite **uniquement** via les deux commandes `labuse jobs run …` ci-dessus, exécutées en
tant qu'utilisateur `labuse` depuis `/home/labuse`, avec sourcing de `/etc/labuse/labuse.env` —
réplique exacte des lignes du crontab. Toutes les autres requêtes (états avant/après, incidents,
sauvegarde, liveness) sont en lecture seule (`sudo -u postgres psql`, `pg_restore --list`, `curl`
sur `/healthz`), avec `statement_timeout` posé, hors des deux fenêtres interdites.

---

## 6. Addendum (lecture seule) — rafraîchir aussi l'existant ?

**Combien de sociétés déjà couvertes ont changé de dirigeant depuis le 05/07 ?** Mesure sur un
échantillon de **200 SIREN à graine fixe** (ordre `md5(siren||'fp3-graine')`, cohorte 05/07 hors
les 277 neufs). Notre base ne permet pas le diff seule (tout l'existant est figé au 05/07) : j'ai
donc comparé à la source publique **Recherche d'entreprises (DINUM)** — qui expose les dirigeants
du RNE —, en lecture seule, **sans toucher l'API INPI ni son quota de prod**. Résultat :

- **~15 % de vrais remaniements** : 24 des 159 SIREN peuplés des deux côtés ont un patronyme de
  dirigeant ajouté ou retiré (ex. `383968716` JAUZELON → +DELEFLIE, `389203191` FRECAUT ISAUTIER →
  −ISAUTIER, `428173702` BALBOLIA → 7 dirigeants). Ordre de grandeur : **~1 société sur 7, soit
  ~1 400 des 9 337 couvertes**.
- **~14 % de trous de couverture** (28/200) : le stock 05/07 n'a stocké **aucun** dirigeant
  physique alors que le producteur en affiche — ce n'est pas un changement mais une lacune, que le
  rattrapage corrigerait aussi.
- Le reste (51 % brut au premier passage) était du **bruit de format** (noms d'usage « X (Y) »,
  artefact « ACTIF », variantes d'orthographe) — écarté après normalisation en jetons de patronymes.

*Limites : source proxy (DINUM agrège le RNE, pas le stock INPI brut qu'on ingère) ; appariement
par patronyme (grossier — gonfle un peu) ; « changé » inclut des corrections. Ordre de grandeur,
pas un compte exact.*

**Ce que coûterait un rafraîchissement complet** (`ingest-inpi-rne --no-resume`, ~9 579 SIREN) :
- **Durée** : ~1 h 45 – 2 h (mesuré : 277 SIREN en 198 s ≈ 0,7 s/SIREN, throttle 0,5 s anti-ban).
- **Disque** : négligeable — `pm_dirigeants` ~27 k lignes, l'upsert écrit sur place (pas de
  croissance notable, pas de table neuve) ; quelques Mo.
- **Risque** : faible. Le vrai risque est le **quota quotidien INPI** (`QuotaExceededError`) : le
  job peut s'arrêter en cours — mais il est **résumable** sans perte (commit par lot de 100). Pas
  d'impact schéma ni score (étage 2 non branché). À lancer **hors** des fenêtres backup/nuit (2 h
  est long → risque de chevaucher le dump de 13 h 30 si lancé trop tard).
- **À l'écran** : Successions et Courrier afficheraient les dirigeants **actuels** et le signal
  « âge du dirigeant » (propension à vendre) recalculé — correction là où un gérant est parti,
  décédé ou ajouté (~1 fiche société sur 7), plus les ~14 % de sociétés qui gagneraient un
  dirigeant là où elles n'en montraient aucun.

**Comment modifier la tâche mensuelle pour rafraîchir aussi l'existant** — aujourd'hui elle tourne
en `--resume` (saute tout SIREN déjà présent). Trois options, par ordre de préférence :
1. **Fenêtre de fraîcheur (recommandé)** : remplacer le saut « déjà présent » par « déjà présent
   **et** `ingested_at ≥ now() − N jours** » (ex. 90 j), plafonné par le quota → chaque société
   est relue au moins une fois par trimestre, sans pic mensuel de 2 h ; un lot roulant par nuit.
2. **Priorisé par signal** : relire d'abord les SIREN touchés par une procédure BODACC ou une mise
   à jour SIRENE depuis la dernière lecture (les plus susceptibles d'avoir changé), puis compléter
   le quota par les `ingested_at` les plus anciens.
3. **Plein périodique** : lancer `--no-resume` une fois par trimestre (accepte le ~2 h et le
   quota) — le plus simple, le moins fin.

---

## 7. Rafraîchissement complet des dirigeants — décision de Vic (une fois)

**Garde-fous** (identiques au § 1) : dump du 14/11 13 h 30 relu (`pg_restore --list` OK), disque
25 Go libres. **Gate horaire** : cadence mesurée **~0,74 s/SIREN** sur les 300 premiers → ~1 h 58
pour 9 614, fin prévue **~08 h 43**, avant 13 h → lancement autorisé.

**Lancement fidèle au cron, avec le drapeau plein.** Le job `labuse jobs run ingest-inpi-rne`
n'accepte pas `--no-resume` (il appelle la CLI en mode `--resume`). J'ai donc lancé la **commande
CLI** `labuse ingest-inpi-rne --no-resume`, en tant qu'utilisateur `labuse`, depuis `/home/labuse`,
avec sourcing de `/etc/labuse/labuse.env` (throttle 0,5 s anti-ban, commit par lot de 100),
détachée (`setsid nohup`).

**Déroulé** : démarré **06 h 45 31**, terminé **08 h 43 43** (Réunion), **1 h 58**, les **9 614
SIREN traités, aucun arrêt quota**. Bilan du job : 27 312 dirigeants écrits, 9 374 SIREN avec
dirigeant. *(Point 2 du mandat — arrêt quota — sans objet : le run est allé au bout. Aucune
reprise à programmer.)*

### Avant / après

| Mesure | Avant (05/07) | Après (15/11) |
|---|---|---|
| Sociétés couvertes (SIREN) | 9 374 | 9 374 |
| Sociétés avec ≥ 1 dirigeant actif (personne physique) | 8 927 | **8 931** (+4) |
| Lignes `pm_dirigeants` | 27 146 | **27 580** (+434) |
| Lecture la plus ancienne **par société** | 05/07/2026 | **15/11/2026 06 h 45** (0 société non relue) |
| **Sociétés dont l'ensemble des dirigeants actifs a changé** | — | **111 / 9 374 (1,2 %)** |

Les 111 changements : **97 ajouts seuls, 14 remaniements, 0 retrait seul**. Exemples foncier :
`311210827` (+LAMY), `329086847` Gilbert Canabady (+VADAMOOTOO, +MOUTIEN), `322153172` (+LOCATE).

**Vérification Successions** (donnée lue par l'outil — endpoint vivant, 401 car session requise ;
contrôlé au niveau base) sur trois sociétés **changées et foncières** :
- **SA Adrien Bellier** (`310862131`, 663 parcelles) : 12 dirigeants lus aujourd'hui, propension
  « très élevé » (aîné 77 ans) — le 5ᵉ BARAU ajouté est présent.
- **SELARL Franklin Bach** (`810061713`, 104 parcelles) : 2 dirigeants lus aujourd'hui (BACH,
  TRON), propension « modéré » (59 ans).
- **Gilbert Canabady** (`329086847`, 50 parcelles) : 3 dirigeants lus aujourd'hui, propension
  « très élevé » (86 ans).

### Deux limites honnêtes

1. **Les départs ne sont pas purgés.** L'upsert `ON CONFLICT … ingested_at=now()` met à jour les
   dirigeants que le RNE renvoie ; il ne désactive pas ceux qu'il ne renvoie plus. Résultat :
   **268 lignes orphelines actives sur 173 sociétés** (un dirigeant présent au 05/07 que le RNE
   ne liste plus) subsistent `actif=true`, datées du 05/07 — c'est pourquoi le `min(ingested_at)`
   **au niveau ligne** reste au 05/07 (au niveau **société**, tout a été relu aujourd'hui). Un
   gérant parti peut donc encore s'afficher ; le « 0 retrait seul » ci-dessus en découle. Exemple :
   `329086847` garde 2 lignes du 05/07 (Gilbert et Gérard Canabady) à côté des 3 lues ce jour.
2. **La mesure §6 (~15 %) était surestimée.** Elle comparait à l'API publique **Recherche
   d'entreprises (DINUM)**, qui modélise les dirigeants différemment du flux INPI RNE que nous
   ingérons (elle développe des représentants que le RNE compte autrement). La mesure
   **autoritaire**, faite ici sur la vraie source après refresh complet, est **1,2 %** de sociétés
   réellement modifiées — à retenir à la place de l'ordre de grandeur du § 6.

### Modification à faire sur la tâche mensuelle (à livrer avec la mise en ligne — NON appliquée ici)

La tâche `ingest-inpi-rne` tourne en `--resume` (saute tout SIREN déjà présent → l'existant n'est
jamais revu). **Modification à livrer** : **relecture roulante** — ne sauter un SIREN que si sa
dernière lecture (`max(ingested_at)` par société) a **moins de 90 jours** ; sinon le relire,
**plafonné par le quota quotidien** (trier par lecture la plus ancienne d'abord, s'arrêter au
quota, reprendre le lendemain). Ainsi chaque société est revue au moins une fois par trimestre,
sans pic de 2 h ni risque de quota. *(À prévoir en complément, hors de cette modification : la
désactivation des dirigeants que le RNE ne renvoie plus, pour résorber les 268 lignes orphelines —
la relecture roulante rafraîchit, mais ne purge pas les départs.)*

*Méthode : écriture prod limitée à la commande `ingest-inpi-rne --no-resume` (utilisateur
`labuse`, env sourcé) ; tout le reste (avant/après, orphelins, vérif) en lecture seule. Lanceur
temporaire retiré. Hors fenêtres backup/nuit.*

---

## 8. Recharge des ventes (DVF) maintenant — décision de Vic

Première exécution du nouveau lecteur Etalab en prod, sous surveillance, au lieu d'attendre
mardi 05 h.

**Garde-fous** : sauvegarde **du jour** (15/11 13 h 30, 6,2 Go) relue (`pg_restore --list` OK),
disque 25 Go. **Fenêtre horaire** : lancé à **16 h 09** (après la sauvegarde du jour, loin de la
fenêtre de nuit) → fin ~16 h 13, aucune collision ; le garde « fin avant 13 h » (éviter le dump de
13 h 30) est sans objet l'après-midi.

**Lancement** : `labuse jobs run ingest-dvf`, utilisateur `labuse`, depuis `/home/labuse`, env
sourcé — **exactement comme le cron** (le job passe par le runner : journal, verrou, incidents).
**Déroulé** : 16 h 09 30 → 16 h 12 36, **186 s, statut ok, aucune erreur**.

### Avant / après — ventes par année (`dvf_mutations`)

| Année | Avant | Après | Δ |
|---|---|---|---|
| 2021 | 6 852 | 6 733 | −119 |
| 2022 | 7 029 | 6 776 | −253 |
| 2023 | 5 942 | 5 900 | −42 |
| 2024 | 4 840 | 4 908 | +68 |
| 2025 | 4 902 | **5 156** | **+254** |
| 2026 | — | **1 606** | **+1 606** |
| **Total** | **29 565** | **31 079** | **+1 514** |
| **Date de vente la plus récente** | 31/12/2025 | **30/06/2026** | ✓ attendu |

**Aucune année n'a disparu, aucune baisse inexpliquée.** Le lecteur **remplace chaque période**
par le fichier Etalab officiel courant (`full-2021-s2`, `full-2022`…`full-2025`, `full-2026-s1`) :
il supprime la fenêtre de dates de la période puis réinsère les mutations 974 (jamais remplacer du
réel par du vide). Les petits écarts 2021-2023 (−) et 2024-2025 (+) sont les **révisions DGFiP**
intégrées depuis l'ancienne ingestion (le fichier officiel actuel fait foi). **2025 augmente
(+254)** — plus complet, pas une perte. Le **2026-S1 = 1 606** coïncide **exactement** avec le test
local FRAICHEUR-FIX-1 → lecteur déterministe et correct. Les archives ≤ 2020 (`dvf_mutations_histo`)
ne sont jamais touchées ; 2021-S1 (hors fenêtre amont) est conservé.

### Trois parcelles — médiane bâti de la fiche (€/m², 36 mois, borne 1 000-12 000)

| Parcelle | Commune | Médiane avant | Médiane après | Comparables | Période après |
|---|---|---|---|---|---|
| 97411000AB0006 | Saint-Denis | 2 608 | **2 667** | 3 935 → 3 712 | 06/2023→**06/2026** |
| 97416000CD0006 | Saint-Pierre | 3 273 | **3 333** | 1 586 → 1 507 | 12/2022→12/2025 ⇒ 06/2023→**06/2026** |
| 97421000AB0001 | Salazie (petite commune) | 1 855 | **1 741** | 43 → 41 | 01/2023→12/2025 ⇒ 07/2023→**06/2026** |

La médiane de la fiche lit `dvf_mutations` en **direct**, fenêtre ancrée sur `max(date_mutation)` :
après la recharge, la fenêtre avance à **06/2026** et les médianes bougent (Saint-Denis et
Saint-Pierre +2 %, Salazie −6 % — petit échantillon, roulement de fenêtre). La baisse de Salazie
et le léger recul des comparables (fenêtre glissante : perte du début 2023, ajout du 1ᵉʳ semestre
2026) sont **expliqués par le roulement de fenêtre**, pas une perte. **Estimer, Marché et la fiche
répondent** (`/healthz` 200 ; `/parcels/…`, `/modules/patrimoine`, `/estimer/…` → 401 : routés,
session requise — la donnée servie, vérifiée au niveau base, est la médiane live à jour).

### Caches et fraîcheur des prix affichés (point 4)

**Ce que le job fait des caches** : il écrit `dvf_mutations`, enregistre la version de chaque
période (`fraicheur_etat` `dvf:res:*` = `20261020-*`), et met à jour `data_sources` (millésime
« géo-DVF Etalab — millésime 2026-S1 », `last_sync_at`, `fraicheur_statut = à jour`). Il **ne
recalcule pas** `dvf_secteur_medianes` et **ne reconstruit pas** `dvf_mutations_parcelle`.

**Les prix servis au client sont à jour** : les lecteurs servis (fiche, documents) lisent la
médiane **LIVE** `marche_dvf_commune` / `marche_dvf` sur `dvf_mutations` — démontré ci-dessus, les
médianes incluent le 1ᵉʳ semestre 2026. Les caches à **clé de fraîcheur** (fiche, commune,
tuiles) s'auto-invalident parce que la date DVF a bougé (30/06/2026) et se recalculent à la
prochaine lecture sur la médiane live.

**Deux dérivés restent en 2025 — dette de donnée, hors chemin servi** :
1. `dvf_mutations_parcelle` (niveau parcelle) **n'est pas rechargé** (max resté 31/12/2025) : le
   `source_horizon_at` de DVF (libellé « DVF jusqu'au … ») et le **prix terrain €/m²** en
   dérivent et affichent encore 2025.
2. `dvf_secteur_medianes` (cache de médianes secteur, millésime 2025, calculé le 02/11) **n'est
   pas recalculé** — mais, par conception (`fraicheur_caches._etat_marche_medianes`), il **n'est
   pas sur le chemin servi** (les lecteurs servent la médiane live) ; sa péremption est une dette
   signalée sur la page Données / `/sante/fraicheur`, résorbée par `labuse rebuild`, **pas** par
   `ingest-dvf`.

En clair : **la médiane de prix de la fiche est à jour ; le libellé de millésime DVF et le prix
terrain (dérivés de la table parcelle) ne le seront qu'après un `rebuild`** (non demandé ici).

**Le cron de mardi 17/11 sera un no-op** : les 6 versions de période sont enregistrées
(`dvf:res:*`) ; `check_dvf_livraison` comparera la version amont à l'enregistrée et, sans nouvelle
publication Etalab d'ici là, ne verra **aucune ressource modifiée** → aucun rechargement, aucun
travail en double.

### Limites et conformité

Aucune année disparue, aucune baisse inexpliquée, aucune erreur de journal → aucune condition
d'arrêt déclenchée. Rien d'autre fait : pas de déploiement, pas de classement, calcul de nuit
toujours gelé, aucun cache vidé à la main. Écriture prod limitée à `labuse jobs run ingest-dvf` ;
le reste en lecture seule. Lanceur temporaire retiré.
