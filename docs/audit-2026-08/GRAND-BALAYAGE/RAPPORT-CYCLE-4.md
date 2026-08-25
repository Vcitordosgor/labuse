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

### LOT A — vérité des données (1-10) ✅ (agent)
1-8 ✅ (10 fiches==mvt_parcels au bit près ; 5 permis==sitadel.raw ; 5 DVF==base ; prix médian=sector_price rayon adaptatif [pas percentile commune, documenté] ; 5 piscines==parcel_equipements ; 3 SUP==assiette GPU ; **7 : 431663−430813=850=slivers<2m² exact** ; 5 solaires==parcel_solar). **9 🟡 GB-021**(loyer `date_amont` null) · **10 🟡 GB-022**(PLU sur-liste zones bord-touchées). ~5 fausses alarmes écartées à la cause. → **0 🔴/🟠, aucun faux chiffre.**

### LOT Q — Courrier profond (161-170) ✅ (agent)
161-167,169 ✅ (10 parcelles→n=10 ; étapes conservées ; PDF 7990 car+accents ; 0 `{placeholder}` résiduel ; **0 nom de PP** par construction ; **dédup GB-013 sur les 3 branches** <120s/corps différent/backdaté ; statut visible client). 168 🟡(pas de gabarit PM/particulier = voulu, générique) · 170 🟡(pas d'alerte « déjà démarchée » = non promis). **GB-023 🟡** : ligature œ/Œ non mappée (`courrier.py:20 _LATIN1_PUNCT`)→« ? » dans le PDF. Purge : demandes 12,13,14.

### LOT R — Surveillance & notifications (171-180) ✅ (agent)
171,172,174,175,177-180 ✅ (watch_zone créée/supprimée cascade propre ; read-all 1259→0 persisté ; badge 99+ ; dédup jour ok ; digest perso/marché séparés ; polling 60s sans reload ; historique alertes cohérent). **173 🟡 GB-025**(PATCH zone = nom SEUL, géométrie non éditable) · **176 🟡 GB-026**(clic notif secteur `veille_zone`→lien `/socle/#surveillance=secteurs` non géré par Header.tsx:277→ne navigue pas ; aucun veille_zone en base actuellement). ⚠ effet de bord test 175 : 1259 events pilote passés `lu=true` (réversible `UPDATE event_log SET lu=false WHERE compte_id IS NULL`).

### LOT T — cohérence documentaire (191-200) — statique ✅ (agent) ; visuel en cours
192,194,197,198 ✅ (8 liens externes vivants ; 0 TODO/undefined/NaN fuite écran ; ~150 libellés FR sans faute ; formats € `1 234 567 €`/m² via `lib/format.ts` centralisé). **199 🟡** : clé `chaude`→« Priorité »(legacy mort) vs « À suivre »(v2 servi) — divergence documentée sans impact servi. (191/195/196/200 → passe navigateur.)

### LOT S — infra & endurance (181-190) — moi
182 ✅ (RSS back 65,8 Mo, stable sur la session) · 183 ✅ (4 idle, pas d'accumulation ; « actives » = agents concurrents) · **184 🟠? GB-024** (fiche `/parcels/{idu}` **7-11s endpoint-wide, sans cache** [2e appel même parcelle 9,6s] ; permis 0,13s/communes 0,02s/tuile 11-46ms rapides — à re-mesurer PROPRE hors contention agents) · 185 ✅ (logs→stdout, aucun stacktrace fuité, confirmé lots K/M) · 187 ✅ (tuile froide 46ms/chaude 11ms, cache OK) · 188 ✅ (100 req /health = 100 ok, 3,0s) · 189 ✅ (pas d'accumulation d'exports). **181/186/190** (redémarrage) = uvicorn simple redémarrable, **différé en fin de campagne** (ne pas saboter l'agent navigateur ni laisser le serveur de Vic à terre).

### LOT P — CRM & Projets profond (151-160) ✅ (agent, [GB-TEST])
151,153-157 ✅ (projet 0 parcelle→200 partout pas de 500 ; note 5000 car stockée/relue exacte ; **DELETE colonne peuplée→422 « indiquez move_to »** jamais de perte muette ; rename vide→422 ; dédup parcelle `already:true` verrou UNIQUE ; export concurrent cohérent 15267 lignes). **152 🟡**(pas d'historique move kanban) · **158 🟡→GB-024**(compteur île entière ~15s sans cache, chiffre juste) · **159 🟡 GB-027**(aucune recherche CRM) · **160 🟡 GB-027**(kanban carte souris-seule, colonnes ont fallback ←/→). Purge : projets 187,188 ; pipeline 93.

### LOT K — contrat API complet (101-110) (agent + vérifié curl)
**101 🟠 GB-028** (2 vrais 500) · 102 ✅(mauvais type→422) · 103 ✅(requis manquant→422) · **104 🟠 GB-029**(offset négatif→500 sur 3 endpoints) · 105 ✅(champ inconnu ignoré) · 106 ✅(méthode interdite→405) · 107 🟡(trailing slash→307 standard) · 108 ✅(content-type JSON/CSV/PDF corrects) · 109 ✅(inexistant→404 JSON) · 110 🟡(22 écritures 200 sans cookie MAIS `env=local` auth off, fail-closed en prod ; non testable ici). **GB-030 🟡** : `/modules/bailleur` >180s. → **2 🟠 (500 sur entrée malformée), reste du contrat propre.**

### Lots en cours
- **LOT D/G/H/I/J + gardées G4-G6 + T-visuel** — agent navigateur en cours.
- **LOT S** m181/186/190 (redémarrage) — différé fin de campagne.

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

#### GB-021 · 🟡 · Ligne loyer du moteur Marché : millésime DHUP non surfacé (`date_amont`=null)
- `marche_commune.py:311,316` lit `rec.get("millesime")` mais `get_loyers` (`loyers.py:61`) ne renvoie pas `millesime` (il est dans `source().millesime`) → la ligne loyer est la SEULE sans date, contre la doctrine « chaque ligne porte sa date ». Valeur correcte. Correctif : lire `source().get("millesime")` / littéral « DHUP 2025 ».

#### GB-022 · 🟡 · Fiche PLU : sur-listage des zones bord-touchées (~11% systémique)
- `_reglement_plu_block` (`app.py:3254`) fait `ST_Intersects` pur, sans poids `ST_Area` ni filtre de recouvrement → une zone qui ne touche que le bord (0-3%) est listée comme référence égale, **tri alphabétique** (peut mettre une zone à 0% en tête). Mesuré : 22,9% ont ≥2 familles, ~11,1% ont une dominante ≥95% + une parasite <2%. **La zone décisive/scoring (`parcel_zone_plu`) est correcte** — c'est le panneau « lecture du règlement » qui sur-liste. Correctif : pondérer par `ST_Area(intersection)/ST_Area(parcelle)`, trier décroissant, masquer/afficher le %.

#### GB-023 · 🟡 · Courrier PDF : ligatures œ/Œ non mappées → « ? »
- `_LATIN1_PUNCT` (`api/courrier.py:20`) mappe ’—…« » mais pas œ/Œ (absents de latin-1) → rendus « ? » dans le PDF. Correctif : ajouter `"œ":"oe","Œ":"OE"`.

#### GB-024 · 🟠 (à confirmer clean) · Perf : fiche `/parcels/{idu}` 7-11s + compteur projet île 15s
- La fiche premium `/parcels/{idu}` (`_q_v2_fiche`) répond en **7-11s pour toute parcelle, sans cache** (2e appel même parcelle 9,6s) — surface CŒUR (chaque clic parcelle) ; les autres endpoints sont rapides (permis 0,13s, communes 0,02s, tuile 11-46ms). Explique aussi la latence Copilote `fiche_parcelle` (21s). Le compteur projet « île entière » (`POST /projets/compteur` cadrage `{}`) = **14-16s sans cache** (chiffre juste). ⚠ Mesuré pendant que des agents chargeaient la DB — **à re-mesurer PROPRE en fin de campagne** ; si confirmé >5s à froid, 🟠 (dégradation perf notable), sinon contention (non-finding). Correctif si confirmé : profiler `_q_v2_fiche` (probable N+1 / jointures lourdes non indexées), cacher le compteur île.

#### GB-025 · 🟡 · Watch-zone : update PARTIEL (nom seul)
- `PATCH /watch-zones/{id}` (`WatchZoneRenameIn`) ne modifie QUE le nom ; géométrie/déclencheurs non éditables → re-dessiner une emprise = supprimer+recréer (perd l'historique d'alertes). Assumé mais non annoncé.

#### GB-026 · 🟡 · Clic notif secteur (`veille_zone`) → cul-de-sac
- Les notifs `veille_zone` portent `lien=/socle/#surveillance=secteurs` sans `idu` ; le handler (`Header.tsx:277`) ne reconnaît que `idu`/`/sources`/`/copilote` → le clic ferme le dropdown sans naviguer. (Aucun `veille_zone` en base actuellement, mais le trou existe dès qu'une notif secteur naîtra.)

#### GB-027 · 🟡 · CRM — recherche absente + kanban souris-seul
- **F159** : aucune recherche CRM (nom/commune/partiel/accent) — `/pipeline` sans param de recherche, pas de boîte au front. **F160** : déplacer une carte kanban = drag souris uniquement (`Card` sans tabIndex/onKeyDown ; l'édition de carte n'expose pas le statut) — les colonnes ont un fallback ←/→, pas les cartes (a11y). **F152** : pas d'historique de move kanban (undo = re-drag). Absences fonctionnelles/a11y assumées, pas des bugs. Correctif : filtre client `.filter` (entrées déjà chargées) + `<select>` colonne dans l'édition de carte (le PATCH `{status}` existe déjà).

#### GB-028 · 🟠 · 500 sur `run_id` non-UUID (2 endpoints)
- `GET /api/copilote/runs/{run_id}` et `/api/copilote/runs/{run_id}/events` avec `run_id=q_v10_m129` (label non-UUID) → **500** (vérifié curl : 500 vs UUID valide → 404). Cause : `copilote.py:56` `WHERE id = CAST(:r AS uuid)` → `invalid input syntax for type uuid` (DataError PG) remonte en 500. Correctif : valider le format UUID / `WHERE id::text = :r` → 404 propre.

#### GB-029 · 🟠 · 500 sur `offset` négatif (3 endpoints)
- `GET /modules/permis`, `/modules/promesses`, `/modules/fantome` avec `?offset=-5` → **500** (vérifié curl, les 3 ; vs `/parcels?offset=-5` → 422). Cause : `modules.py` déclare `offset: int = 0` **sans `Query(ge=0)`** ni clamp → `OFFSET -5` → `ERROR: OFFSET must not be negative`. Les autres endpoints paginés utilisent `Query(ge=0)`. Correctif : `offset: int = Query(0, ge=0)` (ou clamp).

#### GB-030 · 🟡 · `/modules/bailleur` très lent (>180s)
- `GET /modules/bailleur` → 200 mais >180s (~3-5 min), timeout aux passages courts (corps correct total=16351). Risque timeout proxy/UX. Rejoint la famille perf GB-024. Correctif : paginer/borner/cacher.

#### GB-020 · 🟡 · `last_digest_at` loggué « UTC » mais rendu en +04 (cosmétique admin)
- `events.py:1203` imprime `dernier digest {last:%H:%M} UTC` alors que `last` (timestamptz) est rendu +04 par le driver → 4 h d'écart dans le libellé du log recette (jamais exposé client). Correctif : `.astimezone(timezone.utc)` ou libeller « heure Réunion ».

## Verdict de campagne
_(en cours — lots A/K/D/G/H/I/J/P/Q/R/S/T restants ; 2 nouveaux 🟠 (GB-015, GB-016) déjà → PASSE BLANCHE compromise sauf réfutation)_
