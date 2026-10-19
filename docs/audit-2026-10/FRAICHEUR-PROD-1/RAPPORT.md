# FRAICHEUR-PROD-1 — chaque donnée est-elle la dernière version, partout, en prod ?

**Audit en lecture seule, 2026-10-19/20.** Branche `audit/fraicheur-prod-1`. Aucune écriture (base prod,
base Mac), aucune ingestion, aucun job lancé, aucun changement de crontab.

**Contexte des deux bases.** La prod sert `q_v18` (`scoring_run q_v18`, `residuel_run_seq 15`, promu le
13/10). Le Mac est à `q_v19` (run_seq 16, promu le 19/10) — non déployé. Prod = 130 `data_sources`
(dont 99 en vitrine client) ; Mac = 129. Journal `job_runs` prod : fenêtre 13→20/10 seulement (les jobs
mensuels d'avant le 13 n'y figurent donc pas — limite relevée en colonne E).

Preuves détaillées, une ligne par source : **`FRAICHEUR.csv`** (colonnes A→E + verdict + preuve).
Rejeu automatique : **`scripts/coherence/fraicheur.py`** (verrou, cf. §Le verrou).

---

## 1. CE QUI N'EST PAS À JOUR (et le geste exact qui le corrige)

| # | Source / sujet | Verdict | Geste exact | Qui |
|---|---|---|---|---|
| 1 | **DVF / valeurs foncières** (id 5) | **EN RETARD + GELÉ** | Le producteur a publié le **12/10/2026** (géo-DVF Etalab, couvre désormais 2021-07→**2026-06**, S1 2026 ; resource maj 19/10). La prod est figée au **31/12/2025** et `ingest-dvf` est gelé → **rien n'arrivera tout seul**. ① Décider le dégel (Phase 8, avec Stéphanie). ② Retirer `gel="Phase 8 Stéphanie"` de `ingest-dvf` (`src/labuse/jobs.py:414-418`) **et** décommenter la ligne du crontab via `sudo bash /opt/labuse/app/deploy.sh` sur le VPS. ③ Laisser tourner le cron du mardi **ou** lancer une fois `labuse jobs run ingest-dvf` en prod. | **Vic** décide (①) ; une **session CC** peut exécuter ②③ une fois approuvé |
| 2 | **DVF — ligne synthétique en prod** (id 5) | **DÉCALÉ / hygiène** | `dvf_mutations` prod contient **1 ligne de test** (id 33217 : Saint-Paul, 380 000 €, `date_mutation` 2026-08-10 **03:43** — horodatée, `mutation_id` vide), **absente du Mac**. Elle empoisonne `_dvf_couverture` (`modules.py:1752`, `max(date_mutation)` non filtré → « août 2026 »). Aujourd'hui masquée (la fiche préfère `source_horizon_at`=2025-12-31), mais c'est une bombe à retardement + une fausse fraîcheur servie dans le payload. Geste : `DELETE FROM dvf_mutations WHERE id = 33217;` en prod. | **Session CC** (écriture base, hors de ce mandat lecture-seule) |
| 3 | **FRR ex-ZRR** (id 73) | **EN RETARD** | La sentinelle (agent IA) a vu **« Arrêté du 14 avril 2025 (NOR ATDB2508688A) modifiant l'arrêté du 19 juin 2024 »** ; la base est au **« FRR 01/07/2024 »**, non injecté, non acquitté. Geste : vérifier si l'arrêté modifie le **périmètre FRR 974** ; si oui, re-transcrire/ré-ingérer la source Légifrance ; sinon acquitter la notification. | **Vic** (lecture juridique) |
| 4 | **Zones exclues EnR sauf toiture** (id 152) | **EN RETARD** | Entête amont OFB/APER modifié (hash `7:4849…`), **acquitté** mais **pas ré-ingéré**. Geste : relancer l'ingestion OFB/APER (loi APER). | **Vic/CC** (ré-ingestion) |
| 5 | **Radar (pige d'annonces)** (id 84) | **GELÉ** | `radar-cloche`, `radar-cycle`, `radar-cycle-dvf`, `radar-cycle-mensuel` gelés (Phase 8) → le **cycle de vie des annonces** est figé (une annonce expirée reste « active », aucune vente DVF ne se rapproche). Geste : dégeler après la validation Stéphanie (même mécanique que #1). | **Vic** (Phase 8) |
| 6 | **Dates de source affichées au client** (décision 18/09 non appliquée) | **DÉCALÉ (doctrine)** | Rendus confirmés côté client : fiche Marché **« DVF — ventes jusqu'à déc. 2025 »** (`frontend/.../fiche/marche.tsx:62,83` ← `_fraicheur_couche`/`_dvf_couverture`, `api/modules.py:1748-1787`) ; **millésime amont inline** sur chaque ligne de fiche (`.../fiche/primitives.tsx:284`) ; divers `.millesime` dans `reseaux.tsx`, `risques.tsx`, `leBien.tsx`, `autour.tsx`, `blocks.tsx`, `panel/FiltreLabuse.tsx:497`. (La page Sources client et le dashboard admin ont déjà été nettoyés, cf. PAGE-SOURCES-1 / PAGES-RANGEMENT-1.) Liste exhaustive : §4. | **Session CC** (mandat FRONT suivant — hors périmètre constat) |
| 7 | **parcel_zone_plu** (zonage PLU, id 3) | **MAC ≠ PROD** | Mac **430 320** lignes > Prod **427 419** (+2 901) : reconstruction du run q_v19 faite en local, non déployée (prod sert q_v18). **Mac fait foi.** Geste : déploiement du run q_v19 (mandat déploiement — hors périmètre). | **Vic / session CC déploiement** |
| 8 | **4 sources NON SURVEILLÉES** | **NON SURVEILLÉ** | Aucune sentinelle (methode vide) : **INPI RNE** (31, dirigeants — le plus notable), **CBS DEAL** (117), **OpenStreetMap/Overpass** (19), **EduGéo 1980** (156). Geste : câbler une veille (rappel/agent) pour INPI RNE et CBS ; EduGéo (fond historique figé 1980) n'attend aucune fraîcheur → OK sans veille. | **Vic** (décision) |

> **Priorité unique et bloquante : #1 (DVF).** C'est la seule source servie dont le producteur a une
> version plus récente *réellement disponible depuis une semaine* et dont le rafraîchissement est
> *gelé*. Tout le reste est soit acquitté/bénin, soit un choix assumé (gel Phase 8), soit du déploiement
> de run, soit un chantier front.

**Ce qui est sain (rappel) :** 79 sources À JOUR, 7 manuelles dans leur cadence, 3 sous veille agent IA.
Les flux quotidiens/mensuels tournent (BODACC ingéré le 17/10, DPE le 13/10, SIRENE le 13/10,
sync-GPU le 15/10). Le Mac est en retard sur les flux quotidiens (BODACC, DPE) — **attendu** : la prod
fait foi pour les flux, le Mac récupère ensuite (EXPLOITATION.md). CatNat (97) et AZI (114) : données
**identiques** prod/Mac, seul le libellé de millésime du Mac est antérieur (cosmétique).

---

## 2. Verdicts (99 sources de la vitrine client)

| Verdict | Nombre |
|---|---|
| À JOUR | 79 |
| À JOUR (manuelle, dans sa cadence) | 7 |
| NON SURVEILLÉ | 4 |
| À JOUR (veille agent IA) | 3 |
| EN RETARD | 2 (FRR 73, EnR 152) |
| À JOUR (Mac = libellé antérieur, cosmétique) | 2 (CatNat 97, AZI 114) |
| **EN RETARD + GELÉ** | **1 (DVF 5)** |
| GELÉ | 1 (Radar 84) |

---

## 3. Le cas DVF, confirmé de bout en bout

- **A — Producteur.** géo-DVF Etalab, **publication du 12/10/2026** : couvre 2021-07 → **2026-06** (S1
  2026). Cadence semestrielle (avril : année N-1 complète ; octobre : S1 de l'année N). La resource
  géolocalisée a été mise à jour le 19/10/2026. (data.gouv.fr — *demandes de valeurs foncières géolocalisées*.)
- **B — Base prod.** 29 566 lignes `dvf_mutations` : **29 565 réelles jusqu'au 31/12/2025** + **1 ligne
  synthétique** (id 33217, 2026-08-10 03:43). `data_sources` : `source_horizon_at=2025-12-31`,
  `prochain_millesime_at=2026-10-01` (**date dépassée**).
- **C — Base Mac.** 29 565 lignes, jusqu'au 31/12/2025, **propre** (pas de ligne synthétique).
- **D — Lecteurs.** Fiche Marché affiche « DVF — ventes jusqu'à **déc. 2025** » (lu de `source_horizon_at`
  via `_fraicheur_couche`). Le `_dvf_couverture` empoisonné (« août 2026 ») n'est que le *fallback* de
  `marche.tsx:62` — non affiché aujourd'hui, mais servi dans le payload et latent.
- **E — Tenue à jour.** `ingest-dvf` (hebdo mardi) **`# GELÉ (Phase 8 Stéphanie)`** — `cron.d/labuse:34`,
  registre `jobs.py:418`. 0 exécution dans le journal.
- **Angle mort de la sentinelle.** La sonde DVF (méthode `page`) lit un millésime « **2025** » et reste
  `ok` : elle ne détecte PAS l'ajout du semestre S1 2026. L'état interne « à jour » (doctrine
  `etats_sources` R1.2) est donc **faux** pour DVF. Le verrou (§6) confronte la base au calendrier du
  producteur, pas à la sentinelle, pour ne pas hériter de cet angle mort.

**Que se passe-t-il à la sortie d'octobre ?** Elle est **déjà sortie** (12/10). Tant que `ingest-dvf`
reste gelé, **rien** : la prod reste au 31/12/2025. Le geste qui fait arriver la version = #1 du §1.

---

## 4. Dates de source encore affichées au client (décision Vic du 18/09)

Confirmés **rendus** (lus dans le code courant) :

| Emplacement | Fichier:ligne | Champ | Face |
|---|---|---|---|
| Fiche Marché — horizon DVF | `frontend/src/components/fiche/marche.tsx:62,83` | `fraicheur.horizon_libelle` ‖ `dvf_couverture.libelle` | **client** |
| Backend horizon/couverture DVF | `src/labuse/api/modules.py:1748-1787` (`_dvf_couverture`, `_fraicheur_couche`) | `max(date_mutation)`, `source_horizon_at` | **client** |
| Millésime amont **inline sur chaque ligne** | `frontend/src/components/fiche/primitives.tsx:284` | `line.millesime_amont` | **client** |
| Loyers OLL | `.../fiche/marche.tsx:272` | `loyers_oll.millesime` | **client** |
| Fibre Arcep / Trafic RN | `.../fiche/reseaux.tsx:94,113` | `.millesime` | **client** |
| Aléas / Cartofriches / EnR / mesures comp. | `.../fiche/risques.tsx:98,138,151,165,169` | `.millesime` | **client** |
| OCS GE (artificialisation) | `.../fiche/leBien.tsx:216` | `ocsge.millesime` | **client** |
| IRIS quartier | `.../fiche/autour.tsx:126` | `iris.millesime` | **client** |
| PLU | `.../fiche/blocks.tsx:87-90` | `d.millesime` | **client** |
| Filtre de recherche | `.../panel/FiltreLabuse.tsx:497` | `fac.millesime` | **client** |
| Section « Sources et millésimes » (fiche + PDF) | `src/labuse/api/app.py:3260-3357` + `millesime_source.composer` | `source_millesime`/horizon | **client** (servi ; rendu réduit) |

**Déjà nettoyés** (pour mémoire) : page Sources client (PAGE-SOURCES-1, millésime retiré) ; dashboard
admin Circuit/Sources (PAGES-RANGEMENT-1). `millesime_source.composer` nettoie déjà les notes internes
et renvoie `None` quand aucun millésime n'est publié. **Correction = mandat FRONT suivant** (ce mandat
constate seulement).

