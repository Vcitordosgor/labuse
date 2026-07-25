# M20 — LOT C : parité Dossier / PDF Flash

**Branche** `fix/m20-c-parite-dossier`. Non poussée pour merge (CC ne merge pas).

## C1 — Audit (état à l'arrivée sur `main`)

**Découverte clé** : Dossier et Flash **partagent le même moteur** — `collect_report_data()` + le template
`src/labuse/flash/templates/rapport.html.j2` + `render_report_html()`. Le Dossier (`/dossier/{idu}.pdf`,
`src/labuse/api/dossier.py`) appelle `render_report_html(...)` avec `produit="Dossier parcelle"` et **ajoute une
mention** en pied ; c'est la seule divergence de code. **Il n'existe donc aucune divergence de contenu Flash↔Dossier
par construction** : tout ce que reçoit l'acheteur Flash, l'abonné le reçoit.

**Mais** : l'enrichissement M18-D (section 07 « Contexte commune & leviers » + solaire PVGIS + biais vélocité/ZAN)
n'était **PAS sur `main`** — il vivait sur `feat/m18-d-pdf-flash-enrichi` (commits `1d8386f` + `69304e7`,
non mergés, « VALIDÉ Vic »). Sur `main`, `parcel_solar` n'était jamais requêté (bloc solaire = code mort du
template) et la section 07 était encore « Terrain & réseaux » nu. **Ni Flash ni Dossier n'avaient l'enrichissement.**

## C2 — Alignement

Le moteur étant commun, enrichir le moteur = donner la parité aux DEUX d'un coup. J'ai **repris (cherry-pick) les
deux commits M18-D** (uniquement le code : `flash/data.py` + `rapport.html.j2`) sur la branche C. Résultat prouvé
sur parcelle réelle **97418000AT2317** (Sainte-Marie) — `qa/m20/c/dossier_AT2317.pdf` + `dossier_section07.png` :

| Section | Flash | Dossier | Écart |
|---|:---:|:---:|---|
| Page de garde | ✓ | ✓ | produit/sous-titre (paramètre) |
| 01 Identité parcellaire | ✓ | ✓ | — |
| 02 Constructibilité | ✓ | ✓ | — |
| 03 Risques | ✓ | ✓ | — |
| 04 Patrimoine & environnement | ✓ | ✓ | — |
| 05 Marché (DVF anonymisé) | ✓ | ✓ | — |
| 06 Dynamique locale (Sitadel) | ✓ | ✓ | — |
| **07 Contexte commune & leviers** (vélocité PC, SRU/bailleur, QPV/TVA, conso ENAF) | ✓ | ✓ | **aligné** (était unmerged) |
| **08 Terrain & réseaux — Gisement solaire PVGIS** | ✓ | ✓ | **aligné** (était code mort) |
| 09 Sources & millésimes | ✓ | ✓ | — |
| Caveats honnêtes : « permis accordés seulement » · ZAN non territorialisé · gradient côtier solaire | ✓ | ✓ | **suivent dans le Dossier** |
| Page tarifaire | ✗ | ✗ | **intentionnel** (absente des deux) |
| Mention « Généré via LABUSE pour [raison sociale] » | ✗ | ✓ | **intentionnel** (Dossier only) |

Preuve automatisée (probes sur le HTML rendu par le moteur partagé) : les 8 marqueurs (Contexte commune, permis
accordés, SRU, QPV, ENAF, Gisement solaire, gradient côtier, millésime) sont **présents dans Flash ET dans le
Dossier** ; « Généré via LABUSE » **présent dans le Dossier seul** (différence voulue). Données réelles :
vélocité PC ~9 mois (caveat), SRU 28,7 % (objectif 20 %), solaire 1500 kWh/kWc (score 74, caveat côtier).

**Tables requises présentes en base** : `parcel_solar` (431 663), `commune_conso_enaf` (24/24),
`m10_permit_delais` (50 290), `commune_contexte_sru` (24/24) — les garde-fous `if table in avail` dégradent
proprement si une table manque en prod.

## C3 — Quota Dossier (RAPPORT SEUL, aucune décision)

Le quota **est câblé et actif** (`src/labuse/api/dossier.py`) :
- config `dossier_quota_mois = 20` (`config.py`) ;
- accès `plans.acces("dossier_parcelle")` = **Essentiel** — mais **stub « toujours vrai aujourd'hui »** (la porte
  de plan ne bloque encore personne) ;
- si `!plans.acces("dossier_illimite")` (Intégral) et `utilises_mois >= 20` → **HTTP 429** ;
- compteur **incrémenté** dans `usage_compteurs` à chaque génération ; `/dossier/statut` expose restants.

**Résumé** : le mécanisme de quota (comptage + plafond + 429) est opérationnel ; seule la **porte d'accès par plan
est un stub** (tout le monde passe aujourd'hui). Activer/ajuster le quota et la porte = **décision Vic** (politique
commerciale) — hors périmètre M20.

## Non-régression
`golden 116/116` (`LABUSE_DEV_MODE=1`) · import-smoke `flash.data`/`flash.report` OK. Modèle P non touché.
Zéro identité de personne physique (comparables DVF anonymisés, aucune donnée nominative — inchangé).
