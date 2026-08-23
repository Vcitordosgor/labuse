# M143 — Argumentaire : le régime non équilibré, le bouton, les deux dates, les coefficients (`fix/m143-argumentaire`)

Branché sur `origin/main` @ `2005bd1c`. **Prérequis signalé** : `audit/argumentaire` (rapport M142)
pas encore mergé — mais c'est une branche **rapport seul (zéro code)**, aucun impact sur le code de
M143 ; les constats sont en main. Aucune avance de main depuis M142. CC ne merge jamais.

**Résumé : Lot 1 (l'urgence) — plus aucun montant négatif ne circule ; sous des hypothèses qui ne
s'équilibrent pas, le document DIT « opération non équilibrée » et montre les deux termes, au lieu
d'un « −4,51 M€ » héros. Bouton fiche retiré. Deux dates portées. Les deux coefficients : même objet
physique, valeurs divergentes → commentaire rectifié, unification laissée à Vic (STOP sur la valeur).**

---

## Lot 1 — F1 : un changement de régime, pas un plancher

**Un seul point de décision en amont** : `_regime(calc)` (`argumentaire.py`), calculé UNE fois dans
`_collect` (`out["regime"]`), consommé par **toutes** les sections (synthèse, bilan, cascade). Quand
la charge foncière centrale est ≤ 0, `equilibre=False` — et le document n'affiche **aucun prix
d'achat, aucune fourchette, aucun €/m², aucun montant négatif**. La faute M142 (le garde-fou C3 ne
protégeait que la prose du scénario bas) est réparée à la racine : le régime décide, chaque section
obéit.

- **Synthèse** : héros et fourchette supprimés ; à la place, l'énoncé factuel + les deux termes + le
  manque + les leviers (énoncer, jamais conseiller).
- **Bilan (5)** : ni tableau de prix, ni cascade, ni écart de négociation ; l'énoncé factuel + les
  avertissements du moteur.
- **Cascade SVG** : `if terrain <= 0: return ""` (défense) ; jamais appelée en régime non équilibré.
- **§5 cas partiel** (central > 0, borne basse ≤ 0) : la fourchette ne descend pas sous 0 (cellule
  « Bas » → « non équilibré », prose « scénario bas non équilibré »), le pas de synthèse redondant qui
  portait la borne négative est retiré — **sans inventer de borne**.

### Les deux exemplaires (pièce à conviction — texte rendu, hypothèses par défaut 2500 €/m², 21 %)

**Cas F1 `97415000CW1073` (Saint-Paul, 5469 m², AU3a) — AVANT : « −4,51 M€ » en héros. APRÈS :**
> **Synthèse** : « Sous les hypothèses retenues (coût 2500 €/m², marge 21 %), l'opération n'est pas
> équilibrée : le chiffre d'affaires prévisionnel (18,44 M€), une fois la marge et les frais couverts,
> ne suffit pas à financer la construction (18,59 M€) et les VRD (492 k€) — **il manque 4,51 M€ pour
> l'équilibrer. Il n'existe donc pas de prix d'achat maximum** : ce constat porte sur le programme et
> les hypothèses retenues, pas sur la valeur du terrain. Les hypothèses saisies (coût de construction,
> marge) et le programme retenu sont ce qui détermine ce résultat ; les faire varier peut le changer. »
> **Bilan (5)** : « Opération non équilibrée sous ces hypothèses. CA prévisionnel 18,44 M€ · coût de
> construction 18,59 M€ · VRD 492 k€ — après marge et frais, il manque 4,51 M€. Il n'existe pas de
> prix d'achat maximum… »

**Cas nominal `97415000CX1395` (Saint-Paul, 608 m², U3c) — INCHANGÉ AU CENTIME :**
> « la charge foncière supportable … **s'établit entre 35 k€ et 195 k€ (médiane 93 k€)** … Le prix
> demandé (139 k€) excède ce maximum de 46 k€ (+33 %) : l'écart constitue la base factuelle d'une
> contre-proposition. » Héros **93 k€**, tableau `Bas 35 k€ · Médiane 93 k€ · Haut 195 k€ · 153 €/m²`,
> cascade présente. Tous les pas rendus (le filtre ne s'applique qu'aux cas à borne basse ≤ 0).

**Contrôle grep** : sur les DEUX documents complets (synthèse + bilan + réductions + vigilance +
sources), **0 montant en euros négatif** (détecteur `[-−]\d…(?:€|k€|M€)`). Les seuls « -chiffre »
restants sont des dates (2023-2025) et des références d'article (R.571-32) — jamais un montant.

