# OUTILS-P1-1 — dix outils, des résultats qu'on ne peut plus mal lire

Branche `fix/outils-p1-1` (base `origin/main`). Aucun merge, aucune prod. Dev local
ports **10010** (vite) / **7210** (API). Captures WebKit avant/après par point dans ce dossier.

Source : revue d'Astra du livret des outils. Rien d'autre que ces dix points.

> Contrainte respectée : la session OUTILS-P0-1 possède `ModulePanel.tsx` (Prospection solaire,
> fichier `ProspectionSolaire.tsx`) et `blocB.tsx`. Je n'ai touché `ModulePanel.tsx` que pour MES
> points qui y vivent (Permis M03, Scan patrimoine M02, Courrier M09) et jamais le module solaire ;
> `blocB.tsx` n'a pas été modifié du tout.

---

## 1. Successions
- **Âges ≥ 100 ans hors liste, comptés.** Backend `_calcul_successions` : exclusion `coalesce(dir.age,
  v.dirigeant_age) >= 100` + `n_age_ecarte` servi. Île : **6 151** listées, **105 écartées** (max âge
  en liste = 99). Bandeau : « 105 parcelles écartées : âge du dirigeant ≥ 100 ans (donnée amont à vérifier) ».
- **Nom ET âge du même millésime, dans la même requête.** `LEFT JOIN LATERAL` sur `pm_dirigeants`
  (ingestion courante) renvoie le couple nom + âge DÉRIVÉ de la date de naissance — fini la divergence
  entre un nom « au présent » et un âge figé au Score V.
- **Libellé factuel, sans pronostic.** « Nom · N ans » quand nommé, sinon « Dirigeant de N ans » (plus
  de « dirigeant · » orphelin). Le pronostic (« succession probable ») reste dans l'avertissement d'en-tête.
- **Date de la donnée affichée.** « donnée RNE au 05/07/2026 » au bandeau et à l'état vide (ré-ajoutée).
- Fichiers : `src/labuse/api/modules.py`, `frontend/src/components/outils/Successions.tsx`, `frontend/src/lib/api.ts`.

## 2. Assemblage
- **Trois lectures** (tuile SDP, pleine largeur) : « Existant · 436 m² » / « Si conservé · aucun ajout
  estimé » / « Après démolition · 337 m² estimés · −99 m² par rapport à l'existant ». (parcelle témoin
  97411000AB0669+AB0670, même histoire que l'exemple 571/372/−199.)
- **Écart signé**, et **absent avec sa raison** si l'existant n'est pas mesuré (« écart non calculé (existant non mesuré) »).
- **Ligne par parcelle** : « bâti conservé non estimé » quand la SDP résiduelle manque, au lieu d'y
  recopier la valeur de reconstruction — la reconstruction n'est plus présentée SOUS « bâti conservé ».
- Fichiers : `frontend/src/components/outils/moteurs.tsx` (M16), test vitest `Assemblage.test.tsx` mis à jour.
  Champs backend déjà servis (`sdp_existante_totale_m2`, `sdp_bati_conserve_m2`, `sdp_terrain_libere_m2`).

## 3. Comparer
- **« PLU sans plafond d'emprise » seulement si une règle est identifiée, sinon « Règle non renseignée »**
  — à l'écran ET dans le PDF. Backend `compare()` sert `emprise_ces_etat` (`plafond` / `sans_plafond`
  = silence prouvé du règlement, sentinelle « pas de règle dans le PLU » / `non_renseigne`).
- **Statistique de secteur préfixée « Secteur : »** (Assainissement) — écran + PDF.
- **Prix du terrain filtré au calcul sous le seuil de 8 ventes** (`SEUIL_N`, `_compare_row`) : médiane
  fondée sur < 8 ventes → non servie (le nombre de ventes reste, pour dire « échantillon insuffisant »).
- Fichiers : `src/labuse/api/app.py` (`compare`, `_compare_row`), `src/labuse/exports/blocs/comparatif.py`,
  `frontend/src/components/compare/ComparePanel.tsx`, `frontend/src/lib/api.ts`.

## 4. Blocs fonciers
- **« estimé sur 5 des 9 parcelles (somme par parcelle) »** à côté de la valeur (sinon « estimé sur les N
  parcelles (somme par parcelle) » en couverture complète).
- **État vide : « blocs publics »** (plus « propriétaires publics »).
- **Millésime de propriété affiché** : « propriété (DGFiP) 2025 » au bandeau et à l'état vide.
- Fichiers : `frontend/src/components/outils/Blocs.tsx` (backend `millesime`/`sdp_couverture` déjà servis).

