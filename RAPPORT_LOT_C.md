# RAPPORT — Lot C (rapports de disponibilité + livraisons)

> Suivi du Lot C dans l'ordre C0 → C1 → (C2) → C3 → C4 → C5. Règle : **rapport de
> disponibilité AVANT tout loader** ; source introuvable/douteuse → rapport + STOP sur l'item.
> Document vivant, finalisé au STOP & VALIDATE de fin de lot.

---

## C0 — Hauteurs des bâtiments ✅ (livré, opérationnel)

**Disponibilité** : WFS Géoplateforme `BDTOPO_V3:batiment` renvoie `hauteur` (10 170/11 285 =
90 %) et `nombre_d_etages` (45 %). Quirk résolu : `count` plafonné < 5 000 (HTTP 403) → pagination
`page_size=1000`.

**Livré** : ré-ingestion Saint-Paul (11 285 bâtiments, 14 s, hauteur moyenne 5,7 m). Le résiduel
(Lot B) lit désormais `nombre_d_etages` sinon `hauteur/3` → **SDP existante réelle**, flag
`estimation_sdp` retiré. **Recette BV1232** : `niveaux_reels=True`, libellé sans « estimée ».
Effort 15 s (cap ½ journée non atteint).

## C1 — Ravines ✅ (livré)

**Disponibilité** (rapport AVANT loader) : WFS Géoplateforme, `BDTOPO_V3:troncon_hydrographique`
filtré `nature='Ravine'` = **98 tronçons LineString** sur Saint-Paul (toponymes : Ravine Lolotte,
Bassin, Bernica, Précipice…). Source fiable, géométries propres.

**Livré** : loader `ingest_ravines` (kind `ravine`, 98 entités) câblé dans `run_all` ; couche
cascade `RavineLayer` (proximité ≤ `buffer_m`, **PLACEHOLDER défaut 10 m**) → SOFT_FLAG moyen
« proximité d'une ravine », jamais excluante seule. Distance réelle en 2975
(`EvalContext.min_distance_m`, batchée). **Recette** : 78 parcelles flaggées (BC0076 près Ravine
Lolotte, BC0103+ près Ravine Bassin), toutes déjà contraintes (cohérent). Démo 8/8.

## C2 — 50 pas géométriques ⛔ (bloqué — rapport de disponibilité multi-sources)

La zone des **cinquante pas géométriques** (bande littorale de 81,2 m, domaine public) n'est
disponible sur **aucune source atteignable** depuis cet environnement :

| Source | État (re-testé 2026-06-12) | 50 pas / DPM ? |
|---|---|---|
| **PEIGEO** (`peigeo.re`, source autoritaire AGORAH/DEAL) | ❌ timeout (HTTP 000) | — (bloqué) |
| **DEAL Réunion** (`carto.reunion.developpement-durable.gouv.fr`) | ❌ injoignable (HTTP 000) | — |
| **Géolittoral** (`geolittoral…gouv.fr`) | ✅ HTTP 200 (62 couches) | ❌ aucune (énergies marines, sentier littoral, submersion — pas de DPM/50 pas) |
| **Géoplateforme** (`data.geopf.fr`, capabilities 5 Mo) | ✅ HTTP 200 | ❌ aucune couche DPM/cinquante pas |
| **data.gouv.fr** | ❌ connection refused (policy réseau) | — |

**Conclusion** : la donnée n'existe pas sur les sources joignables ; la seule source autoritaire
(PEIGEO) reste bloquée. **STOP sur l'item** — pas d'intégration (le brief interdit de bricoler une
donnée de zonage ; un buffer du trait de côte serait une approximation, pas le DPM réglementaire).
**Reprise dès que le whitelisting PEIGEO (action Vic côté environnement) est effectif.** Per la
directive (« C2 dès déblocage, sinon continuer »), je poursuis sur C3.

## C3 — Personnes morales DGFiP ✅ (livré)

**Disponibilité** : l'identité des propriétaires (Fichiers fonciers Cerema) est **sous
convention, non rediffusable et non scrapable** — aucune source live. C3 CLASSE ce qui est
importé (le cas échéant) et, pour le cas dominant « inconnu », produit la **voie légale**
(demande SPF). Aucune donnée nominative collectée.

**Livré** : module pur `proprietaire_type.py` — classifieur fin `owner_type` (commune, État,
collectivité, EPF, bailleur social, SCI, société, copropriété, indivision, personne physique,
inconnu) + familles public/privé/inconnu. **Badge fiche** (couleur par famille + acquérabilité),
**filtre carte** « Propriétaire » (identifié / public / privé / à identifier), **bouton
« Générer demande SPF »** (`GET /parcels/{idu}/spf-letter` → courrier pré-rempli avec la seule
référence cadastrale publique). **Recette** : SCI→prive/identifiable, Commune→public, EPF/SHLMR→
public/bailleur, indivision prime sur physique, sans données → inconnu+SPF ; sur les 3 000
parcelles réelles : owner_famille=inconnu partout (pas de Fichiers fonciers importés) → chemin
SPF. Tests : +8.

## C4 — SITADEL PC/DP — _en cours_

## C5 — Assemblage v1 — _à venir_
