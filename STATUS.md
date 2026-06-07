# État d'avancement — LA BUSE

Suit l'ordre de construction du brief §12. Mis à jour au fil des commits.

## Légende statut connecteur
`connecte` (branché auto) · `partiel` (import / couverture incomplète) ·
`mock` (fixture) · `manuel` (champ saisi) · `a_faire` (à connecter plus tard)

## Contrainte d'environnement constatée
Le réseau sortant est **restreint à une allowlist** : les API géo publiques
(API Carto IGN, Géorisques, Géoplateforme, Overpass…) sont **injoignables**
depuis cet environnement. Conséquence : les connecteurs externes sont écrits
**d'après les formats documentés `[✓ vérifié]` du brief**, testés contre des
**fixtures**, et marqués honnêtement (`a_faire`/`mock`) tant qu'un appel réel
n'a pas confirmé le format. La règle « tester avant de coder un connecteur `[~]` »
ne peut donc pas être honorée en ligne ici — à refaire dès qu'un accès réseau
est disponible (voir `connectors/*.test_connection()`).

## Ordre de construction (§12)

| # | Étape | État |
|---|-------|------|
| 1 | PostGIS + modèle de données + gestion EPSG (4326/2975) + **test de surface** | ✅ fait, testé sur PostGIS réel |
| 2 | Ingestion cadastre (API Carto PCI) → `parcels` | 🔶 parser + connecteur écrits ; appel live bloqué (allowlist) → démo synthétique |
| 3 | Moteur de cascade (couches ordonnées, verdicts, motifs, config) | ✅ fait |
| 4 | Couches géométriques cœur (eau, Parc, forêts, SAR, GPU, SAFER, Géorisques/PPR ; pente affichée non excluante) | ✅ fait (sur `spatial_layers`) |
| 5 | Page Sources de données + statut connecteurs + test | ✅ API + catalogue ; bouton test = endpoint `/sources/{id}/test` |
| 6 | Fiche parcelle + double score (opportunité TOUJOURS avec complétude) | ✅ fait |
| 7 | Enrichissement async (DVF rayon, SITADEL appariement, Overpass, BAN) + cache | 🔶 DVF/SITADEL ingérés + cascade phase 2 ; connecteurs externes structurés |
| 8 | Analyse IA LA BUSE (anti-hallucination, JSON borné validé) | ✅ prompt + schéma + validateur + provider `stub` (déterministe) ; provider Anthropic prêt à brancher (clé + réseau) |
| 9 | Vue Découverte (cascade sur toute la commune → survivantes classées, offre B) | ✅ fait (CLI `discover` + API `/discover`) |
| 10 | Export fiche premium | ✅ Markdown/HTML via API `/parcels/{idu}/export` |

**Livré en plus** : CLI `labuse` (init-db/seed/evaluate/discover/sources/test-source/api),
API FastAPI (sources, fiche §8, découverte, évaluation, feedback, export), 30 tests verts.

## Suite (post-cœur, §12)
Veille/signaux (offre C) · feedback réinjecté dans le scoring · BD TOPO, BPE,
SIRENE, OCS GE, ABF, ENS, VRD/SPANC réels · Fichiers fonciers sous convention
(propriétaire + indivision) · multi-communes · RAG règlements PLU PDF ·
front carto/dashboard.
