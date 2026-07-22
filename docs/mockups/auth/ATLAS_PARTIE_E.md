# PARTIE E — atlas avant/après des écrans d'entrée

_Embellissement des 9 surfaces d'entrée sur le design system validé (`coffre_ui`).
Rendus réels du serveur (viewport 440×900, ×2). La mécanique de paiement auditée (A–D)
n'est pas touchée : design ≠ mécanique._

Rendus dans `rendus/` (PNG). Source unique du dessin : `src/labuse/api/coffre_ui.py`
(tokens en variables CSS, zéro hex épars, accessibilité AA).

## Les 3 écrans à fort enjeu (priorité Vic)

### 1. Bascule vers Checkout — le point d'anxiété
`rendus/shot_bascule_checkout.png` — **écran NET-NEUF**. Avant : l'invitation partait
directement vers Stripe (aucune page de confiance intermédiaire). Après : récap prix (349 €/mois),
3 signaux de confiance (cadenas « sécurisé par Stripe », bouclier « aucune donnée bancaire ne
transite par LABUSE », horloge « facture automatique, résiliation en un clic »), CTA rassurant.
Protégé par un **jeton HMAC signé** (`pay_token`), pas par la session → atteignable juste après
l'invitation. La mécanique `creer_checkout` est appelée inchangée au POST.

### 2. Retour d'échec — désamorcer
`rendus/shot_retour_echec.png` — **écran NET-NEUF**. Pastille douce ambre `↺`, titre « Paiement
non finalisé », sous-titre **« rien n'a été débité »**, CTA « Réessayer ». Le pendant succès
(`shot_retour_succes.png`) : pastille menthe `✓`, « Bienvenue », entrée dans l'app.

### 3. Les Flash (4 surfaces)
- `rendus/shot_flash_confirm.png` — confirmation avant paiement : récap parcelle (IDU mono),
  prix 79 € détaché, CTA. **Avant/après saisie** : `shot_AVANT_flash_saisie.png` (champ
  souligné, hex en dur `#1E2A23`) → `shot_APRES_flash_saisie.png` (champ `.field` boxé, hint AA).
- `rendus/shot_flash_gen.png` — génération : pastille menthe + spinner, `aria-live` annonce
  « quelques secondes ». Le lien PDF (`.pill` avec icône ↓) s'affiche à la génération.
- Lien expiré / paiement indisponible : messages sobres dans le design system (`.sub`).

## Les surfaces restantes (6)

| Écran | Avant | Après |
|---|---|---|
| **Porte (login)** | `shot_AVANT_login_defaut.png` / `_erreur` — Coffre à soulignement, CSS local | `shot_login_defaut.png` / `_erreur` — design system, champs `.field`, lien « mot de passe oublié », erreur `role=alert` à espace réservé |
| **Invitation** | champ souligné + règles en texte | `shot_invitation.png` — jauge de robustesse `labStrength` (aria-live), consentement CGV encadré |
| **Reset** | `shot_AVANT_reset.png` | `shot_APRES_reset.png` — `.field`, jauge de robustesse, note « toutes les sessions seront fermées » |
| **Retour succès** | inline styles | `shot_retour_succes.png` |
| **CGV / mentions / confidentialité** | `.legal` déjà correct | rendu design system 760 px (`shot_legal_cgv.png`) ; **mentions corrigées** (retrait de « Resend » : plus aucun email automatique) |
| **Guide** | `.legal` | inchangé de structure, hérite du design system |

## Ce qui NE change pas (garde-fous tenus)

- `creer_checkout`, `webhook`, réconciliation, dédup event, FLASH DB-backed : **zéro touche**.
- Zéro hex local : toutes les surfaces naissent des tokens `coffre_ui.CSS`.
- Nouveau code auth-sensible = **testé** : `test_bascule_paiement_atteignable_sans_session_mais_jeton_signe`
  (public par nature, sécurité = jeton signé, 400 gracieux sur jeton absent/forgé/altéré).
