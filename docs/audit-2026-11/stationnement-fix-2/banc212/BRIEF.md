# Banc stationnement 212 — brief pour l'agent lecteur d'IMAGE

You are an INDEPENDENT checker. You read official French PLU règlement page IMAGES and compute the
required number of parking places ("places de stationnement") for standard housing programs.
This is an independent audit: do NOT read any source code, YAML, or pre-computed numbers. Base every
answer ONLY on what you read in the page images.

## Inputs (for commune INSEE)
- Rule list: `docs/audit-2026-11/stationnement-fix-2/banc212/specs/<INSEE>.json`
  (each rule = {rule_id, article, mode, zones, pages}).
- Page images: `docs/audit-2026-11/stationnement-fix-2/banc212/img/<INSEE>/page_<NNN>.png`
  (zero-padded 3 digits; e.g. page 17 → `page_017.png`). Read the pages listed for each rule
  (neighbours ±1 are rendered for tables spanning pages).

## Four programs (compute TOTAL places for each, per rule)
1. `maison_T4_120` — ONE individual house (maison individuelle), T4 = 4 pièces principales, 120 m²
   surface de plancher. Destination: logement individuel.
2. `collectif_20T3_1400` — 20 collective dwellings, each T3 = 3 pièces, 70 m² (total 1 400 m² SDP).
   Destination: logement collectif ordinaire (private, not aided).
3. `aide_20T3_1400` — SAME sizes as #2 (20 × T3 70 m²) but LOGEMENT AIDÉ / locatif social. If the
   règlement has a specific rule for logement social/aidé, apply it; otherwise apply the general rule
   and say so in notes.
4. `mixte_10x110_10x30` — 20 collective dwellings: 10 of 110 m² (T4, 4 pièces) + 10 of 30 m² (T1,
   1 pièce); total 1 400 m² SDP. Destination: collectif ordinaire.

## Conventions (factual, not code)
- Tn = n pièces principales. "chambres" (bedrooms) = n − 1 (the séjour counts as a pièce, not a
  chambre): T1 = 0 chambre, T3 = 2 chambres, T4 = 3 chambres.
- "surface de plancher" = the m² values above.
- Rounding: apply EXACTLY what the image says ("arrondi à l'entier supérieur/inférieur", "par tranche
  de… entamée/complète"). If silent, round UP (ceil) and note it.
- Separate the components: résidents, visiteurs, and places PUBLIQUES (réalisées sur le domaine public
  / la voirie) when the rule distinguishes them. Report each; "publiques" are NOT part of the private
  places to build on the plot.
- IGNORE any national ceiling (Code de l'urbanisme L151-35/36) — you cannot know the TCSP distance.
  Compute the PLU rule only, but NOTE if such a clause appears.
- If a rule offers concurrent formulas (e.g. "max of 1,25/logt OR 1 per 35 m²"), apply the one
  producing the MOST places unless the text says otherwise, and show both in formule.
- If habitation is forbidden in the zone, or the rule does not cover housing, set found=false and
  explain.

## Output — STRICT JSON only (no prose outside it)
{"insee":"<INSEE>","regles":[
  {"rule_id":"<INSEE>-R1","article":"...","found":true,
   "programs":{
     "maison_T4_120":{"total":N,"residents":N,"visiteurs":N,"publiques":N,"arrondi":"superieur|inferieur","formule":"the rule + the arithmetic"},
     "collectif_20T3_1400":{...},
     "aide_20T3_1400":{...},
     "mixte_10x110_10x30":{...}
   },
   "notes":"thresholds, clauses, ambiguities you saw"}
]}
Never invent a number. If unreadable, found=false. Your FINAL message MUST be the JSON, nothing else.
