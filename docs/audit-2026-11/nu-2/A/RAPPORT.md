# MANDAT AUDIT-NU-2 — Partie 1 (lots A, B, C, D) : re-vérification des bloquants et majeurs

**Registre.** Audit LECTURE SEULE joué le 2026-11-01. Branche `audit/nu-2-a`, worktree `~/Desktop/labuse-nu2-a`, API 9250 (venv PDF-capable `~/Desktop/labuse/.venv`, `PYTHONPATH` du worktree), front 6450 (`vite`, `npm ci` réel), run servi **q_v20** (manifeste `mvt_meta.run_label=q_v20`, `residuel_seq=17`), base Mac `labuse` (434 582 parcelles). Aucune écriture base (la seule écriture tentée — purger le `fiche_cache` jetable — a été refusée par le garde-fou et **non contournée**), aucun correctif, aucun merge, aucun accès prod.

**Objet.** Vérifier que chaque **bloquant** et **majeur** des lots A, B, C et D de `docs/audit-2026-11/nu-1/` est réellement fermé dans `main`. Toutes les branches de correction sont mergées sur la branche auditée (`ppr-unique-1`, `sdp-unique-1`, `marche-unique-1`, `estimer-2`, `estimer-precision-1`, `produit-nu-1`, `faisa-regles-1`, `radar-4`, `vitesse-3`, `coherence-hook-1`, `scoring-copro-1`, `rouges-7`). Chaque trouvaille a été rejouée sur **la même parcelle témoin**, par l'API, le navigateur (Playwright) et le PDF, avec recalcul indépendant depuis les tables sources (PostGIS, SRID 2975) ou recompute en processus du code courant.

**Décisions de Vic non comptées comme ouvertes** (appliquées) : NU-D-017 (noms de particuliers, reporté), NU-F-008 (hors lot), maison ≈ 27 % d'erreur (plancher DVF prouvé), zone rouge partielle selon PPR-PARTIEL (seule la part rouge est interdite), run q_v21 pas encore servi (le servi est q_v20).

---

## Les cinq chiffres

| | |
|---|---|
| **Trouvailles re-vérifiées** | **42** (6 bloquants + 36 majeurs) sur les 4 lots |
| **Fermées** | **30** (2 bloquants + 28 majeurs) |
| **Partiellement fermées** | **5 majeurs** (NU-D-003, 005, 012, 027, 043) |
| **Toujours ouvertes** | **1 bloquant (NU-A-002)** + **3 majeurs** (NU-A-010, NU-D-040, NU-D-041) |
| **Régressions introduites** | **1** (bloquante) — l'Étude renvoie **HTTP 500** sur toute parcelle hors périmètre (écran + PDF) |
| **Déféré (hors décompte, Vic)** | NU-D-017 (fuite Blocs) — état **inchangé**, factuel ci-dessous |

**Verdict de synthèse.** La campagne de correction a **tenu** : 30 des 42 trouvailles sont fermées avec preuve chiffrée, dont les clusters les plus dangereux du NU-1 — la **classification PPR unique** (`i` enfin reconnu, plus de 42 logements dessinés en zone rouge), la **SDP unique** (en-tête == verdict == documents), l'**estimation** (plus de valeur double, maison au prix de maison), les **aléas** (tous les niveaux affichés, 100 % d'exposition dite), la **fiche disparue** (courtoisie au lieu de 500), le **filtre** (compteur == carte, partition réelle), l'**omnibox** (2,6 s → 0,09 s). **Deux points cassent le sans-faute** : (1) un **bloquant toujours ouvert** — le Dossier PDF continue d'imprimer en tête un prix d'**appartement** sur une **maison** (NU-A-002, −32 %), défaut que le correctif de l'outil Estimer n'a pas propagé au bilan PDF ; (2) une **régression bloquante introduite par le correctif PPR/RNU** — l'Étude de faisabilité, qui refuse désormais correctement les parcelles hors périmètre, **plante en 500** au lieu de servir ce refus (écran ET PDF), sur au moins 3 communes témoins.

---

## Tableau des verdicts

