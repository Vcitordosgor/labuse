# OUTILS-LOT-4 — petits défauts notés en recette

Branche `fix/outils-lot-4` depuis `origin/main` (`9831d3e14`). Pas de merge, DA existante. Une capture
avant/après par point (cadrée sur l'élément) dans ce dossier. Hook vert.

| # | Point | État | Captures |
|---|-------|------|----------|
| 1 | Solaire : « 8.3° » avec une virgule ; aucun décimal au point | **Fait** | `lot4-01-02-solaire-{AVANT,APRES}` |
| 2 | Solaire : retirer « Écartée » (classement LABUSE) | **Fait** | idem |
| 3 | Pièges : carte du risque naturel trop longue → détail replié | **Fait** | `lot4-03-pieges-risque-{AVANT,APRES}` |
| 4 | Pièges : parcelle 100 % rouge → supprimer « hors zone rouge (0 %) » | **Fait** | `lot4-04-pieges-rouge100-{AVANT,APRES}` |
| 5 | Courrier : destinataire avec nom complet + forme juridique | **Fait** | `lot4-05-courrier-destinataire-{AVANT,APRES}` |
| 6 | Assemblage : astérisque orphelin de la note « * SDP bâti conservé estimée » | **Fait** | `lot4-06-07-assemblage-{AVANT,APRES}` |
| 7 | Assemblage : « fiab. moyenne » → « fiabilité moyenne » | **Fait** | idem |
| 8 | Accueil : sous-titres tronqués par « … » | **Fait** | `lot4-08-accueil-{AVANT,APRES}` |
| 9 | Fiche : nom du propriétaire coupé dans « Identité » | **Fait** | `lot4-09-fiche-identite-{AVANT,APRES}` |
| 10 | Ancien test qui échoue sur un libellé de date | **Fait + rapport** | (test) |

---

### 1 — Solaire : décimales à la virgule
`ProspectionSolaire.tsx` : « Pente du terrain » et « Orientation du bâti » interpolaient le nombre brut
(`${f.pente}°` → « 15.7° »). Helper `dec(v) = String(v).replace('.', ',')` appliqué à la pente et à
l'azimut (la pente du toit médiane et la puissance kWc utilisaient déjà la virgule). Témoin 97401000AB0006
(Les Avirons) : **« 15.7° » → « 15,7° »** (et 33,3° inchangé). Verrou de test : fixture pente `8.3`
→ assert `8,3°` present / `8.3` absent.

### 2 — Solaire : aucune analyse LABUSE
Le classement LABUSE (`f.classement` : « Écartée », « Neutre »…) était collé au nom de la commune dans
l'en-tête de la fiche soleil. **Retiré** : la prospection solaire ne porte que des faits (potentiel,
toiture, orientation), aucun verdict. Témoin AB0006 : **« Les Avirons · Écartée » → « Les Avirons »**.

### 3 — Pièges : carte du risque naturel repliée
La carte « Risque naturel (PPR / aléa) » agrège TOUS les effets (PPR rouge + bleu + aléas) joints par
« · » — jusqu'à 5 lignes, 600+ caractères. `blocB.tsx` : le **1ᵉʳ effet (le plus fort) reste visible**,
le reste passe dans un repli `<details>` « Détail · N autres ». Témoin 97401000AB0007 (5 effets) :
AVANT = un pavé de 606 caractères ; APRÈS = 1 ligne + « ▸ Détail · 4 autres ».

### 4 — Pièges : plus de « hors zone rouge (0 %) »
`servitudes.py _ppr_ligne` : pour une zone rouge sur `pct` % de la parcelle, `hors = 100 − pct` ; quand
`pct = 100` (toute la parcelle rouge), la phrase « Partie hors zone rouge (0 %) : constructible… »
n'a pas de sens. **Elle n'est désormais ajoutée que si `hors > 0`.** Témoin 97401000AC0003 (100 % rouge) :
AVANT = « …quelle que soit la surface. **Partie hors zone rouge (0 %) : constructible**… » ; APRÈS =
« …quelle que soit la surface. » (point final). Verrou `_ppr_ligne("rouge", …, 100)`.

