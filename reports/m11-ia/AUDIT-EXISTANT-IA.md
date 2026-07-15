# M11 — AUDIT DE L'EXISTANT IA (lecture seule, aucune modif)

**Date** : 2026-07-15 · Méthode : lecture de code (back+front) + **appels IA LIVE réels** (instance dev, provider Anthropic actif) + SQL en lecture. Aucune modification, aucun commit.

## ⚠️ 5 constats transverses à retenir avant tout
1. **Il n'y a PAS un moteur IA, mais 3-4 implémentations parallèles non partagées** : `api/ia.py` (Copilote), `api/assistant.py` (Assistant fiche), `ai/nl_segments.py` (NL segments), + `ai/agent.py` (narratif cascade legacy, hors score). Trois détections de clé, deux clients Anthropic, plusieurs stubs — toute évolution de garde-fou doit être répliquée à la main.
2. **Doctrine unique et sérieuse** : *« l'IA traduit / dialogue, le moteur déterministe calcule ; l'IA n'accède JAMAIS à la base et ne modifie AUCUN score »*. Elle est appliquée structurellement (schémas forcés, listes blanches), pas seulement en prompt.
3. **Provider actif = Anthropic** (haiku `claude-haiku-4-5-20251001` pour la NL, sonnet `claude-sonnet-4-6` pour la synthèse). Repli **stub local déterministe** flaggé `stub:true` si clé absente. Crédits OK au 15/07 (appels réels vérifiés live).
4. **🔴 BUG LIVE MAJEUR** : les 2 boutons IA de la fiche (`/ia/synthese/{idu}`, `/ia/pourquoi/{idu}`) renvoient **HTTP 500** (`TypeError: Object of type Decimal is not JSON serializable`, `ia.py:684`). **La synthèse IA et le « pourquoi ce score » sont CASSÉS en mode réel** (marcheraient en stub). Détail §5.
5. **L'assistant fiche qui MARCHE** (`GET /parcels/{idu}/explain`, `assistant.py`, grounding par liste blanche) est **distinct** des 2 boutons cassés — c'est le meilleur garde-fou du repo, mais il n'est pas celui branché sur le panneau « Analyse IA » de la fiche.

---

## 1. RECHERCHE IA SIMPLE (page IA / Copilote)

**CE QUI EXISTE** — `POST /ia/search` (`ia.py:329`) et `POST /ia/segments-search` (`ia.py:411`, délégué à `ai/nl_segments.py`). Front : `frontend/src/components/ia/IAStub.tsx` (hub 2 portes : « recherche simple » / « montage projet »).

