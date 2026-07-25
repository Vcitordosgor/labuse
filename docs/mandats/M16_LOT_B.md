# M16 — LOT B : refonte du panneau Notifications

**Branche** `feat/m16-b-notifications` (base `main`). Prouvé, **non mergé**. Fondé sur l'audit **LOT A**
(`NotifBell`, `Header.tsx`). Aucun back touché (frontend seul) — on ne promet **que le réel** (A5).

## B1 — Texte d'introduction (déclencheurs RÉELS uniquement)
Bandeau en tête du panneau : « Les **changements sur les parcelles que vous suivez** — bascule de statut,
procédure BODACC, permis neuf à proximité — et les **alertes de vos veilles**. On ne vous prévient que
sur ce qu'on sait réellement détecter. » → décrit exactement les 4 déclencheurs câblés (A1), **pas** « les
mises à jour de nos sources » (faux aujourd'hui, A5).

## B2 — « Digest » renommé
Jargon incompris → **« Le point de la semaine → »** (title : « Récapitulatif hebdomadaire — ce qui a bougé
+ top chaudes »). Même cible (`/events/digest.html`, page récap non envoyée par e-mail — A4).

## B3 — « Veilles » clarifié
L'audit A2 établit que la veille est **fonctionnelle** (alerte par filtres, pas une simple recherche
mémorisée). Renommé **« Vos veilles — alertes sur mesure »** + phrase : « Enregistrez une recherche : on
vous alerte dès qu'une parcelle **bascule** et correspond à vos critères. » Rien retiré.

## B4 — « Décrire ce qu'on veut suivre » : exemples RÉELS (pas de fausse saisie)
Les exemples de Vic (« changement de PLU », « permis abandonné ») sont **non détectables** (A5) — écartés.
À la place, deux **chips d'exemples = déclencheurs réels** : « parcelles qui deviennent chaudes » (→
filtre `tiers:['chaude']`) et « nouvelle procédure BODACC » (→ filtre `evenement`). Un clic **pré-remplit
les filtres + le nom de la veille** ; l'utilisateur ajuste, nomme, « + Veille » enregistre — **réutilise
le mécanisme de veille existant** (filtres → `saveSearch` → alerte au run). Aucune saisie qui ne
déclencherait rien.

*(La saisie langage naturel libre → veille est possible en branchant la brique NL validée par schéma sur
`_parse_hash_filters` ; consigné comme évolution — cf. rapport final, décision ouverte.)*

## B5 — Données de démo + « 0 non lue »
- Les entrées DÉMO sont de **vraies lignes** `event_log.demo=true` (A1) : elles restent **badgées DÉMO**
  sans ambiguïté (jamais présentées comme réelles). Leçon Matching M15.
- **État vide honnête** : « Aucune notification pour l'instant — nous vous préviendrons dès qu'une parcelle
  suivie change ou qu'une de vos veilles se déclenche. » (plus « le prochain run… »).
- **Fin de l'incohérence « 0 NON LUE »** : l'en-tête affiche « · X non lue(s) » **seulement s'il y en a**,
  sinon **« · à jour »** (liste pleine mais lue) ou rien (liste vide). Plus jamais « 0 non lue » sur une
  liste pleine.

## Preuve (`:8060`, panneau peuplé par seed démo, `qa/m16/B/prove.mjs`)
- intro réelle ✓ · « Digest » supprimé ✓ · « Le point de la semaine » ✓
- **54 badges DÉMO** ✓ · en-tête **« À JOUR »** (pas « 0 non lue ») ✓
- « VOS VEILLES — ALERTES SUR MESURE » + explication ✓ · **2 chips d'exemples** ✓
- clic exemple → nom pré-rempli **« Parcelles qui basculent en chaude »** + filtres posés ✓
Captures : `b1_panneau_refondu.png`, `b2_exemple_veille.png`, `b3_tout_lu.png`.

## Golden
**116/116 PASS** (`LABUSE_DEV_MODE=1`, `LABUSE_API_BASE=:8060`). Zéro touche back / scoring.
