# FENÊTRE PRÉ-M7 · LA SUITE DES 12 OUTILS (+ lot 0 Score É V2)

Branche `fenetre/outils-suite`. **Un outil = un lot = un commit `[O0]`…`[O12]`.** Rapport incrémenté à chaque lot.
Rythme : O0→O5 puis STOP review (mi-course) ; O6→O12 autonome ; STOP final. Vic merge (`--no-ff`) ; je ne merge jamais.

Règles communes (priment sur la vitesse) : réutiliser l'existant, zéro ingestion risquée, zéro scraping ;
**Sourcé/Estimé sur chaque chiffre** ; non calculable = « non estimable », jamais inventé ; indice non calibrable =
livré MASQUÉ (flag) + finding ; personne morale (SIREN public) OK, particulier JAMAIS nommé ; lot cassé non réparable
en ~15 min → revert + finding + lot suivant ; l'arbre ne finit jamais rouge. Chaque lot note sa **reco d'exposition**.

---

## O0 · Score É V2 — le déblocage ✅

**Problème (note de sensibilité, clôture cycle 2).** Le Score É v1 prenait le prix de sortie sur la **médiane DVF de
l'EXISTANT** (~2 265 €/m², ancien + maisons diluées). Or un promoteur ne revend pas de l'ancien : il vend du **NEUF**.
Ce prix trop bas écrasait ~99 % des marges — **697 parcelles positives sur 58 282 estimables**, médiane −334 k€. Le
Score É était juste dans sa mécanique mais faux dans son entrée prix → livré **MASQUÉ**.

**Correctif.** Nouveau prix de sortie NEUF reconstruit par secteur.

### Table `dvf_prix_sortie_neuf` (additive, `src/labuse/ingestion/dvf_prix_neuf.py`)
- **Source (Sourcé DVF).** Ventes (`nature_mutation='Vente'`, histo + parcelle) d'un logement `Maison`/`Appartement`
  avec surface bâtie, réalisées **≤ 3 ans après l'achèvement d'un PC** sur la parcelle (`m10_permit_delais.date_achevement`).
  Proxy VEFA/livraison : les VEFA pures sont sans surface au 974, d'où le proxy achèvement. €/m² borné **[1 000 ; 12 000]**
  (anti-artefact, mêmes bornes que `bilan.py`).
- **Repli documenté (seuils).** Médiane €/m² au **niveau secteur** (préfixe IDU 10) si **n ≥ 5**, sinon **niveau commune**
  (INSEE 5) si **n ≥ 5**, sinon **absent → « non estimable »** côté score_e. Le niveau retenu est tracé (`niveau_prix`).
- **Couverture.** **45 secteurs + 17 communes** (n ≥ 5). Médiane du prix neuf reconstruit ≈ **3 688 €/m²** (vs 2 265 existant, **+63 %**).

### Score É recalculé (`score_e`, `HYP_VERSION = "bilan-neuf-v2"`)
Charge foncière supportable = bilan à rebours batch inchangé (`surf_habitable = SDP_rés / 1,15` ; `charge = surf_habitable
× prix_sortie_NEUF × 0,79 − SDP_rés × 2 550 €/m²` ; VRD = 0 prudent) — **seule l'entrée prix change** : prix de sortie neuf
(secteur → commune). Nouvelle colonne `niveau_prix` (secteur / commune) exposée en fiche pour la transparence du repli.

**Distribution avant / après** (77 718 parcelles non-écartées de `q_v7_defisc`, Estimé partout) :

| | estimables | **marges positives** | médiane marge | p90 marge |
|---|---|---|---|---|
| **v1 (existant)** | 58 282 | **697** | −334 k€ | — |
| **V2 (neuf)** | 51 926 | **3 788 (×5,4)** | −159 k€ | −18 k€ |

- Les positives passent de **697 → 3 788** ; la médiane des marges se relève de −334 k€ à −159 k€. La marge reste
  négative pour la majorité : c'est **honnête** — la plupart des parcelles ne sont pas des cibles de promotion aux
  hypothèses génériques ; le Score É trie celles qui le sont.
- **3 681 / 3 788 positives font ≤ 5 000 m²** (2 seulement > 5 ha). Le max (33,7 M€) est une vraie parcelle de 4,6 ha
  (SDP résiduelle 57 546 m²) : math cohérente (marge = montant absolu → grand foncier = grand nombre), **pas un artefact**.
- Estimables en baisse (58 282 → 51 926) : le neuf a une couverture plus stricte que l'existant ; **25 792 non estimables**
  (pas de prix neuf secteur ni commune). C'est le prix de l'honnêteté — pas de chiffre inventé.
- **Répartition du niveau prix** (estimables) : **secteur 7 208 · commune (repli) 44 718**. Le repli commune domine (86 %) :
  couverture secteur encore fine, à densifier quand la fenêtre des ventes neuves s'élargira.

