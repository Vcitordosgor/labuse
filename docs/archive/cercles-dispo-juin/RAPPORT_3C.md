# RAPPORT — 3.C Alertes intelligentes (« nouveautés »)

> Cercle 3. v1 = système de zones / parcelles suivies + détection au refresh + liste de
> nouveautés. Notifications push = **hors scope v1** (brief). 281 tests verts, ruff clean.

## Ce qui est livré
**Le scope est défini par l'utilisateur** — on n'inonde pas avec les 3 000 parcelles :
- **Zones de veille** : polygones dessinés sur la carte (réutilise l'outil de tracé existant) —
  table `watch_zones` (4326).
- **Parcelles suivies** : les parcelles du **pipeline de prospection** (déjà existant) — aucune
  nouvelle notion à gérer pour l'utilisateur.

**Déclencheurs** (croisent des faits RÉELS déjà ingérés — rien d'inventé) :
| Alerte | Condition |
|---|---|
| `dvf_in_zone` | une **vente DVF** tombe dans une zone de veille (`ST_Contains`) |
| `permit_near_followed` | un **permis** (SITADEL géocodé, 1.B) à **≤ 200 m** d'une parcelle suivie |

**Détection au rafraîchissement** (`compute_alertes`) : **idempotente** — deux index uniques
PARTIELS (`(zone_id, source_ref)` / `(parcel_id, source_ref)`) + `ON CONFLICT DO NOTHING` font
qu'un même fait-source ne crée **qu'une** alerte. Re-rafraîchir sans donnée neuve n'ajoute rien ;
une donnée **nouvellement ingérée apparaît exactement une fois**.

**UI** (panneau « Veille foncière ») : bouton **« + Zone »** (dessine une zone surveillée, visible
sur la carte), bouton **« ↻ »** (re-détecte), **liste des nouveautés** (non-lues d'abord, badge de
compteur), **✓** pour accuser réception, **✕** pour retirer une zone. Cliquer une alerte de permis
ouvre la fiche de la parcelle suivie.

## Endpoints
`GET/POST /watch-zones`, `DELETE /watch-zones/{id}`, `GET /alertes`, `POST /alertes/refresh`,
`POST /alertes/ack`. Migrations idempotentes (`ensure_watch_zones`) câblées dans `ensure_schema`
+ `create_all`.

## Recette (brief : « simuler une nouvelle donnée → elle apparaît »)
`pytest tests/test_alertes.py` (**8 verts**), dont un test **bout-en-bout via HTTP** :
1. créer une zone de veille → 0 nouveauté ;
2. **insérer une vente DVF** dans la zone → `refresh` → **1 nouveauté** `dvf_in_zone` ;
3. accuser réception → la liste des non-lues se vide.
Couvre aussi : vente **hors** zone ignorée, permis **> 200 m** ignoré, **idempotence** (re-run = 0),
suppression de zone → ses alertes partent **par cascade**.

## Limites assumées (v1)
- Pas de **push** (mail/SMS) — détection à l'ouverture / au clic « ↻ ». Un cron appelant
  `/alertes/refresh` après chaque ingestion suffirait à automatiser, sans rien changer au modèle.
- Les alertes valent ce que valent leurs sources : DVF (millésimé) et SITADEL géocodé à ~79 %
  (1.B) — une vente/permis non géolocalisé ne peut pas déclencher (limite déjà documentée).