---

## 5. Méthode (colonnes A→E) et périmètre

- **A — Producteur** : point de départ `source_veille` (sentinelle prod, authoritative — elle tourne en
  prod via `sonde-sources` 07:00, dernier passage 19/10), vérifiée sur la page/API du producteur pour
  les cas chauds (DVF confirmé sur data.gouv.fr).
- **B — Base prod** / **C — Base Mac** : comptages + dates max mesurés par `ssh … psql` (prod) et `psql`
  (Mac), `SET statement_timeout='60s'`. Mesurés précisément pour les sources flux/servables (DVF, BODACC,
  SITADEL, DPE, SIRENE, PLU, CatNat, AZI) ; pour les autres, le millésime `data_sources` fait foi.
- **D — Lecteurs** : les caches sont majoritairement à **clé de fraîcheur** (`mvt_tile_cache` versionné
  par run + `mvt_meta.updated_at` ; `commune_contexte_cache` à `cle_fraicheur` incluant un hash des
  millésimes de sources ; cache fiche à `data_sources.last_sync_at`). Caches **TTL sans version de run**
  (staleness de *run*, pas de *source*, ≤1 h) : `/accueil/chiffres` (1 h), `/geojson` (10 min),
  `/demo-status` (30 s) — signalés comme veille, hors du cœur « fraîcheur de source ».
