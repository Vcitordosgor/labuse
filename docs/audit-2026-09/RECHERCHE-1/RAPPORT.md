# RECHERCHE-1 — Audit des barres de recherche

**Branche** `audit/recherche-1` (worktree `labuse-recherche`, base `c03f36d8`) · **lecture seule**, aucune écriture dans `src/` ni `frontend/src/`.
**Date** 2026-09-24.

## Mandat de Vic

> Toute barre de recherche de l'app doit accepter et **résoudre les trois familles** — **propriétaire** (nom de société ou SIREN), **parcelle** (IDU ou référence courte type `BW0917`), **adresse** — et le **proposer visiblement** (suggestions par famille pendant la frappe, comme Scan patrimoine aujourd'hui).

## Méthode & preuves live

- **Statique** : lecture de tout ce qui est une barre de saisie de recherche dans `frontend/src` (grep `<ParcelInput`, `<AddressAutocomplete`, inputs à placeholder « recherch/adresse/SIREN/parcelle/nom »).
- **Live** : l'app de mon worktree (8145/5345) n'était pas démarrée ; j'ai interrogé l'instance en cours sur **8135**. `git diff` confirme que `api/recherche.py`, `proprietaire_facettes.py`, `AddressAutocomplete.tsx` et `ParcelInput.tsx` sont **identiques** entre la branche courante et celle de l'instance (`265c81b7`) → les mesures sont fidèles.

`GET /api/recherche/suggest` (les 4 requêtes du mandat, toutes familles demandées) :

| requête | résultat live |
|---|---|
| `CBO` | **propriétaire** ×3 (CBO TERRITORIA `452038805`, CBO DEVELOPPEMENT, CBO PROPERTY) |
| `421032555` | **total 0** — ce SIREN n'a aucune parcelle PM à La Réunion (grammaire SIREN = `siren LIKE …%` sur `parcelle_personne_morale`). `452038805` (CBO) renvoie bien 1. |
| `BW0917` | **parcelle** ×2 (BW 917 — Saint-Benoît / Saint-Paul), désambiguïsation par commune |
| `27 chemin Vidot Saint-Denis` | **total 0** ; `chemin Vidot` → **adresse** ×4, `Vidot` → adresse + **propriétaire** (SCI VIDOT FILS…) |

