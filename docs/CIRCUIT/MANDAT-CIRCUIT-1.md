# MANDAT CIRCUIT-1 — Le circuit qui agit

Branche : `feat/circuit-1`, créée depuis `main` à jour, dans le worktree `~/Desktop/labuse-audit`
Dossier : `docs/CIRCUIT/` (ce mandat, la maquette de référence `maquette-circuit-v5.html`, le compte-rendu)
Référence : `docs/CIRCUIT/INVENTAIRE-RAPPORT.md` et `docs/CIRCUIT/inventaire/*` (CIRCUIT-0, 05/09/2026). Tout ce que ce mandat affirme sur l'existant vient de là ; si le code contredit l'inventaire, le code gagne et l'écart est noté au compte-rendu.
Objectif : que chaque chiffre de LABUSE soit défini une fois, calculé par un seul moteur, servi avec sa provenance, contrôlé chaque nuit, et que Vic voie tout ça sur un seul écran où il injecte, calcule, bascule et envoie des agents.

Vocabulaire (celui de CIRCUIT-0) : **réservoir** = source amont · **pompe** = les moteurs · **robinet** = un endroit qui affiche un chiffre · **chiffre** = une valeur affichée · **tampon** = la provenance portée par une valeur servie · **fuite** = un robinet qui calcule hors moteur · **eau ancienne** = valeur servie calculée sur une version plus vieille que celle du réservoir.

---

## Décisions de Vic qui gouvernent ce mandat (05/09/2026)

1. **Périmètre = tout chiffre servi dans l'app**, pas seulement ceux servis à plusieurs endroits.
2. **Une seule page qui agit** : le Circuit absorbe l'onglet Mise à jour. Vanne sur un réservoir = Injecter ; pompe = Calculer (candidat, jamais servi tout seul) / Basculer (après lecture de la note de version) / Revenir.
3. **Les crons mensuels restent automatiques** (Sitadel, DPE, SIRENE, GPU) ; le dessin les montre avec une horloge. La règle « rien n'entre sans clic humain » vaut pour la vanne et pour les nouvelles versions proposées par la sentinelle.
4. **Part de zonage : la surface partout.** Le compte de parcelles par zone survit uniquement dans les filtres, sous un autre nom, jamais affiché comme une « part ».
5. **Résiduel : une seule bascule déplace tout** (arbitrage Fable sur « fais au plus malin », détail au lot 3) : le résiduel garde sa propre chaîne de calcul et sa nomenclature, mais il est SERVI par le même manifeste que le scoring — un geste, un journal, un retour arrière.
6. **La vanne Injecter s'étend à toutes les sources qui ont un job d'ingestion.** Les dépôts manuels reçoivent une vanne « déposer un fichier » ; les sources interrogées en direct n'ont pas de vanne et le disent.
7. **score_e passe sur le moteur neuf live** (comme comparateur, fiche, carte depuis RETOURS-11F) : c'est un correctif, pas un choix.
8. **Agents à la demande** : un réservoir, une sélection, ou tous ; jamais en cron par défaut.
9. **Mode Traçage** dans le même mandat (lot 7).

---

## Autonomie — le mandat se déroule jusqu'au bout sans revenir vers Vic

