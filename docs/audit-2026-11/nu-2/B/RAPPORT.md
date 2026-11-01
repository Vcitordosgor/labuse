# AUDIT-NU-2 · Partie 2 (Lots E & F) — vérification de clôture

**Branche** `audit/nu-2-b` · worktree `~/Desktop/labuse-nu2-b` · HEAD `7ae0efbc1` (= tip de `main`, toutes les branches fix mergées) · API `:9260` (run servi **q_v20**) + 2ᵉ instance `:9261` (`LABUSE_SERVED_RUN=q_v21`) · front `:6460` (vite dev → API 9260) · base locale `labuse` · **LECTURE SEULE** (aucun correctif, aucun merge, aucun accès prod ; recalculs SQL sous `default_transaction_read_only=on` ; aucune écriture de fichier suivi — q_v21 servi via l'override d'env prévu, jamais le manifeste).

Date : 2026-11-01. Modèle : Opus. Objet : rejouer chaque **bloquant** et **majeur** des rapports `docs/audit-2026-11/nu-1/E/RAPPORT.md` et `.../F/RAPPORT.md`, et dire s'il est réellement fermé dans `main`.

Méthode : pour chaque trouvaille, (a) relecture du code courant à la ligne citée, (b) rejeu de la reproduction — recalcul SQL indépendant pour les moteurs (lot E), parcours navigateur + API + Copilote live pour le transversal (lot F). Verdict exigeant : **« fermé » demande une preuve que la sortie a changé**, pas seulement qu'une branche fix a été mergée.

Décisions de Vic **non comptées comme ouvertes** (par mandat) : NU-F-023 (`/moi` role/statut), retrait du rattachement auto du Radar (NU-E-039/042), « valeur créée » gardée en interne (NU-E-012 côté produit), run q_v21 prêt mais pas encore servi en prod.

---

## Chiffres en tête

- **Scénarios rejoués : ~90** — 13 témoins × recalculs SQL de masse + ~40 appels API/curl + 10 questions-pièges Copilote live + 30 parcelles tirées au sort (classement q_v21) + 3 écrans navigateur.
- **Lot E** (10 bloquants, 27 majeurs instruits) : **bloquants** → 4 fermés, 2 partiels, **1 toujours ouvert (E-038)**, **1 régression (E-055)**, 2 = décision Vic. **majeurs** → majorité fermés ou partiels, détail en table.
- **Lot F** (3 bloquants, 21 majeurs) : **les 3 bloquants fermés** ; **majeurs** → 18/21 fermés, 1 partiel (F-013), 1 décision Vic documentée (F-008), F-018 fermé en code (reste config prod).
- **Non-régression** : classement q_v21 ↔ fiche ↔ filtres **cohérent** (30/30 fiches, bandes = paliers à 876 slivers près) ; Copilote 10/10 pièges **propres** ; sécurité SSRF **fermée** ; console navigateur **0/0** ; journaux API = **3 erreurs, racine unique = la régression E-055**.

**Les deux choses qui doivent remonter avant tout :**
1. **NU-E-055 est une régression servie** : le moteur refuse bien le RNU (plus de zone « UA » inventée), mais `POST /modules/etude` renvoie **HTTP 500** sur toute parcelle RNU portant un aléa (reproduit 3×). Le refus honnête n'atteint pas le client.
2. **NU-E-010 / NU-E-011 sont fermés dans le code mais PAS dans ce que voit l'utilisateur aujourd'hui** : le masque copro n'existe que dans q_v21 (non servi ; q_v20 porte toujours 393 copros en palier), et la fiche sert encore `fraction=1/20` depuis un `fiche_cache` périmé que `config/deploiement.json` (sha pré-merge) n'invalide pas. Le chemin non caché (`/v2/score/{idu}`) est, lui, correct.

---

## Lot E — Moteurs (recalcul indépendant)

### A — Résiduel & SDP + G (cross-cohérence)

