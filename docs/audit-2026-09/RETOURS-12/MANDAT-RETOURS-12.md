# MANDAT RETOURS-12 — recette visuelle et fonctionnelle du 04/09/2026

**Origine** : 18 captures + liste de demandes de Vic (04/09/2026, soir).
**Nature** : correction + refonte ciblée. Pas un audit : on livre du code.
**Branche** : `fix/retours-12`, unique, partant de `main`. **Une seule session**, les trois blocs ci-dessous sont l'ordre d'exécution, pas trois branches.
**Commit par lot** (T, C, O session B, O session C, J, A) pour que Vic puisse relire et revenir en arrière lot par lot. Si le contexte de la session s'épuise, CC s'arrête **sur un lot terminé et commité**, écrit où il en est dans le compte-rendu, et ne laisse jamais un lot à moitié fait.
**Total : 29 travaux numérotés** (T1-T7 · C1-C6 · O1-O13 · J1-J2 · A1). La case à cocher finale les reprend un par un.

---

## Étape 0 — obligatoire avant toute écriture

CC vérifie `pwd`, la branche courante et que l'arbre est propre. Si l'arbre n'est pas celui attendu ou n'est pas propre : **il s'arrête et le signale sans rien écrire**.
Aucun sous-agent ne touche à git. Aucun `git add -A`. La commande de merge n'est jamais jouée par CC.

## Prérequis à vérifier avant de commencer

1. **RETOURS-11 (sessions 11a → 11d) doit être mergé sur `main`.** Sinon, plusieurs travaux ci-dessous entreront en collision (tableaux, survols, pagination). Si ce n'est pas le cas, CC le signale et s'arrête.
2. **DESTINATIONS-1 (`feat/destinations-1`) doit être mergé** avant O13 : la capture d'Étude de zone affiche encore « CALIBRATION EN COURS » sur la zone U de Saint-Denis, alors que DESTINATIONS-1 livre 24 communes sur 24 et 773 zones citées. Si la branche n'est pas mergée, le symptôme est un fantôme — ne pas coder contre.
3. Run servi épinglé : le candidat **q_v12** n'est pas basculé. Tout travail ci-dessous lit le run servi par pointeur (`runs.current()`), **jamais un run en dur**.

## Doctrine rappelée (s'applique à chaque travail)

- Sourcé / Estimé / Dérivé affiché ; **jamais un zéro inventé** ; une donnée absente reste « — » avec la raison.
- Un fait = un moteur = un chiffre. Si deux écrans affichent le même indicateur, ils appellent la même fonction.
- Faux positif = péché cardinal. En cas de doute, on n'affiche pas — on dit pourquoi.
- **L'utilisateur n'est pas forcément un promoteur qui monte une opération.** C'est aussi une agence immobilière qui vérifie une parcelle avant de la prendre en mandat, un notaire, un architecte, un lotisseur, un apporteur d'affaires. Aucun écran ne suppose une opération en cours : on répond d'abord **ce qu'est la parcelle et ce qu'elle porte**, et l'analyse d'opération n'arrive qu'à la demande explicite.
- DA : vert `--mint` pour LABUSE, **mauve réservé aux surfaces IA**, ambre pour Projet. Jamais de camaïeu de vert pour un aplat de données sur la carte.
- Survol : case cliquable → **vert opaque, contenu inversé en sombre**, mauve plein sur les surfaces IA. L'entrée active n'a pas de style de survol.
- Listes longues : « Voir plus — N / M chargés », par 200.
- Chaque défaut corrigé reçoit le test qui l'aurait attrapé.

---

# BLOC 1 — transversal + carte

## Lot T — transversal, sur toute l'app (7 travaux)

### T1 — Recherche par référence cadastrale courte (ex. `BW0917`) partout — **priorité haute**
**Constat Vic** : « c'est le chiffre que les professionnels de l'immobilier ont le plus souvent » ; aujourd'hui, saisir `BW0917` ne donne **aucun résultat** dans aucune barre de recherche.

