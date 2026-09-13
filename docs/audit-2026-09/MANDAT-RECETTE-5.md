# MANDAT RECETTE-5 — retours du 09/09/2026

**Branche** : `feat/recette-5` depuis `main`. **Worktree** : `~/Desktop/labuse-recette5`.
**Modèle CC** : Fable. **Rapport** : `docs/audit-2026-09/RECETTE-5.md`.
**Maquette de référence** : `docs/audit-2026-09/maquette-entete-fiche-v2.html`.

**Garde-fous** : étape 0 (pwd, branche, arbre propre, `.env`) · aucun merge · aucune bascule · aucun rescoring · DA existante · périmètre fermé aux points V1–V22.
**Règle de preuve** : rien n'est déclaré fait sans avoir été constaté dans un vrai navigateur (Playwright), **sur chaque chemin concerné**. Un correctif appliqué à un seul chemin quand deux existent n'est pas un correctif — voir V1.
**Un commit par lot.**

---

## LOT 1 — Ce qui a déjà été demandé et pas fait

- **V1** — **Le voile gris sur la carte, deuxième demande.** Il a été retiré du mode analyse mais **pas du chemin « Voir les parcelles » sans analyse**, où il est toujours là. Retirer sur **les deux chemins**, et le prouver par deux captures distinctes : une depuis « Demander à LABUSE », une depuis le listing factuel.
- **V2** — **Le tri « Potentiel » de la vue factuelle est à retirer.** Il classe par SDP résiduelle, qui est un **calcul LABUSE** : une vue qui s'annonce « tri factuel — sans analyse » sert donc une opinion de LABUSE. Trier par **adresse renseignée d'abord, puis surface décroissante** — que du fait. Le potentiel reste dans l'analyse, nulle part ailleurs.
- **V3** — **Fiche piscines** : l'ancienne fiche de synthèse (nombre de piscines au total et par commune) a disparu. La remettre telle qu'elle était, et ajouter **dessous** le bouton « Voir les parcelles » ; c'est au clic que la fiche se replie pour laisser la place au listing.

## LOT 2 — L'en-tête de la fiche parcelle

- **V4** — Refondre l'en-tête selon `maquette-entete-fiche-v2.html` : **huit tuiles** — surface · zone · pente · vue mer · terrain nu €/m² · bâti ancien €/m² · taxe foncière (part communale) · SDP restante. Chacune avec un « i » qui dit d'où vient le chiffre.
- **V5** — Les **étiquettes** (contraintes, type de propriétaire, voisines du même propriétaire) passent **sous la grille**, plus dans le bloc d'identité.
- **V6** — Le reste des faits (dernière vente, valeur au prix du secteur, bâti au sol, taxe d'aménagement, zonage d'investissement, ensoleillement, transport, fibre) va dans un accordéon « Le reste des faits ».
- **V7** — **Une valeur inconnue s'écrit « — » avec sa raison** (« pas assez de ventes », « zone non constructible »), jamais un zéro.
- **V8** — **Vue mer** : la tuile n'est câblée que si V21 conclut favorablement. Sinon elle n'apparaît pas — pas de tuile vide.

## LOT 3 — Marges, contrastes, vides

- **V9** — **Marges de la fiche** : des mots sortent du cadre et sont coupés (bloc « Le bien », bloc « Dispositifs et périmètres »). Reprendre les marges, les tailles et les graisses de **toute la fiche** pour qu'elles soient cohérentes entre blocs.
- **V10** — **Pastilles du listing au survol** : le contraste casse au scroll, du texte devient illisible. Retravailler pour que tout reste lisible dans les deux états.
- **V11** — **Panneau Cartes** : quand aucun accordéon n'est ouvert, un grand vide noir s'affiche. Au démarrage, une section doit être ouverte par défaut.
- **V12** — **Flèches d'accordéon** : fermé, la flèche pointe **vers la gauche** ; ouvert, vers le bas. Aujourd'hui elle pointe à droite quand c'est fermé.
- **V13** — **Page d'accueil** : ajouter « Remonter le temps » sous les quatre entrées existantes, à la place du vide.
- **V14** — **Bug d'empilement** : ouvrir la fiche commune puis cliquer une parcelle laisse la fiche commune par-dessus, cachant la fiche parcelle. L'une doit fermer l'autre, dans les deux sens.
- **V15** — **Carte rouge** : au chargement, toute l'île apparaît peinte en rouge (deux couches actives). Trouver quelle couche, dire pourquoi, corriger.
- **V16** — **« Bâti à densifier »** : le libellé du segment ne dit rien au client. Le remplacer par une formulation qui dit ce que c'est — une parcelle déjà construite où le PLU autorise encore du plancher.

