# CHASSE-ORFEVRE-1 · Angle D — LE TEMPS (fuseaux, « aujourd'hui », jobs, mails, exports)

Audit LECTURE SEULE du 18/10/2026, worktree `~/Desktop/labuse-orfevre` (= main).
Machine d'audit : Mac en **Europe/Paris (CEST, UTC+2)** ; base Postgres locale (DSN `.env`).
Script rejouable : `docs/audit-2026-10/chasse-orfevre-1/scripts/angle_d_temps.py` (sorties citées ci-dessous).

## 0. Verdict global

**COHÉRENT dans l'architecture, avec 3 écarts gênants (dont 2 conditionnels au fuseau du serveur) et
une poignée de cosmétiques.** Le système du temps de LABUSE repose sur trois garde-fous explicites,
tous VÉRIFIÉS en place :

1. **Côté SQL** — fuseau de session PostgreSQL forcé à `Indian/Reunion` par le moteur applicatif
   (`src/labuse/db.py:90-92`, `connect_args … -c timezone=Indian/Reunion`) → tout `now()` /
   `CURRENT_DATE` / `ts::date` du SQL métier est en heure Réunion, quel que soit le serveur.
2. **Côté Python** — `src/labuse/tz.py` (`now_reunion()` / `today_reunion()`, `REUNION_TZ`) pour
   toute fenêtre MÉTIER (quotas, gels, portes) ; 30 points de consommation hors tz.py.
3. **Côté base** — **100 % des colonnes temporelles sont `timestamptz`** (281 colonnes ; **0**
   `timestamp without time zone` ; 62 `date`) → tout horodatage stocké est un INSTANT, pas une
   heure murale ambiguë.

Le piège documenté d'un audit passé (« `computed_at` stocké en Réunion+04 alors que le shell était
CEST+02 ») est **résolu structurellement** : la colonne étant `timestamptz`, le « +04 » n'est que la
REPRÉSENTATION (session Réunion) d'un instant correct — vérifié §2.

## 1. Timezone réelle de la base (prouvée, script §1-2)

```
session TimeZone (app, forcée db.py) : Indian/Reunion
serveur TimeZone (reset_val)         : Indian/Reunion   (boot=GMT, source session=client)
now() servi      : 2026-10-18 17:52:38+04:00
now() AT TZ UTC  : 2026-10-18 13:52:38
Python now(UTC)  : 2026-10-18 13:52:38+00:00   (dérive −0,006 s)
CURRENT_DATE     : 2026-10-18 (= date Réunion)
```

- La session de l'app est Réunion (db.py), ET le défaut du cluster (`reset_val`) est AUSSI
  Indian/Reunion → même un `psql` ad hoc voit l'heure Réunion. (Sur ce poste dev, c'est donc une
  config délibérée du cluster — `postgresql.conf` ou `ALTER DATABASE` ; ça protège les scripts qui
  n'utiliseraient pas `labuse.db`.)
- Prod VPS : fuseau système **UTC+4 d'après journalctl** (constat d'un mandat antérieur, non
  revérifiable d'ici). `deploy.sh:52-57` lit `timedatectl` et n'accepte QUE `UTC` ou
  `Indian/Reunion` — voir D-01 pour la branche UTC.

### Échantillons de valeurs réelles (script §4 — toutes plausibles)

| table.colonne | servi (session Réunion) | même instant UTC | lecture |
|---|---|---|---|
| `parcel_residuel.computed_at` | 2026-10-17 09:00:22+04 | 05:00 UTC | = 07:00 CEST au Mac — run du matin, instant correct |
| `job_runs.debut` / `fin` | 2026-10-17 09:36→09:40+04 | 05:36 UTC | durée 4 min cohérente |
| `mail_queue.cree_at` → `prevu_at` | 20:43:57 → 20:48:57+04 | +5 min | différé « immédiat J+5 min » exact |
| `sessions_auth.created_at` → `expire_at` | 02:12 → 14:12+04 | +12 h | durée de session exacte |
| `comptes.essai_expire_at` | 2026-10-18 17:01+04 | 13:01 UTC | posé ~16:55 CEST (audit en cours côté voisin) — instant correct |
| `usage_compteurs.jour`, `api_keys.jour` | 2026-10-18 | (date) | = jour Réunion du moment ✓ |

