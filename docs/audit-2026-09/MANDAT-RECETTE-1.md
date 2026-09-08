# MANDAT RECETTE-1 — les retours de recette du 08/09/2026

**Nature** : correctifs de recette. **Branche** : `feat/recette-1` depuis `main`. **Worktree** : `~/Desktop/labuse-recette1`.
**Modèle CC** : Fable. **Rapport** : `docs/audit-2026-09/RECETTE-1.md`.

**Garde-fous** : étape 0 (pwd, branche, arbre propre, `.env` copié) · aucun merge · aucune bascule · aucun rescoring · DA existante, aucun composant neuf · une capture avant/après par point corrigé.
**Périmètre fermé** : uniquement les points R1 à R41 ci-dessous. Pas d'audit collatéral, pas d'extraction de composant partagé, pas de liste des autres endroits au même problème. Ce qui n'est pas listé n'est pas fait.
**Un commit par lot**, dans l'ordre des lots. Chaque point est repris dans le rapport avec son numéro et son état : corrigé / non reproduit / refusé avec motif.

---

## LOT 1 — Bloquants (à faire en premier)

- **R1** — Export **Résumé** cassé : `localhost:5173/resume/<IDU>.pdf` → « The server is configured with a public base URL of /socle/ ». Le lien ne tient pas compte de la base `/socle/`.
- **R2** — Export **Apporteur** cassé : même erreur de base URL.
- **R3** — Export **Financier** cassé : « Impossible de charger le questionnaire ».
- **R4** — Outil **Faisabilité** : le bouton « Trouver les parcelles » ne fait rien.
- **R5** — Cache de carte : après avoir saisi une parcelle dans un outil, la carte reste zoomée dessus dans tous les outils suivants (six outils enchaînés, toujours bloquée).
- **R6** — Listing après « Voir les parcelles » : **toutes** les parcelles affichent « Adresse non disponible ».
- **R7** — Lenteur : le chargement des parcelles est très long (Blocs fonciers, Densifier). Dire la cause avant de corriger.

## LOT 2 — Doctrine du scoring

- **R8** — **Le scoring ne s'affiche que sur demande.** Les pastilles de palier (Priorité / À suivre / Sans signal / Écartée) et tout classement issu de l'algorithme sont réservés à deux endroits : le parcours « Demander à LABUSE » depuis la carte d'accueil, et la fiche parcelle. Partout ailleurs — Scan patrimoine, Densifier l'existant, Blocs fonciers, et tout autre outil qui en afficherait — les pastilles disparaissent. Le client qui n'a pas demandé d'avis n'en reçoit pas. Lister dans le rapport les endroits nettoyés.

## LOT 3 — Vérifications de données (répondre, ne pas corriger sans dire)

