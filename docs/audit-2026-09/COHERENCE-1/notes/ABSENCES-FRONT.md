# COHERENCE-1 lot A/D — vocabulaire d'absence CÔTÉ FRONT (scan statique, 28/09/2026)

Complète `ABSENCES.csv` (les 178 phrases déclarées dans `declarations/*.yaml`) par ce que
le code front rend réellement. Helpers centraux : `frontend/src/lib/format.ts` — `fmtInt/
fmtDec/fmtEur/fmtM2/fmtEurCompact/fmtPct/fmtDate*` rendent tous `'—'` sur null ;
`fmtDateSirene/anneeSirene` rendent `'n.c.'` (sentinelle 1900). Python exports :
`exports/blocs/financier.py:93` `_NON_CHIFFRE` = « non chiffré » (6 usages).

## SUSPECTS « zéro affiché à la place d'une absence » (matière lot D, à vérifier en base)

| Fichier:ligne | Rendu si source nulle | Notion |
|---|---|---|
| `frontend/src/components/MonSecteur.tsx:71` | `fmtInt(sb.median_eur_m2 ?? 0)+' €/m²'` → **« 0 €/m² »** | médiane bâti secteur |
| `frontend/src/components/fiche/ProfilAltimetrique.tsx:70-75` | `?? 0` ×5 → **« 0 m » / « 0 % »** | distance, dénivelé, pente du profil |
| `frontend/src/components/admin/Licences.tsx:27` | `(v ?? 0).toFixed(2)` → **« 0,00 € »** | montants licences (admin) |
| `frontend/src/components/panel/ResultsSection.tsx:107-108` | `(p.cluster ?? 0) - 1` → **« -1/0 autre(s) »** | co-titulaires du propriétaire |
| `frontend/src/components/admin/AdminView.tsx:230,234,237,268,297,420,426` | `?? 0` → **« 0 »** | KPIs dashboard admin (CA, IA, dépôts…) |
| `src/labuse/exports/financier_bilan.py:108-124,172,201` | `or 0.0` sur surfaces/parts/coûts | bilan financier (hypothèses → 0 silencieux) |
| `src/labuse/exports/miroir.py:293,329-343` | `or 0` | ménages, compteurs miroir |

Incohérence d'idiome relevée (lot H) : compteurs nuls → « 0 » dans AdminView mais « — »
dans Radar.tsx:321-324 ; « n.c. » réservé à SIRENE, « — » partout ailleurs, « non chiffré »
dans le PDF financier — trois idiomes pour la même absence.

(Scan : 207 fichiers front + exports/flash Python ; libellés « — » en dur : ~35 sites JSX
listés dans le transcript de l'agent, repris au besoin par le banc lot H.)
