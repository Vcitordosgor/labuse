# MANDAT RECETTE-2 — deuxième tour de recette (08/09/2026, soir)

**Branche** : `feat/recette-2` depuis `feat/recette-1`. **Worktree** : `~/Desktop/labuse-recette2`.
**Modèle CC** : Fable. **Rapport** : `docs/audit-2026-09/RECETTE-2.md`.
**Contexte** : le run servi en local est désormais **q_v14** (basculé après RECETTE-1). Le rapport RECETTE-1 a été écrit sous q_v11_m137 — plusieurs de ses conclusions sont à re-vérifier sous q_v14.

## Règle de vérification — la leçon du premier tour
Quatre points déclarés « corrigés » ou « non reproduits » en RECETTE-1 sont **encore visibles à l'écran** (S8, S9, S12, S14 ci-dessous). Le code a été lu, l'écran non.
**Aucun point n'est déclaré corrigé sans avoir été constaté dans un vrai navigateur** — Playwright MCP sur le Chrome installé, comme au Grand Balayage. Pour chaque point : la manipulation faite, ce qui est vu, la capture. Un point non vérifiable au navigateur est marqué « à recetter à l'œil », jamais « corrigé ».

**Garde-fous** : étape 0 (pwd, branche, arbre propre, `.env`) · aucun merge · aucune bascule · aucun rescoring · DA existante · périmètre fermé aux points S1–S30.

---

## LOT 1 — Ce qui est cassé

- **S1** — **Le Copilote et toutes les surfaces IA ne répondent plus** : « Je ne peux pas instruire votre demande pour le moment (service d'analyse momentanément indisponible) ». Trouver la cause avant de corriger. C'est le point le plus grave du mandat.
- **S2** — **Financier** : le parcours va jusqu'au bout des 4 écrans et **ne produit aucun document**.
- **S3** — **Financier** : trop de questions, mal formulées, incompréhensibles pour qui n'est pas du métier. **Ne garder que les questions dont la réponse change le document.** Toute question dont la valeur n'apparaît pas dans le bilan est supprimée. Les libellés « (saisi) », « (bilan) », « (saisi, %) » sont du jargon interne : les réécrire en français. Rendre compte de la liste avant/après.
- **S4** — **Régression** : la page d'accueil (la carte de l'île avec les étiquettes de communes) a disparu au profit d'une carte grise sans repères. **La remettre telle qu'elle était.** Le gating demandé portait uniquement sur les parcelles, qui ne doivent apparaître qu'au clic sur « Voir les parcelles ».
- **S5** — **Recherche par propriétaire** : la barre annonce « nom de propriétaire, SIREN, commune, nom de projet » mais un nom de propriétaire ne renvoie rien. Corriger, ou retirer la mention. **Retirer « commune » et « nom de projet » de la liste des formats acceptés** (décision Vic).
- **S6** — Les **fiches parcelles** sont toujours lentes à charger. Mesurer et dire la cause avant de corriger.

## LOT 2 — Les documents