| Trouvaille | Gravité | Verdict | Preuve (code courant + recalc) |
|---|---|---|---|
| NU-E-001 deux SDP résiduelles dans la même fiche | BLOQ | **fermé** | `app.py:6592/7140` + réconciliation `:6706-6717`/`:7146-7158`. Curl : IC0114 **68 = 68**, CT1164 **81 = 81** (audit : 68≠64, 81≠70). |
| NU-E-002 run résiduel servi périmé, assiette NULL | BLOQ | **fermé** | `residuel_runs` servi = **seq 17 / q_v20, 2026-10-21** ; `assiette_source` peuplé 265123/433229 (NULL = lignes écartées légitimes). Recalc 11/15 reproduisent (±1 m²). |
| NU-E-003 deux chemins d'assiette → capacités incompatibles | BLOQ | **partiellement fermé** | Servi mono-valué (CT2637 → 8827 partout ; AN0134 → terrain_exigu partout ; recompute legacy écarté s'il diverge de >1 m², `app.py:6818-6823`). Mais défauts moteur toujours incohérents (`db.py` clip=True vs `residuel.py` clip=False). Contradiction **produit** close, défaut **moteur** non. |
| NU-E-004 « 76 % bâti + démolition » vs « 0 m² bâti » | MAJ | **partiellement fermé** | Écrasement CoSIA toujours là (`residuel.py:199-201`) mais source visible (`source_bati="BD TOPO + CoSIA"`, bloc `cosia_couverture`), plus de mot « démolition », flag `hauteur_bati_supposee`. |
| NU-E-005 double-compte bâti (SUM sans ST_Union) | MAJ | **fermé** | `bati.py:110-130` unionne. AN0134 : **89,5 m²** (était 268,5 / 258 %). |
| NU-E-006 booléen littoral annule toute la parcelle | MAJ | **fermé** | `engine.py:804-812` facteur = `max(0,1−littoral_pct)` proportionnel. |
| NU-E-007 SDP sur hauteur-placeholder non signalée | MAJ | **fermé** | `hauteur_bati_source`/`supposee`/note servis (`app.py:6638/6858`), run porte `hauteur_source`. |
| NU-E-008 SDP ×0,45 occupation invisible | MIN | **partiellement fermé** | coef 0,45 toujours appliqué mais exposé dans `steps[]`/`hypotheses[]` et éditable. |
| NU-E-009 exceptions avalées tiroirs | DETTE | **partiellement fermé** | `residuel.py:317` journalise désormais ; `bati.py` tiroirs toujours muets. |
| NU-E-052 emprise bâtie incohérente 165 vs 239 « BD TOPO » | MAJ | **partiellement fermé** | Deux valeurs persistent (**65,8 % divergent >20 %**) mais libellés honnêtes et distincts (source `max(BD TOPO, CoSIA)` explicitée) ; `parcel_residuel_bati` orphelin. Faux « deux fois BD TOPO » corrigé ; source unique non atteinte. |
| NU-E-053 surface dessin étiquetée « cadastre » | MIN | **partiellement fermé** | En-tête reste `526 / "cadastre"` mais `contenance_m2=543` servie et désormais utilisée pour valoriser (Comparatif/Dossier) + flag `surface_incertaine`. |

### B — Scoring & bandes

| Trouvaille | Gravité | Verdict | Preuve |
|---|---|---|---|
| NU-E-010 copro reçoit un palier (doctrine « hors palier ») | MAJ | **fermé en code, PAS dans le run servi** | `statuts.py:288-291` masque copro→sans_signal. SQL : **q_v20 servi = 393 copros en palier (70+323)** ; q_v21 (non servi) = 0. Le masque est prouvé dans q_v21 seul. |
| NU-E-011 copro « Écartée » servie « 1/20, au-dessus de la moyenne » | MAJ | **fermé en code, PAS dans la sortie servie** | `score_v2.py:84` + `app.py:4607` annulent mult/fraction/mot pour copro. `/v2/score/AV0167` (non caché) correct. Mais `/parcels/AV0167` live sert encore `fraction=1/20, "nettement au-dessus"` depuis `fiche_cache` périmé (`deploiement.json` sha pré-merge). |
| NU-E-012 `valeur_creee_eur` = CA brut sans coût (878 M€) | MAJ | **toujours ouvert (défaut), atténuation tient** | `potentiel.py:124` toujours sdp×€/m², min/max = ×q1/q3 (dispersion prix, pas de coût). max 878 615 230 €. **0 écran/PDF ne la lit** (grep) → décision Vic « interne » respectée. |
| NU-E-013 SDP scoring périmée (48 %) | MAJ | **fermé** | recalc `potentiel_sdp_m2 IS DISTINCT FROM round(sdp)` = **0/433229** (q_v20 ET q_v21). L'alarme 48 % était l'artefact du run 1 Mac. |
| NU-E-014 `prix_secteur` communal + millésime incomplet | MAJ | **partiellement fermé** | renommé `prix_commune_eur_m2` (nom honnête) ; granularité toujours `left(idu,5)` ; pas de N-minimum. |
| NU-E-015 étage 0 sur run cascade ≠ run scoré | MAJ | **fermé (garde)** | `bascule_gardes.check_etage0_aligne` ; run servi aligné (q_v20 sur cascade q_v19_sources). `pipeline.py:381` défaut inchangé mais état servi cohérent. |
| NU-E-016 `event_age_mois` horloge OS | MIN | **toujours ouvert** | `pipeline.py:390` `Timestamp.today()`. Impact nul sur paliers servis. |
| NU-E-017 `plancher_c` NULL→0 | MIN | **toujours ouvert (décision produit)** | `statuts.py:69` `fillna(0)`, différé par commentaire. |
| NU-E-018 exception snapshot avalée | DETTE | **toujours ouvert** | `pipeline.py:566-569` `[]` sans warn. |
| NU-E-019 seuils ICD en dur + assert crashant | DETTE | **toujours ouvert** | `icd.py:57-58` assert présent. |
| NU-E-020 `assign_tiers` mort + spec périmée | DETTE | **partiel** | `assign_tiers` toujours présent (mort) ; flag copro confirmé sain. |

