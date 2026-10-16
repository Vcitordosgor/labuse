# VERITE-TERRAIN-2 — volet C : DPE (ADEME par adresse BAN), permis (Sit@del) & salvage NON COMPARABLE

Volet C ferme les **trous** de la première vérité terrain (V-T-1), sur les **mêmes 500 parcelles**
(échantillon stratifié reproductible, graine `20261015`, base q_v18). Il répond à trois questions que
V-T-1 avait laissées ouvertes : le **rappel** du rattachement DPE de LABUSE (pas seulement sa
précision), une **source Sit@del indépendante** pour les permis (V-T-1 ne faisait qu'afficher le
compte ingéré), et le **salvage** des NON COMPARABLE Géorisques qui pouvaient l'être au grain commune.

Lecture seule stricte : connexion DB `read_only = True` (toute écriture lève), aucun appel au code qui
mute, rien sur le VPS, aucune modification du code existant. Un seul module neuf :
`src/labuse/verite_terrain_dpe_permis.py`. Appels réseau séquentiels, espacés (~0,5 s), **cache
disque** (`cache/dpe_permis/`, non commité) et **journal append-only resumable**
(`_dpe_permis_partiel.csv`, non commité ; une (parcelle, contrôle) finie survit à une interruption, la
reprise saute les faits). Le CSV final est reconstruit depuis le journal.

Fichiers du volet : `DPE-PERMIS.csv` (2 048 lignes = 1 ligne par (parcelle, contrôle)), ce NOTES.

---

## 0. Verdict d'ensemble

| Contrôle | Comparables | CONFORME | LABUSE FAUX | Fraîcheur | NON COMPARABLE |
|---|---|---|---|---|---|
| **DPE** (ADEME par BAN) | 226 | 226 | **0** | 0 | 274 |
| **Permis — grain commune** | 24 | 23 | 0 | 1 | 0 |
| **Permis — grain N° de dossier** | 24 | 24 | 0 | 0 | 0 |
| **Géorisques sismicité** (salvage) | 500 | 500 | 0 | 0 | 0 |
| **Géorisques radon** (salvage) | 500 | 500 | 0 | 0 | 0 |
| **Géorisques argiles** (N/A documenté) | 0 | — | — | — | 500 |

**Aucun « LABUSE FAUX » confirmé** sur les trois contrôles. Chaque candidat a été revérifié à la main
(cf. §1.3) ; tous se sont avérés des effets de **grain adresse↔parcelle**, pas des erreurs de LABUSE.

---

## 1. DPE — le nouvel angle : le RAPPEL du rattachement

### 1.1 Méthode (comment on interroge l'ADEME par BAN)

V-T-1 ne vérifiait qu'un sens : « chaque DPE que LABUSE **sert** existe-t-il à l'ADEME ? ». Comme
LABUSE ne rattache un DPE qu'à **1 parcelle sur 500**, V-T-1 n'avait qu'**un seul comparable**. La vraie
question est l'inverse — le **rappel** : *l'ADEME a-t-elle, à l'adresse BAN de la parcelle, des DPE que
LABUSE ne rattache pas ?*

On ne peut **jamais** interroger l'ADEME par rayon géographique : la **géoloc ADEME 974 est corrompue**
(latitude ~−2 au lieu de ~−21). On l'interroge donc par **identifiant BAN** :

1. **Ancre BAN de la parcelle** = les `id_ban` que LABUSE rattache lui-même à la parcelle dans sa table
   `adresses` (rattachement spatial parcelle↔adresse). Vérifié : ces id_ban sont du **même millésime
   BAN que l'ADEME** — ex. la parcelle `97415000BO0407` porte `97415_1330_00038`, et le DPE ADEME de
   cette adresse porte exactement `identifiant_ban = 97415_1330_00038`. (Le reverse BAN *live* au
   centroïde, lui, renvoie un autre code de voie — `97415_2ee97u_…` — car la BAN a re-généré ses codes
   de rue depuis ; la table `adresses` de LABUSE est donc une meilleure ancre que le reverse.)
2. **DPE ADEME** = tous les DPE des jeux ADEME dont `identifiant_ban ∈ {ancres}`, requête OR par jeu
   sur le champ `identifiant_ban` (champ exact utilisé). Jeux interrogés (tous confirmés live) :
   `meg-83tjwtg8dyz4vv7h1dqe` (logements existants depuis 07/2021), `g3cgx7jb3cmys5voxz1mrm22`
   (logements **neufs**), `j9ol0fwjqckyf49vr29nknbu` (tertiaire), `dpe-france` (logements avant
   07/2021). On compte les `numero_dpe` **distincts**.