### 5 — Courrier : nom complet + forme juridique
`courrier_adressage.py` : le destinataire PM nommait la dénomination seule (« MOUTOUSSAMY EMILE »), qui se
lit comme une personne physique. On préfixe la **forme juridique** (`parcelle_personne_morale.forme_juridique`)
quand elle est **commerciale** (SARL/SCI/SAS/SA/SNC/SCEA/EARL/GFA…) et absente du nom — garde anti-doublon
(« SCI DESTINO » reste tel quel). Les entités publiques/institutionnelles (COMMUNE DE…, DÉPARTEMENT…,
SOCIÉTÉ IMMOBILIÈRE…) se nomment déjà en entier → pas de code collé (« COM », « DEPT », « SEM »). Source
unique de l'adressage → écran ET pli. Témoin 97411000BP0863 : **« MOUTOUSSAMY EMILE » → « SARL MOUTOUSSAMY
EMILE »** (— au siège social déclaré). Verrous purs `_nom_affiche`.

### 6 — Assemblage : astérisque orphelin
La note « * SDP bâti conservé estimée… » s'affichait dès `sdp_conserve_estimation`, mais l'astérisque
n'est posé sur la ligne « Si conservé » QUE lorsque `sdp_bati_conserve_m2 > 0`. Quand la ligne dit « aucun
ajout estimé » (conservé = 0), la note restait **sans astérisque de rappel**. `moteurs.tsx` : la note est
désormais gardée par `sdp_conserve_estimation && sdp_bati_conserve_m2 > 0` — elle ne paraît que si un
astérisque est réellement écrit. Témoin 97418000 AO0368+AO0950 (conservé = 0) : AVANT = note orpheline ;
APRÈS = pas de note. Verrous de test (présente si conservé > 0, absente si conservé = 0).

### 7 — Assemblage : « fiabilité » en toutes lettres
`moteurs.tsx` : « DVF · fiab. {niveau} » → « DVF · **fiabilité** {niveau} ». Témoin même assemblage :
AVANT = « fiab. moyenne » ; APRÈS = « fiabilité moyenne ». Verrou de test.

### 8 — Accueil : sous-titres non tronqués
`LeftPanel.tsx` (`AccEntry`) : le sous-titre des cartes utilisait `truncate` (nowrap + ellipse) → « couches,
filtres, Analyse … », « Dossier, Bilan, Étude… su… ». **`truncate` retiré du sous-titre** → il passe à la
ligne (la carte fait 64 px, large de reste). Le titre, court, reste sur une ligne. AVANT/APRÈS visibles sur
les 5 cartes.

### 9 — Fiche : nom du propriétaire entier dans « Identité »
`Fiche.tsx` : la valeur du tiroir « Identité » était coupée à 18 caractères (`proprioType.slice(0, 18)` →
« RESIDENCE LES BAMB »). La classe `.t-val` enroule déjà (max-width 150 px, `break-word`) : le `slice` était
la seule troncature. **Retiré.** Témoin 97411000AB0670 : **« RESIDENCE LES BAMB » → « RESIDENCE LES
BAMBOUS »** (sur deux lignes).

### 10 — Test de libellé de date : l'écran a raison
Test en échec : `tests/test_servitudes.py::test_flux_sup_sourcee_datee_et_dedup` attendait
`it["date"] == "ingéré le 10/07/2026"`, l'écran sert `"au 10/07/2026"`.

**Lequel a raison : l'écran (« au 10/07/2026 »).** Le repli d'ingestion a été renommé par décision Vic
(DOCS-1) dans `millesime_source.libelle_date_source` : « *« ingéré le » est un mot de cuisine interne,
banni des documents client* » → la source sans millésime amont publié est datée « **au** JJ/MM/AAAA ». Le
test (et deux commentaires de `servitudes.py`) portaient encore l'ancien libellé. **Accordé** : test mis
sur « au 10/07/2026 », commentaires corrigés. (Les tests qui mentionnent encore « ingéré le » sont soit des
listes de mots BANNIS à vérifier absents, soit la page interne Sources — contextes légitimes, non touchés.)

---

## Tests (au premier plan)
`npx tsc -b` 0 · `npx vitest run` **335** · `pytest -m "not db and not local and not reel and not network"`
**3308 passed, 49 skipped** · `scripts/ci/coherence_run.sh` **7 passed** · `scan_secrets.sh` rien trouvé.

Fichiers : `ProspectionSolaire.tsx` (1, 2), `blocB.tsx` (3), `servitudes.py` (4, 10), `courrier_adressage.py`
(5), `moteurs.tsx` (6, 7), `LeftPanel.tsx` (8), `Fiche.tsx` (9) ; tests : `ProspectionSolaire.test.tsx`,
`Assemblage.test.tsx`, `test_servitudes.py`, `test_courrier_nom_affiche.py` (nouveau).

PIÈGE setup : le worktree avait `three` déclaré dans `package.json` mais absent de `node_modules` (travail
Gabarit 3D fusionné dans main) → `npm install` requis avant que `tsc` passe.
