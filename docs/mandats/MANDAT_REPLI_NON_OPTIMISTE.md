# MANDAT « REPLI NON OPTIMISTE » — SPEC v2 (refondée sur le correctif du gate)

> Statut : **SPEC SEULEMENT** — rien n'est implémenté sans le GO de Vic sur les mesures.
> **NATURE (arbitrage Vic 28/07) : ce n'est PAS un correctif de code — c'est un correctif
> de code PLUS une migration de données** (recalcul scopé de `parcel_residuel`, sans
> lequel la SDP optimiste périmée continue d'alimenter residuel_socle et les modules
> API). **CONDITION D'ARRÊT PRINCIPALE : si parcel_residuel bouge, residuel_socle bouge,
> donc le scoring servi bouge — si les tiers changent, RIEN ne merge sans re-run du
> champion, arène et arbitrage Vic.**
>
> **CONTRAINTE DE SÉQUENCEMENT INTER-MANDATS (Vic, 28/07) — trois correctifs en attente
> touchent la MÊME chaîne (parcel_residuel → residuel_socle → scoring servi → tiers) :
> (1) hypothèses du bilan (×2,37 charge supportable, session en cours), (2) phase 4 PLU
> (écart repli/calibré, 21 communes), (3) ce mandat. RÈGLE : un seul correctif appliqué
> à la fois, chacun mesuré sur une base stable — sinon les deltas se mélangent et le
> rollback devient impossible. ORDRE ACTÉ : hypothèses du bilan (mesure → arbitrage →
> application → re-golden → tiers) PUIS phase 4 sur base stabilisée PUIS ce mandat en
> DERNIER. Les mesures de ce mandat (§4, §2bis, population e) NE VALENT QUE sur une base
> où les hypothèses du bilan sont déjà réalignées — prises avant, elles porteraient sur
> des chiffres appelés à changer.**
> Rédigée le 28/07/2026 (session A/C, nuit PLU) sur décision Vic. Remplace l'approche
> initiale par liste de codes de zones, **invalidée** par la leçon « le préfixe d'un
> libellé ne prouve rien » (UAa résidentiel habitat-INTERDIT, UEm économique
> habitat-ADMIS — La Possession, §9 rapport A).

## 1. Le bug produit (mécanisme du repli optimiste, découvert de l'intérieur)

`resolve_zone` (src/labuse/faisabilite/plu_rules.py:149-151), mode `progressif` :

```python
if code in rules:
    r = rules[code]
    if strict or _has_usable_height(r):
        return r
    return _zone_generique(code)      # <-- LE GATE
```

Une zone calibrée **sans hauteur chiffrée** (he_m ET hf_m non numériques) est remplacée
par l'estimation générique (hé 9 m ≈ R+2, `calibree=False`). **Tout le contenu calibré
est perdu, dont `habitat: interdit`** — le test `engine.py:157` n'est jamais atteint.
Conséquence produit : une zone où le logement est interdit par le règlement est servie
en R+2 générique constructible. Faux positif maximal — le produit annonce des logements
là où la loi les interdit. Démontré PAR LA MESURE par la session B (capacité fictive
dans le cimetière UFcim, Petite-Île) après un reclassement erroné de la session C,
reverté à raison.

## 2. Mécanisme central du mandat (le correctif remplace la liste de codes)

**Dans `resolve_zone`, retourner l'entrée calibrée quand `habitat == "interdit"`, même
sans hauteur exploitable** (avant le gate). Le moteur rend alors une capacité 0 EXACTE
via engine.py:157 (le test habitat précède le calcul de hauteur), sourcée article à
l'appui. Esquisse (à valider, PAS implémentée) :

```python
if strict or r.habitat == "interdit" or _has_usable_height(r):
    return r
```

**Contrat de référence (consommateur modèle — Copilote, moteurs.py:177-190)** — la
formulation exacte que toute couche consommant ZoneRules doit honorer :

```python
if r is None or not r.constructible_neuf or r.habitat == "interdit":
    continue   # le moteur conclura non-constructible : on laisse la faisabilité le dire
```