- **S7** — **Brief apporteur** : refonte. Retirer entièrement la section « Qui vous envoie ce brief ». Ajouter les informations de parcelle qui manquent (surface, zone, SDP, bâti, contraintes, prix de secteur — ce qu'un apporteur doit avoir en main). Vérifier que les questions posées sont les plus utiles. **Proposer une maquette HTML** avant de coder, à valider par Vic.
- **S8** — **Courrier propriétaire** : le PDF sort avec des « - » à la place de la commune et de la surface (« votre parcelle BZ 1065, à - », « BZ 1065 (-), située à - »). **Un champ vide ne doit jamais s'imprimer** : soit la valeur est là, soit la phrase est reformulée sans elle. C'est un courrier qui part dans une boîte aux lettres.
- **S9** — **Résumé** : à quoi sert ce document, par rapport au Dossier ? Répondre. S'il n'apporte rien, proposer de le retirer (décision Vic, ne pas retirer soi-même).

## LOT 3 — Les trois arbitrages de Vic

- **S10** — **R28 tranché** : les infobulles au survol sont retirées **partout**, sauf sur les contrôles de la carte (couches, légende) où elles restent. Les `title` fonctionnels (valeur tronquée, icône seule sans libellé) restent aussi.
- **S11** — **R36 tranché** : le voile gris disparaît. En mode analyse, opacité uniforme des parcelles ; le palier reste porté par la couleur seule.
- **S12** — **R29 tranché** : l'écran 1 de l'analyse est **conservé** tel quel. Rien à faire.
- **S13** — **« Info classement »** cite encore le modèle q_v8. Le run servi est maintenant **q_v14** : réécrire le texte avec la fenêtre d'entraînement et la méthode réelles de q_v14 (les prendre dans `reports/q-v14/FREEZE-q_v14.json`, ne rien inventer).

## LOT 4 — Ce qui n'a pas été corrigé au premier tour

- **S14** — **Adresses** : le listing affiche toujours « Adresse non disponible » sur toutes les parcelles vues. RECETTE-1 a mesuré 60 % d'adressage en base — donc l'écart est ailleurs (le tri par surface remonte peut-être les grandes emprises non adressées). Reproduire au navigateur avant de conclure.
- **S15** — **Densifier** : le survol vert n'apparaît toujours pas sur les lignes. Vérifier à l'écran, pas dans le code.
- **S16** — **Case Piscine** : toujours sur trois lignes.
- **S17** — **Flèches d'accordéon** : la règle voulue est — **fermé : la flèche pointe vers la droite** ; **ouvert : elle pointe vers le bas**. Aujourd'hui elle alterne haut/bas. Appliquer partout.

## LOT 5 — Vérifications (répondre, ne pas corriger sans dire)

- **S18** — L'**Analyse LABUSE de la fiche parcelle** lit-elle bien q_v14 ? (Le rapport RECETTE-1 a été écrit sous q_v11_m137.)
- **S19** — Sous q_v14, les sources SOURCES-1 orphelines de la fiche (DPF, zones humides, ENP, RPG) **apparaissent-elles maintenant** ? La cascade servie est celle de q_v13_sources1.
- **S20** — La **fiche parcelle** est-elle au mieux de ce qu'elle peut être avec les données disponibles ? Lister ce qui manquerait.
- **S21** — Le **numéro de demande de courrier** est-il bien propre au compte depuis le correctif R13 ? Vérifier à l'écran.
- **S22** — Les **projets** sont-ils listés du plus récent au plus ancien ?
- **S23** — **Pièges et risques** : le dictionnaire `_KINDS` à étendre (DPU, DPF, zones humides, ENP, ER/EBC, PEB retiré). Proposer la liste des kinds à remonter, **ne pas l'appliquer** sans accord.

## LOT 6 — Interactions et visuel

- **S24** — Au survol d'un nom de projet, le texte devient noir et illisible. Corriger.
- **S25** — **« Filtrer par thème »** (page Données) : liseré vert autour du bouton, flèche vers le bas quand la liste est ouverte, animation verte au survol.
- **S26** — **Alignement des cellules** (page Données) : le texte de gauche est calé en haut, celui de droite en bas — la cellule s'écarte pour rien. Aligner les deux sur la même ligne de base.
- **S27** — **Prospection solaire** : retirer le point final de la phrase d'accroche.
- **S28** — **« Poser une question »** (fiche parcelle) doit ouvrir le Copilote **intégré à la fiche**, avec le contexte de la parcelle — pas une page à part.
- **S29** — **« Synthèse IA »** (fiche parcelle) : vérifier qu'elle produit une vraie synthèse de la fiche, et le dire. Dépend de S1.
- **S30** — Le **listing du mode analyse** : Vic avait demandé qu'on segmente la liste par type. Rappeler ce qui avait été convenu, et proposer — **sans coder** — ce que serait cette segmentation.

---

## Rapport
Un tableau des 30 points : numéro · état (corrigé / à recetter à l'œil / répondu / refusé) · **ce qui a été constaté au navigateur** · preuve `fichier:ligne` ou capture. Les points S18–S23 et S30 sont des réponses écrites en français. Rien n'est mergé.
