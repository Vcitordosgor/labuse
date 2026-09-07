# EXPORTS — sources par document (liste définitive, 05/09/2026)

Croisement du sommaire cible et du rapport d'audit, arbitrages de Vic appliqués (les 12 recommandations).

**Statut** : ✅ prêt — servi par un moteur vivant, à brancher au gabarit · 🔧 après correctif — moteur à unifier ou libellé à réparer (mandat correctifs) · 🆕 nouvelle ingestion — effort S sauf mention · ❌ retiré — mirage ou source morte.

**Documents** : D = Dossier (= Flash sans le financier) · P = PDF (résumé sans financier) · F = Financier · A = Apporteur · PC = Pré-dossier PC.

---

## 1 · Identité et situation

| Donnée | Source | Statut | D | P | F | A | PC |
|---|---|---|---|---|---|---|---|
| IDU, commune, section, numéro, contenance | Cadastre Etalab | ✅ | ● | ● | ● | ● | ● |
| Adresse | BAN (rattachement auto, mention à garder) | ✅ | ● | ● | ● | ● | ● |
| Orthophoto + contour + nord + échelle | BD ORTHO IGN | ✅ | ● | ● | ● | ● | ● |
| Forme, largeur, allongement | géométrie | ✅ | ● | – | – | – | ● |
| Pente | RGE ALTI 5 m | ✅ | ● | ◐ | – | – | ● |
| Propriétaire personne morale (SIREN, forme, dénomination) | fichier PM DGFiP + SIRENE | 🔧 une carte unique (3 sources aujourd'hui) | ● | – | ◐ | ◐ type seul | – |
| Historique de propriété 2019 → 2025 | panel DGFiP PM, diff déjà codé | ✅ (PM seulement, 21 % des parcelles) | ● | – | – | – | – |
| Procédures collectives | BODACC par SIREN | 🔧 seulement si SIREN connu | ● | – | ◐ | – | – |
| Parcelles contiguës, même propriétaire ou non | `assemblage.py` | ✅ | ● | – | – | ● | – |
| DPE du bâti | ADEME | ❌ 17 lignes en base | | | | | |
| BDNB | — | ❌ absente au 974 | | | | | |

## 2 · Zonage et règles

| Donnée | Source | Statut | D | P | F | A | PC |
|---|---|---|---|---|---|---|---|
| Zone(s), part, document, classe | GPU — **dominante par surface + drapeau « à cheval »** (Q5) | 🔧 une seule résolution | ● | ● | ◐ | ◐ | ● |
| Fraîcheur du zonage (approbation, GPU vs mairie) | GPU + veille | ✅ à extraire d'`app.py` | ● | ◐ | – | – | ● |
| Règles calibrées : emprise, égout, faîtage, reculs (séparatifs / voirie distingués), pleine terre par zone | YAML calibrés | 🔧 libellés (deux reculs, pleine terre = valeur de zone) | ● | ◐ | ◐ | – | ● |
| Articles du règlement cités | `plu_reglement_extrait` (21/24 communes) | ✅ réutilisable | ● | – | – | – | ● |
| **Destinations autorisées + verrou CDAC** | `plu/destinations.py`, 24/24 | ✅ testé sur les 4 témoins | ● | ◐ | – | – | ● |
| Prescriptions : mixité sociale (secteur / seuil / déclenchement en 2 lignes, Q A5), pluvial | GPU + bilan | 🔧 bloc unique | ● | ◐ | ● | – | ● |
| **Emplacements réservés, EBC** | GPU prescriptions — déjà en base (2 250 + 1 782 objets) | ✅ à imprimer explicitement | ● | ● | ◐ | ◐ | ● |
| **Drapeau « prescriptions non vérifiables »** — Saint-André, Saint-Leu, Saint-Philippe, Petite-Île | règle (Q12) | 🔧 | ● | ● | ● | ● | ● |
| **Droit de préemption urbain** | GPU info-surf typeinf 04 | 🆕 | ● | ◐ | ◐ | ◐ | ● |
| Servitudes SUP (PM1…) avec signification | GPU SUP | 🔧 traduire les codes | ● | – | – | – | ● |
| Servitudes aéronautiques T5 | GPU (assiettes pas encore servies) | 🆕 effort M, re-sonder | ◐ | – | – | – | ◐ |
| Captages AS1 | — | ❌ introuvable en open data | | | | | |
| Lien vers le règlement | GPU | ✅ | ● | ● | – | – | ● |

## 3 · Potentiel constructible

| Donnée | Source | Statut | D | P | F | A | PC |
|---|---|---|---|---|---|---|---|
| Bâti existant : emprise, hauteur, nombre | BD TOPO + CoSIA (emprise révélée 74 %) | ✅ | ● | ● | ● | ● | ● |
| Canopée / végétation | CoSIA 2025 (98,7 %) | ✅ | ● | – | – | – | – |
| SDP consommée / résiduelle | `parcel_residuel` (run servi) ; **0 par règle en N/A** (Q6) | 🔧 | ● | ● | ● | – | – |
| Surélévation | moteur commun, **égout** | 🔧 supprimer la lecture faîtage | ● | ◐ | ◐ | – | – |
| Table rase : emprise, niveaux, SDP, vendable, logements (fourchette finale seule) | `estimate_capacity` | 🔧 ne plus imprimer l'étape intermédiaire « 8 à 10 » | ● | ◐ | ● | – | – |
| Table orpheline `parcel_residuel_bati` (127 m²) | — | ❌ supprimée (Q4) | | | | | |
| Réhabilitation, terrain nu au prix du secteur | `compute_mode_b` | ✅ | ● | ◐ | ● | – | – |

## 4 · Risques, patrimoine

| Donnée | Source | Statut | D | P | F | A | PC |
|---|---|---|---|---|---|---|---|
| PPR, aléas | DEAL, Géorisques | ✅ | ● | ● | ◐ | – | ● |
| Classement sonore | Cerema | ✅ | ● | ● | ◐ | – | ● |
| ICPE : tableau avec régime ; **alerte seulement si classée** (Q9) | Géorisques | 🔧 | ● | ◐ | ◐ | – | ● |
| Abords MH avec nom du monument | Mérimée | 🔧 nommer | ● | ◐ | – | – | ● |
| **PEB aéroportuaire** (Roland-Garros, Pierrefonds) | Géoplateforme DGAC | 🆕 éliminatoire pour le logement | ● | ● | ● | – | ● |
| Aléa sismique | constante zone 2 faible | 🆕 une ligne | ● | – | – | – | ● |
| **Arrêtés CatNat** | GASPAR | 🆕 réparer la troncature (10/commune) | ● | ◐ | – | – | – |
| QPV, espaces protégés, friches, cavités, sols pollués, érosion, 50 pas… | existants | ✅ en une ligne « aucun signal sur… » | ● | ◐ | – | – | ◐ |
| Volcanique, argiles | — | ❌ clos (aucun zonage / non pertinent) | | | | | |

## 5 · Marché et prix

| Donnée | Source | Statut | D | P | F | A | PC |
|---|---|---|---|---|---|---|---|
| **Prix du secteur** : ancien appartement / maison / terrain, avec n et rayon effectif | `sector_price` parcelle via `marche_service` (Q1) | 🔧 point d'appel unique | ● | ● | ● | – | – |
| Médiane par secteur cadastral | `dvf_secteur_medianes` | 🔧 ligne secondaire étiquetée ; « — » = « sous seuil », jamais un vide | ● | – | ◐ | – | – |
| Prix commune « centroïde » (n 11) | — | ❌ supprimé (Q2) | | | | | |
| **Neuf** : neuf observé (≤ 3 ans post-achèvement) | `resolve_prix_neuf_marche` (Q3) | 🔧 seul « neuf » du bilan ; VEFA à l'acte retiré ou étiqueté | ● | ◐ | ● | – | – |
| Comparables anonymisés, **un filtre**, étiquette `immeuble` (Q8) | DVF via `marche_service` | 🔧 | ● | ◐ | ● | – | – |
| Nuage des ventes retenues + écartées | `sector_price` | ✅ à généraliser | ● | – | ● | – | – |
| Tendance et liquidité commune (n récent / n précédent expliqué) | `ligne4_tendance` | 🔧 libellé | ● | ◐ | ● | – | – |
| Borne réelle des ventes (« ventes jusqu'au … ») | `max(date_mutation)` | 🔧 remplacer « DVF 2026 » | ● | ● | ● | – | – |
| Offre engagée, permis voisins **500 m · 24 mois** (Q7), profils réellement appliqués | Sitadel via `marche_service` | 🔧 | ● | ◐ | ● | – | ◐ |
| Couverture SITADEL (83 %) sur chaque compteur | déjà calculée, jamais imprimée | 🔧 | ● | ◐ | ● | – | – |
| Délai médian d'instruction | `m10_permit_delais` | ✅ | ● | ◐ | ● | – | ● |
| **Loyers de marché** | Carte des loyers DHUP 2025, 24/24 | 🆕 | ● | ◐ | ● | – | – |
| Radar (annonces) | pige | ❌ comme statistique ; liste factuelle seulement si rattachée | ◐ | – | – | ◐ | – |
| Programmes de promoteurs | — | ❌ 9 lignes, non rattachables | | | | | |

## 6 · Réseaux, desserte, zone, commune

| Donnée | Source | Statut | D | P | F | A | PC |
|---|---|---|---|---|---|---|---|
| Viabilisation (faisceau), accès voirie **par distance seulement** (A6) | `viabilisation_build` | 🔧 supprimer la couche cascade `acces` | ● | ● | ◐ | ◐ | ● |
| Gestionnaires de réseaux | `resolve_gestionnaires` | ✅ | ● | – | – | – | ● |
| Assainissement | GPU | ✅ | ● | ● | – | – | ● |
| Transports, axes, HT (avec seuils) | GTFS, BD TOPO | 🔧 seuils + extraire d'`app.py` | ● | ◐ | – | – | ◐ |
| Solaire | PVGIS | ✅ | ● | – | – | – | – |
| Étude de zone, contexte (piéton) et chalandise (paramétrée) | deux endpoints existants | ✅ | ● | ◐ | – | – | – |
| Équipements par catégorie, sans nom de professionnel | BPE, OSM | 🔧 | ● | ◐ | – | – | – |
| SRU, parc social (sans % QPV), ZAN, structure du parc | DHUP, RPLS, Cerema, INSEE | ✅ | ● | ◐ | ◐ | – | – |
| **Zonage A/B/C du logement** | arrêté 23/06/2026, 24 lignes | 🆕 | ● | ◐ | ● | – | – |
| Dispositifs fiscaux | CGI + dérivé | ✅ à extraire d'`app.py` | ● | – | ● | – | – |
| Taxe d'aménagement | outil TA + **taux communaux** (publics — à sonder en source avant de faire saisir) | 🆕 sonde + 🔧 | ◐ | – | ● | – | ● |
| Contacts mairie | — | ❌ table vide | | | | | |
| Millésimes de sources | `data_sources` + sentinelle + sondes (26/31 récupérables) | 🔧 composer, masquer les 5 orphelines | ● | ● | ● | – | ● |

## 7 · Financier — hypothèses

| Donnée | Source | Statut | F |
|---|---|---|---|
| Prix demandé, marge, prix de sortie retenu, scénario | **formulaire client** | 🆕 écran app | ● |
| Coût de construction — fourchette **sourcée** par défaut | EPTB 2024 + dataset CDC (2 304 → 2 842 €/m²) | 🆕 remplace le 2 300-2 800 non sourcé | ● |
| Coût de démolition | saisie, défaut « non chiffré » (Q11) | 🆕 | ● |
| VRD et viabilisation | aujourd'hui 90 €/m² non sourcé → saisie avec défaut, modulé par le faisceau de viabilisation | 🔧 | ● |
| Verdict, écart au marché, sensibilité au coût | calcul | 🔧 à imprimer | ● |

---

## Ce que ça retire définitivement des PDF

MOBPRO et Radar des pieds de section · clé de run · `ST_Buffer / EPSG` · `deja_bati` · `zone reglt Forte` · les renvois vers l'app · le nom de la professionnelle de santé · la ligne « prix commune n 11 » · les 127 m² · la surélévation au faîtage · « Non ICPE » en alerte · « pas d'accès à la voirie » · le % QPV · les « 0 » de couverture · l'étape « 8 à 10 » · la synthèse IA du banquier.

---

## Exports existants hors des cinq documents — à trancher

L'audit en révèle trois, chacun sur sa propre chaîne. Recommandation : aucun ne survit comme builder séparé.

| Export | Route / chaîne | Recommandation |
|---|---|---|
| Lettre de vérification de zonage | `/lettre-zonage` (jamais reçue) | Devient un **extrait d'une page du §2 du Dossier** (zonage complet, destinations, ER/EBC, DPU, drapeau « non vérifiable ») — même builder, même moteur. |
| Étude de zone PDF | `api/pdf_zone.py`, FPDF | Devient le **§6 du Dossier** ; l'outil garde un bouton qui exporte ce seul bloc. Sa chaîne FPDF disparaît (elle cite MOBPRO en dur). |
| Projet PDF | `api/pdf_projet.py`, FPDF | À trancher par Vic : absorbé par le Financier (c'est le même contenu une fois le formulaire rempli), ou supprimé. |
