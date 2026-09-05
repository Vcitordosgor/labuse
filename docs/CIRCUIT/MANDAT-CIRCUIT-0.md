# MANDAT CIRCUIT-0 — Inventaire de la plomberie (lecture seule)

Branche : `audit/circuit-0`, créée depuis `main` à jour
Dossier des livrables : `docs/CIRCUIT/`
Nature : audit en lecture seule. Aucun correctif, aucune migration, aucune écriture en base, aucun job lancé, aucun appel HTTP vers un producteur. Les seuls scripts autorisés lisent le code et exécutent des `SELECT`.
Objectif : donner la carte exacte de l'eau dans LABUSE — d'où elle entre (réservoirs), où elle est calculée (pompe), où elle sort (robinets), et où elle fuit — pour dessiner la page Circuit définitive et rédiger le mandat CIRCUIT-1.

Vocabulaire du mandat, à reprendre tel quel dans les livrables :
- **réservoir** = une source amont (Sitadel, DVF, PLU/GPU…)
- **pompe** = un moteur, c'est-à-dire un calcul défini une fois pour un chiffre
- **robinet** = un endroit de l'app qui affiche un chiffre (fond de carte, couche, outil, fiche, PDF, mail, Copilote…)
- **chiffre** = une valeur affichée : nombre, pourcentage, classe, verdict, tranche
- **fuite** = un robinet qui calcule un chiffre par son propre chemin au lieu d'appeler le moteur
- **eau ancienne** = une valeur servie calculée sur une version plus vieille que celle qui est dans le réservoir

---

## Étape 0 — avant toute écriture

1. `pwd`, branche courante, arbre propre. Si l'un des trois ne va pas : stop, rien n'est écrit, tu le signales.
2. `git checkout main && git pull --ff-only`, puis `git checkout -b audit/circuit-0`.
3. En tête du rapport : commit de départ, run servi (lu dans la constante unique, pas dans une table), base utilisée (locale), date.

---

## Règles

1. **Pas de preuve, pas de ligne.** Chaque affirmation porte `fichier:ligne` ou la requête SQL exécutée avec son résultat. Ce qui n'est pas prouvable est marqué `DOUTE`, jamais deviné.
2. **Les comptes sont comptés, pas estimés.** Un compteur du rapport est le nombre de lignes d'un fichier livré, vérifié par script.
3. **Les libellés sont ceux que voit l'utilisateur**, copiés des templates, en français, avec leur casse.
4. **Identifiants stables.** Tu proposes un `id` snake_case pour chaque réservoir, moteur, robinet et chiffre. Ce sont les futurs identifiants du registre : le même id partout, dans tous les fichiers, jamais renommé en cours de route.
5. **Un chiffre = un id.** Si le même chiffre (même sens, même libellé ou libellé équivalent) est affiché à plusieurs endroits, il garde un seul id, même s'il est calculé par des chemins différents — c'est justement ce qu'on cherche. Si tu hésites sur « même chiffre ou pas », tu gardes deux ids et tu notes `DOUTE`.
6. **Mesures sur la base locale**, run servi, sans écriture. Note le run.
7. **Rien n'est réparé.** Une fuite trouvée est notée, mesurée, jamais corrigée. Une table morte encore lue est notée, jamais supprimée.
8. **Deux sessions si besoin** : A = lots 1 à 4, B = lots 5 à 8. La session B repart du rapport et des fichiers de A, commités sur la branche.
9. Chaque lot se termine par un point d'étape dans le rapport : compteurs, lignes `DOUTE`, ce qui a bloqué.

---

## Lot 1 — Les réservoirs

Où est définie la liste des sources ? La page Sources affiche **77 sources, dont 49 sous veille** (constaté par Vic le 05/09/2026). Le 01/09, SENTINELLE-2 en connaissait 64 dont 35 surveillées. Trouve la source de vérité (table, catalogue Python, les deux ?) et dis si la page Sources, la sentinelle et les moteurs parlent de la même liste. Si elles ne concordent pas, chaque écart est une ligne du rapport.

Livrable `docs/CIRCUIT/inventaire/reservoirs.csv`, une ligne par source, colonnes :

