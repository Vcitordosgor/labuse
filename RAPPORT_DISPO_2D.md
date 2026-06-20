# RAPPORT DE DISPONIBILITÉ — 2.D Zone des 50 pas géométriques

> §7 / brief 2.D. Re-sonde multi-sources le 2026-06-14 (data.gouv désormais joignable — ce qui a
> débloqué 1.A — donc re-test de tout ce qui échouait au Lot C2).

## La donnée recherchée
**Zone des cinquante pas géométriques** : bande de 81,20 m comptée depuis la limite haute du
rivage dans les DOM, relevant du **domaine public maritime** (donc inconstructible). Délimitée
administrativement (avec régularisations/exclusions) — **ce n'est PAS un simple buffer du trait
de côte**.

## Sondage multi-sources (Réunion / INSEE 97415)
| Source | État (2026-06-14) | 50 pas Réunion ? |
|---|---|---|
| **PEIGEO** (`peigeo.re/geoserver`) — source autoritaire AGORAH/DEAL | ❌ timeout (HTTP 000) | — (bloqué) |
| **data.gouv.fr** (désormais joignable) | ✅ HTTP 200 | ❌ « pas géométriques » → **uniquement Mayotte** ; « DPM réunion » → 0 ; rien pour 974 |
| **Géolittoral** (`geolittoral…gouv.fr`) | ✅ joignable | ❌ aucune couche DPM/50 pas (énergies marines, sentier littoral, submersion) |
| **Géoplateforme** (`data.geopf.fr`, capabilities 5 Mo) | ✅ HTTP 200 | ❌ seulement `limite_terre_mer` (trait de côte ≠ 50 pas) |
| **DEAL Réunion** (`carto.reunion…gouv.fr`) | ❌ injoignable (HTTP 000) | — |

## Conclusion : ⛔ STOP sur l'item
La zone des 50 pas géométriques de **La Réunion** n'est disponible en SIG sur **aucune source
joignable** ; la seule source autoritaire (PEIGEO) reste **bloquée**.

Conformément au brief : **introuvable partout → rapport + STOP, sans bricoler**. Je n'approxime
PAS la zone par un buffer du trait de côte (la délimitation réelle inclut régularisations et
exclusions — un buffer serait une donnée fabriquée, interdite §0.4 / 2.D).

**Reprise dès que le whitelisting PEIGEO (action Vic, en cours) est effectif** : le loader sera
trivial (couche surfacique → `HARD_EXCLUDE` « domaine public maritime — 50 pas géométriques »).
Per la directive (« sinon continuer »), je poursuis sur 2.E.
