# M16 — LOT C : menu compte / avatar VL

**Branche** `feat/m16-c-menu-compte` (base `main`). Prouvé, **non mergé**.

Avant : l'avatar « VL » était un `<span>` inerte (aucun menu). Maintenant : un menu déroulant digne d'un
SaaS payant, **sans donnée d'abonnement inventée**.

## C1 — Contenu du menu (`AccountMenu` dans `Header.tsx`)
- **Abonnement** : le **palier RÉEL** lu via `GET /moi` → `plan_courant()` (`plans.py`). Aujourd'hui
  **Intégral** (stub env-driven, pilote). Mention honnête : « Accès pilote — l'abonnement par compte
  (facturation) arrive ». **Pas de faux « Pro »** : `plan_par_compte=false` tant que le mandat Auth &
  Plans n'a pas branché le palier par compte en base. Les vrais paliers sont **Essentiel / Intégral**
  (pas Indé/Pro/Organisation — ceux du mandat étaient une supposition ; on affiche le réel).
- **Compte** : mode réel (`Session pilote` en pilote ; `Rôle : …` pour un vrai compte).
- **Se déconnecter** : lien `/logout` (révoque la session serveur + redirige `/login` — existant).

## C2 — « Proposer une amélioration » → formulaire → destination RÉELLE
- Ligne dans le menu → formulaire court (catégorie Idée/Bug/Autre + un champ texte), ton proche.
- **Destination = base de données** (table `suggestions`), **pas d'e-mail** : l'audit A3 confirme
  qu'il n'existe aucune infra e-mail dans l'app (Resend retiré). La base est la destination la plus
  simple **et réellement consultable**.
- **`POST /suggestions`** (onboarding.py) insère `{categorie, texte, contexte, compte_mode}`.
- **Vic consulte** via la commande CLI ajoutée **`labuse suggestions`** (`--nouvelles` pour les non
  traitées). Table créée idempotemment par `ensure_suggestions` **dans `ensure_schema`** (chemin boot,
  comme M15 `ensure_promesses_index`).

## Preuve (`:8060`, `qa/m16/C/prove.mjs` + CLI)
- Menu ouvert : « Plan **Intégral** » + « Accès pilote… » · « Session pilote » · « Proposer une
  amélioration » · « Se déconnecter » (`a[href="/logout"]`). Capture `c1_menu_ouvert.png`.
- Formulaire → envoi → **« ✓ Merci, c'est noté »** (`c2_formulaire.png`, `c3_envoye.png`).
- Persistance prouvée : `labuse suggestions` liste les retours (dont celui du test). Backend :
  `POST /suggestions → {ok:true}`, `ensure_schema` recrée la table après DROP.

## Golden
**116/116 PASS** (`LABUSE_DEV_MODE=1`, `LABUSE_API_BASE=:8060`). Zéro touche scoring.

## Décision ouverte (rappelée au rapport final)
Destination du formulaire = **base + CLI `labuse suggestions`** (retenu, aucune infra e-mail). Si Vic
préfère un e-mail, ce sera le chantier infra e-mail séparé.
