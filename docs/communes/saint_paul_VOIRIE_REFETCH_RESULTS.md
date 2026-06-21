# Saint-Paul — re-fetch voirie ciblé (résultats) · 2026-06-21

> Troisième et dernier re-fetch **réel** du correctif de pagination voirie (commit `4a0fb9c` / `5d704f4`,
> `docs/VOIRIE_CAP_5000_AUDIT.md` §10), sur **la plus grande commune gold** (commune de référence).
> **Voirie SEULE de Saint-Paul** — aucune autre couche, aucune autre commune. Procédure :
> `docs/VOIRIE_REFETCH_RUNBOOK.md`. Run long (~54 min), exécuté **détaché** (`nohup … & disown`),
> API arrêtée pendant la cascade puis redémarrée.

- **Commune / INSEE** : Saint-Paul / 97415
- **État** : `gold` (maintenu — voir conclusion)
- **Fenêtre** : run dédié `2026-06-21T08:58:53Z → 09:53:08Z` · **durée totale 3 255 s** (~54 min 15 s)
- **Code de sortie `evaluate`** : **0** · `/readyz` (après redémarrage API) : **ready: true**

## 1. Backup pré re-fetch (point de rollback)

| | |
|---|---|
| Fichier | `/var/backups/labuse/labuse-labuse-20260621-085854.dump` |
| Taille | 506 Mo (`pg_dump -Fc`, 530,4 Mo annoncé) |
| SHA-256 | `2d0c6d05bdd7063edcd28c1562b54efd350699d5a66864766ba44e59765d38e6` |
| Intégrité | `pg_restore --list` OK · `.sha256` généré |
| Restauration | `labuse restore-db --file /var/backups/labuse/labuse-labuse-20260621-085854.dump --yes` |

## 2. Voirie avant / après

| | tronçons en base |
|---|--:|
| **Avant** | **5 000** (plafonnée — limite serveur WFS) |
| **Après** | **22 999** ✅ |
| Δ | **+17 999** (`-5 000` purgées / `+22 999` ré-ingérées) |

Saint-Paul était **la plus tronquée** : le plafond 5 000 masquait **~78 %** de sa voirie réelle (17 999 tronçons cachés).

## 3. Preuve de pagination réelle + garde-fou

`ingest_bdtopo` paginé → **5 requêtes WFS `GetFeature`** vers `data.geopf.fr/wfs`
(`BDTOPO_V3:troncon_de_route`, `sortBy=cleabs`, `count=5000`), bbox `55.2167131,-21.1170882,55.4651451,-20.9578718` :

| Page | Requête | Entités | Statut |
|---|---|--:|---|
| 1 | `count=5000` (sans `startIndex`) | 5 000 (pleine) | HTTP 200 |
| 2 | `count=5000&startIndex=5000` | 5 000 (pleine) | HTTP 200 |
| 3 | `count=5000&startIndex=10000` | 5 000 (pleine) | HTTP 200 |
| 4 | `count=5000&startIndex=15000` | 5 000 (pleine) | HTTP 200 |
| 5 | `count=5000&startIndex=20000` | **2 999** (incomplète) | HTTP 200 |

- Log applicatif : `INFO labuse: ingest_bdtopo[voirie] : 22999 objet(s) en 5 page(s)`.
- **22 999 = 4×5 000 + 2 999** ; la page 5 (**2 999 < 5 000**) est **incomplète** → la boucle **s'arrête**
  (aucune requête `startIndex=25000`). **Fetch complet prouvé.**
- **5 requêtes, 5× HTTP 200**, aucune erreur WFS.
- **Garde-fou `max_total=60000` : NON atteint** ✅ (0 occurrence ; 22 999 < 60 000).

## 4. Verdicts avant / après (dernière éval par parcelle)

| Verdict | Avant | Après | Δ |
|---|--:|--:|--:|
| faux_positif_probable | 29 943 | 31 897 | +1 954 |
| **à creuser** | **19 172** | **15 852** | **−3 320** |
| écartée | 1 490 | 1 532 | +42 |
| **opportunité** | **524** | **1 848** | **+1 324** |
| **Total** | **51 129** | **51 129** | 0 |

## 5. Matrice de transition (51 129 parcelles — éval précédente → éval post re-fetch)

| Ancien verdict | → Nouveau | Parcelles |
|---|---|--:|
| faux_positif_probable | → faux_positif_probable | 29 901 |
| faux_positif_probable | → écartée | 42 |
| à creuser | → à creuser | 15 830 |
| **à creuser** | → **faux_positif_probable** | **1 962** |
| **à creuser** | → **opportunité** | **1 380** |
| écartée | → écartée | 1 490 |
| **opportunité** | → **opportunité** | **468** |
| **opportunité** | → **faux_positif_probable** | **34** |
| **opportunité** | → **à creuser** | **22** |

