# MANDAT RETOURS-3 — recette visuelle du 31/08

**Branche : `fix/retours-3`** (neuve, depuis `main`). Coller le bloc commun habituel (DA v3, doctrine données, jamais main, merge par Vic uniquement) avec ce mandat.

**Étape 0 (obligatoire, avant toute écriture)** : vérifier `pwd` = `~/Desktop/labuse`, branche = `fix/retours-3` fraîchement créée depuis `main`, arbre propre. Sinon : s'arrêter et signaler sans rien écrire.

**Référence visuelle** : `docs/audit-2026-08/maquette-accueil-v2.html` (validée par Vic).

Rappel DA : vert canonique `#4ADE80` (`--mint`) partout ; **mauve réservé aux surfaces IA** — survol ET état actif/sélectionné.

---

## R1 — Accueil : panneau d'entrée

1. **Régression — les 3 données ont disparu.** La bande sous le titre affichait 3 valeurs (parcelles / communes / sources) ; elle rend aujourd'hui 3 cases vides (constat capture Vic 31/08). Trouver la cause (endpoint, sélecteur, ordre de chargement), restaurer les valeurs **servies par l'API** — pas codées en dur. Si la cause est un endpoint mort, le dire dans le compte-rendu.
2. **Icônes des 4 cartes uniformisées et bien lisibles** : même tuile 44 px, même set, stroke **2.1** (pas plus fin), glyphe 23 px. Au repos la tuile est **franchement teintée** — fond vert ~20 % + contour vert ~45 % (mauve pour le Copilote), pas un voile blanc. Au survol (carte pleine), la tuile devient une **pastille sombre** avec le glyphe resté vert/mauve : l'icône doit ressortir davantage, jamais se fondre. Voir la maquette.
3. **Descriptions sur UNE ligne** (pas d'ellipse CSS, textes courts réels) :
   - Explorer la carte → « couches, filtres, clic parcelle »
   - Suivre le marché — Radar → « les biens en vente, croisés au foncier »
   - Demander au Copilote → « “terrain 1 000 m² à Saint-Paul” »
   - Ouvrir un outil → « 17 outils, du repérage au courrier » (adapter le nombre à la réalité du menu ; le mettre à jour si R5 est joué)
4. **Survols pleins** : au survol, la carte entière se remplit — **vert opaque** (`--mint`) pour les 4 entrées, **mauve plein** pour « Demander au Copilote ». Le contenu s'inverse : titre, icône et flèche en sombre (`#08110b` sur vert, `#150f24` sur mauve), description en sombre à 72 % d'opacité, tuile en voile sombre. **Les 4 cartes sont vertes** au repos (bord + tuile), sauf le Copilote en mauve — plus aucune carte grise.

## R2 — Menu latéral gauche

1. **Ordre imposé des catégories**, de haut en bas — cet ordre est la référence, aucun autre tri :
   1. Carte · 2. Outils · 3. Copilote (IA) · 4. Radar · 5. Veille · 6. Projets · 7. CRM · 8. Sources
   Si une entrée du menu ne figure pas dans cette liste, la placer après Sources et le signaler au compte-rendu.
2. **Survol plein — règle globale de l'app.** Partout où la souris survole une case cliquable (menu latéral, cartes d'accueil, tuiles d'outils, lignes de liste, chips), la case se **remplit en vert opaque** (`--mint`) et son contenu s'inverse en sombre (`#08110b`) — icône comprise. Sur toute surface IA : **mauve plein** (`--mauve`, encre `#150f24`). Plus de survol « teinte légère ». Transition ~120 ms.
3. **Étiquette redondante (capture P2)** : le tooltip qui répète le libellé déjà affiché sous l'icône est supprimé. Ne le conserver que si un mode icônes-seules (libellés masqués) existe — dans ce cas tooltip uniquement dans ce mode.

## R3 — Radar : dépôt agence, étape 1 (drapeau admin inchangé, fermé)

Constat capture Vic : une **URL** Leboncoin collée dans le champ déclenche l'erreur brute « __NEXT_DATA__ absent ». Or la vision produit gravée (dépôt agence V2, RADAR-maquette-logique-v3) dit : *l'agence colle l'URL de sa propre annonce*.

1. Le champ **détecte une URL http(s)** et bascule sur le chemin URL : fetch serveur **one-shot** (headers navigateur, timeout court, **aucun retry**, aucune boucle) puis parseur existant.
2. Si le portail bloque (Datadome, 403, page sans `__NEXT_DATA__` ni variante B exploitable) : **message honnête** expliquant que le portail refuse la lecture automatique + repli guidé Cmd+S « page web complète » → coller le HTML. Jamais l'erreur `__NEXT_DATA__` brute face à une URL.
3. Le chemin HTML collé reste inchangé.

## R4 — Veille promoteurs

1. **Points cliquables.** Constat Vic : aucun point de carte ne réagit au clic. Chaque opération doit ouvrir un popup/panneau : propriétaire moral, nb de permis, période, **et le programme rattaché (nom + lien vers la page du promoteur)** quand il existe. *Recette obligatoire : les 5 programmes CBO rattachés en PROMO-1 doivent être visibles au clic de leurs opérations.*
2. **Barre de recherche adresse/IDU** en tête d'outil (composant commun de l'app) pour se positionner sur une parcelle ou une adresse.
3. **Ponts croisés avec Scan patrimoine** (décision gravée : les deux outils se renvoient) : depuis une opération → « Voir son patrimoine » (Scan patrimoine pré-rempli sur le même propriétaire), et depuis Scan patrimoine → « Voir ses opérations ». Vérifier/câbler les DEUX sens ; Vic n'en voit aucun.

