# Saint-Leu (97413) — PLU / AGORAH : veille de fraîcheur (NO-GO temporaire)

> **Statut : 🔴 NON-GOLD / BLOQUÉE — sous veille PLU.** Décision du **2026-06-23**.
> Géométrie AGORAH techniquement exploitable, **mais PLU 2007 en fin de cycle (révision en cours)** →
> **NO-GO allowlist & run pour l'instant.** Réouverture conditionnée à l'approbation du nouveau PLU.

## Décision (résumé)

- ❌ **Ne pas** ajouter Saint-Leu `97413` à l'allowlist AGORAH (`AGORAH_PLU_ALLOWLIST`).
- ❌ **Ne pas** lancer de pré-vol run, ni `re_couches_re_cascade`, ni import, ni passage gold.
- 🟡 **Saint-Leu reste non-gold / bloquée**, placée **sous veille PLU**.
- ✅ Connecteur AGORAH **inchangé** : le défaut conservateur (Saint-Leu hors allowlist) est **confirmé** par l'enquête de fraîcheur.

## 1. Contexte — Saint-Leu bloquée GPU/PLU

Saint-Leu fait partie des communes dont le **zonage PLU est absent du Géoportail de l'Urbanisme** : le
pipeline gold ne peut pas servir de zonage propre `DU_97413` depuis la chaîne officielle GPU. La commune
n'est donc pas généralisable au standard Saint-Paul par la voie nominale (API Carto / WFS GPU).

## 2. Constat technique GPU / API Carto / WFS (lecture seule)

| Sonde | Résultat |
|---|---|
| API Carto GPU `zone_urba` partition `DU_97413` | **0 zone propre** |
| Géoplateforme WFS `wfs_du:zone_urba` `DU_97413` | **0 zone propre** (vérifié en session) |
| apicarto GPU `/document?partition=DU_97413` | **0 document** (géométrie non publiée) |
| apicarto GPU `municipality` (97413) | `is_rnu=false` → **un PLU EST en vigueur**, mais **non numérisé au GPU** ; `is_coastline=true` (loi Littoral) |

> Conclusion : Saint-Leu a bien **un PLU opposable**, mais **sa géométrie n'est pas publiée au GPU** → repli
> sur une source institutionnelle alternative nécessaire (AGORAH).

## 3. Source AGORAH trouvée (repli candidat)

Base **« Base permanente des PLU de La Réunion »** — AGORAH via Open Data Réunion (OpenDataSoft).

| Champ | Valeur |
|---|---|
| INSEE | `97413` |
| Zones | **371** |
| `idurba` | `97413_20070226` |
| `datappro` (approbation) | **2007-02-26** |
| Couverture parcellaire estimée (pré-vol lecture seule) | **≈ 99,12 %** (22 757 / 22 959) |
| Mix U/AU | **≈ 54 %** |
| Type de document | **PLU communal** (pas un PLUi — le TCO porte le SCoT, pas de PLUi) |
| Fraîcheur du jeu AGORAH | dataset rafraîchi **2023-07-03** → enregistre **toujours** le PLU 2007 pour Saint-Leu |

> Techniquement, AGORAH fournit donc une **géométrie exploitable** (couverture ≈ 99,12 %), comparable au
> repli qui a débloqué **Saint-André** (97409, PLU 2019). **La différence est la fraîcheur** (cf. §4).

## 4. Analyse de fraîcheur — le point bloquant

Le PLU AGORAH de Saint-Leu est **celui de 2007**. Enquête de fraîcheur (sources institutionnelles, lecture seule) :

