# M146 — Audit lecture seule : la lettre de vérification de zonage

Branché sur `origin/main` @ `7b13b00e` (merge de `fix/m145-flash-moteur`). **Audit lecture seule —
aucune ligne corrigée.** Le mandat de correction est arbitré par Vic. CC ne merge jamais.

Périmètre : `src/labuse/api/lettre_zonage.py` (route `/{idu}.pdf`, l.310), sa chaîne de données
(`flash/data.py::collect_report_data`, `faisabilite/plu_rules.py::resolve_zone`,
`plu_reglement.py::resolve_reglement`, `rnu.py`) et son exposition (`quota.py::porte_export`).

**Méthode — exemplaires sur données RÉELLES.** Le rendu binaire (WeasyPrint/pango + chaîne fastapi +
tuiles carte) n'est pas disponible en local (limite établie depuis M142). J'ai donc extrait le
**contenu réel** que la lettre imprime, en exécutant les VRAIS résolveurs (`resolve_zone`,
`resolve_reglement`) et le VRAI SQL de `collect_report_data` contre la base `labuse` locale, pour la
parcelle nominale + les 6 cas qui fâchent. Résultat brut joint : `qa/lettre_zonage/exemplaires/_contenu_reel.txt`.
Le contenu montré ci-dessous EST celui du chemin de code, pas une paraphrase.

---

## Verdict en une ligne

**La lettre ne peut PAS être remise à un tiers en l'état sur deux classes de parcelles — zones GELÉES
(Us / 2AU calibrées) et communes au RNU — et un défaut de troncature de notes ampute des règles
matérielles sur TOUTE lettre calibrée.** L'architecture est pourtant saine et honnête (intersection
spatiale de toutes les parts, article obligatoire par règle, disclaimers proéminents, aucune capacité
chiffrée, aucun rang/score). Trois défauts la rendent dangereuse pour des cas précis. Détail par gravité
en §F.

---

## A — Ce que la lettre affirme, mot à mot

Structure (`_build_pdf`, `lettre_zonage.py:280-307`) — 6 sections, layout attestation :

