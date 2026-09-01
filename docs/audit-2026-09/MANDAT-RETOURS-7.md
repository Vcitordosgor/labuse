# MANDAT RETOURS-7 — recette du 01/09 (soir)

**Branche : `fix/retours-7`** (depuis `main` après merge de `feat/sentinelle-3`). Bloc commun habituel.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.
**Clôture** : `tsc`, build, tests backend et front, puis **commit sur la branche** avant le compte-rendu. Merge = Vic.

---

## Z1 — Fiche parcelle : les boutons « + CRM » / « + Projet » (régression)

Constat Vic : depuis le sélecteur de colonne ajouté en CONNEXIONS-2 (KO-8), « + CRM » est écrasé en carré étroit et « + Projet » a pris un fond **mauve** — le mauve est réservé à l'IA.

1. **Remettre la disposition d'avant** : deux boutons de largeur égale, côte à côte, style neutre identique (bord `--card-line`, fond `--card`), survol plein vert.
2. Le choix de colonne CRM reste, mais **après** le clic (menu qui s'ouvre), pas dans la forme du bouton.
3. Retirer toute teinte mauve de ces deux boutons.

## Z2 — Copilote, section « Ce qu'il sait faire » : mise en ordre

Constat Vic : brouillon — tuiles et textes désalignés, exemples qui débordent sur deux lignes à des hauteurs différentes.

1. Grille 2 × 2 à **gouttières régulières** (même espace horizontal et vertical), tuiles alignées sur la première ligne de texte.
2. Chaque exemple sur **une ligne**, en raccourcissant : « Combien de parcelles en procédure à Saint-Denis ? » → « Parcelles en procédure à Saint-Denis ? » · « Un argumentaire pour convaincre un propriétaire » → « Un argumentaire pour un propriétaire ».
3. Titre et exemple à interligne constant ; la section a la même marge au-dessus et au-dessous que « Reprendre ».

## Z3 — Menu Outils : descriptions sur une ligne

Quatre descriptions passent sur deux lignes à la largeur du panneau. Textes à poser tels quels :

- Étudier un bien → « Le secteur, puis l'étude complète du bien. »
- Assemblage → « Le potentiel de parcelles voisines réunies. »
- Scan patrimoine → « Ce qu'un propriétaire possède et construit. »
- Courrier propriétaire → « Écrivez au propriétaire, LABUSE envoie. »

Puis `white-space:nowrap` + ellipse sur **toutes** les descriptions. Si une description ne tient toujours pas à la largeur courante, réduire d'un point la taille de police de la ligne de description (pas de retour à la ligne). Signaler au compte-rendu celles qui ont exigé la réduction.

## Z4 — Fiche commune : « contacter » en mauve

Le lien « contacter » de la carte « Mairie & service urbanisme » est mauve. Le passer en **vert** `--mint`. Rebalayer la fiche commune pour tout autre mauve hors IA.

## Z5 — Fiche parcelle : « à proximité »

Vérifier ce que la fiche affiche aujourd'hui en matière d'équipements proches (bloc « Autour de cette parcelle », moteur Étude de zone / BPE). Si les distances aux équipements du quotidien ne sont pas nommées, ajouter une **ligne compacte « À proximité »** : école, pharmacie, médecin ou hôpital, supermarché, arrêt de bus — chacun avec sa distance (m ou min à pied), depuis le moteur BPE déjà branché, **sans nouveau calcul**. Une ligne, pas un bloc. Si le moteur n'expose pas une catégorie, elle est omise, pas inventée.

## Z6 — Fiche parcelle : retirer la carte « Qualité de la mesure »

Dans la section « Ce que LABUSE ne peut pas savoir sur cette parcelle », la carte **« Qualité de la mesure · commune »** (RR intra, base %, audit fold…) est retirée de la fiche : c'est de la métrologie interne, illisible pour un client. Elle reste disponible côté admin si elle y existe. La section garde ses autres cartes ; si elle n'en a plus, le titre disparaît avec.

## Z7 — Inventaire des modèles IA (audit + centralisation)

Vic veut savoir **quel modèle** sert chaque surface IA. Lister **tout appel à un modèle** dans le code (Copilote v1, Copilote v2, recherche NL, synthèse IA de la fiche, argumentaire, courrier, parseur de dépôt agence, digests, tout autre) avec : surface · fichier:ligne · modèle · d'où vient le nom du modèle (constante, env, config).

Puis **centraliser** : un seul point de configuration du modèle par usage (ex. `IA_MODELE_COPILOTE`, `IA_MODELE_SYNTHESE`…), avec la valeur par défaut au même endroit ; plus aucun nom de modèle en dur dans le code. Le tableau va au compte-rendu **et** dans une page du dashboard admin (section IA) : surface → modèle, lu depuis la config.

## Z8 — Liste de parcelles : « Adresse non disponible » partout (bug)

Constat Vic : toutes les lignes de la liste de résultats affichent « Adresse non disponible », y compris des parcelles qui ont une adresse en fiche. Trouver la cause (le endpoint de liste ne joint pas l'adresse, ou lit un autre champ que la fiche) et corriger : **la liste lit la même adresse que la fiche**, par le même chemin. Une parcelle sans adresse (grande parcelle rurale) reste « Adresse non disponible » — c'est un état vrai, pas un défaut. Test sur 3 parcelles dont 2 adressées.

Au passage, la fiche affiche « adresse non rattachée (Absent) » sur une parcelle en zone A : vérifier que ce libellé est le bon quand il n'y a réellement pas d'adresse, et qu'il ne cache pas le même défaut.

## Z9 — Filtres : le panneau ne rend pas la place à la liste (bug)

Constat Vic : après retour en arrière pour ajouter un filtre, le panneau Filtres occupe tout l'espace et la liste de parcelles n'est plus visible. **Le clic sur « Voir les N parcelles » referme le panneau Filtres** et affiche la liste. L'état ouvert/fermé du panneau suit l'action de l'utilisateur, pas l'historique de navigation. Test : ouvrir Filtres → ajouter un critère → « Voir les N parcelles » → la liste est visible et Filtres est replié.

## Z10 — Filtres : retirer la création de veille

Décision Vic : la ligne « Cette veille surveille : … » et le bouton « Créer une veille sur cette recherche » **disparaissent du panneau Filtres**. Une veille se crée depuis l'écran Veille.

**Conséquence à assurer** : l'écran Veille doit permettre de **créer une veille de recherche** — bouton « Nouvelle veille » → choix du type (annonces / recherche / parcelle) → pour « recherche », le même constructeur de critères que les filtres de la carte, avec l'aperçu « cette veille surveille : … » (livré en CONNEXIONS-2, il se déplace, il ne se perd pas). Sinon le type « recherche » n'est plus créable nulle part. Test : créer une veille de recherche depuis Veille, elle apparaît et s'évalue.

## Z11 — Liste de parcelles : retirer l'export CSV

Décision Vic : « export ≤ 5000 ↓ CSV » **disparaît** de la liste de résultats. Le compteur passe sur **une seule ligne** : « 200 / 430 813 » avec « Charger plus → » à droite. Si un endpoint d'export n'a plus aucun appelant, le marquer obsolète (ne pas supprimer).

## Z12 — Fiche parcelle : le verdict est-il sur la dernière donnée et le dernier algorithme ?

Vérifier et **prouver** au compte-rendu :

1. Le verdict (tier, probabilité, percentile, rang), le bloc « Pourquoi ce score » et les motifs rédhibitoires/vigilances lisent le **run courant** (point de vérité unique de CONNEXIONS-2) — aucun run en dur.
2. **Trois libellés de version coexistent à l'écran** : « modèle m36-l2f-2026 » sur la fiche, « run m135-run2-ile » dans Projets, `q_v11_m137` en base. Expliquer ce que chacun désigne (modèle de probabilité ? run de cascade ? run de scoring ?). Puis **un seul libellé lisible** pour l'utilisateur, identique partout, dérivé du run courant — les identifiants techniques restent au dashboard.
3. **Contradiction sur la même fiche** : « SDP résiduelle : donnée non disponible » dans « Pourquoi ce score » et « SDP résiduelle 0 m² — rien à construire » en vigilance. Les deux ne peuvent pas être vrais. Trouver lequel est juste et aligner l'autre (même champ, même source).
4. Recette : sur 3 parcelles (Priorité, À suivre, Écartée), comparer verdict de fiche, tier dans Projets et tier dans Scan patrimoine — identiques, même libellé de version.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : Z3 descriptions ayant exigé la réduction · **Z7 le tableau surface → modèle** · Z8 cause du défaut d'adresse · Z12 signification des trois libellés et lequel des deux « SDP résiduelle » était juste. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff fix/retours-7
```
