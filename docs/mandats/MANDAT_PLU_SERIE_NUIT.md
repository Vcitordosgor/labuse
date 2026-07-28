# MANDAT PLU-SÉRIE-NUIT — GRAVURE DES 17 COMMUNES RESTANTES

**Nature** : exécution **non supervisée**. Vic dort. Aucun point d'arrêt bloquant.
**Principe unique en cas de doute** : on **saute la commune** et on consigne. On ne devine jamais, on n'attend jamais.
**Exécuteurs** : Claude Code, modèle **Fable**, 2 sessions d'extraction (A, B) + 1 session de contre-extraction (C, phase 3).
**Ce mandat complète le mandat-cadre** (`MANDAT_CADRE_PLU_instance_saint_pierre.md`) : tout ce qui n'est pas redéfini ici s'y applique tel quel, §9 (leçons accumulées) inclus. Lire le §9 AVANT de commencer — il contient les leçons de Saint-Pierre et du Tampon.

---

## 0 · CE QUI EST EN JEU

À la fin de cette nuit, LABUSE passe de 4 communes calibrées en règles chiffrées à potentiellement 21 sur 24. C'est le passage de « SDP estimée » à « SDP tracée par article » sur l'essentiel de l'île — l'argument que la concurrence ne peut pas répliquer, et la correction du biais mesuré trois fois (repli générique optimiste : −33 / −33 / −53 % de SDP médiane).

**C'est précisément parce que l'enjeu est élevé que la règle est : la qualité ne baisse JAMAIS.** Une commune sautée est un succès du mécanisme. Une commune devinée est le seul vrai échec possible de cette nuit — elle produirait des chiffres faux étiquetés Sourcé, le pire faux positif du produit.

### Invariants de qualité — identiques à Saint-Pierre et au Tampon, aucune exception nocturne

1. **Chaque valeur porte sa source** : article + page (page du PDF, offset documenté). Zéro valeur non sourcée dans un YAML.
2. **Jamais deviner.** Ambiguïté, renvoi non résolu, contradiction entre articles, graphie non tranchée → zone **non calibrée**, passage cité verbatim au rapport.
3. **Règles à tiroirs** : tranche dominante = la plus conservatrice. Quand on ne sait pas, on sous-estime — jamais l'inverse.
4. **Aucune rétro-ingénierie depuis la base.** Les règles se lisent dans le règlement, uniquement.
5. **COS** : vérifier la date d'approbation avant tout usage (aboli ALUR 2014) ; s'il figure dans un document post-2014, le consigner sans l'appliquer.
6. **Sous-secteurs** : une entrée distincte chacun, jamais d'héritage implicite.
7. **Destinations d'abord** (leçon Tampon) : lire l'Art. 1/2 (interdictions) avant les chiffres — `habitat: interdit` prime sur tout calibrage de hauteur.
8. **`source.reglement_grave`** posé dans chaque YAML : fichier, **md5**, millésime, identifiant du document GPU au calibrage, date.
9. **Aucun quota.** Une commune à 40 % de zones correctement gravées, le reste en repli honnête motivé, est un livrable valide.

---

## 1 · PHASE 0 — PRÉ-VOL (session A seule, ~30 min, AUCUN accès base)

