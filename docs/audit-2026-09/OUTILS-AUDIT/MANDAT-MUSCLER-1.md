# MANDAT OUTILS-MUSCLER-1 — Successions · Assemblage : voisines contiguës

**Rédigé par :** Fable, 06/09/2026. Premier mandat « Muscler » issu de OUTILS-AUDIT-1 (Partie C, regroupements 4 et 7). Les quatre mandats de correctifs FIX-1→4 sont mergés.
**Branche :** `feat/outils-muscler-1`, créée depuis `main` à jour.
**Périmètre :** deux lots. Rien d'autre.

## Étape 0

`pwd`, `git branch --show-current`, `git status -sb`. Conditions : branche `feat/outils-muscler-1`, arbre propre, `main` contient le merge de `fix/outils-4`. Sinon : s'arrêter.

## Garde-fous (valent pour les deux lots)

- DA existante, composants existants : omnibox `ParcelInput`, cartes empilées (patron Solaire piscines, panneau 320 px), sélection + compteur (patron Courrier / Comparer), fil de retour `<RetourOutil/>`, badges Sourcé / Estimé, tiroir « Détail et méthode ».
- Aucun bouton d'export. Aucune surface IA. Aucun badge de score sur un écran où l'analyse n'a pas été demandée.
- Propriétaires : personne morale nommée, particulier jamais nommé (doctrine Assemblage / Scan).
- Tout chiffre servi porte son statut et sa chaîne table → moteur → écran. Aucun calcul métier au front.
- Run épinglé `q_v11_m137` via la constante unique. Aucune écriture en base hors ce que A0 conclut avec l'accord de Vic.
- Capture avant / après dans `docs/audit-2026-09/OUTILS-MUSCLER-1/`. Tests verts (`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`). Un commit par lot, push, **pas de merge**.

---

## Lot A — Successions

### A0. État de la donnée, en lecture seule, avant d'écrire une ligne d'outil

Livrable : `docs/audit-2026-09/OUTILS-MUSCLER-1/A0-successions-donnee.md`, ≤ 30 lignes. CC établit, preuves `fichier:ligne` et SQL rejouable :

1. **Origine.** Quelle table porte le signal (`parcel_veille_succession` ou autre), quel module l'alimente, à partir de quelle source amont (MAJIC ? DVF ? BODACC ? autre ?), par quelle règle une parcelle est marquée « en succession ».
2. **Fraîcheur.** Date du dernier calcul, millésime de la source amont utilisée, cadence de rafraîchissement prévue (existe-t-elle ?). Si la source amont a une version plus récente que celle chargée : le dire, avec la version disponible.
3. **Complétude.** Nombre de parcelles marquées, par commune. Y a-t-il des communes à zéro alors que la source amont les couvre ? Le signal dépend-il d'une jointure qui peut perdre des lignes (IDU non résolu, propriétaire non rattaché) — combien ?
4. **Fiabilité.** Que signifie exactement le signal : succession ouverte, indivision, propriétaire décédé, mention « succession » dans un acte ? Faux positifs connus ? Y a-t-il une date de signal par parcelle (pour dire « en succession depuis ») ?
5. **Verdict** en trois lignes : la donnée est-elle servable telle quelle ; si non, ce qui manque ; si un rafraîchissement est possible, la commande exacte — **sans l'exécuter**. C'est Vic qui décide du rafraîchissement (doctrine sentinelle : injection sur clic humain).

### A1. L'outil

Nouvelle entrée du menu Outils : **Successions** — « Les parcelles à potentiel dont le propriétaire est en succession ».

**Entrée.** Sélecteur de commune (Toute l'île par défaut, même composant que Densifier). Filtre « résiduel minimum » (m² SDP). Rien d'autre à l'ouverture.

**Liste.** Cartes empilées, triées par résiduel décroissant, 200 chargées puis « voir plus ». Par carte : IDU · commune · surface terrain · zonage · **résiduel SDP** (Estimé, moteur de la fiche) · type de propriétaire (PM nommée / particulier) · « en succession depuis » si une date existe, sinon « signal daté du [millésime] ». Bandeau de tête : « N parcelles · signal [source] au [millésime] ».

**Gestes.** Voir la fiche → · sélection → « Préparer les courriers (N) » (pont Courrier, fil de retour) · sélection → « Comparer (N) » (cap 3) · « Assembler avec les voisines → » sur une carte (pont vers le lot B).

**État vide honnête.** Commune sans parcelle en succession : « Aucune parcelle en succession connue à [commune] au [millésime] ». Jamais trois zéros.

**Tiroir « Détail et méthode ».** Ce que veut dire le signal (rédigé d'après A0), sa source, son millésime, ce qu'il ne dit pas.

**Capteur d'usage** : même compteur que les autres outils (dashboard Produit).

## Lot B — Assemblage : proposer les voisines contiguës

Aujourd'hui l'outil attend que l'utilisateur clique les parcelles une à une sur la carte. Le moteur de contiguïté existe (ST_DWithin 0,5 m, union-find). Il sert désormais l'utilisateur au lieu de le suivre.

**B1. Entrée par parcelle.** En tête d'Assemblage, omnibox `ParcelInput` (IDU · adresse · référence courte) en plus du clic carte. Une parcelle désignée devient la parcelle de départ.

**B2. Voisines proposées.** Dès qu'une parcelle de départ existe, l'outil sert ses voisines contiguës (premier anneau, cadastre seulement, domaine public exclu) en cartes empilées : IDU · surface · zonage · résiduel SDP (Estimé) · type de propriétaire · « même propriétaire que la parcelle de départ » quand c'est le cas, en tête de liste. Bandeau : « N voisines contiguës, dont M du même propriétaire ».

**B3. Sélection.** Case par voisine ; les cochées entrent dans l'assemblage existant, qui se recalcule comme aujourd'hui. Aucune voisine n'est cochée d'office. Les voisines cochées apparaissent sur la carte avec le même style que les parcelles cliquées.

**B4. Anneau suivant.** Sur une voisine cochée, geste « ses voisines → » qui étend la proposition d'un anneau depuis cette parcelle. Pas de recherche automatique au-delà.

**B5. Ponts.** Ce qui existe déjà reste (Courrier, Projets). En plus : « Scan patrimoine → » sur une voisine à propriétaire PM. Fil de retour si l'outil a été ouvert depuis Successions, Étudier un bien ou une fiche.

**B6. Perf.** Temps de réponse de l'endpoint « voisines » mesuré sur les trois parcelles fixes de l'audit (Saint-Denis Uavap, Saint-Paul Acu, Saint-Philippe RNU) et consigné au compte-rendu.

---

## Compte-rendu

≤ 20 lignes : A0 en trois lignes (servable / manque / commande de rafraîchissement proposée), les commits, les captures, B6, ce qui a résisté avec `fichier:ligne`, tests. Toute décision prise faute d'instruction est signalée.
