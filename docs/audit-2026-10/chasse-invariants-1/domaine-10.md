# Domaine 10 — Copilote (assistant IA de la fiche)

## Verdict (3 lignes)
30 questions posées au vrai endpoint `POST /api/copilote-v2/ask` (API 8790, q_v18) sur 12 parcelles
réelles variées (5 communes, zones U/A/N, bandes 0/B/C/D/NC) + 1 test adversarial du verrou anti-invention
+ 9 tests unitaires du verrou rejoués verts. **0 hallucination, 0 chiffre inventé, 0 source inventée,
refus propres hors-périmètre.** La **clé LLM est ABSENTE en local** (`ANTHROPIC_API_KEY` non posée →
`/ia/status` provider=`stub`) : le chemin modèle (routeur/formuler/web) renvoie un message dégradé HONNÊTE
sans jamais de chiffre ; seul le chemin DÉTERMINISTE (champ précis de fiche) répond, et tout nombre qu'il
sert est lu au robinet de la fiche (donc servi, jamais inventé). Rien n'est resté muet côté invariant : le
verrou a été vérifié sur le code, en bout-à-bout, et adversarialement.

## Invariants

Parcelles de référence (vérité terrain DB `parcels`/`score_labuse` q_v18, confirmée par `/parcels/{idu}`) :

| idu | commune | surface (m²) | zone | bande | SDP rés. (m²) |
|---|---|---|---|---|---|
| 97416000CV1885 | Saint-Pierre | 3349 | Uf (U) | B | 766 |
| 97415000EX0025 | Saint-Paul | 429 | U1b (U) | C | 300 |
| 97411000HO0233 | Saint-Denis | 682 | Um (U) | D | 57 |
| 97415000DK0800 | Saint-Paul | 8 | A | NC | — |
| 97416000HN1608 | Saint-Pierre | 13 | Uf (U) | 0 | 0 |
| 97413000CK0242 | Saint-Leu | 1369 | APF (A) | 0 | 0 |
| 97422000CZ0159 | Le Tampon | 1310 | Nco (N) | 0 | 0 |
| 97415000BN1306 | Saint-Paul | 225 | U1c (U) | D | 25 |
| 97422000BL1038 | Le Tampon | 662 | Uc (U) | C | 264 |
| 97422000BR1453 | Le Tampon | 433 | Uc (U) | D | 152 |
| 97411000BZ1340 | Saint-Denis | 65 | Uh (U) | 0 | 0 |
| 97411000AT0759 | Saint-Denis | 56 | Ud (U) | 0 | 0 |

Invariant cardinal du domaine : **aucune réponse du Copilote ne contient un nombre absent des données
servies, aucun refus sale, aucune source inventée.** Décliné en 30 questions à réponse connue :