| colonne | contenu |
|---|---|
| id | snake_case stable |
| nom_affiche | libellé de la page Sources |
| producteur | organisme |
| famille | regroupement s'il existe dans l'app ; sinon `aucune` |
| tables_servies | tables lues par les moteurs pour cette source |
| millesime_servi | version dans le réservoir, telle que l'app la connaît |
| date_injection | quand cette version est entrée |
| cadence_declaree | cadence renseignée, ou `aucune` (59 sur 64 le 31/08 ; à recompter sur 77) |
| mode_remplissage | `job_sur_clic` · `cron_mensuel` · `depot_manuel` · `one_shot` · `derivee` · `absente` |
| job_ingestion | commande ou module qui remplit le réservoir |
| cron | nom du job et horaire s'il se remplit seul |
| sentinelle | `oui` / `non` |
| methode_sonde | `api` · `page` · `entete` · `temoin` · `aucune` |
| derniere_sonde | date du dernier passage |
| dernier_millesime_publie_vu | ce que la sonde a vu chez le producteur |
| raison_non_surveillee | telle qu'en base |
| url_producteur_connue | URL présente dans le code, la doc ou la base ; vide sinon |
| licence | licence connue, ou `DOUTE` |
| absente_motif | pour les sources voulues mais absentes (Cerema, LOVAC, ECLN, MOBPRO…) |
| preuve | fichier:ligne ou requête |

Questions à répondre dans le rapport, avec preuve :
- 1.1 Les quatre crons mensuels (Sitadel, DPE, SIRENE, GPU) : que font-ils exactement — rafraîchissement complet, incrémental, saut des communes déjà peuplées ? Le cron DPE saute-t-il toujours ce qui est peuplé ? La trace en base suit-elle l'exécution réelle (dernier_ok vs log) ?
- 1.2 Quelles sources sont dérivées d'une autre (détections FLAIR, CoSIA, résiduel…) ? Elles ne sont pas des réservoirs mais des pompes, ou les deux : tranche et justifie.
- 1.3 Quelles sources ont plusieurs millésimes en base (historique MAJIC 2019→2025, DVF par année) et comment l'app choisit celui qu'elle sert ?
- 1.4 Le bouton « Injecter cette version » de la sentinelle : vers quel job pointe-t-il, pour quelles sources est-il réellement branché ?
- 1.5 De 64 à 77 : liste des sources ajoutées, découpées ou renommées depuis le 01/09/2026, avec la date et le mandat d'origine (EDF, TCSP OSM, LiDAR HD, Réunion Express… et le reste).

Compteurs à livrer : total ; par mode de remplissage ; surveillées / non ; sans cadence ; absentes ; avec URL producteur connue.

---

## Lot 2 — La pompe : moteurs et runs

Livrable `docs/CIRCUIT/inventaire/moteurs.csv`, une ligne par moteur (sector_price, résiduel, scoring, cascade, destinations PLU, étude de zone, permis/opérations, marché affiché vs acté, risques, solaire, rattachement BAN, et tout autre que tu trouves) :

| colonne | contenu |
|---|---|
| id | snake_case stable |
| nom | |
| fichier | chemin |
| fonctions | fonctions publiques qui produisent des chiffres |
| entrees | tables lues → ids de réservoirs |
| versionne_par_run | `oui` (résultats stockés par run) / `non` (calcul à la lecture) |
| run_lu | `constante_unique` · `parametre` · `en_dur` · `live` |
| cache | mécanisme et TTL, ou `aucun` |
| preuve | |

