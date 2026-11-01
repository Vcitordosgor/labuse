# Constats CHEF — vérification écran (Playwright) + réglementaire

Env : API 9360 (PDF-capable, code==main edffc61c4), front 6560 (vite, proxy→9360), base `labuse` run 17 q_v20.
Parcours réel reproduit (recherche omnibox → fiche ; sélecteur commune → fiche commune).

## Captures écran réalisées
- `captures_ecran/fiche_parcelle_97415000AB0001.txt` — fiche parcelle Saint-Paul (en-tête + sections LE BIEN/DROIT/MARCHÉ/PROJET).
- `captures_ecran/outils_menu.txt` — menu Outils (16 tuiles + descriptions).
- `captures_ecran/fiche_commune_saintpaul.txt` — fiche commune Saint-Paul complète.

## Constats de libellé / écart (écran réel)

### C-ECRAN-1 — Fiche parcelle : deux surfaces, un même écran (mineur)
En-tête « SURFACE : 11,62 ha » (= contenance cadastre 116 225 m²), mais le cartouche bas
« PARCELLE AB 1 — Saint-Paul » affiche « 115 449 m² » (= surface_m2 dessin géométrique).
Écart 776 m² (0,67 %). surface_source='cadastre' → l'en-tête défère bien à la contenance officielle ;
le cartouche carte montre la géométrie dessinée. Deux chiffres de surface coexistent à l'écran
sans libellé distinguant « cadastre » vs « dessin ». À confirmer côté FICHES (FP surface).

### C-ECRAN-2 — Sélecteur « Fiche commune » : code POSTAL, pas INSEE (mineur, confirme NU-1-B)
Le menu commune affiche le code POSTAL (Saint-Denis 97400, Saint-Paul 97460, Le Tampon 97430…).
Saint-Leu affiché « 97424 » = Piton-Saint-Leu ; le CP de Saint-Leu bourg est 97436. Écho du
mineur NU-1-B (CP Saint-Leu 97424≠97436). Dans la fiche commune elle-même l'Identité affiche
bien l'INSEE « 97415 » pour Saint-Paul (correct). Donc deux numéros selon l'endroit.

## Confrontation réglementaire / fiscale

### R-TAXE-1 — Taxe d'aménagement, forfait 2026 : JUSTE (confronté au texte officiel)
Config servie : valeur_forfaitaire_m2 hors_idf = **892 €**, idf = **1011 €** (annee 2026).
Confronté à service-public.gouv.fr A15416 (WebFetch 01/11/2026) : « 892 € hors IdF, 1 011 € IdF
pour 2026 » — EXACT. Part départementale 2,5 % confirmée 974, part communale plafond 5 %,
abattement 50 % / plafond 100 m² résidence principale, forfaits piscine 251 €/m², exonération <5 m².
(Formule complète écran==API==barème : voir groupe ASSEMB_TAXE.)

### R-TAXE-2 — Exonération petites surfaces : borne STRICTE `< 5` au lieu de `≤ 5` (mineur, ÉCART confirmé)
`taxe_amenagement.py:~256` : `if surf > 0 and seuil_exo and surf < seuil_exo` (seuil_exo=5).
À 5 m² PILE, l'app soumet à la part surface (assiette non nulle) ; à 4,99 m² elle exonère.
Or CGI art. 1635 quater D, 10° = construction « **inférieure ou égale à 5 m²** » (confirmé
BOFiP BOI-IF-TU-10-20-30-160 + Légifrance). Donc 5,00 m² doit être exonéré. Écart de borne
réglementaire, cas limite (surface taxable = 5,00 m² exactement) ; corroboré code + texte officiel.
Remonté par le sous-auditeur ASSEMB_TAXE, revérifié par le chef.
