# MANDAT RETOURS-13 — reprise après recette de RETOURS-12

**Origine** : recette de Vic du 05/09/2026 sur la branche `fix/retours-12` (20 captures + liste). RETOURS-12 n'est **pas mergé** : on corrige sur la même branche.
**Branche** : `fix/retours-12`, on continue dessus. Un commit par lot.
**Total : 32 travaux numérotés** (R1-R32). Vic les checkera un par un.

---

## Étape 0 — obligatoire

`pwd`, branche `fix/retours-12`, arbre propre. Sinon arrêt sans rien écrire. Aucun sous-agent sur git, aucun `git add -A`, aucun merge.

## Contexte à lire avant de commencer

1. `docs/audit-2026-09/RETOURS-12/MANDAT-RETOURS-12.md` — le mandat précédent. Les références T1-T7, C1-C6, O1-O13, J1-J2, A1 dans ce document renvoient à ses travaux.
2. `docs/audit-2026-09/RETOURS-12/COMPTE-RENDU.md` et ses inventaires (T1 barres de recherche, T2 surfaces SIREN, T5 infobulles, T7 vocabulaire, A1 surfaces IA) — ce qui a été livré et où.
3. `docs/audit-2026-09/RETOURS-12/DIAGNOSTIC-O2-faisabilite.md` si R26 touche au moteur de SDP.

**Règles de DA à appliquer telles quelles** (décisions de Vic, cumulées) :
- Vert `--mint` pour LABUSE ; **mauve réservé aux surfaces IA** ; ambre pour Projet ; **pas de bleu**, sauf l'exception décidée le 05/09 : les liens SIREN/SIRET (R17).
- Survol d'une ligne ou carte cliquable : **vert opaque, contenu inversé en sombre**. Les chips et badges à l'intérieur gardent un fond sombre plein et un texte clair. L'entrée active n'a pas de style de survol.
- Action secondaire dans une ligne (« voir la fiche », « Fiche → ») : **jaune opaque au survol**, pour la distinguer du survol de la ligne.
- Une infobulle n'existe que si elle apporte un fait non affiché.
- Listes longues : « Voir plus — N / M chargés », par 200.
- Jamais de camaïeu pour un aplat de données ; jamais de camaïeu de vert.
- Primitive de zoom sur parcelle : `focusParcelle` (créée en O1) — toute modification s'y fait, jamais dans un outil.

**Lots et commits** : Lot 1 (R1-R9) → commit · Lot 2 (R10-R18) → commit · Lot 3 (R19-R32) → commit, R31 en commit séparé s'il aboutit à une ingestion. Si le contexte s'épuise, arrêt sur lot terminé et commité, jamais au milieu.

## Ce qui a manqué dans RETOURS-12 — et qui ne doit pas se reproduire

Trois travaux ont été déclarés « faits » ou « vérifiés » et ne l'étaient pas à l'écran de Vic : la mer en ortho (C6, « vérifié zooms 8/10/12 »), les infobulles (T5, encore là sur la liste des communes et le tableau), le rail (T3, corrigé seulement au retest). Deux autres reposaient sur une recherche de source trop courte (C1 moyenne tension, C2 TCSP) — les sources existent, voir R4 et R5.

**Règles pour ce mandat :**
- Un travail visuel n'est « fait » qu'avec **une capture avant/après** dans `docs/audit-2026-09/RETOURS-13/captures/`, prise sur le fond et au zoom que Vic utilise (vue Ortho IGN île entière, tableau en fenêtre 1440 px, etc.). Pas de « vérifié » sans capture.
- Une couche est recettée sur **les 4 fonds** (sombre, clair, ortho, IGN) et à 3 zooms. Une capture par fond.
- Une absence de source n'est acceptée qu'après avoir **ouvert** les pistes listées dans ce mandat et écrit ce qui a été trouvé à chaque URL.
- Doctrine inchangée : Sourcé / Estimé / Dérivé, jamais un zéro inventé, un fait = un moteur, faux positif = péché cardinal, jamais de camaïeu de vert pour un aplat de données.

---

# LOT 1 — carte, fonds et couches