## R5 — Fusion « Étudier un bien » × « Mon secteur » — *NE JOUER QUE SI VIC L'ACTIVE DANS LE PROMPT*

Une seule entrée « Étudier un bien » : s'ouvre sur la barre adresse/IDU ; dès l'adresse → bloc secteur (moteur `sector_price`, rayon effectif affiché) ; parcelle choisie → étude complète du bien. « Mon secteur » disparaît du menu (redirection interne conservée). Compteur d'outils mis à jour partout.

## R6 — Pages Jaunes : audit + micro-fix

Chercher toute référence (pagesjaunes, pages-jaunes, PJ…) dans le code. Établir si l'intégration est **réelle** (appel/donnée vivante) ou **décorative/morte**. Rapport de 10 lignes max dans le compte-rendu : où c'est branché, ce que ça fait vraiment, état. Si c'est un simple lien mort → corriger ; sinon proposer sans rien casser.

## R7 — Carte : chip « Contexte » → « Fiche commune », et en jaune

1. **Renommer** le chip « ⓘ Contexte » en **« Fiche commune »** — partout : libellé du chip, titre du panneau qu'il ouvre, et toute autre occurrence du mot « Contexte » désignant cet écran (le mot ne dit rien à l'utilisateur, « Fiche commune » dit ce que ça ouvre). Rappel : la fusion des deux fiches commune est déjà gravée — c'est bien la fiche unique.
2. **Couleur** : le chip est mauve alors que ce n'est pas une surface IA. Le passer en **jaune/ambre** (le ton des chips d'information existants, ex. « drapeau fermé »).
3. Dans la foulée : balayage rapide des tokens mauve hors surfaces IA — **lister** au compte-rendu tout autre usage trouvé, ne corriger que celui-ci.

## R8 — Projets : compteurs des tiers cassés

Constat capture Vic : chip « Priorité 34 » alors que des parcelles sont déjà triées (9 retenues) — les chips affichent le total du cadrage, pas le restant. Les compteurs **Tous / Priorité / À suivre comptent ce qui reste À TRIER** (retenues et écartées en sortent — cohérent avec le compteur « à trier » du haut). La mention « les N signalées d'abord » suit la même logique. Dire au compte-rendu d'où venait le mauvais chiffre.

## R9 — Projets : barre de recherche

Retirer la barre « adresse, IDU… » de la page Projets (colonne À trier).

## R10 — Projets : bandeau d'analyse compactable

Le bandeau prend trop de place. **Replié par défaut sur une ligne** : « LABUSE a analysé N parcelles : M ressortent — x Priorité, y À suivre » + « Voir pourquoi » qui **déplie** le contenu complet actuel (phrase gravée entière, signaux détectés, valeurs au…, run). Fond vert et formulation gravée inchangés — seul le repli est nouveau.

## R11 — Menu Outils : textes explicatifs réécrits

Remplacer chaque description par le texte ci-dessous, **tel quel** (une phrase, droit au but). Si un outil du menu n'est pas dans la liste : garder l'ancien texte et le signaler au compte-rendu.

