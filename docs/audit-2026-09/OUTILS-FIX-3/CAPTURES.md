# Captures avant / après — OUTILS-FIX-3

Prises sur l'app RÉELLE (uvicorn `labuse.api.app` + vite, base `openclaw`, données live 431 663 parcelles).
Le fond de carte MapLibre anime le screenshot plein écran ; les valeurs sensibles sont donc AUSSI
mesurées dans le DOM en direct (font-size, présence d'éléments) pour prouver le contraste sans ambiguïté.

| Lot | Écran | Avant | Après | Preuve DOM (live, base `openclaw`) |
|-----|-------|-------|-------|-------------------------------------|
| A | Faisabilité « par parcelle » (pont) | `avant/AF_faisabilite_parcelle_avant.png` | `apres/AF_faisabilite_parcelle_apres.png` | titre « Capacité constructible » (`.sec > span`) = **16 px** avant → **10 px** après (norme DA, classe stylée sous `.fiche-v6`) |
| F | idem (même écran) | idem | idem | `[data-faisa-explain]` **présent** avant → **absent** après ; libellé M22 sans « explication IA » |
| B | Scan patrimoine · SIREN 392801130 | `avant/B_scan_392801130_avant.png` | `apres/B_scan_392801130_apres.png` | avant : chips **0/0/0** + encart `[data-m02-inpi]` ; après : `[data-m02-aucune-parcelle]` « ne détient aucune parcelle à La Réunion » |
| C | Comparer — tableau | `avant/CE_comparer_tableau_avant.png` | `apres/CE_comparer_tableau_apres.png` | avant : puces tier **« Écartée »/« Neutre »** ; après : plus de puce tier, le chip **« secteur qui bouge »** reste |
| E | Comparer — tableau (même capture) | idem | idem | `[data-compare-csv]` **présent** avant → **absent** après |
| D | Fil de retour (pont Scan→Courrier) | (aucun retour — fonction neuve) | `apres/D_fil_retour_courrier_apres.png` | `[data-outil-retour]` = « **← Scan patrimoine** » en tête du Courrier |

Notes :
- `apres/C_comparer_outil_apres.png` : le panneau Comparer (contexte).
- Lot E (Solaire piscines, Permis/Vélocité) : mêmes retraits `⬇ CSV` que Comparer, non recapturés
  individuellement — le geste retiré est identique et couvert par l'inventaire `E-exports.md` + tests.
- Le fil de retour « avant » n'existe pas (fonction ajoutée par ce mandat) : l'outil cible n'avait
  aucun « ← » ; la capture après suffit à le démontrer.
