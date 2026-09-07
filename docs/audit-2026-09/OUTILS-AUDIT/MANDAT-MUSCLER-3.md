# MANDAT OUTILS-MUSCLER-3 — Blocs fonciers

**Rédigé par :** Fable, 06/09/2026. Dernier mandat issu de OUTILS-AUDIT-1 (Partie C, regroupement 7).
**Branche :** `feat/blocs-fonciers`, créée depuis `main` à jour.
**Périmètre :** un outil neuf et son batch. Rien d'autre.

**L'idée en une phrase :** un même propriétaire détient souvent plusieurs parcelles côte à côte sans que ça se voie, parce que chaque parcelle est petite et isolée dans les listes ; regroupées, elles forment une assiette qui intéresse un promoteur — l'outil sert la liste de ces assiettes sur toute l'île, sans qu'on ait à connaître le propriétaire d'avance.

## Étape 0

`pwd`, `git branch --show-current`, `git status -sb`. Conditions : branche `feat/blocs-fonciers`, arbre propre, `main` contient le merge de `feat/remonter-le-temps-2`. Sinon : s'arrêter.

## Garde-fous

- DA existante, composants existants : cartes empilées (panneau 320 px), sélecteur de commune, filtres à paliers, fil de retour `<RetourOutil/>`, badges Sourcé / Estimé, tiroir « Détail et méthode ».
- Aucun bouton d'export. Aucune surface IA. Aucun badge de score.
- Personne morale nommée, particulier jamais nommé.
- Aucun calcul métier au front. Run épinglé `q_v11_m137` via la constante unique.
- Capture avant / après dans `docs/audit-2026-09/OUTILS-MUSCLER-3/` ; si Playwright expire sur le canvas WebGL, preuve DOM écrite.
- Tests verts (`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`). Un commit par lot, push, **pas de merge**.

---

## Lot A — Cadrage, en lecture seule, avant d'écrire le batch

Livrable : `docs/audit-2026-09/OUTILS-MUSCLER-3/A-cadrage.md`, ≤ 30 lignes. CC établit, preuves `fichier:ligne` et SQL rejouable :

1. **Ce qui existe déjà.** Le moteur de contiguïté d'Assemblage (ST_DWithin 0,5 m, union-find) et l'endpoint voisines de MUSCLER-1 : que peut-on réutiliser tel quel, que faut-il écrire ?
2. **L'identité du propriétaire.** Sur quoi regroupe-t-on : SIREN pour les PM, et pour les particuliers ? Si les particuliers ne sont pas identifiables de façon fiable d'une parcelle à l'autre, **l'outil se limite aux personnes morales** et le dit à l'écran — pas de regroupement par nom approché.
3. **Volume réel.** Combien de blocs de 2 parcelles ou plus par SIREN, sur l'île ? Distribution par taille (2, 3-5, 6-10, 10+) et par commune. Le chiffre de ~12 000 clusters de l'audit est-il confirmé ?
4. **Coût du batch.** Temps de calcul estimé sur l'île entière, index nécessaires (existent-ils ?), taille de la table produite.
5. **Verdict en trois lignes** : le batch est-il tenable tel que décrit, ce qui doit être ajusté, et si un index manque, lequel — **sans le créer**.

Si A conclut que le chantier est nettement plus lourd que décrit, CC s'arrête après A et le dit. Le lot B ne démarre pas sur un cadrage négatif.

## Lot B — Le batch

**B1.** Un batch qui balaie l'île et produit une table `parcel_blocs` (ou le nom retenu en A) : un enregistrement par bloc — identifiant de bloc, SIREN, liste des IDU, nombre de parcelles, surface totale, communes concernées, résiduel SDP agrégé (somme des résiduels par parcelle, moteur existant, statut Estimé), zonages présents.

**B2.** Le batch est **rejouable et idempotent**, épinglé au run, journalisé comme les autres batches de l'app. Il ne s'exécute pas automatiquement : CC écrit la commande, la teste, et la documente — c'est Vic qui la lance (doctrine d'injection sur clic humain).

**B3.** Règles de regroupement explicites et écrites : contiguïté à 0,5 m, même SIREN, parcelles cadastrales seulement (domaine public exclu), blocs de 2 parcelles minimum. Toute règle ajoutée par CC est signalée au compte-rendu.

**B4.** Tests : au moins un bloc connu vérifié à la main (IDU listés, surface, résiduel), plus un cas limite (parcelle isolée non regroupée, parcelles contiguës de propriétaires différents non regroupées).

## Lot C — L'outil

Nouvelle entrée du menu Outils : **Blocs fonciers** — « Les assiettes d'un même propriétaire, sur toute l'île ».

**Entrée.** Sélecteur de commune (Toute l'île par défaut). Filtres à paliers : surface totale minimale, résiduel SDP minimal, nombre de parcelles minimal.

**Liste.** Cartes empilées, 200 chargées puis « voir plus », triées par résiduel décroissant. Par carte : propriétaire (PM nommée) · nombre de parcelles · surface totale · communes · résiduel SDP agrégé (Estimé) · zonages présents. Bandeau : « N blocs · signal [source] au [millésime] ».

**Détail.** Au clic sur une carte : la liste des IDU du bloc, chacun avec surface et zonage, et l'emprise du bloc affichée sur la carte.

**Gestes.** Sélection → « Préparer les courriers (N) » (pont Courrier, fil de retour) · sur une carte, « Scan patrimoine → » (le SIREN) et « Assembler → » (Assemblage pré-rempli avec les IDU du bloc) · « Voir la fiche → » sur chaque IDU du détail.

**État vide honnête.** Commune sans bloc : « Aucun bloc de deux parcelles ou plus à [commune] ». Jamais de zéros.

**Tiroir « Détail et méthode ».** Les règles de B3, la source, le millésime, ce que l'outil ne dit pas (notamment : les particuliers, si A a conclu qu'ils sortent du périmètre).

**Capteur d'usage** comme les autres outils.

**Perf.** Temps de réponse de la liste mesuré sur Toute l'île et sur deux communes (une dense, une rurale), consigné au compte-rendu.

---

## Compte-rendu

≤ 20 lignes : le verdict de A en trois lignes, la commande du batch (non exécutée), les commits, les captures ou preuves DOM, les mesures de perf, ce qui a résisté avec `fichier:ligne`, tests. Toute décision prise faute d'instruction est signalée.
