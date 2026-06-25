# Saint-Philippe — BLOCAGE : PLU propre `97417` absent du GPU (2026-06-22)

- **Commune / INSEE** : Saint-Philippe / `97417`
- **Statut** : 🔴 **NON VALIDABLE** — bloquée pour cause de zonage inutilisable
- **État conservé** : `partiel_non_evalue` · **non-gold / non-fiable** · bandeau « Partielle — non évaluée » conservé
- **Date du constat** : 2026-06-22

> Cette note documente un **blocage**. Elle ne modifie ni la base, ni les verdicts,
> ni la configuration. **Aucun run / cascade / re-fetch n'a été lancé** — le blocage
> a été détecté **au pré-vol** (analyse lecture seule), avant toute exécution.

## Contexte

Saint-Philippe (commune du Sud, secteur volcan — Piton de la Fournaise) était la cible
du **pré-vol** suivant, après la validation au standard « Saint-Paul » des **8 communes
gold** : Saint-Paul (référence), L'Étang-Salé, La Possession, Saint-Pierre, Le Tampon,
Saint-Louis, Saint-Denis, Saint-Joseph.

Stratégie prévue : `re_couches_re_cascade` (vague 6, risque moyen). Le registre
(`config/communes_gold_standard.yaml`) flaggait déjà « **couverture GPU faible en base** » —
le pré-vol confirme qu'elle est en réalité **nulle**.

## État actuel (mesuré au pré-vol, lecture seule)

| Élément | Valeur |
|---|---|
| Parcelles | **4 162** |
| Sections | **29** |
| Doublons IDU | **0** |
| Géométries invalides | **0** |
| `geom_2975` nuls | **0** |
| Évaluées | **0 / 4 162** |
| Couverture zonage PLU propre | **0,00 %** (0 / 4 162) |

Cadastre **propre** par ailleurs (0 doublon, 0 géométrie invalide, 0 `geom_2975` nul) —
mais **non exploitable** sans zonage.

## Détection au pré-vol — pas de run réel

Le blocage a été **identifié en amont** par l'analyse de couverture zonage du pré-vol.
**Aucun run réel n'a été lancé**, donc **aucun rollback** n'a été nécessaire et **aucun
rapport `saint_philippe_RESULTS.md`** n'a été généré. La base est strictement inchangée.

> ⚠️ Rappel : le **dry-run**/pré-checks ne vérifient que la *présence* d'une couche
> `plu_gpu_zone` (19 > 0), **pas la couverture réelle**. Seul le post-check
> `couverture zonage ≥ 99 %` (après cascade) attraperait le problème — d'où l'intérêt
> d'avoir tranché au pré-vol pour **ne pas gâcher un run** qui finirait en rollback.

## Cause racine

**Aucune zone PLU propre à Saint-Philippe (`97417`) n'est disponible dans le GPU**
(Géoportail de l'Urbanisme). Le document d'urbanisme communal de Saint-Philippe est
absent du flux : **aucune partition `DU_97417`**, aucun `idurba` `97417`.

Les **19 zones** récupérées par le fallback GPU sur l'emprise **n'appartiennent pas à
Saint-Philippe** mais à des **communes voisines** :

| Commune voisine | Partition | Zones |
|---|---|---|
| Saint-Joseph | `DU_97412` | 18 |
| Sainte-Rose | `DU_97419` | 1 |

Et elles sont si marginales sur l'emprise qu'elles **ne couvrent aucune parcelle** de
Saint-Philippe.

## Conséquence

- Couverture zonage **propre** (`97417`) des parcelles de Saint-Philippe : **0 %**.
- Couverture par **toute** zone (y compris débordement voisin) : **0,00 %** (0 / 4 162).
- Le contrôle critique **`couverture zonage ≥ 99 %`** est **impossible à passer**.
- Tout run de validation au standard gold **échouera donc nécessairement** sur ce contrôle,
  indépendamment du reste (parcelles, bâti, voirie, cascade).

C'est le **3ᵉ cas Saint-Leu-bis** (après Saint-Leu `97413` et Saint-André `97409`) :
**run réel impossible** tant qu'une **source officielle fiable `97417`** n'est pas disponible.

## Décision

- Saint-Philippe **reste `partiel_non_evalue`**.
- Saint-Philippe **reste non-gold / non-fiable** ; le bandeau « Partielle — non évaluée » est **conservé**.
- **Config inchangée**, **aucun verdict modifié**, aucune donnée publiée.

## Condition de reprise

Reprise de Saint-Philippe **conditionnée** à l'une des situations suivantes :

1. **Disponibilité d'un PLU/GPU `97417` fiable** dans le flux GPU (document d'urbanisme
   propre à Saint-Philippe, couvrant ses parcelles) ; **ou**
