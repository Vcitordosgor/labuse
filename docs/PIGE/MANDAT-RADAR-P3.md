# MANDAT — RADAR P3 : L'ÉCRAN CLIENT
Régime AUTONOME. Commits par lot (C1→C4). RÈGLES COMMUNES. Findings RD-301→.
Suite de RADAR V0 (P0 socle, P2 rattachement) et RADAR P1 (vision, extraction, intake admin) — tous livrés et mergés. **Relis les doctrines du §2 de docs/PIGE/MANDAT-RADAR-V0.md avant de commencer.** Réutilise ce qui existe (portails.py, tables.py, rattachement.py, pige/api.py), ne le réécris pas.

## CE QU'ON CONSTRUIT
L'outil « Radar » côté client : ce que voit un abonné Intégral. C'est la première fois que le travail de collecte de Vic devient visible pour un client — la qualité de cet écran décide de la valeur perçue de tout le chantier.

## RAPPEL DE LA LIGNE ROUGE
On affiche **des faits et un lien**. Jamais le titre de l'annonce, jamais son texte, jamais ses photos, jamais les coordonnées de l'annonceur. Aucune capture n'est servie par le web. Si un doute se présente en cours de route, la réponse est non.

## C1 — LES DONNÉES CÔTÉ CLIENT
Endpoints de lecture pour un compte client (pas admin) : liste filtrée des biens, détail d'un bien, et l'enregistrement d'un clic sortant.
- Un client ne voit que des biens **validés** (les brouillons de l'intake admin n'existent pas pour lui).
- Les statuts visibles par défaut : `active` et `en_vente_longue`. Les autres (`a_reverifier`, `retiree`, `vendue`, `retiree_sans_vente`) sont accessibles en filtre, pas montrés d'emblée.
- Chaque bien renvoyé porte : ses faits avec leurs étiquettes Sourcé/Estimé/Absent, son historique de prix, son statut, son rattachement (idu + niveau + confiance) ou son absence de rattachement, le portail et l'URL sortante, ses dates.
- **Chaque clic sortant est logué dans `pige_clics`** (client, bien, date) — c'est ce qui alimentera « usage par outil » du dashboard Produit.
- Pagination et tri côté serveur (le volume grandira).

## C2 — L'ÉCRAN : FILTRES + CARTE + LISTING
Reprend le patron des outils existants — **filtres à gauche, carte à droite** — PLUS un listing. Ne crée pas une carte parallèle : branche-toi sur la carte de l'app.

**Filtres** : commune, type de bien (terrain / maison / appartement / immeuble), fourchette de prix, fourchette de surface (habitable et terrain), particulier ou professionnel, statut, période de parution, et « rattaché à une parcelle » oui/non/indifférent. Chaque filtre affiche le nombre de résultats.

**Carte** : **uniquement les biens rattachés**. Pins différenciés par statut. Un bien non rattaché n'apparaît JAMAIS sur la carte — pas de pin au centre de la commune, pas d'approximation.

**Listing** : **tous les biens**, rattachés ou non, avec une **pastille distinguant les deux cas**. Propose un libellé court et clair (« sur la carte » / « non localisé », ou mieux si tu trouves) — dis ton choix au rapport.
Triable : plus récentes, prix croissant/décroissant, ancienneté, baisses de prix.

**Le clic dans le listing** (décision Vic, à respecter à la lettre) :
- bien **rattaché** → on va sur la carte, à sa parcelle, et sa fiche s'ouvre ;
- bien **non rattaché** → on part **directement sur le portail source**, nouvel onglet, `rel="noopener noreferrer"` — et le clic est logué comme un clic sortant.

## C3 — LA FICHE D'UN BIEN
Pour un bien rattaché, la fiche montre : les faits avec leurs étiquettes, l'**historique de prix** (mini-sparkline si le volume s'y prête, sinon la liste des changements datés), le statut, la parcelle rattachée avec son niveau de confiance — et le **gros bouton « Voir l'annonce sur [portail] »**, seul chemin vers la source.
Un bien en **Estimé** (1 à 3 parcelles candidates) affiche toutes ses candidates avec leur confiance : jamais un pin unique faussement sûr.
Bouton client **« Signaler : annonce retirée / erreur »** → événement `pige.signalement_client` + remontée en tête de la file de re-vérification admin. Le signalement ne change JAMAIS le statut tout seul (anti-abus) — il alerte Vic.

**Sur la fiche parcelle existante** : si un bien Radar est rattaché à cette parcelle, il s'y voit — le fait, le statut, et le lien. Discret, cohérent avec le reste de la fiche (DA-FICHE-v6).

## C4 — INTÉGRATION ET RECETTE
- L'outil rejoint le menu Outils (menu aplati, pas de catégorie), DA LABUSE, couleurs depuis la source unique (config/brand_colors.json, cf. K4). Le mauve reste réservé à l'IA — il n'a rien à faire dans l'écran client du Radar.
- Recette avec un jeu de données de test représentatif (biens rattachés Sourcé, rattachés Estimé, non rattachés, avec et sans baisse de prix, plusieurs statuts, plusieurs communes) — objets préfixés [RADAR-TEST], purgés en fin, vérifié SQL.
- Cas à prouver : filtre qui vide la carte mais garde le listing · clic rattaché → carte · clic non rattaché → portail (nouvel onglet, clic logué) · fiche Estimé avec ses candidates · signalement client · bien affiché sur sa fiche parcelle · liste vide (message honnête, pas un écran blanc).
- **Mobile (390)** : le patron filtres/carte/listing doit rester utilisable sur téléphone. Dis comment tu l'as résolu.

## FIN
Critères : aucun contenu d'annonce affiché (faits + lien uniquement) · carte = rattachés seulement, listing = tout avec pastille · clic conforme à C2 dans les deux cas · clics logués dans pige_clics · signalement sans changement de statut · Radar toujours hors scoring · le test anti-requêtes-portails de P0 reste vert · couleurs depuis la source unique · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree) · [RADAR-TEST] purgés (vérifié SQL).
Captures 390 et 1440 de l'écran, de la fiche et de la fiche parcelle, au rapport, avec leur nombre annoncé. Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff feat/radar-p3). Tu ne merges pas.
