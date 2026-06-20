# L'Étang-Salé — re-fetch voirie ciblé (résultats) · 2026-06-20

> Premier re-fetch **réel** du correctif de pagination voirie (commit `4a0fb9c` / `5d704f4`,
> `docs/VOIRIE_CAP_5000_AUDIT.md` §10), sur la plus petite commune **gold**. **Voirie SEULE de
> L'Étang-Salé** — aucune autre couche (bâti, PLU/GPU, PPR, SAR, ravines, prescriptions…), aucune
> autre commune. Procédure : `docs/VOIRIE_REFETCH_RUNBOOK.md`.

- **Commune / INSEE** : L'Étang-Salé / 97404
- **État** : `gold` (maintenu — voir conclusion)
- **Fenêtre** : run dédié `2026-06-20T21:43:58Z → 21:49:02Z` · **durée totale 304 s** (~5 min 04 s)
- **Code de sortie `evaluate`** : **0** · `/readyz` : **ready: true**

## 1. Backup pré re-fetch (point de rollback)

| | |
|---|---|
| Fichier | `/var/backups/labuse/labuse-labuse-20260620-214358.dump` |
| Taille | 502 Mo (`pg_dump -Fc`, 526,1 Mo non compressé annoncé) |
| SHA-256 | `e855d4a2d48c12423ba4cdeda33eca8ec902b1df1b395bdcb43b299b769a2c7a` |
| Intégrité | `pg_restore --list` OK · `.sha256` généré |
| Restauration | `labuse restore-db --file /var/backups/labuse/labuse-labuse-20260620-214358.dump --yes` |

## 2. Voirie avant / après

| | tronçons en base |
|---|--:|
| **Avant** | **5 000** (plafonnée — limite serveur WFS) |
| **Après** | **6 986** ✅ |
| Δ | **+1 986** (`-5 000` purgées / `+6 986` ré-ingérées) |

## 3. Preuve de pagination réelle

`ingest_bdtopo` paginé → **2 requêtes WFS `GetFeature`** réellement émises vers
`data.geopf.fr/wfs` (`BDTOPO_V3:troncon_de_route`, `sortBy=cleabs`, `count=5000`), bbox
`55.3223621,-21.2924232,55.392935,-21.1768627` :

| Page | Requête | Entités | Statut |
|---|---|--:|---|
| 1 | `count=5000` (sans `startIndex`) | 5 000 (pleine) | HTTP 200 |
| 2 | `count=5000&startIndex=5000` | **1 986** (incomplète) | HTTP 200 |

- Log applicatif : `INFO labuse: ingest_bdtopo[voirie] : 6986 objet(s) en 2 page(s)`.
- **6 986 = 5 000 + 1 986** ; la page 2 (**1 986 < 5 000**) est **incomplète** → la boucle **s'arrête**
  (aucune requête `startIndex=10000`). **Fetch complet prouvé, pas de troncature résiduelle.**
- Si la commune avait réellement ≤ 5 000 tronçons, on aurait vu « en 2 page(s) » avec une page 2 vide ;
  ici la page 2 est non vide et < 5 000 → le plafond 5 000 d'avant **masquait bien 1 986 tronçons**.

## 4. Verdicts avant / après (dernière éval par parcelle)

| Verdict | Avant | Après | Δ |
|---|--:|--:|--:|
| faux_positif_probable | 5 606 | 5 606 | 0 |
| **à creuser** | **2 696** | **2 640** | **−56** |
| écartée | 482 | 482 | 0 |
| **opportunité** | **286** | **342** | **+56** |
| **Total** | **9 070** | **9 070** | 0 |

- **Opportunités gagnées : +56** · **« à creuser » diminués : −56**.
- Décalage **strictement monotone** : exactement **56 parcelles** passent de « à creuser » → « opportunité » ;
  faux positifs et écartées **inchangés** ; **aucune parcelle dégradée**. Ce sont des parcelles dont
  l'accès était faussement « non identifié » faute de tronçon voirie proche : la voirie complète amène
  désormais une route à ≤ 6 m (`ACCES_MAX_M`).
- **+56 est raisonnable** (pas d'explosion), bien en deçà de la borne haute « accès seul » de l'audit
  (~401) — la plupart des parcelles à > 6 m d'un axe le sont **légitimement**, même voirie complète.

## 5. Contrôles d'intégrité

| Contrôle | Attendu | Mesuré |
|---|---|---|
| `geom_2975` voirie manquante | 0 | **0** ✅ (`voirie_sans_geom2975 = 0`) |
| Doublons voirie | 0 | **0** ✅ (`voirie_total = 6 986 / geom_distinctes = 6 986`) |
| Index `idx_spatial_layers_voirie_geom2975` | présent | présent ✅ (reconstruit via `ensure_geom_2975`) |
| Total parcelles évaluées | 9 070 | **9 070** ✅ |
| Erreurs WFS | 0 | **0** ✅ (2× HTTP 200) |
| `evaluate` exit code | 0 | **0** ✅ |
| `/readyz` | ready | **ready: true** ✅ |

## 6. Critères de décision

- **Succès** (tous remplis) : voirie après > 5 000 · 2 pages, dernière incomplète · « à creuser » baisse ·
  opportunités +56 (raisonnable) · total = 9 070 · `geom_2975` 0 manquant · 0 doublon · evaluate 0 · 0 erreur WFS.
- **Rollback** : **aucun critère déclenché** (pas d'erreur WFS, pas d'échec cascade, pas de `geom_2975`
  manquant, pas de pagination suspecte, pas de doublon, pas de hausse de « à creuser », pas d'explosion
  d'opportunités).

## 7. Conclusion

✅ **SUCCÈS — `gold` maintenu — pas de rollback.**

Le correctif de pagination voirie est **validé en réel** sur L'Étang-Salé : le plafond 5 000 est levé
(6 986 tronçons), l'accès est désormais exact, et **56 opportunités** auparavant masquées sont récupérées
**sans dégrader aucun verdict**. Le statut `gold` reste acquis (couches gold intactes, on n'a fait
qu'**améliorer** l'exactitude de l'accès). Le backup pré-run reste disponible pour rollback si besoin.

> **Périmètre du run** : base de travail locale (`localhost:5432/labuse`), **voirie de L'Étang-Salé
> uniquement**. Aucune autre commune, aucune autre couche, **config gold non modifiée**, **aucun
> déploiement**. Prochaine étape (décision séparée) : même protocole sur **La Possession** puis **Saint-Paul**.