| # | Section | Source | Étiquetage |
|---|---------|--------|-----------|
| Garde | Réf. `LZ-AAAA-NNNN` + date d'édition + `LIBELLE` (bandeau) | `_ref_attestation` (l.108, écrit en base) ; `date.today()` | proéminent |
| 1 | Identification (IDU, section, n°, surface cadastre, adresse BAN) | `parcels` (l.285-287) ; adresse via `collect_report_data` | Sourcé |
| 2 | **Zonage applicable** (zone(s) + part % + document d'urbanisme) | `spatial_layers kind='plu_gpu_zone'` ∩ parcelle (`flash/data.py:163-172`) ; document via `resolve_reglement` (l.173-179) | Sourcé (GPU) |
| 3 | **Règles principales** (hauteur, emprise, reculs, pleine terre, stationnement) — **article obligatoire** | `resolve_zone` → YAML `config/plu_<commune>.yaml` clés `*_src` (l.195-224) | Sourcé (calibré) ou « non calibré » |
| 4 | Servitudes / prescriptions cartographiées | `collect_report_data` : `identite.prescriptions`, `risques.couches`, `patrimoine.couches/abf` (l.227-249) | Sourcé (base only) |
| 5 | Limites + Sources/millésimes | `LIMITES` (bandeau) + `rap.sources` (l.252-262) | proéminent |
| Clôture | « Édité par LABUSE … n° LZ-… éditée le … » | `_cloture` (l.265-275) | — |

**La lettre NE contient PAS** : aucune capacité chiffrée (SDP, logements), aucun prix, aucun verdict,
aucun rang, aucun score — vérifié par grep (§D). Son périmètre réel est **« zonage + règles calibrées,
rien d'autre »**. C'est un choix défendable — *à condition que le titre ne promette pas plus et que les
absences soient dites juste* (ce qui casse en RNU, §B3).

**`LIBELLE` (l.35) et `LIMITES` (l.39) — proéminence.** Les deux sont rendus en `<div class='bandeau'>`
(pas en pied de page) : `LIBELLE` en tête de garde (l.155) ET en bandeau de CHAQUE page (paramètre
`libelle` de `bq.render_pdf`, l.304, « C7 bandeau de contexte sur chaque page ») ; `LIMITES` ouvre la
section 5 (l.258). Les deux disclaimers L.410-1 (« ne constitue pas un certificat d'urbanisme… seul
opposable ») sont donc **proéminents et répétés**. Bon point, doctrine respectée.

### Exemplaire NOMINAL — `97422000AD0675`, Le Tampon, 1969 m², **Uc 100 %** (calibré, constructible)

```
2 . Zonage applicable
   Uc  | 100% | PLU de Le Tampon, approuvé le 2023-08-11
3 . Règles principales (avec articles)
   Zone Uc   [moteur: constructible_neuf=True]
     Hauteur maximale : égout 9 m · faîtage 13 m   (Art. Uc10.2, p.46)
     Emprise au sol   : non réglementé             (Art. Uc9, p.46 : « Non réglementée »)
     Recul / voirie   : 4 m                         (Art. Uc6.2, p.43)
     Recul / limites  : 3 m                         (Art. Uc7.1, p.44)
     Pleine terre     : 30 %                        (Art. Uc13.2, p.52)
     Stationnement    : 1 place / logement          (Art. Uc12.2, p.50-51)
     » NOTE : Annexes : 3,5 m. Bande 3,60 m en limite : 6 m max.
     » NOTE : Annexes : 3,5 m. Bande 3,60 m en limite : 6 m max.   ← IMPRIMÉE DEUX FOIS (bug, cf. C1)
```

Sur ce cas simple, la lettre est **juste** (chaque règle a son article, millésime du PLU cité). Le seul
défaut visible ici est cosmétique (note dupliquée) — mais le même mécanisme est **cardinal** sur les
zones gelées (§B5).

---

## B — Les cas qui fâchent (un exemplaire réel par cas)

### B1 — Multi-zones · `97422000BV2471` (Le Tampon)  — **CONFORME**

Réel : **Nco 50 % / Ua 48 % / Uav 2 %** (`flash/data.py:172`, tri `pct DESC`, filtre `pct >= 1`).
La lettre **dit les parts** — elle n'atteste pas une zone unique. Section 2 liste les trois ; section 3
sort les règles de `zones[:3]`. Nco (naturelle, non calibrée) affiche « Règlement non calibré », Ua et
Uav sortent leurs règles. **Pas de faux positif** : une parcelle à moitié naturelle n'est jamais
attestée « Ua ». C'est la force du document. `lettre_zonage.py:198` (`zones[:3]`).

> Réserve mineure (cosmétique) : l'ordre `pct DESC` place Nco en tête (50 > 48) ; sur un quasi-partage
> 50/48, présenter la zone naturelle en premier est neutre voire prudent. Rien à redire.

### B2 — Conflit de source · `97422000CN1677` (Le Tampon) — **DETTE (incohérence inter-documents)**

Réel : la lettre imprime **Nco 64 % / Uc 35 %**. La zone servie AILLEURS dans l'app (fiche,
faisabilité) est celle du **centroïde = Uc** (`faisabilite/db.py:32-36`) — la part **minoritaire 35 %**.

- **Ce que lit la lettre** : l'intersection spatiale COMPLÈTE (toutes les parts par surface), ni
  l'étiquette `parcel_zone_plu`, ni le seul centroïde (`flash/data.py:163-172`).
- **Ce qu'elle dit** : Nco 64 % (naturelle, « règles non vérifiées ») en tête, puis les règles de Uc.

