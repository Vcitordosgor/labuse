# EXPORTS-AUDIT-2 — Les 4 documents après les chantiers

Branche `feat/exports-audit-2` depuis main `85ac26a5fe2ff296b33ce4a611217866de08a71f` (étape 0).
Session du 20/09/2026, backend dédié `:8075`, base locale `labuse` (431 663 parcelles), run servi
intact. **Lecture seule** — aucun code produit modifié, aucun merge, aucune bascule.

## L'en-tête — trois chiffres

- **930 chiffres sur 942 portent un id du registre** (Dossier + Financier + Apporteur × 5 témoins,
  crible de provenance Z5 `exports/provenance.py:inventaire`) ; les 12 restants sont des nombres de
  **structure documentés** (allowlist Z5 : version du modèle, seuils de loi cités, millésimes) ;
  **0 fuite**. ⚠ Le **Pré-dossier PC est HORS crible** : ses chiffres (CERFA, PCMI1/2/4/7-8) ne
  passent ni par le builder ni par le registre — voir liste 1.
- **0 divergence écran/PDF** sur 97410000AN0347 (120 nombres rattachés du Dossier confrontés à la
  fiche ; 2 candidats examinés = descripteurs de couverture de SOURCES, pas des données parcelle).
- **21 couches sur 53 ont un écho dans le Dossier** (le mandat disait « 51 » : le décompte exact sur
  cette branche est **53 couches déclarées** — 38 dans `declarations/couches/famille_*.yaml` + 15
  dans `couches_sans_toggle.yaml` ; clé `surface:`). 32 sans écho — voir liste 3.

## La méthode (preuve)

- 20 documents générés **par les vraies routes** sur `:8075` : `/dossier/{idu}.pdf?carte=false` ·
  `/financier/{idu}.pdf` · `/apporteur/{idu}.pdf` · `/pre-dossier/{idu}.zip`, 5 témoins
  (BO0852, AD0554, DY0106, AV0110 + 97410000AN0347). Tout dans `captures/exports-audit2/<idu>/`
  (PDF + `pdftotext -layout` + `fiche.json` + ZIP dézippé), **non committé** (22 Mo, artefacts).