- **Aucune question à Vic en cours de route.** Devant un doute, CC prend l'option la plus sûre (celle qui ne change rien de servi, ou qui est réversible), l'écrit dans le chapitre « Décisions prises en autonomie » du compte-rendu avec la raison et l'alternative écartée, et continue. Vic relit ce chapitre à la fin, pas pendant.
- **Ce qui ne peut pas être fait est sauté, pas attendu** : une ligne « non fait, raison, ce qu'il faudrait » au compte-rendu, et le lot suivant démarre.
- **Le VPS se lit tout seul** : CC a le droit d'exécuter sur `labuse-vps`, en lecture seule, exactement ces commandes — `ls -la /etc/cron.d/`, `cat /etc/cron.d/*`, `crontab -l`, `ls /opt/labuse/state/jobs/`, `cat /opt/labuse/state/jobs/*.json` — et rien d'autre (aucune écriture, aucun redémarrage, aucun déploiement). Si le ssh échoue, hypothèse de travail : le wrapper est posé (CRON-1/2 via deploy.sh), legacy possible en résidu ; le lot 8 rend cette hypothèse vraie par construction.
- **La branche ne reste jamais rouge** : si un lot casse la suite de tests et que la session ne parvient pas à la remettre verte, le lot est annulé (`git revert` de ses commits, jamais un `reset`), noté au compte-rendu, et le mandat continue avec le lot suivant.
- **Rien n'est perdu entre deux sessions** : `git push origin feat/circuit-1` à la fin de chaque lot. Le compte-rendu est le point de reprise : chaque session nouvelle commence par le lire et reprend au premier lot non clos, sans que Vic ait autre chose à taper que « continue CIRCUIT-1 ».
- **Fin de mandat** : le compte-rendu se clôt par la liste des gestes qui restent à Vic (merge, bascule en production, purge des runs morts, validation des cadences) — rien d'autre n'attend de lui.

---

## Étape 0 — avant toute écriture

1. `pwd` = `~/Desktop/labuse-audit`, arbre propre. Sinon stop et signale.
2. `git fetch && git checkout main && git pull --ff-only && git checkout -b feat/circuit-1`.
3. **`fix/retours-12` mergée ou pas, on ne s'arrête pas** : si elle ne l'est pas, les sources 93-95 (EDF, TCSP, Réunion Express) sont lues telles qu'elles existent en base locale et déclarées au registre à partir de là ; le compte-rendu signale que leur seed vit sur `fix/retours-12` et que le merge les alignera.
4. Suite backend verte au départ (`pytest`), nombre de tests noté. Aucun lot ne se termine avec moins de tests verts qu'au départ.
5. Copier `maquette-circuit-v5.html` dans `docs/CIRCUIT/` et la commiter avec ce mandat (« CIRCUIT-1 — mandat + maquette de référence »).

---

## Règles

1. **Un chiffre = un id = une définition = une fonction.** Deux définitions légitimes = deux ids, deux libellés (jamais le même mot pour deux calculs).
2. **Un robinet ne calcule pas.** Il demande au registre. Toute SQL de calcul dans un endpoint, un template, un builder PDF ou un composant front est une fuite, même sans divergence mesurée.
3. **Rien de servi ne change sans bascule** pour les chiffres liés au run. Les chiffres lus en direct peuvent changer par correctif, mais chaque correctif de valeur servie est listé au compte-rendu avec avant/après sur Saint-Paul.
4. **Aucune table supprimée** : on cesse de lire, on marque obsolète. Toute migration a un backfill et un test.
5. **Chaque fuite corrigée reçoit le test qui l'aurait attrapée** (la première : Saint-Paul zone A = 35,8 %, zone N = 47,2 %, identiques sur tous les robinets).
6. **Rien n'entre sans clic humain** par la vanne ; **rien n'est servi sans bascule** par la pompe ; **un agent ne télécharge ni n'ingère jamais**.
7. **Preuve avant affirmation** : le compte-rendu cite fichier:ligne et, pour tout chiffre, la mesure sur les témoins de CIRCUIT-0 (24 communes, 50 parcelles golden, 5 clés zone / propriétaire / annonce documentées dans `mesure_fuites.py`).
8. **Recette dans un navigateur sur la base réelle** avant de déclarer la page finie : vanne, calcul, bascule, retour, agent — avec capture avant/après (règle RETOURS-13 : un travail visuel n'est fait qu'avec la capture).
9. **Une branche, un commit par lot** (`CIRCUIT-1 lot N — …`), poussé à chaque fin de lot. Le mandat se joue d'une traite ; si une session s'arrête, la suivante reprend seule au premier lot non clos (voir « Autonomie »). Rien n'est mergé : Vic merge depuis `labuse-merge` à la fin.

