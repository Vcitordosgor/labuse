# M130 — PDF projet : audit A → D (rapport seul, avant correctif)

Branche `feat/m130-pdf-projet` (depuis `main` à jour, `bc1732e6`). **Aucun
correctif, aucun commit de code.** Python 3.11.

**Projets de test générés** (PDF joints dans ce dossier) :
- **P1 `projet-P1-large-ile.pdf`** — cadrage LARGE : `{}` (toute l'île),
  programme Logements. Vivier figeable **285 781** / compteur carte 431 663.
- **P2 `projet-P2-etroit-tampon.pdf`** — cadrage ÉTROIT :
  `{communes:[Le Tampon], surfaceMin:3000}`, budget 800 k€. Vivier **839**.
- **P3 `projet-P3-ecartees-stpierre.pdf`** — non constructibles dans la
  shortlist : `{communes:[Saint-Pierre], tiers:[ecartee]}`. Vivier **0**,
  mais 5 parcelles listées (toutes « Écartée »).

Chemin : `projet_export_pdf` (`projets.py:1003`) → `projet_apercu`
(`projets.py:411`) → `_run_cadrage` (`:249`) → `_q_v2_list` (`app.py:2140`) ;
rendu `render_projet_pdf` (`pdf_projet.py:43`).

---

## A — D'où viennent les chiffres

### A.1 Inventaire de chaque grandeur affichée

**Fiche de cadrage :**

| Affiché | Champ | Table / origine | Nature |
|---|---|---|---|
| Programme « Logements (indicatif) » | `identite.type_logement` | `projets.identite` (JSON saisi) | **Saisi**, marqué indicatif |
| Périmètre | `cadrage.communes` | `projets.filtres` (facette) | Saisi (facette) |
| SDP min. | `apercu.sdp_besoin_m2` ← `cadrage.sdpMin` | facette | Saisi (facette) |
| Surface | `cadrage.surfaceMin/Max` | facette | Saisi (facette) |
| Budget foncier | `identite.budget_eur` | `projets.identite` | **Saisi**, indicatif |

**Meilleures parcelles :**

| Affiché | Champ | Table | Nature |
|---|---|---|---|
| « N correspondent au projet » | `apercu.n` = `_vivier_figeable` | `dryrun_parcel_evaluations` × `parcel_p_score_v2` (count hors étage 0) | Dérivé |
| **Ordre 1..5** | `_q_v2_list` `ORDER BY rang` | `parcel_p_score_v2.rang` | **Score interne (rang P)** |
| IDU (+ section/n°) | `it.idu` | `parcels.idu` | Sourcé |
| Commune | `it.commune` | `parcels.commune` | Sourcé |
| Adresse BAN | `adresses_ban`→`format_adresse` | BAN (`adresses`) | Sourcé, sinon « Adresse non disponible » |
| « pourquoi » (ligne unique) | `tier_v2`→`_TIER_LABEL`, ou « Écartée » si `etage0` | `parcel_p_score_v2.tier` / `d.status` | **Verdict interne** |
| « pourquoi » SRU (conditionnel) | `commune ∈ carencees` | `commune_contexte_sru` | Sourcé |

**Code de `_pourquoi_lignes` JAMAIS rendu par ce chemin** (champs absents du
dict `_q_v2_list`) : `q_score` (« qualité X/100 », `:343`), la ligne
« Probabilité de mutation élevée… » (`:350-351`), **SDP résiduelle** (+ % du
besoin, `:352-359`), **Hauteur PLU** (+ zone, vérifiée/à instruire,
`:360-363`). → **code mort dans le PDF projet.** Vérifié empiriquement sur
P1/P2/P3 : chaque « pourquoi » ne contient qu'**une ligne = le verdict**.

### A.2 Correctifs M128/M129 qui auraient dû s'appliquer

- **Hauteur calibrée** (M129-2 A / M128-2-A) : `_pourquoi_lignes:362` prévoit
  « Hauteur PLU {hauteur_plu_m} m » — **valeur unique, non égout/faîtage**,
  intention identique au bug corrigé pour le pack (9 m générique). Non rendu
  aujourd'hui (champ absent), mais le code mort porte la mauvaise intention.
- **SDP / emprise clippée** (M129-2 E) : la ligne SDP résiduelle est du code
  mort ; si rebranchée, devrait venir de la SDP à emprise clippée. Non rendu.
- **Marge / charge foncière** : le PDF projet n'affiche **aucun euro de
  bilan** → correctifs bilan non concernés.
- **Fraîcheur / sources** : le pied de page (`export_commun`) porte les
  attributions + non-garantie + disclaimer CU + **date de génération**, mais
  **aucun millésime de source amont** ni date du run de scoring.
- **Verdict / score exportable** : la doctrine « aucun exportable ne porte
  verdict/rang/score » **n'a jamais été appliquée à ce document** — c'est le
  correctif majeur manquant (cf. B).

### A.3 Snapshot figé ou donnée vivante ?

**Vivante (recalcul au moment de la génération).** `projet_export_pdf`
recalcule via `projet_apercu` (docstring `:1005` « aperçu recalculé sur les
données ACTUELLES »), **ignorant la shortlist FIGÉE** du projet
(`models.Projet.derniere_execution_at` / `shortlist_perimee`). Conséquences :
le PDF peut **diverger de la shortlist enregistrée** que l'utilisateur voit
dans l'app. Le run lu (`q_v10_m129`) est un batch de scoring ; le document
**n'affiche ni sa date ni son libellé**, seulement la date de génération, et
**ne dit pas** qu'il recalcule.

### A.4 Les 8 champs morts de `_q_v2_fiche`

Le PDF projet passe par **`_q_v2_list`, pas `_q_v2_fiche`**. Les 8 champs morts
(`completeness_score`, `score_v`, `anru`, `terrain`, `coproprietes`,
`marche_secteur`, `parc_analysees`, `flags`) sont un sujet `_q_v2_fiche` →
non traversés ici. `_q_v2_list` renvoie bien `completeness_score` (1 des 8)
mais le PDF **ne le sert pas**. → **Le PDF projet ne sert aucun des 8 champs
morts.**

---

## B — Verdicts, rangs, scores

### B.1 Tout ce qui relève de l'analyse

- **VERDICT** : l'unique ligne « pourquoi » = le libellé de tier
  (**Priorité / À suivre / Faible / Neutre**) ou **« Écartée (exclusion
  dure) »**. Verdict servi nu sur un exportable. (Preuve P1/P3.)
- **RANG** : parcelles numérotées **1..5**, section titrée **« MEILLEURES
  PARCELLES »**, ordre = `parcel_p_score_v2.rang` (rang du **P-score**, proba
  de mutation).
- **TRI par score** : oui, implicite (rang P), **invisible** pour le lecteur.
- **« top N »** : « MEILLEURES PARCELLES · N correspondent » — « meilleures »
  = jugement.
- **SCORE « qualité X/100 »** : code présent (`:343`) mais **non rendu** ;
  **la mention menthe l'annonce pourtant** (« statut/score », `pdf_projet.py:149`).
- **Probabilité** : ligne « Probabilité de mutation élevée… » présente en code,
  non rendue.
- **Indices de complétude / étoiles / pastilles couleur** : aucun (texte,
  puces menthe).

### B.2 Le classement est-il un ordre de score ?

**Oui** — `s2.rang` = rang du P-score (proba de mutation calibrée, `_q_v2_list`
tri par défaut `rang`). **Non visible** : aucune mention du critère de tri.

### B.3 Un tri non expliqué est déjà un verdict

Confirmé, et **aggravé** : l'ordre **contredit les libellés visibles**. Sur
P1 : #1-3 « À suivre », #4 « Faible », **#5 « Priorité »** — une « Priorité »
en dernière position. Le lecteur voit un classement dont le critère (rang P)
diffère du label (tier) affiché, **sans aucune explication**. Le tri EST le
verdict caché du document.

---

## C — Faux constats et libellés

1. **Libellé ≠ couche réelle** : la mention menthe (`pdf_projet.py:148-151`)
   annonce « **SDP résiduelle, hauteur PLU, statut/score, contexte SRU** » —
   mais **SDP et hauteur ne sont jamais rendues**, et le score non plus. **La
   mention décrit un contenu que le document ne produit pas** (faux constat
   sur son propre contenu). Proxys SAR/RPG/BD CARTO/INPN : non employés ici
   (pas de builder risque/patrimoine) → RAS. Libellé de zone « U » : code mort.
2. **Fraîcheur** : **aucun millésime de source amont**. Seule date = celle de
   **génération** (pied de page). Le run `q_v10_m129` n'est pas daté.
3. **Builder en panne** : `top` vide → « Aucune parcelle ne correspond encore
   à ce cadrage — élargissez… » (`:140`). Se lit **« rien de constructible »**,
   pas « moteur indisponible » : pas d'état INDISPONIBLE distinct du vide
   légitime. Pire — **incohérence n vs top** (P3) : « **0 correspondent** » en
   titre AU-DESSUS de **5 lignes** listées (`n=_vivier_figeable` exclut
   l'étage 0 ; `top=_run_cadrage(tiers:ecartee)` l'inclut → les deux
   divergent).
4. **Personne physique** : le PDF **n'affiche pas** le champ `proprio`
   (pourtant présent dans `_q_v2_list`). Seulement IDU/commune/adresse
   BAN/verdict. **Aucun nom de personne physique.** ✓
5. **Décimales / milliers / vocabulaire** : milliers = espace insécable
   (« 285 781 ») ✓ ; budget en k€ ✓ ; pas de décimale parasite. Vocabulaire
   de jugement : « MEILLEURES PARCELLES ».

---

## D — Cadrage du document

1. **À qui s'adresse-t-il ?** Titre « dossier PROJET », sous-titre « Radar
   foncier premium ». **Le document ne dit pas** s'il est un document de
   travail interne ou une présentation à un tiers — ambigu entre la fiche
   premium (interne) et le dossier parcelle (tiers). Or il **porte des
   verdicts/rangs** (registre interne) tout en étant estampillé « premium »
   (vendable). Contradiction non levée.
2. **Mention de limites** : **oui** via `export_commun.pied_de_page_pdf` (non-
   garantie + disclaimer CU au mot près + attributions + date de génération).
   Mais **pas de « ce que ce document ne peut pas dire » propre au projet**
   (ex. « le classement est une proba de mutation, pas un avis de
   constructibilité »). Et la mention menthe est **fausse** (annonce
   SDP/hauteur/score absents).
3. **Nommage** : `projet-{slug}.pdf` (slug du nom, 48 car.). Pas `{IDU}-labuse`
   (normal : multi-parcelles). **Proposition** : suffixe doctrine →
   `projet-{id}-{slug}-labuse.pdf` (id stable = pas de collision entre projets
   homonymes ; slug lisible ; suffixe `-labuse`). Actuellement : pas de suffixe
   `labuse`, et deux projets homonymes collisionnent (slug seul).
4. **Deux surfaces** : **même document, aucune variante.** Copilote
   (`App.tsx:216`) et kanban (`ProjetKanban.tsx:189`) pointent tous deux
   `projetPdfUrl(id)` → `GET /projets/{id}/export.pdf` →
   `projet_apercu(limit=5)`. Nuance : le copilote exporte **après**
   enregistrement (il faut un `pid`). Pas de divergence de contenu.

---

## Synthèse — ce qui saute aux yeux

1. **Verdict + rang caché** (B) : le seul contenu par parcelle est un
   **verdict** ; l'ordre est un **rang de P-score** non expliqué, qui
   **contredit les libellés**. Violation frontale de la doctrine.
2. **Mention fausse** (C.1) : le document **promet SDP/hauteur/score** qu'il
   ne rend pas → moitié du `_pourquoi_lignes` est du **code mort**.
3. **Incohérence n vs liste** (C.3, P3) : « 0 correspondent » + 5 parcelles
   « Écartée ».
4. **Live ≠ shortlist figée** (A.3) : le PDF recalcule et peut diverger de ce
   que l'utilisateur a enregistré, sans le dire.

Rien n'a été modifié. Aucun commit. En attente d'arbitrage.