**Travail** :
1. **Inventaire d'abord** : lister dans le compte-rendu **toutes** les barres de recherche de l'app (barre globale, Étudier un bien, Faisabilité, Pièges & risques, PLU, Scan patrimoine, Densifier l'existant, Comparer des parcelles, Assemblage, Taxe d'aménagement, Solaire, Étude de zone, Permis, Courrier propriétaire, Radar, Projets, Veille, Copilote, admin). Une ligne par barre : fichier:ligne, moteur appelé, grammaire acceptée aujourd'hui.
2. **Un seul moteur de résolution** (`recherche/resolveur.py` ou l'existant s'il y en a un) appelé par toutes. Aucune barre ne garde sa propre grammaire.
3. Grammaire acceptée : IDU 14 caractères · **section + numéro** (`BW0917`, `BW 917`, `bw 0917`, `BW-917` — normalisation casse, espaces, zéros de tête) · adresse · nom/SIREN de propriétaire là où c'est déjà le cas.
4. **Ambiguïté** : une référence courte existe dans plusieurs communes. On ne choisit **jamais** au hasard : on rend la liste des candidates avec commune + surface + zone, l'utilisateur tranche. Si le contexte donne déjà la commune (fiche commune ouverte, filtre commune actif), on présélectionne cette commune en tête sans masquer les autres.
5. Zéro résultat n'est jamais muet : message qui dit ce qui a été cherché et sous quelle forme.

**Recette** : `BW0917` saisi dans chacune des barres inventoriées rend un résultat exploitable. Test paramétré sur les 3 formes d'écriture × 3 communes.

### T2 — SIREN / SIRET cliquable partout
**Travail** : inventaire de toutes les surfaces qui affichent un SIREN ou un SIRET (fiche parcelle propriétaire moral, Scan patrimoine, frise des opérations, Radar owner pro, CRM, fiche commune, admin, Étude de zone / SIRENE). Composant unique `<Siren value=… />` : lien vers **Pappers** (`https://www.pappers.fr/entreprise/{siren}`), nouvelle fenêtre, `rel="noopener"`, survol conforme à la règle. Un SIRET affiche le SIRET mais lie sur les 9 premiers chiffres. Pas de lien si la valeur n'a pas 9/14 chiffres valides.

### T3 — Rail latéral fixe
**Constat** : la barre latérale bouge au scroll. **Travail** : rail en position fixe, hauteur pleine, contenu de la page scrollant seul. Vérifié sur les 8 catégories.

### T4 — En-têtes de tableau réellement collants
**Constat** : sur « Les 24 communes » et sur « Densifier l'existant », la ligne d'en-têtes glisse et se superpose aux lignes de données (on lit les libellés par-dessus les chiffres). **Travail** : en-tête `sticky` avec **fond opaque** et z-index correct, sur toutes les tables longues de l'app (Communes, Densifier, PLU, Scan patrimoine, Radar, Projets, admin). Test visuel de scroll sur chaque table.

### T5 — Infobulles redondantes supprimées
**Constat** : au survol d'une pastille de commune sur la carte, une infobulle affiche « Bras-Panon · ouvrir la fiche commune » alors que la pastille dit déjà « Bras-Panon » et que le curseur dit déjà que c'est cliquable. Même chose sur les lignes de parcelles (« Ouvrir la parcelle 974… ») et dans Acquisitions.
**Travail** : une infobulle n'existe que si elle apporte un **fait non affiché**. Retrait sur : pastilles de communes (toutes), lignes de listes de parcelles, lignes du tableau Acquisitions. Inventaire des infobulles restantes dans le compte-rendu, avec ce que chacune ajoute.

### T6 — Contraste garanti au survol
**Constat** : ligne survolée en vert plein → les chips à l'intérieur (ex. `2024→2025` dans Acquisitions) passent en sombre sur vert et deviennent illisibles ; sur la ligne Saint-Joseph du tableau Communes, la ligne survolée déborde et mange la marge gauche.
**Travail** : régler dans **le composant**, pas au cas par cas — sur fond vert opaque, les chips et badges prennent un fond sombre plein avec texte clair (contraste ≥ 4,5:1) ; la ligne survolée respecte les marges du tableau et ne dépasse pas ses bords. Vérifié sur les tables Communes, Acquisitions, Densifier, Scan patrimoine, Radar.

### T7 — Sortir du prisme « opération » — **priorité haute**
**Constat Vic** : « ne vois pas ça par le prisme opération. Ça peut être une agence immo qui veut checker une parcelle. »
Aujourd'hui plusieurs écrans parlent comme si l'utilisateur montait une promotion : « l'opération ne finance pas ce foncier », « CA visé », « charge foncière ». Pour une agence qui prend un mandat, un notaire ou un particulier averti, ces phrases ne veulent rien dire — ou pire, elles rendent un verdict négatif sur une parcelle qui est simplement une parcelle.

