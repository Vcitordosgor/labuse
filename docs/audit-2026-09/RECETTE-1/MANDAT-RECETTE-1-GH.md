## Lot G — Branchement des outils : protocole unique

Pour chaque outil du lot H, « vérifier que les infos sont bien reliées » signifie exactement ceci :
1. Lister chaque chiffre et chaque libellé de donnée affichés par l'outil (tous les chemins), avec son id du registre (V5f) et sa ligne BRANCHEMENT.csv (SOURCES-AUDIT-3). Un chiffre sans id ou sans ligne = bug, à corriger.
2. Sur les témoins (3 par outil ; pour les outils à la commune : Saint-Paul · Bras-Panon · Saint-Denis), recalculer chaque chiffre par SQL direct ou appel direct de la fonction du moteur ; écart = bug, cause, correction, test.
3. Si le banc V6b ne couvre pas ce chiffre, l'y ajouter (famille + témoin).
Livrable : BRANCHEMENT-OUTILS.csv (outil · chemin · donnée · id registre · fonction · source · témoin · valeur écran · valeur recalculée · écart · corrigé). Ce qui est déjà prouvé par CALCULS-AUDIT-1 / COHERENCE-FIX-2 n'est pas recalculé : on le cite.

## Lot H — Outil par outil

H1 · PLU.
1. Les 24 PLU sont rattachés à la bonne commune : table commune → document GPU → millésime, vérifiée sur les 24, avec le statut GPU (Saint-Leu, Saint-André).
2. « Chercher dans le règlement » lit le PDF du PLU de la commune choisie : 3 requêtes par commune témoin (hauteur, recul, stationnement), chaque réponse cite article + page + lien du bon document.
3. « Par parcelle » et « Simuler l'ouverture » : même moteur que Faisabilité ; la simulation AU → U suit le renvoi d'ORACLE-FIX-1 lot A ; vérifier que les 3 choix du chemin sont les bons pour les 24 communes, et le dire.
4. Placeholder coupé : FAIT.

H2 · Permis.
1. Complétude : compter en base (50 544 autorisés) par année et par commune, comparer au fichier Sitadel open data 974 ; trous = ingestion à refaire ou motif. Noter la période couverte.
2. Exactitude : 10 permis tirés au sort (dont 3 géocodés « approx. ») : type, date, logements, état, adresse comparés à la ligne source.
3. Phrase sans accordéon, bulle sur la carte : FAIT.
4. La parcelle définit le périmètre : dès qu'une parcelle est saisie, les compteurs d'état comptent dans les 200 m, le filtre s'applique dans ce périmètre, la carte ne montre que ces permis en couleur d'état ; contour de la parcelle + cercle 200 m discret. Réinitialiser revient à l'île. Jamais deux périmètres actifs.
5. Pastilles retirées : FAIT.

