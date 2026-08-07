# M49 — BILAN · API & IA complètes

**Branche** `m49-api-ia-completes` (pas de merge). Golden **117/117** · tsc vert · **0 tier** ·
re-mesures M34/M35 & SHA256 M37 intacts (aucun code scoring/vigilance touché).

---

## LOT A — Passe helper-tracing des routes (déférée de M31)

**Méthode** : traçage par helper (pas de cross-référence textuelle — la méthode jugée non fiable
en M31). Chaque route résolue à un caller réel (`file:line`) ou prouvée sans caller par recherche
repo-wide (frontend/src + api.ts + qa + scripts + backend-internal). **205 routes** (app.py + 31
routeurs) tracées via 4 passes parallèles. Inventaire machine : `routes_inventaire.csv.gz`.

**Statuts** : VIVANTE (~120, caller prouvé) · EXTERNE-PAR-CONCEPTION (~25 : webhooks Stripe, liens
email, `/api/v1/*` partenaire, `/p/{token}`, health/login, OG — caller-less VOULU, M31 les protégeait) ·
MORTE · DOUTEUSE.

**6 routes MORTES prouvées RETIRÉES** (un commit par retrait, preuve dans le message) :

| Route | Fichier | Preuve |
|---|---|---|
| `GET /operations` + `GET /operations/{siren}/{secteur}` | routeur `operations.py` (supprimé) | O11 « Vérif procédure » appelle `/modules/verif-procedure/{idu}`, PAS ce routeur ; 0 hit repo-wide |
| `GET /rapport-potentiel/{idu}.pdf` | `potentiel.py` (supprimé) | 0 hit ; la fiche lie argumentaire/lettre-zonage/dossier/banquier, jamais celui-ci |
| `GET /tension-fonciere` | `tension.py` (supprimé) | mount déjà « MASQUÉ » ; 0 caller |
| `GET /signals` | `app.py` | vestige offre C (`filters.ts`) ; 0 caller ; 2 tests retirés |
| `DELETE /partners/share/token/{token}` | `partners.py` | `share_revoke` — aucun helper, 0 hit `share/token` |

Tests des routeurs supprimés retirés (`test_operations/potentiel/tension.py` — ne testaient que la
logique de ces surfaces mortes, aucun importeur LIVE hors tests).

**Le reste — arbitrage Vic appliqué** (règle du mandat + leçon pre_pond « aucun retrait sans preuve
de non-usage » ; « une route morte qui dort ne coûte rien, un retrait est irréversible pour un
partenaire inconnu ») :
- **~13 MORTES candidates NON retirées** (vestiges superseded : `/compare`, `/shortlist`,
  `/assemblages`+`/study`, `/courrier/statut|envois`, `/dossier/statut`, `/events/reprise`,
  `/parcels/{idu}/enrichment|explain|spf-letter`, `/map/permits.geojson`) — **listées** au tableau,
  retrait au cas par cas dans un geste futur AVEC preuve individuelle. **Exception « menteuse »
  (chiffre périmé, famille M48) vérifiée : AUCUNE ne s'applique** — elles sont MORTES (0 caller),
  donc ne servent aucun chiffre à personne (rien à mentir).
- **~30 DOUTEUSES admin/ops GARDÉES** (`/bilan/params`, `/parcels/{idu}/evaluate`, `/audit/*`,
  `/watch-zones`, `/alertes`, `/filters`, `/coverage`, `/demo*`, `/sources/{id}/test`, `/stats`,
  `/parcels`) — outils d'opérateur (joignables curl), **NON touchées** (confirmé Vic).
- **5 helpers api.ts orphelins RETIRÉS** (arbitrage Vic : retirer le HELPER, pas la route) :
  `iaSynthese`, `iaPourquoi`, `runMatch`, `matchCompatibilite`, `listShares` — 0 importeur vérifié,
  code mort front, tsc vert. Les routes serveur restent listées « douteuses ».

## LOT B — L'assistant IA couvre les écartées

**Constat live (6 cas, avant)** — l'IA ne montrait PAS tout : elle **refusait** sur une bâti-saturé
(« information non disponible »), disait « motif non disponible » sur une zone fermée, ignorait le
registre (piscine) et le segment Renouvellement. Cause : le contexte IA ne portait que
`motif_exclusion` (HARD_EXCLUDE) — rien pour les déclassées/registre/segment.

