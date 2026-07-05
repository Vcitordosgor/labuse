# NOTES — Vague A1 : ingestion BODACC (procédures collectives)

Branche `ingestion/bodacc`. **Non mergée** — Vic valide puis merge en `--no-ff`.
On INGÈRE la donnée, on ne touche PAS au scoring (étage 2 = plus tard, quand les 3 sources A sont là).

## Ce qui a été fait (4 livrables)

### Livrable 1 — Connecteur `src/labuse/connectors/bodacc.py`
- API Opendatasoft DILA, ouverte, **sans clé** : `annonces-commerciales`.
- Filtre `familleavis="collective"` (= BODACC A, procédures collectives). **Schéma VÉRIFIÉ** sur un
  record réel (id `A200902491993`), pas deviné : `registre` (tableau `["482 309 382","482309382"]`
  → SIREN 9 chiffres), `jugement.nature` (type de procédure), `jugement.date` (texte FR),
  `dateparution` (ISO), `tribunal`, `numeroannonce`, `publicationavis`.
- Interrogation **par SIREN, batchée** (`registre IN (...)`, ~40 SIREN/requête, vérifié live) +
  paginée (100/page, garde-fou offset ≤ 10 000) + throttlée + retry sur 429/5xx.

### Livrable 2 — Table + modèle + fraîcheur
- Modèle SQLAlchemy `BodaccProcedure` (`bodacc_procedures`) : `annonce_id` (unique, dédup), `siren`
  (**index** `ix_bodacc_siren`), `type_procedure`, `famille_jugement`, `date_annonce`,
  `date_jugement_txt`, `tribunal`, `numero_annonce`, `publication`, `url_source`, `raw` (JSONB),
  `ingested_at`. Un SIREN → plusieurs lignes possibles.
- Créée par `create_all` (+ vue via `ensure_bodacc_view`, ajouté aux DEUX chemins : `create_all`
  complet et le repair-schéma léger du boot).
- Source `data_sources` « BODACC (procédures collectives) » ajoutée à `seed_sources` ;
  `last_sync_at` posé à chaque `ingest_bodacc` (cohérent Vague D — fraîcheur par couche).

### Livrable 3 — Croisement + flag `foncier_sous_pression`
- Vue SQL `v_foncier_sous_pression` : `bodacc_procedures.siren` ⋈ `parcelle_personne_morale.siren`
  → une ligne par parcelle (idu), procédure la **plus récente** (`DISTINCT ON`). Source `'BODACC'`.
- Fonction `parcelles_sous_pression(session, insee=None)` : flag *calculable et interrogeable*.
  **N'est PAS branchée au scoring** — marquée `# TODO étage 2` (dans la vue, la fonction, le modèle).

### Livrable 4 — Échantillon Saint-Paul (garde-fou anti-incident)
- `sample_report(session, "97415")` : **LECTURE SEULE** (n'écrit RIEN). Lit les SIREN PM de
  Saint-Paul (idu préfixé), interroge BODACC live, croise **en mémoire**, produit compteurs + 5
  exemples vérifiables. Rapport présenté à Vic. **Passe île entière NON lancée** (attend le feu vert).

## Décisions / écarts à connaître

1. **Distinct SIREN ≪ 82 087 liens.** Beaucoup de parcelles partagent un propriétaire (mairie, SEM,
   bailleur…). SIREN distincts **bien formés** : **9 697** (île), **1 581** (Saint-Paul). L'ingestion
   se fait donc sur les SIREN distincts, pas sur les 82k liens — tractable (l'île entière tient en
   quelques centaines de requêtes batchées, à lancer après feu vert Vic).
2. **9 953 liens ont un SIREN mal formé** (vide / non 9-chiffres). Filtre `siren ~ '^[0-9]{9}$'`
   partout → jamais de requête ni de flag sur un identifiant douteux.
3. **Interrogation par SIREN (pas par département 974).** Une société propriétaire à La Réunion peut
   avoir son tribunal en métropole → filtrer BODACC par `numerodepartement=974` RATERAIT ces
   procédures. Le croisement par SIREN est complet quel que soit le ressort.
4. **`date_jugement_txt` = texte brut** (formats MIXTES selon l'annonce : « 10 décembre 2009 » OU
   « 2025-04-16 » ISO — vérifié). Non parsé en `date` : on ne fabrique pas une date depuis un libellé
   variable. La récence fiable pour l'étage 2 vient de `date_annonce` (`dateparution` ISO, constant).
4bis. **PIÈGE attrapé au sample : `jugement` est une CHAÎNE JSON, pas un objet.** L'API ODS renvoie
   l'objet imbriqué `jugement` sérialisé en string (`'{"nature": ...}'`). Sans `json.loads`,
   `type_procedure`/`date_jugement` étaient TOUJOURS `None`. Corrigé + test de non-régression
   (`test_parse_record_jugement_string_json`). C'est le sample (Livrable 4) qui l'a révélé — d'où le
   garde-fou. (`registre`, lui, est bien une liste.)
4ter. **Sémantique du type = affaire de l'étage 2, PAS de l'ingestion.** Toutes les annonces
   `familleavis="collective"` ne valent pas « deal accessible » : une « clôture pour extinction du
   passif » (SCI DE SAINT ANDRE, 2014) = société qui a tout remboursé (sain, sortie propre) ; une
   « clôture pour insuffisance d'actif » (SCI LAW-KING, 2013) = liquidation soldée (société souvent
   disparue) ; une « conversion en redressement judiciaire » (SOFICOOP, 2025) = détresse ACTIVE.
   Le flag capte « a été/est sous procédure » ; la PONDÉRATION par type × récence est un travail
   d'étage 2 (les champs `type_procedure` + `date_annonce` sont conservés pour ça). `# TODO étage 2`.
5. **`url_source` = permalien explore ODS** (`.../table/?q=id:<id>`), garanti résolvable et
   vérifiable à la main. Les routes `bodacc.fr/annonce/...` testées renvoient un shell SPA (contenu
   chargé en JS) → non fiables pour un lien-preuve. La paternité DILA + licence sont tracées dans
   `data_sources`.
6. **Aucune écriture prod dans cette session.** Table + vue créées uniquement dans la base de TEST
   (par `create_all` du harnais de tests). L'échantillon Saint-Paul est 100 % lecture seule. La
   création de `bodacc_procedures`/`v_foncier_sous_pression` en prod + la passe d'ingestion se font
   après feu vert de Vic (via `labuse` boot/`create_all` puis `ingest_bodacc` chunké).

## Tentations HORS périmètre repérées (non faites)

- **Commande CLI `ingest-bodacc`** : pas ajoutée pour ne pas offrir un bouton « passe complète » avant
  validation. À câbler à la prochaine session (chunké, feu vert acquis). Le cœur (`ingest_bodacc`,
  chunké par batch de SIREN) est prêt et testé.
- **BODACC B/C** (radiations, comptes annuels), **fonds de commerce**, **parsing des dates FR** : hors
  périmètre (autres signaux / autres sessions).
- **Branchement étage 2** (scoring accessibilité) : attend les 3 sources de la Vague A (BODACC +
  décès INSEE A2 + INPI RNE A3). Points d'accroche marqués `# TODO étage 2`.

## Prochaine étape
Après validation de l'échantillon par Vic → créer table+vue en prod (`create_all`) puis `ingest_bodacc`
**chunké** sur les 9 697 SIREN de l'île (lecture API + écriture `bodacc_procedures` validée). Puis Vague
A2 (décès INSEE), A3 (INPI RNE), et seulement ensuite l'étage 2.