La lettre elle-même **n'est pas fausse** — elle divulgue le partage réel, ce qui est le comportement le
plus sûr pour une attestation. Le problème est de **cohérence de la famille** : la fiche/faisabilité
sert « Uc constructible » (dette §7 M133, `qa/faisabilite/DETTE_FAISABILITE.md:143-194`, 288 parcelles),
tandis que la lettre mène avec « Nco 64 % ». Un notaire qui compare fiche et lettre voit **deux documents
LABUSE désigner une zone dominante différente**. La lettre ne signale nulle part que sa source de zone
diverge du verdict servi. Gravité **dette** : rien de faux dans la lettre, mais l'incohérence inter-
documents est exactement le pire endroit (le document est fait pour être opposé).

### B3 — RNU · `97417000AC0003` (Saint-Philippe) — **FAUX NÉGATIF (cardinal pour l'audience tiers)**

Réel : `spatial_layers` ne porte qu'une zone `Npnr` à **pct = 0** (arrondi) → filtrée par `pct >= 1`
(`flash/data.py:172`) → liste vide → section 2 imprime :

```
2 . Zonage applicable
   « Zonage non résolu dans les couches numérisées (GPU) à la date d'édition
     — vérification en mairie indispensable. »   (lettre_zonage.py:162-164)
```

**Le problème.** Saint-Philippe est légalement au **RNU** — pas de PLU, jamais approuvé (statut confirmé,
`config/rnu_communes.yaml:29-38` ; DEAL/GPU/AGORAH cités). La lettre cadre ce fait comme une **lacune de
numérisation** (« non résolu dans les couches », « vérification en mairie »), ce qui **suggère qu'un
zonage PLU existe et n'aurait pas été ingéré**. La vérité inverse : il n'y a AUCUN document local, les
règles nationales s'appliquent. Le module doctrinal existe (`rnu.rnu_block` : « Commune au règlement
national d'urbanisme — pas de PLU local ») **mais la lettre ne l'appelle jamais** — elle n'importe pas
`rnu`. Sur une attestation remise à un tiers, dire « non résolu / à vérifier » là où la réalité est
« RNU assumé » est **matériellement trompeur**. Gravité **faux négatif** (l'absence de zonage est réelle,
mais sa NATURE — RNU vs trou de données — est fausse).

> Fragilité voisine : si l'intersection `Npnr` avait arrondi à ≥ 1 % au lieu de 0, la lettre aurait
> imprimé une zone `Npnr` **comme si Saint-Philippe avait un PLU** — un zonage fantôme. Ici le filtre
> `pct >= 1` sauve par chance, pas par conception.

### B4 — Commune non calibrée · `97409000AB0876` (Saint-André, **UC 100 %**) — **CONFORME (modeste)**

Réel : Saint-André n'a pas de `config/plu_saint_andre.yaml`. La lettre imprime :

```
2 . Zonage : UC | 100% | GPU 97409_20190228
3 . Règles : « Règlement non calibré pour cette zone/commune : règles non vérifiées
              — se reporter au règlement écrit. »   (lettre_zonage.py:203-206)
```

La lettre **reste au zonage pur** et ne parle jamais de droits ni de capacité (elle ne les calcule
nulle part). Réponse nette à la question du mandat : *pas de capacité estimée à signaler, la lettre ne
sort que le zonage et déclare les règles « non vérifiées »*. Honnête. **Réserve cosmétique** : le
millésime est présent mais cru (« GPU 97409_20190228 » au lieu d'une date lisible) — la date lisible
n'apparaît QUE pour les communes calibrées (`_approb_fr`, l.165-169, alimenté seulement si
`reg.get('document')`). Cosmétique.

### B5 — Zone GELÉE Us (6/11 gravé) · `97416000EP1044` (Saint-Pierre, **Us 100 %**) — **FAUX POSITIF CARDINAL**

C'est le constat central de l'audit. Réel, vérifié en exécutant le vrai code :