- ✅ **PLU 2007 toujours JURIDIQUEMENT EN VIGUEUR** au 2026-06-23 (la révision n'est pas approuvée) — confirmé
  par GPU (`is_rnu=false`) et AGORAH (2007 = seul document enregistré).
- 🔄 **Révision générale du PLU EN COURS** (commune de Saint-Leu) :
  - bilan de concertation validé le **21/08/2025** ;
  - **projet de PLU arrêté par délibération le 11/12/2025** ;
  - **avis DÉFAVORABLE de la Région le 27/02/2026** (incompatibilités persistantes avec le **SAR** malgré ajustements) ;
  - enquête publique (1 mois) puis **approbation visée au 2ᵉ semestre 2026** — **non stabilisée** (fragilisée par l'avis Région).
- ❌ **Géométrie de la révision NON disponible** en format exploitable : le projet n'est diffusé qu'en **PDF**
  (aucun SIG / shapefile / GeoJSON) ; rien dans GPU ni AGORAH pour la version révisée.

**Conclusion fraîcheur** : le PLU 2007 est **opposable aujourd'hui mais en fin de cycle**. Le futur PLU
reclassera le zonage (objectifs affichés : +3 100 logements, +12,4 ha de zones U d'ici 2035). Un gold posé
sur le zonage 2007 serait **invalidé à brève échéance** → pas assez **durable** pour un gold fiable. À
l'opposé de Saint-André (PLU 2019, récent et stable), Saint-Leu cumule **PLU ancien + remplacement imminent**.

## 5. Décision détaillée

- **NO-GO allowlist maintenant** : Saint-Leu `97413` **n'est pas** ajoutée à `AGORAH_PLU_ALLOWLIST`.
- **NO-GO run maintenant** : aucun pré-vol run, aucun `re_couches_re_cascade`, aucun import, aucun passage gold.
- **Saint-Leu sous veille** : statut conservé `partiel_non_evalue` (non-gold / bloquée) tant que la fraîcheur
  n'est pas réglée.

## 6. Conditions de réouverture (toutes requises)

1. **Nouveau PLU approuvé** (révision générale rendue exécutoire) — ou, à défaut, confirmation que le 2007
   reste durablement en vigueur (révision abandonnée/repoussée à long terme).
2. **Géométrie publiée** et exploitable dans **GPU** (`zone_urba DU_97413`) **ou AGORAH** **ou** une autre
   **source institutionnelle** fiable (SIG/shapefile/GeoJSON, pas PDF).
3. **Couverture parcellaire ≥ 99 %** vérifiée.
4. **Pré-vol lecture seule validé** (géométries valides, typezones cohérentes, partition `DU_97413`,
   couverture parcellaire) — comme pour Saint-André avant activation.

> Si ces 4 conditions sont réunies → on pourra alors (sur validation) ajouter `97413` à l'allowlist et
> dérouler la séquence run → gold habituelle.

## 7. Veille — prochaine action future (NON exécutée)

Mettre Saint-Leu en **veille PLU** (lecture seule, récurrente) :

- **GPU `DU_97413`** : surveiller la publication d'une **nouvelle partition** (idurba ≥ 2026) dans
  `zone_urba` (API Carto / WFS `wfs_du`).
- **AGORAH** : surveiller un **refresh** de la « Base permanente des PLU » introduisant un `idurba` plus récent
  pour `97413`.
- **Commune / TCO / DEAL** : surveiller l'**approbation** de la révision (site `saintleu.re`, TCO, **DEAL
  Réunion « état d'avancement des documents d'urbanisme »**).

Dès qu'une source publie la géométrie révisée → **re-déclencher le pré-vol AGORAH/GPU lecture seule**, puis
réévaluer la décision d'allowlist. **Rien n'est lancé sans validation explicite.**

---

### Provenance (lecture seule, hors dépôt)

Sondes effectuées le 2026-06-23, conservées **hors dépôt** dans `/tmp/labuse_plu_probe/` (aucun fichier de
probe versionné). Aucune mutation DB, aucun run, aucune modification de code/allowlist.

**Sources** :
- Commune de Saint-Leu — PLU : <https://www.saintleu.re/plan-local-d-urbanisme-plu> · archives <https://www.saintleu.re/plu>
- Région / avis défavorable (27/02/2026) : presse locale (zinfos974) ; IntraMuros Saint-Leu (dossier PLU)
- DEAL Réunion — PLU : <https://www.reunion.developpement-durable.gouv.fr/plan-local-d-urbanisme-plu-r78.html>
- AGORAH « Base permanente des PLU de La Réunion » (Open Data Réunion / OpenDataSoft) — `data.regionreunion.com`
- IGN apicarto GPU `municipality` / `document` ; Géoplateforme WFS `wfs_du`
