# M11 · AUDIT SURFACE B — Recherche IA de la page (traducteur langage→filtres)

**Date** : 2026-07-15. Lecture seule, appels IA réels (instance dev), inspection base. Aucune modif, aucun commit.

## ⚠️ Constat d'entrée : il y a DEUX traducteurs NL distincts
| | `/ia/search` (page IA « recherche simple ») | `/ia/segments-search` (page Segments) |
|---|---|---|
| Code | `api/ia.py:329` + `FILTER_SCHEMA` (`ia.py:87`) | `api/ia.py:411` → `ai/nl_segments.py:169` (`traduire`) |
| Schéma de sortie | JSON `FILTER_SCHEMA` (**14 champs** dashboard) | JSON registry segments (**37 filtres**) |
| Comportement hors-scope | **DROP SILENCIEUX** (§2) | **REFUS HONNÊTE** out_of_scope + liste des groupes |
| Modèle | haiku (`MODEL_FACTUAL`), temp 0 | haiku, temp 0 |

Le mandat vise « la recherche simple de la page IA » = **`/ia/search`** (c'est là qu'est le drop silencieux connu). `nl_segments` est la recherche de la page **Segments**, plus riche et plus honnête. Les deux sont audités ci-dessous.

---

## 1. LE TRADUCTEUR ACTUEL

**CE QUI EXISTE** — deux traducteurs langage-naturel → filtres JSON (pas un chatbot). haiku, `temperature=0`, prompt « n'invente JAMAIS un filtre ». Sortie validée par schéma (garde-fou anti-invention de clé).

**CE QUE ÇA FAIT — la liste EXHAUSTIVE des filtres produits :**

### `/ia/search` (page IA) — `FILTER_SCHEMA` (14 champs)
`tiers` (brulante/chaude/reserve_fonciere/a_creuser/ecartee) · `commune` / `communes` (24) · `statuts` (matrice, deprecated) · `scoreMin` · `surfaceMin` / `surfaceMax` · `sdpMin` · `veille` (bool) · `horsCopro` (bool) · `evenement` (bool) · `vueMer` (bool) · `flags` / `flagsExclus` (sol_pollue/abf/icpe/risques/prescription_plu).
→ **Ni zonage, ni propriétaire, ni DPE, ni viabilisation, ni risque détaillé, ni surface bâtie.**

### `/ia/segments-search` — registry `FILTERS` (37 filtres, par groupe)
- **Marché** : anciennete_mutation_mois, prix_mutation_eur, type_bien (Maison/Appartement/Dépendance/Local).
- **Bâti** : periode_construction (DPE), flag_amiante (pré-1997), emprise_batie_m2, ces_probable_pct.
- **Parcelle** : jardin_m2, communes, adresse_ban.
- **Terrain** : pente_moy_deg, pente_max_deg, pente_non_batie_deg.
- **Équipements** : piscine, pv_detecte.
- **Énergie** : score_solaire, facture_elec_estimee_eur, flag_topo_ombrage, pv_existant, repowering, flag_ombrage_vegetal.
- **Contexte** : proba_proprio_occupant, proprio_occupant_pct.
- **Végétation** : ombrage_vegetal, canopee_limite(+_pct), bati_voisin_limite, confiance_vegetation.
- **Réseaux** : zone_anc, proba_anc, source_anc (assainissement non collectif).
- **Réglementaire** : flag_abf, **zonage_plu (U/AU/A/N/hors)**, qpv.
- **Foncier bâti** : emprise_residuelle_m2, surelevation_possible.
- **Signaux** : catnat_recent.

**LIMITES** — **aucun des deux n'a de filtre « propriétaire personne morale / DGFiP / SIREN »** (le registry a `proprio_occupant_pct` = % occupants INSEE au carreau, ≠ identité DGFiP). `/ia/search` (la page visée) est **le plus pauvre** (14 champs, pas de zonage/DPE/PM). Aucun ne répond à une **question** (seulement des filtres).

---

## 2. LE DROP SILENCIEUX (3 requêtes réelles)

**CE QUE ÇA FAIT (`/ia/search`, sortie RÉELLE) :**