### C — Estimation (« Estimer un bien »)

| Trouvaille | Gravité | Verdict | Preuve |
|---|---|---|---|
| NU-E-021 valeur bâtie = emprise × €/m² HABITABLE | BLOQ | **fermé** | `_surface_pour_total` (`pige/api.py:1724`). CT1164 : **478 000 €** (surface **122 m²** = emprise 239 × ratio commune 0,51, × 3920 €/m²), plus 784 000 €. Le bug d'unité est éliminé ; tout écart résiduel est du calibrage, pas une faute d'unité. |
| NU-E-022 nature lue de la parcelle, pas de la mutation | BLOQ | **fermé** | `_derniere_mutation_dvf` (`api.py:1484`), branche `:1684`. BN2939 : nature **nue/terrain**, **117 000 €** (fourchette 95k–139k ; vendu 140k), plus 59 000 € en maison. |
| NU-E-023 parcelle sujet dans ses propres comparables | MAJ | **fermé** | `marche_service.py:416` (bâti `mutation_id NOT IN …`), `:541` (terrain `id_parcelle <> :idu`). |
| NU-E-024 ±% en dur vendu comme « fiabilité » + 2ᵉ chiffre divergent | MAJ | **partiellement fermé** | Bâti/copro dérivent de n+IQR (`_fiabilite_bien`, CT1164 26 %, AV0167 18 %). **Terrain toujours en dur** (`_ECART_SEGMENT`), et `estimation_prix.py:28 DEMI_LARGEUR=0.30` divergent alimente encore un autre chemin (bilan/Copilote) — non unifié. |
| NU-E-025 pas de filtre VEFA/viager/multi-lot | MAJ | **fermé (VEFA), partiel (viager)** | `nature_mutation = 'Vente'` strict ; terrain dédoublonné `max() PARTITION BY`. Pas de prédicat viager explicite. |
| NU-E-026 branche copro inatteignable si « nue » | MAJ | **fermé** | `api.py:1662` copro avant terrain. AV0167 → copropriete/appartement, valeur_indicative=None. |
| NU-E-027 nature « inconnue » : médiane servie sans réserve | MIN | **partiellement fermé** | AH0007 → `bati_non_mesure` (étiqueté), valeur_indicative=None ; pas de phrase « nature non déterminée ». |
| NU-E-028 repli commune silencieux | MIN | **partiellement fermé** | flag `commune_fallback` servi → force fiabilité « Limitée » + libellé « commune entière ». Pas de phrase complète. |
| NU-E-029 trois chemins de médiane bâti | DETTE | **toujours ouvert** | 3 lecteurs coexistent sans test de cohérence. |

### D — Marché DVF