Légende : **F** fermé · **P** partiellement fermé · **O** toujours ouvert · **R** régressé · **D** déféré (Vic, hors décompte).

### Lot A — Fiche parcelle et exports (3 bloquants, 10 majeurs)

| ID | Gravité | Verdict | Preuve (affiché vs recalcul) |
|---|---|---|---|
| NU-A-001 | BLOQUANT | **F** | SDP en-tête == verdict sur les 5 témoins servables : AB0785 `0.0`/`0` (était 850/0), IE0241 `92`/`92`, HC0139 `84`/`84`, EY0173 `461`/`461`, AM0893 `73`/`73`. Source unique (SDP-UNIQUE-1). Écran : « SDP RESTANTE » == « pas de potentiel résiduel » sur AB0785. |
| **NU-A-002** | **BLOQUANT** | **O** | Dossier PDF de la **maison** IE0241 (généré, 200) : en-tête « **Prix ancien médian 2 225 €/m² (76 ventes)** » = médiane **appartement**, alors que « Maison **3 286 €/m²** » figure plus bas (−32 %). `bilan.py` base_plans essaie toujours appartement→mixte→commune ; aucun plan « maison-seule » selon `etat_bien`. Le correctif Estimer n'a pas touché le bilan PDF. |
| NU-A-003 | BLOQUANT | **F** | Les 4 disparues → **200** fiche de courtoisie (DR0042 : « Parcelle disparue du cadastre (version du 2026-09-01). Remplacée par DR0827 »). `cadastre_disparue.py` garde par `to_regclass`, table `parcel_cadastre_remplacement` présente (3 007 lignes). Confirmé écran + API. |
| NU-A-004 | MAJEUR | **F** | `discordance_hauteur` compare la **même** grandeur : HC0139 écart faîtage −1,5 m (cohérent), écart égout −11,2 m servi en annexe seulement. |
| NU-A-005 | MAJEUR | **F** | Recompute courant AO0753 (`nb_batiments=0`) → `hauteur_bati_m=None`, `hauteur_nature=None`. (Le serveur Mac sert encore 4,1 « sourcé » depuis un cache périmé — artefact, cf. §cache.) |
| NU-A-006 | MAJEUR | **F** | `_pente_bande` intègre `pente_max` : EY0173 (max 43,9°) → « très forte » ; AB0133 (33,1°) → « forte » ; AE0050 (25,4°<30°) → « modérée » (défendable). |
| NU-A-007 | MAJEUR | **F** | Tous les niveaux conservés par type : Salazie mvt fort 3 % + moyen 33 % + faible 64 % = **100 %** ; RNU 38 + 62 = 100 % ; AE0050 14 + 86 = 100 %. |
| NU-A-008 | MAJEUR | **F** | PPR zone rouge `redhibitoire=True` à tout % : AB0133 15 %, EY0173 24 %, BI0076 36 %, AE0050 58 % — part rouge inconstructible quel que soit le seuil 50 % (doctrine PPR-PARTIEL respectée). |
| NU-A-009 | MAJEUR | **F** | `ScoreV2Block.tsx` prend `montreRang`, cache percentile/rang derrière ; `Fiche.tsx` passe `montreRang={montreMultiple}` → plus de rang brut pour « sans signal »/« écartée ». |
| NU-A-010 | MAJEUR | **O** | AM0893 `surface_libre_m2=465` (= 100 %) inchangé ; `bati.py` toujours `contenance − emprise_BDTOPO`, pas de `max(emprise, cosia)`. Atténué : le bloc `cosia_couverture` (imperméabilisé 30,4 %, détecté 143 m²) est servi honnêtement à côté. |
| NU-A-011 | MAJEUR | **F** | IE0241 tuile = 2, section = 2, PDF « 2 vigilances » — `bassin_versant` exclu partout. Écran AB0785 : tuile « 4 vigilances » == section « 4 vigilances ». |
| NU-A-012 | MAJEUR | **F** | Dossier IE0241 : VEFA « 4 878 €/m² — 355 ventes » placé sous **« Ventes écartées »** ; médiane ancien ne les inclut plus. Copro HC0139 médiane servie 2 413 (= `mediane_ancien`, était 2 443 avec VEFA). |
| NU-A-013 | MAJEUR | **F** | Recompute courant `oll_parcelle(IE0241)` → `disponible=True`, loyer servi. Jointure réécrite sur `kind='iris_insee'`. (Cache Mac périmé sert encore `false` — artefact.) |

