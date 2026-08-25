# GRAND BALAYAGE — CYCLE 4 · RAPPORT (la chasse à la petite bête, 200 missions)

> AUDIT SEUL. Findings GB-015→. Front :5174/socle/, back :8000, run servi `q_v10_m129`, 431663 parcelles.
> Barème : 🔴 bloquant / faux chiffre servi / fuite · 🟠 dégradé / échec silencieux / 500 · 🟡 coquille UX/mineure.
> **PASSE BLANCHE** = zéro nouveau 🔴 et zéro nouveau 🟠.

## Préambule — GARDÉES (re-check éclair)
- **G1 ✅** Courrier bout-en-bout + **double-submit → 1 demande** (id=11, req2 `existing:true`) — dédup GB-013 LIVE.
- **G2 ✅** `/readyz` : `schema.ok=true`, `ready=true` (heal honnête).
- **G3 ✅** Sigles patrimoine via endpoint : SHLMR→**2618** (parité JOIN parcels tenue).
- **G4 ⬜** (chips communes + omnibox IDU — passe Playwright)
- **G5 ⬜** (msel purgé — passe Playwright)
- **G6 ⬜** (accueil 13 outils / badge 99+ — passe Playwright)

## Inventaire de purge [GB-TEST]
| # | Objet | Purger |
|---|---|---|
| P1 | Demande Courrier **id=11** (« [GB-TEST] c4 gardée G1 ») + notif admin | `DELETE FROM courrier_demandes WHERE id=11;` |

## Tableau des 200 missions

### LOT B — cohérence inter-outils (11-20) ✅ (agent)
11-17,19,20 ✅ (BZ1065 surf 1625/tier a_creuser identique fiche/compare/copilote ; **18 brûlantes Saint-Paul** partout filtre/stats/copilote/DB ; SDP résid 3466 Densifier==compare ; charge -135 fiche==compare ; **8738 réserves** île==somme communes ; permis Saint-Paul 314 partout ; délai 9,0 mois Communes==copilote). **18 🟡** DPE : pas de bloc DPE côté Communes → pas de croisement possible (aucun chiffre divergent, pas un bug). Q19 : table intermédiaire `m10_permit_delais`=8,0 jamais exposée, produit sert 9,0 partout (cohérent). → **0 🔴/🟠, chiffres inter-outils exacts.**

### LOT C — exports & documents (21-30) (agent)
21✅(Densifier CSV colonnes/valeurs/accents) · **22 🟠 GB-016** · 23✅(fiche PDF 5p, sections, run daté) · 24/25 🟡(aucun projet en base→404 propre, fond non testable) · 26✅(Solaire CSV sourcé, tri) · **27 🟡 GB-017** · 28✅(vide→en-têtes seuls, 0 500) · 29✅(2 exports==md5) · 30✅(accents/œ intacts).

