# MANDAT RETOURS-9 — recette du 02/09, 21 h

**Branche : `fix/retours-9`** (depuis `main` après merge de `fix/retours-8`). Aucun sous-agent ne touche à git.
**Clôture** : tsc, build, tests 100 % verts, commit sur la branche. Merge = Vic.

## Q1 — Circuit : reproduire sur la base réelle, pas sur la base de test

RETOURS-8 a ajouté des replis par brique, mais l'onglet Circuit affiche toujours « Chargement… » chez Vic. Le test passait en base de test ; le défaut est donc dans les données réelles ou dans le front.

1. **Reproduire pour de vrai** : lancer l'API sur la base locale de Vic (`DATABASE_URL` du `.env`), appeler `GET /admin/flux` avec un jeton admin, lire le statut et la réponse. Puis ouvrir la page dans un navigateur (ou un test de rendu avec la réponse réelle) et lire la console. La cause exacte va au compte-rendu — pas une hypothèse.
2. Corriger là où c'est cassé : si l'endpoint répond mais que `Flux.tsx` attend une forme différente, aligner ; si l'endpoint est lent (> 10 s), ajouter un rendu progressif ; si une brique lève sur la base réelle malgré le repli, corriger la brique.
3. Test de rendu **avec la réponse réelle capturée** (fixture), pas une réponse fabriquée.

## Q2 — Catalogue : 64 sources, chacune avec un état lisible

Constat : les chips disent « 1 à rafraîchir · 3 à jour » — 4 sur 64. Presque toutes les lignes affichent « jamais sondée » et « — ». Deux causes : le job `sentinelle-sources` n'a jamais tourné en local (pas de cron sur le Mac), et les chips comptent encore l'ancien bloc fraîcheur au lieu des 4 états de R1.

