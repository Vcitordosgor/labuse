# MANDAT « REPLI NON OPTIMISTE » — SPEC v2 (refondée sur le correctif du gate)

> Statut : **SPEC SEULEMENT** — rien n'est implémenté sans le GO de Vic sur les mesures.
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

La liste O12 redevient ce qu'elle doit être : un **indice de pré-identification pour le
calibrage** (où chercher des Art. 1/2 restrictifs), **jamais une source de vérité pour
le moteur**. La vérité moteur = les statuts `habitat` SOURCES des YAML calibrés
(21 communes, statuts vérifiés articles + pages, contre-preuve à l'appui).

## 3. Vérification du CHEMIN COMPLET (préalable bloquant n°1)

Leçon de la nuit : vérifier une fonction ne suffit pas (engine.py avait le bon ordre,
resolve_zone le court-circuitait). Le correctif étant au point d'étranglement, il soigne
d'un coup TOUS les consommateurs — mais chacun doit être audité pour ses hypothèses :

| Consommateur de resolve_zone | Site | À vérifier |
|---|---|---|
| Moteur faisabilité | faisabilite/engine.py (estimate_capacity) | ordre habitat→hauteurs OK (vérifié) ; messages/steps si hauteur a_verifier |
| Cascade phase 1 | cascade/layers/phase1.py:279+287 | le score utilise-t-il hauteur/emprise du générique ? une parcelle habitat-interdit doit-elle scorer « positive » via positive_prefixes [U, AU] (cascade_rules.yaml:74) ? |
| Chaîne du résiduel | cascade/layers/etage0_ext.py:153 (residuel_socle, barème -25…+30) + scoring/opportunity.py:56 | la SDP résiduelle d'une zone interdite doit passer au barème « hors cible » et non au socle générique ; effet sur les 32 448 verdicts SP d'étalonnage |
| Traducteur API | api/traducteur.py:128 | règles chiffrées affichées : doit montrer l'interdiction, pas le générique |
| Lettre zonage | api/lettre_zonage.py:76 | libellé « calibree=False → repli honnête » à revoir pour interdit-sans-hauteur |
| Modules API (filtre hauteur) | api/modules.py:1001+ (hcache) | cache (zone, commune)→hauteur : gérer a_verifier post-correctif |
| Copilote | copilote/moteurs.py:178 | idem traducteur |
| Fiche règlement | plu_reglement.py:53 | idem |
| DB prospect | faisabilite/db.py (hauteur_mode=prospect) | non concerné (exception déjà dans _has_usable_height) — à confirmer |

Sortie attendue : un tableau « couche → comportement avant/après → OK/à adapter »,
AUCUNE autre couche ne devant écraser l'interdiction plus haut ou plus bas.

## 4. Mesure d'impact (préalable bloquant n°2 — base requise, fenêtre phase 4+)

1. **Parcelles changeant de verdict** : compte exact, par commune, par zone, et par SENS
   (attendu : uniquement générique→0 ; tout changement dans l'autre sens = bug).
2. **Tiers servis** : répartition des parcelles impactées par tiers de score — question
   BLOQUANTE, au même titre que pour les hypothèses du bilan (MANDAT_HYPOTHESES_BILAN) :
   si le correctif vide un tiers commercialement servi, Vic arbitre avant merge.
3. **residuel_socle et chaîne du résiduel** : delta de barème sur les parcelles
   impactées ; re-étalonnage éventuel des bornes (extraites des verdicts SP).
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
c) Hors périmètre : Saint-Paul (mode strict, gate inactif) ; zones hauteur_mode=prospect.

## 6. Séquencement

1. Audit chemin complet (§3) — sans base, faisable immédiatement sur GO.
2. Mesures (§4) — nécessitent la base : à caler après/avec la phase 4 (Vic).
3. GO Vic sur les mesures → implémentation (la ligne + adaptations §3) → golden.
4. Bascule des 14 zones du §5.a (3 communes) → re-golden → fin du repli optimiste
   par interdiction perdue.

— Rien de ce mandat n'est implémenté à ce jour. La seule action déjà faite est du
DONNÉES : statuts habitat sourcés sur 21 communes (série nuit + contre-preuve).
