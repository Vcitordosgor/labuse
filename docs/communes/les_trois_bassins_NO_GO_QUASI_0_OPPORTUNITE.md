# Les Trois-Bassins (97423) — NO-GO gold : quasi-0 opportunité

**Décision (2026-06-23)** : Les Trois-Bassins est **différée** (NON-GOLD) après un run `import_complet`
**techniquement propre** (exit 0) mais dont le **résultat métier est trop faible** (1 opportunité sur
5 314 parcelles). Décision analogue à **La Plaine-des-Palmistes** : le run a fait son travail, mais le
profil d'opportunité de la commune est intrinsèquement quasi nul → **pas de passage gold** sans arbitrage
produit/scoring.

## 1. Le run est techniquement propre (exit 0)

| Contrôle | Valeur |
|---|---|
| Exit code | **0 (SUCCÈS technique)** — 22 post-checks verts |
| Parcelles | **5 314** (distinct IDU 5 314, **0 doublon**, préfixe 97423) |
| Évaluées | **5 314 / 5 314** (100 %) |
| Géométries invalides | 0 · `geom_2975` 100 % |
| PLU/GPU propre `DU_97423` | **100 %** (idurba `97423_PLU_20220602`) · zonage total 100 % |
| Bâti | **7 898** (> 0, dense ≈ 1,49/parcelle) |
| Voirie | **3 625** (non tronquée, ≠ 5 000) |
| DVF | **157** · PPR **4** · `osm_faux_positif` **33** (ingéré OK) · prescriptions 293 |
| Doublons de couche | **0** (contrôle durci) |

Backup pré-commune (point de retour, non utilisé) :
`/var/backups/labuse/labuse-pre-les-trois-bassins-20260623-153129.dump`
(SHA-256 `048b944c6798a73190f3a58281490d70ed3b66dcb9969c0022deb4269174f618`).

## 2. Mais le résultat métier est trop faible

| Verdict | Count | % |
|---|---|---|
| faux positif probable | 3 833 | 72,1 % |
| à creuser | 1 265 | 23,8 % |
| écartée | 215 | 4,0 % |
| **opportunité** | **1** | **0,0 %** |

**1 seule opportunité sur 5 314 parcelles.** La garde QA technique passe (0,0 % ≤ plafond 5 %, qui ne
borne que le haut), mais le résultat est **commercialement quasi nul**.

## 3. Pattern proche de La Plaine-des-Palmistes

Même profil que **La Plaine-des-Palmistes** (différée à 0 opportunité) : petite commune au **bâti très
dense** (1,49 bâtiment/parcelle) → **72,1 % de parcelles réactivées en faux positifs probables** → il ne
reste quasiment aucune parcelle libre constructible. Le 0-opp est **intrinsèque** au profil de la commune,
**pas un artefact** d'un bug ni d'une couche manquante (toutes présentes, PLU propre 100 %, osm OK).

## 4. Décision

- **Gold différé** : Les Trois-Bassins **reste `absent`/non-gold** en config (aucun passage gold).
- **Data conservée en DB** : le run est conservé (5 314 parcelles + couches), **aucun rollback recommandé**
  (le backup pré-commune reste disponible si un retour propre était un jour souhaité).
- **Aucune mutation corrective** : pas de re-cascade, pas de dédup, pas de nettoyage d'évaluations.
- **À reprendre plus tard** : arbitrage **produit / scoring** — une commune à quasi-0 opportunité a-t-elle
  une valeur commerciale ? Faut-il ajuster le scoring sur les communes à très fort taux de bâti ? Décision
  découplée du run technique (qui, lui, est validé).

## 5. Communes au même statut « différé »

| Commune | INSEE | Motif |
|---|---|---|
| La Plaine-des-Palmistes | 97406 | 0 opportunité (scoring/métier) |
| Entre-Deux | 97403 | évaluée sans bâti (La Plaine-bis) |
| **Les Trois-Bassins** | **97423** | **quasi-0 opportunité (1/5 314)** |

> Bloquées PLU/GPU (catégorie distincte, à débloquer séparément) : Saint-Leu, Saint-André, Saint-Philippe.