La liste O12 redevient ce qu'elle doit être : un **indice de pré-identification pour le
calibrage** (où chercher des Art. 1/2 restrictifs), **jamais une source de vérité pour
le moteur**. La vérité moteur = les statuts `habitat` SOURCES des YAML calibrés
(21 communes, statuts vérifiés articles + pages, contre-preuve à l'appui).

## 2bis. CASCADE `positive_prefixes` — section À PART ENTIÈRE (décision Vic, 28/07)

**Périmètre et risque distincts du gate** : le gate corrige la faisabilité ; ceci touche
le SCORING SERVI, donc potentiellement les tiers. Décision de principe (Vic) : **une
parcelle où le logement est interdit ne doit pas scorer positive** — le score sert à
repérer du foncier à bâtir.

État réel du code (audit exécuté 28/07, sans base) :
- `cascade_rules.yaml:74` : `positive_prefixes: [U, AU]` — classification positive par
  PRÉFIXE (l'inférence invalidée par la leçon 15 du §9).
- MAIS un garde-fou existe : **M6 2b (A-03)**, `phase1.py:276-292` — hard_exclude
  « exclue » si recouvrement ≥ seuil par une zone `r.calibree and r.habitat=="interdit"`
  (soft_flag FORT entre plancher et seuil). Le préfixe ne décide donc PAS seul… quand la
  zone est calibrée AVEC hauteur.
- **Angle mort n°1 — le gate** : zone interdit sans hauteur → générique
  (`calibree=False`, habitat perdu) → M6 2b ne la voit pas → positive par préfixe.
  Le correctif du gate RÉPARE AUSSI M6 2b automatiquement (même point d'étranglement).
- **Angle mort n°2 — les gels** : `constructible_neuf` n'est lu NULLE PART dans
  cascade/ ni scoring/ (grep 0 occurrence). Une zone gelée (2AU, AUst, et les 14
  interdit-gelées de §5.a) garde sa classification positive de préfixe ; seule la
  chaîne residuel_socle peut la pénaliser indirectement (si parcel_residuel est à 0).
- **Angle mort n°3 — le générique pur** : zones U/AU de communes/zones non calibrées :
  positive par préfixe, par construction (repli assumé, calibree=False).

**Mesure AVANT tout changement (statut BLOQUANT, même rang que les tiers)** :
1. Parcelles classées positives par la cascade dont la zone porte `habitat: interdit`
   dans un YAML calibré — par commune, par tier. C'est LE chiffre (détail ou trou).
2. Même compte pour les zones en `zones_au_st` (dont les 14 interdit-gelées).
3. Si les tiers servis sont touchés : PAS de correctif sans re-run du champion, donc
   sans arène et sans arbitrage Vic.

## 3. Vérification du CHEMIN COMPLET (préalable bloquant n°1) — AUDIT EXÉCUTÉ 28/07

Leçon de la nuit : vérifier une fonction ne suffit pas (engine.py avait le bon ordre,
resolve_zone le court-circuitait). Le correctif étant au point d'étranglement, il soigne
d'un coup TOUS les consommateurs — mais chacun doit être audité pour ses hypothèses :

| Consommateur | Site | Aujourd'hui (gate actif) | Après correctif | Verdict |
|---|---|---|---|---|
| Moteur faisabilité | engine.py:157+229 | interdit-sans-hauteur → générique R+2 constructible | habitat testé avant hauteurs → 0 exact sourcé | **corrigé par la ligne** |
| Cascade M6 2b | phase1.py:276-292 | exige calibree+interdit → aveugle au gate ET aux gels | gate-population revue → hard_exclude auto ; GELS toujours invisibles (constructible_neuf jamais lu) | **corrigé pour interdit ; angle mort gels → §2bis mesure 2** |
| Chaîne du résiduel | etage0_ext.py:153 + opportunity.py:56 | lit la TABLE parcel_residuel (SDP précalculée) — pas resolve_zone en direct | **le correctif seul ne change RIEN ici : recalcul de parcel_residuel requis pour les parcelles impactées, sinon SDP optimiste périmée** | **à adapter (recalcul scoped)** |
| Traducteur API | traducteur.py:128 | affiche les règles du générique | affichera l'interdiction — rendu à adapter (mise en avant) | à adapter (affichage) |
| Lettre zonage | lettre_zonage.py:74-76 | calibree=False → « repli honnête » | zone interdit calibrée : lignes avec hauteurs a_verifier — wording à revoir | à adapter (wording) |
| Modules API filtre hauteur | modules.py:1001-1040 (hcache) | h = hauteur_max_m/hf/he | h peut devenir « a_verifier » (str) → comparaison str/float à GARDER ; joint aussi parcel_residuel (même point stale) | **à adapter (garde type + recalcul)** |
| Copilote | moteurs.py:177-190 | `if r is None or not r.constructible_neuf or r.habitat == "interdit": continue` | inchangé — **consommateur MODÈLE** (teste déjà les deux drapeaux) | OK |
| Fiche règlement | plu_reglement.py:53 | sources seulement si calibree | interdit calibrée → sources affichées | OK |
| DB prospect | faisabilite/db.py | exception déjà dans _has_usable_height | inchangé | OK (confirmé) |

Constat transverse : `constructible_neuf=False` (gels) n'est consommé QUE par le moteur
et le copilote — cascade, scoring, API l'ignorent. Toute correction future d'un gel doit
repasser par cette table.

## 4. Mesure d'impact (préalable bloquant n°2 — base requise, fenêtre phase 4+)

1. **Parcelles changeant de verdict** : compte exact, par commune, par zone, et par SENS
   (attendu : uniquement générique→0 ; tout changement dans l'autre sens = bug).
2. **Tiers servis** : répartition des parcelles impactées par tiers de score — question
   BLOQUANTE, au même titre que pour les hypothèses du bilan (MANDAT_HYPOTHESES_BILAN) :
   si le correctif vide un tiers commercialement servi, Vic arbitre avant merge.
3. **residuel_socle et chaîne du résiduel** : delta de barème sur les parcelles
   impactées ; re-étalonnage éventuel des bornes (extraites des verdicts SP).
   **Constat d'audit : residuel_socle lit la table précalculée `parcel_residuel`, pas
   resolve_zone — le correctif exige un RECALCUL scoped de parcel_residuel pour les
   parcelles impactées, à inclure dans la mesure (sinon la SDP optimiste périmée
   continue d'alimenter le barème et les modules API).**
4. **Golden 116 + tiers au bit près** avant/après ; échantillons nominatifs de parcelles
   basculées (fiche avant / fiche après) pour lecture Vic.

## 5. Population concernée (recensement au 28/07, 21 YAML)

a) **Interdiction PERDUE aujourd'hui si on les calibrait — actuellement gelées à raison
   (NE PAS TOUCHER avant merge du correctif)** : Saint-Benoît Ue/Up/Ut/AUe3/AUp1
   (5 zones ; données prêtes au commit c44b661) ; Le Port Ue/Up/Uppp/Uv + renvois
   1AUe/1AUv (6 zones ; extraction chapitres faite, art. 2/4/5/7/8/11 relevés) ;
   Petite-Île UF/UFcim/AUF (3 zones ; entrées C conservées « documentaires inertes » par
   B). **Bascule gel→zones calibrées PRÉPARÉE ici, exécutée seulement après merge du
   correctif + re-golden.**
b) **Servies au générique 9 m OPTIMISTE (habitat admis — même gate, effet plus discret)** :
   Saint-Denis Udo/Uavap/Uat/Uma/Upi/Upr/AUx (7 — verdict PARTIEL confirmé, lot de
   consolidation), La Possession UAv/AUAv/AUBm (3), Saint-Pierre AUdma (1). Le correctif
   ne les change PAS (elles restent au repli générique assumé calibree=False) — leur
   sortie du repli = calibrage des hauteurs (arbitrages îlots/AVAP), pools à chiffrer en
   phase 4.
c) Hors périmètre du correctif : Saint-Paul (mode strict, gate inactif) ; zones
   hauteur_mode=prospect.
d) **Générique pur (blind spot c) — population RÉSIDUELLE mesurée au 28/07** : avant la
   série PLU, 22 communes servies au générique par préfixe ; il en reste **3** —
   Saint-André (22 600 parcelles cadastre, dépubliée GPU, dossier d'appel prêt),
   Saint-Leu (22 959, idem), Saint-Philippe (4 162, RNU — pas de PLU à graver), soit
   **~49 721 parcelles cadastre** (source AUDIT_MULTICOMMUNE_24) contre ~450 000 pour
   l'île. Le calibrage a résorbé l'essentiel du blind spot ; le résiduel est l'argument
   chiffré pour aller chercher les deux communes dépubliées. Sous-ensemble U/AU exact à
   chiffrer en phase 4.
e) **ZONES GELÉES CLASSÉES POSITIVES (faux positif à part entière, rang du gate —
   arbitrage Vic 28/07)** : `constructible_neuf` n'étant lu nulle part dans cascade/ ni
   scoring/, une zone juridiquement FERMÉE à l'urbanisation (2AU/3AU, AU-st, et les 14
   interdit-gelées du §5.a) garde sa classification positive de préfixe — le « 227
   logements sur une AU02 fermée » de Saint-Pierre, transposé au scoring servi. Recensement
   au 28/07 : **92 libellés gelés sur 19 communes** (gels des 21 YAML, compte vérifié sur les têtes de branches au 28/07). **Mesure BLOQUANTE
   identique au §2bis : parcelles classées positives dans ces zones, par commune, par
   tier.** Correctif candidat : honorer le contrat de référence (constructible_neuf) dans
   la couche zonage de la cascade — même statut d'arrêt que les tiers.

## 6. Séquencement

1. ~~Audit chemin complet (§3)~~ — **FAIT le 28/07 (GO Vic), table remplie ci-dessus.**
2. Mesures (§4, §2bis, population e — TOUTES bloquantes) — nécessitent la base :
   phase 4 (Vic).
3. Arbitrage Vic sur les mesures. **Condition d'arrêt principale : tiers touchés →
   re-run champion + arène + arbitrage, sinon rien ne merge.**
4. Implémentation (la ligne + adaptations « à adapter » de la table §3) →
   **recalcul SCOPÉ de parcel_residuel** (migration de données, partie intégrante du
   correctif) → **mesure du delta sur les 32 448 verdicts d'étalonnage** →
   vérification des tiers → re-golden.
5. Bascule des 14 zones du §5.a (3 communes) → recalcul scopé → re-golden →
   fin du repli optimiste par interdiction perdue.

— Rien de ce mandat n'est implémenté à ce jour. La seule action déjà faite est du
DONNÉES : statuts habitat sourcés sur 21 communes (série nuit + contre-preuve).
