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

## 4. Parcelles de démo (Saint-Paul) — états vérifiés après `rebuild-demo`

| IDU | Rôle | Ce qu'elle montre | Vigilance |
|---|---|---|---|
| 97415000BP0571 | **Belle opportunité + bilan** | opp ~77, 9222 m², prix **fiable** ~4184 €/m², CA ~23,5 M€ | « vérifiée » = sur couches dispo ; bilan = simulation indicative |
| 97415000BS0009 | Opportunité + bilan (2ᵉ ex.) | opp ~76, prix fiable ~4145 €/m², CA ~8,8 M€ | hypothèses travaux/marge à valider |
| 97415000BN1351 | **À creuser — périmètre PPR** | le PPR rétrograde l'opportunité en « à creuser » + bilan | PPR = prescriptions, **pas** exclusion |
| 97415000BH0283 | SAR compatible | vocation « urbanisé à densifier » | compatibilité ≠ constructibilité |
| 97415000BO0845 | **Faux positif PARKING déclassé** | brut ~82 mais « faux positif » + « parking sur 82 % (OSM) » | score brut conservé (transparence) |
| 97415000BV1431 | **Faux positif PENTE déclassé** | « pente 103 % — terrain non aménageable » + SAR naturel | — |
| 97415000BO0619 | Micro-parcelle déclassée | « micro-parcelle 28 m² — aucun programme » | — |
| 97415000BK0023 | Bord d'équipement CONSERVÉ | effleure un parking (<30 %) → reste opportunité | anti-sur-déclassement (honnêteté) |

## 5. Scénario de démo recommandé (≈ 8 min)

1. **Carte** : « voici Saint-Paul, en vert les opportunités vérifiées ».
2. **BP0571** : belle opportunité vérifiée → bilan (prix de marché **fiable** 4184 €/m², CA ~23,5 M€, neuf vs ancien, charge foncière).
3. **BN1351** : opportunité… mais **périmètre PPR** → « à creuser », prescriptions à vérifier (PPR ≠ exclusion).
4. **BO0845** : « score brut 82… mais c'est un **parking** » → faux positif déclassé, motif visible. *La confiance avant l'effet waouh.*
5. **BV1431** : pente 103 % → déclassée. **BK0023** : effleure un parking mais **conservée** → on ne sur-déclasse pas.
6. **Prospection** : sur BP0571, « + Suivre » → « Propriétaire à identifier » → prochaine action + contact manuel.
7. **Kanban** : pipeline de prospection (entrées de démo) → organiser le suivi.
8. **Export** : fiche Markdown/HTML présentable en réunion.

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