Questions :
- 2.1 Le run servi : la constante unique posée par CONNEXIONS-2 est-elle le SEUL pointeur ? Liste tout ce qui ressemble à un pointeur de run (scoring, `parcel_residuel` avec `residuel-serve`, cascade, autres) et dis s'ils sont alignés aujourd'hui.
- 2.2 Liste des runs existants en base (q_v8 → q_v12…) : date, ce qu'ils contiennent, lequel est servi, lesquels sont morts. Tables de run encore lues par un robinet alors qu'elles ne sont plus servies : liste.
- 2.3 « Calculer » aujourd'hui : quelles commandes produisent un run candidat (golden automatique après Sitadel, commandes `labuse …`), ce qu'elles recalculent (scoring seul ? résiduel ? tout ?), durée mesurée ou estimée, où atterrit le candidat.
- 2.4 « Basculer » et « Revenir en arrière » aujourd'hui : mécanisme exact, atomicité, ce qui est journalisé.
- 2.5 État réel de la page Données › Mise à jour (mandat DONNEES-2) : implémentée ? mergée ? Pour chacune des trois étapes Injecter · Calculer · Basculer : endpoint, commande appelée, synchrone ou asynchrone, ligne d'event_log.
- 2.6 Quels chiffres dépendent d'un run (donc ne changent qu'à la bascule) et lesquels sont lus en direct (donc changent dès l'injection) ? C'est ce qui définit « eau ancienne » pour chaque chiffre.

---

## Lot 3 — Les horloges

Livrable `docs/CIRCUIT/inventaire/jobs.csv`, une ligne par job du wrapper `run-job.sh` (13 attendus) et par cron encore posé hors wrapper :

| colonne | contenu |
|---|---|
| id | nom du job |
| horaire_utc | |
| horaire_reunion | |
| fait_vraiment | lu dans le code, pas dans la doc |
| touche_l_eau | `oui` (ingère, sonde, calcule, contrôle) / `non` (backup, santé, digests) |
| dernier_statut | depuis l'état JSON du wrapper |
| trace_base_coherente | la trace en base suit-elle le log ? |
| preuve | |

Questions :
- 3.1 Table `source_veille` : schéma complet et dump des lignes (dans `inventaire/source_veille.csv`).
- 3.2 Notifications de la sentinelle : cloche, digest, morning brief — où passent-elles, dédoublonnage.
- 3.3 SENTINELLE-3 : exécuté ? mergé ? Quelles sources sont passées de non surveillées à surveillées depuis SENTINELLE-2 (35 → 49), par quelle méthode chacune ?
- 3.4 Le « candidat automatique après Sitadel » existe-t-il en vrai ? Preuve.
- 3.5 Contradictions connues (healthz/crons vs log radar, DPE) : toujours là ?

---

## Lot 4 — Les robinets

Livrable `docs/CIRCUIT/inventaire/robinets.csv`, une ligne par endroit qui affiche au moins un chiffre :

| colonne | contenu |
|---|---|
| id | snake_case stable |
| categorie | `fond` · `couche` · `outil` · `fiche` · `copilote` · `veille` · `projets` · `crm` · `notification` · `pdf` · `page_client` · `admin` |
| nom_affiche | libellé exact du menu ou de l'écran |
| parent | ex. `outil_communes` pour `Évolution du marché` |
| route_ou_template | endpoint API, template, builder PDF, template Brevo |
| producteur | fichier:fonction qui fabrique les chiffres |
| mode_rendu | `template_serveur` · `json_puis_js` · `pdf` · `mail` · `texte_llm` · `tuiles` |
| nb_chiffres | nombre de lignes de chiffres.csv pour ce robinet |
| preuve | |

Périmètre, sans exception :
- les 5 fonds de carte et leur source de tuiles ;
- toutes les couches du menu Carte, dans l'ordre du menu, avec la source de chaque aplat ou point ;
- tous les outils du menu Outils avec leurs sous-entrées (Communes ×3, Scan patrimoine ×2, Permis ×2, Prospection solaire ×2, Pièges ×2…) ;
- la fiche parcelle, une ligne par section-tiroir ; la fiche commune, une ligne par carte (15 attendues) ; fiche annonce, fiche propriétaire, fiche soleil ;
- le Copilote : ses 6 outils SQL et tout chiffre qui apparaît dans une réponse ;
- Veille (les évaluations qui déclenchent), Projets (classement, bandeau d'analyse), CRM ;
- notifications : cloche, morning brief, digest Radar, alertes Radar — chaque paramètre chiffré des templates Brevo ;
- les 6 PDF (Flash, Dossier expert, banquier, pré-dossier PC, lettre de zonage, argumentaire) et la page `/flash` publique ;
- la page Sources côté client ;
- le dashboard admin : chaque page qui affiche un chiffre de données (Données, Pilotage, IA…).

Compteurs : par catégorie ; total.

---

## Lot 5 — Les chiffres, le cœur du mandat

Livrable `docs/CIRCUIT/inventaire/chiffres.csv`, **une ligne par couple (robinet, chiffre)**. Attends-toi à plusieurs centaines de lignes ; c'est le registre en germe.

| colonne | contenu |
|---|---|
| robinet_id | |
| chiffre_id | stable, le même id quand c'est le même chiffre ailleurs (règle 5) |
| libelle_affiche | tel qu'à l'écran |
| unite | `%` · `€` · `€/m²` · `m²` · `logements` · `classe` · `verdict` · `tranche` · `date` · `nombre` |
| niveau | `parcelle` · `commune` · `zone` · `proprietaire` · `annonce` · `global` |
| calcul | `moteur:<id>` · `sql_propre` · `front` · `constante` · `llm` · `passe_plat` (valeur brute d'un réservoir) |
| fichier_ligne | où la valeur est produite |
| reservoirs_lus | ids des réservoirs, via les tables lues |
| run_lu | id du run ou `live` |
| cache | TTL ou `aucun` |
| tampon | ce que la valeur porte aujourd'hui comme provenance : `date` · `millesime` · `run` · `rien` |
| definition_lue | une phrase, telle que le code la fait (dénominateur, périmètre, fenêtre) |
| preuve | |

Questions :
- 5.1 **Fuites candidates** — `inventaire/fuites_candidates.csv` : tout `chiffre_id` servi par ≥ 2 robinets avec ≥ 2 chemins de calcul différents (`fichier_ligne` différents). Commence par la part RNU par commune (fiche commune vs outil Communes › Comparaison, 18 % vs 6 % constaté par Vic sur Saint-Paul).
- 5.2 **Fuites mesurées** — `inventaire/fuites_mesurees.csv` : pour chaque candidate, exécute les deux chemins sur les témoins (les 24 communes ; les 50 parcelles golden ; pour zone, propriétaire et annonce : 5 clés fixes que tu choisis et documentes) et livre `chiffre_id, cle, robinet_a, valeur_a, robinet_b, valeur_b, ecart, cause_probable, preuve`. Causes admises : `denominateur` · `perimetre` · `run` · `table` · `millesime` · `fenetre_temporelle` · `arrondi` · `autre`. Dis quel chemin est fidèle à l'intention du code, ou `DOUTE`.
- 5.3 **Eau ancienne aujourd'hui** — `inventaire/eau_ancienne.csv` : chiffres dont la valeur servie ou cachée vient d'une version plus vieille que celle du réservoir (DPE en premier suspect). Comparaison millésime de la table ↔ millésime réellement utilisé.
- 5.4 **Calculs côté navigateur** : tout JavaScript qui additionne, divise, arrondit ou dérive un chiffre affiché. Liste avec fichier:ligne. « Zéro recalcul au front » a été vérifié sur les 15 outils, pas sur le reste.
- 5.5 **Chiffres du Copilote** : par quel chemin chaque nombre d'une réponse sort-il (outil SQL → moteur ? SQL propre ?) et le verrou anti-invention couvre-t-il tout ?
- 5.6 **Chiffres des PDF et des mails** : même question, builder par builder, template Brevo par template.

Compteurs : lignes totales ; `chiffre_id` distincts ; par `calcul` ; avec `tampon` ≠ `rien` ; fuites candidates ; fuites mesurées avec écart ≠ 0 ; eau ancienne.

---

## Lot 6 — Le graphe

Livrable `docs/CIRCUIT/inventaire/circuit.json`, construit à partir des lots 1, 2, 4, 5 — c'est ce que la page Circuit affichera :

```json
{
  "run_servi": "…",
  "reservoirs": [{"id":"…","nom":"…","famille":"…","mode_remplissage":"…","millesime_servi":"…","sentinelle":true}],
  "moteurs":    [{"id":"…","nom":"…","fichier":"…"}],
  "chiffres":   [{"id":"…","libelle":"…","unite":"…","niveau":"…","moteur":"…|null"}],
  "robinets":   [{"id":"…","nom":"…","categorie":"…","parent":"…|null"}],
  "aretes": {
    "reservoir_vers_chiffre": [["reservoir_id","chiffre_id"]],
    "chiffre_vers_robinet":   [["chiffre_id","robinet_id"]],
    "fuites":                 [["reservoir_id","robinet_id","chiffre_id","fichier_ligne"]]
  }
}
```

Un script `scripts/inventaire/valide_circuit.py` (lecture seule) vérifie : tous les ids référencés existent, chaque chiffre a ≥ 1 réservoir et ≥ 1 robinet, les compteurs du rapport égalent les tailles des listes.

Question 6.1 — **table d'impact par réservoir** dans le rapport : pour chaque réservoir, nombre de chiffres et nombre de robinets touchés par une injection, robinets listés. C'est la réponse à « combien de produits récupèrent cette source ».

---

## Lot 7 — Agents et traçage : faisabilité, sans rien construire

- 7.1 Pile IA : contenu de `ai_models.py`, version du SDK figée, où l'API est appelée aujourd'hui (Copilote, extraction pige, dépôt agence…), mécanisme `ia_budget`, pattern existant pour un appel LLM en job de fond, présence de Playwright ou d'un navigateur sur le VPS, règles de sortie réseau du VPS. Aucun appel externe pour vérifier : lecture seule.
- 7.2 `inventaire/agents_fiches.csv` — pour chaque réservoir non surveillé (28 attendus) : `id, url_producteur_connue, format_du_millesime (comment le producteur nomme ses versions), raison_non_surveillee, page_rendue_en_js (oui/non/DOUTE), piste`. C'est le brief de départ de chaque agent.
- 7.3 Traçage : par quels chemins un chiffre arrive à l'écran ? Compte les chemins de rendu distincts (filtres Jinja de formatage, formateurs JS, builders PDF, templates mail). Existe-t-il un point de passage unique pour formater un nombre ? Si oui, fichier:ligne et nombre d'appels ; si non, estimation du nombre de sites d'appel à équiper d'une étiquette.
- 7.4 Journal : les gestes Injecter, Calculer, Basculer, Revenir sont-ils journalisés (qui, quand, quoi) dans `event_log` ? Preuve.

---

## Lot 8 — Synthèse

`docs/CIRCUIT/INVENTAIRE-RAPPORT.md` commence par ce tableau, chaque nombre égal à un compte de fichier :

| compteur | valeur |
|---|---|
| réservoirs : total / job sur clic / cron mensuel / dépôt manuel / dérivés / absents | |
| réservoirs surveillés par la sentinelle / non surveillés / sans cadence / avec URL producteur connue | |
| moteurs / versionnés par run / live | |
| runs en base / servi / morts / tables mortes encore lues | |
| jobs / qui touchent l'eau / avec trace en base cohérente | |
| robinets : total, puis par catégorie | |
| chiffres : lignes / ids distincts / via moteur / SQL propre / front / passe-plat / avec tampon | |
| fuites candidates / mesurées / avec écart ≠ 0 | |
| chiffres en eau ancienne aujourd'hui | |
| lignes DOUTE | |

Puis, dans l'ordre : les 10 constats qui pèsent le plus (impact sur ce que voit un client) ; les fuites mesurées ; la liste complète des `DOUTE` avec ce qui permettrait de trancher ; les questions pour Vic ; une estimation honnête de la taille du registre à écrire (nombre de chiffres à déclarer, nombre de robinets à rebrancher).

---

## Livrables

```
docs/CIRCUIT/INVENTAIRE-RAPPORT.md
docs/CIRCUIT/inventaire/reservoirs.csv
docs/CIRCUIT/inventaire/moteurs.csv
docs/CIRCUIT/inventaire/jobs.csv
docs/CIRCUIT/inventaire/source_veille.csv
docs/CIRCUIT/inventaire/robinets.csv
docs/CIRCUIT/inventaire/chiffres.csv
docs/CIRCUIT/inventaire/fuites_candidates.csv
docs/CIRCUIT/inventaire/fuites_mesurees.csv
docs/CIRCUIT/inventaire/eau_ancienne.csv
docs/CIRCUIT/inventaire/agents_fiches.csv
docs/CIRCUIT/inventaire/circuit.json
scripts/inventaire/*.py   (lecture seule : extraction, mesure des fuites, validation)
```

CSV en UTF-8, séparateur `;`, en-tête sur la première ligne, ouverts sans erreur dans un tableur. Un commit par lot, message `CIRCUIT-0 lot N — …`. Rien n'est mergé : Vic merge depuis `labuse-merge`.

---

## Définition de fini

- Les 12 fichiers existent et le script de validation passe.
- Chaque ligne de chaque CSV a sa colonne `preuve` remplie, ou porte `DOUTE`.
- Les compteurs du rapport sont produits par script à partir des CSV, pas tapés à la main.
- Les fuites mesurées incluent la part RNU de Saint-Paul avec les deux valeurs et la cause.
- Le rapport se termine par : commit final, nombre de lignes `DOUTE`, temps passé par lot, et la liste de ce que tu n'as pas pu faire, avec la raison.

## Interdits

Pas de correctif, pas de migration, pas d'écriture en base, pas de job lancé « pour voir », pas d'appel HTTP vers un producteur, pas de modification hors `docs/CIRCUIT/` et `scripts/inventaire/`, pas de merge, pas de push sur `main`.