- **R9** — **CBO Territoria** : 1 833 parcelles détenues, 245 logements construits depuis 2013. Vérifier les deux chiffres et expliquer l'écart, ou dire lequel est faux.
- **R10** — **PLU · simuler un changement** : les seules propositions vues, sur toutes les communes, sont `AUc → U` et `AUs → U`. Vérifier si c'est la réalité des règlements ou une limite du code.
- **R11** — **Rechercher dans le PLU** : une recherche (ex. « AU ») renvoie extraits et articles — vérifier qu'ils proviennent bien de la commune sélectionnée.
- **R12** — **Fraîcheur des dates de source** : partout où l'app affiche une date de source (« signal RNE INPI au 09/08/2026 », « millésime 2025 », « maj 2026-09-08 »…), vérifier que la date se met à jour quand une nouvelle version de la source est ingérée. Lister les endroits où elle est figée.
- **R13** — **Numérotation des demandes de courrier** : « Demande n° 44 transmise » — vérifier que le compteur est propre au compte et non global à tous les comptes.
- **R14** — **Nouvelles sources et fiche parcelle** : vérifier que les sources de SOURCES-1 utiles à la fiche y sont bien branchées.
- **R15** — **Nouvelles sources et outils** : vérifier que les outils qui gagneraient à les utiliser les utilisent (exemple cité : Pièges et risques).
- **R16** — **Remonter le temps** : l'historique des faits datés par parcelle. Dire s'il existe, où, et sinon ce qu'il faudrait — **sans le développer ici**.
- **R17** — **Info classement** et **Info scoring** (écran d'analyse) : vérifier que les deux textes décrivent bien le classement q_v14 et les nouveaux paliers, pas l'ancien.

## LOT 4 — Ordre des outils

- **R18** — Ordonner le menu Outils exactement ainsi :
  1. PLU · 2. Permis · 3. Commune · 4. Étudier un bien · 5. Scan patrimoine · 6. Assemblage · 7. Comparer des parcelles · 8. Pièges et risques · 9. Étude de zone · 10. Remonter le temps · 11. Faisabilité · 12. Taxe d'aménagement · 13. Prospection solaire · 14. Densifier l'existant · 15. Blocs fonciers · 16. Successions à venir · 17. Courrier propriétaire.

## LOT 5 — Couches de la carte

- **R19** — **Aucune sous-couche.** « Limites officielles du PLU » et « TVA réduite primo-accédant » deviennent des couches normales, au même niveau que les autres.
- **R20** — Ranger les couches dans cet ordre et sous ces huit intitulés :
  - **Repères** : Limites parcelles (contour cadastral) · Limites communes
  - **Urbanisme** : Zonage PLU par parcelle (calibré) · Limites officielles du PLU · Espaces boisés classés · Emplacements réservés · Droit de préemption (DPU) · Servitudes d'utilité publique (SUP)
  - **Risques et nuisances** : PPR multirisque · Aléa inondation · Aléa mouvement de terrain · Plan d'exposition au bruit (PEB) · Classement sonore (bruit routier) · Cartes de bruit — dépassements · Secteurs d'information sur les sols · Anciens sites industriels (CASIAS)
  - **Nature et protections** : Parc national · ZNIEFF — patrimoine naturel · Espaces naturels protégés · Zones humides
  - **Domanialité** : Ravines et reculs (DPF) · 50 pas géométriques
  - **Usage du sol** : Cultures déclarées (RPG)
  - **Réseaux, mobilité et équipements** : Transport public (lignes et arrêts) · Stationnement allégé — TCSP (art. L151-36) · Axes structurants · Lignes électriques · Équipements (INSEE BPE) · Équipements (OpenStreetMap)
  - **Dispositifs et marché** : QPV — quartier prioritaire · TVA réduite primo-accédant (QPV + 500 m) · NPNRU / ANRU — renouvellement urbain · ZFANG — zone franche d'activité · FRR — France Ruralités Revitalisation · Prix du logement neuf (VEFA)

## LOT 6 — Architecture de deux outils

- **R21** — **Blocs fonciers**, en deux temps : (1) l'utilisateur pose ses filtres ; (2) il clique « Voir les parcelles », le listing s'ouvre et **le bloc de filtres se replie en accordéon** pour laisser la place. Aucun défilement horizontal : les colonnes doivent tenir. Le bouton « Voir la fiche » disparaît — **cliquer la ligne ouvre la fiche**.
- **R22** — **Outil Piscine** : tant que « Voir les parcelles » n'est pas cliqué, aucun des textes et informations de résultat n'apparaît. Ils naissent au clic.
- **R23** — **Outil Piscine** : retirer « Préparer les courriers » et « Comparer ».
- **R24** — **PLU · procédure et changement** : deux onglets — « Par parcelle » et « Simuler l'ouverture ». Aujourd'hui tout est sur une même ligne, illisible.

## LOT 7 — Textes à retirer

- **R25** — Analyse LABUSE : retirer « Liste groupée par priorité d'action (priorité → faible) · trier par Surface pour un ordre global ».
- **R26** — PLU annuaire : retirer « · 3 PROCÉDURES EN COURS ».
- **R27** — Courrier : retirer l'encadré « Envoi automatique indisponible — L'envoi postal n'est pas encore disponible ».
- **R28** — Retirer **tous les bandeaux explicatifs au survol** (infobulles) dans l'app : « Ajouter au CRM (suivi de prospection) », « Résumé de la parcelle (PDF, 3 pages) », « Ouvrir la fiche de la parcelle », et les autres.
- **R29** — Analyse LABUSE, écran 1 (le récapitulatif « LABUSE a analysé les 430 813 parcelles… ») : dire si toutes ses informations sont reprises à l'écran 2 ; si oui, proposer de le supprimer. **Ne pas supprimer sans l'accord de Vic.**

## LOT 8 — Interactions et animation

- **R30** — Survol vert opaque, identique au reste de l'app, sur les cartes de choix de **Veille** (Le foncier / Les annonces).
- **R31** — Même survol vert sur la liste des **sources** (page Données).
- **R32** — Même survol vert sur les lignes du **listing de parcelles** après « Voir les parcelles ».
- **R33** — Même survol vert sur les lignes de **Densifier l'existant**.
- **R34** — Les **flèches d'accordéon** sont inversées : ouvert, la flèche doit pointer vers le bas.
- **R35** — Latence d'allumage : un bouton (ou plusieurs) reste éteint et fade quelques secondes avant de prendre sa couleur. Trouver si c'est une latence de données ou un bug de rendu.
- **R36** — Au clic sur « Voir les parcelles », la carte se teinte d'un filtre gris. Le retirer.

## LOT 9 — Détails visuels

- **R37** — Le bouton pilule « Toutes 68 » (page Données) a un arrondi qu'on ne retrouve nulle part ailleurs. L'aligner sur la DA.
- **R38** — La case « Piscine » doit tenir sur deux lignes.
- **R39** — Étiquette de commune sur la carte : « Sainte-Suzanne » chevauche « Saint-André ». La remonter.
- **R40** — Densifier l'existant : ajouter un « i » à côté de **Score densif.** expliquant son calcul.

## LOT 10 — Le courrier

- **R41** — Le **courrier propriétaire** (PDF) doit être beaucoup plus soigné : mise en page à la DA LABUSE, pas un texte brut sur page blanche. Le fond du texte ne change pas.

---

## Rapport
Un tableau des 41 points : numéro · état (corrigé / non reproduit / refusé) · preuve `fichier:ligne` ou capture avant/après. Pour les points du lot 3, la réponse écrite en français. Rien n'est mergé : Vic relit, recette, merge lui-même.