---

## Lot 2 — Le bouton de la fiche est retiré (affichage seul)

`Fiche.tsx:853` : le `<a data-argumentaire … >Éditer l'argumentaire de négociation (PDF)</a>` (et son
commentaire M22-C) sont **retirés**. **La route et le Copilote ne bougent pas** : `ReponseInline.tsx`
sert toujours l'argumentaire sur demande explicite (aucun chip proactif) ; `argumentaire_pdf` intacte.
**Aucun lien mort** : la route existe toujours, le Copilote pointe vers une route vivante. Fermer la
route (et cesser de peupler `answering.py:785`) reste une décision séparée, liée à l'arbitrage de
posture F4 — non anticipée ici.

---

## Lot 3 — F2 : les deux dates

Aligné sur le dossier projet (M139 lot 2) : `_collect` lit `_residuel_run_servi(db)` (lecture directe
du flag `is_served`, **aucun `MAX`/tri lexical** — dette §8) → `out["valeurs_run"]`. La synthèse porte
désormais **« Valeurs (surface constructible, résiduel) au JJ/MM — run N. Marché DVF et millésimes
PLU : voir partie 7. »** Vérifié : *Valeurs au 2026-08-22 — run m135-run2-ile*. La période DVF et les
millésimes PLU (partie 7) restent. Le document dit de quand datent ses chiffres, pas seulement sa date
d'édition (portée par la garde).

---

## Lot 4 — Les deux coefficients de circulation — **STOP sur la valeur, commentaire rectifié**

**Établi : c'est le MÊME objet physique.** Les deux convertissent une surface **utile → SDP** (ajout
des circulations, murs, parties communes) :
- `M22_CIRCULATION = 1,15` (`projet_schema.py:34`) → `derive_sdp_besoin` (`:141`) : le SDP-besoin du
  **cadrage projet** (programme M22, M120).
- `PROGRAMME_CIRCULATION_COEF = 1,20` (`modules.py:1195`) → **faisabilité sens 2** (`POST /programme`) :
  le SDP-besoin d'un programme (M133).

Même grandeur, même sens, **valeurs divergentes** : M133 (arbitrage Vic) a porté sens 2 de +15 % à
+20 % — « le +15 % sous-estimait le besoin, dans le sens du faux positif » — **sans** toucher
`M22_CIRCULATION` resté à +15 %. Le commentaire `projet_schema.py:32` (« +15 % … **comme
faisabilite_sens2** ») était donc devenu **faux**.

- **Commentaire rectifié** (`projet_schema.py`) : dit l'état réel. **La valeur 1,15 n'est PAS changée.**

### Arbitrage (mandat suite) — unifier à 1,20 : les deux mesures → **STOP, zéro impact (code mort)**

Avant d'appliquer, les deux mesures demandées. **La surprise : `M22_CIRCULATION` (1,15) est du CODE
MORT.** `derive_sdp_besoin` — son seul usage — n'est appelé **NULLE PART** (grep repo entier :
`src`, `tests`, `qa`, `frontend` = 0 appelant). Depuis M120, le cadrage filtre sur la **facette
`sdpMin` saisie** (`sdp_residuelle ≥ sdpMin`, `filters.ts:63`, `projets.py:358`), jamais un besoin
dérivé d'un programme. Le coefficient 1,15 n'entre donc dans **aucune requête servie**.

| Mesure | Attendu (prémisse mandat) | **Mesuré** |
|---|---|---|
| 1 · parcelles quittant le vivier (île) | « combien » | **0** — le coef n'est dans aucune requête de cadrage |
| 1 · QA P1-P4 (N avant/après) | N avant / N après | **identique** — P132-135 / P181-184 n'ont même **pas** de facette `sdpMin` (`None`) |
| 2 · projets existants (N relu live) | « chiffre-le, signaler à l'écran ? » | **0 change** — les 13 projets à `sdpMin` filtrent sur la facette stockée, pas le coef |

Preuve directe : `derive_sdp_besoin(40 logts)` répond bien 2 760 m² (1,15) → 2 880 m² (1,20), **mais
0 appelant** ⇒ effet runtime nul. Le seul coefficient de circulation **vivant** est
`PROGRAMME_CIRCULATION_COEF` (1,20), déjà la valeur cible, alimenté explicitement par le front
(`M22Programme.tsx:24`, `coef_circulation = 1 + circulation_pct/100`, défaut 1,20) sur `POST /programme`.

**Le « deux valeurs pour un objet » était un mensonge de SOURCE, à effet runtime ZÉRO.**

