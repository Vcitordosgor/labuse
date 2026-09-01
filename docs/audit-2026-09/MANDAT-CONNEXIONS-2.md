# MANDAT CONNEXIONS-2 — corrections issues de CONNEXIONS-RAPPORT

**Branche : `fix/connexions-2`** (depuis `main` après merge de `audit/connexions-1`). Bloc commun habituel.
**Source de vérité : `docs/audit-2026-09/CONNEXIONS-RAPPORT.md`** — chaque lot cite ses KO ; CC relit la ligne du rapport (preuve `fichier:ligne`) avant de corriger.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.
**Deux sessions** : Partie A (lots 1→5) puis Partie B (lots 6→10). Chaque session se termine par `tsc`, build, tests **backend et front**, et un **commit sur la branche** avant le compte-rendu. Merge = Vic.

Règles du mandat :
- **On ne supprime aucune table ni colonne.** On cesse de lire, on migre, on marque obsolète — la suppression viendra dans un mandat d'hygiène.
- **Toute migration a un backfill et un test.**
- **Une correction = un test de non-régression** qui aurait attrapé le KO.
- Quand deux implémentations coexistent, on **garde celle qui est servie à l'écran** et on fait pointer l'autre dessus (pas de troisième version).

---

# PARTIE A — session 1

## Lot 1 — Une seule cascade, un seul run (KO-1, KO-2, « trois constantes de run », « deux builders PDF »)

