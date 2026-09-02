# MANDAT RETOURS-10 — recette du 02/09, 23 h

**Branche : `fix/retours-10`**. Aucun sous-agent ne touche à git.
**Maquette** : `docs/audit-2026-09/maquette-retours-10.html` — en-tête de fiche (**variante A — pastilles**) et accueil Copilote.
**Clôture** : tsc, build, tests 100 % verts, commit sur la branche. Merge = Vic.

## T1 — Radar : plus d'instruction

Décision Vic : l'instruction humaine des candidates est retirée. Elle ne sert qu'à trouver des bugs.

1. L'onglet « À rattacher », l'écran Instruire et les endpoints associés disparaissent du front. Rien n'est supprimé en base.
2. Ce qui reste : **le rattachement automatique à confiance forte** (adresse BAN exacte ou position) proposé en un bouton **Rattacher** sur la ligne de l'annonce, dans la re-vérification — un clic humain, toujours. Les candidates faibles ne sont plus des tâches : l'annonce est « non rattachée », point.
3. Les quatre chiffres de tête deviennent trois : annonces en vie · à valider · re-vérifiées aujourd'hui / dues. Le compteur « rattachées N / M » reste sur Circuit et Pilotage.

## T2 — Dashboard : audit de performance sur la base réelle

Le Circuit répondait en 56 s parce qu'il refaisait une comparaison sur 3 millions de lignes. Il ne doit pas en rester d'autres.

1. **Mesurer chaque endpoint admin** (Pilotage, Comptes, IA, Données × 3 onglets, Produit, Courrier, Radar, Contacts, Sources client, accueil client) sur la base réelle de Vic (`DATABASE_URL` du `.env`) : temps de réponse, requêtes SQL exécutées, la plus lente. Tableau au compte-rendu.
2. **Seuil** : tout endpoint > 2 s est corrigé (index manquant, requête à réécrire, compte mis en cache avec sa date, rendu progressif). Tout endpoint qui parcourt une table de plus d'un million de lignes à chaque appel est réécrit ou mis en cache, même s'il tient sous 2 s aujourd'hui.
3. **Un test de garde** : un test qui exécute chaque endpoint admin sur une base de taille réaliste (ou compte les lignes lues via `EXPLAIN`) et échoue au-dessus du seuil.

## T3 — Listes : 200 par 200, partout

Constat Vic : la correction promise n'est nulle part — ni le chemin normal, ni le chemin « Analyse LABUSE ». « Tout voir » charge encore 33 910 parcelles et fige l'app.

1. **Inventaire** de toutes les listes qui peuvent dépasser 200 lignes : liste de parcelles (chemin normal ET chemin Analyse LABUSE), Projets (À trier / Retenues / Écartées), Scan patrimoine (possèdent / construisent), Radar, PLU (« voir 400 de plus » existe déjà — aligner), Densifier l'existant, Permis, résultats de recherche.
2. **Règle unique** : page de 200, bouton **« Voir plus »** (jamais « Tout voir »), compteur « 400 / 33 910 », position de défilement conservée. Un seul composant de pagination réutilisé partout.
3. Test : une liste de 33 910 ne charge que 200 lignes au premier rendu et 200 de plus par clic.

## T4 — Fiche parcelle : en-tête selon la maquette, variante A

1. Les trois pavés pleins disparaissent ; les trois accès (Cadastre Géoportail · Pages jaunes · Google Maps) deviennent des **pastilles contour**, chacune sa couleur (vert · ambre · blanc), **pleines au survol et au clic**, la ligne de chiffres juste dessous. Rien d'autre ne bouge dans la fiche.
2. **Vérifier que chaque lien mène à la bonne donnée**, sur 5 parcelles réelles (2 avec adresse BAN, 2 sans adresse, 1 grande parcelle rurale) :
   - **Cadastre Géoportail** : l'URL ouvre le Géoportail **centré sur cette parcelle** (couche cadastre visible, parcelle identifiable), pas sur la commune. Si l'URL n'accepte pas l'IDU, construire le lien par les coordonnées du centroïde + zoom parcellaire.
   - **Pages jaunes** : la recherche porte l'**adresse exacte** (numéro + voie + commune) quand elle existe ; sans adresse, la commune seule, et la pastille le dit (« Pages jaunes — commune »).
   - **Google Maps** : le lien ouvre **l'emplacement de la parcelle** (coordonnées du centroïde), pas une recherche par texte qui peut tomber ailleurs.
   Résultat des 5 vérifications au compte-rendu, lien par lien.
3. Un test qui construit les trois URL pour une parcelle connue et vérifie qu'elles portent les bonnes coordonnées / la bonne adresse.

## T5 — Copilote : accueil selon la maquette

1. Retirer les deux phrases : « Le Copilote comprend ce que vous demandez — rien à choisir. » et « Cette zone ouvre un nouveau fil ; « Répondre » continue le fil en cours. »
2. Les trois exemples deviennent des chips discrètes sous le champ, mauves au survol, et posent la question au clic.
3. « Ce qu'il sait faire » sur une ligne de quatre, icônes mauves légères ; « Reprendre » : quatre derniers fils, « voir tout · N » dans l'en-tête de section, la phrase de rétention en pied.

## T6 — Bouton « Signaler » : plein quand ouvert

Le bouton reste en contour quand le panneau est ouvert. Il passe **plein vert, encre sombre**, comme tout contrôle actif (règle DA de RETOURS-9). Rebalayer les boutons d'en-tête pour le même défaut (cloche, recherche).

## T7 — Sources client : retirer la tuile « Dernière analyse »

La tuile « arrêtée au 27/08/2026 · dernière analyse » quitte la page Sources client. La date de l'analyse vit déjà sur les fiches et dans Projets.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : **T2.1 le tableau des temps de réponse avant / après**, avec la requête la plus lente de chaque page · T3.1 l'inventaire des listes et celles converties · T4.2 les 5 vérifications de liens, lien par lien.
