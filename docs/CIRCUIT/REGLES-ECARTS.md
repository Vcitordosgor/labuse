# REGLES-ECARTS — CIRCUIT-4 (lot 2)

Les écarts entre la formule codée et le texte, constatés et DOCUMENTÉS — jamais corrigés en
autonomie (règle du mandat : lire un article reste un jugement humain). Chaque ligne : la formule,
le texte, l'écart, la proposition. **À trancher par Vic (avec Stéphanie pour le juridique).**
Exception : E1 relève de l'« arithmétique pure » (seuil large vs strict, référence claire) — le
lot 6 est mandaté pour la corriger, avant/après aux témoins + test.

## Écarts sur textes (décision humaine attendue)

| # | donnée(s) | formule codée | le texte | l'écart | proposition | impact |
|---|---|---|---|---|---|---|
| E1 | drapeau `sous_800m` (fiche `distance_arret_m`) | `proche = d <= 800` (api/app.py) | L151-36 (loi 2025-1129, vigueur 28/11/2025) : « situées à **moins de** huit cents mètres » | seuil comparé LARGEMENT au lieu de STRICTEMENT | `d < 800` — **CORRIGÉ au lot 6** (CORRECTIONS-ARITHMETIQUE.md A1, xfail levé) | d = 800 m exactement (distance entière) servait « sous 800 m » à tort ; aucun autre cas |
| E2 | `surface_plancher_m2`, `capacite_logements`, `surface_vendable_m2`, `sdp_residuelle_m2` | SDP = emprise_modélisée × 0,45 × niveaux (enveloppe gabaritaire) | R111-22 : SDP = Σ niveaux clos et couverts au nu intérieur **moins 8 déductions** (murs, trémies, h ≤ 1,80 m, stationnement, combles, locaux techniques, caves, 10 % habitation) | le moteur n'applique AUCUNE déduction : l'« estimation SDP » majore la SDP réglementaire | libeller « SDP estimée (enveloppe gabaritaire) » partout, OU poser un coefficient de passage documenté (p. ex. −10 à −15 %) validé par Stéphanie | tous les exports/fiches qui affichent une « surface de plancher » ; le bilan promoteur (coût = SDP × €/m²) hérite de la majoration |
| E3 | `permis_5a_n`, `permis_12m_n`, `n_permis_proximite`, `depots_secteur_n` | fenêtres sur `sitadel_permits.date` | SDES : deux dates existent (« date réelle » de l'événement vs « date de prise en compte ») | la base locale ne trace PAS laquelle des deux est ingérée | le dire au réservoir (technical_notes + fiche source) après vérification de l'ingestion Sitadel | lecture des courbes de permis (décalage possible de quelques mois) |
| E4 | `marge_surelevation_m` (et capacité) | une hauteur RETENUE par zone (YAML) | des règlements posent la hauteur PAR BANDE (ex. Saint-Paul U1a : hé 9 m sur 15 m depuis la voie, 12 m au-delà — Art. 10.2, p.20-21) | la bande n'est pas modélisée (une seule valeur, notée dans le YAML) | assumer (note affichée) ou modéliser la bande sur les zones où l'écart est fréquent | parcelles profondes des zones à bande : marge sur/sous-estimée localement |
| E5 | `taxe_amenagement_eur` (references YAML) | commentaires YAML : « valeur forfaitaire (art. 1635 quater I) » et « abattement 50 % (art. 1635 quater H) » | Légifrance : **H = valeurs forfaitaires** (892/1 011 €, vigueur 01/07/2026) ; **I = abattement 50 %** | les DEUX numéros d'articles sont INVERSÉS dans les commentaires (les valeurs, elles, sont exactes — vérifiées) | échanger les deux numéros dans les commentaires du YAML (correction documentaire, sans effet de calcul) | zéro effet chiffré ; crédibilité des références |
| E6 | (mandat CIRCUIT-4 lui-même) | — | le mandat cite « art. L331-10 s. » comme base de la taxe d'aménagement | le L331-* du code de l'urbanisme est ABROGÉ (ord. 2022-883) ; la base en vigueur est le CGI art. 1635 quater A à V — déjà celle du code LABUSE | corriger la référence dans les documents internes qui citeraient encore L331-* | zéro effet code (le YAML cite déjà le CGI) |
| E7 | (mandat CIRCUIT-4, étape 0) | — | le mandat attribue le « 0,5 pour le logement social » à l'art. L151-36 | le 0,5 (≤ 800 m) est porté par l'art. **L151-35** (logements des 1° à 3° de L151-34) ; L151-36 ne porte que le plafond d'UNE place | préciser L151-34 à 36 dans les libellés (le libellé TCSP de app.py cite déjà « art. L151-34 à 36 » — correct) | zéro effet code |

## Références des passe-plats réglementaires (vérifiées — pas de calcul, pas de fiche)

Ces données sont servies TELLES QUELLES (passe-plats du registre) ; leurs références ont été
relues au lot 2, le `domaine_source` du registre fait foi :

- **50 pas géométriques** (`cinquante_pas_couche`) — art. **L121-45** c. urb. (section outre-mer
  L121-38 à 51) : bande entre le rivage et la limite supérieure de la réserve domaniale ; à défaut
  de délimitation, **largeur de 81,20 m** depuis la limite haute du rivage. Conforme au libellé du
  registre (« la bande littorale des 50 pas (81,20 m) »).
- **ZFANG renforcée** (`dispositifs_couche`, `perimetres_dispositifs_liste`) — décret
  **n° 2026-421 du 29/05/2026** (lu au JORF) : abattement renforcé, art. 44 quaterdecies CGI, six
  communes listées à l'article 1 : « Bras-Panon, La Plaine-des-Palmistes, Saint-André,
  Saint-Benoît, Sainte-Rose et Salazie » ; critère : taux de pauvreté > 40 % (INSEE 2021). EXACTEMENT
  la liste servie par `territoire_fiscal.py` (seed CSV). Conforme.
- **DPE** (passe-plats `dpe_records`, passoires F-G du score V) — les seuils cités (arrêté du
  31/03/2021) sont ceux de la **France métropolitaine** ; l'applicabilité du DPE 3CL aux DOM et le
  calendrier « DPE outre-mer » restent À CONFIRMER (pages consultées sans extrait daté opposable
  au 974). Les étiquettes servies sont celles du fichier ADEME (passe-plat) — on n'en recalcule
  aucune. **Question posée à Vic/Stéphanie** : afficher une mention « étiquette ADEME, référentiel
  métropole » sur le 974 ?
- **PPR** (`ppr` couches, domaines de classes) — les niveaux d'aléa servis sont ceux des règlements
  DEAL (documents par commune/aléa) ; le registre porte le domaine par `domaine_source`. Pas de
  recalcul LABUSE.

## Introuvables (ce qui a été tenté)

- `autres_loges_pct` / statuts d'occupation INSEE RP : définition « statut d'occupation » non
  citée avec extrait daté (recherches insee.fr métadonnées — c1051 renvoie une autre définition) ;
  verdict reste `reference_introuvable`, la formule (complément à 100) est arithmétique.
- `zan_reste_ha` : la méthode Cerema (portail artificialisation, ENAF 2021-2024) n'a pas été citée
  avec extrait daté — verdict `reference_introuvable`, conversion m²→ha triviale vérifiée.
- Loi « littoral » hors 50 pas (bande des 100 m, coupures d'urbanisation) : périmètres servis en
  couches ; articles non re-cités faute de fiche de calcul dédiée.