Ordre des lots : 0 (bloquants) → 1 (registre) → 2 (rebranchements) → 3 (pompe) → 4 (sonde) → 5 (la page) → 6 (agents) → 7 (traçage) → 8 (horloges). Points de coupure naturels si une session doit s'arrêter : après le 2, après le 4, après le 5.

---

## Lot 0 — Lever ce qui bloque

- 0.1 **Le jeu de crons réellement posé sur le VPS.** CC le lit lui-même (commandes autorisées dans « Autonomie »), enregistre la sortie brute dans `docs/CIRCUIT/VPS-CRONS-05-09.txt` et en tire la vérité pour le lot 8. Si le ssh échoue : hypothèse « wrapper posé + legacy résiduel possible », notée, et le lot 8 pose la garde qui la rend vraie.
- 0.2 **Compteur de sources unique** : `flux.py:198` et `flux.py:199-201` passent par `WHERE_AFFICHEES` et par un compte des vraies sondes (`api`/`page`/`entete`/`temoin`, actives) ; `dashboard.py:893` passe `affichage_desactive` à `est_affichee`. Test : les trois écrans (page Sources client, Catalogue admin, Circuit) affichent le même nombre. C'est le premier rebranchement, fait ici parce que tout le reste compte des sources.
- 0.3 **Le tampon DPE qui ment** : `dpe.py:243` n'écrit `last_sync_at` que si au moins une commune a été traitée ; le saut des communes peuplées devient un choix explicite (`--force` documenté, cadence de rafraîchissement dans le job) ; test : 0 commune traitée → `last_sync_at` inchangé.

---

## Lot 1 — Le registre

Module `src/labuse/registre/`. C'est le socle ; tout le reste s'y branche.

