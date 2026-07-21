# Nuit N8 (a) — Diagnostic SDP du PDF Flash *(diagnostic seul — AUCUN fix appliqué)*

## Où est le retour persona

- **Template Flash** `src/labuse/flash/templates/rapport.html.j2:139-143`, commentaire *« M6.1 item 6
  (sprint personas) : le libellé client — la « SDP résiduelle » est du jargon ; on dit ce que c'est »* →
  déjà relibellé **« Surface constructible restante (estimation) · {{ sdp_residuelle_m2 }} m² de plancher
  (indicatif) »**. La donnée vient de `parcel_residuel.sdp_residuelle_m2` (`flash/data.py:164-171`).
- **Audit M6** `reports/m6-audit/sections/1-5-outils.md:133-139` — le **toggle carte « Mutabilité »** colore
  un gradient sur `sdp_residuelle_m2` mais l'appelle « Mutabilité ».
- **Audit M6** `reports/m6-audit/sections/1-7-exports.md:80` — export vérifié : « SDP résiduelle 183 m²
  (= fiche app) », cohérent app↔PDF (ce point-là est sain).

## Le problème EXACT (résiduel après le fix de jargon)

1. **PDF Flash — « m² de plancher » lu comme surface utile.** La valeur affichée est la **surface de
   plancher (SDP)**, qui inclut murs/circulations. Or le bilan interne pose `SDP = habitable ×
   coef_plancher_habitable` avec **coef = 1,15** (`faisabilite/engine.py`). Donc **~13 % des m² affichés
   ne sont pas habitables/vendables** — un client (persona « jamais vu l'app ») lit « surface constructible
   restante » comme de la surface exploitable et **surestime d'environ un huitième**. Le mot « plancher »
   est exact mais son implication (≠ habitable) n'est jamais explicitée.

2. **Toggle carte « Mutabilité » = même métrique SDP, libellé qui MENT** (`1-5-outils.md`). Le gradient
   colore la **capacité constructible** (SDP) mais le bouton dit « Mutabilité ». Or depuis M5 la doctrine
   produit martèle **capacité (C) ≠ probabilité de muter (P)** (« C fort, P faible → peu de chances de
   muter »). Le bouton contredit frontalement le lexique de toute l'app. *(Adjacent au PDF, même donnée.)*

3. **Pas de cadre de référence.** « restante » implique une soustraction (résiduel vs un potentiel PLU
   total, ou vs le déjà-bâti) que le PDF ne montre pas → le client ne sait pas « restante par rapport à
   quoi ». Et depuis la nuit N1 il existe une **marge estimée (€)** (`score_e`) qui rendrait ce m²
   actionnable, non reliée.

## Fix PROPOSÉ (à NE PAS appliquer ici — décision Vic)

- **PDF Flash (minimal, wording only, `rapport.html.j2`)** : sous la valeur, une ligne
  *« surface de plancher au sens PLU (hors murs/circulations) — la surface habitable/vendable est ~15 %
  inférieure »*. Aucune logique touchée, juste le caveat qui manque. Option : afficher aussi l'habitable
  dérivée (`SDP / 1,15`) entre parenthèses.
- **Toggle carte (`1-word`, hors PDF)** : renommer **« Capacité (SDP) »** (la légende dit déjà « SDP
  résiduelle » — seul le mot du toggle ment). Fix déjà proposé en M6 (`1-5-outils.md:139`).
- **Cadre de référence (plus tard)** : afficher « sur un potentiel PLU de X m² » quand la capacité totale
  est connue, et relier à la **marge estimée** (`score_e`, N1) pour passer du m² au « ce que ça peut rapporter ».

**Périmètre respecté** : diagnostic uniquement, aucun code modifié, aucune donnée touchée.