2. **Source alternative officielle validée** fournissant le zonage réglementaire de
   Saint-Philippe avec une couverture suffisante pour passer le contrôle
   `couverture zonage ≥ 99 %`.

## Consigne

> ⛔ **Ne pas relancer Saint-Philippe** (run / cascade / re-fetch / passage gold) tant que
> la **condition de reprise** ci-dessus n'est pas remplie. Toute relance retomberait sur le
> même échec de zonage garanti (couverture 0 %).

---

## Mise à jour 2026-06-25 — re-vérification (read-only) : confirmé NO-GO temporaire, **aucun fallback**

Re-sondage strictement lecture seule au 2026-06-25 (`main` à `f623fe3`). Le blocage est **confirmé et précisé** :
aucune géométrie de zonage n'existe dans **aucune** source — y compris AGORAH (ce qui **exclut** un repli à la
Saint-Leu).

| Source | Constat 2026-06-25 | URL |
|---|---|---|
| GPU `document DU_97417` (PLU) | **0** | `apicarto.ign.fr/api/gpu/document?partition=DU_97417` |
| GPU `zone-urba DU_97417` | **0** (`totalFeatures 0`) | `apicarto.ign.fr/api/gpu/zone-urba?partition=DU_97417` |
| GPU `document` / `secteur-cc CC_97417` (carte communale) | **0 / 0** | `apicarto.ign.fr/api/gpu/secteur-cc?partition=CC_97417` |
| GPU `municipality` | `is_rnu=false`, `is_coastline=true` — **ambigu/périmé** (aucune géométrie servie) | `apicarto.ign.fr/api/gpu/municipality?insee=97417` |
| **AGORAH** Base permanente PLU | **0 zone `97417`** (idurba/datappro = null) | `data.regionreunion.com/.../base-permanente-des-plu-de-la-reunion/records?where=insee="97417"` |
| **DEAL** — état d'avancement docs d'urbanisme | **RNU + PLU en élaboration** (non approuvé) | `reunion.developpement-durable.gouv.fr/etat-d-avancement-des-documents-d-urbanisme-a121.html` |
| Commune Saint-Philippe | service urbanisme (suivi PLU) | `saintphilippe.re/urbanisme/` |

**État technique DB (inchangé, lecture seule)** : 4 162 parcelles · 0 doublon · **0 géométrie invalide** ·
0 `geom_2975` nul · **0 évaluée** · DVF 315 · **zonage propre `97417` = 0** (19 zones = bleed Saint-Joseph
`97412` 18 + Sainte-Rose `97419` 1, couverture parcellaire **0 %**) · bâti 0 · PPR/SAR/prescriptions/ravine/osm 0
(pente 5 111, voirie 2 590).

### Conclusion (2026-06-25)

- **Pas de PLU exploitable** (`DU_97417` absent du GPU).
- **Pas de carte communale exploitable** (`CC_97417` absent du GPU).
- **Pas de fallback AGORAH possible** — contrairement à Saint-Leu (`97413` : 371 zones AGORAH 2007), AGORAH **n'a
  aucune zone** pour `97417`. **Il n'y a donc PAS de « Saint-Leu-bis » applicable ici.**
- **Pas de run recommandé**, **pas de gold possible** : le contrôle `couverture zonage ≥ 99 %` reste à **0 %** → échec garanti.
- **Ne PAS improviser une cascade « mode RNU »** sans logique réglementaire dédiée et validée (constructibilité RNU
  subtile : parties urbanisées / règles de continuité — risque fort).
- **Blocage TEMPORAIRE, réversible** dès publication d'une **géométrie PLU exploitable** (GPU `DU_97417`, ou refresh
  AGORAH `idurba 97417`, ou autre source officielle SIG).
- **Priorité FAIBLE** : commune du secteur **volcan** (Piton de la Fournaise, `parc_national` 3 + `foret_publique` 11),
  4 162 parcelles, DVF 315 → même débloquée, opportunités **quasi-nulles** attendues. À traiter **après** les vrais
  leviers (PPR Étape B, généralisation Étape A).

> ⛔ **Statut maintenu : NON-gold / non-validable, sous veille PLU.** Aucun run / cascade / re-fetch / passage gold.
> Config inchangée, DB inchangée (431 663 / 24 / gold 17).
