# CHIRURGICAL-FIX-1 — LOT H (contre-audit documents, points 1 à 9)

**Branche** `fix/chirurgical-h` (créée depuis `origin/main`, qui contenait bien `ce502e3e6`).
**Base** `origin/main`. **Modèle** Opus 4.8. **Dépôt** `~/Desktop/labuse-chasse-ecrans` (worktree).
**Serveur de preuve** uvicorn `:7460` relancé depuis ce worktree (venv `~/Desktop/labuse/.venv`,
`PYTHONPATH=…/labuse-chasse-ecrans/src`) et vérifié frais à chaque étape (une preuve tirée d'un
serveur périmé ne compte pas). Documents régénérés dans `~/Desktop/chasse-1/_lotH-final/`.
**Point 10** (fiche : « PLU constructible » ne cohabite pas avec « habitat interdit ») : déjà traité
dans CHIRURGICAL-FIX-1, hors de ce lot.

Un commit par point. Gardes dans `tests/test_chirurgical_fix_h.py` (10 tests, verts). Les quatre
parcelles : **BW2635** `97422000BW2635`, **AM0838** `97404000AM0838`, **AD0887** `97422000AD0887`
(Le Tampon — celle à 3,9 m / 6,3 m), **IS0448** `97411000IS0448`.

---

## pt1 — Bilan : résultat gelé si un coût requis manque ; taxe sans assiette = « — » (`6c626015e`)
`bilan/excel.py`, `bilan/pdf.py`. Le classeur Excel affichait Résultat = CA et **100 % de marge**
avec des coûts vides (formules `=CA-coûts` sur des coûts à 0). Désormais, si
`Moteur().calculer(...).resultat_net is None`, Résultat net / Cash flow / marge sont **gelés**
(« non calculable — saisissez vos coûts »), comme le PDF ; sinon les formules sont conservées.
Au PDF, une ligne de taxe à assiette non renseignée affiche « — », plus « 0 € · Sourcé ».
Gardes : `test_excel_gele_resultat_si_cout_requis_manquant`,
`test_excel_garde_les_formules_quand_le_resultat_est_calculable`.

## pt2 — Apporteur : mêmes alertes que la fiche ; ICPE sans inférer la pollution (`0f337734f`)
`exports/robinet_fiche.py` (nouvel extracteur `contraintes_parcelle_liste`), `registre/donnees.py`,
`exports/blocs/apporteur.py`, `exports/builder.py`. L'Apporteur lisait une liste d'alertes plus
courte que la fiche (il omettait la zone humide 100 % d'AD0887, l'inondation extrême 85 % de BW2635).
Il lit maintenant **la même liste** que la fiche (toutes les lignes SOFT/HARD, hors marché VEFA,
scoring et bassin versant), sans doublonner les prescriptions (DPU/ER/EBC ajoutées seulement si la
liste complète manque). Pour une ICPE de voisinage, le texte dit « une installation classée (ICPE)
est signalée à proximité » et n'**infère** plus « ancien site industriel / sol pollué » sauf
inventaire sol pollué/CASIAS réellement servi (`pollution_inventaire`).
Gardes : `test_apporteur_liste_alertes_complete_et_filtree`,
`test_apporteur_contraintes_sans_doublon_depuis_la_liste_complete`.

## pt3 — Pré-dossier PCMI4 : PPR dit comme le Dossier (IS0448) (`24c13c005`)
`api/pre_dossier.py`. Le PCMI4 écrivait « pas d'exclusion automatique » / « aucune prescription PPR
opposable » sur l'aléa fort d'IS0448, alors que le Dossier/Gabarit excluent 34 % rouge + 66 % bleue.
Désormais : détection de la présence réelle en PPR (`_parcelle_en_ppr`), clause « aucune prescription
opposable » réservée au **hors de tout PPR**, et clause d'exclusion affichée via la **même** règle que
le Dossier (`ajuster_clause_affichage` quand la parcelle est non constructible). Nouvelle branche
« Aléa naturel (dans le périmètre PPR) → prescriptions du règlement PPR ».

