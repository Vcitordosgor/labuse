# LA BUSE — Préparer une démo propre et reproductible

Le conteneur de dev/démo peut recycler la base et perdre l'état live (geom_2975, PPR, SAR,
déclassement, geo-dvf, colonnes prospection). Le **code est durable** : une seule commande
reconstruit un état cohérent. Rien ici ne change le scoring, les seuils ni les couches.

## 1. Reconstruire la base de démo (idempotent)

```bash
python -m labuse.cli rebuild-demo --commune 97415          # Saint-Paul
# options : --no-seed-pipeline  ·  --skip-ingest (ré-évalue sans ré-ingérer)  ·  --limit N (tests)
```

Enchaîne : schéma + triggers (`geom_2975`, colonne `prospection`) → cadastre + couches
(**geo-dvf 2021-2025, PPR, SAR, OSM faux positifs**, pente, PLU) → `geom_2975` valide
(`ST_MakeValid`) + index GIST → **évaluation** (cascade + scoring + **déclassement**) →
seed pipeline → **healthcheck**. Re-jouable sans rien casser.

## 2. Vérifier que la base est prête

```bash
python -m labuse.cli demo-healthcheck --commune Saint-Paul   # sortie ≠ 0 si une couche critique manque
```

Contrôle : parcelles · `geom_2975` valide + index · DVF geo-dvf · PPR · SAR · OSM ·
déclassement appliqué · top 20 sans faux positif évident · badge « Opportunité vérifiée »
actif · module prospection · pipeline · exports HTML/Markdown.

## 3. Lancer l'application

```bash
python -m labuse.cli api          # FastAPI (uvicorn) → http://localhost:8000/app
```

## 4. Parcelles de démo (Saint-Paul)

| IDU | Rôle | Ce qu'elle montre | Vigilance |
|---|---|---|---|
| 97415000BN1351 | Opportunité vérifiée + bilan + PPR | prix DVF fiable, charge foncière, périmètre PPR | PPR = prescriptions, pas exclusion |
| 97415000BO0057 | Bilan promoteur lisible | CA + charge foncière chiffrés | hors îlot SAR ; bilan = simulation indicative |
| 97415000BH0283 | SAR compatible | vocation « urbanisé à densifier » | compatibilité ≠ constructibilité |
| 97415000BO0845 | Faux positif PARKING déclassé | score brut élevé mais « faux positif probable » + motif | score brut conservé (transparence) |
| 97415000BV1431 | Faux positif PENTE déclassé | déclassement pente 94 % + SAR naturel | — |
| 97415000BO0619 | Micro-parcelle déclassée | ~28 m² → faux positif | — |
| 97415000BN1086 | Micro-parcelle déclassée | ~29 m² → faux positif | — |
| 97415000BK0023 | Bord d'équipement CONSERVÉ | effleure un parking (<30 %) → reste opportunité | anti-sur-déclassement (honnêteté) |

## 5. Scénario de démo recommandé (≈ 8 min)

1. **Carte** : « voici Saint-Paul, en vert les opportunités vérifiées ».
2. **BN1351** : opportunité vérifiée → bilan (prix de marché fiable, charge foncière) + PPR (à vérifier).
3. **BO0845** : « score brut 82… mais c'est un parking » → faux positif déclassé, motif visible. *La confiance avant l'effet waouh.*
4. **BV1431** : pente 94 % → déclassée. **BK0023** : effleure un parking mais conservée → on ne sur-déclasse pas.
5. **Prospection** : sur BN1351, « + Suivre » → « Propriétaire à identifier » → prochaine action + contact manuel.
6. **Kanban** : pipeline de prospection (entrées de démo) → organiser le suivi.
7. **Export** : fiche Markdown/HTML présentable en réunion.

## 6. Limites à expliquer honnêtement

- **Prix** = donnée de marché DVF (geo-dvf 2021-2025). Le **bilan** reste une *simulation indicative* (hypothèses travaux/marge/frais à valider).
- **PPR** = périmètre réglementaire (servitude) → prescriptions, **pas** une exclusion ; zonage rouge/bleue à vérifier au règlement.
- **SAR** = vocation régionale (proxy, **couverture partielle**) → « hors îlot » ≠ « aucune contrainte ».
- **« Opportunité vérifiée »** = contrôlée sur les couches disponibles, **pas** une garantie de constructibilité.
- **Propriétaire** : aucune donnée nominative externe — saisie **manuelle** uniquement.

## 7. Checklist avant appel client

- [ ] `rebuild-demo` lancé, `demo-healthcheck` → **✅ PRÊT POUR LA DÉMO**.
- [ ] Top 20 opportunités sans faux positif évident.
- [ ] Pipeline non vide (entrées de démo).
- [ ] Une fiche exportée (Markdown + HTML) ouverte et présentable.
- [ ] Aucun nom de propriétaire réel à l'écran.
- [ ] `pytest -q` vert (tests critiques).