| Trouvaille | Gravité | Verdict | Preuve |
|---|---|---|---|
| NU-E-030 VEFA blanchie en prix de l'ancien | MAJ | **fermé** | `marche_service.py`/`bilan.py` → `= 'Vente'` ; VEFA marquée et exclue de la médiane servie (`bilan.py:291`). |
| NU-E-031 dénominateur terrain = somme des lignes (×146) | MAJ | **fermé** | `marche_service.py:536` `max(...) OVER (PARTITION BY id_mutation,id_parcelle)`. |
| NU-E-032 `dvf_secteur_medianes` cache figé jamais invalidé | MAJ | **partiellement fermé** | Code ajouté (`millesime_dvf`, `caches_marche_perimes`) **MAIS table locale servie toujours figée 2026-08-17, sans la colonne, et `caches_marche_perimes` n'a aucun appelant** (diagnostic mort). Dette de **donnée**, pas de code. |
| NU-E-034 « marché bâti commune » Radar = une parcelle | MIN | **partiellement fermé** | Chemin servi corrigé (`bien_vs_marche`→`mediane_commune`, n>1000) ; `_dvf_bati` single-parcelle survit mais documenté « jamais servi comme le marché ». |
| NU-E-035 VTB avec bâti dans le comparateur bâti | MIN | **fermé** | `= 'Vente'` exclut VTB. |
| NU-E-036 deux planchers / deux prédicats de nature | DETTE | **partiellement fermé** | Divergence comportementale résolue ; `ILIKE '%vente%'` subsiste sur des chemins *tendance* (`marche_commune.py`, `zone.py`). |
| NU-E-037 docstring `neuf_vefa_commune` « 3 ans » vs code 5 | DETTE | **toujours ouvert** | `dvf_marche.py` docstring 3 ans, code 5 ans. |

### E — Radar / pige

| Trouvaille | Gravité | Verdict | Preuve |
|---|---|---|---|
| NU-E-038 299/416 biens `retiree` par fausse confirmation, jamais nettoyés | BLOQ | **TOUJOURS OUVERT** | **300/513 biens retiree (58,5 %), 0 vendue, 0 retiree_sans_vente** ; restauration jamais rejouée. `pige_passes` : n_supprimees **107/1/134/55/11 = 308**, `n_pages==n_supprimees` (signature intacte). Délai médian de retrait servi sur 223 retraits fantômes. **Dette de donnée, servie par l'API courante.** |
| NU-E-039 rattachement réel 0/416 → aval mort | BLOQ | **décision Vic** | `_rattacher`→`non_rattachee` (RADAR-4, retrait assumé) ; `rattachement_html.py` supprimé. Conséquence voulue, pas un bug. |
| NU-E-040 dédoublonnage sauté pour « à qualifier » | MAJ | **fermé (code), legacy non backfillé** | `html_ingest.py:392` `bien_meme_physique(exact_only=True)` AVANT la garde motif. Paire #284/#332 persiste (ingérée avant le fix ; `fusionner_doublons_existants` jamais joué). |
| NU-E-041 dédoublonnage inter-portail jamais exercé | MAJ | **toujours ouvert** | Bien'ici présent (97 biens) mais chargé séparément → **2–3 vrais doublons exacts inter-portail en base** (#344↔#1000347, #341↔#1000388). |
| NU-E-042 rayon 60/150 m ne rattache rien | MAJ | **décision Vic** | cascade supprimée (RADAR-4). |
| NU-E-043 biens sans date de publication | MIN | **toujours ouvert** | 77 biens sans date → `en_vente_longue` jamais déclenchée pour eux. |
| NU-E-044 deux idiomes de fuseau dans le cycle | MIN | **toujours ouvert** | `cycle.py:61` `now()-interval` vs frère en heure Réunion. Inoffensif. |
| NU-E-045 file `a_confirmer` rejoue sur fantômes | DETTE | **toujours ouvert** | Lié à E-038 non purgé. |

### F — Copilote (vérifié live, 10 pièges)

| Trouvaille | Gravité | Verdict | Preuve |
|---|---|---|---|
| NU-E-046 faux verdict de copropriété inventé | BLOQ | **fermé** | Live AV0167 : **« Oui … en copropriété (9 lots recensés) »**, sources `['RNIC']`, champ `copro`. Fait déterministe `outils.py:378`. |
| NU-E-047 verrou aveugle au qualitatif | BLOQ | **fermé** | `_verdicts_coherents`/`_quali_backing`/`_polarite_quali` (`answering.py:429`), branché dans `_formuler`. |
| NU-E-048 source falsifiée « cadastre Etalab » | MAJ | **fermé** | Live zone A AH0007 : constructibilité sourcée `['PLU — zonage', 'DEAL Réunion — PPR']`, jamais « cadastre ». |
| NU-E-049 `verdict = tier` embarqué systématiquement | MAJ | **fermé** | payload `fiche_parcelle` sans verdict/tier (`outils.py:371`). |
| NU-E-050 exception avalée générique | MIN | **fermé en pratique** | refus typés par outil ; filet générique réservé aux vrais incidents. |
| NU-E-051 % PPR sans borne de plausibilité | DETTE | **toujours ouvert** | `part_pct` brut, gardé par `_anti_invention`. |

