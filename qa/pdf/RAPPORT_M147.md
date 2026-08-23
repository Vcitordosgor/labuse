# M147 — Lettre de zonage : le filet, le gel, le RNU (`fix/m147-lettre-zonage`)

Branché sur `origin/main` @ `ae1597de` (merge `feat/solaire-detection-pv`). Périmètre intact vérifié :
le diff `7b13b00e..ae1597de` ne touche ni `lettre_zonage`, ni `plu_rules`, ni `rnu`, ni `flash/data`.
Corrige les constats de l'audit M146. **CC ne merge jamais.**

**Résumé : une seule ligne (le doublon de note) tombe → toutes les règles matérielles reviennent. Le
gel est dit AVANT le chiffre (bandeau ⚠ « construction neuve non autorisée », colonne « Règle si
ouverture », valeurs M131 6/11 et renvois toujours servis). Le RNU est branché (Saint-Philippe cesse de
dire « zonage non résolu » et dit le RNU). La zone AU porte un caveat ZAC générique et vrai, sans rien
détecter par parcelle. Multi-zones/parts, millésime, disclaimers, zéro score : intacts. ruff 0 nouvelle,
py_compile vert.**

Un seul fichier de code touché : `src/labuse/api/lettre_zonage.py` (+64/−11).

---

## Lot 1 — La ligne (racine transverse)

**Le doublon (`lettre_zonage.py:99-101`).** `ZoneRules.notes` collecte déjà toute clé YAML finissant par
`_note` — dont `hauteur_note`. L'ancien `notes.insert(0, r.raw["hauteur_note"])` la **ré-insérait** :
la 1ʳᵉ note était imprimée deux fois. **Supprimé.** `_regles_zone` retourne désormais `r.notes` tel quel
(la `hauteur_note` y est déjà, en tête naturelle).

**Le `[:2]` (`_regles`, ancienne l.218).** Établi : la coupe était **purement éditoriale** (aucune limite
de gabarit — `bq.render_pdf` (fpdf2) **pagine** le flux HTML, il ne tronque pas). Une note matérielle ne
doit jamais tomber pour une raison de place : **coupe supprimée**, `for n in rz["notes"]:` sort toutes les
notes. Si l'espace manque, la lettre pagine.

**Contrôle (données réelles, `_contenu_reel_apres.txt`) :**
- **Us** : `hauteur_note` **1×** (assert `count == 1`), et la note de GEL — jusqu'ici coupée — **présente**.
- **Ua** : les **5 notes** présentes (annexes, alignement RD3, option limites séparatives, stationnement
  collectif LLS, perméabilité), **aucune en double**.
- **AU3a** : les 3 notes présentes (sous-cas 18/22, retrait ZAC, perméabilité 13.1).

## Lot 2 — Le gel, dit explicitement (cardinal)