### Décision Vic : option A — code mort supprimé (source unique)

**Le vrai constat du lot 4 n'était pas une divergence de valeur, mais un COMMENTAIRE FAUX sur du CODE
MORT.** `derive_sdp_besoin` + `M22_SURFACE_UNITE_M2` + le coefficient 1,15 sont **supprimés** de
`projet_schema.py`. Source unique de la circulation utile→SDP : `PROGRAMME_CIRCULATION_COEF` (1,20,
`modules.py`), le seul chemin vivant (`POST /programme`). Aucune conservation « pour reprise future » :
une fonction inappelée dont l'inertie est ignorée est précisément le piège trouvé ici.

**À consigner pour plus tard (information utile) :** le **cadrage projet ne dérive AUCUN besoin d'un
programme** — depuis M120 il filtre sur la **facette `sdpMin` saisie** (`sdp_residuelle ≥ sdpMin`).
Il n'y a donc pas « deux chemins qui doivent donner le même besoin » : le contrôle homonyme **tombe**
(le cadrage n'a pas de besoin dérivé ; seul `POST /programme` en calcule un, déjà à 1,20).

**Nettoyage des références (aucun orphelin vivant) :**
- Supprimé : les 3 symboles dans `projet_schema.py` ; commentaire remplacé par une note POSITIVE (le
  cadrage filtre sur la facette, source unique = `PROGRAMME_CIRCULATION_COEF`) — sans nommer de symbole
  disparu.
- Corrigé : `docs/cartographie/CARTO_API.md` (cartographie VIVANTE) — mentions retirées des lignes
  projets.py et projet_schema.py.
- **Laissés intacts, signalés** : trois **audits DATÉS historiques** qui les mentionnent au passé
  (`docs/audits/AUDIT_M119_PROJET.md:75`, `reports/m11-ia/AUDIT-EXISTANT-IA.md:43`,
  `reports/m11-ia/AUDIT-SURFACE-C.md:100`) — ce sont des instantanés corrects à leur date ; les
  réécrire falsifierait le registre. Ils ne décrivent pas l'état courant, ne recréent pas le défaut.

Vérifié : `derive_sdp_besoin`/`M22_CIRCULATION` **absents du module** (import OK), `ruff` All checks
passed. Non-régression M143 (régime non équilibré, deux dates, cas nominal) : aucun autre fichier touché.

---

## Lot 5 — Cosmétiques

- **Cascade SVG étiquetée Estimé** : le titre « Le même calcul, en un coup d'œil » porte désormais le
  badge `Estimé`, comme les cartouches et la colonne Nature du tableau.
- **Indicateur de viabilisation** : dit ce qu'il mesure — « proximité des réseaux (eau, électricité,
  voirie, assainissement ; 100 = tout à pied d'œuvre) : X/100 » — au lieu d'un /100 décoratif.

---

## Hors périmètre — dette consignée

**F4 — la posture d'exposition** (route non authentifiée, IDU énumérable, quota contournable sans
session). L'argumentaire n'expose pas de la donnée publique brute : il expose une **position de
négociation** calculée avec les hypothèses de l'utilisateur. La posture mérite un arbitrage à part,
**avec toute la famille de documents parcelle** (dossier, banquier, lettre, pré-dossier — tous
non authentifiés, `tenant.py:24`), pas un correctif isolé. **Dette nommée.** Également hors
périmètre : contenu de la lettre de zonage, Flash, revue de division.

---

## Contrôles finaux

1. **Zéro montant négatif** dans un argumentaire, quel que soit le cas — grep sur les deux PDF de
   référence (F1 + nominal) = 0 montant € négatif. ✓
2. **Cas nominal inchangé au centime** : héros 93 k€, fourchette 35–195 k€, 153 €/m², tous les pas. ✓
3. **Bouton fiche absent** ; **Copilote sert toujours** sur demande ; **aucun lien mort** (route intacte). ✓
4. **Les deux dates présentes**, run lu du flag `is_served` (aucun `MAX`/tri). ✓
5. **Commentaire des coefficients véridique** ; valeur 1,15 non touchée (STOP remonté). ✓
6. **`tsc` vert** ; **ruff** : `argumentaire.py` = 2 pré-existants (F841 `top`, E741 `l`), `projet_schema.py`
   = All checks passed — **zéro nouveau warning**. ✓

*Fin. Commits sur `fix/m143-argumentaire`. Vic merge en `--no-ff` et tranche l'unification des
coefficients (Lot 4) + la posture F4. CC ne merge jamais.*
