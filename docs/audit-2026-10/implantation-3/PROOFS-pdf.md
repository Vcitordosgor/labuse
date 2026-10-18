# IMPLANTATION-3 — preuves PDF « Étude de faisabilité » (0 écart outil ↔ PDF)

PDF générés depuis `etudier_payload` (la MÊME réponse que l'écran) puis `render_pdf` (WeasyPrint).
« Fuites » = nombres imprimés hors payload (verrou `nombres_hors_payload`). pdftotext : pagination `@page` tolérée.

| Commune | N° doc | Retenu | Logts | Places | SDP (m²) | Fuites HTML | Fuites pdftotext | Chiffres retenu imprimés | Pages | « conforme » |
|---|---|:--:|--:|--:|--:|--:|--:|:--:|--:|:--:|
| L'Étang-Salé (UA) | `EF-18102026-8473` | A | 28 | 34 | 1800 | 0 | 0 | ✅ | 11 | ✅ absent |
| Saint-André (UC) | `EF-18102026-9249` | A | 27 | 40 | 1695 | 0 | 0 | ✅ | 11 | ✅ absent |
| Saint-Denis (Ui) | `EF-18102026-1327` | A | 12 | 12 | 795 | 0 | 0 | ✅ | 11 | ✅ absent |

**0 fuite** (HTML et pdftotext) sur les 3 communes : chaque nombre du PDF est une ligne de l'outil. Les chiffres du scénario retenu (logements · places) sont bien imprimés (réciproque). Jamais « conforme ».
