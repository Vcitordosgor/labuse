# MANDAT-CADRE PLU (instance Saint-Pierre) — DÉPÔT DE RECONSTRUCTION

> ⚠ **CE FICHIER N'EST PAS L'ORIGINAL.** Le mandat-cadre était référencé par tous les
> mandats PLU (« MANDAT_CADRE_PLU_instance_saint_pierre.md ») mais n'a jamais été commité :
> introuvable dans le dépôt, dans l'historique git, sur le disque de la machine de nuit et
> dans ~/Downloads (recherches exhaustives, session B, 28/07/2026). Il est déposé ici pour
> que les leçons du §9 aient enfin un support versionné — **Vic : restaurer les §§1-8
> depuis ta copie et remplacer ce squelette.**
>
> §§1-8 (SQUELETTE — contenu original à restaurer) : périmètre et instance de référence
> Saint-Pierre · invariants de qualité (repris opérationnellement dans
> `MANDAT_PLU_SERIE_NUIT.md` §0, invariants 1-9) · schéma YAML v1 et conventions de
> gravure · procédure de calibrage et portes de sortie · golden et mesures.

---

## §9 — LEÇONS ACCUMULÉES (reconstitution sourcée, puis ajouts de la série de nuit)

### Acquis pilote Saint-Pierre + éclaireur Le Tampon (sources : PLU_SAINT_PIERRE_RAPPORT.md, PLU_LE_TAMPON_RAPPORT.md)

1. **Destinations d'abord** : lire l'Art. 1/2 (ou le tableau des destinations) de toutes
   les zones AVANT les chiffres — `habitat: interdit` prime sur tout calibrage de hauteur ;
   un pattern-match (« gardiennage ») peut conclure l'inverse du texte.