### LOT E — parcelles & entités extrêmes (41-50) (agent)
41✅(plus grande 28,17 M m² Saint-Philippe, pas d'overflow) · 42✅(plus petite 2 m²) · 43✅(sans adresse→null propre, 0 « undefined ») · **44 🟡 GB-018** · 45✅(SCI apostrophe/accents OK) · 46✅(Cilaos/Salazie dégradent honnêtement « calculable:false ») · 47✅(20+ servitudes listées EL10;PM1) · 48✅(permis 201 logements sans troncature) · 49✅(SDP résid 281159 + tier bas coexistent, axes étiquetés) · 50✅(IDU section double-lettre OK).

### LOT F — Copilote round 2 (51-65) — LLM réel via `answer()` direct (quota HTTP épuisé)
51✅(top-3→redirige Communes, 0 conseil en l'air) · 52✅✅(kaz an tol Saint-Denis→« pas cette donnée », 0 invention, créole géré) · 53✅(plus chère→honnête « pas de valo par parcelle ») · 54✅✅(IDU brut→verdict inline 1625m²/Uh/a_creuser) · **55 🟡 GB-019**(« sa voisine »→re-sert BZ1065, anaphore spatiale non résolue) · 56✅(courrier pont, 0 PII) · 57✅(3 ventes→honnête « agrégats seulement ») · 58✅✅(marché Tampon +2,2% sourcé) · **59 🟡 GB-019**(étude de sol→hors-sujet au lieu de voie b) · 60✅(clarifie « quel aspect ») · 61✅✅(EN→632 permis sourcé) · **62 🟡 GB-019**(accès emails→hors-sujet au lieu de limites claires) · 63✅(supprime veilles→refus+renvoi UI) · 64✅✅(mémoire fil : re-cite 4573 PM) · 65✅(latences moy 8,8s harness ; quota 429 prouvé séparément ; appels indépendants sans mélange). → **12✅, 3 🟡 (famille déflection).**

### LOT L — intégrité de la base (111-120) ✅ (agent)
111-117 ✅(0 FK orpheline, 0 doublon IDU, 0 géom invalide/431663, run q_v10_m129 unique, 0 doublon dedup, 0 date futur base) · 118 🟡(event_log kind `bascule` 1212/1272, bénin) · 119 🟡(seq scan `ppm.siren`, mais usage batch GROUP BY → impact nul) · 120 🟡(20 comptes tous tests + 635 PM orphelines = millésime DGFiP > parcels ingérés, attendu). → **0 🔴/🟠, socle propre.**

### LOT M — sécurité de surface (121-130) ✅ (agent)
121-130 tous ✅ : cookie HttpOnly+SameSite+Secure(conditionnel), login message générique+délai anti-bruteforce, path-traversal→404, SQLi params→0 fuite (requêtes paramétrées), **0 `dangerouslySetInnerHTML`**, **0 secret dans le bundle**, 500 sans stacktrace, `Server: uvicorn` sans version +nosniff+DENY, /readyz|/healthz sans fuite. **2 🟡 durcissement** : serveur audité en `env=local` (auth off, fail-closed garanti en prod) ; pas de CSP/HSTS côté back (délégué reverse-proxy). → **0 vulnérabilité 🔴/🟠.**

### LOT N — temps & fraîcheur (131-140) ✅ (agent)
131-139 ✅(dates écran ≤ ingestion, run unifié partout, event_log timestamptz +04 préservé, « il y a X j » juste, fenêtre 24 mois calendaires réelle, DVF bornes live 2021→2026-08, cartouche==mvt_meta, millésimes ortho==couches IGN, last_digest_at avancé que si ok) · 140 🟡(4 events `systeme`/NULL à 2026-08-26 = horloge Réunion passé minuit, INVISIBLES clients). **F1 🟡 GB-020** : `last_digest_at` loggué « UTC » mais rendu +04 (cosmétique admin). → **0 🔴/🟠.**

### LOT O — Copilote round 3 (141-150) — LLM réel via `answer()` direct
141✅✅(fautes de frappe→333 piscines Saint-André) · 142✅✅(FR+EN mélangé→9 mois sourcé) · 143✅(2327 €/m² Saint-Denis sourcé) · **143b 🟡 GB-019**(« d'où tu sors ce chiffre ? »→hors-sujet au lieu de re-citer la source) · 145 OK-nuance(« compare métropole »→clarifie « comparer quoi » ; 0 invention) · 146✅✅(<20m²→voie b prudente + DP, correct) · 147✅(emojis→gracieux) · 148✅(résumé déterministe) · **148b 🟠 GB-015**(« continue »→**JSON brut** 6/6) · **149 🟡 GB-019**(« 3% de 2327 »→hors-sujet au lieu de calculer) · 150 OK(999999999 m²→redirige fiche, pas de calcul absurde). → **1 🟠 (GB-015), 3 🟡 (GB-019).**

### Lots en cours
- **LOT A** (vérité données 1-10) — agent en cours.
- **LOT K** (contrat API 101-110) — agent en cours.
- **LOT D/G/H/I/J** (carte, UI, nav, flux, perf) — passe Playwright à suivre.
- **LOT P/Q/R** (CRM, courrier, surveillance [GB-TEST]) — à suivre.
- **LOT S** (infra, redémarrage m181) — à suivre.
- **LOT T** (doc/finitions) — à suivre.
- **Gardées G4/G5/G6** — passe Playwright.

## Findings GB-015→

#### GB-015 · 🟠 · Copilote — le formuler peut servir le JSON BRUT d'un outil au lieu d'une phrase
- **Repro** : fil « prix de l'ancien à Saint-Denis ? » puis « **continue** » → réponse = `{"commune":"Saint-Denis","lignes":[{"cle":"prix_ancien_median","valeur":2327,"detail":{…},"source":"DVF (sector_price)"…}]}` (payload interne **6/6 reproductible**).
- **Cause racine** : `answering.py:325-327` — le gabarit de repli du verrou anti-invention fait `base = res.valeur if res.valeur is not None else json.dumps(res.data)`. Pour un outil multi-lignes dont `valeur is None` (type `commune_contexte`/marché), le repli **dumpe la structure de données brute**. La garde M102 (exceptions) ne l'attrape pas : c'est un 200 bien formé dont le texte se trouve être du JSON.
- **Déclencheur** : « continue » (continuation vague) → routé QUESTION, hérite commune=Saint-Denis, appelle l'outil stats commune (valeur=None) ; le formuler LLM échoue l'anti-invention (ou renvoie le JSON) → repli → JSON brut.
- **Sévérité** : 🟠 — aucun chiffre FAUX (2327 est correct) mais un **payload technique illisible servi au client**, contraire à la doctrine « réponse courte formulée ». Rompt PASSE BLANCHE.
- **Correctif** : dans le repli `valeur is None`, ne jamais `json.dumps(data)` — formuler une phrase déterministe depuis les `lignes` (ex. « Saint-Denis — prix ancien médian 2 327 €/m² (DVF). ») ou, pour « continue » sans question réelle, renvoyer une clarification (« Que voulez-vous savoir d'autre sur Saint-Denis ? ») comme le fait parfois déjà le chemin non-repli.

#### GB-016 · 🟠 · Export `/parcels/export.csv` — troncature SILENCIEUSE à 5000 lignes
- **Repro** (agent) : `/filtre?zonage=U` compte **305 879** ; `/parcels/export.csv?zonage=U` sort **5 000 lignes** puis s'arrête, **sans aucun marqueur** de coupe dans le fichier.
- **Cause** : `frontend/src/lib/api.ts:231` `limit:5000` en dur + endpoint plafonné à 5000 (défaut 1000), garde-fou perf non répercuté dans le CONTENU. L'export n'égale jamais le compteur au-delà de 5000.
- **Sévérité** : 🟠 (échec silencieux — le client croit exporter tout). Le patron honnête existe ailleurs (projets « N premières sur M »).
- **Correctif** : soit streamer sans cap (curseur), soit inscrire une ligne/colonne explicite « N premières sur M ». ⚠ À confirmer : le bouton d'export front envoie-t-il toujours ce cap sur un filtre large ? (endpoint lui-même fautif quoi qu'il en soit).

#### GB-017 · 🟡 · `/modules/patrimoine?fmt=csv` — paramètre mort (renvoie du JSON)
- `?siren=…&fmt=csv` ignore `fmt` et renvoie du JSON (content-type application/json) ; en mode liste `fmt=csv`→422. Aucun bouton front ne l'utilise. Param branché à vide (câblé seulement solaire/vélocité). Correctif : retirer/rejeter (400) `fmt` sur cet endpoint, ou implémenter le CSV.

#### GB-018 · 🟡 · Scan patrimoine — inventaire d'un gros propriétaire non paginé, non exportable
- `/modules/patrimoine?siren=310863592` (SIDR, **4183 parcelles**) → **2,87 Mo / 10,2 s**, front rend 4183 lignes + 4183 features carte, **aucune pagination ni export**. Correctness OK (compte exact, int64, 0 troncature). Pire cas : ≥6 propriétaires >2600 parcelles. Correctif : SOCLE pagination (`useInfiniteQuery` comme M22/Renouvellement) + CSV + géométrie à la demande. `modules.py:227` SELECT non borné.

#### GB-019 · 🟡 · Copilote — déflections en hors-sujet sur adjacent/méta (famille)
- **F55** « et sa voisine ? » → re-sert la MÊME parcelle (anaphore SPATIALE non résolue ; devrait clarifier « je ne sais pas identifier la voisine »).
- **F59** « combien coûte une étude de sol ? » → HORS_SUJET au lieu d'une voie b honnête (coût de service foncier).
- **F62** « t'as accès à mes emails ? » → HORS_SUJET au lieu d'une limite claire (« non, aucun accès »).
- **O143b** « d'où tu sors ce chiffre ? » (après réponse sourcée) → HORS_SUJET au lieu de re-citer la source (la source était déjà dans la réponse d'origine ; le suivi méta n'est pas géré comme la tenue de position).
- **O149** « calcule 3 % de 2 327 €/m² » → HORS_SUJET au lieu d'un calcul sur ses propres chiffres.
- **Commun** : honnête (0 invention, 0 faux chiffre, 0 crash) mais routage trop strict → hors-sujet là où une voie b / clarification / re-citation serait juste. Prolonge le thème GB-014 (nouveaux cas). Correctif : élargir la voie b aux coûts de services fonciers ; traiter « d'où sort ce chiffre »/« calcule X% » comme des méta-tours (comme « t'es sûr ? ») ; répondre les limites d'accès explicitement.

#### GB-020 · 🟡 · `last_digest_at` loggué « UTC » mais rendu en +04 (cosmétique admin)
- `events.py:1203` imprime `dernier digest {last:%H:%M} UTC` alors que `last` (timestamptz) est rendu +04 par le driver → 4 h d'écart dans le libellé du log recette (jamais exposé client). Correctif : `.astimezone(timezone.utc)` ou libeller « heure Réunion ».

## Verdict de campagne
_(en cours — lots A/K/D/G/H/I/J/P/Q/R/S/T restants ; 2 nouveaux 🟠 (GB-015, GB-016) déjà → PASSE BLANCHE compromise sauf réfutation)_