### R1 — La mer en vue Ortho IGN, île entière (P1)
**Constat** : en vue Ortho IGN dézoomée sur l'île entière, la mer est un escalier de tuiles bleues sur fond **blanc**. Identique à la capture du 04/09. C6 n'a pas corrigé le cas que Vic regarde.
**Travail** : reproduire **exactement** ce cadrage (Ortho IGN, île entière, cadre par défaut à l'ouverture). Le fond sous les tuiles ortho doit être une couleur de mer sombre continue, et l'emprise des tuiles gérée jusqu'à la limite du jeu sans marches. Vérifier aussi le fond IGN et le fond clair au même cadrage. Capture avant/après sur les trois.

### R2 — Couche « Parcelles — classement LABUSE » vs « Limites parcelles » : prouver ou retirer
**Constat Vic** : « couche parcelles sert à rien ? il y a une différence avec limites parcelles ? si non enlève-la ».
**Travail** : produire deux captures au même cadrage, l'une avec « Parcelles — classement LABUSE » seule, l'autre avec « Limites parcelles » seule. Si la différence n'est pas **évidente à l'œil** en 2 secondes, la couche « Parcelles — classement LABUSE » est retirée du menu. Si elle l'est, la garder et l'expliquer en une ligne dans le `i`. Décision par la capture, pas par l'argument.

### R3 — Les couches réseaux doivent être visibles dans le menu Couches
**Constat Vic** : « où sont passées les couches que j'avais demandé d'ajouter ?? ». Il ne voit ni HT, ni MT, ni TCSP dans le menu.
**Travail** : un groupe **« Réseaux »** dans le menu Couches, avec des entrées nommées en clair : « Lignes haute tension (HTB) », « Lignes moyenne tension (HTA) », « Transport en commun en site propre », « Arrêts de transport en commun ». Chacune a son `i` (source, millésime, ce que ça couvre). Capture du menu déplié.

### R4 — Moyenne tension : la source existe (P « refais une recherche approfondie »)
**Ce que CC a écrit** : « EDF SEI a retiré ses couches le 24/12/2025 ; Enedis absent des DOM ; BD TOPO = HT seule ».
**Ce que Fable a trouvé le 05/09** : le portail open data d'EDF Réunion publie **« Lignes haute tension (HTA aérien) »** et **« Lignes haute tension (HTA souterrain) »** — HTA dans le vocabulaire EDF, c'est **la moyenne tension** (15-20 kV), pas la HTB. Les fiches portent la mention « les données de cartographie des réseaux électriques ont été mises à jour afin de renforcer la sécurité publique » : la géométrie a peut-être été **généralisée** (simplifiée) plutôt que retirée. Le jeu est aussi miroité sur data.regionreunion.com et référencé sur data.gouv.fr (organisation EDF SEI).
**Travail** :
1. Ouvrir dans l'ordre : `https://opendata-reunion.edf.fr/explore/dataset/lignes-haute-tension-hta-aerien/`, la variante souterraine sur `reunion-edf-sei.opendatasoft.com`, puis `https://data.regionreunion.com/explore/dataset/lignes-haute-tension-hta-aerien/`, puis l'organisation EDF SEI sur data.gouv.fr. Pour chaque URL, écrire dans le compte-rendu : existe / a une géométrie / niveau de détail / licence / date de mise à jour.
2. Si une géométrie exploitable existe (même généralisée) : ingérer, entrée au catalogue des sources et à la sentinelle, `i` honnête (« tracé indicatif publié par EDF, précision réduite pour raison de sécurité publique, ne remplace pas une DT-DICT »).
3. Repli si la géométrie a réellement disparu : OSM `power=minor_line` sur le 974, étiqueté OSM avec sa date d'extraction. Seulement après avoir prouvé l'absence sur les 4 URL.
4. Aussi : **postes sources** (jeu EDF « position des postes source ») — un point sur la carte utile pour le raccordement.

### R5 — TCSP : la vraie couche, pas BAOBAB (P « couche TCSP »)
**Constat Vic** : « Sainte-Marie–Saint-Denis c'était un exemple pour que tu comprennes. Enlève BAOBAB, moi je veux la couche TCSP, je m'en fous de la ligne BAOBAB en particulier. »
**Travail** :
1. **Retirer** la couche « Axe structurant (BAOBAB Express) » et le fait de fiche parcelle qui en dérive. Ne pas laisser un vestige.
2. **Recherche de source** — pistes à ouvrir une par une et à documenter. Vic a signalé les projets par leur nom ; Fable a vérifié le premier le 05/09 :
   - **Réunion Express (Région, tram-train 140 km, 25 gares, Saint-Benoît → Saint-Joseph)** : débat public CNDP du 19/08 au 26/11/2026, `https://www.debatpublic.fr/projet-train-reunion-express`. La Région y publie **une cartographie des hypothèses de tracé et des zones de variantes**. C'est la source « en projet » prioritaire. Chercher le dossier du maître d'ouvrage (PDF) et la carte interactive ; si une couche SIG ou un export est téléchargeable, l'ingérer avec l'étiquette « hypothèse de tracé — débat public 2026, variantes ouvertes, phase 1 Saint-Benoît–Saint-Paul visée 2035 ». Si seulement une image, ne pas numériser : lien vers la carte et mention dans le `i`. Inscrire à la sentinelle : le tracé bougera après le débat.
   - **TCO / Le Port** : voies réservées bus avenue Rico Carpaye, travaux juillet 2026 → janvier 2028 — chercher la source SIG TCO/Kar'Ouest.
   - **CIREST** : TCSP ESTI+ (avenue Jean Jaurès, rue Joseph-Hubert…) — chercher le tracé sur le site CIREST et PEIGEO.
   - **CIVIS** : TCSP Saint-Pierre entrée ouest, projet Néo / pôle d'échanges, site `tcsptoutsavoir.com` et `civis.re`.
   - **CINOR** : TCSP nord et boulevard sud, ancien projet tram TAO devenu BHNS.
   - **PEIGEO / AGORAH** (`peigeo.re`, catalogue GeoNetwork) : « TCSP », « site propre », « Trans-Éco Express », « voies réservées », « SAR » — le Schéma d'Aménagement Régional porte les axes TCSP structurants ; l'AGORAH a instruit le contrat d'axe du RunRail.
   - **Région Réunion** (`data.regionreunion.com`) : « Trans-Éco Express », « VRTC ». Le Cerema documente les **voies réservées bus sur RN1/RN2** — sites propres existants.
   - **OSM** : `highway=busway`, `busway=lane`, `lanes:psv`, `psv=designated` sur le 974 — voies réservées existantes, étiquetées OSM.
3. **Ce qu'on veut afficher** : une couche « Transport en commun en site propre » avec trois états lisibles — **en service** (VRTC RN1/RN2, tronçons CIVIS livrés) / **en travaux** (Rico Carpaye, ESTI+) / **en projet** (Réunion Express, variantes). Chaque tronçon porte sa source, son état, sa date. Jamais un tracé numérisé à la main.
4. **Fiche parcelle — base légale vérifiée le 05/09** : art. L151-36 du code de l'urbanisme (habitation : plafond **1 place / logement**) et L151-34/35 (LLS, intermédiaire, résidences seniors et étudiantes : **0,5 place / logement**) pour toute construction située à moins de **800 mètres** d'une gare ou d'une station de transport public guidé ou de transport collectif en site propre, « dès lors que la qualité de la desserte le permet ». **Le seuil est passé de 500 à 800 m par la loi n° 2026-103 du 19 février 2026** — CC vérifie l'article sur Légifrance (`LEGIARTI000052866917`) et le cite dans le `i`. La distance se mesure **depuis la station, à vol d'oiseau** (Conseil d'État, 2022), pas depuis la ligne ni par la voirie.
   Donc : distance à la **station** en service la plus proche (pas au tracé), drapeau < 800 m, formulation : « à moins de 800 m d'une station de transport collectif en site propre — le PLU ne peut pas exiger plus d'1 place de stationnement par logement (0,5 pour le logement social), si la qualité de la desserte le permet (art. L151-36) ». Le plafond s'impose au PLU, ce n'est pas une faculté ; ce qui reste à instruire, c'est la qualité de la desserte et si l'aménagement est bien un « site propre » au sens du texte (BHNS oui ; couloir bus ponctuel : douteux — ne pas déclencher le drapeau pour un simple couloir).
   Les tronçons en travaux ou en projet ne déclenchent **pas** le drapeau ; ils sont cités comme information datée — pour le Réunion Express : « dans le corridor d'une hypothèse de tracé du Réunion Express (débat public 2026, variantes ouvertes, mise en service visée 2035) ». C'est un fait qui pèse sur une décision d'achat aujourd'hui, mais qui reste une hypothèse : le dire tel quel.