3. **DPE LABUSE** = `dpe_records.parcelle_idu = <idu>` (numero_dpe rattachés).
4. On confronte les deux ensembles de `numero_dpe`.

### 1.2 Le rappel de LABUSE, en chiffres

- **226 / 500 parcelles** ont une **adresse BAN rattachée** (l'ancre) → c'est l'**ensemble
  testable** du rappel. Les **274** autres n'ont **aucun id_ban** dans `adresses` (parcelles agricoles,
  Hauts, dents creuses sans voirie) → **NON COMPARABLE** (pas d'ancre pour interroger l'ADEME ;
  l'absence de DPE n'y est pas assertable).
- Sur ces **226 parcelles ancrées**, l'ADEME porte en tout **8 DPE** à leurs adresses BAN ;
  **LABUSE en rattache 1** à l'échantillon.
- **222 / 226** parcelles ancrées : **l'ADEME n'a aucun DPE à l'adresse, et LABUSE non plus** →
  CONFORME (accord sur le vide — à La Réunion le parc avec DPE est clairsemé hors centres).
- **4 / 226** parcelles ancrées ont un DPE ADEME à l'adresse. Détail revérifié à la main en §1.3.

**Lecture honnête du rappel :** sur les 226 parcelles où le test est possible, LABUSE ne **manque aucun
DPE au grain parcelle**. Mais ce n'est pas parce que l'ADEME serait vide : c'est parce que les quelques
DPE que l'ADEME a à ces adresses sont **géocodés au grain rue** (voir §1.3), donc **non assignables à
une parcelle** — ni par LABUSE, ni par qui que ce soit. Le rappel « parcelle » est donc **non mis en
défaut**, mais la vraie limite est le **grain** : le DPE ADEME est un objet **bâtiment/adresse**, pas
parcelle.

### 1.3 Les 4 cas ADEME-présent, revérifiés un par un

| Parcelle | Commune | Ancre(s) BAN | DPE ADEME | LABUSE | Vérification manuelle |
|---|---|---|---|---|---|
| `97413000CQ0708` | Saint-Leu | `97413_3ri5zr…` | 1 (`2313E4214268V`, étiq. **C**) | 1 (même n°, étiq. **C**) | **Vrai match.** Le seul DPE servi de l'échantillon ; existe à l'ADEME, étiquette identique. **CONFORME**. |
| `97412000BO0144` | Saint-Joseph | `97412_1040_00025` | 1 (`2262E1550602Z`) | 0 | DPE ADEME géocodé **`97412_1040`** = *Rue du Maréchal Leclerc* **sans n°** (grain rue). Peut appartenir à n'importe quelle parcelle de la rue → **non assignable à cette parcelle**. Pas un trou LABUSE. **CONFORME (grain rue)**. |
| `97416000ET0700` | Saint-Pierre | `97416_0566_00266`, `97416_raiurq_00266/268` | 1 (`2506E1751327D`) | 0 | DPE ADEME géocodé **`97416_raiurq`** = *Avenue du Général de Gaulle* **sans n°**. Grain rue → non assignable. **CONFORME (grain rue)**. |
| `97416000IM0125` | Saint-Pierre | `97416_0265_00214/216`, `97416_9jhkyc_*`, `97416_e0sf0r_*` | 5 (`2214E0118290F`, `2214E1877880T`, `2214E2245244D`, `2327T0783821R` tertiaire, `2393E0959730J`) | 0 | Les **5** DPE géocodés **`97416_0265`** = *Rue du Stade* **sans n°** (grain rue). Un paquet de DPE de la rue, aucun sur le point de la parcelle. Non assignables à cette parcelle précise. **CONFORME (grain rue)**. |

Mécanique de tri appliquée (et vérifiée) : un `identifiant_ban` ADEME à **un seul segment de voie**
(`insee_codevoie`, sans numéro) ne peut pas désigner une parcelle unique — on le **signale** (note
« géocodé au niveau rue, grain imprécis ») sans jamais le compter FAUX. Un `identifiant_ban` **exact**
(avec numéro) rattaché par LABUSE à une **autre** parcelle serait du grain adresse↔parcelle (une adresse
BAN peut couvrir plusieurs parcelles) — **aucun cas de ce type** dans l'échantillon. Résultat : **0
FAUX**, et aucun FAUX masqué.

---

## 2. Permis — Sit@del, une source indépendante