```
2 . Zonage : Us | 100% | PLU de Saint-Pierre, approuvé le 2024-06-25
3 . Règles :
   Zone Us   [moteur: constructible_neuf=False]        ← le moteur SAIT que c'est gelé
     Hauteur maximale : égout 6 m · faîtage 11 m   (Art. Us3 §5)
     » NOTE : Règle générale LOGEMENT : 6 m égout/acrotère, 11 m faîtage…   ← imprimée
     » NOTE : Règle générale LOGEMENT : 6 m égout/acrotère, 11 m faîtage…   ← imprimée (DOUBLON)
     [× NON IMPRIMÉE (coupe [:2]) : « Zone urbaine peu dense GELÉE provisoirement
        (construction neuve non autorisée)… capacité = aucune (gel) »]      ← LA SEULE note qui
                                                                              disait le gel : PERDUE
```

**Ce que la lettre atteste** : un tableau formel de règles « Hauteur : égout 6 m · faîtage 11 m », avec
article. Pour un notaire/banquier/acheteur, cela **se lit comme constructible jusqu'à 11 m**.

**La vérité** : `constructible_neuf = False` — zone gelée, construction neuve **non autorisée**, capacité
= aucune. La lettre **ne le dit jamais**. Deux défauts se cumulent :

1. **`_regles_zone` ne lit JAMAIS `constructible_neuf`** (`lettre_zonage.py:72-103`) — le statut de gel
   n'est pas structurellement rendu ; il ne survit QUE si une note en prose le mentionne, et…
2. **…la note de gel est coupée par le doublon + `[:2]`** (voir C1). Filet prose détruit.

Résultat : **une attestation qui affiche des hauteurs constructibles sur une zone où la construction
neuve est interdite, sans jamais l'écrire.** C'est précisément « la lettre qui atteste plus que la
donnée, remise à un tiers ». Gravité **faux positif cardinal**. Le moteur commun (Flash/argumentaire/
fiche, post-M131) gère le gel explicitement ; la lettre est le seul document de la famille à l'ignorer.

### B6 — ZAC · `97415000CW1073` (Saint-Paul, **AU3a 99 %**, ZAC Renaissance III) — **DETTE M144 + risque faux positif**

Réel :

```
2 . Zonage : AU3a | 99% | PLU de Saint-Paul, approuvé le 2012-09-27  ;  Nto | 1%
3 . Règles :
   Zone AU3a   [moteur: constructible_neuf=True]
     Hauteur : égout 15 m · faîtage 19 m   (Zone U3a, Art. 10.2, p.110-112)
     Recul/voirie : 0 m  ·  Recul/limites : 3 m  ·  Pleine terre : 20 %  ·  Station. : 1,5/logt
     » NOTE : Sous-cas : hé 18 / hf 22…              ← imprimée
     » NOTE : Sous-cas : hé 18 / hf 22…              ← imprimée (DOUBLON)
     [× NON IMPRIMÉE ([:2]) : « … ZAC Savane des Tamarins : retrait 3 m possible… »]
```

La lettre affirme les règles PLU de AU3a **comme si elles gouvernaient**, sans aucune couche ZAC (angle
mort documenté, dette M144). Or CW1073 est en **ZAC Renaissance III**, dont le Règlement d'Aménagement de
Zone (RAZ) peut modifier hauteurs/reculs/emprise. La lettre ne signale nulle part « parcelle en ZAC — se
reporter au règlement de zone ». Elle **affirme donc des règles qu'une ZAC pourrait contredire**, ce que
le mandat B6 demandait de vérifier : c'est le cas. Aggravant cosmétique : la note tronquée nomme **une
autre ZAC** (« ZAC Savane des Tamarins »), sans rapport avec Renaissance III — attribution potentiellement
trompeuse si elle sortait. Gravité **dette** (couche ZAC absente = M144) **+ risque faux positif** (règles
opposées par le RAZ). La lettre n'affirme rien de faux *dans le PLU*, mais tait le régime ZAC applicable.

---

## C — Les dates

### C1 — Le défaut de troncature de notes (transverse, RÉEL sur toute lettre calibrée)

Ce n'est pas qu'une date, mais c'est la mécanique qui casse B5. À isoler nettement.