## pt4 — Comparatif : bâti % = fiche ; propriétaire = Dossier (`b07bcbb34`)
`api/app.py` (`_compare_row`), `frontend/.../compare/ComparePanel.tsx`, `exports/blocs/comparatif.py`.
Le bâti % lisait le résiduel (259 m²) → 27 % sur IS0448 ; il lit désormais l'**emprise servie**
(`le_bien.emprise_batie_m2` = 128) → **13 %** (= 128/959 de la fiche). Sans personne morale, le
propriétaire est « **non déterminé** » (comme le Dossier), plus « particulier » par défaut.
Preuve `comparatif_pt4.json` : IS0448 `bati_existant_pct=13`, `proprietaire="non_determine"` ;
BW2635 `proprietaire="non_determine"`. Garde :
`test_compare_bati_pct_depuis_le_bien_et_proprio_non_determine` ; mise à jour de
`test_retours11f3.py::test_m13` (assertion de l'ancien « particulier » → « non_determine »).

## pt5 — Copropriété « à proximité » (proche_20m), jamais celle de la parcelle (`615c6a15a`)
`frontend/.../fiche/CoproprietesBlock.tsx`, `api/pdf_premium.py`, `exports/robinet_fiche.py` (`_c_copro`).
BW2635 (au **2** rue d'Allemagne) affichait les copropriétés des **4** et **6** rue d'Allemagne comme
les siennes. Le rattachement RNIC distingue cadastre/géocode (SUR la parcelle) de `proche_20m`
(voisine, ≤ 20 m). Fiche et PDF portent un libellé « à proximité » ; le Dossier (identité du bien) ne
compte « Bâti en copropriété » que pour une copro réellement sur la parcelle.
Preuve `BW2635_…_preuves.txt` : rattachements `['proche_20m','proche_20m']` →
Dossier « Copropriétés : **aucune copropriété immatriculée sur la parcelle** ».
Garde : `test_dossier_ne_dit_copropriete_que_si_sur_la_parcelle`.

## pt6 — Marge de surélévation nommée par la contrainte qui mord (`851424b63`)
`exports/miroir.py` (`libelle_marge_surelevation`), `registre/donnees.py`. **Deuxième source trouvée**
avant correction : le Dossier est un document **MIROIR** rendu par `miroir.rendu_sections`, qui prenait
le libellé **statique** du registre « Marge de surélévation (au faîtage) » — pendant que la valeur
servie (3,9 m) est la marge **à l'égout** (la contrainte qui mord ; 6,3 m au faîtage). Le bloc
Potentiel, lui, dérivait déjà la face de toit de `hauteur_contrainte`. Une seule source à la fin : la
face de toit vient de `hauteur_contrainte` (même signal que la fiche et le bloc Potentiel) ; le
registre ne fige plus « (au faîtage) ».
Preuve `AD0887_…_preuves.txt` : « **Marge de surélévation à l'égout · 3,9 m** ».
Garde : `test_marge_surelevation_nommee_par_la_contrainte_qui_mord`.

## pt7 — Estimer : aucun mot « constructible » sur une parcelle non constructible (`018e808d4`)
`pige/api.py` (`_parcelle_mesures`, `_contrainte_limitante`, `_classement_phrase`, `rapport_parcelle`).
AM0838 (habitat interdit en UE, `potentiel_a_batir.constructible=False`) qualifiait les 11 762 m² hors
zone rouge d'« **assiette constructible** ». Le mot suit désormais le verdict unique de la fiche :
ligne « **Surface hors aléa fort** » (fait mesuré), phrase de classement portant le motif
(« Rien à bâtir — Habitat interdit… »), plus de « règle qui limite la capacité » fabriquée. Une
parcelle constructible (AD0887) garde « Assiette constructible » et « marge constructible ».
Preuve `AM0838_estimer.json`. Garde :
`test_estimer_aucun_mot_constructible_sur_parcelle_non_constructible`.
**Fichier partagé** (Estimer / `pige/api.py`) — plus petit changement possible, à fusionner.

## pt8 — « Surface perméable » ≠ « pleine terre » (chaque règle garde son nom) (`a37819316`)
`faisabilite/zonage.py` (`pleine_terre_nature`, `_pleine_terre_nature`, `libelle_espaces_libres`),
`plu_reglement.py`, `api/traducteur.py`, `exports/etude_faisabilite.py`. Vérifié au règlement
(UE 2.6.7 §3, p.59) : « **Au moins 25 % de la surface de la parcelle doit être perméable.** » — la
pleine terre n'y est qu'une priorité qualitative (sans chiffre). LABUSE rangeait les 25 % dans
`pleine_terre_pct` et imprimait « Pleine terre min 25 % ». Le champ agrège en fait **4 règles
distinctes** (recensement des citations : 65 pleine terre, 187 perméable, 7 espaces verts, 40
biotope/autre). Le nom est désormais dérivé de la **citation sourcée** (source unique par zone).
Preuve `AM0838_…_preuves.txt` : « **Surface perméable min · 25 % · Art. UE 2.6** ». Les zones citant
« pleine terre »/« biotope » gardent leur nom. **195 tests pleine-terre rejoués verts.**
Garde : `test_espaces_libres_regle_garde_son_nom_permeable_vs_pleine_terre`.

## pt9 — Pas de « stationnement non réglementé » en zone habitat interdit (`69e82b373`)
`plu_reglement.py` (`_regles_valeurs`). AM0838 (UE, habitat interdit) affichait « Stationnement : non
réglementé » parce qu'aucune norme **par logement** n'est fixée. C'est faux : il n'y a pas de logement
(habitat interdit) et le règlement fixe des normes pour les **autres destinations**. Quand
`habitat == "interdit"` et la norme par logement est absente, la ligne devient « sans objet pour le
logement — habitat interdit dans la zone (voir le règlement pour les autres destinations) ». Les zones
à habitat autorisé sont inchangées (UA reste « à vérifier au règlement »). `engine.py:974/793` (verdict
« exemptée ») laissés intacts : non atteints en habitat interdit, justes pour une zone résidentielle
réellement exemptée. Preuve `AM0838_…_preuves.txt`. Garde :
`test_stationnement_pas_non_reglemente_en_zone_habitat_interdit`.

---

## Preuves régénérées pt1 / pt2 / pt3 (demande de contre-vérification)

Les points 1, 2 et 3 (les plus graves) manquaient de preuve tirée d'un document régénéré. Voici les
documents produits dans `~/Desktop/chasse-1/_lotH-final/` et les valeurs lues.

### pt1 — Bilan : résultat/marge/cash gelés ; taxe PDF sans assiette = « — »

**Excel recalculé RÉELLEMENT** (moteur de formules `formulas`, pas une lecture des valeurs en cache —
65 cellules recalculées par classeur). Scénario = CA du bien (surface vendable × prix de sortie DVF),
**coûts vides** — exactement le cas qui affichait un résultat = CA et 100 % de marge. Fichiers
`bilan_<parcelle>_coutsVides.xlsx` (corrigé) et `bilan_<parcelle>_coutsVides_BUG_avant.xlsx`
(l'ancien comportement reproduit en forçant l'ancien chemin à formules).

| Parcelle | CA (coûts vides) | AVANT (recalc des formules) | CORRIGÉ (recalc des formules) |
|----------|------------------|------------------------------|-------------------------------|
| BW2635 (×4 547 €/m²) | **251 449 €** | Résultat **251 449 €** · marge **100 %** (1,0) · cash **251 449 €** | Résultat **« non calculable — saisissez vos coûts »** · marge **vide** · cash **« non calculable… »** |
| AM0838 (×4 375 €/m²) | **241 938 €** | Résultat **241 938 €** · marge **100 %** · cash **241 938 €** | **« non calculable… »** · marge **vide** · **« non calculable… »** |
| AD0887 (×4 318 €/m²) | **238 785 €** | Résultat **238 785 €** · marge **100 %** · cash **238 785 €** | **« non calculable… »** · marge **vide** · **« non calculable… »** |

(Les 251 449 / 241 938 / 238 785 € correspondent aux 251 447 / 241 935 / 238 783 € cités, au centième
près de la surface vendable retenue.) Le `Moteur().calculer()` renvoie `resultat_net is None` sur ces
trois entrées → les cellules ne portent PLUS de formule `=D..-D..`, mais un texte ; un recalcul
LibreOffice/Excel afficherait donc exactement ce texte, aucun 251 449 caché.

**PDF — taxe sans assiette** (`bilan_pt1_PDF_taxe_sans_assiette.html`, taxe d'aménagement à 25 €/m²
sans surface taxable renseignée) :

> **Taxe d'aménagement** — Assiette : **—** · Taux ou montant : **25 €/m²** · HT : **—** · TVA : **—** · TTC : **—** · État : ratio

(Avant : « 0 € · Sourcé ».)

### pt2 — Apporteur : mêmes alertes que la fiche + ICPE « à proximité »

Documents `apporteur_<parcelle>_<idu>.html` (ligne « Ce qui gêne » / section ICPE).

- **AD0887 — zone humide** : « *Zone humide inventoriée (espace fonctionnel (2009)) : La Grande Ferme
  (**100 % de la parcelle**)* ». (Avant : omise.)
- **AM0838 — installation classée** : « *Une installation classée pour la protection de
  l'environnement (**ICPE**) est signalée **à proximité**. Installation (ICPE) à proximité — LOGISUD,
  régime Autres régimes, 10 m.* » — plus d'inférence « ancien site industriel / sol pollué ».
- **BW2635 — inondation** : « Ce qui gêne … · **Zone inondable TRI** · … ». Cette alerte n'apparaissait
  PAS avant pt2 (la couche `tri_zone` n'est pas dans `aleas_parcelle_liste`, qui ne lit que
  `layer='risques'`) ; elle vient de la nouvelle liste `contraintes_parcelle_liste`. La ligne « Ce qui
  gêne » affiche la NATURE de chaque alerte (libellé avant « — », règle RECETTE-11 D7) : la fiche porte
  le détail complet « *Zone inondable TRI — scénario extreme (85 % de la parcelle)* », et l'Apporteur en
  reprend la nature « Zone inondable TRI ». L'alerte d'inondation n'est donc plus omise.

### pt3 — Pré-dossier PCMI4 IS0448 : PPR dit comme le Dossier

`PCMI4_IS0448_apres.pdf` (+ `.txt`) :

> **Risque naturel (PPR)** — PPR **zone rouge sur 34 % de la surface** — vigilance forte. Les
> prescriptions du règlement PPR (niveau de plancher, …) …
> **Aléa naturel (dans le périmètre PPR)** — Aléa inondation — niveau fort. La parcelle étant en zone
> de PPR, **les prescriptions du règlement PPR s'appliquent** …
> **Risque naturel (PPR)** — **Zone bleue PPR** inondation et mouvement de terrain (~38 % / ~28 % de la
> parcelle) — **constructible SOUS PRESCRIPTIONS** (règlement DEAL) …

La phrase « **aucune prescription PPR opposable** » (et toute forme « aucune prescription… ») est
**absente** de la notice : 0 occurrence (vérifié sur le texte extrait du PDF). La notice dit désormais
la même chose que le Dossier/Gabarit (34 % rouge exclu, 66 % bleu sous prescriptions).

---

## À lister seulement (non corrigés, hors mandat de fix)
- Étude de zone : « revenu médian » vs « niveau de vie moyen » (vocabulaire INSEE).
- Estimer BW2635 : les ventes comparables apparaissent en double.

## Fichiers partagés avec `fix/chirurgical-docs` (déjà mergée) — pour la fusion
- **`pige/api.py`** (Estimer) — pt7 : plus petit changement possible (3 fonctions + 2 appels dans
  `rapport_parcelle`).
- **`exports/blocs/apporteur.py`**, **`exports/builder.py`** — pt2.
- **`exports/robinet_fiche.py`** — pt2 (`contraintes_parcelle_liste`) + pt5 (`_c_copro`).
- Les points Dossier passent par `miroir.py` / `plu_reglement.py` / `registre/donnees.py` /
  `faisabilite/zonage.py` / `traducteur.py` / `etude_faisabilite.py`.

## Recette
`tests/test_chirurgical_fix_h.py` — **10 tests verts**. Suite pleine-terre élargie (traducteur,
plu_calibrage4, etude_v6*, implantation, faisabilite…) : **195 passed** après le relabel pt8.
Hook pré-push complet rejoué vert **sans `--no-verify`**, branche poussée, **pas de merge**.
