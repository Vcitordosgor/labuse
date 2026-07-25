# M18 — Enrichissement du PDF Flash (À VALIDER par Vic avant de figer)

**Branche** `feat/m18-d-pdf-flash-enrichi` (base `main` M18 merged). **Committée localement, NON poussée** —
en attente de la validation du contenu par Vic (comme demandé : « montre-le-moi avant de figer »).

Nouvelle **section 07 « Contexte commune & leviers »** (indicateurs à l'échelle commune ; Terrain →
08, Sources → 09). Exemple généré : `qa/m18/B/flash_enrichi_sample.pdf` (parcelle 97416000CD0024,
Saint-Pierre) — section p.3, millésimes p.5.

## Garde-fous tenus
- **Zéro identité de personne physique** : que des agrégats commune ; vérifié (aucun nom, aucun `M./Mme/né le`).
- **Chaque donnée sourcée + exacte** ; la donnée douteuse a été **exclue** (voir ZAN).

## Ce qui est AJOUTÉ (sourcé, exact)
| Bloc | Valeur (exemple Saint-Pierre) | Source | Provenance affichée |
|---|---|---|---|
| **Vélocité admin PC** | délai médian **8 mois** (fourchette 6–11, **4 897 dossiers**) | Sitadel/SDES (`m10_permit_delais`) | **Sourcé** + caveats (dossiers accordés uniquement, cohortes mûres, historique 2013+) |
| **Leviers SRU / bailleur** | commune **déficitaire** — 22,85 % LLS / objectif 25 % · besoin **~763** LLS | Inventaire SRU DHUP (`commune_contexte_sru`) | **Sourcé** (millésime 2024-2025) ; le besoin = **Estimé** (dérivé taux/objectif), étiqueté |
| **QPV / TVA réduite** | présence QPV → TVA 2,1 %, TFPB −30 % | ANCT génération 2024 (`spatial_layers` qpv) | **Sourcé** ; dispositif fiscal « à instruire au cas par cas » |
| **Consommation d'espace (ENAF)** | rythme **201 609 m²/an** (2021-2024) vs **291 024 m²/an** (2011-2021) | Cerema ENAF (`commune_conso_enaf`) | **Sourcé** (2009-2024, publié 05/2025) ; chip « accélération » si le rythme récent dépasse l'ancien |

**Seuil de fiabilité** : la vélocité ne s'affiche que si **≥ 8 dossiers** mûrs (sinon médiane non
significative → omise). Chaque bloc/section absent(e) est omis(e) proprement (parcelle/commune sans donnée).

## Ce qui est VOLONTAIREMENT EXCLU (garde-fou « pas de champ faux »)
- **Budget & horizon ZAN (années restantes)** : la −50 % « loi TRACE » est une **hypothèse**, le SAR de
  La Réunion **n'a pas territorialisé** l'enveloppe → un « horizon 2031/2034 » ou un « budget restant »
  afficherait une valeur **potentiellement fausse**. **Non ajouté.** À la place : uniquement le **rythme
  observé** (sourcé) + la mention « enveloppe non encore territorialisée — à confirmer PLUi ». **Signalé
  ici pour ton arbitrage** : si tu veux l'horizon estimé malgré tout, dis-le et je l'ajoute clairement
  étiqueté « Estimé ».
- **PLH des 5 EPCI** : table vide en base (data-gap connu) → rien à afficher.

## À VALIDER
1. Le **contenu** des 4 blocs (valeurs, formulations, caveats).
2. L'**exclusion** du budget/horizon ZAN (garder observé seul, ou ajouter l'horizon estimé étiqueté ?).
3. Toute autre donnée que tu voudrais (solaire PVGIS, marché RP2023… — dis-moi, j'évalue la fiabilité avant d'ajouter).

Rien n'est poussé ni figé tant que tu n'as pas validé. Golden non impacté (aucune touche scoring) —
je le lance au moment du figeage.