`lettre_zonage.py:99-101` (`_regles_zone`) :
```python
notes = list(r.notes or [])                       # r.notes CONTIENT DÉJÀ hauteur_note
if r.raw.get("hauteur_note"):                      #   (ZoneRules.notes = clés finissant par _note)
    notes.insert(0, str(r.raw["hauteur_note"]))    # → hauteur_note DUPLIQUÉE en tête
```
puis `lettre_zonage.py:218` (`_regles`) : `for n in rz["notes"][:2]:` — cap à 2.

**Conséquence, mesurée sur données réelles** (`_contenu_reel.txt`) : toute zone calibrée portant un
`hauteur_note` voit sa 1ʳᵉ note **imprimée deux fois**, ce qui **consomme les deux emplacements** et
**laisse tomber silencieusement toutes les notes suivantes** :

| Zone | Note dupliquée | Notes matérielles PERDUES par `[:2]` |
|------|----------------|--------------------------------------|
| Us (Saint-Pierre) | « 6 m / 11 m… » | **le GEL** (« construction neuve non autorisée, capacité = aucune ») |
| Ua (Le Tampon) | « Annexes 3,5 m… » | alignement RD3, option limites séparatives, stationnement collectif LLS, **perméabilité** |
| AU3a (Saint-Paul) | « Sous-cas hé 18/22 » | retrait ZAC, perméabilité 13.1 |
| Uc (nominal) | « Annexes 3,5 m… » | (aucune autre — visible seulement comme doublon) |

Gravité : **faux positif cardinal** en zone gelée (§B5) ; **faux négatif** ailleurs (règles matérielles
amputées d'une attestation) ; **cosmétique** partout (même note deux fois sur un document formel). Racine
unique, l.99-101.

### C2 — Millésime du PLU attesté

**Présent pour les communes calibrées.** `_zonage` (l.177-179) sort « PLU de <commune>, approuvé le
<date> » via `resolve_reglement().approbation` (date d'approbation RÉELLE par commune, lue de
`config/plu_<commune>.yaml › source › approbation` — pas codée en dur ; ex. Le Tampon 2023-08-11,
Saint-Pierre 2024-06-25, Saint-Paul 2012-09-27). **Conforme** : une vérification de zonage porte bien le
millésime du document vérifié. Pour les communes **non calibrées** (B4), seul le millésime GPU cru
(« GPU 97409_20190228 ») apparaît — présent mais non lisible (cosmétique).

### C3 — Deux dates (patron M139/M143)

**Sans objet, correctement.** La lettre ne fait entrer **aucune valeur d'un run servi** (pas de SDP, pas
de capacité, pas de scoring). Il n'y a donc qu'une date d'édition (`date.today()`) + le millésime du PLU.
Le patron « deux dates » ne s'applique pas — périmètre modeste assumé. Bon.

### C4 — « à la date d'édition »