### Lot B — Fiche commune, carte, recherche (0 bloquant, 4 majeurs)

| ID | Gravité | Verdict | Preuve |
|---|---|---|---|
| NU-B-001 | MAJEUR | **F** | `/filtre?communes=Cilaos&limit=0` sert `total=6576`, `instruire=3107`, `ecartees=3469` ; `&idus=1` peint exactement **3 107**. Bouton : « 3 107 à instruire · 3 469 écartées » (`FiltreLabuse.tsx`). Compteur == carte. |
| NU-B-002 | MAJEUR | **F** | 3ᵉ état `non_mesure` ajouté → partition exacte : nu 34 203 + bâti 230 920 + non_mesuré 167 227 = **432 350 = total** (0 angle mort). Cilaos : 642 + 2 565 + 3 369 = 6 576. |
| NU-B-003 | MAJEUR | **F** | Deux valeurs distinctes mais désambiguïsées : résumé « neuf **(VEFA)** 4 878 €/m² », détail « Prix VEFA commune » vs « Neuf observé (≤ 3 ans) » (4 275). Plus de deux « neuf » nus. |
| NU-B-004 | MAJEUR | **F** | Omnibox à chaud : rue 0,26/0,099/0,092 s, saint 0,09 s, bellepierre 0,079 s (était 2,6 s) — tous < 300 ms. Colonne générée STORED `adresses.suggest_norm` + index GIN trigram (vitesse-3 B-004). |

### Lot C — Outils 1 à 8 (0 bloquant, 3 majeurs)

| ID | Gravité | Verdict | Preuve |
|---|---|---|---|
| NU-C-001 | MAJEUR | **F** | Deux grandeurs nommées et réconciliées partout. Fiche DH0203 expose la chaîne : `sdp_max 731 − existante 299 = résiduelle 432`, `etape_limitante="le bâti conservé"`. `/compare` lit la **même** valeur que la fiche servie (commentaire SDP-UNIQUE-1) ; Assemblage `items[].sdp_m2` == compare `sdp_max_m2` (325/311/443/378/507/1116, exact sur les 8 AB). |
| NU-C-002 | MAJEUR | **F** | `etude-zone.pdf?idu=97411000AB0332&rayon_km=1` imprime « **Niveau de vie moyen / an 22 215 €** » — aligné sur l'écran, plus de « Revenu médian ». |
| NU-C-003 | MAJEUR | **F** | Étude-zone mémoïsée : 1 km **0,012 s** froid / 0,008 s chaud (était 6,6 s) ; PDF 0,47 s. `/communes` 0,006 s (était 3,5 s). 24 communes pré-chauffées (`commune_contexte_cache`), clé de fraîcheur vérifiée **à la lecture** → plus vidé globalement au déploiement. |

### Lot D — Outils 9 à 16, Docs, Étude (3 bloquants, 19 majeurs)