1. **Une constante de run unique** : créer un point de lecture unique du run courant (ex. `runs.current()` ou table `runs` avec un flag `courant`), utilisé par TOUS les appelants. Supprimer les trois constantes en dur trouvées par l'audit ; `served_cascade.py:20 _DEFAULT_RUN="q_v8_calibre"` disparaît au profit de ce point unique (aujourd'hui `q_v11_m137`).
2. Les appelants sans run (`flash/data.py:150,367,410`) passent le run courant explicitement.
3. **`cascade_results` LIVE n'est plus lue** : `anti_fiche.py:52` et `app.py:4428` lisent la cascade run-scopée servie à l'écran. La table reste en place, marquée obsolète (commentaire daté + entrée dans le rapport d'hygiène).
4. **Un seul builder de fiche pour les exports** : Finance et Argumentaire (`banquier.py:216`, `argumentaire.py:77` via `bq.collect` + `_PDF_CACHE`) lisent `_q_v2_fiche` comme Dossier, Lettre zonage et Pré-dossier PC. `_PDF_CACHE` séparé disparaît ou s'aligne sur l'invalidation de la fiche.
5. **Recette obligatoire** : pour 3 parcelles (une Priorité, une À suivre, une sans signal), générer les 5 exports experts et comparer à l'écran : zonage, risques, tier, capacité, **date de valeur** — identiques au chiffre près. Le test automatisé compare fiche écran et payload d'export sur ces champs.

## Lot 2 — Copilote : un seul quota, par compte (KO-3, K4)

1. `/ask` v2 (`copilote_v2.py:76`) lit le quota **par compte** (`copilote_quota_jour` avec l'override édité au dashboard, `ia.py:340`) — plus de plafond global `copilote_v2_missions_jour`.
2. Un seul compteur, un seul plafond, une seule fonction `quota_du_compte(compte_id)` appelée par `/ia` et `/ask`.
3. Le dashboard affiche pour chaque compte : consommé aujourd'hui / plafond ; l'édition du plafond est relue à la requête suivante (test).
4. **Copilote v1** : lister les endpoints encore joignables ; s'ils ne sont plus servis par aucun écran, les marquer obsolètes (ne pas supprimer) et le dire au compte-rendu.

## Lot 3 — Gestes de fiche (KO-4, KO-5, KO-8, KO-9)

1. **Signaler** : un seul système de signalement. Le « Signaler » de la fiche (`postSignalement` → `/signalements`, revue CLI-only) et celui du Radar (`event_log`) écrivent dans **la même table**, avec type (fiche/annonce), IDU, auteur, motif, date. Le compteur du dashboard lit cette table ; l'admin **voit et traite** les signalements dans le dashboard (liste, statut ouvert/traité), plus de CLI-only.
2. **Courrier depuis la fiche** : la tuile et la porte (`Fiche.tsx:2514,2658`) appellent `setCourrierPrefill(idu, propriétaire)` — l'outil s'ouvre pré-rempli. Test.
3. **Ajouter au CRM** : `addToPipeline` (`api.ts:860`) passe la colonne choisie ; l'UI propose le choix de la colonne (sélecteur, valeur par défaut = première colonne) au lieu de l'imposer en silence (`app.py:5657`).
4. **Annonces-Radar depuis la fiche commune** : `RadarView.tsx:342` lit `communesFilter` posé par `ContextePanel.tsx:98` — le Radar s'ouvre filtré sur la commune, et le compteur affiché égale « N biens en vente » de la fiche commune. Test.

## Lot 4 — La boucle commerciale se ferme (KO-6, KO-16, KO-17, KO-10, I4, J3, J4, « deux systèmes Courrier », KPI dashboard)

Objectif : retenue → piste → courrier → réponse → statut, **sans ressaisie**, et chaque étape relue partout.

1. **Un seul système Courrier** : identifier les deux systèmes trouvés par l'audit ; garder celui servi par l'outil Courrier propriétaire ; l'autre devient une façade qui pointe dessus ou est marqué obsolète.
2. **Rattachement** : `courrier_demandes` (`courrier.py:52`) gagne `pipeline_entry_id` (FK) et `projet_id` ; backfill par IDU + compte quand c'est univoque, sinon NULL et listé.
3. **Un seul vocabulaire de statuts** : un modèle de statut courrier unique (`demande → déposé → envoyé → répondu / sans réponse`), avec table de correspondance vers les colonnes Kanban (`crm_columns`/pipeline.yaml) et les buckets dashboard (`Courrier.tsx:22`). « répondu » et « sans réponse » **existent** et sont saisissables (par la cliente dans le CRM, par l'admin au dashboard). Une seule source pour les trois écrans.
4. **Piste → courrier sans ressaisie** : `ModulePanel.tsx:912` ouvre le Courrier pré-rempli depuis la piste (IDU, propriétaire, projet).
5. **Statut relu** dans « Mes courriers » (`ProjetsPanel.tsx:235`), dans l'outil Courrier, dans le Kanban (la carte de la piste montre le statut du courrier), et au dashboard.
6. **KPI dashboard « courriers à déposer »** : `dashboard.py` agrège `courrier_demandes` par statut ; tuile avec le nombre à déposer, lien vers la liste.
7. **Scan patrimoine « actionnables hors écartées »** (KO-10) : `/modules/patrimoine` (`modules.py:255`) joint les décisions du compte (`projet_parcelles`, `pipeline_entries`) — « écartées » = celles que **ce compte** a écartées. Le libellé dit ce qu'il fait : « hors écartées par vous » ; sans décision, « N actionnables » sans mention.
8. **Recette bout en bout** (test d'intégration) : retenir une parcelle → la piste apparaît → ouvrir le courrier depuis la piste (pré-rempli) → déposer la demande → le dashboard compte 1 à déposer → l'admin passe « envoyé » puis « répondu » → le Kanban, « Mes courriers » et l'outil affichent le nouveau statut. Zéro ressaisie sur tout le chemin.

## Lot 5 — Veille de recherche : parité filtre ↔ veille (KO-7, D3)

1. **Même moteur** : l'évaluation d'une veille de recherche (`events.py:587`, 5 dimensions) réutilise le **constructeur de requête des filtres de la carte** (`filters.ts:206` sérialise 35 dimensions) — côté serveur, une fonction unique transforme le hash de filtres en requête, utilisée par la carte ET par la veille. Toute dimension filtrable devient surveillable.
2. Tant qu'une dimension ne peut pas être évaluée, elle **n'est pas enregistrée en silence** : l'UI de création affiche « cette veille surveille : … » avec la liste exacte, et signale ce qui n'est pas retenu.
3. Test : une veille créée avec 3 critères (dont un hors des 5 anciens) ne se déclenche que sur les parcelles qui vérifient les 3.

---

# PARTIE B — session 2

## Lot 6 — Fraîcheur et sources (KO-11, KO-14, M2)

1. **Accueil** : « Toutes les données sont à jour » (`LeftPanel.tsx:466`, littéral) devient une phrase calculée depuis l'état des sources (`/accueil/cette-semaine` `accueil.py:111`, aujourd'hui non consommé, ou `/sources`) : « Toutes les données sont à jour » / « N sources en retard » / « Une source en erreur ». Même donnée que la page Sources et le dashboard.
2. **Échec d'ingestion → « en erreur »** : le job connaît un état `en_erreur` ; `/sources` (`app.py:928`) l'expose ; la page Sources et le dashboard l'affichent (badge rouge, date, message).
3. **Désactiver une source depuis le dashboard** : action `est_affichee=false` (endpoint admin) ; **propagation** : les consommateurs (couches, outils, moteurs) vérifient `est_affichee`/status — un consommateur d'une source désactivée affiche « source désactivée » à la place du chiffre, jamais un chiffre périmé. `SOURCES_MASQUEES` en dur (`frozenset()`) disparaît au profit du flag en base. Test sur une couche et un outil.
4. **Millésime ortho en dur** → lu depuis la table de millésimes comme les autres (« millésime ortho codé en dur » du rapport).
5. Agent généralisé de nouvelle version amont (`admin/Sources.tsx:122` grisé V2) : **hors périmètre** de ce mandat — le dire au compte-rendu avec ce qu'il faudrait (par famille de source : URL de version, fréquence).

## Lot 7 — Dashboard : actions et santé (N2, N3)

1. **Toggle dépôt agence** : le flag passe de l'env (`config.py:70`) à un réglage en base, éditable au dashboard (admin seul), relu à chaud par `/etat`, `/ouvert` (`pige/api.py:572,584`) et par tous les écrans qui masquent les dépôts. Valeur par défaut = fermé. Test : bascule → visibilité immédiate.
2. **Monitoring des endpoints métier** : la sonde `healthcheck` (`jobs_impl.py:148`) ne teste que `/health` sans DB. Ajouter une sonde qui appelle, avec DB, une liste d'endpoints porteurs (`/accueil/chiffres`, fiche parcelle sur un IDU témoin, liste Radar, projets d'un compte témoin, `/sources`, `/ask` en mode dry-run) et vérifie **forme et non-vacuité** de la réponse. Résultat dans une tuile « Santé » du dashboard (dernier passage, endpoints en échec) + notification admin à la première panne. Le cas `/accueil/chiffres` vivant / écran vide doit être capté (test qui simule un payload vide).
3. **Crédits IA** : « ajouter des crédits » = éditer le plafond par compte (Lot 2) ; la tuile IA du dashboard montre consommé / plafond par compte et le total ; le lien console Anthropic reste pour le solde global (assumé, le dire dans l'UI).
4. Révoquer une session : **pas d'action** (doctrine SESSION-1 : signal commercial, pas de coupure). Rien à faire, le noter.

## Lot 8 — Recherche globale (C1)

1. La barre du bandeau résout, dans l'ordre : IDU · SIREN/SIRET · nom de propriétaire (`/proprietaires/autocomplete` existe, non câblé) · projet du compte · adresse · commune. Nom et SIREN ouvrent **Scan patrimoine à l'état 2** (propriétaire posé) ; projet ouvre le projet.
2. La résolution réutilise la fonction auto-suffisante livrée en RETOURS-6 (`fetchQuery` de Scan patrimoine) — pas une quatrième implémentation.
3. Annonce Radar par la barre : **seulement si trivial** (par IDU, la fiche montre déjà l'annonce rattachée) ; sinon le noter.

## Lot 9 — Dédoublonnages (KO-12, KO-13, KO-15, non-prévus)

1. **Transport mail unique** : une fonction d'envoi, un expéditeur, utilisée par invitation, veille, courrier, Radar. La doctrine « transport unique » redevient vraie ; test qui échoue si un second transport est instancié.
2. **Rattachement adresse → IDU** : une implémentation (`audit.py:162`, `scoreur.py:47,125` avec deux `BAN_URL`, `copilote_v2/outils.py`) → une fonction, un `BAN_URL`, appelée partout.
3. **Ratio de gain d'assemblage** (KO-15) : calculé et arrondi **au backend uniquement** (`assemblage.py:216`) ; `moteurs.tsx:152` affiche la valeur servie.
4. **Commentaires périmés** trouvés par l'audit : corrigés ou supprimés (un commentaire faux est pire qu'aucun).

## Lot 10 — Lever les 22 DOUTE

Pour chaque ligne DOUTE du rapport : **exécuter** (test, appel réel en local, lecture de table) et reclasser en OK ou KO. Un KO réparable en moins de 30 minutes est corrigé dans ce lot avec son test ; les autres sont listés avec estimation. Le rapport `CONNEXIONS-RAPPORT.md` est mis à jour (colonne état) et recommité.

---

## Hors mandat — à trancher par Vic (ne rien faire, juste noter)

- **E3 — adresse exacte et abonnement** : le gating par plan est un stub Phase 0 (`plans.py`). Question : l'essai 48 h voit-il l'adresse exacte ? Si oui, rien à faire aujourd'hui ; si non, c'est le chantier « wave-adresses ».
- **O2 — multi-sièges** : mono-siège par conception (`sieges` = 1, CGV art. 3). À rouvrir avec la grille multi-licences.

---

## Compte-rendu attendu (par session)

Par lot : fait / constat / reste, avec le test ajouté pour chaque KO. Attendus nommés : Lot 1 résultat de la recette 3 parcelles × 5 exports · Lot 2 endpoints v1 encore joignables · Lot 4 quel système Courrier est gardé, et nombre de courriers non rattachés après backfill · Lot 6 ce qu'il faudrait pour l'agent de nouvelle version · Lot 10 tableau des 22 DOUTE reclassés. Commit par CC. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff fix/connexions-2
```
