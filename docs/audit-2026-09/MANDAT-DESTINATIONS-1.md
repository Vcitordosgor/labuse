# MANDAT DESTINATIONS-1 — ce qu'on a le droit d'y faire

**Branche : `feat/destinations-1`** (depuis `main`). Aucun sous-agent ne touche à git. Claude Code en Fable (lecture de règlements). Mandat long : plusieurs sessions, commit par commune.
**Doctrine** : une valeur servie est **lue dans le règlement, article et page cités**, ou n'est pas servie. Une commune non calibrée affiche « destination non calibrée sur cette commune » — jamais un silence, jamais un verdict déduit de la lettre de la zone.

**Étape 0** : pwd, branche, arbre propre. Puis lire la calibration de constructibilité existante (schéma, doctrine de citation, les 2 communes déjà calibrées en destinations s'il y en a) — on prolonge, on ne recrée pas.

## X1 — Le schéma, aligné sur le code de l'urbanisme

1. Référentiel des **5 destinations et 21 sous-destinations** (art. R151-27 et R151-28 du code de l'urbanisme, version en vigueur) — une table, avec le libellé officiel.
2. Table de calibration : commune · zone · sous-destination · **statut** (autorisé / interdit / sous condition) · **condition** en clair (texte court) · **seuil** (surface de vente ou de plancher, m²) · article · page du règlement · millésime du PLU · date de lecture. Un état « non lu » distinct de « non mentionné dans le règlement » (silence = interdit ou autorisé selon la structure du règlement — le dire zone par zone).
3. Les deux communes déjà calibrées (si elles existent) migrent dans ce schéma sans perte.

## X2 — Les 24 communes, toutes les zones

Décision Vic : **24 sur 24**, pas d'échantillon. Saint-Philippe est au RNU : ses règles de destination sont celles du règlement national d'urbanisme (art. R111-1 et suivants), calibrées une fois et citées comme telles.

Ordre de lecture (les communes à forte activité d'abord, pour qu'une démo soit possible avant la fin) : Saint-Denis · Saint-Paul · Saint-Pierre · Le Port · Sainte-Marie · Le Tampon · Saint-André · Saint-Louis · Saint-Joseph · Saint-Benoît · La Possession · Saint-Leu · puis les 12 autres. Chaque commune est **commitée dès qu'elle est finie** — la calibration se sert au fur et à mesure, une commune lue est une commune servie.

Pour chaque commune :
1. **Zones U et AU à vocation d'activité, de centralité ou mixtes** : lecture complète, toutes les sous-destinations, seuils inclus.
2. **Zones résidentielles** : toutes les sous-destinations aussi, même si la réponse tient en une ligne (commerce de proximité autorisé ou non, seuil, article).
3. **Zones A et N** : ce qu'elles autorisent réellement (exploitation agricole, hébergement touristique parfois, équipements d'intérêt collectif) — lu, pas supposé.
4. Chaque valeur citée (article, page, millésime). À la clôture de chaque commune, **10 lignes relues au hasard** ; le taux d'écart par commune va au compte-rendu, et une commune à plus de 5 % d'écart est relue en entier.

Si la session s'épuise, commiter les communes finies et rendre le compte-rendu : les suivantes partent en Partie B, dans le même ordre. L'état « non calibrée » n'existe que le temps de la lecture.

## X3 — Les deux verrous que le PLU ne dit pas

1. **CDAC** : au-delà de 1 000 m² de surface de vente, autorisation d'exploitation commerciale obligatoire (code de commerce, L752-1). Règle statique, citée, affichée dès qu'un seuil est dépassé : « soumis à CDAC ».
2. **SCoT / DAAC** : les cinq SCoT de La Réunion (un par EPCI) localisent le commerce (localisations préférentielles, ZACOM). Vérifier si ces périmètres existent en géométrie (GPU, portails des EPCI) ; si oui, les ingérer comme source (catalogue, sentinelle) ; si seulement en PDF, extraire la liste par commune avec la page, et servir « secteur préférentiel du SCoT : oui / non / non localisé ». Ne rien inventer.

## X4 — Servir, trois surfaces

1. **Étude de zone › chalandise** : pour le point choisi et l'activité choisie (sous-destination), le verdict : « Commerce de détail **autorisé jusqu'à 300 m²** de surface de vente — zone UE, art. UE 2, PLU 2024, p. 41 · au-delà : CDAC · secteur préférentiel SCoT : oui ». Trois états : autorisé / sous condition (la condition affichée) / interdit — et « en cours de calibration » pour une commune pas encore lue. Le reste de l'Étude de zone est inchangé.
2. **Fiche parcelle › Urbanisme** : une ligne « Destinations » dans le tableau des règles de la zone : les principales autorisées, les interdites, le seuil commerce, dépliable par sous-destination, chacune sourcée.
3. **Faisabilité** : si le programme saisi comporte une destination non résidentielle, vérifier qu'elle est autorisée dans la zone ; sinon le dire avant de calculer.
4. **Copilote** : « peut-on ouvrir un restaurant sur cette parcelle ? » → même moteur, même phrase, bouton vers Étude de zone prérempli.

## X5 — Une seule vérité, et son entretien

1. Un module unique `plu/destinations.py` lu par les quatre surfaces ; test qu'aucune autre lecture n'existe.
2. La sentinelle des PLU (GPU) signale déjà une nouvelle version de document : la calibration destinations porte le millésime lu, et une nouvelle version de PLU passe la commune « à relire » (état visible dans Données › Catalogue, ligne PLU).
3. Page admin : tableau commune × état (calibrée le … / à relire / non calibrée), lien vers le règlement.

---

## Compte-rendu attendu

X2 le nombre de zones et de lignes calibrées par commune, le taux d'écart de la relecture par commune, les communes restantes s'il y en a · X3.2 ce qui existe pour le DAAC, commune par commune · X4.1 trois captures de chalandise (autorisé, sous condition, interdit) · le temps passé par commune.

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff feat/destinations-1
```