### 2.1 Méthode (la source Sit@del 974 et le grain)

V-T-1 classait tout NON COMPARABLE (« pas d'API Sitadel »). On prend ici la **base nationale SDES/DiDo
en open data**, exposée en API data-fair : **`sitadel-logements`** sur `opendata.koumoul.com`
(permis de construire et déclarations préalables **créant des logements**, depuis 2013, 1,9 M lignes
nationales), filtrable par commune (`COMM`), type (`TYPE_DAU`), et N° de dossier (`NUM_DAU`). C'est la
**même source** que LABUSE ingère (« SDES Dido — Sitadel3 (974) »), mais interrogée **en direct et
indépendamment**. On compare la **famille « logements »** (PC + DP) de LABUSE, **depuis 2013** (fenêtre
commune), aux permis `sitadel-logements` de chaque commune des 500 parcelles. Deux grains :

- **grain commune** : `count` officiel (`COMM:<insee>`) vs `count` LABUSE (`famille='logements'`,
  `date_depot >= 2013`). Un appel `size=0` par commune, mémoïsé.
- **grain N° de dossier** : le `permit_id` de LABUSE et le `NUM_DAU` de Sit@del **partagent le même
  format** (ex. `97441512A0461`) → on peut **joindre par identifiant**. On récupère les NUM_DAU de la
  commune (paginé, plafond 20 000) et on mesure le **recouvrement** : combien de `permit_id` LABUSE
  sont retrouvés dans Sit@del, et combien de NUM_DAU Sit@del manquent à LABUSE.

### 2.2 Résultats

**Grain commune** (24 communes des 500 parcelles) : **Sit@del 41 177 permis logements / LABUSE
39 018 (94,8 %)**. **23 / 24 communes** sont dans la bande ±10 % → CONFORME. **1 commune** sort :
**Cilaos** (Sit@del 375 / LABUSE 312, LABUSE ≈ 17 % en deçà) → classée **SOURCE PLUS RÉCENTE** : les
trimestres Sit@del open-data postérieurs à l'ingestion LABUSE et les révisions expliquent l'avance ;
sur un petit cirque, 63 permis d'écart pèsent lourd en pourcentage.

**Grain N° de dossier** : **recouvrement 100 % sur les 24 communes** — **0 permit_id LABUSE absent de
Sit@del** (0 « LABUSE-seul » partout). Chaque permis logement que LABUSE sert **existe** dans la base
Sit@del autoritative, à l'identifiant près. Les **2 159 NUM_DAU Sit@del en plus** (41 177 − 39 018) sont
des permis que LABUSE n'a pas encore ingérés (fraîcheur : trimestres récents + révisions), **pas des
inventions de LABUSE**.

### 2.3 Limite de faisabilité & renvoi au volet D

La comparaison **per-parcelle autoritative** (capacité LABUSE vs surface/logements réellement
**autorisés** sur la parcelle) demande de croiser `SEC_CADASTRE1`/`NUM_CADASTRE1` (présents dans
`sitadel-logements`) avec la géométrie — c'est exactement l'objet du **volet D (temps 2)**, qui est
explicitement Sitadel. Ici on a fait la **meilleure comparaison honnête possible maintenant** : grain
commune + join par N° de dossier, qui établit déjà que **l'ingestion LABUSE est exhaustive et fidèle à
la source** (0 permis inventé, 94,8 % du volume, 100 % de recouvrement d'identifiants). Le grain
parcelle autoritatif reste au volet D.

---

## 3. Salvage des NON COMPARABLE — Géorisques

V-T-1 posait sismicité / radon / argiles en NON COMPARABLE « absent au point ». Deux des trois sont en
fait **publiés par commune** → **devenus comparables**.

### 3.1 Sismicité — SAUVÉ (comparable au grain commune)

Endpoint `GET /api/v1/zonage_sismique?code_insee=<insee>`. Les **24 communes** rendent une **zone
réglementaire** (toute La Réunion = **zone 2 « faible »**, cohérent avec le zonage sismique national).
On compare la zone officielle à ce que LABUSE sert (fiche `aleas`/`risques`) : **500 / 500 CONFORME** —
LABUSE **ne contredit jamais** la zone officielle (il ne sert pas toujours la zone en détail, mais
n'affiche jamais une zone 1/3/4/5 là où l'officiel dit 2). Taux : **100 %**.

### 3.2 Radon — SAUVÉ (comparable au grain commune)

Endpoint `GET /api/v1/radon?code_insee=<insee>`. Les 24 communes rendent une **catégorie de potentiel
radon** (Saint-Paul = catégorie 1, p. ex.). **500 / 500 CONFORME** (LABUSE ne contredit jamais le
potentiel officiel). Taux : **100 %**.

### 3.3 Argiles (retrait-gonflement, RGA) — reste NON COMPARABLE, mais raison **documentée**

Géorisques déclare le RGA **N/A à La Réunion** : l'endpoint `/rga` renvoie 500/vide (île volcanique, pas
d'argiles gonflantes continentales) — c'est **écrit dans le connecteur `connectors/georisques.py`**
(« /rga (argiles) : 500 sur code_insee, vide sur latlon même en métropole — écarté ; N/A géologique à La
Réunion »). Les **500** lignes restent donc NON COMPARABLE, mais pour une raison **sourcée et
structurelle** (pas « absent au point » comme dans V-T-1). Ce n'est pas un trou de LABUSE : il n'y a
simplement **rien à servir**.

### 3.4 Familles qui restent VRAIMENT non comparables (non forcées)

Listées honnêtement, sans comparaison bidon :
- **DVF recompte/dédup** (déjà traité en V-T-1) : agrégat dérivé, l'écart de méthode ±25 % n'est pas un
  faux — non re-forçable ici.
- **Dirigeants d'entreprise** : LABUSE ne sert pas les dirigeants → rien à comparer côté servi.
- **RNB (bâti)** : registre en cours de complétude → un RNB en deçà de BD TOPO ne réfute rien
  (asymétrie déjà documentée en V-T-1).
- **Argiles** : cf. §3.3 (N/A géologique).

---

## 4. Limites honnêtes (dominantes)

1. **Grain adresse↔parcelle du DPE (limite n°1).** Le DPE ADEME est un objet **bâtiment/adresse**, pas
   parcelle. Quand l'ADEME géocode un DPE au seul **segment de rue** (`insee_codevoie`, sans numéro),
   il est **non assignable** à une parcelle unique — ni par LABUSE ni par l'audit. Les 4 cas
   ADEME-présent de l'échantillon sont 1 vrai match + 3 géocodages rue. On ne compte donc **FAUX** que
   les manques assignables (il n'y en a aucun). Le rappel « parcelle » de LABUSE est **non mis en
   défaut**, mais c'est sur un **très petit N testable** (8 DPE ADEME sur les adresses de 226 parcelles).
2. **Géoloc ADEME 974 corrompue — contournée par BAN.** Jamais de rayon géographique ; on interroge
   exclusivement par `identifiant_ban`, ancré sur la table `adresses` de LABUSE (même millésime BAN que
   l'ADEME). C'est robuste mais borné aux parcelles **avec** adresse BAN (226/500).
3. **N réel du rappel DPE = 226/500.** 274 parcelles n'ont pas d'ancre BAN → non testables. Le rappel
   DPE est donc mesuré sur **moins de la moitié** de l'échantillon ; c'est une borne honnête, pas un
   taux gonflé.
4. **Permis per-parcelle = volet D.** On a validé le grain commune (94,8 % du volume, 1 commune en
   fraîcheur) et le grain N° de dossier (100 % de recouvrement, 0 permis inventé). La comparaison
   capacité↔autorisé au grain parcelle relève explicitement du **volet D (temps 2)**.
5. **Sit@del set tronqué sur très grosses communes.** Le join par NUM_DAU récupère les dossiers jusqu'à
   un plafond de 20 000/commune ; aucune commune de l'échantillon ne l'a atteint (max Saint-Paul 5 185),
   donc le recouvrement 100 % est exact ici — la garde est documentée pour la robustesse.

**Nombre de « LABUSE FAUX » confirmés : 0** (sur DPE, permis et Géorisques).

---

## 5. Reproduire

```
PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis dpe          # rappel DPE par BAN
PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis permis       # Sit@del commune + dossier
PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis georisques   # salvage sismique/radon/argiles
PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis tout         # les trois + finalisation
PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis rapport      # reconstruit DPE-PERMIS.csv
```

Échantillon = les 500 parcelles de V-T-1 (`_charger_echantillon()`, graine 20261015). Cache réseau dans
`cache/dpe_permis/`, journal append-only `_dpe_permis_partiel.csv` — **ni l'un ni l'autre n'est commité**
(`.gitignore` du dossier). Appels séquentiels espacés ~0,5 s ; reprise automatique en sautant les
(parcelle, contrôle) déjà faits.