> **REQ 1** — *« les brûlantes de Saint-Pierre avec un propriétaire personne morale »*
> → `{"filters":{"commune":"Saint-Pierre","tiers":["brulante"]},"explanation":"Filtres proposés par l'IA (validés par schéma)."}`
> ➜ **« propriétaire personne morale » DROPPÉ EN SILENCE.** Aucun signalement. Le client lit « Filtres proposés » et **croit sa demande honorée** — il ignore que son critère principal n'est pas appliqué. **Faux positif de confiance.**

> **REQ 3 (pire qu'un drop)** — *« les passoires thermiques classées G à Saint-Denis »*
> → `{"filters":{"commune":"Saint-Denis","flags":["risques"]}}`
> ➜ **MISTRADUCTION SÉMANTIQUE** : « passoire thermique G » (DPE énergie) → `flags:["risques"]` (flag risque, **sans rapport**). Le schéma valide la clé/enum mais **PAS le sens** → un filtre faux mais « validé par schéma ». Le client obtient des parcelles à risque, pas des passoires. Plus grave qu'un drop.

**Contraste — `/ia/segments-search` REFUSE honnêtement :**
> **REQ 2** — *« maisons avec grand jardin détenues par une personne morale »*
> → `{"out_of_scope":"La nature du propriétaire (personne physique vs morale) n'existe pas dans le registry LA BUSE.","message":"Je ne peux filtrer que sur : Marché, Bâti, Parcelle, Terrain, Équipements, Énergie, Contexte, Végétation, Réseaux, Réglementaire, Foncier bâti, Signaux."}`
> ➜ Refus explicite + **liste de ce qu'il SAIT filtrer**. Honnête. MAIS : all-or-nothing — il refuse la requête ENTIÈRE (perd aussi le « grand jardin » pourtant supporté) au lieu d'appliquer le filtrable et signaler le reste.

**LIMITES** — `/ia/search` (page IA) : **drop silencieux + mistraduction sémantique non détectée par le schéma**. `nl_segments` a un mécanisme `rejetes` (`valider_filtres` liste les clés rejetées) mais ici le modèle choisit `out_of_scope` sur la requête entière → le partiel valide-avec-signalement n'existe nulle part.

---

## 3. LES QUESTIONS AGRÉGÉES

**CE QUE ÇA FAIT (`/ia/search`, réel) :**
> *« quelle commune a le plus de brûlantes ? »* → `{"out_of_scope":"Cette question demande une analyse statistique globale, pas une recherche filtrable. Utilisez l'interface de visualisation pour comparer les communes."}` — **refus**.
> *« combien de chaudes à Saint-Pierre ? »* → `{"filters":{"commune":"Saint-Pierre","tiers":["chaude"]}}` — **converti en filtre**, PAS un compte. Le client demande un nombre, obtient une liste filtrée.

**LA DONNÉE EXISTE — un simple SQL suffirait** (run servi q_v6_m8) :
```
brûlantes par commune : Saint-Paul 28, Saint-Pierre 12, Saint-Leu 9, Saint-Denis 9, Saint-Benoît 8…
```
Donc « quelle commune a le plus de brûlantes ? » = **Saint-Paul (28)**, réponse triviale non fournie.

**Questions agrégées réalistes qu'un client poserait (toutes répondables par SQL, aucune répondue aujourd'hui) :**
- « quelle commune a le plus de brûlantes / de foncier mobilisable ? » (GROUP BY tier)
- « combien de chaudes à Saint-Pierre ? » (COUNT)
- « quelle est la surface moyenne des opportunités à Saint-Paul ? » (AVG)
- « combien de parcelles détenues par une personne morale à Saint-Denis ? » (JOIN parcelle_personne_morale)
- « combien de terrains > 1000 m² en zone U non bâtis ? »
- « répartition des brûlantes par tranche de SDP résiduelle »

**LIMITES** — aucune question agrégée n'est répondue : soit `out_of_scope`, soit convertie en filtre. Le traducteur ne SAIT que filtrer, jamais compter/agréger/classer, alors que la base le permet trivialement.

---

## 4. LES DONNÉES FILTRABLES RÉELLES (l'écart demande↔donnée)