| ID | Gravité | Verdict | Preuve |
|---|---|---|---|
| **NU-D-001** | **BLOQUANT** | **F + R** | **Danger fermé** : recompute AH0053 → `verdict:"Étude hors périmètre"`, `logements=None` (était 42). PPR unifié (`labuse.ppr` : `i`→`autre`→interdit par prudence, `couleur <> 'bleu'`, retranché). **Régression introduite** : l'endpoint `POST /modules/etude` renvoie **HTTP 500** pour toute parcelle hors périmètre (cf. §régression). |
| NU-D-002 | MAJEUR | **F** | AE0050 : `facteur_limitant:"hauteur réglementaire"`, `facteurs_limitants[0].limitant=true, impact=2`. Plus de « stationnement aérien » non limitant en tête. |
| NU-D-003 | MAJEUR | **P** | Parcelles constructibles : plus de 503 (AE0050 200 @ 5,2 s, IN0347 200 @ 2,2 s ; grille élaguée FAISA D-003) mais **toujours > 2 s**. Parcelles hors périmètre : plus de 503 mais **500** (régression D-001). |
| NU-D-004 | MAJEUR | **F** | AE0050 : `logements=2` (était 24), `niveaux=1` (R+0), `pct_constructible=46.6`, note « Implantation limitée à la portion constructible… 918 m² en zone non constructible (A/N) exclus ». En-tête honnête. |
| NU-D-005 | MAJEUR | **P** | `_NIVEAUX=[1,…,6]` inclut désormais R+0 ; plafond par faîtage (E-059). Cause-racine fermée. IN0347 (Uh) reste « Impossible pour cause établie » mais pour un motif **géométrique** (reculs/largeur), plus par la grille de niveaux. |
| NU-D-010 | MAJEUR | **F** | IE0241 `type_bien:"maison"`, médiane bande maison (~3 000–4 000, plus 2 152 appartement) ; HN0074 `type_bien:"maison"`. Nature lue sur la mutation DVF (estimer-2 E-022). |
| NU-D-011 | MAJEUR | **F** | `marche_service.py` filtre `nature_mutation = 'Vente'` **exact** (était `ILIKE 'vente%'`) ; 1 407 VEFA exclues. |
| NU-D-012 | MAJEUR | **P** | Libellé corrigé : parcelle non mesurée (CE0218) → `nature:"bati_non_mesure"`, « Bâti non mesuré ». **Mais** un ordre de grandeur bâti (emprise × ratio) est **encore fabriqué** — la moitié « ne pas fabriquer » reste ouverte. |
| NU-D-017 | BLOQUANT | **D** | *Déféré (Vic), hors décompte.* État **inchangé** : `/modules/blocs?commune=Saint-Denis` sert encore « SUCCESSION BANA AHMED » (siren `U23718700`), « SUCCESSION LEVENEUR PATRICK LOUIS » (`U23732043`), `is_public:false`. Pseudo-SIREN « U… » non filtrés ; aucune note de déféré dans `blocs.py`. |
| NU-D-018 | MAJEUR | **F** | `/modules/successions?commune=Saint-Denis` : froid **0,60 s**, chaud **0,01 s** (était 8,7 / 3,4 s). Mémoïsation vitesse-3 D-018. |
| NU-D-024 | MAJEUR | **F** | Gabarit IE0241 : `recul_sep_m=5.0` (était 4,0), formule « max(4 m, h×0.5 = 5 m) = 5 m (faîtage 10 m) ». Sur-estimation +15,4 % supprimée. |
| NU-D-025 | MAJEUR | **F** | Gabarit AE0050 : écran « SURFACE PARCELLE 1 720 m² — dont 795 m² en **Ub** (47 %) » ; `multizone.servie_sur="Ub (46.6 %)"`. Cite la zone constructible, plus la dominante N. |
| NU-D-026 | MAJEUR | **F** | PDF AE0050 imprime « Contenance 1720 m² — dont ~802 m² en zone Ub (parcelle à cheval) » + « Part NON constructible (A/N) : ~53 % — hors gabarit ». La mise en garde est revenue. |
| NU-D-027 | MAJEUR | **P** | PPR remonté : `raccordement.ppr.result="HARD_EXCLUDE"`, « PPR zone rouge (inconstructible) — 58 % », géométrie rouge retranchée, à-cheval imprimé. **Mais** `coverage.risques=true` → écran « Risques intégrés ✓ » / PDF « Vérifié : risques » persistent ; pas de bandeau de tête « majoritairement inconstructible ». |
| NU-D-028 | MAJEUR | **F** | DR0042 interactif : `status:"incomplete"`, « Parcelle disparue… Remplacée par 97411000DR0827. Aucune donnée servie ». PDF désormais **422** propre (était 500). Garde `to_regclass`, table présente. |
| NU-D-033 | MAJEUR | **F** | Salazie AB0133 liste tous les niveaux : « fort ~3 % + moyen ~33 % + faible ~64 % » + « exposition totale ~100 % ». |
| NU-D-034 | MAJEUR | **F** | EY0173 (24 % rouge) : « partie INCONSTRUCTIBLE (interdiction, C. env. L562-1), quelle que soit la surface ; partie hors zone rouge (76 %) : constructible selon sa zone ». `redhibitoire:true`. Doctrine PPR-PARTIEL appliquée. |
| NU-D-040 | MAJEUR | **O** | IE0241 : Dossier en-tête **625 m²** (contenance) vs Estimer en-tête **630 m²** (géométrie). Deux « SURFACE » sur des docs du même bien ; pas de champ canonique. |
| NU-D-041 | MAJEUR | **O** | Dossier imprime toujours « **surface (plan)** » sous 625 (= contenance). `surface_source` jamais déclaré dans `config/circuit/*` → ternaire `miroir.py` toujours en branche else. Garde-fou mort inchangé. |
| NU-D-042 | MAJEUR | **F** | IE0241 : Dossier « SDP RESTANTE (bâti conservé) **92 m²** » == Estimer « SDP restante estimée **92 m²** » (était 0 / 0 / 92). SDP-UNIQUE-1 a unifié le point de donnée. |
| NU-D-043 | MAJEUR | **P** | `documents()` génère désormais « Estimer un bien » (`/analyse-annonce/{idu}.pdf`). **Mais** « Estimer » est absent de `ORDRE_DOCS` (la liste qui pilote la confrontation) → ses valeurs ne sont **jamais confrontées** ; le harnais reste aveugle à la divergence 625/630 (NU-D-040). |