- Étudier un bien → « Une parcelle → tout ce que LABUSE en sait. »
- Mon secteur → « Une adresse → les prix réels du secteur. »
- Veille promoteurs → « Ce que les promoteurs construisent, opération par opération. »
- Permis → « Qui construit quoi, commune par commune — et les permis au point mort. »
- Densifier l'existant → « Le bâti en zone U qui peut porter davantage. »
- Étude de zone → « Habitants, emplois, concurrents : la zone autour d'un point. »
- Faisabilité → « Ce que le PLU laisse construire sur la parcelle. »
- Taxe d'aménagement → « La taxe du projet, calculée d'avance. »
- Pièges et risques → « Ce qui peut bloquer le projet, avant d'acheter. »
- PLU → « Chaque zone, son règlement, articles cités. »
- Comparer des parcelles → « Des parcelles côte à côte, critère par critère. »
- Assemblage → « Des parcelles voisines réunies : le potentiel du tout. »
- Scan patrimoine → « Tout ce qu'un propriétaire possède sur l'île. »
- Courrier propriétaire → « Écrivez au propriétaire — LABUSE se charge de l'envoi. »
- Remonter le temps → « La parcelle vue du ciel, année après année. »
- Prospection solaire → « Les toits bien exposés, les piscines à équiper. »
- Communes → « Les 24 communes en chiffres : marché, rareté, rythme. »

Si R5 (fusion) est joué : « Étudier un bien » prend « Une adresse → les prix du secteur ; une parcelle → l'étude complète. » et « Mon secteur » disparaît.

## R12 — Copilote : écran d'accueil v3 — *NE JOUER QUE SI VIC L'ACTIVE DANS LE PROMPT*

Appliquer `docs/audit-2026-08/maquette-copilote-v3.html` : contenus gravés inchangés (champ d'abord, 4 capacités **non cliquables**, Reprendre), mise en page resserrée, mauve assumé (bouton Envoyer, focus du champ), **tuiles d'icônes contrastées** sur les 4 capacités (même traitement que l'accueil : fond mauve ~22 % + contour ~48 %, stroke 2.1), **survol plein mauve** sur les lignes Reprendre (texte inversé sombre), dates « il y a N j » jamais tronquées.

## R13 — Radar : barre de filtres resserrée

Six rangées de filtres à plat noient l'écran (constat Vic). Aucun filtre n'est supprimé, ils passent sur **deux étages** — référence : `docs/audit-2026-08/maquette-radar-filtres-v4.html`.

1. **Barre visible, une seule ligne** : recherche adresse/commune/IDU (composant commun de l'app) + commune + type + bouton **« Filtrer »** portant le nombre de filtres actifs.
2. **Tiroir « Filtrer »** : prix min/max, surface min, rattachement, vendeur, prix face au marché — groupés par intitulé, avec « Tout effacer » et « Voir les biens ».
3. **Pastilles de filtres actifs** sous la barre, chacune retirable, plus « tout effacer » : ce qui filtre reste visible sans occuper six lignes.
4. Ligne de résultats et tri inchangés.
5. Au passage, **vérifier** que le segment Tous/Rattachés est bien celui qui doit rester : la décision du 28/08 retirait du Radar le filtre « non rattaché » (parti en Veille). Si c'est le même, le retirer et le dire ; sinon le garder dans le tiroir.

## R14 — Menu latéral : état collé en « double sélection »

Constat Vic : une entrée reste parfois affichée en double état — cadre vert de sélection **et** tuile survolée — même après avoir quitté la souris ou changé de page. Causes à écarter, dans cet ordre :

1. **Focus confondu avec sélection** : après un clic, le `:focus` du bouton reste et se cumule au survol. Passer tous les états de focus décoratifs en **`:focus-visible`** (le clavier garde son anneau, la souris non).
2. **Survol collé** : encadrer les règles de survol dans `@media (hover:hover) and (pointer:fine)` pour qu'un pointeur qui a quitté la fenêtre (ou un trackpad) ne laisse pas l'état allumé.
3. **Deux sources de vérité** : vérifier qu'il n'existe pas à la fois une classe `.active`/`.selected` posée en JS **et** un état dérivé de la route. Une seule source — la route — et le JS ne fait que la refléter ; s'assurer que l'ancienne classe est retirée de TOUTES les entrées avant d'en poser une nouvelle, y compris quand la navigation vient d'ailleurs (lien interne, retour navigateur).
4. Un seul traitement visuel par état : **sélection** = fond teinté léger + libellé coloré · **survol** = case pleine (vert opaque, mauve sur l'IA — voir R2.2). Les deux ne se cumulent jamais : l'entrée active **n'a pas** de style de survol (`:not(.active):hover`), l'état sélectionné reste donc reconnaissable même souris dessus.

Recette : cliquer chaque catégorie, changer de page par un lien interne, revenir par le bouton retour du navigateur, sortir la souris de la fenêtre — une seule entrée allumée à chaque fois, aucun résidu.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : R1.1 cause de la régression des 3 données · R6 rapport Pages Jaunes · R7 liste des usages mauve hors IA · R8 origine des compteurs faux. Aucun merge par CC — la commande de merge en **dernier élément isolé** :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff fix/retours-3
```
