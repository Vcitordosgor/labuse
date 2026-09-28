# PLU-EXCEPTIONS-1 — les 147 exceptions se voient

**Branche** `audit/plu-verif-1` (suite de PLU-VERIF-1) · worktree `~/Desktop/labuse-pluverif` · API 8665 / front 5865.
« Hauteur 9 m » est juste, mais si le règlement ajoute « sauf en bande de 3 m depuis la limite, où
la hauteur est limitée à 6 m », le promoteur qui lit la fiche se trompe. La règle reste la règle ;
l'exception se lit à côté. Ce mandat rend **lisibles** les 147 exceptions repérées par PLU-VERIF-1
(verdict « JUSTE + exception »), **sans changer aucun calcul**.

## Étape 0
- 147 feuilles JUSTE+exception (bloc `regles` de `config/plu_destinations/*.yaml`), sur **16 communes**.
- Chacune porte déjà son **article** et sa **page** (0 manquant).
- Extraction VERBATIM du texte de l'exception depuis le PDF servi (16 sous-lecteurs, un par commune) :
  **151 exceptions** (quelques feuilles en portent 2), **0 sans verbatim**.

## Lot A — l'exception est une donnée servie
- Chaque feuille `regles` porte désormais un bloc **`exceptions:`** (liste) : `texte` (verbatim du
  règlement, jamais reformulé), `article`, `page_pdf`, `porte`, `modifie_calcul`.
- Servie AVEC sa règle par le moteur de zonage (`faisabilite/zonage.py` → `ZoneRules.exceptions`,
  puis `plu_reglement._regles_valeurs`), **même id que la règle** : `<cle>.exception`
  (`hauteur.exception`, `emprise.exception`, `recul_voirie.exception`…). Jamais recomposée ailleurs.
- Dédoublonnage faîtage/égout : une clause portée par deux feuilles n'est servie qu'une fois.
- Une règle sans exception ne sert **rien** (pas de champ vide).

`porte` (à quoi l'exception s'applique) : sous_secteur 30 · exclusion_generique 52 ·
majoration_conditionnelle 17 · voie_specifique 15 · destination 14 · bande_limite 12 ·
hauteur_alternative 6 · autre 5.

## Lot B — où ça se voit (5 surfaces, aucune autre)
1. **Fiche §Urbanisme** — la tuile de la règle porte un **point d'exception** (`*` ambre) + un
   « i » ; le « i » ouvre le **texte verbatim** avec article + page (`PluExceptionTip`). Une règle
   sans exception garde son rendu actuel.
2. **Fiche §Potentiel** — quand une exception **pourrait changer le calcul** (`modifie_calcul`),
   une ligne ambre « **Exception au règlement — à vérifier** » sous la capacité, renvoyant à
   §Urbanisme. Jamais appliquée au calcul.
3. **Dossier / Flash / Pré-dossier** — l'exception suit par le **miroir registre**
   (`flash/data.collect_report_data → regles.exceptions`), rendue **sous la règle, en note** (verbatim
   + article/page) dans le pré-dossier PC et le rapport Flash. (Le dossier banquier ne rend pas les
   règles de volumétrie → rien à y ajouter.)
4. **Copilote (chemin FICHE)** — contexte `reglement_exceptions` + consigne système : quand il cite
   une règle chiffrée qui a une exception, il **cite l'exception** (source `⟨src:reglement_exceptions⟩`).
5. **Outil PLU** — recherche cadrée sur une zone (ouverte depuis la fiche/Copilote) : les exceptions
   calibrées de la zone s'affichent **sous l'article** (`exceptions_zone`).

## Lot C — garde-fous
- Texte affiché = **celui du règlement**, entre guillemets, jamais une reformulation (les 151 textes
  sont des verbatim extraits du PDF).
- **Aucune exception n'entre dans un calcul** : résiduel, gabarit, faisabilité inchangés. Test
  `test_plu_exceptions_1.py::test_exception_nentre_dans_aucun_calcul` : la valeur servie par
  `resolve_zone` reste celle des `regles`.