## LOT 4 — Les documents

- **V17** — **Renommer « Finance » en « Dossier financier »** partout (bouton, titre du PDF, nom de fichier).
- **V18** — **Dossier financier, deux bugs** : (a) `<strong>Charge foncière supportable</strong>` s'imprime **avec ses balises HTML** ; (b) le document sort trois pages de tableau « non chiffré » alors qu'il annonce lui-même en tête qu'il ne peut pas être établi. Tant que les champs obligatoires manquent, **le document ne se génère pas** — l'écran dit lesquels manquent.
- **V19** — **Questionnaire du Financier** : chaque question porte un « i » qui dit ce qu'on attend comme valeur. Les questions **indispensables au calcul** bloquent le passage à l'écran suivant tant qu'elles sont vides ; les autres sont marquées facultatives et n'empêchent rien. Rendre compte de la liste des unes et des autres.
- **V20** — **Brief apporteur, reprise** : (a) il imprime « 0 m² de plancher restant » — un zéro ne s'imprime pas, la ligne disparaît ou se reformule ; (b) **les voisines du même propriétaire, la dernière vente et le propriétaire ont disparu** de la page 1, alors qu'ils étaient l'apport principal — les remettre ; (c) le plan remonte **en page 1**, le document fait 4 pages et non 5 ; (d) retirer « Document à jour du GPU — c'est celui qui fait foi », langage de plomberie.
- **V21** — **Dossier parcelle, chiffre impossible** : emprise bâtie **302 m²** sur une contenance cadastrale de **273 m²**. Trouver la cause (débord de l'emprise BD TOPO sur la parcelle voisine ?), dire combien de parcelles sont dans ce cas, et poser une garde.

## LOT 5 — Le courrier au propriétaire

- **V22** — Réécrire le fond du courrier. Il part dans une boîte aux lettres et doit donner envie de répondre. Ce qu'il dit, dans cet ordre :
  1. **Qui écrit** — LABUSE, l'outil d'intelligence foncière de La Réunion. Une phrase, sans jargon, qui rassure sur le sérieux.
  2. **Pourquoi cette parcelle** — une raison concrète et vraie, tirée de la fiche (zone constructible, potentiel restant, secteur qui bouge). Jamais une raison inventée ; si aucune ne se calcule, une formulation générale honnête.
  3. **Ce qu'on propose** — une étude gratuite de sa parcelle, ou simplement un échange sur ce qu'il pourrait en faire. Sans engagement, y compris s'il ne vend pas.
  4. **Comment répondre** — par mail à **victor@labuse.immo**, expert LABUSE.
  Le ton : посéré, respectueux, jamais commercial agressif. La mise en page reste celle de la DA. Le nom LABUSE est visible : c'est ce qui donne au propriétaire une raison de répondre, et au client une raison de passer par nous.

## LOT 6 — Vue mer : instruire, ne rien coder

- **V23** — Le RGE ALTI est un modèle de **terrain** : une ligne de vue calculée dessus annoncerait « vue mer » à une parcelle masquée par un immeuble. Instruire, **en lecture seule** :
  - ce qu'apporte la hauteur du bâti de la BD TOPO (déjà servie sur la fiche) une fois ajoutée au relief ;
  - ce que ça ne verra jamais : végétation, constructions à venir, trous et approximations de la BD TOPO ;
  - le coût d'un batch sur 430 663 parcelles, et s'il est rejouable ;
  - **calculer sur une seule commune** et sortir **20 parcelles avec leur verdict** (dégagée / partielle / aucune), que Vic ira vérifier lui-même.
  - Proposer trois états honnêtes plutôt qu'un oui/non, avec la phrase qui dit sur quoi c'est calculé.
  **Ne rien brancher, ne rien servir.** Vic tranche au vu des 20 parcelles.

---

## Rapport
Un tableau des 23 points : numéro · état · ce qui a été constaté au navigateur · preuve. V21 et V23 sont des réponses écrites en français. Rien n'est mergé.
