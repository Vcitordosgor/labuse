# M18 — RAPPORT DE VAGUE : parcours onboarding & paiement (Intégral + Flash)

Autonome. **CC ne merge pas.** Une branche par lot, poussée. Filet `avant-m18` (sur `main`). Golden
**116/116** (`LABUSE_DEV_MODE=1`) par lot. Modèle P **gelé**. **Stripe et envoi e-mail hors périmètre** :
pages/mécaniques prêtes au branchement, jamais de paiement ni d'e-mail simulé.

---

## 1. PREUVES PAR ÉCRAN

**Intégral** (`qa/m18/A/`) — arrivée + CGV bloquée (`a1`), CGV cochées → CTA actif (`a2`), paiement
« engagement 12 mois » (`a3`), post-paiement valorisant (`a4`), reset formulaire + nouveau mdp (`a6`).
**Flash** (`qa/m18/B/`) — arrivée vendeuse (`b1`), pré-paiement (`b2`), génération (`b3_generation`) →
« rapport prêt » + bouton PDF proéminent (`b3_rapport_pret`), inventaire PDF (`flash_sample.html`).

| Point | Résultat |
|---|---|
| RG-FAV | favicon LABUSE (buse) sur toutes les pages — SVG inline garanti (A, `coffre_ui`) + PNG |
| A1 | arrivée soignée + offre « 349 €/mois · engagement 12 mois » ; placeholder `prenom.nom@cabinet.re` |
| **A2** | **CTA désactivé + message tant que CGV décochées** ; page « Conditions requises » gagne « ← Revenir » — **cul-de-sac fermé** |
| A3 | « Engagement 12 mois, facturé mensuellement » ; « en toute sécurité » **retiré** |
| A4 | « Bienvenue chez LABUSE » + gros bouton d'accès |
| A5 | phrase « pré-analyse sur données publiques » **retirée** du consentement |
| A6 | self-service reset (formulaire + token 1 h + page nouveau mdp), envoi câblé + **état honnête** |
| B1 | bouton « Voir ma parcelle » + valeur du PDF explicitée |
| B2 | pré-paiement attractif + réassurances |
| B3 | « **Votre rapport est prêt** » en vedette + **bouton PDF proéminent** |
| B4 | PDF inventorié (8 sections sourcées) + boussole OK (aucune identité de personne physique) |

---

## 2. TEXTES PRODUITS (relecture Vic — sa voix commerciale)

- **Offre Intégral** : « licence Intégral · 349 €/mois · engagement 12 mois » · « Engagement 12 mois,
  facturé mensuellement » · bouton « Payer 349 € ».
- **Message CGV bloquée** : « Vous devez d'abord accepter les conditions générales pour continuer. »
- **Post-paiement Intégral** : « Bienvenue chez LABUSE · votre abonnement Intégral est actif » + « Vous
  avez désormais accès à tout le radar foncier de La Réunion — le scoring des parcelles, les fiches
  sourcées, les outils d'analyse et le dossier banquier. »
- **Reset (honnête)** : « Demande enregistrée · un lien valable 1 h a été généré · l'envoi automatique
  par e-mail est en cours d'activation — en attendant, votre contact LABUSE peut vous le transmettre. »
- **Placeholder e-mail** : `prenom.nom@cabinet.re`.
- **Flash — tagline** : « le dossier complet d'une parcelle, en PDF · 79 € ».
- **Flash — bouton d'entrée** : « Voir ma parcelle → » *(écartés : « Analyser ma parcelle »,
  « Préparer mon rapport »)*.
- **Flash — valeur** : « Ce que vous n'auriez pas trouvé seul : les règles du PLU traduites en clair, le
  potentiel constructible chiffré, et les signaux croisés que LABUSE agrège — pas une simple fiche
  cadastrale. »
- **Flash — bouton pré-paiement** : « Payer 79 € et recevoir mon rapport → ».
- **Flash — post-paiement** : hero « Votre rapport est prêt » · bouton « ↓ Télécharger mon rapport PDF ».

---

## 3. PDF FLASH — inventaire + propositions (arbitrage Vic)

Détail dans `M18_LOT_B.md` §B4. **8 sections** : identité · constructibilité (règles calibrées + verdict/score
v2) · risques · patrimoine & environnement · marché (comparables DVF **anonymisés**) · dynamique locale ·
terrain · sources (avec millésime). **Boussole vérifiée : aucune identité de personne physique.**
**Propositions à arbitrer** (non ajoutées) : millésime au plus près de chaque valeur · vélocité admin de la
commune (délai PC) · rareté/horizon ZAN · encadré « leviers » commune · solaire. **Jamais** le propriétaire
personne physique.

---

## 4. ÉTATS DÉPENDANTS D'UN SERVICE EXTERNE

- **Stripe (paiement)** : **non branché** (hors périmètre). Les pages Intégral (`/onboarding/paiement`) et
  Flash (`/flash` → Checkout) sont **prêtes** — l'acte de payer s'activera au branchement Stripe, sans
  retoucher ces écrans.
- **E-mail (reset mot de passe)** : **mécanique complète** (token 1 h, page reset). L'**envoi réel est
  inactif** faute de service e-mail (Resend retiré, audit M16). Point d'envoi identifié :
  `onboarding._envoyer_reset_email(email, lien)` (trace le lien dans le log = file d'attente). **Dès qu'un
  service e-mail sera câblé, ce corps de fonction est remplacé sans toucher aux appelants.** L'UI n'affiche
  **jamais** « e-mail envoyé ».

---

## 5. DÉCISIONS OUVERTES

- ⚠ **CGV vs engagement 12 mois** : le texte légal CGV (`onboarding.py`) dit encore « résiliable à tout
  moment » — **contradiction** avec l'engagement 12 mois désormais affiché sur la page paiement. **Je n'ai
  pas touché au texte légal** (ressort de Vic). À réconcilier (rédaction juridique).
- **Libellé bouton Flash** : « Voir ma parcelle » retenu (alternatives consignées).
- **Enrichissement PDF Flash** : liste §3 à arbitrer avant tout ajout.
- **Montant Intégral** : affiché à **349 €/mois** (valeur réelle `PLANS.integral`) — le « 290 » du mandat
  était un exemple à adapter.

---

## 6. NON FAIT / BLOQUÉ

- **Paiement Stripe** et **envoi e-mail** : hors périmètre (chantiers dédiés) — construits prêts, jamais
  simulés.
- **Génération PDF (WeasyPrint)** : le rendu PDF binaire nécessite le `.venv` weasyprint (le HTML de
  référence a été rendu et inventorié à la place — `flash_sample.html`).
- **Texte légal CGV** : non modifié (décision + rédaction = Vic).

---

## 7. BRANCHES ET ORDRE DE MERGE

Toutes **poussées, non mergées**. A et B **indépendants** (ordre libre).

```
feat/m18-a-integral   (onboarding.py, coffre_ui.py [favicon + :disabled], auth.py)
feat/m18-b-flash      (onboarding.py — pages Flash)
docs/m18-rapport      (ce rapport)
```

⚠ **Conflit attendu sur `onboarding.py`** (A et B éditent ce fichier, sur des routes différentes :
A = `/invitation`, `/onboarding/*`, `/reset` ; B = `/flash*`). Garder **les deux** intentions au merge.
La partie favicon/`:disabled` de `coffre_ui.py` vient de **A** (partagée) — bénéficie aussi à Flash.

**LOT C** (re-vérification sur `main` mergée) : après le merge Vic — reboot, recapture des 12 points de la
checklist (favicon, A1-A6, B1-B4), golden 116/116.