- **E — Tenue à jour** : crontab `/etc/cron.d/labuse` + registre `labuse.jobs` + journal `job_runs` prod.
- **Périmètre.** Pas d'audit collatéral : le retard de *run* (prod q_v18 vs Mac q_v19) et le chantier
  front des dates client sont **nommés** mais relèvent d'autres mandats.

---

## 6. Le verrou — `scripts/coherence/fraicheur.py`

Rejoue l'audit **en lecture seule** (même DSN que les bancs COHERENCE-1 / chasse_* : `LABUSE_COHERENCE_DSN`
→ `LABUSE_DATABASE_URL` → dev ; connexion `read_only`, `statement_timeout 60 s`). **Sort en erreur
(exit 1)** dès qu'une source est **EN RETARD**, **DÉCALÉ** ou **GELÉE sans motif déclaré**. Un gel motivé
et une source non surveillée sont **rapportés** (ligne `[OK]` annotée), jamais une erreur.

Cinq gardes :

| Garde | Détecte | Fail si |
|---|---|---|
| `dvf-en-retard` | couverture réelle DVF (lignes à minuit) vs calendrier producteur (avril/octobre) | réel < couverture attendue → **EN RETARD** |
| `dvf-ligne-incoherente` | lignes `dvf_mutations` horodatées (synthétiques) ou postérieures à l'année courante | ≥ 1 → **DÉCALÉ** |
| `nouvelle-version-pendante` | sources vitrine en `nouvelle_version` non injectées (hors allowlist `_ACQUIS_BENINS = {25,148,157}`) | ≥ 1 → **EN RETARD** |
| `gel-motive` | jobs d'ingestion gelés sans motif (registre `gel=` / crontab `# GELÉ (motif)`) | gel sans motif → **GELÉ SANS MOTIF** |
| `sources-non-surveillees` | sources vitrine sans sentinelle ni job | jamais (rapport) |