`_regles_zone` lit maintenant `r.constructible_neuf` et renvoie `"gel": not r.constructible_neuf`
(structurel, plus dépendant d'une note en prose). Dans `_regles`, quand `gel` :
- titre `Zone <code> — zone gelée` ;
- **AVANT le tableau**, un `<div class='bandeau'>` (même proéminence que les disclaimers L.410-1) :
  *« ⚠ Zone gelée à la date d'édition : construction neuve non autorisée. Les valeurs ci-dessous sont
  les règles qui s'appliqueraient si la zone était ouverte à l'urbanisation ; elles ne valent pas
  autorisation de construire. »* ;
- colonne du tableau renommée **« Règle si ouverture »** (au lieu de « Valeur calibrée »).

La condition gouverne le chiffre (doctrine M143 L1 / M145 B.1.4) — jamais l'inverse.

**Contrôle :**
- **EP 1044** (Saint-Pierre, Us) : bandeau de gel **avant** le `<table>` (assert `index(gel) < index(table)`) ;
  hauteur **6 m / 11 m** (Art. Us3 §5) **toujours servie**.
- **2AU du Tampon** (`97422000AK0771`, 2AUc) : gel dit ; hauteur **9 m / 13 m par renvoi** (AUindicée→Uc)
  **servie**. Les valeurs M131 (gravées + renvois) restent intactes.

## Lot 3 — Le RNU

`rnu.rnu_block(idu, db)` existait et n'était **jamais appelé** (constat M146 §B3). Branché dans
`_build_pdf` (calculé une fois, `None` hors commune RNU), passé aux sections 2 et 3 :
- **Section 2** (`_zonage`) : si RNU, bandeau **« Commune au règlement national d'urbanisme — pas de PLU
  local »** + `DETAIL_RNU` + commune et date de vérification du statut — **au lieu de** « zonage non
  résolu dans les couches numérisées » (qui imputait un fait de droit à un défaut de numérisation).
- **Section 3** (`_regles`) : si RNU, mention **« non applicable — RNU »** (`rnu.NON_APPLICABLE_RNU`,
  wording Vic) — jamais un en-tête de règles vide.

Une commune au RNU n'a pas de zonage PLU à attester : le RNU **est** la réponse, servie en tête.

**Contrôle :** `97417000AC0003` (Saint-Philippe) → « Commune au règlement national d'urbanisme — pas de
PLU local », « statut vérifié le 2026-07-26 » ; « zonage non résolu » **absent** (assert).

## Lot 4 — La ZAC, caveat honnête (pas de détection)

Aucune couche ZAC (dette M144) : **on n'invente rien par parcelle.** Mais sur une zone **AU** (détectée
sur le subtype GPU `classe` commençant par `AU` — pas sur le libellé, pour ne pas confondre `Uav` avec de
l'AU), `_regles` ajoute une phrase **générique et vraie** : *« Zone d'urbanisation future : l'ouverture à
la construction est conditionnée à une opération d'aménagement d'ensemble. Un périmètre d'aménagement
(ZAC) peut s'y appliquer, avec un règlement propre — à vérifier auprès de la commune ; il n'est pas
modélisé dans la présente lettre. »*

**Contrôle :** AU3a (`97415000CW1073`) → caveat présent ; **Us** (zone U gelée) → caveat AU **absent**
(bonne séparation : le gel et l'AU sont deux régimes distincts, le 2AU cumule les deux à juste titre).

---

## Contrôles finaux

- **Six exemplaires régénérés** par le VRAI code M147 sur base réelle : `qa/lettre_zonage/exemplaires/`
  (`_contenu_reel_apres.txt` = après ; `_avant_apres.md` = tableau avant/après par cas).
- **Non-régression (assertions automatiques, toutes vertes)** : multi-zones sortent les parts
  (Nco 50 / Ua 48 / Uav 2 ; Nco 64 / Uc 35) ; millésime du PLU cité (11/08/2023, 25/06/2024, 27/09/2012) ;
  `LIBELLE`/`LIMITES` non touchés ; **aucun rang/score/tier/verdict** (grep vert).
- **ruff** : 3 constats sur le fichier (2×E741 `l`, 1×I001) — **identiques à `origin/main`** (dette
  préexistante), **0 nouvelle erreur** introduite. **py_compile** vert.
- **tsc** : sans objet — aucun fichier TypeScript touché (mandat 100 % back).

## Hors périmètre, en dette (signalé, non corrigé)

- **B2 — conflit de source lettre/fiche** : la lettre lit l'intersection spatiale (Nco dominant), la
  fiche/faisabilité le centroïde (Uc) → deux documents désignent une dominante différente. C'est **§7
  M133** — correctif de fond AMONT (source de zone unifiée), pas un rustine dans cette lettre.
- **F4 — exposition** : `/lettre-zonage` est **hors `PREFIXES_PROTEGES`** (ni auth ni rate-limit) **et**
  `_ref_attestation` écrit une référence officielle `LZ-AAAA-NNNN` en base **à chaque appel anonyme**.
  Aggravé par la nature attestataire du document. À traiter au niveau routing/quota, hors M147.

---

*Push `fix/m147-lettre-zonage`. Vic arbitre le merge — CC ne merge jamais.*
