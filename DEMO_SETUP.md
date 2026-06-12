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
| 97415000BK0023 | **VITRINE — opportunité VACANTE + bilan** | opp ~74, **9 723 m² nus (0 % bâti, vérifié orthophoto)**, accès voirie, prix **fiable** ~5 310 €/m², CA indicatif ~32-35 M€ | « vérifiée » = sur couches dispo ; bilan = simulation indicative |
| 97415000BV0912 | Opportunité + **bâti léger signalé** (2ᵉ ex.) | opp ~77, ~3 948 m², prix fiable ~3 014 €/m² ; « présence de bâti à vérifier (7 %) » affiché | bâti léger signalé, pas caché — terrain à vérifier |
| 97415000BP0571 | **RÉSIDENCE DÉTECTÉE — correctif « déjà bâti »** | score brut 77 mais « ensemble bâti : 4 bâtiments couvrant 18 % (BD TOPO) » → faux positif | l'argument honnêteté : on s'est corrigés et on le montre |
| 97415000BN1351 | **À creuser — périmètre PPR** | le PPR rétrograde l'opportunité en « à creuser » + bilan | PPR = prescriptions, **pas** exclusion |
| 97415000BH0283 | SAR compatible | vocation « urbanisé à densifier » | compatibilité ≠ constructibilité |
| 97415000BO0845 | **Faux positif PARKING déclassé** | brut ~82 mais « faux positif » + « parking sur 82 % (OSM) » | score brut conservé (transparence) |
| 97415000BV1431 | **Faux positif PENTE déclassé** | « pente 103 % — terrain non aménageable » + SAR naturel | — |
| 97415000BO0619 | Micro-parcelle déclassée | « micro-parcelle 28 m² — aucun programme » | — |

## 5. Scénario de démo recommandé (≈ 8 min)

1. **Carte** : « voici Saint-Paul, en vert les opportunités vérifiées — et VACANTES (bâti contrôlé sur BD TOPO) ».
2. **BK0023** : opportunité vitrine, **0 % bâti** → bilan (prix de marché **fiable** ~5 310 €/m², CA indicatif ~33 M€, neuf vs ancien, charge foncière).
3. **BP0571** : « score brut 77… mais c'est une **résidence existante** : 4 bâtiments détectés (BD TOPO) → faux positif ». *L'outil détecte le déjà-bâti — la confiance avant l'effet waouh.*
4. **BN1351** : opportunité… mais **périmètre PPR** → « à creuser », prescriptions à vérifier (PPR ≠ exclusion).
5. **BO0845** : parking sur 82 % → déclassée. **BV1431** : pente 103 % → déclassée. **BV0912** : bâti léger 7 % → **signalé sans déclasser** (on ne sur-corrige pas).
6. **Prospection** : sur BK0023, « + Suivre » → « Propriétaire à identifier » → prochaine action + contact manuel.
7. **Kanban** : pipeline de prospection (entrées de démo) → organiser le suivi.
8. **Export** : fiche Markdown/HTML présentable en réunion (avec la section « Occupation actuelle »).

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