- **Financier** : les 5 témoins rendaient **422 « document non établissable »** (aucun questionnaire
  saisi — comportement voulu RECETTE-5 V18b ; les manques : programme constructible, prix de sortie,
  régime de TVA). Pour générer les 5 PDF, un questionnaire minimal a été saisi par la route
  (`PUT /financier/{idu}/questionnaire` : 4 logements T3, 3 800 €/m², TVA assujetti) puis **les 5
  lignes ont été supprimées** après génération (base revenue à l'état initial). Les corps 422 sont
  gardés (`financier.422.json`).
- Inventaire de provenance : `captures/exports-audit2/inventaire_audit2.py` →
  `inventaire/<idu>-<doc>.json` (chaque nombre : contexte, `chiffre_id`, état) + `resume.json`.
  Nature par id (`exports/nature.py:nature_de`) et section par bloc (rendu fragment par fragment).
- Écran=PDF : `captures/exports-audit2/ecran_pdf_an0347.py`.
- `tsc -b` **vert** (front du worktree, node_modules lié).

## Rejeu de `scripts/recette_exports1.py`

**ÉCHEC 8 divergences — les 8 sont le même sujet : le Résumé.** (2 par témoin : `resume.pdf HTTP
404` + `document inconnu 'resume'`.) Le Résumé a été **supprimé volontairement en RECETTE-3 (T2,
décision Vic)** ; le script doré n'a pas suivi. Tout le reste est VERT : dossier/financier/
apporteur/flash rendus + archives JSON, surfaces cohérentes, prix ancien écran=PDF (3 811 · 2 308 ·
3 103 · 3 118 €/m²), 0 mot interdit, 0 ◌. **Geste : retirer le Résumé du script** (2 lignes) — non
fait ici (lecture seule).

## Par document — les chiffres et leurs ids

| Document | Nombres imprimés (5 témoins) | Rattachés à un id | Structure (allowlist) | FUITES |
|---|---|---|---|---|
| Dossier | 558 | 553 | 5 | **0** |
| Financier | 330 | 328 | 2 | **0** |
| Apporteur | 54 | 49 | 5 | **0** |
| **Total builder** | **942** | **930** | **12** | **0** |
| Pré-dossier PC | non criblable | — | — | hors circuit |

Détail par section et par témoin : `captures/exports-audit2/inventaire/*.json` (champ
`par_section`, un inventaire par bloc). Natures servies : les pastilles sourcé/estimé/dérivé/projet
sont dérivées du registre (`nature.py`), jamais écrites dans un gabarit — vérifié sur les 15
documents (chips présents, ex. §4 « sourcé », §8 « ƒ dérivé » sur le périmètre fiscal).

### Liste 1 — chiffres SANS id du registre (défauts)

Dans les 3 documents du builder : **aucun** (0 fuite sur 942).
Le défaut est **structurel et concentré sur le Pré-dossier PC** (`api/pre_dossier.py`, route ZIP) :

- il ne passe **ni par `builder.construire` ni par `collecte`** : `collect_report_data` (flash/data)
  + SQL directs (`_terrain_dims` ST_XMax/YMax `pre_dossier.py:465-481`, emprise
  `ST_Area(ST_Intersection)`, CERFA `:122-167`, points de vue `:736-777`) ;
- il est **invisible au crible Z5** (`tests/test_circuit_provenance.py` : documents testés =
  dossier, flash, apporteur — pas de pré-dossier) ;
- exceptions vertueuses : la zone vient de `zone_servie.zone_dominante` et les hauteurs de
  `faisabilite/zonage.resolve_zone` (donc du calibrage PLU, en vif) ; le taux de taxe vient de la
  fiche ;
- vestige : `regles-zonage.pdf` imprime `emprise_max_m2` **jamais renseigné** par `resolve_zone`
  (`pre_dossier.py:215`) — ligne morte.

### Liste 2 — divergences écran/PDF (AN0347) : **0**

120 nombres rattachés du Dossier, tous retrouvés dans la fiche (l'égalité est structurelle : la
collecte lit la fiche `/parcels/{idu}` elle-même). Les 2 seuls nombres non retrouvés sont des
descripteurs de couverture de source imprimés dans les traces « Sources : » (« archives DGFiP
2014-2020 », « 330 051 immeubles » Arcep) — pas des données de la parcelle. Seul collecteur qui lit
la base en direct (et pas la fiche) : `n_permis_proximite` (rayon 500 m / 24 mois) — même moteur
que l'écran, pas d'écart observé.

**Les 11 sections de la fiche ont-elles un écho dans le Dossier ?** Oui pour les 11, mais 3 échos
maigres :

| Fiche (11 sections, `Fiche.tsx:1229`) | Dossier (10 sections) | Écho |
|---|---|---|
| ① Identité | §1 Identité | ✓ (manquent : filiation DFI, permis DE la parcelle) |
| ② Terrain | §1 (pente) + §6 | **partiel** (exposition, artificialisation OCS GE, piscine absents) |
| ③ Bâti | §3 Potentiel | ✓ (manquent : DPE, RNB, toit) |
| ④ Urbanisme | §2 Zonage | ✓ (manquent : **SUP** — servi par la fiche `dispositifs.sup`, absent des IDS du bloc —, procédures PLU, RTAA) |
| ⑤ Risques | §4 Risques | **partiel** — voir liste 3 (le bloc ne lit que `aleas_parcelle_liste`) |
| ⑥ Réseaux | §6 Réseaux | ✓ (manquent : solaire, lignes HT/MT) |
| ⑦ Fiscalité | §8 Commune | **partiel** (TFPB absente du Dossier ; taxe d'aménagement dite « avant projet » ✓) |
| ⑧ Marché | §5 Marché | ✓ (manquent : VEFA/neuf, loyers, annonces) |
| ⑨ Quartier | §7 Autour | ✓ |
| ⑩ Potentiel | §3 Potentiel | ✓ |
| ⑪ Simulation | §9 Bilan (encart → Financier) | ✓ |

### Liste 3 — couches : 21 échos sur 53, 32 absentes du Dossier

Échos (le bloc lit un robinet qui porte la donnée de la couche) : zonage PLU, ER, EBC, DPU, PEB
(§2) · bâti 3D/BD TOPO (§3) · PPR, aléa inondation, aléa mouvement de terrain (§4) · axes,
lignes+arrêts transport, pôles d'échange, TCSP (§6) · équipements OSM, BPE (§7) · ZFANG, FRR,
ANRU/NPNRU, QPV, TVA primo (§8, `territoire_fiscal.perimetres` — observé : ANRU sur AN0347).

**Le fait central : la fiche sert 41 familles de verdicts dans `lines` (cascade) — le Dossier n'en
lit AUCUNE.** Le bloc §4 ne lit que `aleas_parcelle_liste` (PPR/Géorisques) ; l'Apporteur ne puise
dans `lines` que l'ICPE (RECETTE-11 D7). Toutes les mentions « friche/cavités/ABF… » des PDF sont
dans la **table des sources §10**, pas dans le corps. Un seul geste — brancher §4 (et §2 pour SUP)
sur `fiche.lines` — ferme l'essentiel du trou avec le moteur déjà servi à l'écran.

Les 32 absentes, avec avis « place dans un document client ? » :

| Couche | Avis client | Couche | Avis client |
|---|---|---|---|
| dpf (ravines) | **OUI** — recul opposable | sis (sols) | **OUI** — obligation d'information |
| casias | **OUI** — sols, diligence | endiguement | OUI — protection/risque résiduel |
| bruit_route | OUI — classement sonore | bruit_carte | OUI — dépassements |
| sup | **OUI** — servitudes opposables (§4 s'intitule déjà « servitudes ») | cinquante_pas | OUI — domanialité littorale |
| zone_humide | OUI — contrainte env. | enp | OUI — contrainte env. |
| znieff | OUI — signal env. | parc national | OUI — cœur = quasi-inconstructible |
| icpe | **OUI** (déjà dans l'Apporteur, pas le Dossier) | friche | OUI — opportunité/diligence |
| cavite | OUI — risque sol | trait_de_cote | OUI — érosion, littoral |
| tri_zone | OUI — inondation | abf | **OUI** — avis conforme, délais |
| sar | OUI — vocation Région (divergence signalée au registre) | zone_activite | moyen — contexte |
| safer/RPG | moyen — foncier agricole | artificialisation | moyen — contexte ZAN |
| ligne_ht | OUI — nuisance/servitude I4 | ligne_mt | moyen |
| vefa_neuf | **OUI** — le §5 n'a que l'ancien + terrain | telepherique | non — marginal |
| foret_publique | non — carto | bassin_versant | non — carto |
| cimetiere | non — carto | construction_lineaire | non — carto |
| construction_surfacique | non — carto | piscine | moyen — signal bâti (fiche ②) |

### Liste 4 — données du registre pertinentes client, absentes des 4 documents

(41 ids collectés par les blocs ; 139 données parcelle/commune/zone du registre hors documents —
les `bilan_*` et saisies `projet` sont, elles, bien servies via le contexte du Financier.)
Les absentes qui regardent un client :

- **`dpe_connu`** — le DPE du bâti (fiche ③) n'apparaît dans aucun document.
- **`historique_permis_liste`** — les permis DE la parcelle ; le Dossier ne montre que le rayon 500 m.
- **`sols_parcelle` / `sis_classe` / `casias_statut`** — l'état des sols (même trou que la liste 3).
- **`catnat_n` / `catnat_arretes_liste`** — les arrêtés CatNat de la commune (argument assurance).
- **`filiation_parcelle`** — l'historique cadastral (remembrements/divisions).
- **`tfpb_taux_pct` / `tfpnb_taux_pct`** — au Financier (ctx) mais pas au Dossier §8, où le taux
  foncier aiderait le portage.
- **`prix_neuf_vefa_acte_eur_m2` / `tranche_prix_vefa` / `loyer_median_eur_m2` / `vacance_pct`** —
  le §5 Marché ignore le neuf et le locatif.
- **`prod_spec_kwh_kwc` (+ toit : `nature_toit`, `pente_toit_deg`, `azimut_bati_deg`)** — le solaire.
- **`divisible_classe`**, **`destination_statut`** (« ouvrir une activité ? »),
  **`tcsp_stationnement_allege`** (L151-36, argument stationnement), **`rtaa_exigences`** (rappel
  conception DOM — sa place naturelle serait le Pré-dossier), **`endiguement_zone_protegee`**.
- **`assemblage_*`** — les voisines du même propriétaire sont dans l'Apporteur, pas dans le Dossier.
- `ventes_100m_n` / `voisinage_100m_liste` — hors PDF par arbitrage (M73-B) : à re-trancher, pas un
  défaut.

## Ce qui a bougé — les chaînes

- **Capacité ← zonage.py : OUI pour le code, NON pour la fraîcheur.** Chaîne :
  `capacite_logements`/`sdp_residuelle_m2` ← fiche `potentiel_transformation` ← table
  **`parcel_residuel`** (`app.py:5010-5016`, garde ZONE-1 `garde_sdp_residuelle`) ← builder
  résiduel ← `faisabilite/potentiel.py` ← **`faisabilite/zonage.py:resolve_zone`** (le module
  PLU-CALIBRAGE-4, source unique, plus aucun `config/plu_<slug>.yaml`). **Mais `parcel_residuel`
  date des 22-23/08/2026** (min/max `computed_at`), AVANT le calibrage PLU (septembre) : le Dossier
  §3 sert des SDP/capacités pré-calibrage, pendant que la **surélévation** (vive, `surelevation()`
  + LiDAR) et les **hauteurs du Pré-dossier** (`resolve_zone` en vif) sont, elles, déjà calibrées.
  → **Incohérence potentielle entre pièces d'un même envoi ; rebuild résiduel = geste Vic.**
- **Zonage ← zone_servie : OUI partout.** `zone_plu_famille`/`reglement_plu_bloc` ←
  `zone_servie.zone_dominante` (dominante par surface, ZONE-1) pour les 3 documents builder ET le
  Pré-dossier (`flash/data.py:_identite`). Aucun chemin centroïde restant.
- **Prix ← marche_service : OUI.** Point d'appel unique `marche_service.marche_dvf()` (profils
  nommés) ; les ids servis aux documents (`prix_sortie_bati_eur_m2`, `prix_terrain_secteur_eur_m2`)
  = moteur `sector_price`. Les profils voisinage 100 m et neuf/VEFA existent mais sont hors PDF
  (arbitrage).
- **Vestiges : propres.** `plu_rules` = **0 occurrence** dans src/. `parcel_residuel_bati` =
  **morte côté documents** (lecture supprimée EXPORTS-1 lot 3, `app.py:5005-5008`) ; survit hors
  périmètre comme filtre d'ingestion (ban_adresses, ortho_*, anc) et métadonnée scoring — aucun
  chemin depuis `builder.construire`. Seul vestige trouvé : `emprise_max_m2` du Pré-dossier
  (liste 1).

## Les gestes qui découlent (rien d'exécuté ici)

1. **Brancher le §4 du Dossier sur `fiche.lines`** (et le SUP au §2) — un robinet, 41 familles déjà
   servies à l'écran ; ferme l'essentiel des listes 3 et 4.
2. **Rebuild `parcel_residuel`** après calibrage PLU (geste Vic) — sinon le Dossier sert des
   capacités d'avant les règles calibrées, incohérentes avec le `regles-zonage.pdf` du même client.
3. **Mettre le Pré-dossier PC dans le circuit** : ses chiffres au registre + au crible Z5 (au
   minimum ajouter le document au test de provenance).
4. **Retirer le Résumé de `recette_exports1.py`** (8 « divergences » fantômes à chaque rejeu).
5. Candidats faciles au Dossier : DPE, permis de la parcelle, TFPB, VEFA/loyer au §5.

— Audit lecture seule, généré le 20/09/2026. PDF/textes/fiches : `captures/exports-audit2/`
(scripts `inventaire_audit2.py`, `ecran_pdf_an0347.py` au même endroit).