**Deux constats de fond côté serveur** (indépendants du front) :
- **G-SRV1 — adresse « n°+voie+commune » sans code postal = 0.** `_sugg_adresse` (`recherche.py:129`) matche la saisie repliée en **sous-chaîne contiguë** (`col LIKE '%'||q||'%'`) sur `numero+rep+voie+CP+commune`. `27 chemin Vidot Saint-Denis` saute « La Bretagne » **et** le CP 97490 qui sont stockés *entre* la voie et la commune → aucune sous-chaîne contiguë → **0**. `chemin Vidot` seul marche. C'est exactement le format qu'un pro colle. À corriger par un match par **jetons (AND)** plutôt qu'une sous-chaîne unique.
- **G-SRV2 — SIREN absent de la base PM = 0 muet côté famille.** Honnête (pas d'invention) mais la barre doit le **dire** (« aucun propriétaire pour ce SIREN à La Réunion ») ; l'état vide de `AddressAutocomplete` liste les formats acceptés, pas ce cas précis.

## Architecture (ce qui existe déjà)

Le socle unifié **est déjà en place** (RETOURS-16 V5). Ce n'est pas à reconstruire :

- **`api/recherche.py`** — **un seul** endpoint `/api/recherche/suggest`, **6 grammaires typées** : `adresse`, `cadastre` (IDU + référence courte), `proprietaire` (dénomination PM), `siren`, `commune`, `projet`. Les 3 familles du mandat sont **toutes** servies par le back. Aiguillage par forme de saisie, 8 propositions max, `< 150 ms` (index dédiés).
- **`AddressAutocomplete.tsx`** — LE composant de barre partagé (suggestions groupées, type en libellé discret à gauche, clavier + ARIA, état vide honnête). Il consomme les grammaires que l'appelant **déclare** via la prop `grammaires` (**défaut `['adresse','cadastre']`**).
- **`ParcelInput.tsx`** — enveloppe `AddressAutocomplete` pour les barres « parcelle » (+ désambiguïsation réf. courte multi-communes + bouton « cliquez une parcelle »). Prop `grammaireProprietaire` qui, si activée, ajoute `proprietaire`+`siren` et route un pick propriétaire vers `onAddress(siren)`.

**Conséquence :** le manque est **quasi entièrement côté front** — la plupart des barres ne **déclarent pas** les grammaires propriétaire/SIREN et ne savent pas **quoi faire** d'un pick propriétaire. Le back sait déjà résoudre les 3 familles.

**Note « résolution adresse ».** `_sugg_adresse` ne renvoie que des lignes `idu IS NOT NULL` : **choisir une suggestion d'adresse rattache donc toujours une parcelle** (`onSelect` → `idu` → `onPick(idu)`). L'adresse est donc *résolue* dans toutes les barres `ParcelInput`, même celles sans `onAddress` (le `onAddress` ne sert qu'au repli « Entrée » sur une adresse libre hors suggestion).

---

## A. Inventaire

Légende par famille : **S** = suggère pendant la frappe · **R** = résout (sélection → action). `—` = ni l'un ni l'autre.

### A.1 Barres de recherche d'entité (le mandat 3-familles s'applique)

| # | Barre (écran) | fichier:ligne | Composant | Propriétaire | Parcelle | Adresse |
|---|---|---|---|---|---|---|
| 1 | **Header / omnibox app** | `header/Header.tsx:212` | `AddressAutocomplete` `grammaires=[adresse,cadastre,proprietaire,siren]` + `onEnterRaw` résolveur complet | **S+R** (pick→Scan patrimoine ; nom tapé→`modPatrimoineSearch`→Scan) | **S+R** (réf. courte multi-commune gérée) | **S+R** |
| 2 | **Scan patrimoine (outil)** | `outils/ScanPatrimoine.tsx:138` | `ParcelInput grammaireProprietaire` | **S+R** (pick→SIREN→scan) | **S+R** | **S+R** |
| 3 | Étudier un bien (bloc B / O5) | `outils/blocB.tsx:58` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 4 | Faisabilité (M22, via `ParcelPicker`) | `outils/ParcelPicker.tsx:10` (`M22Programme.tsx:256`) | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 5 | Gabarit | `outils/Gabarit.tsx:175` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 6 | Étude de zone (autour d'un point) | `outils/EtudeZone.tsx:226` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 7 | Prospection solaire | `outils/ProspectionSolaire.tsx:325` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 8 | Renouvellement urbain | `outils/Renouvellement.tsx:78` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 9 | Calculette foncière | `outils/CalculetteFonciere.tsx:26` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 10 | Mon secteur | `outils/MonSecteur.tsx:143` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 11 | Taxe d'aménagement | `outils/TaxeAmenagement.tsx:156` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 12 | Vérif. procédure | `outils/VerifProcedure.tsx:30` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 13 | Assemblage — parcelle de départ | `outils/moteurs.tsx:191` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 14 | Comparer des parcelles | `compare/ComparePanel.tsx:142` | `ParcelInput` `withCarte=false` | — | **S+R** | **S+R** |
| 15 | Veille / Surveillance — suivre une parcelle | `surveillance/SurveillancePanel.tsx:110` | `ParcelInput` (+`onAddress` message) | — | **S+R** | **S+R** |
| 16 | Remonter le temps | `outils/ModulePanel.tsx:1173` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 17 | Courrier propriétaire | `outils/ModulePanel.tsx:1395` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 18 | Due diligence (lot) | `outils/ModulePanel.tsx:1566` | `ParcelInput` (défaut) | — | **S+R** | **S+R** |
| 19 | Permis (recherche) | `outils/ModulePanel.tsx:735` | `AddressAutocomplete` `grammaires=[adresse,cadastre,commune]` | — | **S+R** (+ n° permis) | **S+R** |
| 20 | Radar — recentrer la carte | `outils/RadarView.tsx:477` | `AddressAutocomplete` (défaut) | — | **S+R** | **S+R** |
| 21 | Veille promoteurs — se positionner | `outils/VeillePromoteurs.tsx:217` | `AddressAutocomplete` (défaut) | — | **S+R** | **S+R** |
| 22 | Radar — dépôt agence | `radar/DepotAgence.tsx:74` | `AddressAutocomplete` (défaut) | — | **S+R** | **S+R** |
| 23 | **Scan patrimoine (module fusion)** | `outils/ModulePanel.tsx:216` | `<input>` local + typeahead maison (`modPatrimoineSearch`) | **S+R** (nom/SIREN) | — | — |
| 24 | **Signal ZAN par parcelle** | `outils/moteurs.tsx:496` | `<input>` local brut (aucun suggest) | — | **R** (IDU collé/clic carte, **pas de S**) | — |

### A.2 Barres qui NE sont PAS des résolveurs d'entité (autre nature — listées pour complétude)

| Barre (écran) | fichier:ligne | Nature | 3 familles ? |
|---|---|---|---|
| CRM — recherche | `crm/Kanban.tsx:462` | **Filtre client** des cartes du pipeline (nom, commune, IDU, société) — n'ouvre rien, filtre une liste | non (filtre local, aucune suggestion) |
| Fiche — chercher dans la fiche | `fiche/Fiche.tsx:1112` | **Recherche dans-page** (risque/réseau/ICPE) — surligne le contenu de la fiche ouverte | hors sujet |
| Copilote (accueil) | `copilote/AccueilCopilote.tsx:169` | **Prompt conversationnel** (mission en langage naturel) | hors sujet (l'agent peut résoudre des entités, mais ce n'est pas une barre de recherche) |
| Copilote (embarqué) | `copilote/CopiloteEmbarque.tsx:78` | Prompt conversationnel | hors sujet |
| Sources (page) | `sources/SourcesPage.tsx:190` | Filtre de la liste des sources de données | hors sujet |
| Admin — circuit (diagramme) | `admin/circuit/CircuitDiagram.tsx:136` | Filtre réservoirs/robinets | hors sujet |
| Admin — circuit (sources) | `admin/circuit/Sources.tsx:41` | Filtre sources | hors sujet |
| Admin — licences | `admin/Licences.tsx:690` | Filtre licences (nom/e-mail) | hors sujet |

**Écrans sans barre de recherche** : **Projets** (`projets/*` = champs de formulaire nom/budget uniquement ; une parcelle entre dans un projet *depuis la fiche*, pas via une recherche). Champs de formulaire non comptés : `admin/Programmes.tsx:69-70` (SIREN/nom du promoteur), `admin/Courrier.tsx:267` (adresse d'opportunité), `fiche/Fiche.tsx:108` (« champ concerné » d'un signalement).

### Décompte

- **24** barres de recherche d'entité (A.1) + **8** barres filtre/find/chat (A.2) = **32** champs de saisie de recherche.
- **Conformes aux 3 familles (S+R partout)** : **2** — Header (#1) et Scan patrimoine outil (#2).
- **17** barres (#3–#19) couvrent **2 familles sur 3** (adresse + parcelle) et **ne proposent jamais un propriétaire**.
- **3** barres franchement incomplètes (voir §Message de fin).

---

## B. Ce qui manque, barre par barre

### B.1 Le trou commun : la famille « propriétaire »

Les 17 barres `ParcelInput`/`AddressAutocomplete` par défaut (#3–#22) **ne déclarent pas** `proprietaire`+`siren`. Conséquence testable :
- un **nom** tapé (« CBO ») n'apparaît jamais en suggestion ;
- un **SIREN** tapé (`452038805`) : `ParcelInput.onEnterRaw` ne reconnaît ni IDU (14 car.) ni section+numéro → part en `onAddress(raw)` (repli adresse) ou tombe dans le vide → **jamais résolu**.

Le back sait pourtant répondre (cf. §preuves). **Il suffit de déclarer les grammaires et de router le pick.**

### B.2 Les deux barres à socle propre (à rapatrier)

- **#24 Signal ZAN** (`moteurs.tsx:496`) : `<input>` brut, **1 famille** (IDU), **aucune suggestion**, ni adresse ni propriétaire, ni référence courte. La barre la moins-disante de l'app.
- **#23 Scan patrimoine (module)** (`ModulePanel.tsx:216`) : `<input>` + typeahead maison, **propriétaire seul** — exactement l'inverse du reste. Double emploi avec Scan patrimoine outil (#2) qui, lui, fait déjà les 3 familles via `ParcelInput grammaireProprietaire`.

### B.3 Ce qu'un résultat « propriétaire » doit faire dans un outil qui part d'une parcelle

C'est le point de conception clé (Vic l'a esquissé). Un outil comme *Étudier un bien*, *Gabarit*, *Taxe*, *Comparer* attend **un IDU**, pas un SIREN. Proposition :

> **Choisir un propriétaire dans la liste → dérouler ses parcelles et laisser choisir.**
> Réutiliser `parcelles_par_entreprise` / `patrimoine()` (la donnée de Scan patrimoine, `parcelle_personne_morale` par SIREN). Afficher une mini-liste (référence courte · commune · surface, comme la désambiguïsation réf. courte déjà présente dans `ParcelInput`), l'utilisateur tranche → `onPick(idu)` alimente l'outil normalement. **Jamais d'auto-pick** (doctrine V5.5 : ne pas deviner à la place).
> - 1 parcelle → sélection directe.
> - N parcelles → liste (triée commune du contexte d'abord, exactement comme la réf. courte multi-communes existante).
> - Cas particuliers : *Comparer* peut proposer « ajouter les N parcelles » ; *Courrier* part déjà du propriétaire → un pick propriétaire peut cibler directement le destinataire ; *Radar/Veille positionnement* → recentrer sur l'emprise des parcelles du propriétaire.

Ce comportement **n'existe nulle part** aujourd'hui côté outil (seuls Header et Scan patrimoine consomment un propriétaire, et pour eux la cible EST le patrimoine, pas une parcelle unique).

### B.4 Corrections back (transverses, bénéficient à toutes les barres)

- **G-SRV1** — `_sugg_adresse` : passer d'un `LIKE '%q%'` contigu à un **AND par jetons** (chaque mot de la saisie doit apparaître, ordre libre) pour que « n° + voie + commune » sans CP retrouve la parcelle. Test de non-régression : `27 chemin Vidot Saint-Denis` doit renvoyer la parcelle.
- **G-SRV2** — SIREN/propriétaire sans résultat : message dédié (« aucun propriétaire pour « … » à La Réunion ») au lieu de l'état vide générique.

---

## C. Plan de branchement (en lots)

**Composant unique à retenir : `ParcelInput`** (qui enveloppe déjà `AddressAutocomplete`). C'est la seule barre d'entrée d'entité de l'app. `AddressAutocomplete` reste le **moteur de suggestion** sous-jacent ; on ne le rappelle en direct que pour les barres non-parcelle (permis, positionnement carte) — et encore, on peut les faire passer par `ParcelInput` aussi.

### Lot 1 — `ParcelInput` couvre les 3 familles par défaut *(le gros du gain, ~0 code par outil)*
1. Généraliser `grammaireProprietaire` : `ParcelInput` déclare **par défaut** `['adresse','cadastre','proprietaire','siren']`.
2. Y intégrer le **sous-panneau « propriétaire → ses parcelles »** de §B.3 (réutilise la liste patrimoine + le rendu de désambiguïsation déjà présent). Un pick propriétaire n'émet `onPick(idu)` qu'après le choix d'une parcelle.
3. Effet : les barres **#3–#18** (13 outils) deviennent conformes **sans toucher un seul outil**. Les tests `omnibox.test.tsx` couvrent déjà le socle.

### Lot 2 — Rapatrier les deux socles propres
- **#24 Signal ZAN** (`moteurs.tsx:496`) → remplacer le `<input>` brut par `ParcelInput`.
- **#23 Scan module** (`ModulePanel.tsx:216`) → soit `ParcelInput` (3 familles), soit fusion pure avec Scan patrimoine outil (#2). Supprimer le typeahead maison `modPatrimoineSearch` en front au profit du suggest unifié.

### Lot 3 — Barres carte (`AddressAutocomplete` direct : #19–#22)
- Décider par barre : *Radar / Veille positionnement / dépôt agence* → ajouter `proprietaire` avec l'action « recentrer sur l'emprise des parcelles du propriétaire » (fly-to / liste). *Permis* → ajouter `proprietaire` (permis rattachés au patrimoine) ou statuer que le propriétaire n'y a pas de sens et le documenter. Le plus simple : les faire passer par `ParcelInput` du Lot 1 quand une parcelle unique est attendue.

### Lot 4 — Corrections back transverses
- **G-SRV1** (match adresse par jetons) et **G-SRV2** (message SIREN absent). Indépendant des lots front, à faire tôt (bénéficie à tout le monde, y compris Header/Scan déjà conformes).

### Lot 5 — CRM (optionnel, hors mandat strict)
- `Kanban.tsx:462` reste un **filtre** ; on peut lui adjoindre le suggest unifié comme raccourci « aller à » (ouvrir la fiche d'une parcelle / le patrimoine d'un propriétaire) sans casser le filtre local. À trancher avec Vic.

### Ordre conseillé
**Lot 4** (back, socle) → **Lot 1** (13 outils d'un coup) → **Lot 2** (2 socles propres) → **Lot 3** (barres carte) → **Lot 5** (CRM, si validé).

---

## Synthèse

- **32** champs de recherche, dont **24** résolveurs d'entité.
- **2** conformes aux 3 familles : **Header** et **Scan patrimoine (outil)**.
- Le trou est **uniforme et front** : 17 barres à 2/3 (jamais de propriétaire) + 2 socles propres à 1/3. Le back résout déjà les 3 familles.
- **Un seul geste structurant** (Lot 1 : `ParcelInput` 4 grammaires par défaut + sous-panneau propriétaire→parcelle) rend conformes 13 outils sans les toucher.
</content>
</invoke>