2. **Préambules porteurs de droit** : les caractères de zone se lisent systématiquement
   (secteurs, indices, renvois s'y cachent).
3. **Renvois explicites pour les codes à préfixe chiffré** (1AUx/2AUx) : le renvoi
   mécanique du moteur ne les couvre pas → entrées explicites.
4. **Offset de pagination PDF ↔ imprimée** : à établir et documenter AVANT de citer
   (3 pages fausses au Tampon avant le script de re-vérification) ; re-vérification
   par script de CHAQUE (article, page) avant commit.
5. **`null` sourcé** ≠ valeur manquante : « Non réglementé » se grave null AVEC citation.
6. **Gels conditionnels via `zones_au_st`** (friction F2) : capacité zéro exacte,
   étiquette « secteur de transition » inexacte — assumée, documentée.
7. **Base partagée** : aucun moyen sans modification de code de booter l'API sans risque
   de convoi de verrous pendant une ingestion (PGOPTIONS écrasé par db.py) ; golden et
   mesures en fenêtre calme uniquement.
8. **COS post-ALUR** : vérifier la date d'approbation ; citer avec la date, ne JAMAIS
   appliquer.

### Ajouts série de nuit — session B, 9 communes, 27-28/07/2026 (source : PLU_NUIT_RAPPORT_B.md)

9. **PDF composite à double pagination imprimée** (Saint-Benoît) : le vote d'offset
   majoritaire peut désigner le mauvais bloc (cahier d'annexes auto-paginé). Identifier CE
   QUE numérote le bloc gagnant ; en double référentiel → `pagination_citee: "pdf"`,
   jamais de mélange.
10. **Numéros de page imprimés en EN-TÊTE** (Les Avirons, Cilaos, Bras-Panon,
    Trois-Bassins) : un vote de pied de page rend 0 sur un document proprement paginé.
11. **Couches texte fantômes** dans les notices de modification concaténées
    (Plaine-des-Palmistes) : contenu normatif lisible uniquement en rendu IMAGE.
12. **Le pré-vol pypdf peut mentir dans les deux sens** : lettres doublées fantômes
    (Cilaos, PyMuPDF propre) ET COS invisible à la regex naïve (les textes écrivent
    « coefficient d'occupation DU SOL », apostrophe typographique).
13. **Chapitre AU à destinations propres + renvoi d'indice** (Trois-Bassins 1AUe) : les
    Art. 1/2 du chapitre peuvent CONTREDIRE la zone U d'indice → vérifier renvoi vs
    contenu autonome avant de propager un habitat-interdit ; en contradiction :
    non-calibrage, arbitrage sur pièces.
14. **Renvois de modification asymétriques** (Trois-Bassins AUa→Uaa) : chercher les
    renvois article par article, pas seulement en tête de chapitre.
15. **Article hauteur qui ne fixe que le secteur** (Le Port Ue 8 → Uem seul) : vérifier le
    PDF brut avant de conclure à une perte d'extraction ; zone support sans hauteur →
    capacité zéro exacte via st-liste, jamais d'entrée sans hauteur (retombée générique
    9 m avec habitat non contraint).
16. **STECAL à caducité légale datée** (Saint-Benoît, ELAN 31/12/2021 + condition
    préfet/SCOT invérifiable) : seul le non-calibrage motivé est honnête.
17. **Sommaire périmé** après modifications successives (Petite-Île) : citer le corps
    vérifié, jamais le sommaire.
18. **Convention de citation des sous-alinéas** : « Art. X 2.2 (al. 7) » (le vérificateur
    ne résout pas les jetons à 3 niveaux) ; articles à cheval sur 2 pages → citer la plage.
19. **Hauteurs par SECTEURS GRAPHIQUES transverses aux zones** (Saint-Benoît, 4-15 m) :
    règle NON PORTABLE par le schéma v1 — arbitrage Vic 28/07/2026 : ne pas graver une
    tranche (facteur 4 de sous-estimation = faux négatifs en série), zones non calibrées
    motif « hauteur définie par secteur graphique, non portable par le schéma v1 ».
    **Friction de schéma majeure — candidat v2 : hauteur par calque graphique.**
20. **Doctrines harmonisées A/B/C (arbitrage Vic, 28/07/2026)** :
    - % « espace vert et perméable » sans sous-minimum de pleine terre → VALEUR GRAVÉE
      dans `pleine_terre_pct`, libellé verbatim conservé en `_src` (fini le null+note) ;
      ne s'applique QU'AUX règles qui bornent réellement l'emprise constructible —
      « espace vert paysager » où les stationnements sont comptables, ou « libres et
      paysagés » sans exigence de perméabilité, ne bornent pas le bâti et restent
      null sourcé (raisonnement Cilaos, validé par Vic).
    - Retraits en H/2 → valeur gravée = **max(H/2 à la hauteur maximale gravée, plancher
      du texte)**, fond du calcul en note.
21. **Signal de pré-vol ≠ preuve** (Cilaos NtoPOS→Nto) : un rattachement de famille
    proposé par le pré-vol reste une hypothèse — le corps du texte prime, sinon non
    calibrée.
22. **Rattachement d'un secteur muet à sa zone support** : uniquement si la règle
    générale « la règle de la zone s'applique aux secteurs sauf disposition particulière »
    est ÉCRITE dans le règlement (citée dans l'entrée) — sinon non calibrée.
    **Précision d'arbitrage (Vic, 28/07/2026)** : une clause de règle générale écrite
    fonde un rattachement, une déduction par élimination non. La clause ne couvre que
    les secteurs d'une ZONE : Cilaos Ub1 (secteur cartographique d'une zone Ub sans
    secteur déclaré) → rattachement VALIDÉ ; Saint-Louis 1AUb1/1AUb2/2AUb1/2AUb2
    (zones AU dont l'indice « b1 »/« b2 » ne correspond à aucune zone urbaine — le
    passage b1→b est une élimination non écrite, même si la commune possède aussi une
    clause générale des secteurs, p.4) → rattachement REFUSÉ, zones non calibrées,
    motif « rattachement non fondé sur une clause du règlement, indice cartographique
    sans disposition écrite ».
23. **Schéma v1, manques récurrents constatés en série** (2e signalement après le
    Tampon) : `habitat: interdit` devrait primer sur le gate hauteur dans `resolve_zone`,
    et un vrai type « gel » devrait remplacer l'étiquette « secteur de transition »
    (utilisée pour capacité zéro exacte dans 6 communes sur 9 du lot B).

### À fusionner (sessions A et C)

Les leçons propres au lot A (PLU_NUIT_RAPPORT_A.md) et au verdict de contre-preuve
(PLU_NUIT_CONTREPREUVE.md) sont à verser ici par leurs sessions ou par Vic au moment
de la mise à jour post-nuit du §9 prévue par MANDAT_PLU_SERIE_NUIT.md §6.
