# La Possession — re-fetch voirie ciblé (résultats) · 2026-06-20

> Deuxième re-fetch **réel** du correctif de pagination voirie (commit `4a0fb9c` / `5d704f4`,
> `docs/VOIRIE_CAP_5000_AUDIT.md` §10), après L'Étang-Salé. **Voirie SEULE de La Possession** — aucune
> autre couche (bâti, PLU/GPU, PPR, SAR, ravines, prescriptions…), aucune autre commune. Procédure :
> `docs/VOIRIE_REFETCH_RUNBOOK.md`.

- **Commune / INSEE** : La Possession / 97408
- **État** : `gold` (maintenu — voir conclusion)
- **Fenêtre** : run dédié `2026-06-20T22:01:04Z → 22:08:30Z` · **durée totale 446 s** (~7 min 26 s)
- **Code de sortie `evaluate`** : **0** · `/readyz` : **ready: true**

## 1. Backup pré re-fetch (point de rollback)

| | |
|---|---|
| Fichier | `/var/backups/labuse/labuse-labuse-20260620-220104.dump` |
| Taille | 503 Mo (`pg_dump -Fc`, 526,7 Mo annoncé) |
| SHA-256 | `60cb470762281ff6616d07d3076933014911ec0fe9c7fa3224ace0ffed7c4022` |
| Intégrité | `pg_restore --list` OK · `.sha256` généré |
| Restauration | `labuse restore-db --file /var/backups/labuse/labuse-labuse-20260620-220104.dump --yes` |

## 2. Voirie avant / après

| | tronçons en base |
|---|--:|
| **Avant** | **5 000** (plafonnée — limite serveur WFS) |
| **Après** | **11 825** ✅ |
| Δ | **+6 825** (`-5 000` purgées / `+11 825` ré-ingérées) |

La Possession était **fortement tronquée** : elle perdait **6 825 tronçons** (plus que le double de ce
qui était conservé). Le plafond 5 000 masquait donc **70 %** de sa voirie réelle.

## 3. Preuve de pagination réelle

`ingest_bdtopo` paginé → **3 requêtes WFS `GetFeature`** vers `data.geopf.fr/wfs`
(`BDTOPO_V3:troncon_de_route`, `sortBy=cleabs`, `count=5000`), bbox
`55.3201789,-21.0966005,55.4651123,-20.8967836` :

| Page | Requête | Entités | Statut |
|---|---|--:|---|
| 1 | `count=5000` (sans `startIndex`) | 5 000 (pleine) | HTTP 200 |
| 2 | `count=5000&startIndex=5000` | 5 000 (pleine) | HTTP 200 |
| 3 | `count=5000&startIndex=10000` | **1 825** (incomplète) | HTTP 200 |

- Log applicatif : `INFO labuse: ingest_bdtopo[voirie] : 11825 objet(s) en 3 page(s)`.
- **11 825 = 5 000 + 5 000 + 1 825** ; la page 3 (**1 825 < 5 000**) est **incomplète** → la boucle
  **s'arrête** (aucune requête `startIndex=15000`). **Fetch complet prouvé, pas de troncature résiduelle.**
- 3 requêtes WFS, **3× HTTP 200**, aucune erreur.

## 4. Verdicts avant / après (dernière éval par parcelle)

| Verdict | Avant | Après | Δ |
|---|--:|--:|--:|
| faux_positif_probable | 7 987 | 7 987 | 0 |
| **à creuser** | **4 141** | **3 950** | **−191** |
| écartée | 790 | 790 | 0 |
| **opportunité** | **420** | **611** | **+191** |
| **Total** | **13 338** | **13 338** | 0 |

- **Opportunités gagnées : +191** · **« à creuser » diminués : −191**.
- Décalage **strictement monotone** : exactement **191 parcelles** passent de « à creuser » →
  « opportunité » ; faux positifs et écartées **inchangés** ; **aucune parcelle dégradée**.

## 5. Cohérence métier (validation par proportionnalité)

Le gain n'est **pas une explosion** : il est **proportionné à la voirie récupérée**, comparé à L'Étang-Salé.

| Commune | Voirie récupérée | Opportunités gagnées |
|---|--:|--:|
| L'Étang-Salé | +1 986 (5 000 → 6 986) | +56 |
| La Possession | +6 825 (5 000 → 11 825) | +191 |
| **Ratio** | **×3,44** | **×3,41** |

La récupération d'opportunités **suit linéairement** la voirie récupérée (×3,44 ≈ ×3,41). La Possession
était bien plus tronquée → gain plus élevé, mais cohérent. **+191 reste sous la borne « accès seul » de
l'audit (1 081 ; soit ~18 %)**, comparable aux ~14 % de L'Étang-Salé. Pas d'anomalie.

## 6. Contrôles d'intégrité

| Contrôle | Attendu | Mesuré |
|---|---|---|
| `geom_2975` voirie manquante | 0 | **0** ✅ (`voirie_sans_geom2975 = 0`) |
| Doublons voirie | 0 | **0** ✅ (`voirie_doublons = 0`) |
| Index `idx_spatial_layers_voirie_geom2975` | présent | présent ✅ (reconstruit via `ensure_geom_2975`) |
| Total parcelles évaluées | 13 338 | **13 338** ✅ |
| Erreurs WFS | 0 | **0** ✅ (3× HTTP 200) |
| `evaluate` exit code | 0 | **0** ✅ |
| `/readyz` | ready | **ready: true** ✅ |

## 7. Critères de décision

- **Succès** (tous remplis) : voirie après > 5 000 (11 825) · 3 pages, dernière incomplète · « à creuser »
  baisse · opportunités +191 (proportionnées, pas d'explosion) · total = 13 338 · `geom_2975` 0 manquant ·
  0 doublon · evaluate 0 · 0 erreur WFS.
- **Rollback** : **aucun critère déclenché** (pas d'erreur WFS, pas d'échec cascade, pas de `geom_2975`
  manquant, pas de pagination suspecte, pas de doublon, pas de hausse de « à creuser », pas d'explosion).

## 8. Conclusion

✅ **SUCCÈS — `gold` maintenu — pas de rollback.**

Le correctif de pagination voirie est validé en réel sur **la 2ᵉ commune gold**, plus grande et **plus
tronquée** que L'Étang-Salé (voirie ×2,4 : 5 000 → 11 825). L'accès est désormais exact et **191
opportunités** auparavant masquées sont récupérées **sans dégrader aucun verdict**, de façon **proportionnée**
(validation croisée avec L'Étang-Salé). Le statut `gold` reste acquis (couches gold intactes, accès amélioré).
Le backup pré-run reste disponible pour rollback si besoin.

> **Périmètre du run** : base de travail locale (`localhost:5432/labuse`), **voirie de La Possession
> uniquement**. Aucune autre commune, aucune autre couche, **config gold non modifiée**, **aucun
> déploiement**. Reste à traiter (décision séparée) : **Saint-Paul** (dernière commune gold, la plus grande).
