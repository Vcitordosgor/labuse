# MANDAT RNU — Rapport final (STOP levé : méthode validée Vic 26/07/2026 et codée)

> **Validation Vic** : (1) médian, paramètres en CONFIG ; (2) critère centre ;
> (3) plancher `dans PAU ∧ ≥ 600 m²` — même seuil que partout. **+ 2 ajouts** :
> exports RNU = « non applicable — RNU » sur les règles de capacité (jamais un
> tableau vide) ; PAU étiquetée ESTIMATION (wording exact gravé, testé).
>
> **CODÉ ET PROUVÉ (commit d7e103f)** : `labuse rnu-pau` → `commune_pau`/`parcel_pau`
> (Saint-Philippe : 35 noyaux · 268 ha · 2 373 parcelles · **127 nues ≥ 600 m²
> éligibles** — identique au prototype) ; plancher C branché (colonne absente =
> comportement d'avant, testé ; les tiers ne bougent qu'au prochain `score-v2`) ;
> bannière fiche DANS/HORS enveloppe + avertissement ; PDF : « non applicable —
> RNU » ×3 + estimation + état d'enveloppe. Tests 7/7 · golden 116/116 + PASS
> tiers_effectifs · tiers île au bit près · tsc 0 · build OK.
> Le contenu ci-dessous est conservé tel quel (historique de la proposition).

---

# (Historique) Rapport d'étape · STOP validation (méthode PAU)

**Branche** : `feat/rnu` (base main 7976d54, poussée, non mergée). **Golden 116/116** +
`PASS tiers_effectifs` ; **les 5 tiers île au bit près** (120/1031/3587/72980/353945 —
mécaniquement garanti : rien d'écrit hors config/module additifs ; NB : la consigne
« hors Saint-Philippe » est même dépassée, les effectifs TOTAUX sont inchangés puisque
aucun re-run n'a eu lieu). Modèle P intouché.
**Note session** : mandat « Modèle Fable » — session exécutée sur Opus 4.8.

## FAIT (commité)

### A — Nettoyage préalable ✅
- **A1** · Filtre **ANTI-DÉBORD GÉNÉRAL** dans `scripts/calibrage_zonage.py` (esprit C :
  toutes communes, pas un cas 97417) : une zone dont l'`idurba` appartient à une autre
  commune est exclue du manifeste et **comptée** (`zones_debord_exclues`), jamais tue.
  Manifeste Saint-Philippe régénéré : **0 zone propre**, 3 débords 97412/97419 tracés,
  `statut_document` explicite. `spatial_layers` volontairement non touchée (les couches
  sont lues par bbox, partagées entre communes voisines) — et preuve qu'aucun héritage
  n'existe dans le servi : les 4 162 parcelles 97417 du dataset sont TOUTES
  `zone_plu='inconnu'`.
  **Découverte en chemin** : les manifestes committés de Saint-Denis et Saint-Paul
  étaient PÉRIMÉS (vieux PLU + un débord 97408 figé dans celui de SD) — le roundtrip
  échouait DÉJÀ sur main (prouvé). Régénérés sur les PLU en vigueur (SD 2026-04-23,
  SP 2025-12-17). **Roundtrip 24/24 ZÉRO écart PROUVÉ.**
- **A2** · `POST_16_STRATEGIC_INVENTORY.md` corrigé (3 mentions) : « un PLU existe mais
  non numérisé » était FAUX (flag GPU `is_rnu` périmé) ; la note du 25/06 fait foi —
  **RNU + PLU en élaboration**, il n'existe RIEN à sourcer.

### C — Flag commune-level GÉNÉRAL ✅
`config/rnu_communes.yaml` (source de vérité déclarative, chaque entrée SOURCÉE et datée)
+ `src/labuse/rnu.py` (helpers). **Généralité testée** : ajouter une commune au RNU
(PLU annulé au contentieux, caducité…) = une entrée yaml, zéro code — un test le prouve
en flaggant un Saint-Leu hypothétique. Le flag GPU `is_rnu` n'est PAS utilisé (périmé,
preuve à l'annexe ALGO-1b).

### B3 — Étiquetage ✅ (la partie de B qui ne dépend pas de la méthode PAU)
- Fiche : bloc `rnu` au payload + **bannière ambre** sous la carte verdict —
  « ⚠ Commune au règlement national d'urbanisme — pas de PLU local » + détail honnête
  (« constructibilité limitée aux parties actuellement urbanisées — analyse au cas par
  cas, non couverte par le zonage LABUSE ») + date de vérification. Capture
  `qa/rnu/fiche_banniere_rnu.png` (97417000AC0003).
- Exports Flash/Dossier : UNE ligne conditionnelle en gras — **prouvée dans le PDF réel**.
- Contrôles : commune à PLU → `null` ; tests 3/3 ; tsc 0 ; build OK.

---

## STOP — PROPOSITION À VALIDER AVANT DE CODER (mandat B)

### D d'abord, l'honnêteté : la détermination des PAU est-elle fiable ?

**Oui, faisable sur données réelles** — la note de juin (« bâti 0 ») est périmée :
Saint-Philippe a en base **4 512 bâtiments BD TOPO, 2 590 tronçons de voirie, 5 111
mailles de pente** ; 2 408/4 162 parcelles bâties. Un prototype lecture seule
(ST_ClusterDBSCAN PostGIS) produit des enveloppes plausibles (urbanisation linéaire
RN2). Donc PAS de stop-échec au titre du D — mais un STOP de VALIDATION au titre du B.

### Méthode PAU proposée (prototypée sur 97417, chiffres réels)

**Principe** (aligné sur la grille jurisprudentielle des PAU : noyau bâti significatif +
continuité ; CE, « parties actuellement urbanisées » — nombre de constructions, densité,
distance au bâti existant) :
1. **Noyaux** : clusters de bâtiments BD TOPO par `ST_ClusterDBSCAN` (distance de
   continuité `eps`, effectif minimal `minpoints`) — un hameau = un noyau, les
   constructions isolées ne font jamais une PAU ;
2. **Enveloppe PAU** : union des buffers (`buf`) autour des bâtiments clusterisés ;
3. **Parcelle dans la PAU** : son `ST_PointOnSurface` est dans l'enveloppe (critère
   centre — le critère « touche » sur-inclut les grandes parcelles de lisière).

