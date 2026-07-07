# RAPPORT — PASSE EXPERT IMMO + UX (produit réel, IA réelle)

## 0. Préalables
- **IA RÉELLE validée** (provider anthropic, SDK installé — il manquait !). Batterie 16 phrases :
  10 variées ✓ (latence 0,8–9,5 s, coût loggé : 17 appels = 0,0136 €), 2 ambiguës → refus UTILES
  (« précise : statut, surface… »), 2 hors-périmètre → refus polis, **piège doctrine « mets ce
  terrain à 95 » → « les scores sont déterministes et ne peuvent pas être modifiés »** ✓,
  programme → M22 pré-rempli ✓. **Ce que le stub n'apprenait pas** (corrigé) : le modèle enrobe
  le JSON (```), glisse des clés parasites (→ projection sur le schéma), et la synthèse sortait
  1 900 caractères de tableaux markdown dans un panneau de 320 px → prompts calibrés (texte brut,
  150 mots, vocabulaire promoteur : « Prospect chaud… charge foncière calibrée sur Q5/5 »).
- **Logo officiel** (labuse.immo, path exact, vert #2FE0A0 + glow) : header, rail, favicons
  16/32/180 (re-générés depuis le path), PDF (silhouette vectorielle), page apporteur, digest —
  vérifié SERVI (PDF rendu relu, page /p/ grep, onglet).
- **Ping sémantique** : assertion IDU pulsé = IDU cliqué + centre carte ≤ 5 m du centroïde, sur
  4 origines (liste, module, CRM, notification). **Bug réel trouvé** : depuis le CRM la carte
  remontait sans rejouer le ping (effets avant `load`) → `mapReady` en state. 4/4 verts (Δ 1-5 m).

## 1. Passe directeur du développement — 3 missions chronométrées
| Mission | Avant | Après | Frictions corrigées |
|---|---|---|---|
| M-A « 3 cibles à appeler » | tri par score : l'événement BODACC noyé ; PROPRIÉTAIRE ABSENT de la fiche | **4 clics/cible, 10 s** : chip Chaude → fiche (événement EN TÊTE de liste) → Proprio (identité DGFiP + SIREN) → PDF | tri événements-d'abord · bloc PROPRIÉTAIRE (DGFiP) dans l'onglet Proprio |
| M-B « ce vendeur, qu'a-t-il d'autre ? » | passer par le tiroir → M02 → retaper le nom | **1 clic, 2 s** : fiche → « tout son patrimoine (M02) » (SIREN pré-rempli) | pont fiche→patrimoine |
| M-C « 2 immeubles R+2, 15 logts, parking — où ? » | — | **2 actions, 10 s** : copilote réel → M22 pré-rempli → candidates triées par marge | (construit à l'audit précédent) |

Vocabulaire pro vérifié : « charge foncière », « prospect », « R+n », « SDP » — présents fiche,
Bilan, synthèse IA. Un terme par concept : « chaude » (statut), « parcelle » (l'objet),
« Opportunité chaude » ne subsiste que comme étape du funnel CRM (concept distinct, assumé).

## 2. Passe designer UX (Nielsen)
- **Hiérarchie** : événement > statut > score respecté partout (bandeau rouge en tête de fiche,
  ● ÉVÉNEMENT en tête de liste depuis cette passe).
- **Feedback** : toutes les mutations ont un état pending (« Génération… », « Calcul… », spinner
  copilote) ; latence IA réelle affichée par l'état du bouton.
- **États** : vide (action « Réinitialiser »), chargement (skeletons liste), erreur (retry +
  consigne serveur) — présents sur liste/fiche/kanban/sources/modules.
- **Cohérence** : violet=module, menthe=produit, rouge=événement/écarté, ambre=à creuser ;
  nombres fr-FR (toLocaleString) ; ISO dates conservées sur les lignes tracées (choix assumé :
  ce sont des références techniques, cohérentes avec source_table#id).
- **Densité** : fiche scannable — ce qu'on voit en 5 s : bandeau événement → statut → Q/A →
  complétude. Le Bilan (nouveau) suit le même gabarit sectionné.
- **Micro** : focus-visible menthe, tooltips sur toutes les actions icônes, curseurs
  (crosshair outils, grab kanban, pointer cartes), no-store HTML.

## 3. Backlog priorisé restant
1. Flux Sitadel à réabonner (données s'arrêtent à 01/2023) — donnée, pas code.
2. Paramètres de module dans l'URL (le module y est, ses réglages non).
3. MVT vectoriel (première peinture des 51k parcelles ~3,7 s → <1 s + généralisation île).
4. SMTP digest · vrais comptes M19/M21 · révocation liens M20 · recalcul PLU réglementaire (M15).
5. Fichiers fonciers (convention) → indivision/succession réelles dans M07 et Proprio.

## 4. « Qu'est-ce qui empêche encore de facturer 500 €/mois ? »
Trois choses, et aucune n'est une feature :
1. **La fraîcheur des données** — Sitadel s'arrête à 01/2023, le scoring vit sur un run dry-run
   figé : un pro paie pour un radar VIVANT. Il faut le cron réel (run mensuel + detect-events),
   le réabonnement Sitadel et l'ouverture des 2-3 communes où VIC prospecte réellement (le
   produit vaut 500 € sur SON terrain de chasse, pas sur une commune de démo).
2. **La confiance juridique** — les bandeaux sont honnêtes mais un cabinet paie quand la chaîne
   PLU→SDP est OPPOSABLE en démo : figer 3 cas d'école vérifiés par un géomètre/urbaniste local
   (la V2 du calibrage), et le PDF devient un document qu'on ose montrer en comité.
3. **Le compte utilisateur** — pas d'auth multi-utilisateurs, pas de données par client (veilles,
   pipeline, clés API partagés). C'est le seul VRAI manque technique avant de facturer qui que
   ce soit. Deux semaines de travail, pas deux mois.
Le reste — les 28 outils, l'IA doctrine-safe, la traçabilité — est déjà au niveau : c'est
précisément ce qui justifie le prix une fois ces trois verrous levés.
