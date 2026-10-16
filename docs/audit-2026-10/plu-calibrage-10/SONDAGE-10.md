# SONDAGE-10 — 10 règles de distance entre constructions (valeur · citation · page)

Dix règles tirées du corpus règlementaire (`plu_reglement_extrait`, texte opposable servi par le GPU),
étalées sur les communes et sur **toutes les formes** (fixe, relative, conditionnelle, silence, forme
hors schéma). Pour chacune : la valeur lue, le verbatim et la page PDF. Sert de contrôle ponctuel de la
calibration (LOT B) et de la lecture (LOT A).

---

**1. Bras-Panon — zone UA — fixe 6 m** *(art. UA 8, p. 18)* — calibrée
> « Deux constructions principales non contiguës implantées sur une même unité foncière, doivent respecter une distance entre elles d'au moins **6 mètres**. »

**2. Bras-Panon — zone UE — fixe 8 m** *(art. UE 8, p. 70)* — calibrée
> « 8.2 - Règle générale Deux constructions principales non contiguës implantées sur une même unité foncière, doivent respecter une distance entre elles d'au moins **8 mètres**. »

**3. Cilaos — zone Ua — fixe 4 m** *(art. Ua 8, p. 24)* — calibrée
> « 8.2 - Règle générale L'implantation de plusieurs constructions sur une même unité foncière est autorisée à condition que la distance séparant deux bâtiments soit au moins égale à **4 mètres**. »

**4. La Plaine-des-Palmistes — zone Uc — fixe 7 m** *(art. Uc 8, p. 41)* — calibrée
> « 8.2 - Règle générale Deux constructions principales non contigües, doivent être distantes d'au moins **7,00 mètres**. »

**5. Le Port — zone Ua — fixe 3 m** *(art. Ua 6, p. 25)* — calibrée
> « Deux constructions implantées sur une même propriété doivent être à une distance l'une de l'autre au moins égale à **3 mètres**. »

**6. Saint-Denis — zone Ui — relative (cumulée) : 0,5·(H+h), min 4 m** *(art. Ui.8, p. 55)* — calibrée *(témoin)*
> « Deux bâtiments non contigus, implantés sur une même propriété, devront respecter entre eux, une distance L supérieure ou égale à la **moyenne des hauteurs** des façades en vis-à-vis et/ou des niveaux droits en vis-à-vis avec un **minimum de 4m** : 4m ≤ L ≥ H+h /2 … »

**7. Les Trois-Bassins — zone Ua — relative (plus haut) : D = H/2, min 4 m** *(art. Ua 8, p. 16)* — calibrée
> « La distance (D) entre deux constructions principales non contiguës doit être au moins égale à **D=H/2** (H étant la hauteur à l'égout du toit ou au sommet de l'acrotère) **du bâtiment le plus haut**, sans être inférieure à **4,00 mètres**. »

**8. Sainte-Rose — zone UA — conditionnelle (ouvertures) : (H+h)/2, min 6 m avec baie / 3 m sans** *(art. UA 8, p. 14)* — calibrée
> « La distance en tout point entre deux constructions non contigües sur une même unité foncière doit être au moins égale à la moitié de la hauteur cumulée des deux constructions … (L ≥ (H+h) /2) avec un minimum de : - **6 mètres dès lors qu'au moins une façade comporte une baie**, - **3 mètres dès lors qu'aucune des façades concernées ne comporte de baie** ou si au moins une des constructions est une annexe. »

**9. Saint-Pierre — zone UA — silence prouvé (Non réglementée)** *(art. Ua3, pt 3/, p. 176)* — silence
> « 3/ Implantation des constructions les unes par rapport aux autres sur une même parcelle **Non règlementée**. »

**10. Le Tampon — zone Ua — FORME HORS SCHÉMA (seuil par nombre de logements) → STOP** *(art. Ua8, p. 17)* — non calibrée
> « L'implantation de plusieurs constructions sur une même unité foncière est autorisée à condition que la distance séparant deux bâtiments soit au moins égale à **3 mètres**. Dans le cas d'un bâtiment comportant **plus de cinq logements, ce seuil minimal est porté à 6 mètres, hors circulations extérieures de type coursive**. »

> Règle **présente et claire**, mais conditionnée au **nombre de logements** — forme non prévue au
> schéma (qui n'autorise que fixe / relative / conditionnelle-par-ouvertures / contiguïté). Conformément
> à la doctrine « autre forme = STOP », elle n'est **pas** servie en l'état. À noter : le règlement de
> Le Tampon confirme explicitement que les **coursives extérieures sont hors** du calcul — ce que fait
> désormais aussi le moteur pour la SDP (LOT D, art. R111-22).

---

*Contrôle croisé calibration :* les feuilles 1–8 sont servies `validee` et vérifiées par le lecteur
`regles.charger` (valeur, forme, article, page). La 9 est servie « non réglementé » (silence prouvé,
`absent: true`). La 10 est documentée comme STOP (hors schéma).