Script unique sur les 17 communes : Les Avirons, Bras-Panon, Cilaos, Entre-Deux, L'Étang-Salé, Petite-Île, La Plaine-des-Palmistes, Le Port, La Possession, Saint-Benoît, Saint-Joseph, Saint-Louis, Sainte-Marie, Sainte-Rose, Sainte-Suzanne, Salazie, Les Trois-Bassins.
(Hors périmètre : Saint-André et Saint-Leu — dépubliés du GPU, dossiers d'appel prêts pour Vic. Saint-Philippe — RNU, rien à graver.)

Pour chaque commune :
1. **Concordance GPU** : idurba du document en vigueur vs manifeste `config/calibrage/zonage_<commune>.yaml`.
2. **Téléchargement du règlement** en vigueur : md5, nombre de pages, **offset pagination PDF ↔ pagination imprimée** (leçon Tampon : l'écart des deux paginations a produit 3 citations de page fausses).
3. **Inventaire des libellés** du manifeste : croisement avec le texte (détection des graphies divergentes type « Uc1 » vs « UC 1 »), croisement avec `o12_zones_activite.yaml` (pré-identification des zones habitat-interdit — leçon Saint-Pierre).
4. **Alertes automatiques** : COS détecté · dépublication · document en révision · plus de 20 % de libellés non rattachables.

**Sortie** : tableau par commune → `PRET` / `À SAUTER` (motif précis), nombre de zones, **pool servi** (nombre de parcelles), signaux de difficulté (règles à tiroirs détectées, densité de renvois).

Puis **répartition en 2 lots équilibrés par pool servi ET par difficulté** — pas par simple compte de communes. **Ordre de traitement dans chaque lot : pool servi décroissant.** Si la nuit tourne court, les communes qui pèsent sont faites.

La session A écrit le tableau dans `docs/mandats/PLU_NUIT_PREVOL.md`, le commite, puis attaque son lot. La session B lit ce fichier au démarrage et attaque le sien.

## 2 · PHASE 1 — EXTRACTION (sessions A et B en parallèle)

| Session | Clone | Branche |
|---|---|---|
| A | `labuse-plu` | `feat/plu-nuit-a` |
| B | `labuse-plu-b` | `feat/plu-nuit-b` |

**Un commit par commune**, message `[PLU-NUIT] <Commune> — N zones calibrées / M non calibrées`. Fable ne merge jamais. Ne jamais toucher une commune de l'autre lot.

### Boucle par commune

1. Vérifier le statut pré-vol. `À SAUTER` → consigner, suivante.
2. **Passe destinations** (Art. 1/2 toutes zones) → `habitat: interdit` posés et sourcés.
3. **Passe chiffres** par famille de zones (U par pool décroissant, puis AU, puis A/N seulement si règles réellement consommables — sinon décision motivée de non-calibrage, comme à Saint-Pierre).
4. **Porte de sortie de commune — obligatoire, sans base** :
   a. Tous les libellés du manifeste sont soit calibrés, soit explicitement non calibrés avec motif. Aucun libellé orphelin silencieux.
   b. **Script de re-vérification des citations** (celui du Tampon, qui y a corrigé 14 citations dont 3 pages fausses) : chaque (article, page) du YAML est re-résolu contre le PDF. Zéro citation non vérifiée en sortie.
   c. Le YAML se charge sans erreur (test de chargement local, sans base applicative).
5. Commit. Commune suivante.

### Motifs de saut (consigner avec le passage cité, ne jamais forcer)

Divergence de millésime · règlement introuvable ou OCR défaillant · >20 % de libellés non rattachables après tentative de résolution des graphies · chaîne de renvois non résolue touchant >3 zones · règles conditionnelles que le schéma v1 ne porte pas et qui touchent l'essentiel de la commune · toute situation où graver exigerait de deviner.

## 3 · PHASE 2 — CONTRE-EXTRACTION À L'AVEUGLE (session C, après les extractions)

**Le mécanisme de contrôle de la nuit.** Sans lui, un biais systématique de lecture serait répliqué 17 fois sans que personne ne le voie.

1. La session C tire **3 communes** parmi les traitées : la plus grosse par pool, une moyenne, une petite (tirage documenté).
2. Pour chacune, elle **ré-extrait entièrement le YAML depuis le règlement, SANS ouvrir le YAML produit en phase 1** ni les rapports des sessions A/B. Clone `labuse-plu-c`, branche `feat/plu-nuit-verif`. Mêmes invariants, même schéma.
3. **Diff structuré** : valeur par valeur, zone par zone, entre l'extraction et la contre-extraction.
4. Verdict par commune :
   - **Concordance totale** (ou divergences purement rédactionnelles) → la méthode est stable, présomption de qualité sur tout le lot de la session concernée.
   - **Divergence sur une valeur chiffrée ou une destination** → chaque cas est documenté avec les deux lectures et le passage du règlement verbatim. **Aucune des deux versions n'est corrigée** : c'est Vic qui tranche au matin, sur pièces.
5. Rapport : `docs/mandats/PLU_NUIT_CONTREPREUVE.md` — communes tirées, diff complet, verdict, et si divergences : la liste des motifs récurrents (c'est le biais systématique qu'on cherche).

## 4 · INTERDIT ABSOLU — LA BASE APPLICATIVE

**Aucun accès, toute la nuit, pour les trois sessions.** Ni golden, ni API, ni échantillon, ni écart repli/calibré, ni requête de confort.

Raison technique établie : le boot de l'API pose un `ALTER TABLE parcels` en convoi de verrous, et `lock_timeout` est inopérant (`db.py` écrase `connect_args`). Deux sessions qui se disputent la base = nuit perdue. L'extraction n'a besoin de rien d'autre que les PDF et les manifestes.

**Toutes les mesures se font au matin** (phase 4), en une passe groupée séquentielle : golden 116/116 par branche · tiers 120/1031/3587/72980/353945 au bit près · échantillon 10 parcelles avant/après par commune · écart repli/calibré sur 400 parcelles par commune. Rien de tout cela n'est lancé cette nuit, même si « la base a l'air libre ».

## 5 · RAPPORTS DE NUIT

Chaque session d'extraction écrit `docs/mandats/PLU_NUIT_RAPPORT_<A|B>.md` :

- **Tableau par commune** : traitée/sautée + motif · zones calibrées / non calibrées (motifs) · % du pool servi couvert par le calibrage · temps réel (horodatages de commits) · md5 gravé · alertes (COS consigné, zones habitat-interdit posées).
- **Frictions de schéma v1** : le schéma a-t-il tenu partout ? Chaque contorsion évitée est citée.
- **Nouveaux pièges** rencontrés → formulés pour le §9 du mandat-cadre.
- **Reste à faire au matin**, commune par commune.
- Synthèse : communes traitées / sautées / temps cumulé / heure de fin.

La session C écrit son rapport de contre-preuve (§3.5).

## 6 · CE QUE VIC TROUVE AU RÉVEIL

1. `PLU_NUIT_PREVOL.md` — l'état des lieux et les communes écartées d'entrée.
2. Jusqu'à 17 YAML commités sur 2 branches, chaque valeur sourcée et re-vérifiée par script.
3. `PLU_NUIT_RAPPORT_A.md` + `_B.md` — le détail par commune.
4. `PLU_NUIT_CONTREPREUVE.md` — le verdict de stabilité de la méthode, et les éventuelles divergences à trancher **sur pièces, passages cités**.
5. La liste exacte des arbitrages qui l'attendent : communes sautées, divergences de contre-preuve, zones en suspens.

Puis, dans l'ordre : arbitrages → phase 4 (mesures groupées) → merges `--no-ff` par Vic → mise à jour du §9 du mandat-cadre.

## 7 · INTERDITS

Merger · deviner une valeur · valeur sans article + page vérifiés par script · toucher à la base ou lancer l'API · traiter une commune de l'autre lot · ouvrir les YAML de phase 1 pendant la contre-extraction · corriger une divergence de contre-preuve sans Vic · relâcher un invariant pour finir plus vite · réveiller Vic.