### H — Implantation & étude de faisabilité

| Trouvaille | Gravité | Verdict | Preuve |
|---|---|---|---|
| NU-E-055 RNU → zone « UA » inventée, programme chiffré | BLOQ | **partiellement fermé + RÉGRESSION servie** | Moteur corrigé (`_resoudre_zone` lève `EtudeHorsPerimetre('rnu')`, plus de « UA », `etudier_payload` AT1496 → 0 logement). **MAIS `POST /modules/etude` sur AT1496 → HTTP 500 (reproduit 3×)** : `service.py:934 "terrain": None` + `modules.py:2198 setdefault("terrain",{})[...]` → `TypeError: 'NoneType' object does not support item assignment`. Déclenché dès qu'une parcelle RNU porte un aléa. Le refus honnête n'atteint pas le client. |
| NU-E-056 seuil TCSP 500 m (loi = 800 m) | MAJ | **fermé** | `service.py:609 _RAYON_TCSP_M = 800`, citations « loi 2025-1129 » L151-35/36. |
| NU-E-057 parcelle >1 ha → 503 | MAJ | **fermé** | grille grossière >5000 m² + budget dur 22 s. CT2637 → résultat borné, pas de 503 (~28 s < borne 60 s). |
| NU-E-058 CES/pleine terre : dessin vs contenance | MAJ | **fermé** | `controles.py:258` calcule sur `aire_dessin_m2` (même repère que l'emprise). |
| NU-E-059 hauteur = niveaux×3 m forfait | MAJ | **fermé** | `controles.py:45 hauteur_projet_m` distingue égout/faîtage + toiture, marque `estimee`. |
| NU-E-060 verdict sans Emprise/Hauteur « Réussi » | MIN | **toujours ouvert (partiel)** | `statut_etude` autorise encore « exploitable » avec Emprise/Hauteur « Non effectué ». |
| NU-E-061 ratio L151-35 piloté par distance seule | DETTE | **toujours ouvert** | pas de table par catégorie de logement. |
| NU-E-062 ZeroDivisionError sous-sol | DETTE | **fermé** | division gardée (`if places else None`). |
| NU-E-063 exceptions avalées (plan/accès/LiDAR) | DETTE | **toujours ouvert** | `terrain.py` `except: pass` sans drapeau client. |

---

## Lot F — Transversal (navigateur + API)

### Bloquants

| Trouvaille | Verdict | Preuve |
|---|---|---|
| NU-F-001 deux médianes « acté maisons » contradictoires sur le même écran | **fermé** | MARCHE-UNIQUE-1 : `_dvf_bati_type`→`mediane_commune` (point unique). Live bien 428 (L'Étang-Salé) : `/vs-marche` **3865 €/m²** = `/marche-tableau` **3865 €/m²**. Le 4030 vs 3750 a disparu. |
| NU-F-002 code interne du tier fuit au client | **fermé** | `fiche_parcelle` n'embarque plus de tier/verdict (`outils.py:369-401`). Replay sur AO0113 (tier base `ecartee`) : aucun code brut dans `faits`/substance. |
| NU-F-003 « les mêmes filtres que la carte — rien d'autre » faux | **fermé (décision Vic total+split)** | « rien d'autre » retiré ; `FiltreFacettes` réutilise `AffinerRecherche`+`SectionProprietaire` (toutes familles). Live {Saint-Denis, nu} : `/filtre` total **2889** = `/projets/compteur` total **2889** (figeable 2256 · écartées 633). |

### Majeurs

| Trouvaille | Verdict | Preuve |
|---|---|---|
| NU-F-004 SSRF « Analyser une annonce » | **fermé** | `radar_annonce_analyser` ne fait **plus aucun fetch sortant** (lookup Radar DB seul, `pige/api.py:1313-1339`) ; `/analyse-annonce.pdf` passe par le même handler. Oracle de ports supprimé par construction. |
| NU-F-005 Pilotage 88 s (Stripe synchrone) | **fermé** | `dashboard.py:398`→`apercu_affichage()` sert le cache + rafraîchit en thread démon (`stripe_lecture.py:170-190`) ; jamais d'appel réseau dans le thread de requête. |
| NU-F-006 Sources 14,8 s à froid | **fermé** | cache clé-fraîcheur `etat_sources` (`fraicheur.py:199`), préchauffé au boot. |
| NU-F-007 SSRF « dépôt agence » (latent) | **fermé** | primitive `_fetch_page_oneshot` durcie : `_valider_cible` (liste blanche d'hôtes, rejet RFC-1918/loopback/link-local, `allow_redirects=False`). |
| NU-F-008 CRM « Étiquette de contact » morte, Pilotage ment | **décision Vic (documentée)** | backend vivant, aucune UI ne pose l'étiquette, `contact_etiquette_log` = 2 lignes `compte_id` NULL (compteur honnêtement ~0). Laissé + documenté (verrou tests, `produit-nu-1`). |
| NU-F-009 garde colonne double source (colonne « vide » indéboulonnable) | **fermé** | `crm_columns.py:170-177` `_cards_in` a `AND archived_at IS NULL`, aligné au compteur affiché. |
| NU-F-010 dialogue lit un compteur filtré par la recherche | **fermé** | `Kanban.tsx:623` ouvre avec `cardCountAll(...)` non filtré. |
| NU-F-011 kanban contredit le discours du wizard | **fermé** | bandeau reformulé « signal de vie récent … sans jugement » ; plus de « LABUSE a analysé »/« probabilité de mutation ». |
| NU-F-012 compteur liste périmé jusqu'à la 1ʳᵉ ouverture | **fermé** | `projets.py:667-676` recalcule si `cadrage_total_at < runs.promu_at()`. |
| NU-F-013 table figée (≤200) vs compteur vif : « à trier » à deux sens | **partiellement fermé** | figé = export-only, compteur = vif (clarifié en code) ; message « plafond 200 » absent du kanban (présent dans FiltreFacettes). |
| NU-F-014 « En vente depuis N j » dans deux fuseaux | **fermé** | front `joursDepuis` retiré ; `/radar/biens` sert `anciennete_j` (heure Réunion, `marche.py:316`). Source unique. |
| NU-F-015 compteur d'alerte : valeur/libellé/vide sur trois fenêtres | **fermé** | libellé + vide alignés sur « depuis hier » (`VeilleEcrans.tsx:298`), backend fenêtre hier 00:00 Réunion. |
| NU-F-016 « 30 j/90 j depuis la dernière collecte » faux | **fermé** | phrase trompeuse supprimée du front ; libellé « Ce qui a bougé · 30 jours ». |
| NU-F-017 brief « Rien de nouveau » avec événements présents | **fermé** | `events.py:1256` `vide = (n_evenements == 0)`. |
| NU-F-018 liens des mails morts (base_url localhost) | **fermé en code (reste config prod)** | fail-closed `exiger_base_url_publique` (`events.py:1373`, `digests.py:513`) lève si base_url absente/localhost. `readyz` local montre encore `mail_liens.ok:false` → dépend du `public_base_url` prod. |
| NU-F-019 DA Projets hex de marque en dur (`#4ADE80`) | **fermé** | `#4ADE80` remplacé par `var(--mint)` ; `tests/test_brand_colors.py` **7 passed**. (restent des gris non-marque hors verrou.) |
| NU-F-020 `<select>` natifs + pastilles maison | **fermé** | `Badge`/`Select`/`Chip` (ui) adoptés ; `bg-mint/12` et `#E7B008` disparus. |
| NU-F-021 espace insécable manquante avant €/%/m² | **fermé** | 4 fichiers importent les helpers NBSP de `lib/format` ; plus de redéfinition locale. |
| NU-F-022 a11y clavier + champs sans label | **fermé** | rangées `role="button" tabIndex onKeyDown` ; inputs `aria-label`. |
| NU-F-050 « L'usine » job gelé peint « au vert » | **fermé (backend)** | `_pastille_job`/`_job_perime` (`cockpit_resume.py:33-78`) : après `ok`, compare à 1,5× cadence → **ambre** si périmé (pas front-only). |
| NU-F-051 incidents périmés en alarmes rouges vivantes | **partiellement fermé** | l'âge « ouvert depuis » monte dans la phrase (`cockpit_resume.py:211`), mais aucun prédicat de fraîcheur vs la dernière passe `verifier_tout` ; l'incident reste rouge « présent ». |

### Mineurs & dettes (balayage)

| Trouvaille | Verdict | Note |
|---|---|---|
| NU-F-023 `/moi` role/statut | **décision Vic** | utile au front (non comptée ouverte). |
| NU-F-025 `/events/count` ≠ `/events` sur types mis en sourdine | **toujours ouvert** | `events.py:781` `notifications_non_lues` sans `cloche_filter_sql`. |
| NU-F-026 `resume_fiche` expose des ids de champ | **fermé** | tuiles `{libelle,valeur}`, sections `{titre,verdict,ton}`. |
| NU-F-027 tolérance anti-invention ±1 + source/millésime | **toujours ouvert** | `answering.py:316` `abs(n-a)<=1` ; source/millésime toujours autorisés. |
| NU-F-028 message d'erreur étiquette fuit les clés | **fermé** | `app.py:9695` joint `.values()` (libellés). |
| NU-F-029 `priority` éditable jamais affiché | **toujours ouvert** | pas de rendu sur la carte. |
| NU-F-030 `proprietaire_label`/`has_manual_contact` servis non rendus | **toujours ouvert** | payload mort. |
| NU-F-031 `/version` divulgue `env`/`par` | **toujours ouvert** | `app.py:704-705`, pas de gating admin. |
| NU-F-032 date de relevé affichée ici/masquée là | **fermé (décision Vic 18/09)** | plus aucune date de relevé rendue. |
| NU-F-033 sous-titre Veille mélange 7 j/1 j | **partiellement fermé** | libellé trompeur retiré ; les deux fenêtres restent additionnées (documenté). |
| NU-F-034 « Archivées » sur « projet » (masculin) | **toujours ouvert** | `ProjetsPanel.tsx:235`. |
| NU-F-035 formateurs monétaires admin hors `lib/format` | **toujours ouvert** | admin-only. |
| NU-F-037 Segment dupliqué + opacité hors charte | **toujours ouvert** | `VeilleEcrans.tsx:405`. |
| NU-F-038 boutons icône 28 px dans Veille | **toujours ouvert** | `h-7 w-7`. |
| NU-F-039 statut notif par couleur seule | **partiellement fermé** | cloche/bouton `aria-label`+`aria-pressed` ; pastille lu/non-lu couleur-seule subsiste. |
| NU-F-040 alt d'image générique | **toujours ouvert** | `Header.tsx:545 alt="logo"`. |
| NU-F-041 bouton « Envoyer » Copilote codé à la main | **partiellement fermé** | textarea `aria-label` ajouté ; bouton toujours `bg-cp-ia` (pas `Bouton`). |
| NU-F-052 « Les un cache sont en retard » | **toujours ouvert (clôture inefficace)** | `_CACHE_NOM["derives_regle"]` posé sur la clé interne ; le nom émis est `"tables dérivées (version de règle)"` → `startswith` échoue → repli « un cache ». La grammaire reste cassée. |
| NU-F-053 tuile « en échec » sur pastille grise (jamais passé) | **toujours ouvert** | `else` regroupe rouge+gris ; un job jamais passé lit « en échec ». |
| NU-F-054 commentaires périmés + `job-retard:` sans bouton | **toujours ouvert (dette)** | `_titre_incident_generique` ne traite que `job-echec:`. |
| NU-F-042..049, F-048 | dettes | CORS `*` local = sûr/non régressé ; autres dettes non individuellement rejouées. |

---

## Balayage de non-régression

**Run q_v21 servi en local (`:9261`, override `LABUSE_SERVED_RUN`).**
- **30 parcelles tirées au sort — classement ↔ fiche :** 30/30 le tier servi par la fiche (`/parcels/{idu}`) == le tier `parcel_p_score_v2` run q_v21, copro identique. 0 écart.
- **Classement ↔ filtres :** `/filtre?source=q_v21` (sans commune) total **432 353** = 433 229 − 876 slivers (<2 m², masqués des deux côtés) ; bandes = paliers exacts (brûlante 73 = `priorite`, chaude 335 = `a_suivre`, sans_signal 279 185, écartée 152 760 = 153 636 − 876). Par commune (Saint-Louis) : filtre 29 248 = somme des bandes ; `parcels` 29 342 − 94 slivers. **Cohérent.**
- **Masque copro (NU-E-010) effectif dans q_v21 :** 0 copro en palier (3113 sans_signal + 317 écartée), vs 393 en palier dans q_v20 servi.

**Copilote — 10 questions pièges (live `:9260`) : 10/10 propres.** copro OUI (AV0167, RNIC, 9 lots) / copro NON (IC0114, RNIC) ; constructibilité zone A sourcée PLU+PPR (jamais « cadastre ») ; « verdict LABUSE » → ouvre la Calculette, **aucun code de tier** ; prix → refuse, ouvre la Calculette ; propriétaire particulier → « non renseigné » (RGPD) ; RNU → « je ne tranche pas sans PLU (L111-3) » ; PPR % borné (2 %, DEAL) ; parcelle inexistante → ouvre Faisabilité sans inventer ; zone → « Ug (famille U) » sourcée PLU ; SDP résiduelle → défère au règlement, n'invente pas.

**Sécurité :** SSRF `POST /radar/annonce/analyser` fermée (plus de fetch client) ; primitive `_fetch_page_oneshot` durcie (liste blanche + IP privées + no-redirect) ; `/version` fuit encore `env`/`par` (mineur F-031). Routes admin gardées (non re-testées au-delà du code `exiger_admin`).

**Console navigateur :** Accueil + fiche `97404000AV0167` + Radar → **0 erreur / 0 avertissement** (seul un info React DevTools).

**Journaux API :** **3 erreurs sur toute la session, racine unique** = la régression NU-E-055 (`POST /modules/etude` RNU → `TypeError NoneType`). L'instance q_v21 : 0 erreur. Hors cette régression, journaux propres.

---

## Ce qui reste ouvert, par gravité

### Bloquants
- **NU-E-038 — toujours ouvert.** 300/513 biens Radar `retiree` par fausse confirmation jamais purgés (restauration RADAR-FIX-3 non rejouée sur cette base) ; servis par l'API courante (délai médian de retrait calculé sur des fantômes). **Dette de donnée** (le code de confirmation est corrigé, la purge n'a jamais tourné).
- **NU-E-055 — régression.** Le moteur refuse correctement le RNU, mais `POST /modules/etude` renvoie **HTTP 500** sur toute parcelle RNU portant un aléa (`service.py:934 "terrain": None` + `modules.py:2198 setdefault`). À corriger : `_attach_contraintes_signalees` doit gérer `terrain=None`.
- **NU-E-003 — partiellement fermé.** Contradiction produit close (surface servie mono-valuée), mais les deux chemins d'assiette et leurs défauts incohérents subsistent au niveau moteur.

### Majeurs — défauts de fond encore présents
- **NU-E-010 / NU-E-011** — fermés dans le code mais **pas dans la sortie servie** : masque copro seulement dans q_v21 (non servi en prod), et `fiche_cache` périmé sert encore `fraction=1/20` (sha `deploiement.json` pré-merge jamais bougé). Clôture réelle = servir q_v21 + déploiement qui invalide le cache.
- **NU-E-032** — cache `dvf_secteur_medianes` jamais reconstruit (figé 2026-08-17, sans colonne millésime, diagnostic de péremption non branché). **Dette de donnée.**
- **NU-E-041** — doublons exacts inter-portail (LBC↔Bien'ici) en base, Bien'ici chargé hors du chemin de dédoublonnage.
- **NU-E-012** — `valeur_creee_eur` = CA brut sans coût (max 878 M€) ; non servi (atténuation tient, décision « interne »).
- **NU-E-024** — ±% terrain toujours en dur ; 2ᵉ chemin `estimation_prix.py` (±30 %) non unifié.
- **NU-E-052** — deux emprises bâties (65,8 % divergent >20 %) ; libellés honnêtes mais source non unique.
- **NU-F-013** — figé/vif clarifié en code, message « plafond 200 » absent du kanban.
- **NU-F-018** — fail-closed en code ; dépend encore du `public_base_url` prod.
- **NU-F-051** — incidents sans prédicat de fraîcheur vs la dernière passe de monitoring.

### Mineurs encore ouverts
NU-E-016, E-017, E-027/028 (partiels), E-034 (partiel), E-043, E-044, E-060 (partiel) ; NU-F-025, F-027, F-029, F-030, F-031, F-033 (partiel), F-034, F-035, F-037, F-038, F-039 (partiel), F-040, F-041 (partiel), **F-052 (clôture inefficace)**, F-053.

### Dettes encore ouvertes
NU-E-009 (partiel), E-018, E-019, E-020 (partiel), E-029, E-036 (partiel), E-037, E-045, E-051, E-061, E-063 ; NU-F-054 (+ dettes F-042..F-049 non rejouées).

---

## Conduite d'audit

Lecture seule respectée : recalculs SQL sous `default_transaction_read_only=on`, aucune écriture métier, aucun accès prod, aucun fichier suivi modifié (q_v21 servi via l'override d'env `LABUSE_SERVED_RUN`, jamais le manifeste ; les deux instances API et le front dev sont jetables et locaux). Les instances API ont servi leurs caches de lecture normalement contre la base locale. Verdicts fondés sur la sortie observée (fiche/API/PDF/Copilote/console/journaux), pas sur la présence d'une branche fix.