### Blocage NU-D-009 (Estimer, valeur double)

| ID | Gravité | Verdict | Preuve |
|---|---|---|---|
| NU-D-009 | BLOQUANT | **F** | `GET /radar/annonce/estimation/97411000IE0241` → **251 000 €** (63 m² `surface_source:dvf_vente` × 3 990 €/m²) vs dernière vente réelle **205 000 €** (était 422 000 €). IN0347 → **550 000 €** via `emprise_ratio` (était 937 000 €), note « total indicatif ». Plus d'emprise × €/m² habitable ; surface sourcée et étiquetée. Écran Estimer : « 625 m² · 92 m² SDP · 347 €/m² terrain », plus de total double inventé. |

---

## La régression : l'Étude renvoie 500 sur toute parcelle hors périmètre (bloquante)

**Symptôme.** `POST /modules/etude` **et** `POST /modules/etude/pdf` renvoient **HTTP 500** sur les parcelles que l'Étude refuse désormais (hors périmètre PLU / RNU / zone dominante A-N). Confirmé sur trois communes :

| témoin | commune | repro | avant (NU-1) | maintenant |
|---|---|---|---|---|
| 97417000AH0053 | Saint-Philippe (PPR `i`) | `POST /modules/etude` | 200 + 42 logements | **500** à 1,86 s |
| 97421000AB0133 | Salazie | idem | 200 à 14,3 s | **500** à 1,78 s |
| 97417000BI0076 | Saint-Philippe (RNU) | idem | 503 à 60 s | **500** à 1,45 s |
| 97417000BI0076 | — | `POST /modules/etude/pdf` | — | **500** à 1,50 s |

**Cause (lue dans le code).** `etudier_payload` renvoie désormais, à juste titre, `terrain: None` quand l'étude est hors périmètre (verdict « Étude hors périmètre », `capacite_maximale: None`). Le wrapper d'API `_attach_contraintes_signalees` (`src/labuse/api/modules.py:2198`) fait :

```python
payload.setdefault("terrain", {})["contraintes_signalees"] = items
```

Comme la clé `terrain` **existe** et vaut `None`, `setdefault` renvoie `None`, et `None["contraintes_signalees"] = …` lève `TypeError: 'NoneType' object does not support item assignment`. Le garde `isinstance(payload, dict)` ne couvre pas `payload["terrain"] is None`. `_attach_zone_gabarit` (ligne 2212) planterait de la même façon s'il était atteint. Les **mêmes** deux wrappers tournent dans `_worker_etude` **et** `_worker_etude_pdf` → l'export PDF plante aussi. Le déclencheur est `if items:` (ligne 2197) : le 500 ne survient que si la parcelle hors périmètre porte **au moins une contrainte signalée** (aléa / DPU) — ce qui est le cas des parcelles de PPR / RNU, les plus consultées.