1. **Les chips comptent les 64** : à jour N · nouvelle version N · à rafraîchir N · non surveillée N · **jamais vérifiée N** (surveillée mais l'agent n'est pas encore passé). La somme fait 64, testée.
2. **Une source surveillée jamais sondée** affiche « en attente de la première vérification » avec un bouton **Vérifier maintenant** en action principale — pas « — ».
3. **Étiquette AUTO / MANUELLE** sur chaque ligne, sous le nom : « auto · agent quotidien » (avec la méthode) ou « manuelle · rappel N j » ou « non surveillée · <raison> ». Vic doit lire en une seconde qui s'occupe de cette source.
4. **Un bouton « Vérifier toutes les sources maintenant »** en tête de Catalogue (lance le job `sentinelle-sources` à la main — le même que l'Horloge). Indispensable en local, utile en prod.
5. La phrase « Qui fait quoi » en pied dit aussi : « En local, l'Horloge ne sonne pas : cliquez Vérifier toutes les sources. »

## Q3 — Catalogue : retirer la barre de recherche

La barre « Chercher une source, un fournisseur » disparaît (les groupes repliables et les chips suffisent).

## Q4 — Flux : 20 ou 21 surfaces ?

L'en-tête dit « 20 surfaces sur ce run », la colonne Surfaces dit « 21 · toutes sur q_v11_m137 ». Un seul chiffre : établir lequel est vrai (la 21ᵉ est probablement « rattachement adresse → IDU », vivante, hors run), et écrire une phrase exacte partout : « 21 surfaces · 20 sur q_v11_m137 · 1 vivante (hors run) ». Test d'égalité entre en-tête et colonne.

## Q5 — Circuit : dire ce que le clic montre

Sous les colonnes, une ligne d'aide : « Cliquez une source, un moteur ou une surface : tout ce qui est relié s'allume — en amont ce qui l'alimente, en aval ce qui s'en sert. » Et un bouton « Tout désélectionner ».

## Q6 — « Horloge » s'appelle CRON

Renommer l'onglet et toutes ses mentions : **CRON**. C'est ce que c'est. La phrase « Qui fait quoi » suit.

## Q7 — Radar › Instruire : de quoi trancher

Vic demande comment, humainement, savoir si la candidate est la bonne parcelle. L'écran Instruire doit mettre côte à côte **l'annonce** et **la candidate** :

- annonce : type · surface habitable · surface terrain · prix · quartier/commune · lien portail (photos) ;
- candidate : IDU · surface cadastrale · **surface bâtie** (BD TOPO) · nombre de bâtiments · zone PLU · adresse BAN si connue · ortho centrée ;
- une ligne « **ce qui concorde / ce qui diverge** » calculée (terrain 600 ≈ 612 ✓ · bâti 180 m² pour 170 hab ✓ · quartier ✓) et le score de confiance.

Décision : Rattacher · Suivante (candidate) · Aucune. Aucun calcul neuf : tout est déjà dans la fiche parcelle.

## Q8 — Fiche parcelle : plus d'onglets, trois boutons, exports sur deux lignes

1. **Retirer les onglets** Analyse · Autour · Actions (Autour existe dans les outils, Actions est déjà dans la fiche). Retour à la fiche unique qui défile.
2. **En tête**, sous l'IDU, trois **boutons pleins** du même gabarit que les tuiles d'export, texte en toutes lettres : **Cadastre Géoportail** (vert), **Pages jaunes** (jaune), **Google Maps** (blanc). Ils quittent définitivement Exports.
3. **Exports en bas sur deux lignes de trois** : PDF · Dossier · Finance / Argumentaire · Courrier · Pré-dossier PC.
4. La ligne **« À proximité »** (école · commerces · santé · bus) n'est plus orpheline entre deux sections : elle entre **dans la carte « Autour de cette parcelle »**, en sous-ligne.

## Q9 — État cliqué, partout

Règle DA gravée : **tout contrôle sélectionné ou actif devient plein de sa couleur**, encre sombre — vert par défaut, mauve pour l'IA, ambre pour Projet/jaune. Pas un liseré : un fond. Concerné : + CRM, + Projet, la cloche, contour 3D, les boutons d'outils de la carte, les chips de filtre, les onglets, les boutons de tri Radar. `grep` des classes actives au compte-rendu, avec la liste des composants passés.

## Q10 — Panneau « Poser une question »

1. Retirer l'encart « L'IA ne juge pas le sentiment d'une communauté… ».
2. Retirer la suggestion « Pourquoi ce statut ? ».
3. Retirer toute mention « premium » (`grep -ri premium frontend/src`) — l'essai voit tout, il n'y a pas de premium.
4. Ajouter aux exemples du Copilote (accueil « Ce qu'il sait faire » et suggestions) : « Dis-moi tout sur la parcelle 97415000CV1186 » · « Combien de parcelles possède CBO Territoria ? » · « Quels sont les pièges de la parcelle 97415000CV1186 ? » — ils déclenchent les raccourcis de RETOURS-8 R12.

## Q11 — Page Sources client : ce qui intéresse un client, rien d'autre

1. **Les chips de tri** « À jour 64 · Mise à jour en cours 0 · Millésime non tracé 5 » disparaissent. À la place : « Toutes » et un **accordéon replié « Filtrer par thème »** (Énergie, Agriculture, Urbanisme, Risques, Marché, Cadastre…) — le thème existe déjà dans le catalogue.
2. **La ligne** « 6 vérifiées automatiquement · 5 sans date exposée · radar amont : dernier passage… » disparaît. C'est de l'exploitation, pas de l'information client.
3. **La dernière colonne** (collecte manuelle / automatique, méthode de veille) disparaît côté client. Le client lit : source · producteur · publié le · à jour. Ces informations restent dans Données (admin).
4. **Le texte d'introduction** passe en pleine largeur (la marge interne gauche est trop grande) et se raccourcit : « Chaque chiffre LABUSE est traçable jusqu'à sa source publique : d'où il vient, quand son producteur l'a publié, et s'il est à jour dans l'app. »
5. **Les deux grands chiffres** « 64 sources · 64 à jour » gagnent des voisins qui parlent au client, lus des données réelles : **parcelles couvertes** (436 3xx) · **communes** (24 / 24) · **transactions DVF** analysées (période) · **annonces Radar** suivies · **date de la dernière analyse** (run courant, « arrêtée au 27/08/2026 »). Cinq tuiles au plus, une ligne.

---

## Compte-rendu attendu

Q1 la cause exacte du Circuit vide · Q2 les 5 compteurs après un passage de `sentinelle-sources` sur la base locale (somme = 64) · Q4 le chiffre vrai · Q9 la liste des composants passés à l'état plein.

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff fix/retours-9
```