## 5. Permis
- **Période écrite dans le libellé** : « Autorisés » + « depuis 90 jours » (« Récent » renommé).
- **Compteur = liste, test à l'appui** : le compteur de l'état ACTIF lit le total de la liste ; test DB
  `test_p1_1_compteur_et_liste_portent_sur_le_meme_ensemble` (count_only.total == liste.total ET géolocalisés,
  à l'état défaut comme sous filtre).
- **« Dormant » → « Ancien permis sans achèvement déclaré »** (libellé, définition, infobulle, carte).
- **« N dossiers · M géolocalisés » + date de la dernière donnée** : « 760 dossiers · 715 géolocalisés ·
  donnée Sitadel au 2026-08-31 ».
- Fichiers : `frontend/src/components/outils/ModulePanel.tsx` (M03), tests `test_retours16/17_permis.py`,
  `PermisDouble.test.tsx` mis à jour.

## 6. Fiche commune
- **Horizon ZAN plus mis en avant** : le sous-titre de « Foncier et rareté » dit le compte factuel de
  parcelles (« 38 295 parcelles »), plus « ZAN 1,1 an ».
- **Passe dans le détail « Scénario au rythme observé »** avec hypothèse et années (« Projection, pas une
  échéance réglementaire : au rythme observé de X ha/an, le budget ZAN restant serait consommé en 1,1 an »).
- **« Échantillon insuffisant · N vente(s) »** quand un prix de terrain (par zone) est masqué.
- Fichiers : `frontend/src/components/contexte/ContextePanel.tsx`.

## 7. Scan patrimoine
- **Trois comptes sur des ensembles distincts** : « Recensées (DGFiP) » / « Rattachées au cadastre » /
  « Visibles selon les filtres ». SIREN témoin 310863592 : **4 241** recensées, **4 188** rattachées.
- **Écart ventilé** : « 4 241 recensées (fichiers fonciers DGFiP), dont 4 188 rattachées au cadastre —
  53 sans géométrie cadastrale (hors carte). » (le JOIN cadastre les écartait en silence.)
- **« bâti non renseigné » distinct de « nu »** : tuile « 0 / 3 366 / 822 — nus / bâtis / bâti non renseigné »
  (les 822 à `p_model_bati` absent étaient comptés « nus » par le `COALESCE(…,0)`).
- Fichiers : `src/labuse/api/modules.py` (`patrimoine`), `frontend/src/components/outils/ModulePanel.tsx` (M02).

## 8. Taxe d'aménagement
- **Champ « Surface taxable (différente de la surface de plancher) » + exemple garage** : « Ex. : une
  maison de 100 m² + un garage de 20 m² = 120 m² de surface taxable. »
- **Chaque taux montre source, date d'effet, dernière vérification** :
  - communal : « Source : délibération communale (fichiers DGFiP) · effet le 01/01/2022 · vérifié le 28/08/2026 » ;
  - départemental : « Source : Conseil départemental 974 (délibération — plafond légal 2,5 %) · barème 2026 · vérifié le 28/08/2026 ».
- **« à confirmer » à côté de « Total à prévoir » quand le taux départemental est simulé au plafond**
  (`!part_departementale_confirmee`). À La Réunion le départemental 2,5 % est **confirmé** par DELTA
  (`part_departementale_confirmee_974: true`) → le badge ne s'affiche PAS (état honnête) ; le câblage
  est en place et s'activera pour tout taux simulé non confirmé.
- Fichiers : `frontend/src/components/outils/TaxeAmenagement.tsx` (champs backend déjà servis).

## 9. PLU
- **Édition + état d'indexation du document au-dessus de la recherche** : « 97411_reglement_20260805.pdf ·
  édition 05/08/2026 · 97411_PLU_20260805 · Indexé pour la recherche : 241 extraits d'articles. »
- **Recherche vide sur document partiel** : « Aucun extrait trouvé dans les documents indexés » + note
  (« le règlement complet peut contenir d'autres passages ») + lien **« Ouvrir le règlement ↗ »**.
- Fichiers : `frontend/src/components/outils/PluAnnuaire.tsx`.

## 10. Courrier
- **L'écran dit ce qui se passe vraiment** : bouton **« Déposer une demande d'envoi »** → confirmation
  **« Demande reçue — C-1211-OC. État : À déposer. »** → l'état réel servi par le back (cycle
  `demande → depose → envoye` = « À déposer → Déposé → Envoyé »).
- **« Posté » seulement après un dépôt effectif** : une demande fraîche reste « À déposer » ; la note dit
  que l'état passe à « Déposé » puis « Envoyé » seulement une fois le pli effectivement posté.
- Fichiers : `frontend/src/components/outils/ModulePanel.tsx` (M09), test `CourrierService.test.tsx` mis à jour.

### ⚠ Écart coût / prix signalé (sans changer le prix)
- **Coût configuré : 2,69 €** (`courrier_cout_lettre_eur` dans `config.py` — « lettre verte 3 pages Merci
  Facteur, grille 2026 »).
- **Prix client : 2,50 €** (`courrier_prix_client_eur` ; servi par `/courrier/statut`, `tarif_unitaire_eur = 2,50`).
- **Le prix client (2,50 €) est INFÉRIEUR au coût prestataire (2,69 €) de 0,19 € par courrier** : chaque
  lettre est vendue à perte d'environ 0,19 €. Conformément au mandat, **le prix n'a pas été changé** —
  c'est un arbitrage commercial (Vic) à trancher, pas un bug de calcul.

---

## Vérification
- Hook : secrets ✓ · tsc 0 ✓ · vitest **326** ✓ · pytest unitaires **3273 passed / 49 skipped** ✓ · cohérence (12 témoins) ✓.
- Tests DB touchés : `test_retours16/17_permis` (11 passed, dont la preuve compteur=liste), compare/assemblage/
  patrimoine/blocs/successions (ré-exécutés verts).
- Captures WebKit (1440×900) : `0X-<outil>-avant.png` / `0X-<outil>-apres.png`. Pour les points en
  `ModulePanel.tsx` partagé (5 Permis avant/après OK ; 7 Scan et 10 Courrier : après capturé, avant
  documenté par le diff git — reverter le fichier entier aurait écrasé les autres points du même fichier).
