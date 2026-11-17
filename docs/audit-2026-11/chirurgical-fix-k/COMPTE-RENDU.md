# CHIRURGICAL-FIX-1 — LOT K (4ᵉ passage du relecteur, 4 parcelles)

**Branche** `fix/chirurgical-k` (depuis `origin/main`, qui contient le LOT J mergé).
**Modèle** Opus 4.8. **Dépôt** `~/Desktop/labuse-chasse-ecrans`. Livraison honnête dans
`~/Desktop/chasse-1/_lot-final-4/` (+ `_saisies.json`). Parcelles : **BW2635** `97422000BW2635`
(Uav, Le Tampon), **AM0838** `97404000AM0838` (UE, L'Étang-Salé), **AD0887** `97422000AD0887`
(Ud, Le Tampon), **IS0448** `97411000IS0448` (Uh, Saint-Denis). Un commit par groupe, gardes dans
`tests/test_chirurgical_fix_k.py`.

---

## 1 — Une livraison honnête
Les **Bilans passent par les VRAIES routes HTTP** (`POST /bilan/{idu}/generer` puis `GET .pdf` / `.xlsx`,
compte authentifié), appelées comme l'écran. **Aucun programme fabriqué, aucun terrain passé à la
main** : la surface de terrain vient du **cadastre** (prefill de la route), la SDP est dimensionnée sur
la **capacité que LABUSE calcule** pour la parcelle (Étude/potentiel), le prix de sortie sur le **neuf
VEFA / médian servi par la fiche**. La **carte de situation N'EST PAS neutralisée** (plan réel rendu →
Dossiers ~273 Ko vs ~160 Ko au LOT J). Script : `scripts/lot_k_livraison.py` ; saisie exacte de chaque
fichier dans `_lot-final-4/_saisies.json`.

| fichier | route | terrain (cadastre) / SDP / prix | note |
|---|---|---|---|
| bilan_BW2635 | `POST /bilan/97422000BW2635/generer` → `.pdf`/`.xlsx` | **2 003** m² / 3 317 m² / 3 000 €/m² | |
| bilan_AM0838 | `POST /bilan/97404000AM0838/generer` | **20 336** m² (était 1 270) / 500 m² / 1 909 €/m² | capacité LABUSE = 0 → SDP hypothétique, **garde-fou affiché** |
| bilan_AD0887 | `POST /bilan/97422000AD0887/generer` | **1 703** m² / 1 047 m² / 2 577 €/m² | |
| bilan_IS0448 | `POST /bilan/97411000IS0448/generer` | **959** m² (était 1 450) / 85 m² / 2 480 €/m² | SDP = capacité terrain libéré |

---

## 2 — Le Bilan ne présente pas ce que le Dossier écarte
### 2a — route Excel : terrain du cadastre, aucune erreur avalée
`api/bilan.py`. La route Excel référençait `_rep` **non importé** → `NameError` avalé par un
`except Exception` → terrain vide. Un helper partagé **`_terrain_sourcee(db, idu)`** sert le PDF ET
l'Excel depuis le cadastre ; l'erreur n'est plus masquée.

### 2b — garde-fou en tête (PDF ET Excel)
`bilan/pdf.py`, `bilan/excel.py`, `bilan/reperes.py` (`garde_fou_bilan`). Si la fiche écarte le
programme (**habitat interdit / non constructible**) ou si la **SDP saisie dépasse la capacité estimée**
(bâti conservé / terrain libéré), un bandeau le dit EN TÊTE, en clair, avec le motif. Le résultat est
identifié **« Programme saisi — non vérifié par LABUSE »**. Preuve AM0838 : PDF et Excel (cellule A2)
portent « habitat interdit » + « non vérifié ».

### 2c — PDF et Excel, mêmes surfaces
Les deux routes lisent le **même document** (`_saisies_du_document`) et le même prefill terrain
(`_terrain_sourcee`) → plancher et taxable identiques. (Le décalage vu au LOT J venait du script qui
passait `programme={"terrain": …}` au PDF sans SDP/taxable ; la livraison LOT K ne passe plus de
programme à la main.)

### 2d — saisie invalide bloque
`bilan/excel.py`, `api/bilan.py`. Une **TVA de vente hors [0 %, 100 %]** (−100 % → `#DIV/0!`) : la
formule CA HT dit **« saisie invalide »** au lieu de propager l'erreur ; une **validation Excel « entre
0 et 1 »** couvre les cellules de TVA (le coût négatif était déjà refusé — LOT I/J).

---

## 3 — Dossier, Estimer, pré-dossier
- **3a** — Estimer : stationnement Le Tampon = **renvoi à l'article** (« voir l'article Ua 12.2 / Ud
  12.2 »), comme le Dossier (`pige/api._regles_zone`) ; plus le barème partiel.
- **3b** — sol : **« 40 % de la parcelle en surface perméable et 30 % de la parcelle en pleine terre »**
  (plus « dont », qui se lit « 30 % de 40 % »). Dossier + traducteur.
- **3c** — IS0448 : raison concrète avec les chiffres — **« mesurée à l'égout (4,1 m, sous la limite
  d'égout de 4,5 m), mais la surélévation est plafonnée au faîtage (7 m) — un repère différent »**
  (`miroir._raison_marge_surelevation`).
- **3d** — AD0887 : le verdict §Risques **NOMME la zone humide** (La Grande Ferme, 100 %) au lieu d'un
  « aucun rédhibitoire » sec (lit `contraintes_parcelle_liste`).
- **3e** — AM0838/UE : la destination « Logement » sous conditions **nomme l'exception réelle**
  (« logement … gardiennage … maximum 50 m² ») via la clause « sauf … » du règlement
  (`destinations._avec_condition`) ; dans l'annexe des sources, le plan de 2017 s'appelle **« PPR
  littoral »** (`sources.corps_sources`).
- **3f** — couverture : le **risque principal** y figure (BW2635 : **« Zone inondable TRI — scénario
  extrême, 85 % »**), lu sur les lignes de la fiche ; un **« 0 m² »** de SDP s'accompagne de son motif
  (AM0838 : **« 0 m² — habitat interdit en zone UE »**).
- **3g** — CERFA : le numéro de voie garde son indice (bis/ter) → **« 18 ter »** (champ `rep`, preuve
  sur le CERFA livré d'IS0448). Estimer et Comparatif changent de numéro quand **leur contenu rendu
  change** (jeton → `_signature_contenu` → substitution, comme pt4) et restent idempotents.
- **3h** — ventes comparables : la date porte le **jour** (« JJ/MM/AAAA ») quand la source DVF le porte
  (`estimer3._jour_mois_annee`). Comparatif compacté.

---

## Recette
`tests/test_chirurgical_fix_k.py` (K2a..d, K3a..h) + tests LOT I/J alignés (sol, validation TVA).
Livraison complète (25 fichiers) régénérée par les vraies routes dans `_lot-final-4/`. Hook pré-push
(secrets + front + unitaire + cohérence) **vert sans `--no-verify`**, branche poussée, **pas de merge**.