- **Les 147 sont servies** : `test_147_feuilles_portent_une_exception` compte les feuilles porteuses
  et échoue à tout écart ≠ 147.
- Banc `--echantillon` rejoué : **0 écart nouveau** (les exceptions sont additives, aucun nombre
  servi ne change). V6b **vert** (9/9). `tsc` **0**, `vitest` **225 vert**, `build` **0**.

## Les exceptions « qui devraient modifier un calcul » — laissées pour calibrage
**81 exceptions** (`modifie_calcul=true`) changeraient l'enveloppe chiffrée d'une parcelle ordinaire
(bande depuis une limite, sous-secteur à valeur différente, majoration/minoration conditionnelle,
recul RN/RD). Elles sont **affichées** (« à vérifier ») mais **pas appliquées** — liste complète
dans `PLU-EXCEPTIONS-1/A_CALIBRER.csv`, pour un futur PLU-CALIBRAGE. Répartition : sous_secteur 30 ·
majoration_conditionnelle 17 · voie_specifique 12 · bande_limite 12 · autre 5 · destination 4 ·
hauteur_alternative 1. Les 66 autres (surtout `exclusion_generique` : ouvrages techniques, extensions
de bâti non conforme, éléments protégés, équipements d'intérêt collectif) ne touchent pas la capacité
de base.

## Par commune (151 exceptions · 81 à calibrer)

| INSEE | Commune | Exceptions | dont « à calibrer » |
|---|---|---:|---:|
| 97401 | Les Avirons | 16 | 0 |
| 97402 | Bras-Panon | 10 | 7 |
| 97405 | Petite-Île | 20 | 2 |
| 97406 | La Plaine-des-Palmistes | 18 | 8 |
| 97407 | Le Port | 3 | 3 |
| 97408 | La Possession | 10 | 10 |
| 97411 | Saint-Denis | 7 | 7 |
| 97412 | Saint-Joseph | 14 | 14 |
| 97413 | Saint-Leu | 1 | 1 |
| 97414 | Saint-Louis | 3 | 3 |
| 97415 | Saint-Paul | 3 | 3 |
| 97416 | Saint-Pierre | 31 | 11 |
| 97421 | Salazie | 1 | 1 |
| 97422 | Le Tampon | 9 | 9 |
| 97423 | Les Trois-Bassins | 2 | 2 |
| 97424 | Cilaos | 3 | 0 |
| | **TOTAL** | **151** | **81** |

## Témoins (captures dans `PLU-EXCEPTIONS-1/captures/`)
- **Le Tampon Ua** `97422000BE2255` (avec exception) — hauteur (bande limite, Ua 10.3, p.18) +
  recul voie (RD3, Ua 6.2, p.15) ; §Potentiel affiche « à vérifier ».
- **Saint-Pierre Uazi** `97416000CS1429` (avec exception) — hauteur ZI N°4 (bande, p.177) ;
  §Potentiel « à vérifier ».
- **Saint-André** `97409000AB0876` (sans exception) — témoin négatif : aucune tuile marquée, aucune
  ligne « à vérifier ».

## Livrables
- `config/plu_destinations/*.yaml` — bloc `exceptions:` sur 147 feuilles (1 commit / commune).
- `src/labuse/faisabilite/zonage.py`, `plu_reglement.py`, `api/{app,fiche_ask,pre_dossier,modules}.py`,
  `flash/{data.py,templates/rapport.html.j2}` — serving.
- `frontend/…` — §Urbanisme (`formes.tsx`, `blocks.tsx`, `PluExceptionTip.tsx`), §Potentiel
  (`constructibilite.tsx`), Outil PLU (`PluAnnuaire.tsx`), types.
- `tests/test_plu_exceptions_1.py` — garde-fous (147, verbatim, servi, 0 calcul).
- `PLU-EXCEPTIONS-1/{verbatim/,verbatim_agrege.json,A_CALIBRER.csv,captures/}`.