**CE QUE ÇA FAIT** — Ce n'est **pas un chatbot Q&R** : c'est un **traducteur langage-naturel → filtres**. haiku, `temperature=0`, `max_tokens=600`. Le prompt `_NL_SYSTEM` (`ia.py:295-326`) reçoit le `FILTER_SCHEMA` et **aucune donnée base**. Sortie = 4 formes : `filters` (validés par schéma), `programme` (préremplit M22), `projet_intent` (ouvre l'entretien), `out_of_scope`. Validation serveur `validate(data, FILTER_SCHEMA)` (`ia.py:379`) = un filtre inventé est **rejeté mécaniquement**.

**3 REQUÊTES RÉELLES (live, provider anthropic, stub:false) :**

> **REQ 1** — *« les parcelles brûlantes à Saint-Pierre avec un propriétaire personne morale »*
> → `{"filters":{"tiers":["brulante"],"commune":"Saint-Pierre"},"explanation":"Filtres proposés par l'IA (validés par schéma)."}`
> ⚠️ **Qualité partielle** : « brûlante » + « Saint-Pierre » captés, mais **« propriétaire personne morale » silencieusement DROPPÉ** (pas de filtre PM au schéma → l'IA l'omet sans le dire). L'utilisateur croit sa demande honorée à 100 %.

> **REQ 2** — *« je veux monter une opération de 25 logements à Saint-Paul »*
> → `{"projet_intent":true,"reformulation":"Montage d'une opération immobilière de 25 logements à Saint-Paul"}`
> ✅ Intention projet correctement détectée → bascule vers l'entretien de cadrage.

> **REQ 3 (faible, volontaire)** — *« quelle est la meilleure parcelle pour investir et pourquoi le marché va monter »*
> → `{"out_of_scope":"Demande de conseil d'investissement et prédiction de marché — hors du périmètre de prospection foncière filtrable."}`
> ✅ **Refus propre** (bon garde-fou), mais illustre la **limite de fond** : le Copilote ne répond à **aucune question analytique/advisory** — il ne sait que filtrer. Pour un promoteur qui pose une vraie question, la réponse est un refus.

**LIMITES** — champ figé au `FILTER_SCHEMA` (tiers/veille/commune/score/surface/SDP/événement/vueMer/flags) ; hors périmètre explicite (`IAStub.tsx:9-12`) : dirigeant âgé, détention longue, hors-île, DPE/passoires, clôture piscine, **propriétaire PM**. Verbes d'action (supprimer/écrire/envoyer) refusés (`_VERBES_HORS_PERIMETRE`, `ia.py:216`). Le stub NL (`_stub_nl`, `ia.py:222`) est purement lexical (regex).

---

## 2. COPILOTE / CRÉATION DE PROJET

**CE QUI EXISTE** — Un vrai **objet `Projet` persistant** (table `projets`, `models.py:635`, DDL `projets.py:37`) + un **copilote d'entretien de cadrage** (`POST /ia/entretien`, `ia.py:586`). Schéma fiche fermé `FICHE_SCHEMA` (`projet_schema.py:38` : type_programme, ampleur{logements,sdp,niveaux}, perimetre, contraintes[], budget, critères libres).

**CE QUE ÇA FAIT** — **Vraie IA UNIQUEMENT pour le dialogue** (haiku, temp 0, max_tokens 900, `_ENTRETIEN_SYSTEM` `ia.py:514`), **tout le chiffrage est déterministe** :
- `derive_filtres()` (`projets.py:122`), `derive_sdp_besoin()` = formule M22 `logements × 60 × 1,15` (`projet_schema.py:85`), `derive_programme()` → params M22 (`projets.py:149`).
- Aperçu `POST /projets/apercu` (`projets.py:244`) : compteur SQL + top parcelles avec « pourquoi » **sorti du moteur** (verdict tier, SDP résiduelle vs besoin, hauteur PLU, carence SRU). Repères sourcés `GET /projets/reperes` (100 % SQL).
- CRUD + `/rejouer` (réapplique les filtres sur les données du jour, jamais un snapshot figé) + `GET /projets/{pid}/export.pdf` (`pdf_projet.py`).
- **Moteurs mobilisés** : faisabilité M22 (`faisabilite_sens2`) + scoring q_v2/q_v6 + PLU (hauteur via `resolve_zone`). **Aucune valeur inventée par l'IA.**
- **Garde-fous** : `validate(data, ENTRETIEN_SCHEMA)` (`ia.py:625`), `_neutralise_opinion()` (`ia.py:564`, purge les opinions marché non chiffrées), sans clé → `fallback:true` (**pas d'entretien simulé**).

**EXEMPLE RÉEL EN BASE** (table `projets`, 6 lignes, ex. id 22 « LES LILAS ») :
```json
fiche:     {"ampleur":{"logements":40},"perimetre":{"mode":"secteur","secteur":"Ouest"},
            "type_programme":"etudiant","criteres_libres":"Budget serré","budget_foncier_eur":0}
filtres:   {"sdpMin":2760,"communes":["Le Port","La Possession","Saint-Paul","Les Trois-Bassins","Saint-Leu"]}
programme: {"type":"etudiant","niveaux":2,"parking":true,"batiments":1,"surface_unite_m2":60,"logements_par_batiment":40}
```
Dérivation vérifiable : secteur Ouest → 5 communes ; 40 logts → sdpMin 2760 (=40×60×1,15) ; R+2 défaut. *(5/6 lignes = doublons de test.)*

**LIMITES** — `budget_foncier_eur` non filtrable (aucun prix/parcelle en base) ; programme dérivé seulement si type≠autre ET logements présents ; pas d'export batch ; **cron « re-match events↔projets actifs » : structure prête, rien câblé** (`models.py:648`).

**Vraie IA ou templating ?** → **hybride** : dialogue = vraie IA (haiku sous schéma fermé) ; tout le reste = templating de filtres + moteurs SQL déterministes.

---

## 3. MOTEUR FAISABILITÉ (`src/labuse/faisabilite/`)

**CE QUI EXISTE** — `engine.py` (capacité), `bilan.py` (bilan promoteur), `db.py` (intégration parcelle→moteur), `plu_rules.py`, `bilan_params.py`/`bilan_calibration.py`, `residuel.py`, `viabilisation.py`. **100 % déterministe, aucune IA à l'intérieur.**

**CE QUE ÇA CALCULE** — Enveloppe constructible → fourchette (niveaux R+n, SDP, logements) : reculs → emprise % → pleine terre → niveaux → emprise bâtie (coef 0,45) → SDP → habitable (0,80) → logements (÷65-80 m²) → plafond densité → stationnement → modulation réunionnaise (pente/PPR/littoral/SAR). Bilan : prix DVF fiabilisé → CA → **charge foncière à rebours** (CA − construction − marge − frais − VRD) + clause mixité sociale.

**ENTRÉES / SORTIES (pour brancher une couche IA)** :
- `estimate_capacity(rules, surface_m2, contraintes?, hyp?, emprise_geo?) -> Faisabilite` (`engine.py:125`) — **PURE**. Sortie `fourchette{niveaux, hauteur_m, emprise_*, surface_plancher_m2, shab_vendable_m2, logements_au_sol:(lo,hi), stationnement_regime}`.
- `compute_bilan(shab_vendable, surface_terrain, prix, hyp, contexte_eco?) -> Bilan` (`bilan.py:248`) — **PURE**. Sortie `{fiable, fiabilite, ca:{bas,central,haut}, charge_fonciere:{...,par_m2_terrain}, steps, avertissements}`.
- `compute_calculette(shab, terrain, prix, cout_m2, marge_pct, prix_demande) -> dict` (`bilan.py:469`) — **PURE**.
- `class Hypotheses` (`engine.py:22`) = ~30 params tunables (`.charger()` lit le YAML).
- **Intégration base** : `parcel_faisabilite(session, parcel_id)` (`db.py:182`) + `fiche_payload(session, parcel_id) -> dict` (`db.py:327`, payload JSON complet, défensif).
- **API** : `GET /modules/faisabilite/{idu}` (sens 1), `POST /modules/programme` (sens 2), `POST /modules/faisabilite/{idu}/charge` (calculette).

**→ Appelable par une couche IA de 2 façons** : fonctions pures (l'IA fournit les params) ou via base (`fiche_payload` sur un IDU). Le copilote-projet passe déjà par `faisabilite_sens2` (M22).

**LIMITES** — calibré surtout Saint-Paul (`calibree=False` ailleurs → estimation prudente R+2) ; params PLACEHOLDER (prix LLS, VRD pluvial) ; emprise = géométrie réelle sinon modèle carré ; bilan seulement si DVF suffisant.

---

## 4. ALERTES / EVENTS

**CE QUI EXISTE** — `detect_events(db, run_from, run_to)` (`events.py:56`), CLI `labuse detect-events`, API `POST /events/detect`. Stockage **`event_log`** (`events.py:26` : kind, idu, titre, detail, run_from/to, demo, lu). Tables voisines : `watched_parcels` (suivi cible), `saved_searches` (veilles).

**CE QUE ÇA GÉNÈRE (4 types, en diffant 2 runs de scoring)** :
| kind | Diff | Code |
|---|---|---|
| `bascule` | `matrice_statut` run A vs B (▲ montée / ▼ descente) | `events.py:60` |
| `bodacc` | `cascade_results.evenement='rouge'` présent en run_to, absent en run_from | `events.py:80` |
| `veille`/`match` | bascules montantes ∩ filtres d'une `saved_searches` | `events.py:98` |
| `permis` | `sitadel_permits` ≤300 m d'une parcelle suivie (12 derniers mois) | `events.py:102` |

**ÉTAT RÉEL EN BASE** : bascule=8, match=5, permis=5 — **TOUT est en démo** (`demo=true`, run `q_v2_demo`) ; 17 non lus. **Aucun diff de 2 runs réels effectué** (la bascule M8 q_v5→q_v6 est un candidat idéal pour le 1er run réel).

**NotifBell** — `frontend/src/components/header/Header.tsx:278` (pas un fichier séparé). Cloche + badge non-lus ; panneau = événements (titre/detail/date/DÉMO) + section VEILLES. Endpoint `GET /events` (`{unread, items[]}`). **Déclenchement = polling 60 s** (react-query `refetchInterval:60_000`). Marquage lu `POST /events/{id}/read` + `/read-all`. Digest hebdo `GET /events/digest.html`.

**LIMITES** — tout dépend d'un 2e run réel (sinon seule la démo vit) ; **SMTP du digest non branché** (`events.py:342`) ; veilles par hash d'URL, **pas de comptes utilisateurs** ; permis limités aux parcelles déjà suivies ; divergence libellé `veille`/`match`.

---

## 5. RECHERCHE PAR FICHE (la loupe / panneau « Analyse IA »)

**CE QUI EXISTE** — Un panneau flottant **« Analyse IA »** sur la fiche (`Fiche.tsx:438-472`, `IAPanel({idu})`) avec **2 boutons** (pas de champ libre) : « Synthèse » et « Pourquoi ce score ? » → `POST /ia/synthese/{idu}` / `POST /ia/pourquoi/{idu}` (`api.ts:185`). *(La question libre n'existe QUE dans la barre globale `/ia/search`, hors fiche.)*

**CE QUE ÇA FAIT (back `ia.py:693-716`)** — récupèrent `_fiche_json(db,idu)` = `_q_v2_fiche` (la fiche JSON tracée = **seule donnée passée au modèle**), puis sonnet (`MODEL_SYNTH`, max_tokens 700). Prompts stricts (« INTERDIT d'inventer », 150 mots, `ia.py:671`/`708`).

**🔴 TEST LIVE — LES DEUX SONT CASSÉS** :
```
POST /ia/synthese/97423000AB1908  → HTTP 500
POST /ia/pourquoi/97423000AB1908  → HTTP 500
Traceback: ia.py:684 _real_text → json.dumps(payload)
           TypeError: Object of type Decimal is not JSON serializable
```
La fiche `_q_v2_fiche` contient des `Decimal` (colonnes `numeric` : DVF, RPLS, filosofi…) que `json.dumps` refuse. **Le panneau « Analyse IA » de la fiche est donc non-fonctionnel en mode réel** (il ne marcherait qu'en stub, qui n'appelle pas `_real_text`). Bug présent aussi sur l'app servie (même code).

**✅ CE QUI MARCHE À CÔTÉ (mais pas branché sur ce panneau)** — `GET /parcels/{idu}/explain` (`assistant.py`, grounding par **liste blanche** `assistant_facts`). Sortie réelle live (sonnet, extrait) :
> **Potentiel** — Statut **À creuser**, 61/100, complétude 92/100. Zone PLU **1AUb**. Capacité **ESTIMÉE** : R+2, ~183 m² SDP, **1 à 3 logements**. Parcelle couverte par l'îlot « Potentiel foncier » Région (SOURCÉ).
> **Contraintes** — ⚠️ Accès non identifié (voirie ~7 m, BD TOPO). ⚠️ PPR Inondation/Mouvement — **constructibilité non garantie**. Propriétaire inconnu (Cerema absent).
> **Bâti/libre** — Parcelle **vacante** (BD TOPO, ratio 0 %, SOURCÉ).
> **Économie indicative** — CA ~834 k€, charge foncière centrale ~241 k€ (~771 €/m²). ⚠️ Fourchette basse=centrale=haute (données limitées) : ne pas prendre pour une précision.
> **Recommandation** — 1. Lever l'accès. 2. Consulter le règlement PPR. 3. Identifier le propriétaire.

Réponse **groundée, sourcée (SOURCÉ/ESTIMÉ), honnête sur l'incertitude** = le meilleur exemple de l'existant. **Découverte clé pour la refonte : le bon moteur (assistant.py) existe déjà mais n'est PAS celui que la fiche appelle.**

**LIMITES** — 2 actions figées (pas de question libre en fiche) ; sonnet coûteux ; les 2 endpoints branchés sont cassés (§ ci-dessus) tandis que le bon (`/explain`) n'est pas câblé au panneau.

---

## 6. INFRA IA COMMUNE

**Pas de service central.** 3-4 implémentations :
| Module | Endpoints | Client | Modèle | Contexte envoyé au LLM |
|---|---|---|---|---|
| `api/ia.py` (Copilote) | search, segments-search, entretien, synthese, pourquoi | SDK `anthropic` | haiku NL / sonnet synth | search : texte+schéma ; **synthese/pourquoi : fiche JSON ENTIÈRE** (`ia.py:684`) |
| `api/assistant.py` (Assistant fiche) | `/parcels/{idu}/explain` | `httpx` brut | sonnet | **liste blanche** `assistant_facts` (grounding) |
| `ai/nl_segments.py` | segments-search (délégué) | SDK anthropic (sa propre détection clé) | haiku | texte + registry sérialisé |
| `ai/agent.py` (legacy) | narratif cascade | Stub/Anthropic | — | **hors score** (`ai_adjustment=0`, opt-in `stub`) |

- **Bascule provider/stub** : `_has_key()` (`ia.py:79`, lit `ANTHROPIC_API_KEY` après `load_dotenv`) ; partout `if _has_key(): réel + try/except → _note_erreur + repli stub ; else stub`. Repli **gracieux**. Diagnostic `_DERNIERE_ERREUR` + `GET /ia/status`.
- **Modèles** : `MODEL_NL="claude-haiku-4-5-20251001"`, `MODEL_SYNTH="claude-sonnet-4-6"` (`ia.py:28-29`). `/ia/status` live : provider `anthropic`, doctrine *« l'IA ne calcule ni ne modifie aucun score ; aucun accès base »*.
- **Contexte passé au modèle** : varie fortement — de « rien que le texte » (search) à « la fiche entière » (synthese/pourquoi, le plus large et le plus risqué) à « liste blanche » (assistant, le plus sûr).

**LIMITE structurelle** : triple duplication (détection clé × 3, clients × 2, stubs × 3). Un durcissement de garde-fou n'est pas centralisé.

---

## 7. GARDE-FOUS ANTI-HALLUCINATION (le point le plus solide du repo)

**Défense en profondeur, multi-couches** :
1. **Structurel** : l'IA n'accède jamais à la base ; la recherche NL passe TOUJOURS par un **JSON schema forcé** validé serveur (`FILTER_SCHEMA`, `ENTRETIEN_SCHEMA`, registry) — filtre inventé = rejeté mécaniquement (`ia.py:379,625`, `nl_segments.py:120`).
2. **`temperature=0`** partout.
3. **Prompts stricts (verbatim)** :
   - Synthèse `_SYNTH_SYSTEM` (`ia.py:671`) : *« EXCLUSIVEMENT à partir du JSON fourni. INTERDIT d'inventer un fait absent. »*
   - Assistant `SYSTEM` (`assistant.py:32-62`, le plus strict) : *« Tu n'utilises QUE les valeurs du JSON. Tu n'inventes AUCUN chiffre… PROVENANCE : distingue SOURCÉ / ESTIMÉ / ABSENT… Ne déclare JAMAIS constructible de façon certaine… Si données insuffisantes, tu REFUSES de conclure… Termine TOUJOURS par Fiabilité + Données manquantes. »* + anti-inversion *« ne déduis jamais une absence de risque d'une donnée manquante »*.
4. **Grounding par liste blanche** (assistant) : `assistant_facts(fiche)` = seul contenu envoyé (`assistant.py:107`) + `_niveaux_fiabilite` (carte de provenance que le prompt oblige à citer).
5. **Validation de SORTIE** (entretien) : `_neutralise_opinion()` (`ia.py:564`) purge post-hoc toute opinion marché non chiffrée (regex `_MARCHE_OPINION`) → `doctrine_neutralise=True`.
6. **Disclaimers/mentions** : fiche `disclaimer` (`app.py:2202`) + `assistant_rules` ; chaque réponse IA porte une `mention` de provenance ; refus gracieux (no_key/timeout/empty).

**LIMITES des garde-fous** :
- **Asymétrie** : `/ia/synthese` & `/ia/pourquoi` envoient la **fiche ENTIÈRE** (pas de liste blanche) — moins sûr que l'assistant. Or ce sont ceux du panneau fiche (et ils sont cassés, §5).
- **Pas de validation de sortie sur la PROSE** : seul l'entretien (sortie JSON) est re-vérifié ; synthese/pourquoi/explain n'ont pas d'équivalent `_neutralise_opinion` — une hallucination en prose passerait.
- Duplication → un garde-fou doit être re-répliqué dans chaque module.

---

## 8. CATALOGUE DONNÉES PAR FICHE (exhaustif — ce que l'IA de fiche pourra exploiter)

⚠️ **DEUX fiches** : **premium v2** `_q_v2_fiche` (`app.py:1415`, `GET /parcels/{idu}?source=q_v*`) et **legacy** `_build_fiche` (`GET /parcels/{idu}` sans source). Blocs cumulés :

| Bloc | Champs | Source (table / calcul / connecteur) |
|---|---|---|
| Identité | idu, commune, surface_m2, coords, adresse | `parcels` ; centroïde geom ; BAN (`_ban_adresse`) |
| Verdict cascade | statut, q_score, a_score, a_completude, completeness, etage0, `lines[]` (tracé q/a/onglet/result/severity/source), flags, evenement | **`dryrun_parcel_evaluations`** + **`dryrun_cascade_results`** ⨝ `data_sources` |
| **Score P (opportunité)** | score_v2{tier, rang, mult_base, percentile, copro} | **`parcel_p_score_v2`** (run servi q_v6_m8) |
| **ICD** (confiance données) | score, bande, libellé, detail{groupe:bool}, manquants, cloisonnement | **`parcel_p_score_v2.icd`/`.icd_detail`** (cloisonné du score P) |
| **Score V (vendabilité)** | v_score, v_band, owner_type/siren/denomination, badge, signals[] | **`parcel_v_score`** (signaux JSONB) |
| **Règlement PLU** | zone, idurba, libellé, deep-link article/#page | `spatial_layers`(plu_gpu_zone) + `plu_reglement.reglement_block()` + `config/plu_<commune>.yaml` |
| **Potentiel transformation** | niveau, pct_consommé/résiduel, sdp_residuelle, sous_densite, capacite_estimee, surélévation, hauteurs | **`parcel_residuel`** + **`parcel_residuel_bati`** (ex-« Mutabilité ») |
| **Viabilisation M-VIA** | score, band, contributions, coût raccordement, elec_pv, note S3REnR | **`parcel_viabilisation`** → `viabilisation.build_indicateur()` (faisceau de preuves, pas de tracé réseau) |
| Gestionnaires | EPCI, eau, assainissement, SPANC, élec | config YAML `gestionnaires_via` par commune |
| Propriétaire | proprietaire_moral{denomination, siren, groupe_label} | **`parcelle_personne_morale`** |
| DVF | dernière mutation + médianes secteur (prix_m2 bâti/terrain) | `v_parcel_dvf_last` + `dvf_secteur_medianes` (2021-2025) |
| Terrain | pente_moy/max, terrassement lourd | **`parcel_terrain`** (RGE ALTI 5 m) |
| Copropriétés | n° immat, syndic, lots, rattachement | **`rnic_coproprietes`** (RNIC) |
| Marché secteur | filosofi_200m (niveau de vie, pauvreté, propriétaires) + rpls_commune (%QPV) | `filosofi_carreaux_200m` (INSEE 2021) + `rpls_commune` |
| ANRU | quartier, intérêt, dans/adjacent ≤100 m | `spatial_layers`(anru) |
| Bâti | ratio, nb, plus grand bâtiment | `bati.fiche_block` (BD TOPO) |
| Voisinage | parcelles adjacentes, assemblage_unlock | `voisinage` + `assemblage` |
| **Faisabilité** *(legacy seulement)* | fourchette logements, SDP, bilan | `faisabilite.db.fiche_payload` (§3) |
| PLH / Marché / Loyers / Occupation *(legacy)* | orientations PLH, obsimmo, loyers DHUP, INSEE RP 2022 | `plh` / `obsimmo` / `loyers` / `occupation` |
| **Permis à proximité** *(legacy)* | permis ≤300 m (12 max) | **`sitadel_permits`** via `permits.nearby_permits` |
| Risques | PPR/aléa (dans `lines[]` cascade) | `spatial_layers`(ppr, georisque_alea) |

**Note** : la fiche **premium n'expose NI permits, NI faisabilité, NI PLH/marché/loyers** (uniquement dans la legacy). Le bloc promoteur lourd (altimétrie/façade/réseaux) est en **lazy-load** `GET /parcels/{idu}/enrichment`. **Vélocité permis M10** (`m10_permit_delais`) = dans le radar `modules.py`, **pas** dans la fiche.

---

## 9. COÛT & PERF DES APPELS IA

- **Cache IA : AUCUN.** Chaque `/ia/synthese`, `/ia/pourquoi`, `/ia/search` re-appelle le provider (ou stub) à chaque fois. *(Un cache existe pour l'enrichissement non-IA : `parcel_enrichment`, cache-on-read permanent SANS TTL — pattern réutilisable.)*
- **Lazy-load : OUI.** L'IA n'est JAMAIS appelée à l'ouverture de fiche — uniquement sur bouton (`/ia/synthese|pourquoi`). Le bloc promoteur lourd est séparé (`/enrichment`).
- **Quota / rate-limit** (`protection.py`, `config.py:68`) : **300 fiches/jour/sujet** (429 sinon), **60 req/min** (burst→défi arithmétique, 3 bursts/j→gel + alerte admin), **NL 30/jour**. `LABUSE_DEV_MODE=1` court-circuite tout. *(⚠️ ce quota bloque les runs golden répétés — cf. bascule M8.)*
- **Coût (table `ia_log`, prix indicatifs `ia.py:31` : haiku 1/5, sonnet 3/15 €/Mtok)** — état réel 07→14 juil. :
  - **944 appels** (790 réels / 154 stub), **≈ 2,96 € / 7 jours**.
  - Répartition : search haiku 544 (0,81 €), entretien haiku 163 (0,74 €), **synthese sonnet 48 (0,94 €)**, **pourquoi sonnet 22 (0,43 €)**, segments 8. Le sonnet (70 appels) = ~46 % du coût.
- **🔴 RISQUE si IA branchée à CHAQUE ouverture de fiche** : un appel synthèse sonnet ≈ **0,020 €**. À 300 fiches/j (le plafond quota) → **≈ 5,9 €/j ≈ 176 €/mois pour UN sujet**, linéaire par client. **Sans cache IA, chaque ré-ouverture re-paie.** Parade évidente : cache `ia_synthese` par (idu, run_servi) — le pattern `parcel_enrichment` existe déjà.

*(Volume réel actuel : pics 300 fiches/j (11/07) et 157 (14/07), mais seulement 2 sujets = usage QA interne, pas trafic client.)*

---

## Récapitulatif « où est le code »
- **Copilote / NL / entretien / synthese / pourquoi** : `src/labuse/api/ia.py`
- **Assistant fiche (grounding liste blanche, MARCHE)** : `src/labuse/api/assistant.py` → `GET /parcels/{idu}/explain`
- **NL segments** : `src/labuse/ai/nl_segments.py` · **narratif cascade legacy (hors score)** : `src/labuse/ai/agent.py`
- **Projets** : `src/labuse/api/projets.py` + `projet_schema.py` + `models.py:635` + `pdf_projet.py`
- **Faisabilité** : `src/labuse/faisabilite/{engine,bilan,db,plu_rules,residuel,viabilisation}.py` · exposition `api/modules.py:613-792`
- **Events / veilles / digest** : `src/labuse/api/events.py` · **NotifBell** : `frontend/src/components/header/Header.tsx:278`
- **Fiches** : `src/labuse/api/app.py:1415` (premium) + `:2050-2260` (legacy + enrichment)
- **Protection / quota** : `src/labuse/api/protection.py` + `config.py:68` · **coût** : table `ia_log`
- **Front IA** : `frontend/src/components/ia/IAStub.tsx`, `projets/ProjetEntretien.tsx`, `fiche/Fiche.tsx:438-472`, `lib/api.ts:181-188`

*Fin de l'audit. Aucune modification, aucun commit. Aucune reco (hors périmètre).*