**Travail** :
1. **Inventaire du vocabulaire d'opération** dans l'app (opération, charge foncière, CA visé, bilan, marge, prix de sortie, promoteur) : fichier:ligne, écran, contexte. Le rendre dans le compte-rendu.
2. **Règle** : la réponse de premier niveau est **descriptive et neutre** — ce qu'est la parcelle, ce que le PLU y autorise, ce qu'elle peut porter, ce que valent les biens du secteur, ce qui la contraint. Elle est utile à tous les métiers.
3. Le **raisonnement d'opération** (bilan, charge foncière, marge) devient un **second niveau explicite**, ouvert par un geste de l'utilisateur, jamais l'accueil d'un outil. Il est étiqueté comme tel : « analyser une opération sur cette parcelle ».
4. Aucun écran de premier niveau ne rend un **verdict négatif** issu d'un calcul d'opération. « Ne dégage pas de valeur » n'est pas un fait sur la parcelle, c'est le résultat d'hypothèses que l'utilisateur n'a pas posées.
5. Là où un terme métier est indispensable, il est **dit en français d'abord** et le terme technique suit entre parenthèses.

## Lot C — carte et couches (6 travaux)

### C1 — Couche réseau électrique : moyenne tension et haute tension
Deux entrées distinctes dans le menu Couches. Source à identifier et à documenter (open data RTE pour la haute tension, open data Enedis pour la moyenne tension ; OSM `power=line` en repli, étiqueté comme tel). **Aucune ingestion sans traçabilité** : URL, millésime, date de constat, entrée au catalogue des sources et à la sentinelle. Si aucune source ouverte fiable n'existe pour la moyenne tension au 974, on ne pose pas la couche : on l'écrit dans le compte-rendu avec le motif.

### C2 — Couche TCSP + distance à l'arrêt
**Vision Vic** : le tracé TCSP part de Sainte-Marie et va jusqu'au bout du boulevard sud. C'est un axe majeur : la densification s'y oriente, **et à moins de 500 m d'un TCSP le règlement peut réduire l'exigence de places de stationnement** — c'est un fait qui change la valeur d'une parcelle, utile à qui la vend comme à qui la construit.
**Travail** : tracé + arrêts en couche dédiée (source CINOR / Région Réunion — chercher le jeu ouvert, sinon numérisation documentée). Sur la fiche parcelle, un fait : distance à l'arrêt TCSP le plus proche, avec le seuil 500 m signalé. **Formulation prudente** : « à moins de 500 m d'un axe de transport structurant — le règlement de la zone peut moduler l'exigence de stationnement : à vérifier dans le PLU ». On ne promet jamais une réduction de parking : on signale le point à instruire, en renvoyant à la zone lue par le module destinations.

### C3 — Rampes de couleur des aléas
**Constat** : les légendes inondation et mouvement de terrain sont des camaïeux, on ne distingue pas l'échelle.
**Travail** : rampes à teintes franchement distinctes, légende par tranches nommées (pas un dégradé continu).
- Inondation : bleu (faible) → jaune → orange → **rouge** (le plus grave).
- Mouvement de terrain : beige → **marron** → orange → **rouge** (le plus grave).
Les libellés officiels de l'aléa restent la vérité affichée ; la couleur ne fait que les ordonner. Même rampe partout où l'aléa apparaît (carte, fiche parcelle, Pièges & risques, exports).

