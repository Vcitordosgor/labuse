# Bascule 2026 — base commune `labuse` / prod — RUNBOOK (NON exécuté)

> OUTIL-SCAN-FIX-4. Procédure PRÉPARÉE, **non lancée** sur `labuse`/prod (l'agent ne lance `--go`/`--rollback`
> que sur `labuse_scanfix`). Script : `scripts/bascule_2026_labuse.py`. Vic choisit la cible et le moment.
> **Plus AUCUNE étape manuelle** : le script enchaîne TOUT (droits → archive 2025 → flip → BODACC →
> blocs+membres → recalcul & promotion V-score). `--rollback --sauvegarde <N>` ramène TOUT, run servi compris.

## Sûretés intégrées (relecture-scan-3)

- **Cible par ARGUMENT, zéro environnement.** `--db <url>` est OBLIGATOIRE ; le script ne lit NI
  `LABUSE_DATABASE_URL`, NI `.env`, NI aucun défaut (`create_engine(url)` direct). `--confirme` est comparé à
  l'**identité renvoyée par le serveur** : `current_database()` @ `system_identifier` (identité du cluster,
  IDENTIQUE pour `localhost`/`127.0.0.1`/`::1`/socket) `:` port — insensible à la casse. Un refus
  **n'imprime jamais** la valeur attendue (sinon il dicterait le `--confirme` qui débloque la prod).
- **Sauvegardes NUMÉROTÉES & DATÉES, jamais périmées.** Chaque `--go` crée `_bascule_bak__<N>__*` + une ligne
  au registre `_bascule_sauvegardes`. `--go` REFUSE si une sauvegarde plus ancienne existe, SAUF
  `--malgre-sauvegarde <N>` (qui la nomme). `--rollback` EXIGE `--sauvegarde <N>`, affiche (numéro, date,
  lignes) et n'agit que sur celle-là. `--purge-sauvegarde <N>` la supprime une fois la bascule validée.
- **Staging + transaction unique.** Droits 2025 & 2026 → table d'attente `parcelle_pm_droit_staging` ;
  promotion droits + archive 2025 + flip = UNE transaction. Interruption avant son commit → servie inchangée.
- **Sauvegarde COMPLÈTE.** Couvre les 8 tables touchées : `parcelle_personne_morale`,
  `pm_proprietaires_millesimes`, `parcelle_pm_droit`, `bodacc_depots`, `parcel_blocs`,
  **`parcel_bloc_membres`**, **`p_score_v2_runs`**, **`parcel_p_score_v2`**, + les **octets exacts** du
  **label servi** (`config/served_run.txt`). `--rollback` restaure tout EN UNE transaction et **re-sert
  réellement** le run précédent (réécrit `config/served_run.txt`) puis le **vérifie** (`_served_run_versionne`).

## Procédure (une commande)

```bash
P=.venv/bin/python; S=scripts/bascule_2026_labuse.py
U="postgresql+psycopg://<user>@<host>:5432/labuse"       # local commun ; prod = l'URL prod

# Inspection (lecture seule ; donne l'identité serveur à mettre dans --confirme) :
$P $S --db "$U" --empreinte
$P $S --db "$U" --dry-run
$P $S --db "$U" --lister-sauvegardes

# BASCULE ENTIÈRE (chaîne droits, archive, flip, BODACC, blocs+membres, recalcul+promotion V-score) :
$P $S --db "$U" --go --confirme <base>@<system_identifier>:<port>
#   (si une sauvegarde ancienne existe : ajouter --malgre-sauvegarde <N> OU --purge-sauvegarde <N> d'abord.)

# RETOUR ARRIÈRE total (ramène TOUT, run servi inclus) :
$P $S --db "$U" --rollback --sauvegarde <N> --confirme <base>@<system_identifier>:<port>

# Quand la bascule est validée et stable :
$P $S --db "$U" --purge-sauvegarde <N> --confirme <base>@<system_identifier>:<port>
```

(programmes et sirene_etablissements sont DÉJÀ en base `labuse` → rien à recharger. Base vide : programmes via
l'admin `/admin/programmes/collecter`+`valider`, sirene via `labuse ingest-sirene-etab`, avant le `--go`.)

## Ce que la bascule change (parcelles multi-titulaires : ≈ 2 711 SIREN principaux, 3 989 `groupe`)

| Écran / moteur | Effet |
|---|---|
| Fiche parcelle | propriétaire = le propriétaire (P) sur les multi-titulaires ; + « + N autres titulaires ». |
| Blocs fonciers | `blocs-build` chaîné (reconstruit `parcel_blocs` + `parcel_bloc_membres`). |
| Communes « changements » | archive 2025 même règle → ≈ 963 vrais changements (≈ 1 056 artefacts retirés). |
| Classement / V-score | recalcul + **promotion** chaînés ; `config/served_run.txt` → nouveau run. |
| Scan patrimoine / Copilote | millésime 2026, droits séparés, DP/annulés à part, catégorie NAF, sans valorisation. |

## 12 témoins de cohérence (hook)

Marché €/m², indépendants du propriétaire → le flip ne crée aucun écart 1 €/1 m². Relancer
`bash scripts/ci/coherence_run.sh` après la bascule : un témoin multi-titulaire voit son owner changer
identiquement sur tous les écrans (source unique) → 0 divergence.

## Durée & reproductibilité

Procédure entière mesurée sur `labuse_scanfix` : **≈ 55 s** (hors téléchargement des ZIP, mis en cache
/tmp). En prod, postes longs : BODACC (`--bodacc-limit 0` = tous les SIREN, minutes, API) et le **recalcul
V-score réel** (`run_score_v2`, minutes-dizaines). **Reproductibilité** : deux `--go` donnent le même état
MÉTIER mais des colonnes **volatiles** diffèrent (`id` série, `date_import`=`now()`, `run_id` horodaté) — un
`diff` naïf verrait des écarts ; la vérité se lit sur les colonnes métier. Le `--rollback`, lui, ré-insère
le snapshot **à l'octet** (volatiles comprises).

## Rollback — ce qui revient

`--rollback --sauvegarde <N>` restaure les 8 tables + réécrit `config/served_run.txt` (run précédent
re-servi **et vérifié**). Couvre donc : données, archive, `bodacc_depots`, `parcel_blocs` **et**
`parcel_bloc_membres`, le run V-score (`p_score_v2_runs`/`parcel_p_score_v2`) et le **label servi**. Nommer
la bonne sauvegarde : un `--rollback --sauvegarde 2` après deux bascules ramène à l'état **d'après la 1ʳᵉ**
(prouvé), pas à l'origine.

## ARRÊT

Rien n'est exécuté sur `labuse`/prod. Vic déclenche la fenêtre.
