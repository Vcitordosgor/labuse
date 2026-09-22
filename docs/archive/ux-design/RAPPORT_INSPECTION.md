# 🔍 RAPPORT D'INSPECTION HOSTILE — feat/outils-ia

> Casquette inspecteur : l'objectif était de CASSER, pas de prouver. Méthode : harnais
> « clique-tout » (inventaire DOM → clic souris réel au centre → verdict par triple signal
> DOM/URL/réseau + détection d'occlusion et de rognage), 28 scénarios métier/hostiles,
> revues visuelles. Chaque bug corrigé a reçu un test reproduisant LA CONDITION UTILISATEUR.

## Compte global
**326 éléments cliqués (souris réelle) sur 28 écrans · 4 « morts » détectés → 2 faux positifs du
harnais (vérifiés fonctionnels à la main), 2 vrais défauts UX corrigés · 0 douteux résiduel.**
115 « neutres » = éléments occultés au moment du clic (fiche par-dessus la toolbar) ou recréés
par React — re-couverts par les suites ciblées. Après fixes : **8 suites, 223 checks, 0 échec**
(`outputs/qa_inspection_finale.log`).

## 🐛 Bugs TROUVÉS et CORRIGÉS (fix → re-inspection réelle → test de non-régression)
| # | Gravité | Bug | Fix | Test ajouté |
|---|---|---|---|---|
| 1 | HAUTE | **M08 : côté 1950 NOIR au zoom > 15** — source WMTS sans maxzoom, MapLibre n'affiche rien au lieu d'agrandir les tuiles parentes (trouvé par capture après drag+zoom) | maxzoom 15/17 sur TimeMachine + sélecteur de fonds ; vérifié visuellement à z17 (image N&B agrandie, synchro exacte) | `qa_regressions.mjs` : z17 → pixels non-noirs + zooms égaux (hook __labuse_tm) |
| 2 | MOYENNE | **M03 ignorait la zone dessinée** — le mandat nuit dit « Sitadel par zone dessinée/commune », seul commune+période était câblé | filtre pointInPolygon des permis géocodés + libellé « N permis dans la zone dessinée · outil Zone actif » | `qa_regressions.mjs` : zone posée → libellé + compte filtré |
| 3 | BASSE | **M18 : « 2700.0 €/m² »** dans le rapport marketing + médianes communales sans trim anti-aberrants (incohérent avec les quintiles) | `::int` + trim 100-12 000 €/m² | `qa_regressions.mjs` : toutes les médianes sont entières |
| 4 | HAUTE | **Les veilles ne notifiaient JAMAIS** (demi-feature : sauvegardées mais muettes — le mandat M11 dit « une veille alimente la cloche ») | `detect_events` matche chaque bascule montante contre les filtres de chaque veille (hash parsé serveur) → événement 🔭 nominatif | `qa_regressions.mjs` : veille + détection → 🔭 en base ET visible dans la cloche |

## ⚠ Douteux assumés (consignés, pas cassés)
- **Fiche Bilan** : état vide annoncé (« le moteur existe, paramètres à valider ») — message utile,
  pas d'action car c'est une capacité future, pas une erreur.
- **Deux lignes « dvf »** dans l'onglet Marché (prix + liquidité) — les détails désambiguïsent ;
  renommage éventuel (« dvf-prix » / « dvf-liquidité ») = choix produit à trancher par Vic.
- **M01 « 3 sliders »** (mandat) : UN slider exposé (score) — C1-C5 sont des critères serveur
  documentés ; exposer surface/emprise en sliders = itération produit, pas un bouton mort.
- **M02 SIREN inexistant** : impossible via l'UI (autocomplétion sur les SIREN réels) ; l'API
  répond proprement (0 parcelle) — testé.
- **Double-clic « Partager » (M20)** : crée 2 liens (chaque clic = un lien traçable distinct —
  comportement défendable, chaque lien a son compteur). Consigné.

## Scénarios métier & états hostiles (28 exécutés — inspect_scenarios.mjs)
✓ M08 poignée (drag réel Δ−319 px) et synchro caméras · ✓ M09 15 parcelles × 3 contextes +
contenu du .md téléchargé (15/15) · ✓ cloche s'incrémente sur événement · ✓ F5 restaure les
15 modules (#m=…) · ✓ back/forward ×10 sans casse · ✓ double-clic + Pipeline → 1 seule entrée ·
✓ score −5 / 999999999 → état vide propre avec action · ✓ émoji dans l'omnibox · ✓ 1024 px
utilisable (panneau + carte, zéro débordement) · ✓ M20 en session vierge (filigrane + horodatage
+ compteur) · ✓ M21 401/200/429 (quota réel testé à 2) · ✓ M15 ne persiste RIEN (compte des
runs identique avant/après) · ✓ M16 non-contiguës → « NON contiguë » visible · ✓ M10 vide/émoji
→ réponses propres · ✓ IA « les parcelles de Saint-Denis » → refus honnête (commune non filtrable) ·
✓ 3 PDF rendus et RELUS (fiche simple, fiche événement, baromètre).

## Clique-tout — les 4 « morts » et leur verdict final
| Élément | Verdict après contre-enquête |
|---|---|
| [fiche] case « Parcelles » (fiche ouverte) | **FONCTIONNE** (vérifié à la main : le DOM change) — faux mort : l'échantillonnage du hash du harnais a raté un petit changement de classe |
| [cloche] titre d'un événement | **FONCTIONNE** (clic → fiche de la parcelle) — faux mort : ordre de clics du harnais (backdrop) |
| [crm] corps d'une carte kanban | **VRAI DÉFAUT** → corrigé : tout le corps ouvre la fiche (✕ et drag préservés) + test |
| [rail] IA déjà actif | **no-op volontaire non annoncé** → corrigé : `aria-current` sur le rail (a11y) + test |

## Bugs 5-6 (clique-tout) — corrigés
| # | Bug | Fix | Test |
|---|---|---|---|
| 5 | Corps de carte kanban inerte au clic | carte entière cliquable → fiche | qa_regressions |
| 6 | État actif du rail non annoncé | aria-current="page" | qa_regressions |

## Bruit console éliminé
Les tuiles océan hors-emprise (Plan IGN WMTS → 400 légitimes) polluaient la console : avalées au
niveau carte (MapView + TimeMachine) — la console ne montre plus QUE les vraies erreurs.
`seed_demo` est désormais REJOUABLE (reset des événements démo → la cloche se rallume à chaque
démonstration).

Annexes : `docs/design/captures/inspection/` (rapport.jsonl 326 lignes, captures avant/après,
revues visuelles fiche/PDF/1950).