H3 · Communes.
1. Protocole G sur les 4 chemins (Comparer · Évolution du marché · Marché des annonces · Acquisitions).
2. Évolution du marché, île entière : 2024T1 ancien vide alors que terrain = 449 ventes ; permis vides 2024T1-T3 puis 685 en T4 ; en-tête « 8 trimestres » mais 11 lignes ; 2026T1-T2 vides. Pour chacun : bug de requête (à corriger) ou vrai trou (à expliquer dans la ligne, « DVF publié jusqu'au … ») ; l'en-tête dit le nombre de lignes affichées.
3. Marché des annonces lit la même table que Radar ; la capture Radar tourne chaque jour (planificateur, dernière exécution, journal) ; la page affichait « dernière capture 27/09 » un 4 octobre : dire pourquoi et ce qui garantit la cadence sur le VPS. Le bloc affiche la date de la dernière capture.

H4 · Scan patrimoine.
1. Protocole G.
2-4. Bouton, repli, retours : FAIT. Vérifier aussi : au clic sur « Voir ses parcelles », liste (IDU · commune · surface · nu/bâti · zone · Fiche →) ET surbrillance sur la carte (contour menthe 2 px + aplat léger, distincte de la sélection), recadrage sur l'ensemble.

H5 · Assemblage.
1. Protocole G, dont la taxe foncière : même fonction que la fiche §Fiscalité, pas un calcul local ; vérifier que la fiscalité suit l'union des géométries.
2. Refonte en étapes (modèle Comparer communes) :
   - Étape 1 « Choisir les parcelles » : EntreeParcelle (adresse OU clic carte), liste des parcelles retenues avec ✕, 8 maximum (au-delà : « 8 parcelles maximum pour un assemblage »), bouton « Vérifier l'assemblage ».
   - Étape 2 « Assemblage » : si contiguës → « N parcelles contiguës · surface totale … » puis le résultat actuel ; sinon → « Pas d'assemblage possible : ces parcelles ne se touchent pas », avec la liste des parcelles isolées, rien d'autre.
   - Réinitialiser vide la liste.
3. Retirer la section « parcelles voisines » et le bouton « Préparer courrier propriétaire ».

H6 · Comparer communes.
1. Protocole G.
2. La 2e colonne du tableau est beaucoup plus large que les autres : trouver la cause ; colonnes égales, libellés sur 2 lignes si besoin, nombres jamais coupés.
3. État vidé en sortant de l'outil.

H7 · « Méthode et limites » (pied de chaque outil).
1. Le texte liste exactement les sources que l'outil lit (BRANCHEMENT-OUTILS.csv) avec millésime ; rien de plus, rien de moins.
2. Bouton vert opaque « ‹ Méthode et limites » : le rond autour de la flèche ne se voit pas (vert sur vert) ; rond contrasté, lisible aussi au survol.

H8 · Étude de zone.
1. Protocole G.
2. Fusion des deux chemins : une seule entrée depuis une parcelle (rayon en km, + / −) ; au départ un choix « Zone seule » ou « Zone + chalandise » (ajoute le sélecteur d'activité et le bloc chalandise) ; les 7 sections affichées une seule fois.
3. Retirer « ou en temps de trajet → ».
4. « Nouvelle étude » → Réinitialiser en haut à droite.
5. Après « Calculer la zone », le bouton vert « Lire la zone » disparaît ; l'étape 2 s'ouvre d'elle-même avec le résultat.

H9 · Remonter le temps.
1. Protocole G (chaque millésime = la couche IGN réellement servie).
2. « 1980 carte » ne marche pas : corriger (identifiant WMTS, emprise 974, clé), ou si aucune carte 1980 n'existe sur La Réunion, retirer le bouton et le dire.
3. Réinitialiser.

H10 · Faisabilité.
1. Protocole G (même appel que la fiche §Faisabilité : zéro écart).
2. Vérifier les calculs du panneau sur les témoins (enveloppe, plancher, logements, hypothèses modifiables, « Revenir aux valeurs LABUSE »).
3. « Voir en 3D » → « Gabarit » (ouvre l'outil Gabarit sur la parcelle, vue 2D).
4. « 7 règles du PLU · zone Uh » mis en valeur (titre de bloc, chevron, même DA que les blocs du panneau).
5. Réinitialiser.
6. Retirer tout le pied « Chercher des parcelles par capacité → · Pré-faisabilité indicative … par un professionnel. »

H11 · Gabarit.
1. Protocole G (HN0047 : 1 177 m², zone d'implantation 563 m², hauteur 14 m, limites 5 m, recul voie 6 m, 4 règles non intégrées).
2. Retour 2D sombre en quittant l'outil : FAIT.

H12 · Taxe d'aménagement. Protocole G.

H13 · Prospection solaire.
Chemin Piscines :
1. Dire clairement « N confirmées · N à confirmer », par commune, les 24 communes listées (aujourd'hui top 8 tronqué, et « +11 706 à confirmer » laisse croire deux comptes).
2. Retirer le plafond « 1 000 parcelles » : pagination serveur par 50 ; la carte montre tout le périmètre, avec le compte.
3. Refonte : étape 1 « Périmètre » (île ou une commune, compte à côté) ; étape 2 « Statut » (confirmées / à confirmer) ; résultat : compte, carte (parcelles colorées, pas des points), liste paginée (IDU · commune · source FLAIR/CoSIA · Fiche → · « pas une piscine » en icône). Tri par commune puis section.
4. Retirer la colonne m² par piscine.
Chemin Ensoleillement :
5. Protocole G ; F2/F3 : FAIT si déjà appliqué.

H14 · Bloc foncier. Protocole G.
H15 · Succession à venir. Protocole G.
H16 · Courrier. Protocole G (chaque champ du courrier = une donnée du registre).