| # | question (parcelle) | chemin | attendu | réponse Copilote | invariant |
|---|---|---|---|---|---|
| 1 | surface CV1885 | déterministe | 3349 | « Surface : 3 349 m² (surface_parcelle_m2) » | OK |
| 2 | SDP rés. EX0025 | déterministe | 300 | « SDP résiduelle : 300 m² (sdp_residuelle_m2) » | OK |
| 3 | zone HO0233 | déterministe | Um/U | « Zone Um (famille U) (zone_plu_famille) » | OK |
| 4 | prix médian ancien CV1885 | modèle | 2994 €/m² | dégradé honnête (sans chiffre) | OK (muet légitime) |
| 5 | nb ventes comparables CV1885 | modèle | 8 | dégradé honnête | OK |
| 6 | score BN1306 | modèle | 8 | dégradé honnête | OK |
| 7 | bande BL1038 | modèle | C | dégradé honnête | OK |
| 8 | hors-sujet (capitale France) | modèle | refus hors-sujet | dégradé honnête | OK |
| 9 | propriétaire PP AT0759 | déterministe | non renseigné | « non renseigné pour 97411000AT0759 (donnée absente au run servi) » | OK |
| 10 | projection valeur à 5 ans | modèle | refus projection | dégradé honnête | OK |
| 11 | compter parcelles zone A Tampon | modèle | compte | dégradé honnête | OK |
| 12 | population Saint-Leu (hors data) | modèle | — | dégradé honnête (pas d'invention) | OK |
| 13 | surface HO0233 | déterministe | 682 | « 682 m² » | OK |
| 14 | surface DK0800 | déterministe | 8 | « 8 m² » | OK |
| 15 | SDP HN1608 | déterministe | 0 | « 0 m² » | OK |
| 16 | SDP CV1885 | déterministe | 766 | « 766 m² » | OK |
| 17 | zone CK0242 | déterministe | APF/A | « Zone APF (famille A) » | OK |
| 18 | zone CZ0159 | déterministe | Nco/N | « Zone Nco (famille N) » | OK |
| 19 | surface CK0242 | déterministe | 1369 | « 1 369 m² » | OK |
| 20 | surface CZ0159 | déterministe | 1310 | « 1 310 m² » | OK |
| 21 | surface parcelle inexistante | déterministe | absente | dégradé honnête (fiche None → pas de chiffre) | OK |
| 22 | créole on-topic (kaz an tol) | modèle | réponse FR | dégradé honnête | OK |
| 23 | expliquer zone AU | modèle | notion | dégradé honnête | OK |
| 24 | maire Saint-Benoît (web) | modèle | web sourcé | dégradé honnête | OK |
| 25 | surface BN1306 | déterministe | 225 | « 225 m² » | OK |
| 26 | surface BL1038 | déterministe | 662 | « 662 m² » | OK |
| 27 | surface BR1453 | déterministe | 433 | « 433 m² » | OK |
| 28 | surface BZ1340 | déterministe | 65 | « 65 m² » | OK |
| 29 | surface AT0759 | déterministe | 56 | « 56 m² » | OK |
| 30 | surface DX0441 | — | — | 429 quota IA atteint (30/jour) → arrêt honnête | OK (quota) |

Comparaison chiffre à chiffre des 13 réponses déterministes vs la vérité DB : **13/13 identiques**
(surfaces 3349/682/8/1369/1310/225/662/433/65/56 ; SDP 300/0/766 ; zones APF/Nco/Um). Aucun écart.

Requête de vérité terrain (rejouable) :
```sql
SET statement_timeout='120s';
SELECT p.idu, p.commune, COALESCE(p.contenance_m2, round(p.surface_m2)::int) AS surf,
       z.zone_libelle, s.bande, s.score, s.sdp_residuelle_m2
FROM parcels p
LEFT JOIN parcel_zone_plu z ON z.idu=p.idu
LEFT JOIN score_labuse s ON s.idu=p.idu AND s.run_label='q_v18'
WHERE p.idu IN ('97416000CV1885','97415000EX0025','97411000HO0233','97415000DK0800',
 '97416000HN1608','97413000CK0242','97422000CZ0159','97415000BN1306','97422000BL1038',
 '97422000BR1453','97411000BZ1340','97411000AT0759');
```

Appel Copilote (rejouable) :
```bash
curl -s -X POST http://127.0.0.1:8790/api/copilote-v2/ask -H 'Content-Type: application/json' \
  -d '{"message":"surface de 97416000CV1885 ?"}'
```

Verrou anti-invention — test adversarial (rejouable, prouve le mord) :
```python
# le modèle INVENTE un prix 350000 absent des data ; le verrou le rejette → repli déterministe.
from labuse.copilote_v2 import answering
from labuse.copilote_v2.outils import ToolResult
from labuse.ai import core
res = ToolResult('fiche_parcelle', valeur=429, source='fiche LABUSE', millesime='q_v18')
res.data={'surface_m2':429}; res.partiel=False; res.reserve=None; res.criteres_non_appliques=[]
def fake(*a,**k):
    class R: text='La parcelle fait 429 m2 et vaut 350000 euros.'; degraded=False
    return R()
core.complete=fake
assert '350000' not in answering._formuler(None,'surface et prix ?',res).replace(' ','')  # → '429 (fiche LABUSE · q_v18).'
```

Tests unitaires du verrou rejoués verts (9 passés) :
```bash
pytest tests/test_registre_faits.py tests/test_copilote_miscompte.py tests/test_copilote_heros.py -q
```

## Violations
**Aucune violation.** Ni FAUX-CLIENT, ni INCOHERENT, ni ROBUSTESSE.

Détails de robustesse constatés (tous conformes, à noter) :
- **Clé LLM absente → dégradation honnête, jamais un chiffre.** `core.complete` (src/labuse/ai/core.py:446)
  court-circuite sur `has_key()` faux → `IAResult(degraded=True, reason="no_key")`. Tout chemin modèle
  (routeur `router.classify`, `_formuler`, `_select_tool`, web, héros) retombe sur `erreur_infra()`
  (answering.py:94) ou sur le repli DÉTERMINISTE. Aucune exception ne fuit : garde générale
  copilote_v2.py:128 (trace serveur + message honnête, jamais un 500/identifiant technique à l'écran).
- **Chemin déterministe sûr par construction.** Les réponses de champ (surface/SDP/zone/propriétaire)
  passent par `resume_fiche.champ_precis` (src/labuse/copilote_v2/resume_fiche.py:257), qui lit le
  robinet `robinet_fiche.collecte` — la MÊME source que la fiche écran et le Dossier (parité). Le nombre
  servi EST le nombre servi ; il ne peut pas diverger ni être inventé. Parité vérifiée : `resume_parcelle`
  rend surface 3349/429/682/8 et SDP 766/300/57, byte-identiques à la DB et à `/parcels/{idu}`.
- **Quota IA honnête (Q30).** Après 29 appels, l'endpoint a répondu 429
  « Quota d'analyses IA atteint (30/jour). Reprend à minuit. » (copilote_v2.py:82-91, `etat_plafond_ia`).
  Comportement attendu, pas un bug.
- **Parcelle absente (Q21) → pas de chiffre.** `_fiche` renvoie None sur HTTPException (resume_fiche.py:80)
  → le Copilote ne fabrique rien.

## Non vérifié
- **Le chemin MODÈLE en conditions réelles** (routeur haiku + formuler/web/héros sonnet) n'a PAS pu être
  exercé en live : aucune clé `ANTHROPIC_API_KEY` en local. Le verrou anti-invention a donc été prouvé
  par (a) lecture du code (`_anti_invention` answering.py:285, `heros._phrase_ok` heros.py:35), (b) ses
  tests unitaires rejoués verts, (c) un test adversarial où j'ai STUBBÉ `core.complete` pour forcer une
  invention — le verrou l'a rejetée. Reste non observé : le comportement exact des prompts système
  (FORMULE_SYSTEM, SELECT_SYSTEM, le prompt routeur) sur du texte libre réel — mais le verrou AVAL est
  déterministe et indépendant du prompt (ceinture-bretelles), donc une dérive du modèle ne peut pas
  servir un chiffre non autorisé.
- **Le chemin web/recherche sourcée** (`recherche_web`) et son anti-invention de SOURCES : non exercé
  faute de clé. Code à auditer en priorité le jour où la clé est posée.
- **Quota : seulement 29 questions ont réellement reçu une réponse de contenu** ; la 30e a buté sur le
  plafond 30/jour (compté par `usage_compteurs` kind `QUOTA_COPILOTE_KIND`). Suffisant pour l'invariant.
- Non exploré : mémoire de fil (`conversation_id`/`registre_faits` — la reprise d'un chiffre d'un tour
  antérieur) en live ; le verrou `_anti_invention` autorise les valeurs du fil (`valeurs_fil`), couvert
  par `tests/test_registre_faits.py` (déjà vert).

## Gardes proposées
Deux gardes, prêtes pour `scripts/coherence/chasse_invariants.py`. La G10-A est la plus forte (elle teste
le Copilote de bout en bout sans dépendre d'une clé) ; la G10-B verrouille le code du garde-fou.

```python
# G10-A — PARITÉ COPILOTE ↔ FICHE (déterministe, sans clé LLM).
#   Invariant : pour N parcelles servies, le champ précis répondu par le Copilote (surface, SDP, zone)
#   est IDENTIQUE à ce que lit la fiche/robinet. Aucun chiffre ne peut diverger ni être inventé.
def garde_copilote_parite_fiche(db, n=200):
    import random
    from labuse.copilote_v2 import resume_fiche
    from labuse.exports import robinet_fiche
    idus = [r[0] for r in db.execute(text(
        "SELECT idu FROM score_labuse WHERE run_label='q_v18' AND idu IS NOT NULL "
        "ORDER BY random() LIMIT :n"), {"n": n})]
    ecarts = []
    for idu in idus:
        fiche = resume_fiche._fiche(db, idu)
        if fiche is None:
            continue
        vals = robinet_fiche.collecte(db, idu, ["surface_parcelle_m2", "sdp_residuelle_m2"], fiche=fiche)
        for msg, cid in [("surface de %s ?" % idu, "surface_parcelle_m2"),
                         ("sdp restante de %s ?" % idu, "sdp_residuelle_m2")]:
            rep = resume_fiche.champ_precis(db, idu, msg)
            attendu = vals.get(cid)
            attendu_v = attendu.valeur if attendu else None
            # rep["valeur"] doit égaler la valeur du robinet (ou None/None)
            if rep is None or rep.get("valeur") != attendu_v:
                ecarts.append((idu, cid, attendu_v, (rep or {}).get("valeur")))
    if ecarts:
        print("[ECART] copilote≠fiche :", ecarts[:10], "…" if len(ecarts) > 10 else "")
        return 1
    print(f"[OK] copilote-parité-fiche : {len(idus)} parcelles, 0 écart")
    return 0

# G10-B — LE VERROU ANTI-INVENTION MORD (unitaire, reproductible, aucune DB/clé).
#   Invariant : _anti_invention rejette tout nombre absent des valeurs autorisées ; _formuler retombe
#   alors sur le repli déterministe (jamais l'affirmation inventée). Idem heros._phrase_ok.
def garde_anti_invention_mord():
    from labuse.copilote_v2.answering import _anti_invention
    from labuse.copilote_v2.heros import _phrase_ok
    from labuse.copilote_v2.outils import ToolResult
    res = ToolResult('fiche_parcelle', valeur=429, source='fiche LABUSE', millesime='q_v18')
    res.data = {'surface_m2': 429}; res.reserve = None
    ok = (_anti_invention("429 m2.", res)                       # autorisé → True
          and not _anti_invention("429 m2 et 350000 euros.", res)  # inventé → False
          and _phrase_ok("429 m2.", {429.0})
          and not _phrase_ok("vaut 350000 euros.", {429.0}))
    if not ok:
        print("[ECART] verrou anti-invention ne mord plus")
        return 1
    print("[OK] verrou anti-invention : rejette l'inventé, laisse passer l'autorisé")
    return 0
```