**Résultat prouvé en prod** (requêtes des gardes rejouées via `ssh … psql`, 20/10) :

```
[ECART] dvf-en-retard            — base DVF jusqu'à 2025-12-31 < attendu 2026-06-30
[ECART] dvf-ligne-incoherente    — 1 ligne synthétique (id 33217), 0 future
[ECART] nouvelle-version-pendante— #73 FRR ; #152 Zones exclues EnR
[OK]    gel-motive               — gels motivés : ingest-dvf (Phase 8 Stéphanie)
[OK]    sources-non-surveillees  — rapport (INPI RNE, CBS, OSM, EduGéo…)
→ exit 1 (3 ECART)
```

Exécuté contre le **Mac** (q_v19, DVF propre) : `dvf-ligne-incoherente` passe `[OK]` (aucune ligne
synthétique), `dvf-en-retard` reste `[ECART]` (le Mac aussi est au 31/12/2025), `nouvelle-version-pendante`
reflète la sentinelle **du Mac** (états différents) — le verrou est fidèle à la base qu'on lui pointe.

L'`allowlist _ACQUIS_BENINS` est à **curer** quand Vic acquitte une notification bénigne (base == amont).

---

## 7. Proposition — faire tourner le verrou chaque nuit (SOLIDITE-1) — *proposée, pas posée*