Aucune colonne ne contient d'heure « murale CEST déguisée » : tous les instants recoupés tombent
sur des événements plausibles (runs du matin, activité de dev l'après-midi CEST = soirée Réunion).

## 2. Inventaire des pratiques (grep exhaustif src/ + frontend/)

Volumes (`grep -c`, hors tests) :

| pratique | n | classement |
|---|---|---|
| `datetime.now(timezone.utc)` (aware-UTC) | 71 | **sain** pour horodater/comparer du `timestamptz` ; voir D-07 quand on en tire une **date** |
| `now_reunion()` / `today_reunion()` / `REUNION_TZ` / `ZoneInfo("Indian/Reunion")` | 30 | aware-Réunion (fenêtres métier, mails) — la bonne pratique maison |
| `date.today()` | 57 | **naïf-local** — correct SI le process tourne en fuseau Réunion (prod VPS) ; J-1 pendant 2 h/nuit sur le Mac dev (voir D-01, D-03, D-13) |
| `datetime.now()` nu | 5 réels | naïf-local : `mail.py:59`, `bascule_gardes.py:222`, `jobs_impl.py:216` (**D-02**), `api/partners.py:399` (**D-05**), `api/app.py:1401` |
| `datetime.utcnow()` | 0 | — (éradiqué) |
| `fromtimestamp(…, tz=utc)` | 3 | aware ✓ (`stripe_lecture.py:47`, `radar.py:61`, `api/dashboard.py:312`) |
| `func.now()` / `server_default=now()` | ~30 modèles + DDL | tous sur `DateTime(timezone=True)` / `timestamptz` ✓ |
| `CURRENT_DATE` / `now()` SQL | ~40 | session Réunion ✓ (db.py) ; DVF ancrée `max(date_mutation)` JAMAIS `CURRENT_DATE` (`dvf_fenetre.py`) ✓ |
| front `new Date(` / `toLocale*` / `Intl` | 191 | fuseau du NAVIGATEUR sauf 9 usages forcés `Indian/Reunion` (admin : `Licences.tsx`, `Produit.tsx`, `Radar.tsx`, `AdminView.tsx`, `Courrier.tsx`, `RadarHub.tsx`) — voir D-09 |

Points remarquables par fichier (sélection commentée ; la liste brute s'obtient par les greps du
script et de ce rapport) :

| fichier:ligne | usage | classement |
|---|---|---|
| `src/labuse/db.py:90-92` | `-c timezone=Indian/Reunion` sur TOUTES les connexions du moteur | fondation ✓ |
| `src/labuse/tz.py` | `REUNION_TZ`, `now_reunion`, `today_reunion` | fondation ✓ |
| `src/labuse/api/protection.py:170-174` | `_aujourdhui()` = `today_reunion()` (compteurs jour) | aware-Réunion ✓ |
| `src/labuse/api/partners.py:468-472` | porte quota partenaires : `today_reunion()` (bug R2 historique corrigé) | aware-Réunion ✓ |
| `src/labuse/quota.py:75-92` | `CURRENT_DATE` (session Réunion) | ✓ |
| `src/labuse/api/events.py:197-229` | `ts::date = now()::date` (dédup/jour) | ✓ session Réunion |
| `src/labuse/api/dashboard.py:1024-1033` | `_fmt_reunion` (« le %d/%m/%Y à %Hh%M (heure Réunion) ») | ✓ |
| `src/labuse/comptes.py:286-704` | essais/verrous/sessions : `datetime.now(timezone.utc)` vs `timestamptz` | aware-UTC ✓ |
| `src/labuse/jobs.py:153-192` | runner : début/fin aware-UTC + `debut_reunion` lisible | ✓ |
| `src/labuse/jobs_impl.py:216` | `datetime.now().weekday() == 6` | **naïf — D-02** |
| `src/labuse/jobs_impl.py:458/488/854/863/898` | clés dédup `_date.today()` | naïf — D-04 |
| `src/labuse/ops_alertes.py:110-119` | « déjà envoyé aujourd'hui » : jour **UTC** (SQL `AT TIME ZONE 'UTC'` + Python UTC, cohérent en interne) | D-04 |
| `src/labuse/api/dossier.py:36` | `date.today().replace(day=1)` (quota MENSUEL dossiers) | **naïf — D-03** |
| `src/labuse/scoring/score_v.py:48` | `_today()` = date **UTC** | D-07 |
| `src/labuse/ingestion/permits_sdes.py:149/170` | rejet « date future » sur date UTC | D-07 |
| `src/labuse/faisabilite/bilan.py:29` | `ANNEE_REF = date.today().year` **à l'import** | D-06 |
| `src/labuse/api/partners.py:399-400` | horodatage page publique `datetime.now()` naïf vs `created_at` session-Réunion | D-05 |
| `src/labuse/stripe_lecture.py:47` | mois de facture = epoch Stripe → `%Y-%m` en UTC | D-08 |
| `src/labuse/exports/builder.py:472-568`, `exports/numeros.py:29`, `bilan/pdf.py:160`, `api/pdf_premium.py:388`, `api/export.py:446`, `api/export_commun.py:182` | « généré le » / n° `AAAAMMJJ` = `date.today()` local | D-13 |
| `src/labuse/exports/builder.py:18-30` | « Données LABUSE au » = `promoted_at` du manifeste servi, PAS la date du jour | ✓ (bonne pratique) |
| `src/labuse/mail.py:59` | nom de fichier `.eml` dry-run : stamp naïf local | cosmétique assumé (nommage) |
| `src/labuse/api/onboarding.py:639-640` | « le %d/%m/%Y à %Hh%M (heure Réunion) » via ZoneInfo | ✓ |
| `src/labuse/comptes.py:744-745` | mail résiliation `DATE_FIN_ACCES` : `astimezone(Indian/Reunion)` | ✓ |
| `src/labuse/api/events.py:1233` | brief copilote `genere_le` : `now(REUNION_TZ)` | ✓ |
| `frontend/src/components/admin/Licences.tsx:19-43` | `fmtReu` + `fmtVisite` : `Intl … timeZone:'Indian/Reunion'` (aujourd'hui/hier en jour Réunion) | ✓ |
| `frontend/src/components/admin/CircuitDiagram.tsx:129`, `admin/Destinations.tsx:12`, `panel/ResultsSection.tsx:101-104`, `copilote/AccueilCopilote.tsx:81` | `toLocaleDateString`/Intl SANS timeZone → navigateur | D-09 |

## 3. Constats

### D-01 — Le code suppose « heure locale = Réunion », mais deploy.sh accepte AUSSI un serveur UTC
**Gravité : gênant (latent — sain sur la prod actuelle).**
- Preuve : `deploy.sh:52-57` accepte deux fuseaux serveur (`UTC` → `gentz=utc` ; `Indian/Reunion` →
  conversion +4). Or 57 × `date.today()` + 5 × `datetime.now()` nu + 2 × `.astimezone()` sans
  argument (`ops_alertes.py:348/355`, `jobs_impl.py:419`) prennent le fuseau DU PROCESS.
- Sur la prod actuelle (VPS en UTC+4 d'après journalctl, et `reset_val` Postgres Indian/Reunion),
  tout est cohérent : « local » == Réunion.
- Scénario d'erreur (si un jour la branche UTC de deploy.sh est empruntée) : tous les
  « aujourd'hui » naïfs basculent à **04:00 Réunion** au lieu de minuit ; `jobs_impl.py:216` décale
  l'intégrale du banc d'un jour (D-02) ; les PDF « généré le » affichent J-1 jusqu'à 04:00 (D-13).
- Correction proposée (non appliquée) : soit retirer la branche `UTC` de deploy.sh (un seul fuseau
  serveur admis = Indian/Reunion, comme la base), soit finir la migration `date.today()` →
  `today_reunion()` sur les sites métier. Un test de registre « aucun `datetime.now()`/`date.today()`
  nu dans src/labuse hors liste blanche » fermerait la classe.

### D-02 — `coherence-banc` : le « dimanche = intégrale » est décidé en fuseau du PROCESS
**Gravité : gênant (conditionnel D-01).** `src/labuse/jobs_impl.py:216` :
```python
_mode = "tout" if datetime.now().weekday() == 6 else "nuit"   # dimanche = l'intégrale hebdo
```
Le job tourne à `45 23 * * *` UTC (`jobs.py`, « 03:45 » Réunion). Sur serveur **Réunion** :
naïf = 03:45 dimanche → `tout` la nuit de samedi à dimanche ✓. Sur serveur **UTC** (branche admise
par deploy.sh) : au même instant le naïf dit 23:45 **samedi** → `weekday()==6` n'est vrai que le
dimanche 23:45 UTC = **lundi** 03:45 Réunion : l'intégrale glisserait d'une nuit, silencieusement.
Correction : `from ..tz import today_reunion ; _mode = "tout" if today_reunion().weekday() == 6 else "nuit"`.

### D-03 — Quota MENSUEL des dossiers : borne du mois en date LOCALE, compteurs au jour RÉUNION
**Gravité : gênant (théorique en prod, réel sur machine CEST).** `src/labuse/api/dossier.py:33-40` :
```python
    Jour de référence = heure LOCALE python (cohérent avec protection._aujourdhui)."""
    premier = date.today().replace(day=1)
```
La docstring est **fausse** : `protection._aujourdhui` (`api/protection.py:170-174`) est
`today_reunion()`, PAS l'heure locale — et c'est bien `_aujourdhui()` qui POSE les compteurs
(`dossier.py:122-127`). Scénario (machine CEST, ex. le Mac dev ou un serveur UTC D-01) : le **1ᵉʳ du
mois entre 00:00 et 02:00 Réunion** (= 22:00-24:00 CEST le 30/31), un dossier est compté sur
`jour = <1ᵉʳ>` (Réunion) mais `premier = 1ᵉʳ du mois PRÉCÉDENT` → la somme reprend tout le mois
écoulé → quota mensuel « atteint » à tort dès la bascule du mois. Sur VPS Réunion : aucun écart.
Correction : `premier = today_reunion().replace(day=1)` (+ corriger la docstring).

### D-04 — Trois définitions du « jour » coexistent pour les clés de dédup d'alertes
**Gravité : cosmétique.**
- `ops_alertes.py:108-122` : rappel quotidien d'incident dédupliqué au **jour UTC** (SQL
  `AT TIME ZONE 'UTC'` + `datetime.now(timezone.utc).date()` — cohérent en interne) ;
- `jobs_impl.py:458, 488, 854, 863, 898` : dédup `sante_endpoints:/coherence_run:/verrous:/…` au
  **jour local** (`_date.today()`) ;
- `protection._aujourdhui` / `quota.py` : **jour Réunion**.
Scénario : autour de 04:00 Réunion (frontière UTC) ou 02:00 Réunion (frontière CEST), un rappel
peut partir deux fois dans la même journée Réunion, ou être retenu un jour de plus. Personne ne
reçoit un mail faux, juste un rythme de rappel décalé. Correction : une seule clé,
`today_reunion().isoformat()`.

### D-05 — Page publique partenaire : « consulté le » en heure du process, « créé le » en heure Réunion
**Gravité : cosmétique.** `src/labuse/api/partners.py:399-400` :
```python
horodatage = datetime.now().strftime("%d/%m/%Y à %H:%M")      # fuseau du PROCESS
cree = link["created_at"].strftime("%d/%m/%Y à %H:%M")        # timestamptz rendu en session = Réunion
```
Les deux lignes voisines de la même page peuvent diverger de 2 h (serveur CEST) — en prod VPS
Réunion elles coïncident. Correction : `now_reunion().strftime(…)` (et au passage libeller le
fuseau comme le fait onboarding : « (heure Réunion) »).

### D-06 — `ANNEE_REF` du bilan figée à l'import du module
**Gravité : à surveiller (théorique).** `src/labuse/faisabilite/bilan.py:29` :
`ANNEE_REF = date.today().year`, consommée lignes 166 (`age = ANNEE_REF - annee_max`) et 247
(fenêtre `PERIODE_SECTEUR_ANS`). Un worker API démarré en décembre et toujours vivant en janvier
calcule âges et fenêtres secteur sur l'année N-1 jusqu'au redémarrage. Même motif :
`faisabilite/defisc.py:39-57` et `api/fiche_blocs3.py:182` recalculent à l'appel (sains) — seul
`bilan.py` fige. Correction : propriété/fonction `annee_ref()`.

### D-07 — « Aujourd'hui » en date UTC : J-1 entre 00:00 et 04:00 Réunion
**Gravité : cosmétique / à surveiller.** Sites : `scoring/score_v.py:48` (`_today()` = as-of du
score V), `ingestion/permits_sdes.py:149/170` (rejet « date future »), `ops_alertes.py:119`,
`jobs_impl.py:750` (`prochain_millesime_at <= date UTC`). Scénario concret permis : un permis daté
du jour Réunion ingéré entre minuit et 04:00 Réunion serait rejeté « date future » — en pratique
Sitadel publie avec des mois de retard et les jobs tournent 04:00-07:30 Réunion (= UTC date déjà
alignée), donc inoffensif aujourd'hui. Correction douce : `today_reunion()` pour toute décision
métier « quel jour sommes-nous ».

### D-08 — Mois de facture Stripe compté en UTC
**Gravité : cosmétique.** `src/labuse/stripe_lecture.py:47` : facture epoch →
`fromtimestamp(ts, tz=utc).strftime("%Y-%m")`. Une facture émise le 1ᵉʳ du mois entre 00:00 et
04:00 Réunion est rangée dans le mois PRÉCÉDENT de l'agrégat affiché. Stripe facture en général en
UTC lui-même — choix défendable, à documenter plutôt qu'à corriger.

### D-09 — Front : fuseau du navigateur par défaut (9 écrans admin forcés Réunion)
**Gravité : cosmétique (clientèle = Réunion).** 191 usages `new Date`/`toLocale*`/`Intl` ; seuls
les écrans admin sensibles (`Licences.tsx:19-26` + `fmtVisite` 36-43 en fr-CA/Indian/Reunion,
`Produit.tsx:20`, `Radar.tsx`, `AdminView.tsx`, `Courrier.tsx`, `RadarHub.tsx`) forcent
`timeZone:'Indian/Reunion'`. Les autres (`CircuitDiagram.tsx:129`, `Destinations.tsx:12`,
`ResultsSection.tsx:101-104`, `AccueilCopilote.tsx:81`, `ProjetsPanel.tsx:55`…) rendent en fuseau
NAVIGATEUR : pour un utilisateur à la Réunion c'est juste ; pour Vic consultant depuis l'Europe,
un événement de 00:00-02:00 Réunion s'affiche la veille. Les dates-SEULES (`YYYY-MM-DD` parsées
par `new Date()` = minuit UTC) ne régressent jamais pour un navigateur à offset positif (Réunion,
Europe) — elles régresseraient d'un jour sur un fuseau négatif (Amériques), hors cible.
L'API sérialise toujours des datetimes AWARE (+04:00 session pg ou +00:00 isoformat) → aucun
parsing ambigu constaté.

### D-10 — Base : 0 colonne naïve, instants corrects (le piège « computed_at » est fermé)
**Gravité : constat positif.** Script §3-4 : 281 `timestamptz`, **0** `timestamp without time
zone`, 62 `date`. Tous les échantillons recoupés (tableau §1) sont des instants exacts. Le piège
documenté (« computed_at en Réunion+04, shell CEST+02 ») ne peut plus produire une valeur fausse :
le +04 affiché est la session, l'instant stocké est vrai (ex. `parcel_residuel.computed_at`
17/10 09:00+04 = 07:00 CEST, l'heure réelle du run côté Mac).

### D-11 — Conversion crontab +4 : deux angles morts LATENTS (aucun job touché aujourd'hui)
**Gravité : à surveiller.** `src/labuse/cli.py:4928-4941` (`_h_reunion`) : (a) ajoute +4 **mod 24
sans décaler `dom`/`dow`** — le docstring l'assume (« sûr : les jobs concernés sont quotidiens ») ;
tout FUTUR job hebdo/mensuel avec heure UTC ≥ 20 h tomberait le mauvais jour (ex. `0 21 * * 0`
UTC = dimanche 21:00 UTC = **lundi** 01:00 Réunion, mais la conversion produirait `0 1 * * 0` =
**dimanche** 01:00 Réunion → 24 h d'avance). (b) ne convertit que `h.isdigit()` : une heure en
liste/plage (`1,13`, `2-6`) resterait en UTC **silencieusement**. Vérifié (script §5) : aucun job
actuel n'est dans ces cas (`agents-sources` 19:00 UTC dim est le plus tardif des datés, et il est
`planifie=False`). Correction : assert dans `_crontab_du_registre` (« heure ≥ 20 interdite si
dom/dow ≠ * ; heure non simple interdite ») — le registre refuse plutôt que convertir faux.

### D-12 — Jobs de nuit : planification propre, registre en UTC, affichage en Réunion
**Gravité : constat positif.** Registre `jobs.py:313-535` : `cron_utc` (UTC) + `heure_reunion`
(affichage) cohérents sur les 20+ jobs (vérifié : chaque `heure_reunion` = heure UTC + 4). Chaîne :
`deploy.sh` lit `timedatectl` → `labuse jobs crontab --tz utc|reunion` → pose `/etc/cron.d/labuse`
→ `--verifier` refuse tout écart. « La nuit à la Réunion » est respectée : ingestions 04:00-06:40,
évaluateurs 07:02-07:15, digest 07:15, récap 07:30 — l'ordre relatif tient dans les DEUX fuseaux
admis. `prochaine()` (`jobs.py:252-266`) calcule en UTC et `liste()` affiche
`astimezone(REUNION_TZ)` (`jobs.py:285`) ✓. `semaine_agents` (parité ISO) est appelée sur la date
UTC (`jobs_impl.py:696`) : à 19:00 UTC dimanche, dates UTC et Réunion sont le même dimanche → même
semaine ISO ✓. Seul écart : D-02.

### D-13 — Exports PDF/CSV : « généré le » et numéros `AAAAMMJJ` en date du PROCESS
**Gravité : cosmétique.** `api/pdf_premium.py:388`, `api/export.py:446`,
`api/export_commun.py:182`, `exports/builder.py:141/176/472/561`, `bilan/pdf.py:169/238`,
`exports/numeros.py:29` (`numero_rapport` → `PREFIXE-AAAAMMJJ-xxxx`). En prod (process en fuseau
Réunion) : juste. Généré depuis une machine CEST entre 22:00 et 24:00 CEST (= 00:00-02:00 Réunion
J+1) : le PDF affiche et NUMÉROTE la veille Réunion. Bon point contrasté : « Données LABUSE au »
ne dépend PAS de l'horloge (ancré `served_manifest.json:promoted_at`, `exports/builder.py:18-30`),
et la fenêtre DVF est ancrée `max(date_mutation)` jamais `CURRENT_DATE` (`dvf_fenetre.py`).
Correction douce : `today_reunion()` comme `jour` par défaut des builders.

### D-14 — Comparaisons naïf/aware : aucune mine trouvée
**Gravité : constat positif.** Toutes les colonnes étant `timestamptz`, psycopg rend des datetimes
AWARE (+04 session) ; tous les comparateurs Python trouvés comparent de l'aware à de l'aware :
`comptes.py:361/445`, `pige/api.py:431/440`, `filtres/__init__.py:201`, `circuit_garanties.py:617/701/720`,
`api/fiche_commune.py:455`, `api/dashboard.py:650`. `api/partners.py:369` se protège même d'un
`expires_at` naïf (`datetime.now(link["expires_at"].tzinfo)`). Le seul TypeError historique
(datetime vs `date` sur `prochain_millesime_at`) est corrigé et commenté (`jobs_impl.py:748-750`).
Les états JSON des jobs stockent des isoformat AWARE (`+00:00`) relus sans ambiguïté.

### D-15 — Mails : toutes les dates affichées aux clients sont en heure Réunion
**Gravité : constat positif.** « Votre essai se termine le … » : `FIN_ESSAI` / `DATE_FIN_ACCES`
= `_fmt_reunion()` (`api/dashboard.py:1064/1082`, helper 1024-1033 « (heure Réunion) ») ; mails
auto résiliation (calque relance_carte) : `comptes.py:744-745` `astimezone(Indian/Reunion)` ;
onboarding : `api/onboarding.py:639-640` idem avec libellé « (heure Réunion) ». Dates relatives
des relances J+3/J+10 : `mail_queue.prevu_at` = instant `timestamptz` (vérifié en base : cree_at
+5 min exactes) → l'heure d'envoi ne dépend d'aucun fuseau. Les sujets de mail ne portent pas de
date. Seule trace naïve : le NOM DE FICHIER des `.eml` dry-run (`mail.py:59`, stamp local) —
diagnostic interne, sans enjeu.

## 4. Pièges notés pour les angles suivants

- Les datetimes lus de la base arrivent en **+04:00** (session) : un `strftime` « naïf » sur une
  valeur DB est DÉJÀ en heure Réunion (c'est ce qui rend `partners.py:400` juste et `:399` louche).
- `reset_val` du cluster = Indian/Reunion : un `psql` à la main donne l'heure Réunion — ne pas en
  conclure que le SERVEUR est à la Réunion (le Mac d'audit est CEST ; `boot_val=GMT`).
- `deploy.sh` admet DEUX fuseaux serveur : toute correction « naïf local » doit être testée dans
  les deux branches, ou la branche UTC supprimée (D-01).
- Le garde-fou §5 du script (jobs hebdo/mensuels à heure UTC ≥ 20 h) est à REJOUER à chaque ajout
  de job : la conversion crontab +4 ne protège pas d'elle-même (D-11).

## 5. Récapitulatif des anomalies

| id | gravité | une ligne |
|---|---|---|
| D-02 | gênant (conditionnel) | `jobs_impl.py:216` : « dimanche = intégrale » du banc décidé en fuseau process — glisse au lundi Réunion sur un serveur UTC (branche admise par deploy.sh) |
| D-03 | gênant (théorique en prod) | `api/dossier.py:36` : borne du quota mensuel en `date.today()` LOCAL vs compteurs posés au jour RÉUNION ; docstring fausse ; blocage à tort possible à la bascule de mois |
| D-01 | gênant (latent) | 57 `date.today()` + 5 `datetime.now()` nus supposent process=Réunion alors que deploy.sh admet un serveur UTC — classe entière à fermer ou branche UTC à retirer |
| D-04 | cosmétique | dédup d'alertes : jour UTC (ops_alertes) vs jour local (jobs_impl) vs jour Réunion (protection) — rappels doublés/retenus autour de 02:00/04:00 Réunion |
| D-05 | cosmétique | `partners.py:399` : « consulté le » en heure process à côté d'un « créé le » en heure Réunion (divergent de 2 h sur machine CEST) |
| D-13 | cosmétique | PDF « généré le » + `numero_rapport` AAAAMMJJ en date du process (J-1 pendant 2 h/nuit hors prod) |
| D-07 | cosmétique | « aujourd'hui » en date UTC (`score_v.py:48`, `permits_sdes.py:149/170`, `ops_alertes.py:119`) : J-1 entre 00:00 et 04:00 Réunion |
| D-08 | cosmétique | mois de facture Stripe agrégé en UTC (`stripe_lecture.py:47`) |
| D-09 | cosmétique | front en fuseau navigateur hors 9 écrans admin — juste pour un client Réunion, J-1 possible pour un lecteur en Europe la nuit |
| D-06 | à surveiller | `faisabilite/bilan.py:29` : `ANNEE_REF` figée à l'import — année périmée si le process passe le Nouvel An |
| D-11 | à surveiller | conversion crontab +4 : ne décale pas dom/dow (h UTC ≥ 20) et ignore les heures en liste — aucun job touché AUJOURD'HUI, garde à rejouer |
| D-10/12/14/15 | positifs | base 100 % timestamptz instants exacts · registre cron UTC→Réunion vérifié par deploy.sh · zéro mélange naïf/aware · mails clients en heure Réunion |
