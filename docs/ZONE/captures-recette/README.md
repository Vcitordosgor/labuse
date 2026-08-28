# ZONE-RECETTE — captures (vérif)

Prises sur le stack dev réel (uvicorn + vite, base dev, isochrones IGN live). Parcelle test :
`97415000AB0004` (Saint-Paul), activité « Boulangerie et boulangerie-pâtisserie » (1071C).

| Capture | Montre |
|---|---|
| `00-panneau-initial-1440` | Panneau à l'ouverture — segmenté **[ Autour d'un point ] [ Zone dessinée ]** (LOT C). |
| `01-point-avant-analyse-1440` | Mode point : ParcelInput (IDU), temps 5/10/15, mode voiture/à pied, activité. |
| `02-point-resultats-1440` | Isochrone tracée + résultats. |
| `03-point-scroll-bas-1440` | **Panneau scrollé jusqu'au « Marché immobilier de la zone »** à zoom 100 % (LOT B). |
| `04-relance-rearme-1440` | Après changement de temps (15 min) : « Analyser la zone » réarmé (RELANCER). |
| `05-seconde-analyse-1440` | Seconde analyse enchaînée (nouvelle isochrone). |
| `06-point-mobile-390` | Mobile 390 : en-tête **« LA ZONE À 15 MIN EN VOITURE — DEPUIS AB 0004 »** (LOT D) ; **« non couvert · actifs y travaillent (MOBPRO non ingéré) »** et **« Concurrents — Non couvert par la base — le répertoire SIRENE… pas encore ingéré »** (LOT A, plus de faux zéro). |
| `07-point-mobile-scroll-390` | Mobile 390 scrollé — tout atteignable. |
| `08-polygone-en-cours-1440` | Mode « Zone dessinée » : tracé du polygone (Entrée valide). |
| `09-polygone-resultats-1440` | Résultats sur le polygone + polygone sur la carte (en-tête « LA ZONE DESSINÉE — N ha », LOT D). |
| `10-sortie-carte-nette-1440` | Après « ← Outils » : **carte NETTE, plus de pointillé** (LOT F). |

Note : l'adresse BAN de la parcelle test étant non rattachée, l'en-tête retombe honnêtement sur le
libellé court de la parcelle (« AB 0004 ») — jamais un « — » muet.