Mécanique existante : `ops_alertes.signaler(db, cle, sujet, detail)` ouvre **un** incident (mail Vic +
cloche admin), au plus **un rappel/jour** ; `resoudre(db, cle)` referme et envoie « résolu ». C'est la
porte unique de SOLIDITE-1.

**① Entrée au registre** `src/labuse/jobs.py` (à placer après `filtres-sources`, touche `eau`) :

```python
_j("fraicheur-verrou", "Verrou de fraîcheur des sources — EN RETARD / DÉCALÉ / GELÉ sans motif",
   "quotidien", "20 3 * * *", "07:20", touche="eau", timeout_s=600,
   raison="Après la sonde (07:00) et les filtres (07:05) : rejoue scripts/coherence/fraicheur.py et "
          "ouvre UN incident ops_alertes si une source servie est EN RETARD, DÉCALÉE ou gelée sans "
          "motif. Le producteur a publié et on ne l'a pas vu ⇒ Vic est prévenu, une fois.",
   test="tests/test_cron1_registre.py::test_job_a_une_raison"),
```

**② Implémentation** `src/labuse/jobs_impl.py` (sur le modèle de `coherence_banc`) :

```python
def fraicheur_verrou(ctx: JobContext) -> None:
    from scripts.coherence import fraicheur
    from . import ops_alertes
    ecarts = []
    for nom, garde in fraicheur.GARDES:
        verdict, detail = garde()
        if verdict == "ECART":
            ecarts.append(f"{nom} — {detail}")
    ctx.compte(gardes=len(fraicheur.GARDES), ecart=len(ecarts))
    if ecarts:
        ops_alertes.signaler(ctx.db, "fraicheur-sources",
                             f"Fraîcheur des sources : {len(ecarts)} source(s) non à jour",
                             "\n".join(ecarts))
    else:
        ops_alertes.resoudre(ctx.db, "fraicheur-sources")
```

**③ Ligne de crontab** (générée par `deploy.sh` depuis le registre — ne pas éditer à la main) :

```
# quotidien · 07:20 Réunion · eau — Verrou de fraîcheur des sources (EN RETARD / DÉCALÉ / GELÉ sans motif)
20 3 * * *   labuse  sh -c 'set -a; . /etc/labuse/labuse.env; set +a; exec /opt/labuse/venv/bin/labuse jobs run fraicheur-verrou'
```

Placé à **07:20 Réunion**, après `sonde-sources` (07:00) et `filtres-sources` (07:05), pour lire une
sentinelle fraîche ; l'incident éventuel part avant le récap du matin (07:30). Dédup assurée par
`ops_alertes` (un incident `fraicheur-sources`, un rappel/jour max).

> **Note.** Tel quel, ce verrou déclencherait un incident **dès cette nuit** (DVF EN RETARD + ligne
> synthétique + FRR/EnR). C'est voulu — mais il faut poser le job **après** avoir traité #1-#4 du §1,
> sinon l'alerte sonnera tous les jours jusqu'au dégel DVF. Alternative : le brancher tout de suite et
> le laisser rappeler, comme aiguillon, jusqu'à résolution.

---

## 8. Limites

- Le journal `job_runs` prod ne remonte qu'au 13/10 : le « dernier succès réel » des jobs **mensuels**
  d'avant cette date (sitadel 10, dpe 12, sirene 7) n'y est pas ; la fraîcheur de leur **base** (dates
  max mesurées) les confirme à jour malgré tout.
- B/C mesurés finement pour les sources flux/servables ; pour le reste, le millésime `data_sources` fait
  foi (aucun comptage ligne à ligne des ~90 tables de fond).
- Le verrou n'a pas été **exécuté** sur le VPS (aucun code expédié en prod — lecture seule) : ses gardes
  ont été **rejouées requête par requête** via `ssh … psql` (§6).