5. Si, après avoir ouvert toutes les pistes, rien n'est exploitable : compte-rendu URL par URL, et la couche n'est pas posée. C'est le seul cas où l'absence est acceptée.

### R6 — Aléa mouvement de terrain : pas de rouge visible
**Constat Vic** : « je ne vois rien en rouge, je vois que du orange et du jaune, c'est normal ? »
**Travail** : sortir la table des classes réelles du jeu (PPR mouvement de terrain : libellés exacts, effectifs par classe). Vérifier que chaque classe est affectée à une teinte distincte et que **la classe la plus grave est bien rouge**. Si le rouge n'apparaît pas parce que la classe existe mais est rare, l'afficher dans la légende avec son effectif ; si elle n'existe pas dans le jeu, la légende ne doit pas la promettre. Même vérification pour inondation. Capture avec légende.

### R7 — Aléas : plus de hachures (P5)
**Constat Vic** : « enlève le hachurage ». Les aplats hachurés (capture 5) sont illisibles sur fond sombre.
**Travail** : aplats pleins semi-transparents, opacité calibrée par fond (sombre / clair / ortho / IGN) pour que la couleur reste identifiable sans masquer le cadastre. Une capture par fond.

### R8 — Aléas en ortho : contours noirs illisibles (P6)
**Constat Vic** : sur ortho, les contours noirs des polygones d'aléa font une bouillie. « Le délimitage noir devrait apparaître quand on zoome plus, comme tu l'avais fait sur sombre. Vérifie que sur clair et IGN c'est aussi le cas. »
**Travail** : contour absent aux petits zooms, apparaît à partir du seuil déjà utilisé sur le fond sombre, **même règle sur les 4 fonds**. Capture à 2 zooms sur chaque fond.

