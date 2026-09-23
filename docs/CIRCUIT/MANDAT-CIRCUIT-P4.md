# MANDAT CIRCUIT-P4 — La page Données, simple

Date : 23/09/2026 · Modèle : Opus
Branche : `feat/circuit-p4` depuis `main` · Worktree : `~/Desktop/labuse-p4` · Ports : API 8165 · Vite 5365
Maquette de référence : `docs/CIRCUIT/maquette-donnees-v9.html` (à déposer par Vic ; les chiffres y sont illustratifs, seule la structure compte)
Livrables : `docs/CIRCUIT/RAPPORT-CIRCUIT-P4.md`, `docs/CIRCUIT/captures/p4/` (avant/après par onglet)

## Étape 0
`pwd`, branche, `git status` propre, `.env` copié, ports libres. Sinon STOP. Pas de merge. Un commit par lot. Aucun changement au moteur, à la pompe, aux verrous, au registre : ce mandat touche l'affichage, les états et une règle de dépendance.

## Ce qui change, en une phrase
La page répond à quatre questions, une par onglet : **qu'est-ce que je dois cliquer ? · où en est chaque source ? · comment ça coule ? · qu'est-ce qui s'est passé ?** Tout ce qui ne répond pas à sa question sort de l'onglet.

## Lot 0 — la sonde marche en local
Sur le Mac, 84/84 sondes échouent en `CERTIFICATE_VERIFY_FAILED`. Faire pointer la sonde sur le bundle `certifi` (ou `SSL_CERT_FILE` dans `.env`), documenter dans `docs/CIRCUIT/VERROUS.md`. Preuve : `labuse sonde` (ou le job) en local → 0 erreur SSL. Sans ce lot, la page mentira toujours en local.

## Lot 1 — trois états pour une source
Une source servie a exactement un état, calculé par une fonction unique (`etat_source()` existante, simplifiée) :
- **À jour** — un contrôle (sonde ou agent) l'a confirmé dans sa cadence, ou une manuelle est dans son échéance.
- **Nouvelle version** / **Échue** (manuelle) — une action est attendue.
- **Jamais vérifiée** — aucun contrôle réussi ; gris, jamais jaune.
Plus un signal technique **Sonde en panne** (rouge) après 3 échecs non-SSL consécutifs.
« À regarder » disparaît. Test : la somme des états = le nombre de sources en vitrine, sur la base réelle.
Constat du 23/09 (lecture seule CC) : dans `etat_reservoir()` (`circuit_etats.py:235-274`), la règle 10 « `dernier_statut == injoignable` → ambre » produit 80 des 87 « à regarder » ; c'est elle qui disparaît. Un échec de sonde n'est pas un état de la source : il devient « Sonde en panne » seulement après 3 nuits d'échec non-SSL, sinon la source garde son dernier état confirmé. Les vrais restes attendus après le lot 0 : ~8 « jamais vérifiée » (one-shot / job sur clic), Radar échue, 1 fuite `exports_recette` (robinet), 46 robinets non couverts — à lister dans le rapport, pas à corriger ici.

## Lot 2 — onglet À faire (par défaut)
Une liste ordonnée calculée côté serveur (`circuit_resume.py`), vide si rien (« Rien à faire » + la phrase de contexte). Cinq types de lignes seulement, chacune avec un verbe et UN bouton :
- **Injecter** — source en nouvelle version (vanne existante).
- **Déposer** — manuelle échue (dépôt de fichier existant).
- **Calculer** — des sources injectées OU des règles PLU modifiées depuis le run servi, avec la liste et ce que ça touche (lot 4).
- **Basculer** — candidat prêt ; bouton grisé avec la raison tant que la note n'est pas lue ou qu'un Calculer le précède.
- **Décider** — verrou cassé, lien vers son détail.
Le nombre dans l'onglet = le nombre de lignes. Les boutons « Vérifier maintenant » et « Envoyer les agents » restent en haut à droite ; les bandeaux (agents 0 €, contrôle terminé, sens inverse, lien Destinations) disparaissent de cette vue — voir lot 5.

## Lot 3 — onglet Sources
Un tableau, une ligne par source servie : nom + famille · millésime servi (+ date d'injection) · version chez le producteur (+ date de publication) · dernier contrôle (date + sonde/agent) · état · bouton seulement si une action existe. Horloge ⟳ sur les automatiques. Recherche. Segment **Vitrine / Hors vitrine** : les hors vitrine (alias, retirées, internes, à obtenir, à demander, hubs) avec leur statut, **la raison en français** et la date de la décision — rien n'y est masqué.
Clic sur une ligne → page de détail (existante, à compléter) : les trois dates, « Ce qu'elle alimente » par catégorie (couches, fiche parcelle, fiche commune, outils, exports, scoring) lu du registre, « Si une nouvelle version entre : recalcul de X / rien », « Comment elle entre » (ingestion, sonde, filtre, garde 974), historique. Le détail de `plu_destinations` (calibrage par commune) vit ici, plus en bas du Circuit.

## Lot 4 — la règle : injection → recalcul
Le registre sait quelles données lit chaque moteur (`circuit.json`, `moteurs.csv`). En déduire, pour chaque source, si elle nourrit le résiduel, le scoring, ou aucun. Après toute injection réussie, et après tout commit qui change `config/plu_destinations/*.yaml`, une ligne **Calculer** apparaît dans À faire avec la liste des changements depuis le run servi. Un test construit le cas : injecter une source qui nourrit le scoring → la ligne apparaît ; une source qui ne nourrit rien → rien.

## Lot 5 — Circuit et Journal
Circuit : le dessin existant, sans aucun bouton ; le champ « Sens inverse » vit ici ; clic = détail. Journal : inchangé sur le fond, vérifier que chaque passage est une ligne dépliable avec des noms d'écran (déjà fait en P2) et que les gestes de ce mandat y écrivent une ligne avec « par ».

## Lot 6 — tests et recette
Tests : états (lot 1), résumé (lot 2 : chaque type de ligne construit puis vide), dépendance (lot 4), compteur de l'onglet = lignes. `pytest tests/` (rapporter), `tsc -b`, `vite build`, verrous verts.
Recette Playwright sur la base réelle, **trois preuves par geste** (endpoint appelé, ligne de journal, écran qui change) : Injecter une source de test → Calculer apparaît → Vérifier maintenant → bouton Basculer grisé avec raison → filtre Hors vitrine → détail Sitadel → sens inverse depuis Circuit. Captures avant/après par onglet.

## Hors mandat
Moteur, pompe, manifeste, verrous, registre (lecture seule) · Pilotage et autres pages · agents (crédit) · merge · `residuel-serve` · toute bascule.

## Rapport
Ce qui a changé par onglet, la fonction d'état et sa règle, la règle de dépendance et ses tests, ce qui reste en jaune ou rouge sur la base réelle après le lot 0 et pourquoi, commandes et résultats.
