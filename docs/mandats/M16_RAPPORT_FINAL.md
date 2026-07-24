# M16 — RAPPORT DE VAGUE : Notifications & menu compte

Autonome. **CC ne merge pas.** Une branche par lot, poussée. Filet `avant-m16` posé au départ.
Golden **116/116** (`LABUSE_DEV_MODE=1`) à chaque lot. Modèle P **gelé** (zéro touche scoring).

---

## 1. AUDIT NOTIFICATIONS (LOT A) — ce qui déclenche quoi, ce qui est démo, ce qui est notifiable

Rapport complet : `docs/mandats/M16_LOT_A.md`. Synthèse :

- **4 déclencheurs RÉELS**, tous **produits par un nouveau run de scoring** (`detect_events`, pas de
  temps réel) : **bascule** de statut · **procédure BODACC** · **permis neuf ≤ 300 m** d'une parcelle
  suivie · **match de veille** (filtres). Table `event_log`.
- **DÉMO = vraies lignes en base** (`event_log.demo=true`), semées par `seed_demo()` (run `q_v2_demo`,
  `POST /events/demo`). **Pas un mock front.** Badgées DÉMO à l'écran, effaçables/rejouables.
- **« 0 non lue » sur liste pleine** = compteur (`WHERE NOT lu`) ≠ liste (`LIMIT 100`, tout). Après
  lecture, entrées grisées mais toujours listées → lu comme un bug.
- **Veilles** = alerte par filtres **fonctionnelle** (pas une simple recherche mémorisée), mal nommée.
- **E-mail : ABSENT** (SMTP non branché, Resend retiré). Rien à fabriquer côté e-mail ici.
- **Digest** = page HTML « pépites de la semaine » (7 j + top 5 chaudes), **non envoyée**.
- **Notifiable** : **aujourd'hui** = les 4 déclencheurs ci-dessus. **Avec un travail raisonnable** =
  « nouvelle publication » d'une des **5 sources auto** (DVF/BAN/BODACC/DPE/SITADEL) branchée sur
  `event_log`. **Pas notifiable** = changement de PLU, **permis abandonné** (on ne détecte que
  l'apparition), les ~43 sources non sondables. ⚠ écart consigné : mandat = « 9 sondables », `radar.py`
  n'en câble que **5** en `auto` — sans effet sur la conclusion (le radar n'émet **aucune** notif).

---

## 2. PREUVES PAR POINT (app en marche `:8060`)

| Lot | Point | Preuve |
|---|---|---|
| **A** | audit | `M16_LOT_A.md` (lecture seule, refs code) |
| **B1** | intro déclencheurs réels | `qa/m16/B/b1_panneau_refondu.png` |
| **B2** | Digest → « Le point de la semaine » | idem (Digest supprimé, nouveau libellé) |
| **B3** | veilles renommées + expliquées | « VOS VEILLES — ALERTES SUR MESURE » + phrase |
| **B4** | exemples réels (chips) | clic → nom pré-rempli « Parcelles qui basculent en chaude » |
| **B5** | DÉMO badgées · « à jour » · état vide | 54 badges DÉMO ; en-tête « À JOUR » (plus « 0 non lue ») |
| **C1** | abonnement réel + compte + déconnexion | `qa/m16/C/c1_menu_ouvert.png` (Plan Intégral, Session pilote, /logout) |
| **C2** | formulaire suggestion → base | `c2/c3` + CLI `labuse suggestions` liste le retour |

Golden 116/116 sur A(n/a), B, C.

---

## 3. TEXTES PRODUITS (relecture Vic)

**Intro notifications (B1)** — « Les **changements sur les parcelles que vous suivez** — bascule de
statut, procédure BODACC, permis neuf à proximité — et les **alertes de vos veilles**. On ne vous
prévient que sur ce qu'on sait réellement détecter. »

**Renommage Digest (B2)** — « **Le point de la semaine →** » (retenu parmi : Le point de la semaine /
Résumé de la semaine / Récap hebdo).

**Veilles (B3)** — titre « **Vos veilles — alertes sur mesure** » · phrase « Enregistrez une recherche :
on vous alerte dès qu'une parcelle **bascule** et correspond à vos critères. »

**Exemples de veilles (B4)** — « parcelles qui deviennent chaudes » · « nouvelle procédure BODACC ».

**État vide (B5)** — « Aucune notification pour l'instant — nous vous préviendrons dès qu'une parcelle
suivie change ou qu'une de vos veilles se déclenche. »

**Menu compte (C1)** — Abonnement : « Plan **Intégral** · Accès pilote — l'abonnement par compte
(facturation) arrive. » · Compte : « Session pilote » · « Proposer une amélioration » · « Se déconnecter ».

**Formulaire suggestion (C2)** — « Une idée, un bug, un manque ? Dites-le en une phrase — ça compte
vraiment pour la suite. » (catégories Idée / Bug / Autre) · succès : « ✓ Merci, c'est noté. Votre retour
est bien arrivé — on le lit vraiment. »

---

## 4. DÉCISIONS OUVERTES

- **Destination du formulaire de suggestion** : **retenu = base (`suggestions`) + CLI `labuse
  suggestions`**. Motif : aucune infra e-mail dans l'app (audit A3). Si Vic préfère l'e-mail, c'est le
  chantier infra e-mail séparé.
- **Saisie langage naturel (B4)** : livré sous forme d'**exemples-chips branchés sur des déclencheurs
  réels** (réutilisent le mécanisme de veille). La **saisie libre NL → veille** est possible en branchant
  la brique NL validée par schéma sur `_parse_hash_filters`, mais dépassait le cadre honnête de ce lot →
  **évolution proposée** (à valider : quels déclencheurs on autorise en NL, tous limités au réel).

---

## 5. NON FAIT / BLOQUÉ

- **Notification sur mise à jour de source** : **pas câblée**. Le radar SAIT qu'une source a republié
  (5 sources auto) mais n'émet pas d'événement. Travail raisonnable = brancher `nouvelle_publication` →
  `event_log`. **Non promis dans l'UI** tant que non fait.
- **Changement de PLU / permis abandonné** : **non détectables** aujourd'hui (aucun type d'événement) →
  volontairement **absents** des exemples B4.
- **E-mail** (notifications + envoi du « point de la semaine ») : chantier infra à part, hors mandat.
- **Abonnement par compte** : `plan_par_compte=false` — le palier par compte/siège en base est le
  « mandat Auth & Plans » ; le menu affiche le plan courant réel (stub Intégral, pilote) sans inventer.

---

## 6. BRANCHES ET ORDRE DE MERGE

Toutes **poussées, non mergées**. Filet : tag `avant-m16` (sur `main` 1b3ed66).

```
audit/m16-a              (rapport — bloque B ; à lire avant de merger B)
feat/m16-b-notifications (dépend de A)
feat/m16-c-menu-compte   (indépendant)
docs/m16-rapport         (ce rapport)
```

Ordre suggéré : **A → C (indépendant) → B**, puis `docs/m16-rapport`. Aucune dépendance croisée de code
entre B et C (B = `Header.tsx`/NotifBell ; C = `Header.tsx`/AccountMenu + back `onboarding`/`models`/`cli`
+ `api.ts`) — **un conflit léger est possible sur `Header.tsx`** (deux composants voisins) : garder les
deux (NotifBell refondu **et** AccountMenu).

**LOT D** (re-vérification sur `main` mergée) : à exécuter **après** le merge Vic — reboot, recapture des
points B/C, RG1 non concerné ici, golden 116/116.
