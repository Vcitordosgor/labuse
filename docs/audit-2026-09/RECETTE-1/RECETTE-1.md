# RECETTE-1 — retours de recette de Vic (4 oct.) — rapport

Branche `fix/recette-1` (base `origin/main` = `3e3a2afa`, après merge ORACLE-FIX-1) · worktree
`~/Desktop/labuse-recette1` · API 8695 / front 5895 · Opus · 1 session.

**Règle du run** : aucun run, aucune bascule. Toute valeur affichée qui change est consignée dans
`CHANGEMENTS.csv` avec la colonne **touche le run (oui/non)**. Le run q_v16 est un geste de Vic.

## État de départ (Étape 0)
- `pwd` = worktree · branche `fix/recette-1` · `git status` propre (hors `docs/.../RECETTE-1/`).
- base = `origin/main` du jour, contient le merge ORACLE-FIX-1 (`d5c90ea9`, `3e70a6b8`).
- `.env` copié depuis `~/Desktop/labuse/.env` ; base réelle île `labuse` (431 663 parcelles) pour
  les témoins/oracles ; base de test isolée pour pytest.
- **Python** : l'env conda `labusedb` n'a pas de binaire python ; on utilise `~/Desktop/labuse/.venv`
  avec `PYTHONPATH=src` (résout bien le code du worktree) + `PROJ_DATA` de l'env conda.
