# MANDAT RETOURS-5 — recette du 01/09

**Branche : `fix/retours-5`** (neuve, depuis `main` **après** merge de `fix/retours-4`). Bloc commun habituel.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter sans écrire.
**Fin de session** : `tsc`, build, tests, puis **CC commite sur sa branche** avant le compte-rendu. Merge = Vic.

**Référence** : `docs/audit-2026-08/maquette-v6-scan-depot-popup.html` (T3, T4, T5).

---

## T1 — Accueil : la ligne de chiffres saute à la ligne

Constat Vic : « 64 sources » passe à la ligne. **Retirer purement et simplement la ligne de chiffres** du panneau d'accueil — le bloc entier disparaît (plus de `statline`, plus d'appel dédié si l'endpoint ne sert que ça ; le dire au compte-rendu s'il sert ailleurs). Le titre est suivi directement de « PAR OÙ COMMENCER ».

## T2 — Rail : +10 % de largeur

Le rail est trop serré. **Largeur +10 %** (64 → 70 px, ou la valeur courante × 1,1). L'oiseau suit la même proportion : `max-width` porté de 36 à ~40 px, marges latérales conservées ≥ 12 px. Les libellés ne doivent pas être coupés à la nouvelle largeur.

## T3 — Popups et surfaces flottantes : jamais de fond blanc

Règle DA rappelée par Vic : **aucune surface blanche** dans l'app, c'est illisible sur le fond sombre. Le popup de la carte (opérations) doit être **sombre** : fond `rgba(14,18,16,.97)`, bord `--card-line`, texte clair, ombre portée pour le détacher de la carte. Voir la maquette (bloc P4).

**Balayage obligatoire** : chercher toute autre surface flottante à fond clair (popups MapLibre, tooltips, menus déroulants, modales) et les aligner. **Lister au compte-rendu** celles trouvées et corrigées.

Au passage, dans ce popup : les faits sur deux lignes lisibles (`Type · N permis · N logements` puis `Commune · période`), pas de dates collées bout à bout, et les deux actions côte à côte sur une ligne.

## T4 — Scan patrimoine : simplifier l'encart de synthèse

Constat Vic : trop d'infos, zones petites, textes coupés. Refonte selon la maquette (bloc P5) :

1. **Trois chiffres seulement, en grille de 3 cartes** : parcelles · actionnables · m² SDP résiduelle. Rien d'autre au premier niveau.
2. **Tout le reste passe dans un dépliant « Détail et méthode ▾ »** : détail des actionnables, valorisation indicative du foncier nu, périmètre (zones U/AU, DVF terrains), nature de l'estimation. Le libellé de valorisation actuel est trop long pour la largeur du panneau — il vit dans le dépliant, en ligne clé/valeur.
3. **« 200 affichées sur 1 833 » quitte l'encart** et devient une ligne discrète **sous** la liste, avec le tri : « 200 affichées sur 1 833 · triées par probabilité ».
4. « Voir ses opérations → » devient un bouton pleine largeur entre l'encart et la liste (survol plein).
5. Les lignes de parcelles reçoivent le **survol plein** (elles ne l'ont pas).

## T5 — Dépôt agence : simplifier au maximum

Constat Vic : l'info du bas est coupée, et le champ URL en tête fait doublon avec le champ « URL de l'annonce » plus bas. Refonte selon la maquette (bloc P6) :

1. **Le bloc « Raccourci : collez l'URL » disparaît de la tête d'écran**, avec son message d'échec. Un seul champ lien, **en bas du formulaire**, libellé « Lien de l'annonce ». Le pré-remplissage par URL est retiré du parcours client (il vaut pour Vic, pas pour une agence qui connaît ses propres faits).
2. **Champs réduits à l'essentiel** : adresse exacte · type · prix · surface bâtie · surface terrain · lien. **Retirer « Nb de pièces »** et **retirer le champ « Parcelle (résolue de l'adresse) »** — la parcelle se déduit de l'adresse, l'agence n'a pas à la saisir ; l'afficher en résultat après validation, pas en champ.
3. **Le champ « Agence déposante » n'est pas saisi** : il est déduit du compte connecté.
4. La phrase d'aide sous l'adresse remplace la mention longue : « Visible des seuls abonnés · sert au rattachement de la parcelle ».
5. **Recette : le formulaire entier tient dans la hauteur du panneau sans que le bouton soit coupé.**

## T6 — Étudier un bien : liseré vert au repos

Le champ de saisie apparaît **déjà focalisé** (contour vert) à l'ouverture de l'outil. Retirer l'autofocus visuel : bord neutre `--card-line` au repos, vert seulement au focus réel. Vérifier les autres outils qui ouvrent sur une barre de recherche — même correction si le cas se répète, à lister.

## T7 — Bandeau Radar : retirer la mention de drapeau en double

La ligne ambre « drapeau fermé — le dépôt reste invisible des clients » apparaît **deux fois** : sous le titre de l'écran Radar et dans l'encart de dépôt. **Retirer celle du bandeau Radar**, garder celle de l'encart (c'est là qu'elle est utile).

## T8 — Sélecteur de commune : survol plein

Le menu déroulant des 24 communes n'a pas le survol. Chaque ligne (nom + code postal + « voir la fiche → ») reçoit **l'aplat plein vert avec encre sombre**, comme le reste de l'app. Vérifier au passage que le fond du menu est bien sombre (voir T3).

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : T1 (l'endpoint chiffres sert-il ailleurs ?) · T3 liste des surfaces flottantes claires trouvées · T6 liste des autres outils avec autofocus visuel. Commit fait par CC. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff fix/retours-5
```