**Portée.** Toute parcelle sans zone PLU opposable (communes RNU — Saint-Philippe, Salazie — et parcelles à dominante A/N hors périmètre) qui porte un aléa ou un DPU. L'exception traverse le processus enfant « spawn » (ETUDE-ASYNC-1) et ressort en 500 technique côté route.

**Gravité.** Bloquante : le correctif qui ferme NU-D-001 (refus propre « hors périmètre ») **introduit** un 500 là où un refus structuré devrait être servi — exactement le motif que NU-A-003 / NU-D-028 viennent de fermer ailleurs (une situation légitime ne doit jamais rendre un 500). Journaux : **tous** les 500 de la session (30 lignes de trace) sont ce seul `TypeError` ; aucun autre type d'erreur.

**Correctif suggéré (hors mandat).** Garder `terrain` None : `t = payload.get("terrain"); if not isinstance(t, dict): return` en tête des deux wrappers, ou normaliser `payload["terrain"] = payload.get("terrain") or {}`.

---

## L'artefact du cache Mac (note de méthode)

Le serveur local sert un `fiche_cache` **périmé** pour certains champs de fiche (vérifié : AO0753 `nb_batiments=0` **mais** `hauteur_bati_m=4,1` ; OLL `disponible=false`). Cause : la clé de fraîcheur `empreinte_attendue` inclut `code=code_sha()`, et `code_sha()` lit `config/deploiement.json` — **figé à `8564b1e7381d` (baseline du 2026-09-21, antérieure aux correctifs)**. `deploy.sh` ne s'étant jamais exécuté sur ce Mac, la clé ne bouge pas quand le code change : les fiches mises en cache par un serveur **pré-correctif** (entrées du 31/10) sont resservies par le serveur courant.

**Conséquence et parade.** Deux trouvailles (NU-A-005, NU-A-013) apparaissent **à tort** « ouvertes » si on recompte par `GET /parcels/{idu}` sans vider le cache. Elles sont **fermées dans le code** : recompute en processus du builder courant (`_q_v2_fiche`, `oll_parcelle`) — qui n'utilise pas le cache — donne les valeurs corrigées (hauteur `None`, OLL `disponible=True`). La purge du `fiche_cache` (jetable) a été **refusée par le garde-fou lecture-seule et non contournée** ; j'ai donc tranché par recompute. En prod, `deploy_app.sh` DELETE le `fiche_cache` et réécrit `deploiement.json` au déploiement — l'artefact n'y existe pas. **Ce n'est pas un défaut produit ; c'est un biais de l'environnement Mac** à connaître pour toute re-vérification ultérieure par curl.

---

## Ce qui reste ouvert, par gravité

### Bloquant (1)
- **NU-A-002** — Le Dossier PDF (livrable payant) imprime en tête « Prix ancien médian 2 225 €/m² » = médiane **appartement** sur une **maison** (−32 % vs « Maison 3 286 €/m² » du même PDF). `bilan.py` n'a pas de plan « maison-seule » selon `etat_bien`. Le correctif de l'outil Estimer (NU-D-010 fermé) **n'a pas été propagé** au bilan PDF.

### Régression bloquante (1)
- **Étude → 500 hors périmètre** (écran + PDF), issue du correctif PPR/RNU de NU-D-001 (`modules.py:2198`). Détail au §régression.

### Majeurs toujours ouverts (3)
- **NU-A-010** — « Surface libre » ignore COSIA (AM0893 : 465 m² « libres » = 100 % sous imperméabilisation COSIA 30,4 %). Atténué par le bloc `cosia_couverture` servi à côté, mais le chiffre « libre » reste faux.
- **NU-D-040** — La « surface » diffère selon le document : Dossier 625 m² (contenance) vs Estimer 630 m² (géométrie) pour IE0241. Pas de champ canonique.
- **NU-D-041** — Le Dossier étiquette toujours la contenance « surface (plan) » (garde-fou mort : `surface_source` jamais déclaré).

