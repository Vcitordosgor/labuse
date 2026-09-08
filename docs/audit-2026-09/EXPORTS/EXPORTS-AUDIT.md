# EXPORTS — AUDIT des documents PDF (parcelle 97415000BO0852, Saint-Paul)

Date : 03/09/2026 · Rédigé par Fable · Lecture seule, aucun code touché.
Destination : `docs/audit-2026-09/EXPORTS/EXPORTS-AUDIT.md` (précède la maquette et le mandat EXPORTS-1).

Gravité : 🔴 faux ou contradictoire servi au client · 🟠 fuite / manque bloquant pour l'usage · 🟡 forme, précision, dette.
Nature : **FAUX** (donnée fausse ou contradictoire) · **FUITE** (clé interne, jargon scoring, note de travail) · **MANQUE** (absent pour l'usage réel) · **FORME** (hiérarchie, densité, DA v3, ruptures de page) · **FRAÎCHEUR** · **DOUTE** (à vérifier en base).

---

## 0. Périmètre reçu

| Reçu | Fichier | Contenu réel | Pages | Générateur |
|---|---|---|---|---|
| **[BANQUIER]** | `ARGUMENTAIRE.pdf` | « Dossier banquier · présentation financeur » | 9 | WeasyPrint 69 |
| **[DOSSIER]** | `DOSSIER.pdf` | « Dossier parcelle » DP-20260903-0852, modèle 1.4 | 9 | WeasyPrint 69 |
| **[FICHE]** | `PDF.pdf` | Export brut de la fiche écran (toutes sections) | 5 | inconnu — aucune métadonnée Producer, PDF 1.4 |
| **[PC]** | zip | CERFA 13406*17 pré-rempli + PCMI1/2/4/7-8 + règles-zonage + LISEZMOI | 20+2+1+1+2+2 | InDesign (CERFA) · WeasyPrint (notice, règles) · inconnu (plans) |

Trois constats sur le périmètre lui-même :

1. **Le fichier nommé `ARGUMENTAIRE.pdf` contient le Dossier banquier.** Soit mauvais fichier, soit le bouton Argumentaire sert le gabarit banquier → à confirmer par Vic (DOUTE-0).
2. **[DOSSIER] porte une phrase du parcours Flash** (§09 : « le parcours Flash ne précise pas encore l'activité étudiée »), un numéro de rapport et une version de modèle → c'est très probablement le builder du Flash (ou son gabarit copié). Vic pensait ne pas avoir envoyé le Flash : il faut trancher lequel des deux est le Flash vendu 79 €.
3. **Non reçus** : Lettre de vérification de zonage, Argumentaire (vendeur), Flash (si ≠ [DOSSIER]), captures écran de la fiche, destinataires par document. La cohérence « exports ↔ écran » est jugée ici via [FICHE], miroir de l'écran — à confirmer sur captures.

**Trois chaînes de rendu coexistent** (WeasyPrint · générateur sans métadonnées pour [FICHE] et les plans PCMI · CERFA InDesign) — l'objectif « un seul builder PDF » de CONNEXIONS-2 n'est pas atteint côté [FICHE] et plans.

---

## 1. Verdict

**Le socle est un seul moteur, et ça se voit** : risques, viabilisation, assainissement, réhabilitation, règles calibrées, zonage, ZAN, SRU sont rendus à l'identique dans les quatre documents (mêmes phrases, mêmes chiffres, même date 03/09). Aucun chiffre servi n'est à zéro par oubli sauf un (D3). Les mentions « ce que ce document ne peut pas dire » sont justes et utiles.

**Mais trois familles de défauts rendent les exports indéfendables devant un tiers aujourd'hui :**

1. **Contradictions servies noir sur blanc** — 9 chiffres différents pour « le prix » (§4), 4 verdicts de constructibilité incompatibles (D2), clause de mixité sociale « imposée » ici / « non déclenchée » là (B2), « pas d'accès à la voirie » et « façade sur voie au contact » dans le même document (F2), un banquier à qui l'on présente un scénario table rase à 175 k€ de charge foncière sur une parcelle dont le bâti « justifie ~3,65 M€ » (B1).
2. **Fuites** — 30+ occurrences de clés internes, jargon de scoring, notes de calibration et disclaimer de modèle IA dans des documents clients (§5). La règle « jamais de clé interne ni de jargon de scoring » est violée dans les 4 documents.
3. **Forme** — [BANQUIER] tient sur 4 pages et en occupe 9 ; en-têtes orphelins ; chips ESTIMÉ en ambre (= Projet en DA v3) ; la seule prose IA est en vert (= devrait être mauve) ; corps de [FICHE] illisible (~7 pt).

**Fraîcheur** : les données sont lues à la génération (rien n'indique un instantané figé), donc les PDF **suivent le pointeur** — mais aucun document ne le prouve : 10 sources « millésime non renseigné », une seule date « Valeurs au 2026-08-22 » et elle sert avec une clé de run. Seul un test doré (annexe A) répondra durablement à « figé ou pas ».

---

## 2. Lecture document par document

### 2.1 [BANQUIER] — Dossier banquier (ARGUMENTAIRE.pdf)

| ID | Grav. | Nature | Constat | Correctif attendu |
|---|---|---|---|---|
| B1 | 🔴 | FAUX | Le hero et la synthèse vendent un **scénario table rase** (635 m² vendables, 7–9 logts, charge foncière 175 k€) sur une parcelle bâtie à 73 % (540 m², 2 bâtiments, 9,4 m). Le même document dit p.8 « surface constructible déjà consommée par le bâti » et « ce que la réhabilitation du bâti justifie : ~3,65 M€ » — soit plus que le CA neuf (3,00 M€) — et « terrain nu au prix du secteur ~570 k€ » (3,3× la charge foncière). Un banquier lit : « pourquoi démolir ? ». | Le bilan choisit son scénario selon l'état de la parcelle : bâti dense → **réhabilitation / surélévation** en scénario principal, table rase en second **avec la démolition chiffrée** ; ou deux colonnes côte à côte avec une phrase de verdict. |
| B2 | 🔴 | FAUX | « Clause de mixité sociale — **non déclenchée** — pas de quota LLS sur ce programme » vs [FICHE]/[DOSSIER] « Secteur de mixité sociale : Clause logements aidés — **quota imposé** (impacte le bilan) ». Contradiction sur un poste du bilan. | Si c'est un seuil (quota applicable à partir de N logts, programme 7–9 en dessous) : l'écrire (« applicable au-delà de N logements — non déclenchée pour 7–9 logts, à confirmer au règlement »). Un seul moteur « mixité » lu par la fiche et le bilan. |
| B3 | 🔴 | FUITE | La **Synthèse exécutive est de la prose IA** rendue dans un cadre **vert**, suivie du disclaimer de modèle « *L'IA ne juge pas le sentiment d'une communauté, n'évalue pas le risque politique d'un processus d'autorisation, et ne remplace pas les éléments relationnels du sourcing* » — livré tel quel au banquier. Phrases boiteuses (« rendant la construction constructible », « la marge n'étant pas fournie en valeur absolue… »). | Deux options : (a) synthèse **déterministe** à trous, remplie par le moteur (recommandé pour un tiers) ; (b) prose IA balisée **mauve** avec mention « rédaction assistée, chiffres vérifiés en base ». Le disclaimer de modèle disparaît dans les deux cas. |
| B4 | 🟠 | FUITE | « contour cadastral réel inseté de 3 m (**ST_Buffer, EPSG:2975**) » · « Recul voirie « **à_vérifier** » pour U1a » · « Voir la **fiche commune** pour budget/reste » (renvoi vers l'app, que le banquier n'a pas). | Formulations métier : « contour réduit de 3 m (reculs) » · « recul sur voie non calibré → hypothèse prudente 5 m » · supprimer les renvois app. |
| B5 | 🟠 | FAUX | Recul appliqué **3 m** dans le calcul (441 m²) mais avertissement « hypothèse prudente **5 m** » sur la voirie : lequel est dans le chiffre ? | Une seule valeur de recul par façade, affichée dans la ligne de calcul. |
| B6 | 🟠 | FAUX | Chaîne : 8–10 logts → plafond densité 8–9 → stationnement ≤ 19 → « retenus **7 à 9** ». Le 7 ne sort d'aucune ligne ; la synthèse le reprend. | Le résultat final = intersection affichée des bornes, sans borne fantôme. |
| B7 | 🟠 | FAUX | « Prix de sortie neuf (marché) **4 730 €/m²** ESTIMÉ » sans méthode ; = 3 818 × 1,24 (dérivé de l'ancien). Or la base sert un **VEFA commune à 5 003 €/m² (80 ventes / 3 ans)** dans [FICHE] et à l'écran. Deux moteurs pour « prix neuf ». | Un seul : VEFA secteur si n ≥ seuil, sinon VEFA commune, sinon **Dérivé** affiché avec sa formule (« ancien × 1,24 ») — et la nature affichée dans tous les cas. |
| B8 | 🟠 | FAUX | Même page : « Fiabilité du bilan : **fiable** » et « Marge **NON ESTIMABLE — données de marché insuffisantes** », alors que les comparables sont « fiable, 25 ventes ». La marge manque un **prix d'acquisition**, pas des données de marché. | « Marge : renseignez le prix d'acquisition envisagé (Projet) » — et le calcul suit. |
| B9 | 🟠 | FORME | Hero « **175 k€ médiane** » : c'est le centre d'une fourchette **−23 k€ → 374 k€** (±100 %), pas une médiane. Le chiffre-titre n'est pas décisionnel. | Hero à trois bornes (plancher / central / haut) + « ≈ 236 €/m² terrain » ; « central » à la place de « médiane ». |
| B10 | 🟡 | DOUTE | « VRD / viabilisation ~83 k€ » sur une parcelle déclarée « raccordement a priori SIMPLE » et en tout-à-l'égout. Forfait aveugle ? | Afficher la règle (% du CA ou €/m²) ou moduler par le faisceau de viabilisation. |
| B11 | 🟡 | FORME | ZAN en **ha totaux** ici (435 / 90 ha), en **m²/an** dans [DOSSIER] (434 928 / 300 038) — même moteur, deux unités. « Pleine terre 10 % » ici vs « espaces libres perméables sans sous-minimum de pleine terre » dans la note de calibration [FICHE] — mauvais terme. | ha/an partout ; « espaces libres perméables ». |
| B12 | 🟡 | MANQUE | « Permis voisins ≤ 5 ans » = les **5 plus proches** (31→168 m) : le PC de **8 logements à 09/2025** (< 500 m, [DOSSIER] §06) n'y figure pas — c'est pourtant l'opération comparable qui intéresse un financeur. Colonne DATE = colonne STATUT (« autorisé le … » répète la date). | Lister les N plus **significatifs** (logements, récence) ; supprimer la colonne redondante. |
| B13 | 🟠 | MANQUE | Pour l'usage financeur, il manque : identité du porteur, **prix d'acquisition envisagé**, coût total (foncier + démolition + construction + frais + TA), marge en € à partir du prix, apport / LTV, calendrier (le délai d'instruction 9 mois existe dans [DOSSIER] §07 mais pas ici), état du bâti existant (DPE ADEME, année BDNB), **taxe d'aménagement** (l'outil existe), marché de la zone (§09 absent ici). | Bloc « **Paramètres du projet** » en ambre (saisis par le client dans Projet) qui alimente marge, LTV, coût total ; sections calendrier / bâti existant / TA / zone. |
| B14 | 🟡 | FORME | 9 pages pour ~4 pages de contenu (une section = une page ; p.2 carte seule ; p.8–9 quasi vides). Chips **ESTIMÉ en ambre** = couleur Projet en DA v3. Bandeau de réserve en ambre. Pas de sommaire. | Pagination fluide (rupture seulement avant Bilan et Risques) ; chips : Sourcé mint · Estimé gris · Dérivé gris + ƒ ; ambre réservé aux paramètres Projet. |
| B15 | 🟡 | FRAÎCHEUR | Ni « données au », ni version de modèle, ni n° de rapport (le [DOSSIER] a les trois). | Cartouche commun à tous les exports (§6). |

### 2.2 [DOSSIER] — Dossier parcelle DP-20260903-0852 (DOSSIER.pdf)

| ID | Grav. | Nature | Constat | Correctif attendu |
|---|---|---|---|---|
| D1 | 🔴 | FUITE | « Valeurs au 2026-08-22 — **run m135-run2-ile** » servi au client. Clé de run + révèle un résiduel de 12 jours que q_v12 va remplacer (résiduel corrigé). | « Données LABUSE au 22/08/2026 » sans clé, alimenté par le pointeur servi. |
| D2 | 🔴 | FAUX | **Quatre verdicts de constructibilité incompatibles** : (a) §02 « Emprise résiduelle constructible **127 m²** » + « Surélévation envisageable » ; (b) même page « scénario retenu neuf **635 m² / 7–9 logts** » ; (c) [FICHE] « **Aucun** droit à bâtir résiduel au sol (densité atteinte). Seule marge : surélévation (~6,6 m) » ; (d) §08 et [BANQUIER] p.8 « surface constructible **déjà consommée** ». La marge de surélévation est calculée sur le **faîtage 16 m** (→ 6,6 m) alors que le scénario neuf compte les niveaux sur l'**égout 12 m** (→ 2,6 m < 2,8 m : surélévation impossible). | Un seul bloc « Potentiel » à trois lignes issues d'un seul moteur : **au sol** (emprise et SDP résiduelles), **en hauteur** (surélévation, référence de hauteur tranchée : égout ou faîtage), **table rase** (neuf, démolition chiffrée) + une phrase de verdict. |
| D3 | 🔴 | FAUX | « Marché immobilier de la zone — **Annonces actives : 0** » = zéro de couverture (Radar en amorçage : 108 annonces, 7 rattachées) servi comme un fait. | « Radar : couverture partielle — non servi » ou omettre la colonne. Jamais un zéro inventé. |
| D4 | 🟠 | FUITE | « *le parcours Flash ne précise pas encore l'activité étudiée. L'outil « Étude de zone » la fournit sur demande* » — renvoi produit, et phrase du gabarit Flash dans le Dossier. | « Analyse de concurrence par activité : disponible sur demande » ou rien ; l'activité étudiée devient un paramètre Projet (ambre). |
| D5 | 🟠 | FAUX | Pied de §09 : « Sources : INSEE (Filosofi, **MOBPRO**), SIRENE, BPE, DVF, IGN, **Radar LABUSE** ». MOBPRO a été **écartée** le 28/08 (jamais ingérée) ; Radar ne sert rien ici. Fausse citation de source. | Le pied de section se génère depuis les sources **réellement lues** par la section. |
| D6 | 🟠 | FAUX | Marché commune : « Prix ancien médian **3 766 €/m² (appartement, n 11)** » à côté de « tendance … (n 218/583) ». Onze ventes pour tout Saint-Paul (136 ventes/trimestre) = requête mal scopée. Idem [FICHE] p.1. Et « Comparables de proximité : 22 ventes dans un rayon de 500 m sur 3 ans » **sans la médiane** (le nombre est annoncé, la valeur n'est pas imprimée). | Supprimer la ligne « n 11 » ; toutes les valeurs de prix depuis le moteur secteur (§4). |
| D7 | 🟠 | FAUX | Comparables : « **Appartement 750 m²** · terrain 170 m² · 4 500 000 € · **6 000 €/m²** » = mutation d'immeuble entier classée appartement. La note dit « ventes au prix/m² aberrant écartées » ; [FICHE] montre **10 135 €/m²** et **814 €/m²** dans la même liste. Le filtre diffère selon l'export. | Un seul filtre de plausibilité (type × surface, €/m² hors [p5 ; p95], dédoublonnage par mutation multi-lots) partagé par tous les exports et l'écran. |
| D8 | 🟠 | DOUTE | Permis : « **17** autorisations (500 m · 24 mois) » ici vs [FICHE] « **17** PC à ≤ 400 m sur **5 ans** » — même nombre, deux définitions. [BANQUIER] « ≤ 5 ans » ; [FICHE] « 0 permis < 100 m / 36 mois » vs « 6 permis autorisés < 100 m » (viabilisation). Quatre fenêtres, un chiffre douteux. | Une seule définition (rayon × fenêtre) affichée partout ; vérifier en base laquelle des deux étiquettes du 17 est vraie. |
| D9 | 🟠 | FAUX | Tableau « Installations classées (ICPE) » : « ENGEN (ex CALTEX) — **Non ICPE** — 158 m » et la ligne risque dit « Installation classée (ICPE) à proximité ». | Si le régime Géorisques est « non ICPE / autre », ne pas titrer ICPE ; vérifier la donnée (une station-service est en général une ICPE à déclaration). |
| D10 | 🟡 | FUITE | « Prescriptions graphiques : **zonage d'eau pluviale - zone reglt Forte** » — libellé brut GPU (aussi dans [PC]). | « Zonage pluvial — secteur à règlement fort (rétention / infiltration imposée) ». |
| D11 | 🟡 | MANQUE | « Abords MH ~500 m (tampon) » : quel monument, à quelle distance réelle ? « ~500 m » se lit comme une distance alors que c'est le rayon du tampon. | « Dans le périmètre des abords de [monument] (à X m) — avis ABF probable ». |
| D12 | 🟡 | FAUX | « Équipements les plus proches » : « Enseignement — **FORMA OUEST INSERTION** », « Santé — **MONTAGNON LAETITIA** » (nom d'une personne physique publié), « Services — REUNION OUEST IMMOBILIER ». Cinq « plus proches à 2 min » ne disent rien d'une zone de 19 617 habitants. | Comptes par catégorie (X écoles, Y commerces, Z santé…) + équipements structurants (Super U, gare, collège) ; jamais de nom de professionnel libéral. |
| D13 | 🟡 | FORME | Isochrone **10 min voiture** pour une parcelle de 742 m² de centre-ville : la zone va de Saint-Gilles à Rivière des Galets. Pour le contexte parcelle, 10 min à pied / 5 min voiture sont plus parlants ; pour la chalandise, le mode/temps est un paramètre Projet. | Deux réglages : contexte parcelle (piéton) par défaut, chalandise sur paramètre. |
| D14 | 🟡 | FORME | « Revenu médian **20 978 €** » (zone) vs [FICHE] « niveau de vie médian **~25 993 €** (carreau 200 m) » — deux périmètres, deux libellés. | Le périmètre dans le libellé, un seul terme (niveau de vie). |
| D15 | 🟡 | FRAÎCHEUR | §10 « Sources & millésimes » : « **millésime non renseigné** » ×10, « Etalab cadastre « latest » ingérée », « édition non enregistrée » — dans un tableau qui promet la synchronisation. | Renseigner (Géorisques = date d'extraction, BAN mensuelle, Mérimée, OSM = date d'extrait, BD TOPO/RGE ALTI = édition) ou masquer la cellule ; chantier « cadences » de la sentinelle. |
| D16 | 🟡 | FORME | Mentions + Sources **avant** « 11 Ce que ce document ne peut pas dire » ; p.7 = **3 lignes orphelines** (note * de §09) ; « Densifier l'existant » orphelin en tête de p.3 ; sous-titre « **Étude de faisabilité** indicative » contredit §02 « ce n'est pas une étude de faisabilité réglementaire » ; « zone bleue PPR » dans un encadré **rouge**. | §11 clôt le document ; keep-with-next sur notes et sous-titres ; sous-titre « Étude foncière indicative » ; accent PPR bleu. |
| D17 | 🟡 | FRAÎCHEUR | « **DVF 2026** » = millésime de publication ; les ventes vont jusqu'à fin 2025. « SRU inventaire 01/01/2024 » alors que l'inventaire 2025 est publié (DOUTE). | « DVF (ventes → 12/2025, publication 04/2026) » ; vérifier SRU 2025. |
| D18 | 🟡 | MANQUE | Pas d'**Analyse LABUSE** (palier Priorité / À suivre + trois raisons en français) alors que c'est le document du client lui-même. | À trancher par Vic (§7) — jamais RR / base / score, seulement le palier et ses raisons. |

### 2.3 [FICHE] — export brut de la fiche écran (PDF.pdf)

| ID | Grav. | Nature | Constat | Correctif attendu |
|---|---|---|---|---|
| F1 | 🔴 | FUITE | Jargon de scoring servi : « **(0 pt, anti-double-compte)** », « **(score 1.00)** », « **SIGNAL DE ZONE** », « (densité 100 % du **plafond 15**) », « **non éliminatoire** », « Contexte de marché favorable », « **hors scoring** » ×2, « + N **sans signal**, regroupés en fin de document » ×4, « 18 points sans signal », « **Contrôle géométrique OSM : aucun faux positif** », « (0 m d'axes, **densité 0.00**, bâti 73%) », « **Segment renouvellement urbain** », « Bâti d'origine : **deja_bati** », « (**groupe 0**) », « **acquérable** », « **RPG.LATEST, année non pinnée** », « **fiabilité suivie / à confirmer** » ×28, « **proxy** » ×3, légende ortho « (**piscine, 90,7 %**) » (confiance FLAIR). | Un gabarit client distinct de la vue de contrôle : aucune de ces chaînes ne doit pouvoir atteindre un export (test « mots interdits », annexe A). |
| F2 | 🔴 | FAUX | p.2 « **Accès voirie : Pas d'accès direct évident à la voirie** » vs p.3 « **Façade sur voie publique urbanisée — voie au contact** » — pour le 103 Chaussée Royale, sur la Chaussée Royale. Faux négatif sur un fait de premier rang (boussole). | Un seul test d'accès voirie, celui de la viabilisation ; vérifier la géométrie OSM/BD TOPO du N1A / Chaussée Royale. |
| F3 | 🟠 | FAUX | Propriétaire à la fois **catégorisé** (« Foncier public : Propriétaire PM « Personnes morales non remarquables » (groupe 0) — acquérable »), **inconnu** (« Propriétaire (personne morale) non renseigné pour cette parcelle ») et **sondé** (« BODACC : aucune procédure — propriétaire sondé le 19/08/2026 »). Le titre « Foncier public » est faux pour une PM privée. | Une ligne : « Propriétaire : personne morale privée (non nominatif) » ou « non renseigné » — pas les deux ; BODACC seulement si un SIREN a été sondé. |
| F4 | 🟠 | FUITE | Notes de calibration servies : « Art. 6, p.14-16 : **valeurs multiples (alignement/3/6/8 m) non attribuables sûrement à la sous-zone** », « (**page corrigée à la consolidation**) », « (**doctrine a**) ». | Citations propres (article, page, règle retenue) ; les notes restent dans l'admin. |
| F5 | 🟠 | FAUX | Proximités hors de portée présentées comme des faits utiles ou des contraintes : « Téléphérique Bois de Nèfles — **23 793 m** », « Ligne haute tension (90 kV) à **~3 487 m** — contrainte potentielle (servitudes, reculs) ». | Seuils : transport ≤ 1 km, HT ≤ 300 m, sinon absent. |
| F6 | 🟠 | FAUX | « Secteur — autre : médiane **— €/m² (20 ventes)** » (20 ventes sans médiane) ; VEFA 5 003 €/m² (n 80) présent ici et ignoré par le bilan (B7). | Calculer ou supprimer la ligne ; un moteur prix (§4). |
| F7 | 🟠 | DOUTE | « Parc social commune : 7 265 logements · **100.0 % en QPV** » — invraisemblable pour Saint-Paul (jointure QPV probablement sur un sous-ensemble). | Vérifier en base ; ne pas servir tant que non expliqué. |
| F8 | 🟡 | FORME | Bloc **RTAA DOM** de 12 lignes en page 1 : utile à un architecte, pas à un client foncier. | Annexe du Pré-dossier PC / Dossier expert, pas en tête de fiche. |
| F9 | 🟡 | FAUX | Comparables : 12 lignes avec 10 135 et 814 €/m² (cf. D7) ; « (millésimes géo-DVF disponibles) » ×4. | Filtre unique ; libellé « ventes 2021-2025 ». |
| F10 | 🟡 | FORME | « Potentiel foncier Région » **deux fois** dans les points sans signal ; « RPG proxy » ; « Cartofriches » et « Cavités » sans millésime. | Dédoublonner ; les points sans signal en une ligne (« Aucun signal sur : forêt publique, parc national, RPG, cavités, 50 pas, hydrographie, espace protégé, mouvement de terrain, ravine, sols pollués, érosion, friche »). |
| F11 | 🟡 | FORME | Générateur différent (pas de Producer) = 2ᵉ chaîne de rendu ; corps ~7 pt illisible ; en-têtes orphelins bas de p.1 (« RÈGLES D'URBANISME ») et bas de p.2 (« DISPOSITIFS TERRITORIAUX ») ; p.4–5 = listes de sources / points sans signal ; chips Sourcé/Estimé sur 2 blocs seulement ; pas de n° de rapport. | Ce document devient le **Dossier expert** rendu par le builder commun (§6) — ou disparaît si [DOSSIER] joue ce rôle. |
| F12 | 🟡 | DOUTE | ZFANG « réf. Décret n° 2026-421 du 29 mai 2026 (LF 2026, art. 18) » — référence à vérifier sur Légifrance avant de la servir. Bien : « Périmètre DÉRIVÉ par LABUSE… (Estimé) » pour la bande QPV 500 m. | Lien Légifrance dans la ligne. |
| F13 | ✅ | — | **À garder** : orthophoto + contour + échelle + nord (meilleur plan de situation des 4 docs) · « Fraîcheur du zonage (GPU vs mairie) » (seul document à l'avoir → à généraliser) · gestionnaires de réseaux · dispositifs fiscaux avec Dérivé affiché · articles du PLU cités. | |

### 2.4 [PC] — Pré-dossier permis de construire (zip)

| ID | Grav. | Nature | Constat | Correctif attendu |
|---|---|---|---|---|
| P1 | 🟠 | FAUX | Pack **maison individuelle** (CERFA 13406, PCMI1–8) servi pour une parcelle dont le scénario retenu ailleurs est un **collectif 7–9 logements** (CERFA 13409, pièces PC1–PC8). Le pack contredit le Dossier. | Choisir le CERFA selon le projet (13406 PCMI · 13409 PC · 13404 DP) avec la liste de pièces qui va avec ; à défaut, l'annoncer en tête : « pack calibré maison individuelle ». |
| P2 | 🟠 | MANQUE | « Servitudes et périmètres connus » ne liste que des **risques** ; la **SUP PM1** ([FICHE]) et surtout les **abords MH / avis ABF** — déterminants pour un PC — n'y sont pas. | Servitudes par code + signification + effet sur le PC (ABF = avis conforme/simple, délai majoré). |
| P3 | 🟠 | MANQUE | PCMI4 notice terrain : pas d'**adresse**, pas le **PPR zone bleue** (prescriptions à intégrer au projet), pas le **bruit cat. 1** (isolement acoustique) — ce que l'instructeur vérifie. « Source : viabilisation LABUSE » n'est pas une source pour une mairie. | Le § terrain reprend adresse, PPR, bruit, SUP, ABF ; sources publiques nommées (DEAL, Cerema). |
| P4 | 🟡 | FUITE | PCMI2 : « (contour cadastral **2975**) » = code EPSG ; « enveloppe ~40 × ~38 m » (= 1 520 m²) pour 742 m² ; largeur réelle ~21 m × ~36 m ([FICHE]) serait l'info utile ; **un seul polygone** bâti alors que la fiche dit 2 bâtiments ; pas de cotes des limites. | Cotes des côtés, deux bâtiments, échelle 1/500 vraie. |
| P5 | 🟡 | FORME | PCMI1 vue d'ensemble : parcelle **invisible** (contour de 2 mm) ; tuile blanche en haut à gauche (ortho manquante) ; ortho là où un fond IGN Plan / cadastre est lisible ; échelles attendues 1/25 000 et 1/2 000 (ratio + barre) ; deux vues = deux pages à moitié vides. | Repère + cercle, fond plan, ratio d'échelle, une page. |
| P6 | 🟡 | FORME | règles-zonage : ligne PCMI8 **coupée** sur deux pages (p.2 = une ligne) ; « zone reglt Forte » brut. | keep-together sur les lignes. |
| P7 | ✅ | — | **À garder** : LISEZMOI honnête (superficie non servie, adresse BAN à vérifier, checklist réelle), CERFA millésime vérifié le 21/08, nommage {IDU}-labuse, 9 champs pré-remplis justes (préfixe 000, n° 852). | |
| P8 | 🟡 | MANQUE | La **taxe d'aménagement** (outil existant), le **délai d'instruction** ([DOSSIER] §07) et les **articles du PLU U1a** ([FICHE]) manquent à « règles-zonage », qui est précisément l'aide à la préparation. | Ajouter les trois. |

---

## 3. Contradictions croisées — même donnée, valeurs différentes

| Donnée | [BANQUIER] | [DOSSIER] | [FICHE] | [PC] | Verdict |
|---|---|---|---|---|---|
| Constructibilité résiduelle | table rase 635 m² / 7–9 logts | 127 m² d'emprise + surélévation + table rase 635 m² | « aucun droit résiduel au sol, surélévation 6,6 m » | — | 🔴 D2 |
| Mixité sociale | non déclenchée, 0 quota | clause logements aidés (prescription) | quota imposé, impacte le bilan | clause logements aidés | 🔴 B2 |
| Accès voirie | — | façade sur voie (viabilisation) | « pas d'accès direct » ET « voie au contact » | — | 🔴 F2 |
| Prix « neuf » | 4 730 €/m² (dérivé) | — | VEFA 5 003 €/m² (n 80) | — | 🟠 B7 |
| Prix ancien | 3 818 (25 ventes, 500 m) | 3 766 (n 11) · 4 490 (n 218) · 4 561 (zone) | 3 766 (n 11) · 3 804 (36 ventes) | — | 🟠 §4 |
| Comparables (même liste) | 22 ancien + 3 VEFA | 5 lignes, « aberrants écartés » | 12 lignes dont 10 135 et 814 €/m² | — | 🟠 D7 |
| Permis autour | 5 plus proches (≤ 5 ans) | 17 (500 m · 24 mois) | 17 (400 m · 5 ans) · 0 (100 m · 36 mois) · 6 (< 100 m) | — | 🟠 D8 |
| ICPE ENGEN | « installation classée » | « Non ICPE » | « installation classée » | « installation classée » | 🟠 D9 |
| Recul | 3 m calculé / 5 m « prudent » | — | Art. 6 « valeurs multiples » | — | 🟠 B5 |
| Hauteur de référence surélévation | égout 12 m (niveaux) | faîtage 16 m (envisageable) | faîtage 16 m (6,6 m) | 12 / 16 | 🟠 D2 |
| ZAN | 435 ha · 90 ha (totaux) | 434 928 · 300 038 m²/an | — | — | 🟡 B11 |
| Revenu | — | 20 978 € (zone 10 min) | 25 993 € (carreau 200 m) | — | 🟡 D14 |
| Propriétaire | — | — | catégorisé / inconnu / sondé | — | 🟠 F3 |

Cohérents partout (à ne pas toucher) : 742 m² · U1a 100 % · 97415_PLU_20251217 · 668 / 12 / 16 m · bâti 540 m² / 9,4 m · PPR bleue · bruit cat. 1 · ICPE 158 m (distance) · ABF · assainissement collectif · pente 1,3° · SRU 18,3 % · réhabilitation 3,65 M€ · terrain nu 570 k€ · 768 €/m² terrain · viabilisation (4 indices) · PVGIS 1 280 kWh/kWc/an.

---

## 4. « Un seul moteur par donnée » — le cas du prix

Neuf valeurs de « prix » sur une même parcelle, chacune avec son périmètre, jamais hiérarchisées :

| # | Valeur | Périmètre / effectif | Où |
|---|---|---|---|
| 1 | 3 766 €/m² | « commune », appartement, **n 11** | [DOSSIER] p.3, [FICHE] p.1 |
| 2 | 3 804 €/m² | secteur, appartement, 36 ventes 2021-25 | [FICHE] hero + p.3 |
| 3 | 3 818 €/m² | 500 m adaptatif, 25 ventes 2022-25 | [BANQUIER] p.1, p.6 |
| 4 | (non imprimé) | 500 m · 3 ans, 22 ventes | [DOSSIER] p.3 |
| 5 | 4 490 €/m² | commune, 12 mois, n 218 | [DOSSIER] p.3, [BANQUIER] p.6 |
| 6 | 4 561 €/m² | isochrone 10 min, 104 ventes / 12 mois | [DOSSIER] p.6 |
| 7 | 4 730 €/m² | « prix de sortie neuf », dérivé ×1,24 | [BANQUIER] p.5 |
| 8 | 5 003 €/m² | VEFA commune, 80 ventes / 3 ans | [FICHE] p.3, écran |
| 9 | 4 927 €/m² · 768 €/m² | maison secteur (24) · terrain secteur (12) | [FICHE] p.3, [DOSSIER] p.5 |

Cible : **le moteur secteur (« Mon secteur » — exclusion des 5 % extrêmes, segments type × période, rayon adaptatif jusqu'à n min, rayon effectif affiché)** alimente tous les exports et l'écran avec quatre sorties — ancien appartement · ancien maison · terrain · neuf VEFA — chacune avec (médiane, n, rayon effectif, période). La tendance commune (n 218/583) reste un bloc distinct, étiqueté « commune ». Les lignes 1, 4 et 7 disparaissent.

Même règle pour : comparables (un filtre), permis (une fenêtre), constructibilité (un bloc à trois lignes), mixité (un moteur), accès voirie (un test).

---

## 5. Fuites — inventaire (règle « jamais de clé interne ni de jargon de scoring »)

| Type | Occurrences |
|---|---|
| Clés / identifiants internes | `run m135-run2-ile` · `EPSG:2975` ×2 · `ST_Buffer` · `à_vérifier` · `deja_bati` · `groupe 0` · `RPG.LATEST` · `zone reglt Forte` ×3 |
| Jargon de scoring | `0 pt, anti-double-compte` · `score 1.00` · `SIGNAL DE ZONE` · `plafond 15` · `non éliminatoire` · `hors scoring` ×2 · `sans signal` ×5 · `acquérable` · `Segment renouvellement urbain` · `Contexte de marché favorable` |
| Notes de travail / QA | `page corrigée à la consolidation` · `doctrine a` · `valeurs multiples … non attribuables sûrement` · `Contrôle géométrique OSM : aucun faux positif` · `densité 0.00` · `année non pinnée` · `fiabilité suivie / à confirmer` ×28 · `proxy` ×3 · `édition non enregistrée` · `« latest » ingérée` · `(piscine, 90,7 %)` |
| Texte de modèle IA | « L'IA ne juge pas le sentiment d'une communauté … sourcing » |
| Renvois vers l'app | « Voir la fiche commune » · « le parcours Flash » · « L'outil « Étude de zone » » · « figure au dossier parcelle » |

Toutes dans [FICHE] sauf : D1, D4, D10 ([DOSSIER]), B3, B4 ([BANQUIER]), P4, P6 ([PC]).

---

## 6. Fraîcheur et figement

**Les PDF suivent-ils les données ?** Oui, très probablement : rien n'indique un instantané stocké, les quatre documents portent la même date et les mêmes valeurs, et la seule date de données affichée (« Valeurs au 2026-08-22 ») est celle du résiduel servi par pointeur. Conséquence : **à la bascule q_v12, les chiffres 127 m² / 635 m² / 7–9 logts changeront** dans tous les exports (résiduel corrigé). Deux réserves :

- **Aucun document ne le prouve** : trois exports sur quatre n'ont ni « données au », ni version de modèle ; seul un test doré (annexe A) le garantira à chaque commit.
- **Le Flash vendu 79 € doit être l'exception** : un document payé doit être **archivé tel que livré** (PDF + JSON d'entrée) — reproductible et opposable à une réclamation — alors que les exports d'abonné se régénèrent à la demande.

État des millésimes lus (au 03/09/2026) :

| Source | Servi | Attendu | État |
|---|---|---|---|
| PLU Saint-Paul (GPU) | 2025-12-17 | idem, « à jour du GPU » | ✅ |
| Sitadel | 2026-07 | mensuel | ✅ |
| BD ORTHO | 2025 | — | ✅ |
| BPE · Filosofi · RP · RPLS · QPV · sonore · PPR · gestionnaires | 2025 · 2021 · 2023 · 01/2025 · 2024 · 12/2023 · 2011-2026 · 2026-07 | derniers disponibles | ✅ |
| DVF | « DVF 2026 », ventes 2021-2025 | libeller la période des ventes | 🟡 D17 |
| SRU | inventaire 01/01/2024 | inventaire 2025 publié | 🟡 DOUTE |
| ENAF Cerema | 2009-2024 (publié 05/2025) | mise à jour 2025 attendue | 🟡 DOUTE |
| PM DGFiP | 2019→2025 | millésime 2026 (situation 01/01) ? | 🟡 DOUTE |
| Cadastre · BAN · Géorisques ×5 · Mérimée · OSM · BD TOPO · RGE ALTI · Cartofriches · SUP | « non renseigné » / « latest » / « édition non enregistrée » | date d'extraction ou édition | 🟠 D15 |
| Résiduel | run du 22/08 (clé servie) | pointeur, sans clé | 🔴 D1 |

---

## 7. Ce qui manque pour l'usage réel (par destinataire)

| Document | Destinataire (hypothèse) | Manque |
|---|---|---|
| Dossier expert ([DOSSIER] ou [FICHE], à trancher) | le client | Analyse LABUSE (palier + 3 raisons, jamais de métrique) · propriétaire PM nominatif quand connu · servitudes par code · articles PLU · DPE du bâti existant (ADEME, déjà ingéré) · année/matériaux BDNB (au catalogue) · taxe d'aménagement · « Mon secteur » avec rayon effectif · Radar (annonce rattachée ou « couverture partielle ») · parcelles voisines (assemblage) · une page « comment lire » |
| Banquier | établissement prêteur | cf. B13 : paramètres Projet (prix, apport), coût total, marge en €, LTV, calendrier, bâti existant, TA, marché de la zone |
| Pré-dossier PC | mairie / architecte | cf. P1–P3, P8 : bon CERFA, servitudes + ABF, PPR et bruit dans la notice, TA, délai, articles PLU |
| Flash | acheteur sans compte (souvent non-professionnel) | glossaire (SDP, PPR, U1a, VEFA) · aucun renvoi à l'app · Étude de zone (présente si [DOSSIER] = Flash) · archivage du document livré |
| Lettre de vérification de zonage | mairie | non reçue |
| Argumentaire | vendeur | non reçu (fichier reçu = banquier) |

**Étude de zone / chalandise** : présente dans [DOSSIER] §09 seulement ; absente de [BANQUIER] (le « marché de la zone » y a sa place) et de [FICHE]. Le cas chalandise exige une **activité** : elle devient un paramètre Projet (ambre) — sans activité, le bloc reste « contexte » (piéton par défaut, D13).

**Zonage** : présent dans les 4 documents (U1a 100 %, document 97415_PLU_20251217) ; le bloc « Fraîcheur du zonage (GPU vs mairie) » n'existe que dans [FICHE] → à généraliser ; la Lettre de vérification de zonage, non reçue, est le document où il compte le plus.

---

## 8. Forme — DA v3 et pagination (transversal)

- **Vert --mint** : titres, filets, chips Sourcé — conforme dans [BANQUIER] et [DOSSIER] ; [FICHE] n'a que des barres.
- **Mauve = IA seul** : la seule prose IA (synthèse banquier) est **verte** (B3). Rien d'autre n'est IA — c'est bien.
- **Ambre = Projet** : aujourd'hui l'ambre marque les chips **ESTIMÉ** et les bandeaux de réserve — collision. Aucun paramètre Projet n'existe dans les exports → l'ambre n'a pas encore son usage. Cible : Sourcé mint · Estimé gris · Dérivé gris + ƒ · Projet ambre · IA mauve.
- **Ruptures de page** : [BANQUIER] une section = une page (9 → 4 pages) ; [DOSSIER] p.7 orpheline, sous-titre orphelin p.3 ; [FICHE] deux en-têtes orphelins ; [PC] ligne PCMI8 coupée, PCMI1 deux demi-pages. Règles : keep-with-next sur tout titre, keep-together sur toute ligne de tableau et toute note, rupture forcée seulement avant les sections lourdes.
- **Densité** : [FICHE] ~7 pt ; [BANQUIER] 60 % de blanc ; [DOSSIER] correct.
- **Cartouche commun** manquant : nom du document · IDU · adresse · n° de rapport · « données LABUSE au » · version du modèle · page x/y — présent en entier dans [DOSSIER] seulement.
- **Carte** : l'orthophoto avec contour + échelle + nord de [FICHE] bat la carte OSM de [DOSSIER]/[BANQUIER] ; une seule carte de situation pour tous.

---

## 9. Priorités (pour le mandat EXPORTS-1, à rédiger après validation de cet audit)

1. 🔴 **Un builder, un gabarit client** : [FICHE] rejoint la chaîne WeasyPrint ; test « mots interdits » sur tout export (annexe A). Règle F1.
2. 🔴 **Un seul bloc Potentiel** à trois lignes, référence de hauteur tranchée, scénario du bilan choisi selon l'état de la parcelle (D2, B1).
3. 🔴 **Un moteur prix** (§4) et un filtre comparables ; suppression des lignes « n 11 », « ×1,24 », « — (20 ventes) » (B7, D6, D7, F6).
4. 🔴 **Mixité, accès voirie, ICPE, propriétaire, annonces** : un moteur, une phrase, jamais un zéro de couverture (B2, F2, D9, F3, D3).
5. 🟠 **Synthèse banquier déterministe** + paramètres Projet en ambre (prix d'acquisition, apport, activité) alimentant marge, LTV, chalandise (B3, B13, D4).
6. 🟠 **Fuites** : suppression des 30+ chaînes (§5) ; notes de calibration et sources « fiabilité » restent admin.
7. 🟠 **PC** : CERFA selon projet, servitudes + ABF, notice complète (P1–P3).
8. 🟡 **Cartouche commun, chips recolorées, pagination**, sources millésimées ou masquées, footers sourcés depuis les sources lues (D5, D15, §8).
9. 🟡 **Flash** : archivage du document livré ; glossaire ; Étude de zone piéton par défaut.

Questions à trancher par Vic avant le mandat :
- Quel document est le **Dossier expert** ([DOSSIER] ou [FICHE]) et lequel est le **Flash** ?
- Surélévation : référence **égout** ou **faîtage** ?
- Le palier LABUSE figure-t-il dans le Dossier expert (D18) ? Jamais dans les documents tiers.
- Synthèse banquier : déterministe (recommandé) ou IA en mauve ?
- Le Pré-dossier PC reste-t-il « maison individuelle » seul, ou suit-il le projet (13409) ?

---

## Annexe A — Méthode de recette (à graver dans EXPORTS-1)

1. **Parcelle dorée** : 97415000BO0852 (bâtie, U1a, PPR, bruit, ICPE, ABF, mixité) + une parcelle nue + une parcelle en zone A — les trois régénérées à chaque commit.
2. **Diff écran ↔ PDF** : extraction des ~40 valeurs numériques de chaque export (pdfplumber) et comparaison au JSON servi à la fiche pour le même IDU — toute divergence = échec.
3. **Mots interdits** : grep sur le texte extrait de chaque PDF — clés de run, `EPSG`, `ST_`, `_` dans un libellé, « score », « pt », « signal », « scoring », « proxy », « fiabilité suivie », « doctrine », « page corrigée », « L'IA », « fiche commune », « parcours Flash », « outil ».
4. **Zéros** : tout « 0 » servi doit provenir d'une source à couverture complète déclarée (Radar exclu tant que la couverture est partielle).
5. **Pagination** : aucune page < 15 % de remplissage hors dernière ; aucun titre en dernière ligne d'une page.
6. **Cartouche** : IDU, adresse, n° de rapport, « données au », version, page x/y présents sur chaque page de chaque export.
7. **Recette réelle** : les vrais PDF générés et ouverts avant commit (mandat) — jamais un test sur HTML seul.

---

## 10. Complément du 03/09 (soir) — captures écran et réponses de Vic

**Vérification écran ↔ exports (captures fiche 97415000BO0852)**

- [FICHE] (`PDF.pdf`) **est l'écran imprimé** : mêmes textes, mêmes fuites (« doctrine a », « page corrigée », « SIGNAL DE ZONE », « score 1.00 », « Pas d'accès direct évident à la voirie »). Les fuites F1, F2, F4 sont donc **à corriger à la source (textes de la fiche)**, pas seulement dans le PDF.
- **Constructibilité** : l'écran dit « 204 % SDP consommée », « SDP résiduelle 0 m² — rien à construire », tuile « SDP dispo. — ». [DOSSIER] dit 127 m² d'emprise résiduelle + surélévation envisageable + neuf 635 m². **Divergence écran ↔ export confirmée** (D2). À noter aussi : tuile « — » et corps « 0 m² » sur le même écran.
- **Prix en tête** : l'écran met en avant **768 €/m² (terrain nu)** ; [FICHE] PDF met **3 804 €/m² (appartement)**. Deux titres différents pour la même parcelle bâtie.
- **DVF** : l'écran libelle « jusqu'à déc. 2025 » ; les PDF disent « DVF 2026 » (D17 : PDF seulement).
- **Neuf VEFA 5 003 €/m²** = **commune, 80 ventes / 3 ans** (et non secteur) — B7 et §4 corrigés.
- « Accès voirie » vient de **BD TOPO**, pas d'OSM (F2 : vérifier la géométrie BD TOPO du N1A / Chaussée Royale).

**Réponses de Vic**

| Question | Réponse | Effet sur EXPORTS-1 |
|---|---|---|
| Dossier expert / Flash | `DOSSIER.pdf` et `PDF.pdf` viennent tous deux des **boutons d'export en bas de la fiche** ; le Flash est à part | Deux exports de fiche → **un seul Dossier expert** (fusion [DOSSIER] + blocs utiles de [FICHE]) ; le Flash est un document distinct |
| Flash | « **un condensé de tous les exports** » (79 € one shot) | Flash = synthèse d'une page + extraits de chaque export (potentiel, bilan indicatif, risques, zonage, zone) ; archivé tel que livré |
| Surélévation (égout / faîtage) | « fais au mieux » | **Égout (12 m)** : c'est la règle qui borne les niveaux, et BD TOPO mesure le haut du bâti (≈ acrotère en toit-terrasse) → 9,4 m + 2,8 m > 12 m → **pas de surélévation** ici. Choix prudent (boussole : pas de faux positif) |
| Palier LABUSE dans le Dossier expert | **Non** | Aucun palier ni métrique dans aucun export (D18 clos) |
| Synthèse banquier | **Texte à trous** | Gabarit déterministe rempli par le moteur ; plus de prose IA dans les exports |
| Pré-dossier PC | « fais au mieux » | **Le CERFA suit le scénario retenu du Dossier** : collectif → 13409 (PC1–PC8), maison individuelle → 13406 (PCMI) ; à défaut de scénario, 13406 avec la mention en tête du LISEZMOI |

**Données, bascule et exports** (question de Vic)

- Un export est **rendu au clic** depuis ce qui est servi à cet instant : les tables vives (PLU calibré, DVF, Sitadel, risques…) et le **run servi par pointeur** (scoring, résiduel). Rien n'est figé, rien n'est stocké — sauf le Flash à venir (archivé car payé).
- Donc : une donnée injectée dans une **table vive** (ex. calibration PLU d'une commune, mergée et déployée) apparaît dans **l'export suivant**, sans geste ; une donnée qui vit dans un **run candidat** (q_v12 : résiduel corrigé) n'apparaît qu'**après la bascule** de Vic.
- **On n'attend pas** : les défauts de cet audit sont structurels (contradictions, fuites, forme, blocs manquants) et ne dépendent pas des valeurs. EXPORTS-1 se rédige et s'exécute maintenant ; la **recette finale sur vrais PDF** se joue après la bascule q_v12 et le merge de DESTINATIONS-1, pour valider sur les dernières données. Le test doré (annexe A) garantit ensuite que chaque bascule est reflétée à l'identique écran / PDF.

---

## 11. Argumentaire et Flash — lecture du 04/09/2026

Les deux PDF manquants ont été générés par CC (mandat EXPORTS-0, lecture seule) et lus. **Correction d'une hypothèse que j'avais avancée** : je pensais que le bouton « Argumentaire » servait le gabarit banquier. C'est faux — l'Argumentaire est un document distinct, avec son propre titre, son propre destinataire et son propre bilan. En revanche l'autre moitié de l'hypothèse est confirmée, et elle est plus lourde de conséquences (§11.1).

### 11.1 🔴 Le Flash 79 € est le Dossier parcelle, à l'en-tête près

`FLASH.pdf` (04/09, FL000001) et `DOSSIER.pdf` (03/09, DP-20260903-0852) sont le **même document** : 9 pages, mêmes 11 sections dans le même ordre, mêmes phrases, mêmes chiffres, même « Version du modèle de rapport 1.4 ». Les seules différences : le sur-titre (« RAPPORT FLASH · parcelle à l'unité » vs « DOSSIER PARCELLE »), le titre H1, le préfixe du n° de rapport (FL vs DP) et la date.

Conséquence commerciale, pas technique : **ce qu'un acheteur paie 79 € à l'unité est exactement ce qu'un abonné télécharge gratuitement depuis le bas de sa fiche.** Deux lectures possibles, à trancher par Vic :

- *C'est voulu* — le Flash est « la fiche à l'unité pour qui n'a pas d'abonnement ». Alors il faut au moins l'adapter à son lecteur : synthèse d'ouverture, glossaire, zéro renvoi vers l'app (cf. 11.2).
- *Ce n'est pas voulu* — le Flash devait être le condensé de tous les exports (ta décision du 03/09). Alors il est aujourd'hui à écrire, et ce qui existe n'en est pas la première version mais un autre document.

Tous les constats D1→D18 de l'audit s'appliquent donc **deux fois** : au Dossier et au Flash. Notamment le zéro Radar inventé (D3), les 127 m² contredits par l'écran (D2), la clé de run servie (D1), MOBPRO cité alors qu'il a été écarté (D5).

**Confirmé au passage** : générés à 24 h d'écart, les deux affichent les mêmes valeurs et le même `run m135-run2-ile`. Le pointeur n'a pas bougé, la bascule q_v12 n'est pas faite — cohérent.

### 11.2 🔴 Le Flash renvoie son acheteur vers une app qu'il n'a pas

Trois renvois, dans un document vendu à quelqu'un sans compte :
- « L'outil « Étude de zone » la fournit **sur demande** » (§09) — sur demande à qui ?
- « le **parcours Flash** ne précise pas encore l'activité étudiée » — le lecteur n'a pas à connaître le nom interne de son propre parcours d'achat.
- « Le potentiel « bâti conservé » figure **au dossier parcelle** » — un document qu'il n'a pas acheté.

Un document payé à l'unité doit se suffire à lui-même. Aucun renvoi, ou alors un lien d'achat explicite.

### 11.3 Argumentaire de négociation — lecture page par page

**Ce que c'est** : un document destiné à l'**acquéreur** (« À vérifier par l'acquéreur et ses conseils », sur-titre « contre-offre fondée »), pas au vendeur. C'est une bonne idée de produit — armer une contre-offre avec des faits plutôt qu'avec du marchandage. C'est aussi le document le plus abouti sur un point : le nuage des 25 ventes DVF une à une, avec la mention « aucune vente n'est fabriquée ni lissée ». À garder tel quel et à propager.

| ID | Grav. | Nature | Constat | Correctif attendu |
|---|---|---|---|---|
| G1 | 🔴 | FAUX | **Deux documents, deux verdicts opposés sur la même parcelle.** Le Banquier conclut à une charge foncière supportable de 175 k€ (jusqu'à 374 k€) ; l'Argumentaire conclut qu'il manque 136 k€ et qu'**« il n'existe pas de prix d'achat maximum »**. Même moteur de bilan, deux jeux d'hypothèses : coût 2 300-2 800 vs 2 500 €/m², marge & frais 24 % vs 21 %, VRD 83 k€ vs 67 k€ — et surtout **prix de sortie 4 730 €/m² (neuf dérivé) contre 3 818 €/m² (ancien)**. Le CA passe de 3,00 M€ à 2,42 M€ : c'est ce seul choix qui bascule l'opération de rentable à déficitaire. | Un seul moteur de prix de sortie (§4 de l'audit) partagé par les deux documents. Si les hypothèses diffèrent volontairement selon l'usage, **chaque document doit afficher qu'il en existe d'autres** et laquelle il retient — sinon LABUSE se contredit devant deux interlocuteurs de la même opération. |
| G2 | 🔴 | FAUX | **Renvoi vers une partie 3 qui n'existe pas** : « le détail figure dans la dérivation de la **partie 3** » (p.4). Le sommaire réel est 1, 2, [Faisabilité neuve, sans numéro], 4, 5, 6, [Assainissement & réhabilitation, sans numéro], 7. Deux sections ont perdu leur numéro et la numérotation saute de 2 à 4. | Numérotation continue générée, jamais écrite en dur ; renvois internes calculés. |
| G3 | 🔴 | FORME | **La page 5 « Le bilan à rebours » ne contient aucun bilan.** Titre « du prix de sortie au foncier », encadré d'hypothèses, trois phrases de conclusion — et rien : ni tableau de postes, ni fourchette, ni €/m². Une ligne mentionne pourtant « Charge foncière NÉGATIVE **en bas de fourchette** », donc une fourchette est calculée quelque part et n'est pas imprimée. C'est la page centrale du document. | Le tableau du bilan et la fourchette à trois bornes s'impriment, y compris quand le résultat est négatif — surtout quand il est négatif. |
| G4 | 🔴 | MANQUE | **Le prix demandé par le vendeur n'apparaît nulle part.** Un argumentaire de contre-offre sans le prix affiché ne peut pas argumenter : ni écart, ni décote justifiée, ni contre-proposition chiffrée. C'est le paramètre Projet manquant (I5 du catalogue), et ici il est bloquant, pas cosmétique. | Champ « prix demandé » en ambre (Projet) → écart vs charge foncière supportable, décote justifiée poste par poste, contre-offre argumentée. Sans lui, le document n'a pas d'objet. |
| G5 | 🟠 | FAUX | La section « **4 · Ce qui réduit la capacité constructible** » annonce des facteurs et n'en liste **qu'un** (plafond de densité), tout en citant en pied « PPR/aléas (DEAL), potentiel foncier Région (indicatif), indicateur d'érosion (Cerema), pente » — des sources dont **aucune n'a réduit quoi que ce soit** ici (la fiche dit « hors îlot cartographié », « hors zone de recul », pente non éliminatoire). Le lecteur croit que quatre contraintes ont joué. | Ne citer que les sources ayant réellement produit un facteur ; sinon « aucun facteur réducteur au-delà du plafond de densité ». Même défaut que D5 (pied de section non sourcé de ce qui est lu). |
| G6 | 🟠 | FUITE | « Indicateur de viabilisation (…) **100/100** » — un score servi au client, dans le document qui doit être le plus sobre de tous. Plus les fuites déjà connues : `ST_Buffer, EPSG:2975`, `Recul voirie « à_vérifier »`, renvoi « au dossier parcelle ». | Le faisceau de viabilisation se dit en mots (« confirmée par les faits : 4 indices concordants »), jamais en note sur 100. |
| G7 | 🟠 | FAUX | Le nuage de ventes retient les **25 ventes brutes**, extrêmes compris (1 569 → 10 135 €/m²), alors que le Flash affirme au même moment « ventes au prix/m² aberrant écartées ». L'appartement de 750 m² à 4,5 M€ (D7) est dedans. La transparence est bonne, le filtre reste incohérent d'un document à l'autre. | Un seul filtre (D7), et le nuage montre les retenues **et** les écartées, grisées — c'est encore plus honnête et ça règle la contradiction. |
| G8 | 🟠 | FAUX | Le document conclut que l'opération neuve n'est pas viable, puis imprime deux pages plus loin que la **réhabilitation du bâti justifie ~3,65 M€** et que le terrain nu vaut ~570 k€. Pour un acquéreur en contre-offre, ces deux chiffres démolissent l'argument qu'on vient de lui donner. Même incohérence de scénario que B1, aggravée par l'usage. | Le scénario dominant est choisi une fois (état de la parcelle), et le document argumente **sur ce scénario**. Le second scénario reste, en second, comme alternative — jamais comme contre-argument implicite. |
| G9 | 🟡 | FORME | Page 1 : une seule tuile (« terrain 742 m² »), synthèse en cadre vert clair, puis 60 % de blanc. Page 2 : la carte seule. Page 5 : quasi vide (G3). Soit 8 pages pour ~4 pages de contenu. Pas de n° de rapport (le Flash et le Dossier en ont un). Pied de page en trois lignes serrées. | Cartouche commun (K1), pagination fluide, hero à trois chiffres (742 m² · charge foncière supportable · écart au prix demandé). |
| G10 | 🟡 | MANQUE | Absents pour l'usage : comparables de **terrain** (le 768 €/m² n'apparaît qu'en note de réhabilitation), coût de démolition, délai d'instruction, taxe d'aménagement, et une page « comment utiliser ce document en négociation ». | cf. catalogue §3 du document de contenu. |

### 11.4 Ce que ça change pour EXPORTS-1

1. Le **prix de sortie** n'est plus un défaut théorique : il fait dire à LABUSE deux choses opposées sur la même parcelle, dans deux documents qu'un même client peut avoir en main le même jour. C'est le correctif n° 1.
2. Le **paramètre Projet** (prix demandé, prix d'acquisition envisagé) n'est plus un confort : sans lui, l'Argumentaire n'a pas d'objet et le Banquier n'a ni marge ni LTV. Il passe devant la moitié des correctifs de forme.
3. Le **Flash** doit être tranché avant d'être maquetté : version pour non-abonné du Dossier, ou condensé de tous les exports. Les deux se défendent, mais ce ne sont pas les mêmes 8 pages.
4. Le nuage de ventes de l'Argumentaire et le bloc « fraîcheur du zonage » de la fiche sont les deux meilleures trouvailles des six documents : à généraliser partout.