### Reco d'exposition (décision Vic au STOP) — **LEVER le flag, avec garde-fous**
Le Score É V2 est **économiquement juste** : bilan à rebours d'un promoteur sur le prix de sortie neuf, qui est
exactement le raisonnement métier. Le blocage v1 (prix existant) est corrigé. Je recommande de **lever le flag de masquage**
sous trois conditions déjà tenues dans le livrable :
1. **Badge `Estimé` systématique** (jamais un prix ni une promesse) — présent (`libelle_court` + `detail`).
2. **Niveau du prix affiché** (`secteur` / `commune (repli)`) — l'utilisateur voit la granularité. Le repli commune
   (86 %) est plus grossier : c'est dit, pas caché.
3. **« non estimable » explicite** là où le prix neuf manque (25 792 parcelles) — pas de zéro trompeur.

Le Score É reste **un signal parmi d'autres**, cloisonné du score P servi (colonnes annexes `score_e.*`, zéro touche au
scoring / runs servis / golden). **Décision finale à Vic.**

### Livrable technique
- `src/labuse/ingestion/dvf_prix_neuf.py` — builder + table `dvf_prix_sortie_neuf`.
- `src/labuse/ingestion/score_e.py` — prix de sortie neuf (secteur→commune), `niveau_prix`, `HYP_VERSION` v2.
- `src/labuse/api/app.py` — `niveau_prix` exposé en fiche.
- `src/labuse/cli.py` — commandes `prix-neuf` et `score-e` (chaîne le prix neuf par défaut).
- `tests/test_score_e.py` — mis à V2 : **5/5 verts**.

**Findings O0.** (1) Couverture secteur du prix neuf encore fine (86 % de repli commune) → se densifiera avec le flux DVF ;
à re-builder périodiquement. (2) VEFA sans surface au 974 → proxy achèvement PC, borné, documenté ; **ne pas sur-vendre**
comme « prix VEFA réel ». (3) `q_v7_defisc` = run servi ; le Score É suit ce run, à re-builder après toute bascule de run.

---

## O1 · Dossier banquier ✅ (candidat démo)

**Le PDF qu'un porteur pose sur le bureau de son financeur.** 6-8 pages print sobres, **tout sourcé**, zéro donnée
nouvelle — assemble l'existant. Endpoint `GET /dossier-banquier/{idu}.pdf` (`src/labuse/api/banquier.py`), bouton
« Banquier » ajouté à la fiche (à côté de PDF / Dossier).

### Structure (7 pages sur la parcelle de test)
1. **Couverture** — identité + **photo aérienne IGN (BD ORTHO, Géoplateforme)** avec contour parcelle + **synthèse
   exécutive** + bandeau de KPI (terrain, surface vendable, charge foncière, marge Score É).
2. **Identité** — références cadastrales, adresse BAN, surface, **zonage** + règles calibrées (Estimé).
3. **Faisabilité** — les **11 steps déterministes** (`parcel_faisabilite`), chaque ligne Sourcé/Estimé + potentiel indicatif.
4. **Bilan promoteur & charge foncière** — postes du `compute_bilan`, fourchette de charge foncière, + **Score É V2**
   (marge = charge supportable − prix probable, prix de sortie neuf O0).
5. **Marché de comparaison** — comparables DVF (Q1/médiane/Q3, ancien vs neuf/VEFA) + **permis SITADEL voisins**.
6. **Risques, servitudes & ZAN** — couches dormantes + consommation ENAF de la commune (Cerema, Sourcé).

### Synthèse exécutive — narrée par le socle IA, **strict_numbers**
`core.complete(model=sonnet, validate=True, strict_numbers=True)` sur un contexte de **faits sourcés uniquement**
(parcelle, capacité, charge foncière, marché, marge, permis, vigilance). L'IA **narre les étapes, n'invente aucun
chiffre** ; la couche de validation rejette tout nombre absent des faits. **Repli déterministe honnête** si pas de clé
(crédits épuisés) : concaténation des faits, aucune invention. **Jamais de RR ni de score interne en vitrine.**

### Robustesse
- Chaque section est guardée (`to_regclass`, try/except) : une donnée absente devient « non estimable », jamais un
  chiffre fabriqué. Testé sur parcelle **sans** faisabilité/marge → PDF produit proprement.
- **Bug corrigé en cours de route** : la requête ZAN utilisait `code_insee` (colonne réelle = `insee`) → elle abortait
  la transaction Postgres et faisait échouer la synthèse IA en aval. Colonne corrigée ; TX propre vérifiée.

### Livrable technique
- `src/labuse/api/banquier.py` — module + endpoint.
- `src/labuse/api/app.py` — routeur branché.
- `frontend/src/components/fiche/Fiche.tsx` — bouton « Banquier ».
- `tests/test_banquier.py` — **7/7 verts** (puces Sourcé/Estimé, Score É rendu, non estimable sans chiffre, comparables
  ancien/VEFA, synthèse de repli sans invention, absence de RR/percentile en vitrine).

**Reco d'exposition.** **Visible** (candidat démo). C'est une vitrine, pas un indicateur calibré : aucun risque de
faux signal, tout est sourcé et labellisé. **Findings O1** : (1) synthèse IA en repli déterministe tant que les crédits
Anthropic sont épuisés — fonctionnel mais moins fluide ; (2) gating `dossier_parcelle` (Essentiel) — à confirmer si le
dossier banquier doit être un cran au-dessus (Intégral).