### C4 — Couche « parcelle » : trancher
**Question Vic** : « à quoi sert-elle ? j'ai l'impression qu'elle ne sert à rien ». **Travail** : établir ce qu'elle dessine réellement et en quoi elle diffère du fond cadastral toujours présent. Si elle est redondante, **la retirer du menu** (le code d'affichage cadastral reste). Si elle porte quelque chose d'unique, le dire en une phrase dans le compte-rendu et renommer l'entrée pour que ce soit évident. Décision par la mesure, pas par prudence.

### C5 — Arrêts de transport en commun : les grossir
**Constat** : les points d'arrêt sont des pastilles minuscules, invisibles au zoom courant.
**Travail** : rayon nettement augmenté et **proportionné au zoom** (petit à l'échelle île, franc à l'échelle quartier), contour sombre pour tenir sur fond clair comme sur fond ortho, zone de clic ≥ 24 px, survol conforme à la règle. Cohérent avec le tracé de la ligne (l'arrêt doit se lire comme un arrêt, pas comme un pixel sur un trait).

### C6 — Vue ortho : bug de la mer
**Constat** : en vue ortho dézoomée, la mer apparaît en escalier de tuiles bleues sur fond blanc — l'image s'arrête net en marches.
**Travail** : fond de mer continu sous les tuiles (couleur de fond de carte, pas du blanc), et emprise des tuiles ortho gérée jusqu'aux limites du jeu. Vérifié aux niveaux de zoom 8 à 12 et au recadrage sur l'île entière.

---

# BLOC 2 — outils, première moitié

### O1 — « Étudier un bien » : zoomer sur la parcelle
À la validation d'une adresse ou d'un IDU, la carte **zoome sur la parcelle et la met en surbrillance**, distincte de ses voisines. Le geste existe déjà ailleurs dans l'app : le réutiliser, ne pas en écrire un second (fonction commune, appelée par tous les outils qui prennent une parcelle en entrée — voir aussi O12).

### O2 — « Faisabilité » : refonte de lisibilité — **priorité haute**
**Constat Vic** : « on m'accueille avec −219 k€, je mets 500 k€ de prix et on me dit −719 k€. J'ai compris qu'on faisait le calcul mais ça correspond à quoi ? Ce n'est pas bon : soit mal expliqué, soit n'importe quoi. Retape cet outil, je ne le comprends pas. »

**Diagnostic obligatoire avant tout code** (à écrire dans le compte-rendu) : d'où sortent exactement −219 123 €, les −135 €/m², les 526 k€ de CA visé et les 123 m² vendables ; et ce que devient le prix saisi. L'hypothèse à confirmer ou infirmer : le bilan à rebours donne une **charge foncière admissible négative**, et le prix demandé est ensuite **soustrait** de cette charge, ce qui produit un déficit cumulé arithmétiquement exact mais illisible.

**Attendu — l'outil change d'accueil (voir T7)** :
1. **Premier niveau, sans hypothèse et sans argent** : ce que la parcelle porte. Zone et règles applicables, surface de plancher constructible, emprise, hauteur, nombre de logements plausible, ce qui est déjà bâti, ce qui contraint (accès, risques, servitudes). C'est ce que veut une agence qui vérifie une parcelle avant de la prendre en mandat, et c'est vrai pour tout le monde.
2. **Repères de marché à côté, pas un verdict** : prix du terrain nu dans la zone, prix de l'ancien et du neuf dans le secteur, avec `n` et fiabilité. Des faits, pas une conclusion.
3. **Second niveau, ouvert par un geste** : « analyser une opération sur cette parcelle ». Là seulement apparaissent le bilan à rebours, la charge foncière et la marge — et seulement après que l'utilisateur a posé ses hypothèses. **Aucun nombre négatif n'accueille l'utilisateur.**
4. Dans ce second niveau : **un seul chiffre de tête**, dit en français — « ce qu'une opération pourrait payer ce terrain, à vos hypothèses ». Quand il est négatif : « à ces hypothèses, une opération de ce type ne dégage rien pour le terrain » — et on **ne descend pas plus bas** en additionnant le prix demandé.
5. Le prix demandé est **comparé, jamais additionné** : « prix demandé 500 000 € · une opération pourrait en payer 0 € · écart 500 000 € ». L'écart est étiqueté écart.
6. La chaîne du calcul est dépliable, ligne à ligne, avec Sourcé / Estimé / Dérivé sur chaque entrée. Le bloc « Calibrées LABUSE » / « Vos hypothèses » reste, mais la bascule dit laquelle est active et ce qui change.
7. **Cohérence exports** : ce second niveau est le moteur du document FINANCIER décidé le 04/09 (formulaire d'hypothèses rempli par le client). Le premier niveau, lui, est ce qui nourrit le DOSSIER et le FLASH — qui n'ont **pas** de partie financière. Un seul moteur, un seul vocabulaire, les mêmes libellés à l'écran et dans le PDF.
8. Vérifier au passage la **surface vendable** : l'écran affiche 123 m², les exports 127 m² sur des parcelles comparables — établir si c'est la même parcelle et le même calcul, et supprimer le recalcul en double s'il existe.

### O3 — « Pièges & risques » : l'encadré doit disparaître
**Constat Vic** : « pourquoi cet encadré ? Soit on l'enlève, soit on règle le problème, mais je ne veux plus le voir. » Il s'agit de « NON COUVERT PAR LA BASE — À VÉRIFIER AILLEURS » (PEB aérodrome, procédures PLU en cours, canalisations de matières dangereuses, SUP hors GPU).
**Travail** : l'encadré **quitte la vue client**. Pour chacune des 4 lignes, trancher et documenter :
- **PEB** et **canalisations TMD** : chercher le jeu ouvert (Géorisques / DEAL). S'il existe, l'ingérer devient un travail de couche à chiffrer dans le compte-rendu (hors périmètre de ce mandat, mais nommé). S'il n'existe pas, la limite descend dans « méthode ».
- **Procédures PLU en cours** : déjà servies par l'outil PLU → renvoi discret, pas un encadré d'alerte.
- **SUP hors GPU** : 417 SUP sont ingérées et décodées ; la réserve devient une phrase courte dans la méthode dépliable (« une servitude non publiée au Géoportail n'est pas vue — le certificat d'urbanisme reste la référence »).
Résultat visible : plus aucun encadré d'aveu d'ignorance sur la fiche client ; ce qui reste vit dans la méthode, replié.

### O4 — Outil « PLU » : réconcilier les compteurs + bug IDU
**Constat Vic** : « zone annuaire : on me dit qu'il y a 2 PLU en révision et 1 RNU ; par contre dans procédures et changements, on me dit qu'il y a quelque chose sur Trois-Bassins. Comment ça se fait ? Accorde tout ça. »
**Travail** :
1. Un seul moteur, une seule liste de procédures (radar Sudocuh + registre curaté). Le compteur de l'annuaire et le registre affiché lisent la **même** requête. Si Trois-Bassins est en révision générale prescrite le 02/06/2022, il est compté ; s'il ne l'est pas, il ne s'affiche pas. Écrire dans le compte-rendu le nombre réel de communes par état (révision générale / modification / élaboration / RNU) et ce qui manquait au compteur.
2. **Bug** : la vérification « un IDU → la commune est-elle en procédure PLU » rend « Parcelle inconnue ou erreur » sur un IDU valide (exemple affiché : `97413000CJ0096`). Trouver la cause (résolution d'IDU, run lu, jointure commune) et corriger. Test de régression sur 24 IDU, un par commune.

### O5 — « Scan patrimoine » : la liste des parcelles ne s'ouvre pas
**Constat Vic** : bug, on ne voit pas la liste des parcelles.
**Travail** : le bouton « Voir ses opérations → » est remplacé par **« Voir ses parcelles → »** ; au clic, la liste des parcelles du propriétaire s'ouvre et **le bandeau du haut se replie en accordéon** pour lui laisser la place. Le bandeau reste rouvrable. Les opérations restent accessibles par l'onglet « Ce qu'ils construisent » — on ne perd pas le geste, il change de porte. Pagination par 200, « Voir plus — N / M chargés ».

### O6 — « Scan patrimoine » / constructions : doublons
**Constat Vic** : « je vois des doublons ou je rêve ? J'ai vu plein de fois les mêmes noms d'opération. » La capture montre **CBO TERRITORIA affiché deux fois**, avec deux blocs de permis différents (33 permis / 115 logements et 8 permis / 8 logements) mais **la même frise « 20 opérations · 230 logements »** et la même liste de programmes publiés.
**Travail** : établir la cause — probablement un regroupement par SIREN qui produit plusieurs cartes (deux `id` propriétaire pour le même SIREN) alors que la frise, elle, agrège au SIREN. Corriger : **un propriétaire moral = une carte** ; les compteurs de permis et la frise lisent le même périmètre ; les programmes publiés ne sont listés qu'une fois. Test anti-doublon sur les 16 promoteurs du seed. Rappel de la dette connue : le rattachement programme ↔ opération est stocké par les coordonnées de l'opération faute d'identifiant persistant — si la correction touche les règles de regroupement, le rattachement doit être recalculé, pas cassé en silence.

### O7 — « Prospection solaire » / Ensoleillement : pente et photo du toit
Ajouter, **si la donnée existe déjà** (données solaires gelées au 11/07/2026, PVGIS, azimut/pente) : nature de la toiture — **simple pente / double pente** (avec la méthode et son incertitude), et **la photo du toit** en vue ortho, surmontée d'une **rosace d'orientation** (nord, sud, est, ouest) alignée sur l'azimut réel. Si la distinction simple/double pente n'est pas dérivable des données en base, ne rien inventer : le dire dans le compte-rendu et n'afficher que l'azimut et la pente moyenne.

---

# BLOC 3 — outils, seconde moitié + projets + IA

### O8 — « Communes » / comparaison : le SRU ne concorde pas — **priorité haute**
**Constat Vic** : « SRU 6,7 dans le tableau alors que sur la fiche commune il est à 18 %. Comment ça se fait ? »
**Travail** :
1. Établir la définition de chaque colonne. Le tableau annonce « Déficit SRU (pts) = objectif légal − taux de logement social (points) » ; la fiche commune affiche probablement le **taux** en %. Deux grandeurs différentes qui portent le même mot → soit on nomme explicitement (« déficit, en points » vs « taux SLS, en % »), soit on affiche les deux côte à côte. Une seule fonction produit les deux.
2. **Audit ligne à ligne des 7 indicateurs du tableau** (parcelles à potentiel, instruction, permis 5 ans, déficit SRU, €/m² ancien, €/m² neuf, €/m² terrain nu) contre la fiche commune correspondante, sur les 24 communes. Un tableau de résultat dans le compte-rendu : indicateur × moteur appelé par le tableau × moteur appelé par la fiche × concordent oui/non. Tout écart est corrigé en ramenant les deux à un seul moteur.
3. Les « — » restent des « — » (Saint-Louis, Saint-Joseph, Saint-André en €/m² neuf) : jamais de zéro inventé.

### O9 — « Communes » : tenue du tableau au scroll
En-tête fixe (voir T4), marges gauche/droite respectées y compris sur la ligne survolée (voir T6), la fiche modale ne doit pas paraître coupée en bas au scroll (hauteur et masque de défilement), la légende reste lisible et ne flotte pas au milieu des lignes.

### O10 — « Communes » / évolution du marché : passer en tableau
**Constat Vic** : « c'est trop serré, ça ne respire pas ». **Travail** : même grammaire visuelle que « comparaison communes » — vrai tableau, colonnes triables, en-tête collant, légende sous le tableau, une ligne par commune ou par période selon l'axe. Aucune donnée nouvelle : c'est une remise en forme sur les moteurs existants.

### O11 — « Communes » / acquisitions : survol illisible + infobulle
Chips de millésime (`2024→2025`) lisibles sur ligne survolée (voir T6) ; retrait de l'infobulle « Ouvrir la parcelle 974… » qui répète le lien déjà affiché sous la ligne (voir T5).

### O12 — Outil « Permis » : lever l'ambiguïté et zoomer
1. **« Permis en cours »** : dire de quoi on parle. Si c'est l'instruction (déposé, pas encore autorisé) → « en cours d'instruction ». Si c'est le chantier (autorisé, travaux non achevés) → « chantier en cours ». Si les deux existent en base (dates de dépôt, d'autorisation, DOC, DAACT), en faire **deux entrées distinctes** plutôt qu'un libellé flou. Le libellé retenu doit être le même dans l'outil, la fiche parcelle, la carte et les exports.
2. À la recherche par adresse ou IDU, **la carte zoome sur la parcelle et la délimite** — même fonction que O1, pas une seconde implémentation.

### O13 — « Étude de zone » : refonte — **priorité haute**
**Constat Vic** : « pas possible d'avoir une donnée plus récente que 2011 ? Je ne peux pas écrire "boulangerie" moi-même, je peux juste choisir, et je ne trouve pas boulangerie — on dirait qu'il n'y a pas tout. Retape l'outil, là ça bugue beaucoup, ce n'est pas pro. Où est passée la donnée PLU destinations pour la zone de chalandise ? Il faut deux entrées distinctes : zone particulière et zone de chalandise. »

**Travail** :
1. **Deux portes distinctes** à l'ouverture de l'outil :
   - **Zone de chalandise** — implantation d'une activité : point ou adresse, activité visée, temps de trajet → population, emplois, concurrence, équipements, trafic, et **ce que le PLU autorise pour cette activité** dans les zones couvertes.
   - **Zone particulière** — contexte foncier autour d'une parcelle ou d'un périmètre libre : ce qu'il y a autour, sans hypothèse d'activité.
   Le moteur reste unique, les deux visages ne sont que des entrées et des sorties différentes. Le bloc « Autour de cette parcelle » de la fiche parcelle reste branché sur le même moteur.
2. **Activité en champ libre avec autocomplétion**, pas une liste fermée : l'utilisateur tape « boulangerie » et l'outil résout vers la sous-classe NAF (10.71C / 47.24Z selon fabrication ou vente) et vers la sous-destination PLU correspondante. Le libellé saisi reste affiché ; la correspondance retenue est montrée et modifiable. Si un terme ne résout pas, on le dit et on propose les voisins — jamais de silence.
3. **Trafic** : la fiche affiche « N6 · 2011 · 15 000 véh./j ». Chercher un millésime plus récent (Région Réunion, DEAL, comptages routiers ouverts). S'il n'y en a pas, **le millésime reste affiché** et la phrase de méthode le dit — 2011 assumé vaut mieux que 2011 caché. Écrire la recherche et son résultat dans le compte-rendu.
4. **Destinations PLU** : la capture montre « U · Saint-Denis · CALIBRATION EN COURS · zone U non lue ». Après merge de DESTINATIONS-1 (24/24 communes, 773 zones, 3 136 sous-destinations), plus aucune zone calibrée ne doit afficher cet état. Vérifier que l'outil appelle bien `plu/destinations.py` et pas un vestige. Les verrous CDAC (> 1 000 m² de surface de vente) et SCoT/DAAC restent affichés comme points à instruire, jamais comme verdicts.
5. **Chasse aux bugs** : parcourir l'outil de bout en bout sur 5 cas réels (2 chalandises, 3 zones particulières), lister chaque anomalie rencontrée et la corriger. L'outil doit être présentable à un client à la fin de la session.

## Lot J — Projets (2 travaux)

### J1 — Voir la parcelle sur la carte depuis la liste
À côté des boutons **✓** et **✗** d'une ligne de la colonne à trier, ajouter un **œil en ambre** (couleur Projet) : au clic, la carte zoome sur la parcelle **en vue ortho**, délimitée, sans quitter le projet ni perdre l'état de la liste. Même fonction de zoom que O1/O12.

### J2 — Un projet créé apparaît immédiatement
**Constat Vic** : « j'ai créé un projet, puis depuis une fiche parcelle j'ai cliqué sur "Projet" pour la ranger, et le projet n'apparaissait pas alors que d'autres oui. Soit il y a de la latence, soit je ne sais pas. »
**Travail** : reproduire, établir la cause (cache client non invalidé après création, liste chargée une fois au montage, ou filtre côté serveur qui exclut un projet vide). Corriger à la source : le menu « Projet » de la fiche parcelle lit la liste à l'ouverture. Test de bout en bout : créer un projet → ouvrir une fiche parcelle → le projet est dans le menu, sans rechargement de page.

## Lot A — IA (1 travail)

### A1 — L'IA est mal branchée, et pas seulement dans le Copilote
**Constat Vic** : « IA mal branchée, mais pas que dans le Copilote — partout sur l'app. Regarde partout où on est branché à l'IA et rebranche. » La capture montre le Copilote qui répond « Je ne peux pas instruire votre demande pour le moment (service d'analyse indisponible) » sur une question simple.

**Travail** :
1. **Inventaire de toutes les surfaces IA** de l'app : Copilote (v1 et v2), synthèse IA de fiche parcelle, résumés de fiche commune, extraction des dépôts agence / programmes promoteurs, aide à la rédaction du Courrier propriétaire, tout appel restant. Une ligne par surface : fichier:ligne, modèle appelé, d'où vient le nom du modèle, d'où vient la clé.
2. **Cause du dégradé** : vérifier en priorité les dettes connues — version du client `anthropic` (le code exige la lignée `0.116.0` ; `1.1.0` refuse le paramètre `temperature` et fait tomber en mode dégradé **sans erreur visible**), nom du modèle (source unique `ai_models.py`, config **fail-closed** au boot — si la variable d'environnement est absente ou périmée, l'API ne démarre pas au lieu de servir un dégradé muet), et validité de la clé.
3. **Aucun modèle en dur, aucun modèle dans l'environnement seul** : `ai_models.py` est la source unique, l'inventaire est visible au dashboard admin.
4. **Le message d'erreur devient honnête** : plus de « réessayez dans un instant » quand la cause est structurelle. Côté admin, l'incident est visible (quelle surface, quel modèle, quelle cause). Côté client, un message qui n'invite pas à réessayer 20 fois pour rien.
5. **Le verrou anti-invention reste intact** : aucun chiffre généré n'échappe à la vérification en base. On rebranche, on n'assouplit pas.

---

## Recette et livraison

- **Recette dans un vrai navigateur**, sur la base réelle, écran par écran, avant tout commit. Les travaux de carte (C1-C6) se vérifient à 3 niveaux de zoom.
- Chaque travail corrigé reçoit **le test qui l'aurait attrapé**.
- **Aucune table supprimée** : on cesse de lire, on marque obsolète.
- Toute migration porte son backfill et son test.
- Un **compte-rendu unique** dans `docs/audit-2026-09/RETOURS-12/` : une ligne par travail numéroté — fait / fait autrement (avec le pourquoi) / pas fait (avec le motif). Les inventaires demandés (T1, T2, T5, A1) y sont joints en entier.
- Commits par lot, message explicite, **jamais de merge par CC**. La branche reste `fix/retours-12` du début à la fin.

---

## Case à cocher — les 28 travaux

**Transversal**
- [ ] T1 — recherche par référence courte `BW0917` dans toutes les barres, un seul moteur, désambiguïsation par commune
- [ ] T2 — SIREN/SIRET cliquable vers Pappers partout
- [ ] T3 — rail latéral fixe
- [ ] T4 — en-têtes de tableau collants et opaques sur toutes les tables
- [ ] T5 — infobulles redondantes retirées (pastilles communes, lignes de parcelles, acquisitions)
- [ ] T6 — contraste garanti au survol (chips lisibles, ligne qui ne déborde pas)
- [ ] T7 — sortie du prisme « opération » : premier niveau descriptif pour tous les métiers, bilan d'opération en second niveau explicite

**Carte et couches**
- [ ] C1 — couches ligne moyenne tension et haute tension
- [ ] C2 — couche TCSP + distance à l'arrêt et point de vigilance stationnement (< 500 m)
- [ ] C3 — rampes distinctes pour aléa inondation (bleu → rouge) et mouvement de terrain (marron → rouge)
- [ ] C4 — couche « parcelle » : tranchée (retirée ou renommée avec son utilité)
- [ ] C5 — arrêts de transport en commun nettement grossis
- [ ] C6 — vue ortho : bug de la mer réparé

**Outils**
- [ ] O1 — « Étudier un bien » zoome et délimite la parcelle
- [ ] O2 — « Faisabilité » retapée : accueil descriptif (ce que porte la parcelle), bilan d'opération en second niveau, écart au prix demandé, moteur partagé avec le PDF FINANCIER
- [ ] O3 — « Pièges & risques » : encadré « non couvert par la base » retiré de la vue client
- [ ] O4 — « PLU » : compteur et registre des procédures réconciliés + bug « Parcelle inconnue » sur IDU valide
- [ ] O5 — « Scan patrimoine » : « Voir ses parcelles » ouvre la liste, bandeau en accordéon
- [ ] O6 — « Scan patrimoine » : doublons de propriétaires/opérations supprimés, test anti-doublon
- [ ] O7 — « Prospection solaire » : simple/double pente + photo du toit avec rosace d'orientation
- [ ] O8 — « Communes » : SRU concordant et audit des 7 indicateurs contre la fiche commune
- [ ] O9 — « Communes » : tenue du tableau au scroll (en-tête, marges, fiche non coupée)
- [ ] O10 — « Communes » / évolution du marché en vrai tableau
- [ ] O11 — « Communes » / acquisitions : survol lisible, infobulle retirée
- [ ] O12 — « Permis » : « en cours » désambiguïsé (instruction vs chantier) + zoom sur la parcelle
- [ ] O13 — « Étude de zone » retapée : zone de chalandise / zone particulière, activité en champ libre, trafic daté, destinations PLU rebranchées, bugs soldés

**Projets**
- [ ] J1 — œil ambre à côté de ✓ / ✗ : voir la parcelle sur la carte en ortho
- [ ] J2 — un projet créé apparaît immédiatement dans le menu « Projet » de la fiche parcelle

**IA**
- [ ] A1 — inventaire de toutes les surfaces IA, cause du dégradé traitée, source unique de modèle, erreur honnête