**CE QUI EXISTE en base (requêtable) vs exposé par le traducteur :**
| Donnée | En base ? | Exposée `/ia/search` ? | Exposée segments ? |
|---|---|---|---|
| **Propriétaire personne morale (DGFiP)** | **OUI — `parcelle_personne_morale` : 82 701 parcelles, 12 605 SIREN, groupe_label 100 %** | ❌ **NON** | ❌ NON (juste % occupants INSEE) |
| Surface parcelle | OUI (`parcels.surface_m2`, 431 663) | ✅ surfaceMin/Max | ✅ (jardin/emprise) |
| Zonage PLU (U/AU/A/N + libellé) | OUI (`parcel_zone_plu` 427 419 ; `spatial_layers`) | ❌ NON | ✅ zonage_plu |
| DPE / passoire thermique | OUI (couche DPE, periode_construction) | ❌ NON (→ mistraduit en « risques ») | ✅ periode_construction |
| Risque (PPR/aléa) | OUI | ⚠ flag « risques » grossier | ✅ catnat_recent, + cascade |
| Viabilisation M-VIA | OUI (`parcel_viabilisation`) | ❌ NON | ⚠ partiel (ANC) |
| Score V / veille succession | OUI (`parcel_v_score`) | ⚠ `veille` bool | ❌ |

**LIMITES** — **l'écart le plus criant = le propriétaire personne morale** : 82 701 parcelles portent une PM identifiée (SIREN + groupe), donnée centrale pour un prospecteur (« qui possède ? »), **totalement absente des deux traducteurs** alors qu'elle est en base et jointe. Idem le zonage : filtrable en base (427k) mais absent de la page IA. Le traducteur expose **beaucoup moins** que ce que la donnée permet.

---

## 5. LE SOCLE

**CE QUI EXISTE** — après le rebranchement §0, les deux traducteurs passent par le **client unique** `core.complete` :
- `/ia/search` : `ia.py:314` → `core.complete(kind="search", model=MODEL_FACTUAL, …)`.
- `nl_segments` : `nl_segments.py:181` → `core.complete(kind="segments-search", …)`.
→ clé, routeur modèle, timeout/retries, repli `degraded` flaggé, log de coût = mutualisés.

**CE QUE ÇA NE FAIT PAS (encore)** — la recherche NL **n'utilise PAS** le grounding (`build_context`) ni la validation de sortie (`validate=True`, `validate_output`) du socle. Raison : elle produit des **FILTRES JSON** (validés par `FILTER_SCHEMA` / le registry), pas de la **prose sourcée**. Le grounding/validation du socle est conçu pour des réponses en prose (Surface A) — il ne s'applique pas à la traduction en filtres.

**LIMITES / ce qui serait réutilisable** — pour une future **réponse agrégée** (« quelle commune… » → un nombre), le socle **serait** réutilisable : construire un contexte autorisé à partir d'un résultat SQL (déjà calculé), et faire formuler la réponse en prose **sourcée + validée** (couche chiffres du socle = garantie qu'aucun nombre inventé). Le socle couvre donc déjà le « répondre sans halluciner » ; il manque la brique « traduire une question agrégée → SQL déterministe → contexte ». La validation sémantique des filtres (le cas « passoire → risques ») n'est PAS couverte par le socle (schéma ≠ sens).

---

## Synthèse des limites (sans reco)
1. **Deux traducteurs au comportement opposé** : `/ia/search` (page IA) droppe en silence ; `nl_segments` refuse honnêtement mais en tout-ou-rien.
2. **Drop silencieux + mistraduction sémantique** sur `/ia/search` : critère non supporté disparu sans signal (personne morale), ou traduit en un filtre faux mais « validé par schéma » (passoire → risques).
3. **Aucune question agrégée répondue**, alors que la base le permet trivialement (SQL).
4. **Écart donnée↔filtre majeur** : le propriétaire personne morale (82 701 parcelles) et le zonage (427k) sont en base mais absents de la page IA.
5. **Socle** : client mutualisé oui ; grounding/validation non utilisés (filtres ≠ prose) — mais réutilisables pour des réponses agrégées sourcées.

*Aucune reco, aucune modif. Fin de l'audit.*