### R9 — Arrêts de transport cliquables
**Constat Vic** : « les arrêts devraient être cliquables et juste donner le nom de l'arrêt et la ligne à laquelle il appartient ».
**Travail** : au clic, une bulle minimale : nom de l'arrêt, ligne(s) qui le desservent, réseau. Rien d'autre. Les données sont déjà dérivées du GTFS (`transport_arret` 9 956, `transport_ligne` 300) — mais les lignes n'ont **pas de nom** en base (attrs = route_id / route_type seulement) : reprendre `route_short_name` et `route_long_name` de `routes.txt` à l'ingestion. Survol conforme à la règle.

---

# LOT 2 — tableaux, listes et survols

### R10 — Liste des communes (« Toute l'île ») : infobulle + « voir la fiche » (P4)
**Constat** : au survol de « Saint-Paul », une infobulle répète « Saint-Paul ». Et on ne sait pas si on clique la ligne ou « voir la fiche ».
**Travail** : infobulle retirée (T5 n'a pas couvert cette liste — refaire l'inventaire des infobulles, liste par liste, et le joindre). Au survol de « voir la fiche → » : **jaune opaque** (couleur d'action secondaire), pour distinguer l'action du survol vert de la ligne.

### R11 — Tableau des 24 communes : marges, infobulle, « Fiche → » (P7)
**Constat** : ligne survolée collée aux bords (pas de marge gauche/droite), infobulle « Le Port » qui répète le nom, « Fiche → » ne réagit pas au survol.
**Travail** : élargir la modale et poser des marges internes gauche/droite ; la ligne survolée respecte ces marges. Infobulle retirée. « Fiche → » en **jaune** au survol, comme sur le tableau principal des parcelles. Capture survol.

### R12 — « Ouvrir le Radar → » centré verticalement (P8)
Le lien est aligné en haut du bloc, le texte au milieu. Aligner sur la ligne de base du texte.

### R13 — « Évolution du marché » : un vrai tableau en grand, comme « comparaison communes »
**Constat Vic** : « j'avais demandé que ça apparaisse en tableau en grand comme comparaison commune, j'ai l'impression que tu as fait n'importe quoi ».
**Travail** : même composant, même modale plein écran, même en-tête collant, même légende sous le tableau que « Les 24 communes ». Une ligne par période, colonnes = indicateurs de marché, triables. Aucune donnée nouvelle. Capture côte à côte avec « Les 24 communes » pour prouver la parenté.

### R14 — Acquisitions : « 50 servis sur 773 » (P9)
**Constat Vic** : « pourquoi on peut en voir que 50 ? rajoute le moyen de dérouler la liste + un moyen de filtrer par année ».
**Travail** : pagination « Voir plus — N / M chargés » par 200 (règle existante) ; filtre par année de mutation (chips d'années présentes dans les données, multi-sélection) ; le compteur reflète le filtre.

### R15 — Survol des cartes d'entrée d'outils : vert opaque (P10)
**Constat** : sur l'écran d'entrée PLU, « Annuaire PLU » a un contour vert au survol au lieu du vert opaque.
**Travail** : toutes les cartes d'entrée d'outils (PLU, Étude de zone, Scan patrimoine, etc.) appliquent la règle — vert opaque, contenu inversé sombre. Inventaire des cartes d'entrée dans le compte-rendu.

### R16 — Exemples de recherche : contraste au survol (P17)
**Constat** : sur les chips d'exemples (nom / SIREN / IDU / adresse), au survol le fond du libellé de type disparaît ou passe au vert et on lit moins bien.
**Travail** : le libellé de type garde un fond sombre plein et un texte clair sur ligne survolée (même mécanique que T6 pour les chips).

### R17 — SIREN / SIRET : bleu et souligné, partout
**Constat Vic** : « tous les SIREN/SIRET sont cliquables et de couleur bleue et soulignés, on comprend mieux comme ça que c'est cliquable ».
**Travail** : le composant `Siren` passe en bleu lien souligné. C'est **la seule exception** à la règle « pas de bleu » de la DA, et elle est justifiée : un lien externe doit ressembler à un lien. Vérifier les 7 surfaces inventoriées en T2 plus celles que Vic a vues (Acquisitions, fiche commune).

### R18 — Scan patrimoine : la liste ne doit pas être ouverte au départ (P19)
**Constat** : la liste des parcelles est déjà affichée sous le bouton « Voir ses parcelles → » — donc le bouton fait doublon.
**Travail** : au chargement, la liste est **repliée** ; « Voir ses parcelles → » l'ouvre et replie le bandeau (mécanique O5 conservée). Un seul état visible à la fois.

---

# LOT 3 — outils

### R19 — Trouver les parcelles : contour vert du bloc de résultat retiré (P2)
**Constat Vic** : « encore ce contour vert que j'avais demandé d'enlever ». Le bloc « 19 342 parcelles · 8 unités → SDP gabarit ≥ 576 m² » a une bordure verte.
**Travail** : bordure retirée. Inventaire des blocs de résultats à bordure verte résiduelle dans toute l'app et retrait de tous.

### R20 — Trouver les parcelles : paragraphe d'aide retiré (P3)
Le paragraphe « Décrivez votre programme — bâtiments, hauteur… Le Copilote peut remplir le formulaire pour vous » disparaît. Si une aide est nécessaire, elle vit derrière un `i`.

### R21 — Annuaire PLU : le nom de commune a disparu (P11)
**Constat Vic** : « oulà qu'est-ce que tu m'as fait ?? on voit plus le nom de la commune ». La carte affiche un badge « révision générale — règlement… » qui écrase le nom.
**Travail** : le nom de commune revient en premier, toujours visible. Le badge dit **« révision »**, un mot, à droite, sur une ligne. Pas « révision en cours — vérifier en mairie ».

### R22 — « 21 PLU disponibles » est faux (P12)
**Constat Vic** : « on en a 23, c'est pas parce que 3 sont en révision qu'il faut les enlever, sinon on a un trou — explique-moi ».
**Travail** : un PLU en révision **reste en vigueur** jusqu'à l'approbation du nouveau. Le compteur doit dire **23 PLU disponibles (24 communes, 1 en RNU) · 3 procédures en cours**. Mesurer ce qui produit 21 : si deux communes n'ont pas de règlement ingéré, ce sont des trous à nommer, pas à cacher dans un compteur. Écrire la liste des 24 avec leur état réel.

### R23 — Badge « révision générale du PLU » sur une seule ligne (P13)
Saint-André et Saint-Leu sur une ligne, Trois-Bassins sur deux. Largeur fixe du badge ou `white-space: nowrap`, sur toutes les cartes de procédure.

### R24 — Référence courte dans la vérification PLU (P14)
**Constat** : `BZ1065` saisi dans « un IDU → la commune est-elle en procédure » ne résout pas, alors que T1 promettait toutes les barres.
**Travail** : brancher cette barre sur le moteur unique. Puis **refaire l'inventaire T1** en testant réellement `BZ1065` dans chaque barre listée, et joindre le tableau barre × résultat. Toute barre qui échoue est corrigée dans ce mandat.

### R25 — Simulateur zone AU : accordéon « Attention » (P15)
Les deux blocs d'explication (« Périmètre : toute l'île — simulation hypothétique… » et « Recalcul à blanc — rien n'est persisté… ») passent dans un accordéon replié, libellé « Attention », déplié seulement au clic.

### R26 — Taxe d'aménagement : préremplir ce que LABUSE sait (P16)
**Constat Vic** : « c'est pas à moi de remplir le m² taxable, LABUSE a déjà la parcelle, le client ne remplit que ce que LABUSE ne connaît pas ».
**Nuance à respecter** : la surface taxable est celle du **projet** (surface de plancher créée), pas celle du terrain. LABUSE ne connaît pas le projet du client, mais connaît la **SDP constructible au gabarit** et la SDP existante.
**Travail** : préremplir la surface taxable avec la SDP constructible au gabarit (étiquetée « pré-rempli par LABUSE — SDP au gabarit, modifiable »), le terrain et la zone déjà posés. Le client ne touche que ce qui dépend de lui : résidence principale, surface réellement projetée s'il la connaît. Le calcul se met à jour en direct.

### R27 — Étudier un bien : zoom plus franc
**Constat Vic** : « le zoom est un peu timide ». Une adresse ou un IDU doit amener la parcelle à occuper une part nette de la carte (elle doit se lire comme la parcelle, pas comme un point dans un quartier). Régler le niveau cible de `focusParcelle` (padding réduit, zoom minimal 17-18 selon la surface). Cette primitive est partagée : le réglage s'applique aussi à R32.

### R28 — Étude de zone : bouton « Lire la zone » vert opaque
Le bouton principal de l'outil est terne (fond sombre, texte gris). Il doit être vert opaque, texte sombre, comme les autres boutons d'action principaux.

### R29 — Scan patrimoine : « CBO a que 20 opérations depuis 2013 ?? »
**Question Vic**, à traiter comme un doute sur un chiffre servi en confiance.
**Travail** : mesurer. Sitadel 974 depuis 2013 filtré sur le SIREN de CBO Territoria donne 20 opérations / 230 logements — mais CBO opère via des **SCI ou SNC d'opération** (un SIREN par programme), et Sitadel enregistre le demandeur du permis, pas la maison-mère. Établir : combien d'opérations Sitadel portent CBO en demandeur direct, combien portent une filiale identifiable (par nom contenant « CBO », par adresse de siège, par dirigeant commun via SIRENE), et ce que donne la réconciliation. Le chiffre affiché doit ensuite dire ce qu'il compte : « 20 opérations au nom de la société · N supplémentaires via ses filiales identifiées ». Jamais un total gonflé sans méthode.

### R30 — Permis : un chantier connu absent de la base (P20)
**Constat Vic** : « sur la parcelle 97418000AX0439 ou celles autour, il y a sûrement un permis — quelqu'un fait un hôtel là depuis plus de 3 ans, c'est en travaux, on le voit sur l'ortho. Regarde pourquoi ce permis passe outre ma base. »
**Travail** :
1. Chercher dans Sitadel brut (pas la table dérivée) tout permis à Sainte-Marie sur AX0439 et les parcelles adjacentes, 2021-2026, toutes natures (PC, PA, DP, hôtel = destination hébergement hôtelier).
2. Établir la cause parmi : millésime Sitadel en base trop ancien (dernier mois chargé ?), permis rattaché à une autre parcelle (division, remembrement, parcelle mère), champ parcelle vide dans Sitadel (fréquent : la géolocalisation est alors à l'adresse), filtre « logements » qui exclut les hôtels.
3. Corriger la cause. Si c'est le rattachement par adresse, brancher le repli adresse → parcelle. Si c'est le filtre, servir toutes les destinations avec leur nature. Si c'est la fraîcheur, documenter la cadence de mise à jour Sitadel et l'inscrire à la sentinelle.
4. Recette : la fiche AX0439 ou sa voisine montre le permis, daté, sourcé.

### R31 — Prospection solaire : simple / double pente, recherche réelle
**Constat Vic** : « fais une recherche approfondie, si on trouve pas c'est pas grave mais je pense qu'on peut trouver ».
**Pistes ouvertes par Fable le 05/09** :
- **LiDAR HD IGN** : le programme couvre les DROM (hors Guyane) d'ici 2026, et **La Réunion a été la première zone test** des cartographies dérivées du LiDAR HD (macarte.ign.fr, « Comparaison Plan Lidar sur la Réunion »). Vérifier la disponibilité des dalles sur le 974 via `macarte.ign.fr/carte/mThSup/diffusionMNxLiDARHD` et le téléchargement `cartes.gouv.fr/telechargement/IGNF_MNS-LIDAR-HD` (dalles 1 km, pas de 50 cm, GeoTIFF, licence ouverte).
- **Méthode** : MNS − MNT sur l'emprise du bâtiment (BD TOPO) = modèle de hauteur du toit ; un calcul de pente et d'orientation sur ce modèle donne les **plans de toiture** ; 1 plan dominant = monopente, 2 plans opposés = double pente, 4 = croupe. Sortie : nature du toit + pente + azimut de chaque pan, étiquetée **Dérivé (LiDAR HD IGN, méthode plans de toiture)** avec incertitude.
- **Replis** : nuage de points classé « bâtiment » si le MNS n'est pas encore diffusé ; OSM `roof:shape` là où renseigné (rare, étiqueté OSM).
**Travail** : vérifier la couverture 974, écrire ce qui est disponible (dalles, date, densité). Si disponible : prototype sur 20 bâtiments de test, contrôle visuel contre l'ortho, puis intégration si le taux de bonne détection dépasse 80 % sur l'échantillon. Si non disponible : compte-rendu daté avec la date prévue de diffusion, et le point est ré-ouvert à cette date par la sentinelle.

### R32 — Projets : l'œil doit zoomer plus
Même réglage que R27 sur `focusParcelle`. La parcelle vue depuis l'œil doit occuper l'écran comme dans Étudier un bien.

---

## Recette et livraison

- Recette dans un vrai navigateur sur la base réelle, **au cadrage et sur le fond que Vic a montrés**. Captures avant/après obligatoires pour tout travail visuel.
- Chaque défaut corrigé reçoit le test qui l'aurait attrapé.
- Compte-rendu `docs/audit-2026-09/RETOURS-13/COMPTE-RENDU.md` : une ligne par travail R1-R32 — fait / fait autrement (pourquoi) / pas fait (motif mesuré, URL par URL pour R4, R5, R31).
- Inventaires joints : infobulles (R10), cartes d'entrée (R15), blocs à bordure verte (R19), barres × référence courte (R24).
- Commits par lot, **jamais de merge par CC**.

## Case à cocher — 32 travaux

**Carte et couches**
- [ ] R1 — mer en Ortho IGN île entière : fond continu, plus d'escalier ni de blanc
- [ ] R2 — couche « Parcelles — classement LABUSE » : prouvée par capture ou retirée
- [ ] R3 — groupe « Réseaux » visible dans le menu Couches (HTB, HTA, TCSP, arrêts)
- [ ] R4 — moyenne tension ingérée depuis EDF Réunion open data (HTA aérien + souterrain) + postes sources
- [ ] R5 — BAOBAB retiré ; vraie couche TCSP (en service / en travaux / en projet), drapeau 800 m depuis la station (L151-36), sources PEIGEO-AGORAH / Région / EPCI / OSM
- [ ] R6 — mouvement de terrain : classe la plus grave en rouge, légende conforme aux classes réelles
- [ ] R7 — aléas sans hachures, opacité calibrée par fond
- [ ] R8 — contours d'aléas seulement au zoom, même règle sur les 4 fonds
- [ ] R9 — arrêts cliquables : nom + ligne(s) + réseau

**Tableaux, listes, survols**
- [ ] R10 — liste des communes : infobulle retirée, « voir la fiche » jaune opaque au survol
- [ ] R11 — tableau 24 communes : marges, infobulle retirée, « Fiche → » jaune au survol
- [ ] R12 — « Ouvrir le Radar → » centré sur la ligne de texte
- [ ] R13 — évolution du marché : même modale/tableau que « Les 24 communes »
- [ ] R14 — acquisitions : Voir plus par 200 + filtre par année
- [ ] R15 — cartes d'entrée d'outils : vert opaque au survol
- [ ] R16 — chips d'exemples : contraste au survol
- [ ] R17 — SIREN/SIRET bleu souligné partout
- [ ] R18 — Scan patrimoine : liste repliée au départ, plus de doublon

**Outils**
- [ ] R19 — Trouver les parcelles : contour vert du bloc de résultat retiré (+ inventaire)
- [ ] R20 — Trouver les parcelles : paragraphe d'aide retiré
- [ ] R21 — annuaire PLU : nom de commune visible, badge « révision » sur une ligne
- [ ] R22 — compteur « 23 PLU disponibles · 1 RNU · 3 procédures », trous nommés
- [ ] R23 — badge « révision générale du PLU » sur une seule ligne partout
- [ ] R24 — référence courte dans la vérification PLU + re-test réel de toutes les barres
- [ ] R25 — simulateur AU : accordéon « Attention » replié
- [ ] R26 — taxe d'aménagement : surface taxable préremplie (SDP au gabarit, modifiable)
- [ ] R27 — Étudier un bien : zoom franc sur la parcelle
- [ ] R28 — Étude de zone : « Lire la zone » vert opaque
- [ ] R29 — CBO 20 opérations : mesuré, filiales réconciliées, chiffre expliqué
- [ ] R30 — permis AX0439 Sainte-Marie : cause trouvée et corrigée, hôtel visible
- [ ] R31 — toiture simple/double pente : LiDAR HD 974 vérifié, prototype si disponible
- [ ] R32 — Projets : l'œil zoome comme Étudier un bien

---

## Prompt de lancement (à coller tel quel dans Claude Code, depuis `~/Desktop/labuse`)

> Étape 0 : `pwd`, branche courante, arbre propre. Tu dois être dans ~/Desktop/labuse sur `fix/retours-12`. Sinon arrête-toi et signale-le sans rien écrire.
>
> Lis `docs/audit-2026-09/RETOURS-13/MANDAT-RETOURS-13.md` en entier, puis les fichiers listés dans sa section « Contexte à lire ». Exécute les 32 travaux R1-R32 dans l'ordre des lots, sur la branche `fix/retours-12`. Un commit par lot.
>
> Pour R4, R5 et R31 : ouvre chaque URL listée et écris ce que tu y trouves avant de conclure à une absence. Pour R5, relis l'article L151-36 sur Légifrance avant d'écrire le seuil dans l'interface.
>
> Aucun travail visuel n'est « fait » sans capture avant/après au cadrage indiqué. Recette navigateur sur la base réelle avant chaque commit. Aucun sous-agent sur git, aucun `git add -A`, aucun merge.
>
> Compte-rendu final `docs/audit-2026-09/RETOURS-13/COMPTE-RENDU.md` : une ligne par travail R1-R32, les inventaires demandés joints.