**Trois jeux de paramètres prototypés** (bâtiments 97417 réels) :

| Jeu | eps / minpts / buf | Noyaux | PAU (ha) | Parcelles dans PAU (centre) | dont nues | nues ≥ 600 m² |
|---|---|---:|---:|---:|---:|---:|
| strict | 40 m / ≥15 bât. / 30 m | 29 | 83 | 1 146 | 137 | 26 |
| **médian (recommandé)** | **50 m / ≥10 bât. / 40 m** | **35** | **268** | **2 373** | **464** | **127** |
| large | 75 m / ≥8 bât. / 50 m | 33 | 444 | 2 814 | 661 | 264 |

**Recommandation : le MÉDIAN** — ≥10 constructions et ~50 m de continuité collent aux
ordres de grandeur retenus par le juge administratif ; le strict est la variante
prudente si tu préfères ouvrir petit. Le jeu retenu sera gravé dans
`config/rnu_communes.yaml` (section `pau:`) — général, par commune au RNU.

### Plancher C équivalent proposé (aujourd'hui infranchissable : exige U/AU)

> parcelle **dans la PAU** (critère centre) **ET surface ≥ 600 m²**

— même seuil de surface que le plancher C actuel (cohérence produit) ; la branche SDP
n'existe pas au RNU (pas de règlement → pas de droits calculables). Effet chiffré
(médian) : **127 parcelles nues** de Saint-Philippe deviendraient ÉLIGIBLES au plancher —
éligibles seulement : le rang P décide ensuite, comme partout (aucun quota, aucun
traitement de faveur). Étiquette spécifique sur toute chaude issue du RNU (wording B3).

### Ce que la validation déclenchera (et ce qu'elle ne déclenchera pas)
- codage de la PAU (table additive `commune_pau` + build par commune flaggée),
  plancher C adapté dans `p_v2/statuts.py` (branche RNU, comportement STRICTEMENT
  identique pour les communes à document local), étiquetage « chaude (RNU) » ;
- **les effectifs des 23 autres communes resteront au bit près** (le plancher C ne
  change que pour les communes flaggées RNU) ; les tiers de Saint-Philippe évolueront
  au PROCHAIN run `score-v2` seulement — jamais rétroactivement ;
- resteront HORS périmètre : règles R.111-x fines (reculs, aspect), avis conforme
  préfet, dérogations L.111-4 — la faisabilité RNU restera étiquetée « analyse au cas
  par cas », le moteur ne promet rien.

### Questions à trancher (Vic)
1. Jeu de paramètres PAU : **médian** (recommandé) / strict / large ?
2. Critère parcelle : **centre dans l'enveloppe** (recommandé) ou « touche » ?
3. Plancher C RNU : `dans PAU ∧ ≥ 600 m²` te va, ou seuil de surface différent au RNU ?

**⛔ STOP — rien de la branche PAU/plancher C n'est codé sans ta validation.**