- **5 oracles (baseline)** : `50 vrai · 0 faux · 90 non vérifiable` (API 8695, le reste des
  témoins est non vérifiable quand l'API externe — Géorisques/IGN/BAN/RNB — ne répond pas). **0 faux
  = point de départ à préserver.** (⚠ la forme `LABUSE_ORACLE_API=:8695` donne une URL malformée ;
  utiliser l'URL complète `http://127.0.0.1:8695`.)
- **pytest faisabilité** (base réelle via `LABUSE_AUDIT_DATABASE_URL`) : 2 échecs PRÉ-EXISTANTS
  (`test_u1pru_stationnement_exempte_non_borne`, `test_plafond_densite_borne_les_zones_denses`) —
  confirmés rouges sur la base, avant toute modification (cf. CALCULS-FIX-1). Hors périmètre.
- **V6b** (banc de cohérence île, long) : à rejouer en fin de mandat (job nocturne).

---

## Lot A — ce qui peut toucher le run

### A1 · Faisabilité — verdict « terrain trop exigu » sur de grandes parcelles — ✅ FAIT
**Diagnostic (prouvé à la volée, 0 run).**
1. Le test « cercle inscrit » sur la géométrie ENTIÈRE de la parcelle est trompeur : la plupart des
   grandes parcelles `terrain_exigu` sont **à cheval** (zone dominante A/N + mince portion U/AU) ou
   couvertes par un **PPR zone rouge** / un **emplacement réservé**. L'assiette calculée est la
   portion U/AU clippée, pas la parcelle entière → le 0 m² est souvent **substantiellement correct**.
2. Mesure île (échantillon 400 parcelles `terrain_exigu` > 800 m², clip U/AU puis cercle inscrit de
   la portion) : 295 portion U/AU < 50 m² (légitime), 82 portion large (candidats « faux »), 23
   étroites (légitime).
3. Les 82 « candidats » examinés un par un : tous dissous — PPR INTERDICTION ~100 % (ex.
   `97415000BN1169`, U1b 19 047 m², 100 % PPR rouge), ER ~100 % (ex. `97401000AI0016`, Ud 5 345 m²,
   100 % « ER logements/mixité »), ou petites parcelles/slivers où les **reculs par côté du gabarit**
   (voie ~6 m + limites 3 m, bien plus qu'un inset uniforme de 3 m) vident légitimement l'assiette.
4. **La vraie cause (bug de Vic)** : le message « Terrain trop exigu compte tenu des reculs (4 m) »
   était affiché dès que l'emprise se vidait, **quelle que soit la raison** — y compris un PPR rouge
   ou un ER couvrant 19 000 m². Le chiffre (0 m²) est juste ; le **message** était faux.
   (Le bug de CAPACITÉ structurel — clip `name` vs `subtype` sur zones AU numérotées — avait déjà été
   corrigé par EXIGU-GRANDES ; c'est pourquoi le code courant donne des aires non nulles là où le run
   servi, antérieur, affiche encore `terrain_exigu`.)

**Correctif (run-safe).** `parcel_faisabilite` mesure désormais la **raison réelle** du vidage
(`extras['assiette_vide']`), passée au moteur. `estimate_capacity` choisit le message et pose
`Faisabilite.exigu_raison` ∈ {`reculs`, `ppr_rouge`, `emplacement_reserve`, `ebc`, `contraintes`,
`portion_reduite`}. Le `cause` reste `terrain_exigu` et la capacité reste 0 → **AUCUNE valeur du run
ne change** (SDP identique). `scenarios._cause_limite` suit la même raison pour « ce qui limite ».

**Témoins (après correctif).**
| idu | zone | surf | raison | message |
|---|---|---|---|---|
| 97415000BN1169 | U1b | 19 047 | `ppr_rouge` | « Parcelle couverte par le PPR en zone rouge… » |
| 97401000AI0016 | Ud | 5 345 | `emplacement_reserve` | « Emplacement réservé couvrant la parcelle… » |
| 97415000AS0941 | N | 1 625 | `portion_reduite` | « Portion constructible U/AU trop réduite… » |
| 97407000AK1335 | Uc | 167 | `reculs` | « Terrain trop exigu compte tenu des reculs (4 m)… » |

**Portée (échantillon 200 `terrain_exigu`, code courant)** : `reculs` 67 % (message déjà juste),
`ppr_rouge` 14 %, `portion_reduite` 14 %, `emplacement_reserve` 4 %, `contraintes` 1 % → **~33 %**
(≈ 20 600 parcelles île) recevaient un message trompeur « reculs », désormais exact.
**Touche le run : NON** (capacité et `cause` inchangés ; seul le libellé/`exigu_raison` est servi en
direct par le moteur). Verrou : `tests/test_recette1_a1.py` (5 tests verts, dont 4 témoins base réelle).

### A2 · Gabarit — « Plafond d'emprise — non réglementé » en U1e Saint-Paul — ✅ FAIT (aucun correctif)
PLU de Saint-Paul (`97415_reglement_20251217`), chapitre **Zones U1e, U1l**, **Article 9 — Emprise au
sol des constructions : « Il n'est pas fixé de règle. »** Le règlement est **réellement muet** sur
l'emprise au sol en U1e. Le modèle (`maxFootprint status='absent'`, « non réglementé — silence du
règlement ») est **correct**. Ce n'est PAS le cas ORACLE-FIX-1 lot A (où une valeur existait et
manquait). Rien à corriger ; la recherche île sur la règle emprise n'est pas à relancer pour ce motif.
**Touche le run : NON.**

---

## Lots B → H — état
Voir le suivi point par point ci-dessous. Chaque point non traité dans cette session est marqué
`NON FAIT` avec motif, conformément à la règle « rien n'est oublié silencieusement ».

| Point | État | Note |
|---|---|---|
| A1 | ✅ FAIT | message/raison ciblés, run-safe, verrou |
| A2 | ✅ FAIT | règlement muet confirmé (Art. 9 U1e), aucun correctif |
| B (vitesse carte) | ⏳ À FAIRE | mesure avant/après + pistes cache/MVT |
| C1–C8 (couches/légende) | ⏳ À FAIRE | |
| D1–D7 (i, fiches, Copilote, Radar, Sources) | ⏳ À FAIRE | |
| E1–E4 (filtres) | ⏳ À FAIRE | |
| F1–F4 (règles outils) | ⏳ À FAIRE | |
| G + H1–H16 (outils) | ⏳ À FAIRE | |

> Captures de Vic : **5** présentes dans `captures-vic/` (le mandat en annonce ~20 ; les points se
> lisent sans elles, comme prévu). Signalé, non bloquant.
