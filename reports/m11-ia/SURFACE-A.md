# M11 · SURFACE A — Recherche IA par fiche (livré, `feat/m11-surface-a`, PAS de merge)

**Date** : 2026-07-15. Sur le socle §0 (mergé main). Décisions Vic respectées. Aucun merge, aucune touche scoring.

Le geste : **une barre premium en haut de fiche** — le client tape une question libre sur LA parcelle, l'IA répond en clair, **sourcé**, à partir des seules données autorisées. Remplace les 2 boutons cassés (`/ia/synthese`, `/ia/pourquoi`).

---

## 1. L'endpoint conversationnel — `POST /parcels/{idu}/ask`

`src/labuse/api/fiche_ask.py` (nouveau). Contrat :
- **Entrée** : `{"question": "<libre>"}` sur l'IDU ouvert.
- **Flux** : cache `(idu, run, question)` → quota → **contexte autorisé** (liste blanche) → routeur modèle → `core.complete(validate=True, require_sources=True)` → cache.
- **Sortie** : `{texte, sources[], deeplinks{}, provenance{}, model, absent?, cached?, quota_atteint?, rejected?}`.

**Requête réelle (live) :**
> `POST /parcels/97423000AB1908/ask {"question":"Combien je peux construire ?"}`
> → model `claude-sonnet-4-6` · **texte** : « La surface de plancher résiduelle estimée est de 183 m², sur une parcelle de 313 m²… gabarit R+2, 1 à 3 logements. Ces chiffres sont des estimations… la zone PLU réelle n'est pas disponible et devra être confirmée. »
> → **sources** (avec provenance) : `Estimé · moteur faisabilité`, `Estimé · potentiel de transformation`, `Sourcé · cadastre`, **`Absent · zonage PLU`**. (voir capture `02-reponse-sourcee.png`)

Chaque affirmation est ancrée (`⟨src:…⟩` validés par le socle) ; chaque chiffre vient du contexte ; les champs nuls sont dits « non disponibles ». **L'IA n'invente rien.**

## 2. Catalogue de champs autorisés (liste blanche, `_ask_context`)
Fiche **premium** (`_q_v2_fiche`) + agrégation **faisabilité** (legacy). Tout champ hors catalogue = **jamais** envoyé au modèle.
| Bloc | Champs (clé → provenance) |
|---|---|
| Identité/zonage | idu, commune, surface_m2 (SOURCE) · zone_plu, zone_plu_libelle, reglement_regles (SOURCE) · statut_tier (SOURCE) |
| Viabilisation M-VIA | eau, assainissement, élec, indice, coût raccordement (SOURCE/ABSENT selon dispo) |
| Risques | risques (extrait des lignes cascade PPR/aléa, SOURCE) |
| Potentiel transformation | potentiel_niveau, sdp_residuelle_m2, pct_consomme, sous_densite (**ESTIME**) |
| ICD / score P | icd_bande, icd_manquants (SOURCE, lecture seule) |
| DVF | prix_m2_bati, dernière mutation (SOURCE) |
| Motif d'exclusion | motif_exclusion (lignes HARD_EXCLUDE, SOURCE) |
| Faisabilité (legacy) | niveaux, hauteur, SDP, logements, charge foncière, fiabilité (**ESTIME**) |

Chaque champ nul → provenance **ABSENT** → l'IA dit « non disponible ». Deep-link règlement PLU exposé pour l'étiquette « Sourcé · règlement PLU ↗ ».

## 3. Décisions Vic appliquées
- **Fiche = premium + faisabilité** ✅ (catalogue ci-dessus).
- **Quota = 20 / fiche / jour / sujet** ✅ (table `ia_ask_quota`) — le **hit cache ne décompte pas** (testé). Au-delà : message poli, **pas d'appel IA**.
- **Modèle = haiku par défaut, sonnet UNIQUEMENT faisabilité** ✅ — un seul point de décision (`_choose_model`, regex `combien|construi|sdp|faisabilit|rentab|charge fonci|logement|bilan|…`). Testé : « risque inondation » → haiku, « combien construire » → sonnet.
- **Validation = celle du socle** ✅ (hybride 1+3, jamais réimplémentée).

## 4. La barre (front) — `frontend/src/components/fiche/AskBar.tsx`
Conforme maquette §1.4 (validée à l'œil, captures) :
- Accent **premium violet** `#B497F0` (bordure + badge PREMIUM).
- Champ libre + Entrée, bouton « Demander ».
- **Chips** contextuelles (zonage, combien construire, assainissement, risque inondation, pourquoi ce statut).
- **Provenance visible** : `Sourcé` (vert) + deep-link, `Estimé` (ambre), `Absent` (gris) → « cette information n'est pas disponible ».
- **État de chargement honnête** (« L'IA lit la fiche… »), pas de silent-fail. Message **quota atteint** clair.

---

## 5. STOP — preuves pour Vic

**(1) Endpoint + réponse sourcée** : §1 ci-dessus (live, sonnet, 183 m² sourcé, provenance Sourcé/Estimé/Absent).

**(2) Test anti-hallucination « amiante → Absent »** ✅ — `tests/test_fiche_ask.py::test_amiante_hors_donnees_renvoie_absent` (vert) **et** live :
> `{"question":"Y a-t-il de l'amiante ?"}` → « Cette information n'est pas disponible de façon sourcée pour cette parcelle. » (`absent:true`, `rejected:true`) — **jamais** d'invention. (capture `03-reponse-absent.png`)

**(3) Captures** (`reports/m11-ia/captures/`) : `01-barre-vide`, **`02-reponse-sourcee`** (réponse + étiquettes provenance), **`03-reponse-absent`** (amiante → non disponible), **`04-quota-atteint`**.

**(4) Quota + cache** ✅ (tests + live) :
- `test_quota_21e_refusee_sans_appel` : la 21ᵉ → `quota_atteint`, **0 appel modèle**.
- `test_hit_cache_ne_decompte_pas_le_quota` : hit cache → compteur inchangé.
- `test_cache_question_repetee_zero_appel` : même question (normalisée casse/espaces) → `cached:true`, **1 seul appel modèle**.

**(5) Zéro touche scoring** ✅ — `git status` : `fiche_ask.py` (neuf), `AskBar.tsx` (neuf), `app.py` (1 ligne : include_router), `Fiche.tsx`/`api.ts` (barre), tests. **Aucun** fichier scoring/cascade/étage 0/run servi.

**Coût** (parcours type) : N questions distinctes = N appels ; questions répétées = **0 appel** (cache) ; sur clic uniquement (jamais auto à l'ouverture). Le routeur réserve sonnet à la faisabilité.

**Non-régression** : `/explain` + appels socle inchangés ; 35 tests verts (core+fiche_ask+assistant). Les anciens `/ia/synthese`,`/ia/pourquoi` restent 200 (socle) mais la fiche appelle désormais `/ask`.

---

## Reste / notes
- Les anciens boutons `/ia/synthese`,`/ia/pourquoi` : laissés inertes (dépréciés) — la fiche pointe sur `/ask`. À retirer dans un nettoyage ultérieur.
- Rendu markdown de la réponse : le texte peut contenir des `**gras**` non rendus (affiché en `whitespace-pre-wrap`) — cosmétique, à polir si besoin.
- Le front `dist/` est un artefact de build (gitignoré) ; la source `AskBar.tsx` est committée, le bundle se reconstruit au déploiement.

Commit sur `feat/m11-surface-a`, **PAS de merge**. Captures dans `reports/m11-ia/captures/`.