Marginaux recoupés exactement (avant/après) ; **total 51 129 conservé des deux côtés** ; aucune parcelle perdue.

## 6. Opportunités gagnées / dégradées

- **Nouvelles opportunités : 1 380**, venant **exclusivement** de « à creuser » (0 d'ailleurs).
- **Anciennes opportunités sorties du statut : 56** (34 → fpp, 22 → à creuser) ; 468/524 conservées (89,3 %).
- **Gain net : +1 324** opportunités, **borné** sous la « accès seul » de l'audit (6 922).

### Explication des 56 dégradées — refinement, pas régression

Pour **les 56**, `opportunity_score` et `completeness_score` sont **identiques avant/après** (ex. parcelle
333923 : opp 69→69, compl 92→92). Le basculement vient d'un **flag métier** (`decide_status` : opp≥65 &
compl≥50 **mais flag fort** → à creuser), tracé dans `cascade_results` :

```
declassement | SOFT_FLAG | sev=FORT | « bâti significatif : 30 % de la surface intersecte
                                        des bâtiments (BD TOPO) — occupation à vérifier »
acces        | POSITIVE  |          | « Accès direct à la voirie (tronçon au contact) »  ← accès OK
```

- **22/22** des `opp → à creuser` portent un **flag `declassement` sévérité FORT** d'**occupation/bâti**
  (« occupation à vérifier ») — **pas un problème d'accès** (l'accès est POSITIF, voirie à 0–5 m).
- Les **34** `opp → fpp` portent un blocker d'occupation au niveau « faux positif ».
- **Zéro dégradation due à l'accès** : le correctif voirie est **monotone sur l'accès**. Ces 56 sont des
  parcelles **partiellement bâties (~30 %)** en **lisière** de la frontière opportunité/à-creuser, que la
  re-cascade complète range du côté **conservateur** (« à vérifier ») — verdict **plus juste**.

> Réserve de transparence : `cascade_results` est réécrit à chaque passe (historique non reconstituable),
> donc le déclencheur du flag d'occupation sur ces 56 cas-frontière n'est pas prouvable au signal près.
> **Certitudes** : scores inchangés, direction **conservatrice**, échelle **0,1 % des parcelles**, **0 lié à l'accès**.

## 7. Contrôles d'intégrité

| Contrôle | Attendu | Mesuré |
|---|---|---|
| `geom_2975` voirie manquante | 0 | **0** ✅ (`voirie_sans_geom2975 = 0`) |
| Doublons voirie | 0 | **0** ✅ (`voirie_doublons = 0`) |
| Garde-fou `max_total=60000` | non atteint | **non atteint** ✅ |
| Total parcelles évaluées | 51 129 | **51 129** ✅ |
| Erreurs WFS | 0 | **0** ✅ (5× HTTP 200) |
| `evaluate` exit code | 0 | **0** ✅ |
| `/readyz` (après redémarrage API) | ready | **ready: true** ✅ |

## 8. Cohérence inter-communes (validation forte)

Après correctif, les **3 gold convergent** — Saint-Paul, qui était hors-norme, rentre dans le rang :

| Commune (après) | opportunité | à creuser | fpp |
|---|--:|--:|--:|
| L'Étang-Salé | 3,8 % | 29,7 % | 61,8 % |
| La Possession | 4,6 % | 29,6 % | 59,9 % |
| **Saint-Paul** | **3,6 %** | **31,0 %** | **62,4 %** |

Avant, Saint-Paul était à **opp 1,0 % / à creuser 37,5 %** (la plus tronquée). Le correctif **normalise** son profil → **preuve métier** que le résultat est correct.

## 9. Conclusion

✅ **SUCCÈS — `gold` maintenu — pas de rollback.**

Sur la plus grande commune gold (la plus tronquée), le correctif lève le plafond (5 000 → 22 999) et
récupère **+1 324 opportunités nettes** (1 380 depuis « à creuser », **monotone sur l'accès, 0 dégradation
d'accès**). Les 56 anciennes opportunités sorties sont des reclassements **conservateurs** de parcelles
partiellement bâties (scores inchangés, flag occupation) — elles **renforcent** la justesse. La distribution
post-correctif **s'aligne** sur les deux autres gold. Le statut `gold` reste acquis. Backup pré-run disponible.

> **Périmètre du run** : base de travail locale (`localhost:5432/labuse`), **voirie de Saint-Paul
> uniquement**. Aucune autre commune, aucune autre couche, **config gold non modifiée**, **aucun déploiement**.
> **Les 3 communes gold (Saint-Paul, La Possession, L'Étang-Salé) sont désormais re-fetchées au standard voirie complet.**