- 1.1 **Déclaration en code** : `registre/chiffres.py` déclare chaque chiffre — `id` (snake_case, ceux de `chiffres.csv` conservés tels quels), `libelle` (celui de l'écran), `unite`, `niveau` (`parcelle` · `commune` · `zone` · `proprietaire` · `annonce` · `global`), `definition` (une phrase en français, dénominateur et fenêtre compris), `moteur` (id de `moteurs.csv`), `fonction` (référence Python appelable), `reservoirs` (ids de `data_sources`), `portee` (`run` = ne change qu'à la bascule · `live` = change à l'injection), `version_def` (date). Seed : les 88 ids de `chiffres.csv`, puis la longue traîne (1.3).
- 1.2 **Déclaration des robinets** : `registre/robinets.py` — les 122 ids de `robinets.csv` avec `categorie`, `parent`, `route`, `mode_rendu`, et la liste des chiffres qu'ils servent. Le graphe réservoir → chiffre → robinet est dérivé, jamais saisi deux fois.
- 1.3 **La longue traîne** : les 67 robinets à 0 chiffre dans l'inventaire sont parcourus un par un ; chaque nombre affiché reçoit un id (CIRCUIT-0 estime 150-250 chiffres supplémentaires). Ce qui n'est pas un chiffre (tuiles, géométries, textes) est marqué `hors registre` avec la raison, dans `robinets.py`.
- 1.4 **Le tampon** : toute valeur servie par le registre est un objet `Valeur{valeur, chiffre_id, version_def, run, reservoirs:{id: millesime}, calcule_le}`. Les endpoints JSON servent la valeur seule par défaut et le tampon complet avec `?trace=1` (admin seulement) ; les builders PDF et mails reçoivent l'objet et n'utilisent que `.valeur`. Test : `?trace=1` sur `/parcels/{idu}` et `/communes/{c}/contexte` renvoie un tampon pour chaque champ numérique déclaré.
- 1.5 **Miroir en base** : `labuse registre sync` écrit `registre_chiffres`, `registre_robinets`, `registre_aretes` depuis le code (le code est la vérité, la base sert la page et la sonde). Test : `sync` est idempotent ; `valide_circuit.py` de CIRCUIT-0 passe sur l'export du miroir.
- 1.6 **Couverture** : un test parcourt chaque endpoint de `robinets.py` avec `?trace=1` sur un témoin et échoue sur tout champ numérique sans `chiffre_id`, hors liste d'exceptions justifiée dans le fichier de test. C'est la garde qui interdit qu'un nouveau chiffre naisse hors registre.
- 1.7 **Réservoirs** : `seed_sources.py` reçoit deux champs déclarés pour chaque source — `mode_remplissage` (énum de CIRCUIT-0, `en_direct` compris) et `cadence_attendue` (les 71 « aucune » sont renseignées par CC d'après le rythme connu du producteur — annuel pour un millésime, mensuel pour un flux, à défaut 365 jours — marquées `proposee`, appliquées tout de suite ; la liste est livrée dans `CADENCES-PROPOSEES.md` et Vic corrige plus tard depuis la page, pas pendant le mandat).

Compte-rendu du lot : nombre de chiffres déclarés, par `portee`, par moteur ; nombre de robinets couverts ; la liste des exceptions de 1.6.

---

## Lot 2 — Les rebranchements

Chaque point : correction, test qui l'aurait attrapée, mesure avant/après sur Saint-Paul.

- 2.1 **Zonage** : la part de zonage est la part de SURFACE (`_foncier_commune`, `app.py:1908-1955`) partout, sous les ids `part_zone_U_pct` / `AU` / `A` / `N`. Le compte de parcelles de `/zones-plu` (`app.py:2436`) devient `parcelles_par_zone_n`, un nombre, libellé « parcelles en zone … », réservé aux filtres ; le mot « part » n'y apparaît plus. Test : pour les 24 communes, chaque robinet qui affiche une part de zonage renvoie la valeur surface de `fuites_mesurees.csv` (Saint-Paul A 35,8 %, N 47,2 %).
- 2.2 **score_e** : `score_e.py:59` lit `neuf_vefa_commune` (moteur live `marche_communes`) au lieu du précalcul `dvf_prix_sortie_neuf` ; le précalcul est marqué obsolète, plus jamais lu (grep vide). Prend effet au prochain run candidat (portée `run`). Test : le neuf utilisé par score_e sur Saint-Paul = 5 003 €/m² (celui du comparateur).
- 2.3 **Division d'or** : les quatre lecteurs (`app.py:1573`, `app.py:2692-2696`, `division_review.py:38`, `verdict_servi.py:40`) lisent le run du manifeste (lot 3) ; `division_or` est recalculé pour le label candidat par Calculer. Tant qu'un run n'a pas ses candidats, la fiche affiche « divisibilité non recalculée pour ce run » plutôt qu'une valeur d'un run mort. Test : aucune ligne `q_v10_m129` servie.
- 2.4 **Les 9 calculs au navigateur** deviennent des chiffres du registre servis par le serveur : autres logés gratuitement (`ContextePanel.tsx:526`), charge foncière bornée (`constructibilite.tsx:137`), kWc et MWh/an (`ProspectionSolaire.tsx:325-326`), % propriétaires (`MarcheSecteurBlock.tsx:16`), % ZAN (`blocB.tsx:358`), % décidées (`ProjetsPanel.tsx:53`), heures restantes (`Licences.tsx:26`), n_vigilances, et le 9e listé par l'agent front de CIRCUIT-0. Les 17 dérivations légères restent au front et sont listées comme telles dans `robinets.py` (formatage, pas calcul).
- 2.5 **Les 54 `sql_propre`** : chacune est soit rebranchée sur un moteur existant (quand un autre robinet calcule déjà le même chiffre), soit extraite dans `registre/moteurs/*.py` sous l'id du chiffre (quand elle est l'unique calcul). Aucun endpoint ne garde de SQL de calcul ; les SQL de simple lecture (passe-plat) sont taguées `passe_plat` dans le registre.
- 2.6 **Copilote** : les 10 outils passent par le registre (déjà vrai pour 9 par point unique, à formaliser par l'id) ; garde formelle sur `copilote-general` : toute réponse libre contenant un nombre non issu d'un outil est reformulée sans le nombre (test adversarial : 10 questions pièges, 0 nombre inventé).
- 2.7 **Caches** : `zone_isochrone_cache` reçoit un TTL (30 jours) et une purge à la bascule ; `fiche-commune-cache` garde ses 24 h mais son tampon devient un vrai tampon de registre (1.4).

Compte-rendu : tableau des ~15 rebranchements, avant/après, test associé ; nombre de `sql_propre` restantes = 0 ou liste justifiée.

---

## Lot 3 — La pompe unifiée

- 3.1 **Le manifeste de service** : `config/served_manifest.json` = `{scoring_run, residuel_run_seq, mvt_run, division_run, promoted_at, par, precedent: {…}}`, écrit de façon atomique (fichier temporaire puis `rename`). `runs.current()` lit le manifeste ; `served_run.txt`, `run_precedent.txt`, `mvt_meta.run_label` et `residuel_runs.is_served` deviennent des vues dérivées du manifeste (écrites par lui, jamais par un autre chemin) le temps de la transition, puis marqués obsolètes. Test : aucun module n'écrit un pointeur ailleurs que par `bascule_flux` ; les quatre pointeurs sont toujours égaux au manifeste.
- 3.2 **Le résiduel dans le manifeste** (« au plus malin ») : sa chaîne de calcul reste séparée (`residuel_runs`, nomenclature propre) ; Calculer produit un candidat résiduel seulement si ses entrées ont changé (PLU/GPU, cadastre, CoSIA — d'après les tampons), sinon le manifeste candidat reporte le résiduel servi. Basculer déplace scoring, résiduel, mvt et division en un seul écrit. Revenir restaure le manifeste précédent entier. Une bascule scoring ne peut plus laisser le résiduel derrière.
- 3.3 **Calculer** = `labuse pompe calculer --label L` : cascade + scoring (`flux-run`), score_e sur le neuf live, division_or pour L, candidat résiduel si nécessaire, puis **préparation des tables servies pour L** (`build-mvt` sur le label candidat, tables run-scopées construites AVANT la bascule) et `rapport_candidat`. Asynchrone, progression `run_progress`, un seul calcul à la fois, **identité de qui l'a lancé** dans le journal. La **note de version** est produite par le registre : réservoirs et millésimes utilisés (tampons), chiffres recalculés, sorties/entrées de Priorité expliquées, écart de classement.
- 3.4 **Basculer** = écrit du manifeste, purge des caches, `runs.invalidate()`, journal `run_bascule_journal` (existant, complété par le manifeste), notification, puis **contrôle après bascule** (lot 4) lancé automatiquement. Comme les tables sont préparées à 3.3, la bascule est instantanée et la garde de cohérence passe à 6/6, pas 5/6 « assumé ».
- 3.5 **Purge des runs morts** : bouton sur la page (lot 5) qui appelle `labuse purge-runs-morts --apply` avec confirmation ; jamais automatique.
- 3.6 **Événements** : Injecter, Calculer, Basculer, Revenir, purge et agents écrivent une ligne `circuit_journal(ts, geste, cible, par, resultat, details)` — le « qui » manquant pour Injecter et Calculer est comblé.

---

## Lot 4 — La sonde de cohérence, « Vérifier que tout coule »

- 4.1 Job `coherence-robinets` (wrapper, 07:15 chaque nuit, après chaque bascule, et sur bouton) : pour chaque chiffre servi par ≥ 2 robinets, appelle chaque robinet par son vrai chemin (`?trace=1`, builders PDF en collecte seule, outils Copilote) sur les témoins et compare à la fonction du registre. Écarts dans `circuit_ecarts(chiffre_id, cle, robinet_a, valeur_a, robinet_b, valeur_b, cause, depuis, statut)`. Seed et méthode : `scripts/inventaire/mesure_fuites.py`.
- 4.2 **Eau ancienne** par tampon : toute valeur dont le tampon porte un run ≠ manifeste, ou un millésime de réservoir plus vieux que celui de `data_sources`, va dans `circuit_eau_ancienne(chiffre_id, robinet, tampon, attendu, mecanisme)`. Les six familles de CIRCUIT-0 sont le jeu de test : après les lots 2-3, il doit en rester zéro hors « solaire gelé, étiqueté ».
- 4.3 **Verdict** : une ligne par passage (`circuit_controles`) : fuites ouvertes, eau ancienne, robinets couverts / non couverts, durée. La page lit la dernière ligne.
- 4.4 Un écart soldé par un correctif garde sa ligne avec `statut='solde'` et le commit — c'est l'historique que Vic veut voir.

---

## Lot 5 — La page Circuit

Référence exacte : `docs/CIRCUIT/maquette-circuit-v5.html` (structure, états, couleurs, fiche du bas, pastilles, recherche, groupes repliables, pompe collante). Elle remplace `Flux.tsx` (fourmilière) et l'onglet Mise à jour ; `MiseAJour.tsx` disparaît, ses trois endpoints sont réutilisés.

- 5.1 **Endpoint** `GET /admin/circuit` : la structure de `circuit.json` calculée en direct — réservoirs (`data_sources` + `source_veille` + mode + cadence + horloge + dernier rapport d'agent), pompe (manifeste, candidat, eau en attente, moteurs et pointeurs, horloges qui touchent l'eau), robinets et chiffres (miroir du registre), arêtes, fuites (`circuit_ecarts` ouvertes), eau ancienne, dernier contrôle, compteurs du bandeau. Un seul appel, < 1 s sur la base réelle (test de perf).
- 5.2 **Front** `frontend/src/components/admin/Circuit.tsx` conforme à la maquette : bandeau « Tout coule, sauf : » avec pastilles cliquables (fuites, hors moteur, à purger, horloge qui ment, réservoir plein, jamais vérifiés, pompe) ; trois colonnes réservoirs / pompe / robinets, tuyaux SVG, chemin allumé au clic, fuites en rouge autour de la pompe ; fiche du bas à trois colonnes ; recherche ; groupes repliables ; pompe collante. Règles DA : survol vert opaque contenu inversé, mauve réservé aux agents (IA), « Fiche → » en jaune, aucun camaïeu.
- 5.3 **La vanne** : `sources_ingestion.yaml` étendu à toute source dont `mode_remplissage` ∈ {`job_sur_clic`, `cron_mensuel`, `one_shot`} et qui a un job ou un script identifiable (52 + 4 + 3 ; ceux sans script sont listés au compte-rendu avec la raison). `depot_manuel` (5) : vanne « déposer un fichier » vers le chemin de dépôt existant. `en_direct` (4) : pas de vanne, mention « interrogée en direct ». `absente` : réservoir vide, motif. L'injection reste détachée, journalisée avec « qui », et l'eau attend dans la pompe (les robinets à portée `run` passent en « eau ancienne » jusqu'à la bascule).
- 5.4 **La pompe** : Faire tourner (3.3), Basculer (3.4, bouton actif seulement quand la note de version a été ouverte), Revenir, Purger les runs morts.
- 5.5 **Vérifier que tout coule** (4.1) et **Envoyer les agents** (lot 6) depuis le bandeau ; sur un réservoir : Envoyer un agent, Ouvrir la vanne.
- 5.6 **Page Sources client** inchangée dans sa doctrine (à jour / pas à jour, jamais « retard ») mais alimentée par les mêmes objets que le Circuit.
- 5.7 **Recette navigateur sur la base réelle LOCALE** (jamais le VPS) : injecter une source à job court (BODACC), calculer un candidat, basculer, vérifier, revenir — captures avant/après de chaque geste dans `docs/CIRCUIT/RECETTE-CIRCUIT-1/`, prises par CC avec le Chrome local (comme au Grand Balayage). La base locale est remise dans son état de départ à la fin (retour arrière joué).

---

## Lot 6 — Les agents

- 6.1 `labuse agent source <id>` · `--ids a,b,c` · `--tous` : un appel Claude par réservoir via la façade `ai/core.complete()`, surface `agent_source` ajoutée au registre `SURFACES` de `ai_models.py` (modèle `MODEL_REASONING` par défaut, override env), **avec l'outil de recherche web de l'API** ; entrée = fiche de recherche (`agents_fiches.csv` + `url_producteur_connue` + format du millésime + dernier vu par la sonde) ; sortie JSON strict : `{verdict: a_jour|nouvelle|introuvable|vide, version_trouvee, date_publication, preuve:{url, extrait}, cherche:[…], sonde_proposee:{methode, url}|null, page_js: oui|non|inconnu}`.
- 6.2 **Anti-invention** : `a_jour` et `nouvelle` exigent un `extrait` daté réellement présent dans une page lue par l'outil ; sinon le verdict est forcé à `introuvable` avec la raison. Un agent ne télécharge rien, n'ingère rien, n'écrit que `source_agent_rapports` et, sur verdict `nouvelle`, `source_veille.dernier_vu/dernier_statut` (ce qui fait apparaître la vanne).
- 6.3 **Sonde proposée** : bouton « inscrire dans la sonde de nuit » (clic humain) qui crée ou corrige la ligne `source_veille` (méthode et URL proposées, testées par un appel réel avant écriture — règle SENTINELLE-2).
- 6.4 **Exécution** : job détaché, 5 agents en parallèle au plus, progression par réservoir sur la page, coût par agent inscrit au ledger `ia_log` et affiché dans le rapport ; aucun cron par défaut (un job `agents-sources` mensuel existe, désactivé).
- 6.5 **Pages en JavaScript** : hors v1 — l'agent le dit (`page_js: oui`) et la piste Playwright est notée au compte-rendu.
- 6.6 Test : trois agents en dry-run sur des pages fixées (fixtures) donnent les verdicts attendus ; un agent sur une page sans date donne `introuvable`.

---

## Lot 7 — Le mode Traçage

- 7.1 **Serveur** : `?trace=1` (1.4) sur tous les endpoints de `robinets.py` ; réservé au compte admin (403 sinon, test).
- 7.2 **Front** : `frontend/src/lib/format.ts` devient l'unique point de formatage — les ~58 formateurs inline (`ContextePanel.tsx`, `MarcheSecteurBlock.tsx`, `RadarMarche.tsx`, `toLocaleString` admin) migrent vers `format.ts` ; chaque formateur accepte un `chiffre_id` ; quand l'interrupteur Traçage (bandeau, admin seulement) est allumé, le nombre porte une étiquette (id, couleur d'état) et le clic ouvre le tiroir de trace : définition, moteur, run, millésimes, calculé le, et « la même valeur sur chaque surface » (dernières valeurs de la sonde). Éteint : rendu strictement identique au client (test de snapshot avant/après sur la fiche parcelle et la fiche commune).
- 7.3 PDF et mails : hors traçage v1 (le tampon y est disponible côté serveur, pas affiché) — noté.

---

## Lot 8 — Les horloges honnêtes

- 8.1 **Un seul jeu de crons** : le wrapper. `deploy/cron.d/*` (13 lignes legacy) retiré du déploiement et marqué obsolète dans le dépôt ; `deploy.sh` refuse de déployer si `/etc/cron.d/` contient encore un fichier legacy (message qui nomme le fichier) ; BODACC entre dans le wrapper (quotidien, comme legacy) ; `ingest-bdnb` posé ou retiré selon le 974 (absent de l'amont : retiré, noté) ; `copilote-purge` et `sante-endpoints` posés.
- 8.2 **healthz lit le registre des jobs** (`ops.py:23-41` remplacé) : les cadences attendues viennent de `jobs.py`, jamais d'une table à la main.
- 8.3 **Trace de chaque job qui touche l'eau** dans `circuit_journal` (quoi, quand, résultat, lignes touchées), y compris les crons.
- 8.4 **« À vérifier »** : un réservoir dont le dernier contrôle (sonde, agent ou dépôt) est plus vieux que sa `cadence_attendue` passe à l'état « à vérifier » sur la page — c'est la règle qui manquait tant que 71 sources n'avaient pas de cadence.

---

## Livrables

```
docs/CIRCUIT/MANDAT-CIRCUIT-1.md              (ce fichier)
docs/CIRCUIT/maquette-circuit-v5.html         (référence de la page)
docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-1.md        (un chapitre par lot, tenu au fil des sessions)
docs/CIRCUIT/RECETTE-CIRCUIT-1/               (captures avant/après de 5.7)
docs/CIRCUIT/CADENCES-PROPOSEES.md            (1.7, à valider par Vic)
src/labuse/registre/                          (chiffres.py, robinets.py, moteurs/, valeur.py, sync)
config/served_manifest.json · config/sources_ingestion.yaml étendu
migrations : registre_*, circuit_ecarts, circuit_eau_ancienne, circuit_controles, circuit_journal, source_agent_rapports
frontend/src/components/admin/Circuit.tsx · lib/format.ts étendu
tests : couverture du registre (1.6), fuites (2.x), manifeste (3.1), sonde (4.x), page (5.x), agents (6.6), traçage (7.2), crons (8.1)
```

## Définition de fini

- `labuse registre sync` puis `valide_circuit.py` passent ; le test de couverture 1.6 passe sans exception non justifiée.
- Sur les témoins : 0 fuite ouverte hors celles listées avec motif, 0 eau ancienne hors « solaire gelé, étiqueté ».
- Un seul pointeur de service (le manifeste) ; une bascule et un retour joués en recette navigateur avec captures.
- La vanne existe pour toute source à job, la page dit pourquoi pour les autres.
- Un agent réel envoyé sur DEAL PPR et sur Office de l'eau, rapports lus par Vic.
- Traçage allumé : chaque nombre de la fiche parcelle et de la fiche commune a son étiquette ; éteint : rendu identique (snapshot).
- Un seul jeu de crons posé, healthz aligné, DPE ne tamponne plus à vide.
- Suite backend verte, au moins autant de tests qu'au départ, rien mergé, compte-rendu clos avec commit final et liste de ce qui n'a pas pu être fait.

## Ce qui reste à Vic, après la fin

Rien pendant le mandat. Après : lire « Décisions prises en autonomie » et « non fait » au compte-rendu · merger `feat/circuit-1` (et `fix/retours-12` s'il ne l'est pas encore) · déployer · basculer en production et purger les runs morts depuis la page · corriger les cadences proposées qui ne lui conviennent pas, depuis la page. La question « sur quels écrans as-tu lu 18 % et 6 % » n'a plus d'importance : les deux chemins sont unifiés au lot 2.

## Interdits

Pas de merge, pas de push sur `main`, pas de bascule sur la base réelle hors recette 5.7 avec retour arrière immédiat, aucun agent en cron par défaut, aucun téléchargement par un agent, aucune table supprimée, aucun chiffre servi hors registre une fois le lot 2 clos.