**Correctif** (`fiche_ask._ask_context`) — version conversationnelle du « Pourquoi pas ? » :
`motif_classement` (verdict_servi.motif : registre motif_client / bâti-saturé fb_motif, OU motif
STRUCTUREL par tier), `classement_registre`, `vigilances` (SOFT_FLAG hors RGPD), `segment_
renouvellement`, `mode_b_rehabilitation`. Whitelist/grounding inchangés.

**Après (transcriptions `constat_ia.tar.gz`)** — l'IA cite le motif EXACT :

| Cas | Avant | Après |
|---|---|---|
| écartée PPR (BP0477) | ✅ déjà | « bâtie 100 % + zone rouge PPR inconstructible » |
| **déclassée bâti saturé (AD0573)** | ❌ « non disponible » | « bâtie 15-40 %, bâti d'année absente, non divisible » |
| **déclassée zone fermée (AD0016)** | ⚠️ « motif non disponible » | « zone fermée à l'urbanisation » |
| **registre piscine (AK1442)** | ❌ « pas de motif » | « piscine détectée sur imagerie 2025 » |
| **Renouvellement (AZ0004)** | ⚠️ segment ignoré | « écartée… mais potentiel de renouvellement urbain » |
| RNU (AE0003) | ✅ | « à creuser, rang… » |

**Tests de non-régression** : `tests/test_ia_ecartees.py` (6, un par cas : motif bâti-saturé,
structurel zone fermée, registre, segment Renouvellement, mode B, vigilances hors-RGPD).

## LOT C — La phrase de cadrage IA — DÉJÀ EN PLACE (constaté sur pièces)

**Rien à ajouter** : la phrase verbatim existe déjà depuis **EXPRESS-01 · Volet B**, source unique,
sur TOUTES les surfaces IA :
- Front : `CLIENT.avisIa` (au mot près) rendu par `<AvisIA>` → AskBar (fiche), CopiloteView, IAStub,
  ProjetEntretien, faisabilité, traducteur. Placement discret, non repliable, avant toute interaction.
- Exports (« reprise si pertinent ») : jumelle Python `AVIS_IA` (`ai/avis.py`) utilisée dans
  `export.py` (md `> {AVIS_IA}` + HTML **seulement si faits IA**) et `banquier.py` (si `ai_used`).

*(J'avais commencé un encart — puis constaté le doublon et l'ai retiré : « constater avant présumer ».)*
Captures de l'existant : `captures/cadrage_askbar.png`, `captures/cadrage_copilote.png`.

## VÉRIFICATION

| Gate | Résultat |
|---|---|
| **Golden** | **117/117** (0 FAIL) |
| **0 tier modifié** | oui — Lot A retire des routes mortes, Lot B enrichit le contexte IA (grounding inchangé) ; aucun scoring touché |
| re-mesures M34/M35 · SHA256 M37 | intacts |
| tsc | vert |
| tests | 58 ciblés verts + `test_ia_ecartees` 6/6 + `test_api` /signals ajusté 2/2 |
| **route morte retirée (avant/après)** | 6 routes, un commit chacun, preuve au message |
| Captures | phrase de cadrage (2) · mention/segment IA transcriptions (6) |

## Actif rejouable
`routes_inventaire.csv.gz` = **le tableau complet 205 routes × statut × preuve**, consigné comme
actif (comme la grille M48) — resservira à chaque passe API/release : rejouer les 4 traçages,
diff le CSV, tout nouveau MORTE se voit.

## Reste (à ta main)
- **Bundle front** : `npm run build` au déploiement (embarque Lot B + le retrait des 5 helpers
  morts ; aucun changement Lot C).
- Retrait des ~13 MORTES candidates : au cas par cas, dans un futur mandat qui les croise (pas en bloc).

## Annexes
- `routes_inventaire.csv.gz` — table complète routes × statut × preuve (actionnables + résumé).
- `constat_ia.tar.gz` / `constat_ia/` — transcriptions IA avant/après, 6 cas.
- `captures/` — cadrage IA (AskBar, Copilote).
- Scripts : `capture_cadrage.mjs`.
