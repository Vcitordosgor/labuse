# MANDAT RETOURS-16 — reprise après quatrième recette (05/09/2026, 22 h)

**Branche** : `fix/retours-12`, on continue. **5 travaux** (V1-V5). Un commit par lot (carte V1 · permis V2-V4 · recherche V5).
**Contexte** : mandats et comptes-rendus RETOURS-13, 14 et 15. Mêmes règles : mesurer avant de coder, capture avant/après au cadrage de Vic, jamais un « vérifié » sans preuve.

## Étape 0
`pwd`, branche `fix/retours-12`, arbre propre. Sinon arrêt. Aucun sous-agent sur git, aucun `git add -A`, aucun merge.

---

## V1 — Ortho : la mer partout, sans marches (P2)
**Constat Vic** : « il ne peut pas juste y avoir la mer partout ? Pourquoi cette délimitation ? » La capture montre au large des **rectangles bleus décalés en escalier**, avec des liserés blancs le long des marches — le fond de mer est là, mais découpé en tuiles d'un bleu légèrement différent.
**Diagnostic établi (à confirmer par la mesure)** : U1 a posé un proxy qui rend transparents les pixels blanc-mer des tuiles ortho. Ce proxy ne traite qu'**une** des deux sources (l'Ortho Express). Aux zooms où les deux cohabitent, les tuiles non traitées gardent leur blanc ou leur bleu d'origine, d'où les marches. Vérifier lesquelles sont servies à ce cadrage (onglet réseau, URL des tuiles).
**Travail** :
1. **Toutes** les sources ortho passent par le même proxy et le même traitement — aucune ne reste brute.
2. Sous toutes, un aplat de mer d'**une seule couleur** couvrant l'emprise entière de la carte, jamais par tuile. Le résultat doit être uniforme : à ce cadrage, on ne doit distinguer aucune limite de tuile.
3. Supprimer les liserés blancs aux jointures (bord de tuile non couvert : `raster-fade-duration`, arrondi de l'emprise).
4. **Coût** : mesurer le temps de rendu du proxy à z8-z10 (nombre de tuiles × ms). Si le dézoom devient lent, poser un cache disque des tuiles traitées et le dire.
5. Recette : île entière · côte nord au large · Saint-Gilles · z16. Quatre captures, fond ortho **et** fond IGN. Aucune marche visible.

## V2 — Ligne de permis : la puce coupée (P1)
**Constat Vic** : « puce coupée, enlève "Autorisé" partout, au moins ça laissera de la place pour la puce "non localisée" ».
**Travail** :
1. **Retirer le chip « Autorisé »** de toutes les lignes de la liste : Sitadel 974 ne publie que des permis autorisés, l'information est constante donc muette. Elle reste dans la phrase d'explication en tête d'outil.
2. La puce de localisation approximative s'affiche **en entier**, jamais tronquée : elle passe avant tout autre chip et le conteneur ne coupe pas (cf. U4, plus aucun débordement horizontal).
3. Vérifier les autres chips constants de l'app (une valeur qui ne varie jamais n'est pas une information) et les lister dans le compte-rendu.

## V3 — « Dormant » (décision Vic)
Remplacer « Au point mort » par **« Dormant »** partout : onglet, filtres, légende, infobulles, exports. La définition (autorisé ancien sans achèvement déclaré) reste dans la phrase d'explication.

## V4 — Les compteurs de permis doivent dire ce qu'ils comptent
**Constat Vic** : « il y a que 21k permis en tout tout tout ? » L'écran affiche « Tous 21 038 » en haut et « 50 544 permis · 8 200 sur la carte » en bas. Deux totaux différents sous des libellés qui ne disent pas leur périmètre.
**Travail** :
1. Établir ce que compte chaque chiffre (filtre commune actif ? emprise de carte ? natures ?) et l'écrire dans le compte-rendu.
2. Nommer à l'écran : le sélecteur du haut dit son périmètre (« Tous — 21 038 sur ce filtre »), la ligne du bas dit le total base et le nombre localisable (« 50 544 en base · 47 270 localisés · données jusqu'au 2026-07-31 »).
3. Vérifier que le « sur la carte » a bien suivi la levée du LIMIT de U2 (8 200 est l'ancien chiffre).
4. Règle générale : **aucun compteur de l'app n'affiche un nombre sans dire de quoi**. Inventorier les compteurs de l'app et signaler ceux qui manquent leur périmètre.

## V5 — Autocomplétion sur toutes les barres de recherche — **priorité haute**
**Demande Vic** : « sur toutes les barres de recherche de l'app, il faut qu'il y ait comme pour une adresse une recherche qui devine la fin, qui propose des propositions. C'est possible ou non ? »
**Réponse** : oui. L'adresse a déjà une autocomplétion (BAN) ; il faut la même pour les autres grammaires, servie par le moteur de résolution unique de T1.
**Travail** :
1. **Un endpoint de suggestion** unique (`/api/recherche/suggest?q=`), appelé au fil de la frappe (déclenchement à 2 caractères, anti-rebond ~200 ms, annulation de la requête précédente, réponse < 150 ms). Index en base sur les colonnes interrogées ; mesurer et dire le temps de réponse.
2. **Grammaires proposées**, chacune avec son type visible dans la liste :
   - **adresse** (BAN, comme aujourd'hui) ;
   - **référence cadastrale** : IDU complet et référence courte (`BZ1065`, `BZ 65`) → propose les parcelles correspondantes avec commune et surface ; si plusieurs communes, elles apparaissent toutes ;
   - **propriétaire** : nom de personne morale, à la frappe ;
   - **SIREN** ;
   - **commune** ;
   - **projet** (les projets de l'utilisateur).
3. **Présentation** : liste sous la barre, groupée par type, 8 propositions maximum, type en libellé discret à gauche, l'essentiel en clair. Navigation clavier (flèches, Entrée, Échap). Le survol suit la règle (vert opaque, contenu inversé).
4. **Une seule implémentation**, dans le composant de barre partagé. Toutes les barres inventoriées en T1/R24 l'utilisent — aucune barre ne garde son autocomplétion maison. Joindre l'inventaire barre × autocomplétion active.
5. Ne jamais deviner à la place de l'utilisateur : la frappe reste ce qu'il a tapé, la proposition ne se substitue qu'au clic ou à Entrée sur une ligne sélectionnée.
6. Zéro proposition n'est pas muet : « aucune correspondance pour "xxx" — formats acceptés : adresse, IDU, référence courte, SIREN, nom ».

---

## Livraison
- Captures avant/après pour V1 (4 cadrages × 2 fonds), V2, V3, V4, V5 (les six grammaires en action).
- `docs/audit-2026-09/RETOURS-16/COMPTE-RENDU.md` : une ligne par travail, la mesure de coût de V1, ce que comptent les compteurs de V4, l'inventaire barre × autocomplétion de V5.
- Commits par lot, jamais de merge.

## Case à cocher
- [x] V1 — mer uniforme partout, aucune marche ni liseré, sur ortho et IGN, coût mesuré
- [x] V2 — chip « Autorisé » retiré, puce de localisation entière
- [x] V3 — « Dormant » partout
- [x] V4 — chaque compteur dit son périmètre ; « sur la carte » à jour
- [x] V5 — autocomplétion sur toutes les barres, six grammaires, un seul endpoint
