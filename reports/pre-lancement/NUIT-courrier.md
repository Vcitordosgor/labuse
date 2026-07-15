# NUIT — Courrier postal (point 43) · `feat/nuit-courrier`

**NON mergée.** Front + backend. Zéro touche scoring. Privacy respectée.

## Lot 0 — Constat
Deux surfaces existaient : `/courrier/*` (envoi postal réel, provider **stub** Merci Facteur → bouton
masqué) et `/modules/courriers` (M09) qui générait un **lot** de textes-gabarits (motif → texte rempli
avec les faits parcelle). Pas de parcours guidé.

## Fait
M09 devient un **parcours GUIDÉ 4 étapes** (maquette) : **Parcelle (IDU) → Motif → Rédaction → Demande**.
- **Étape 3 (rédaction)** : brouillon **groundé** (faits réels de la parcelle via le gabarit serveur —
  réf. cadastrale, commune, surface, motif) et **entièrement éditable**.
- **Étape 4 (demande)** : aperçu + « Demander l'envoi » → nouvel endpoint **`POST /courrier/demande`**
  qui **enregistre une DEMANDE** (table `courrier_demandes`) et répond « **notre équipe prépare l'envoi
  et reviendra vers vous** ». **Ce n'est pas un envoi automatique.**
- **Privacy (ligne rouge)** : le courrier est **adressé génériquement** (« Madame, Monsieur ») — **aucune
  identité de propriétaire particulier** n'est injectée ni stockée ; l'identification passe par le workflow
  SPF/CERFA. La demande stocke l'IDU + le texte, jamais un nom de particulier.

## Preuves (`reports/pre-lancement/captures/`)
`nuit-courrier-1-parcelle.png` · `-2-motif.png` · `-3-redaction.png` (brouillon groundé éditable) ·
`-4-apercu.png` · `-5-demande.png` (confirmation « notre équipe reviendra »). Smoke test API : `POST
/courrier/demande` → `{ok:true, message:"Demande enregistrée…"}`.

## Tests / garanties
`tsc` vert, build OK, endpoint testé live. Zéro fichier scoring/cascade/run. `git diff` = `api/courrier.py`
(+endpoint demande), `ModulePanel.tsx` (M09 wizard), `lib/api.ts` (client), QA + captures.

## Merge
```
git -C /Users/openclaw/Desktop/labuse checkout main && git merge --no-ff feat/nuit-courrier
```
**État : ✅ prêt à merger** (revue à l'œil des 5 captures).