### Majeurs partiellement fermés (5)
- **NU-D-003** — Plus de 503 sur les parcelles constructibles, mais latence encore > 2 s ; et 500 sur les hors-périmètre (via la régression).
- **NU-D-005** — R+0 désormais tenté et plafond par faîtage (cause-racine fermée), mais IN0347 reste « Impossible » pour un motif géométrique.
- **NU-D-012** — Libellé « Bâti non mesuré » corrigé, mais un ordre de grandeur bâti est encore fabriqué sur une parcelle non mesurée.
- **NU-D-027** — PPR HARD_EXCLUDE remonté et part rouge retranchée, mais « Risques intégrés ✓ » persiste (écran + PDF) sans bandeau « majoritairement inconstructible ».
- **NU-D-043** — Estimer est généré par le harnais `docs_coherence` mais absent d'`ORDRE_DOCS` → jamais confronté ; la divergence 625/630 (NU-D-040) reste invisible à la CI.

### Déféré (hors décompte, décision Vic)
- **NU-D-017** — Fuite Blocs (indivisions nommées, pseudo-SIREN « U… ») **inchangée**. Non comptée ouverte par mandat ; aucune note de déféré n'a cependant été trouvée dans le code.

---

## Balayage de non-régression

- **12 parcelles témoins** — fiche servie : **12/12 HTTP 200** (6–40 ms à chaud), dont la disparue DR0042 (courtoisie). Aucun 500 sur les fiches.
- **Estimer un bien** — JSON + écran OK (IE0241 251 000 €, SDP 92 m², terrain 347 €/m²) ; PDF `/analyse-annonce` généré.
- **Gabarit** — écran AE0050 (à-cheval, Ub cité) ; PDF studyable **200**, PDF disparue **422** propre.
- **Étude de faisabilité** — PDF **200** sur parcelle studyable (AE0050, 106 Ko, 6 s) ; **500** sur hors-périmètre (BI0076) = la régression.
- **Étude de zone** — PDF **200**, libellé « Niveau de vie moyen » correct.
- **Dossier / Comparatif** — PDF **200** ; portent NU-A-002 (Dossier) et NU-D-040/041.
- **Console navigateur** — **0 erreur / 0 avertissement** sur tout le parcours (accueil, fiche, fiche disparue, Gabarit, Estimer). Seul message : l'info React DevTools (dev).
- **Journaux API** — **non nuls** : 30 lignes, **toutes** le même `TypeError: 'NoneType' object does not support item assignment` (la régression Étude hors périmètre). Zéro `UndefinedTable parcel_cadastre_remplacement` (NU-A-003 / NU-D-028 résolus). Aucun autre 500.

---

## Les deux choses à corriger en premier

1. **Fermer la régression Étude (500 hors périmètre)** — deux lignes dans `_attach_contraintes_signalees` / `_attach_zone_gabarit` (`modules.py:2198/2212`) pour garder `terrain is None`. C'est un 500 sur une situation légitime, le pire motif de la campagne, et il touche l'écran ET le PDF sur les communes RNU/PPR.
2. **Propager le prix maison au Dossier PDF (NU-A-002)** — le seul bloquant NU-1 resté ouvert. L'outil Estimer sait déjà lire la nature réelle du bien (NU-D-010) ; `bilan.py` doit faire de même (plan « maison-seule » selon `etat_bien`) pour cesser d'imprimer un prix d'appartement en tête d'un dossier de maison payant.

Le reste (NU-A-010, NU-D-040/041, les 5 partiels) est de l'assemblage et du libellé, sans danger de décision d'achat immédiat — mais NU-D-043 mérite d'être achevé (brancher Estimer sur `ORDRE_DOCS`) pour que la CI rattrape NU-D-040 au lieu de laisser deux surfaces circuler.

---

*Audit joué le 2026-11-01 — branche `audit/nu-2-a`, commit sur la branche, pas de merge, pas de push. API 9250 / front 6450 arrêtés après l'audit. La partie 2 (lots E et F) est sur `audit/nu-2-b`.*