La date d'édition est `date.today()`, rendue en clair en garde (« éditée le JJ/MM/AAAA », l.143/153) et
en clôture (l.268/271). Le texte de `LIMITES` (« … tels que numérisés à la date d'édition ») pointe cette
même date, **visible et exacte**. Conforme.

---

## D — Libellés et doctrine

- **Promesse vs donnée.** Titre « Lettre de vérification de zonage · attestation documentaire » (l.151),
  h1 « Lettre de vérification de zonage » (l.152). `LIBELLE` et `LIMITES` désamorcent explicitement
  (« ne constitue pas un certificat d'urbanisme… seul opposable »). Le corps **ne promet pas** « PDF
  officiel » ni opposabilité (l'interdit du mandat sur le mot « opposable » appliqué à la lettre est
  **respecté** : « opposable » n'apparaît que pour QUALIFIER le certificat d'urbanisme, jamais la lettre).
  `_cloture` reste modeste (« valable en l'état de ses sources »). **Conforme** — sous réserve que le
  *contenu* ne sur-atteste pas, ce qui casse en B5 (le titre « vérification » + un tableau de hauteurs
  sur zone gelée promet, de fait, plus que la donnée).
- **Rang / score.** grep `rang|score|tier|classement|verdict` sur `lettre_zonage.py` → **néant** dans le
  rendu. `collect_report_data` calcule bien un rang/tier (`flash/data.py:282`, `verdict_servi`) mais la
  lettre **ne lit que** `identite.zones`, `risques`, `patrimoine`, `sources` — jamais le verdict. **M133
  B.6 respecté** (aucun verdict/score/rang en export).
- **Jeton interne en prose.** Aucun « (Absent) » façon Flash, aucun jeton brut. **Conforme.**
- **Vocabulaire des absences** (doctrine M130-9/M130-12) :
  - Servitudes vides → « Aucun élément dans les couches numérisées… ce constat ne vaut pas absence de
    servitude » (l.246-248). **Exemplaire** — on n'affirme jamais l'absence du non-modélisé.
  - Règle à valeur nulle mais sourcée → « non réglementé » avec l'article (l.64). **Conforme.**
  - **Zonage vide → « Zonage non résolu… vérification en mairie » (l.162-164) : le seul faux pas** — il
    conflatte le RNU (absence légale de PLU) avec un trou de numérisation (§B3).

---

## E — Exposition (constat, dette F4)

Route publique de la famille : `lettre_zonage_pdf` (`lettre_zonage.py:310-320`) appelle `porte_export`
(`quota.py:62`), qui **renvoie tout-None et laisse passer sans session** (`quota.py:69-71`, « en
pilote/dev sans session »). **Sans authentification, l'IDU est énumérable dans le path** (`/lettre-zonage/<idu>.pdf`).

Pire que la fiche : `/lettre-zonage` **n'est même pas dans `PREFIXES_PROTEGES`** (`protection.py:150-153`)
— la garde anti-abus (burst/quota, défi de challenge) **ne s'engage pas** sur cette route (`protection.py:300`
laisse passer tout droit ce qui ne préfixe pas la liste). L'attestation n'est donc ni derrière l'auth, ni
derrière le rate-limit : **route ouverte**.

Nuance propre à CE document, à consigner en dette F4 : ce n'est pas une fiche de données publiques, c'est
une **attestation générable par n'importe qui au nom de LABUSE**. Deux effets de bord aggravants,
spécifiques :

1. `_ref_attestation` (l.108-130) **écrit une ligne en base à CHAQUE génération** (`LZ-AAAA-NNNN`,
   numérotation officielle) — donc une énumération non authentifiée **fabrique des références
   d'attestation officielles** en série (même famille de risque que le compteur Flash de M145).
2. Numérotation par `count(*) … WHERE ref LIKE 'LZ-AAAA-%'` puis `n+1` (l.119-122) — sensible aux
   suppressions (trous/réemploi ; le retry sur `UNIQUE` couvre la collision mais pas la sémantique).
   Dette mineure, à noter à côté de F4.

Gravité **dette** (constat, pas de correctif — hors périmètre M146).

---

## F — Verdict franc

**Peut-elle être remise à un notaire aujourd'hui ?**

- **Parcelle mono-U calibrée, constructible (nominal, B1, B4)** : oui sur le fond (zonage juste, articles,
  millésime), **mais** amputée de règles matérielles par le défaut C1, et une note visiblement dupliquée
  fait tache sur un document formel. *Acceptable après C1.*
- **Zone GELÉE calibrée (Us / 2AU — B5)** : **NON.** Atteste des hauteurs constructibles sur une zone où
  la construction neuve est interdite, sans jamais le dire. **Bloquant.**
- **Commune au RNU (B3)** : **NON.** Cadre le RNU en « zonage non résolu / à vérifier en mairie »,
  suggérant un PLU non numérisé là où il n'y a pas de PLU. **Bloquant** pour l'audience tiers.
- **Parcelle en ZAC (B6)** : **risqué.** Affirme les règles PLU qu'un RAZ peut modifier, sans caveat ZAC.
- **Multi-zones / conflit de source (B1/B2)** : la lettre est **honnête** (elle dit les parts) mais
  **diverge de la fiche** (zone servie par centroïde) — incohérence de famille à assumer.

**Défauts (à corriger) vs manques (à assumer)** :

| Constat | fichier:ligne | Gravité |
|---------|---------------|---------|
| Zone gelée : `constructible_neuf=False` jamais rendu → hauteurs attestées comme constructibles | `lettre_zonage.py:72-103` (absent) + `:99-101`/`:218` | **faux positif (cardinal)** |
| Doublon de note (`insert(0, hauteur_note)` sur `r.notes` qui la contient déjà) + coupe `[:2]` → règles matérielles perdues | `lettre_zonage.py:99-101`, `:218` | **faux négatif** (+ cosmétique) |
| RNU cadré en « zonage non résolu » (module `rnu.rnu_block` jamais appelé) | `lettre_zonage.py:162-164` | **faux négatif** |
| ZAC : aucune couche, règles PLU affirmées sans caveat RAZ | `lettre_zonage.py:195-224` (dette M144) | **dette** + risque faux positif |
| Conflit de source zone : lettre (intersection) diverge de la fiche (centroïde), non signalé | `flash/data.py:163-172` vs `faisabilite/db.py:32-36` (dette §7 M133) | **dette** |
| Exposition : attestation générable sans session ; écrit une réf. en base à chaque génération | `quota.py:69-71`, `lettre_zonage.py:310`, `:108-130` | **dette (F4)** |
| Numérotation `LZ-` par `count(*)+1` (trous/réemploi sur suppression) | `lettre_zonage.py:119-122` | **dette** (mineure) |
| Millésime GPU cru pour communes non calibrées (« GPU 97409_20190228 ») | `lettre_zonage.py:181` | **cosmétique** |
| Note tronquée nommant une ZAC sans rapport (Savane des Tamarins sur parcelle Renaissance III) | `config/plu_saint_paul.yaml` (note AU3a) via `:218` | **cosmétique** |

**Améliorations valeur/coût** (pour l'arbitrage de Vic, non implémentées) :
- **C1 (coût minime, valeur maximale)** : supprimer le doublon l.100-101 (la `hauteur_note` est déjà dans
  `r.notes`) **et** relever le cap `[:2]` ou prioriser la note de gel. Débloque B5 et rend les règles aux
  autres lettres d'un coup. C'est LA correction à faire en premier.
- **B5 structurel** : rendre `constructible_neuf=False` explicitement (bandeau « Zone gelée — construction
  neuve non autorisée » en tête de la section règles), ne pas dépendre d'une note en prose.
- **B3** : brancher `rnu.rnu_block` — quand la commune est au RNU, dire le RNU, pas « non résolu ».
- **B6** : caveat ZAC si une couche ZAC intersecte (dette M144 partagée).

**Le périmètre honnête** de ce document est « zonage + règles calibrées, avec articles, sans capacité » —
et c'est un bon périmètre, **modeste et vrai**. L'architecture le sert bien (toutes les parts, article
obligatoire, disclaimers proéminents, zéro verdict). Ce qui l'empêche d'aller chez un tiers aujourd'hui
n'est pas son ambition mais **trois fuites précises** : le gel non dit (C1+B5), le RNU conflaté (B3), et
la troncature de règles (C1). Corriger C1 seul remonte déjà la plupart des cas au vert.

---

*Contrôles : garde-fou OK (branché sur `origin/main` @ `7b13b00e`, hors périmètre de l'avance) ;
exemplaires extraits sur base réelle `labuse` via les vrais résolveurs (`resolve_zone`,
`resolve_reglement`) et le vrai SQL de `flash/data.py` — joints en `qa/lettre_zonage/exemplaires/_contenu_reel.txt` ;
aucune ligne de code modifiée (audit lecture seule). CC ne merge jamais — Vic arbitre la correction.*
