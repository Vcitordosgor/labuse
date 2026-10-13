# LOT E — hors de l'app (mails, PDF, partage, /flash, vitrine)

## Domaine de base des liens (jamais 127.0.0.1)
- Source unique : `public_base_url` ; repli `127.0.0.1:8000` UNIQUEMENT en `env=local`, sinon `https://app.labuse.immo` (`config.py:335-341`). **Garde** `config.py:383-396` : fonction unique qui AVERTIT (lue par `/readyz`, page Comptes, fiche, `mail_queue`) si l'URL pointe sur localhost/127.0.0.1/0.0.0.0. ⇒ en prod, aucun lien 127.0.0.1 ne part en silence. **Point sain.**
- Pages publiques servies sans `127.0.0.1`/localhost dans le HTML (`/flash`, `/login`, `/reset`, pages 404).

## Mails
| Mail | Lien | Domaine | Expiration | Verdict |
|---|---|---|---|---|
| Reset mdp (Brevo 14) | `/reset?token=` | public_base_url | 60 min | OK |
| Invitation / Essai 48h / Bienvenue (4/6) | `/invitation?token=` | public_base_url | 7j / 48h | OK (invalide → page HTML brandée) |
| Flash prêt (17) | `/flash/retour?session_id=` | public_base_url | 30j | OK |
| Téléchargement Flash | `/flash/telecharger?token=` | public_base_url | 30j | OK (invalide → page HTML brandée) |
| **Digest notifications** | `/socle/#parcelle={idu}` | public_base_url | — | **ÉCART N-1 🟡** |
| List-Unsubscribe (RFC 8058) | LIEN_DESABO | — | — | OK (optionnel) |

**N-1 raffiné (matérialisé)** : `digest_notifications(...)` produit littéralement `https://app.labuse.immo/socle/#parcelle=97411000BZ1065` — format `#parcelle=` que le front ne lit pas (il lit `#idu=`). Le digest **HTML** (version primaire, `digest_html_email`) n'a **aucun** lien cliquable par parcelle (texte « détail dans l'application »). ⇒ aucun deep-link parcelle fonctionnel depuis un digest. (Détail dans ECARTS.md.)

## PDF
- `/dossier/{idu}.pdf` généré (200, 265 Ko) : **0 URI http, 0 localhost** dans le fichier. Les PDF ne portent aucun lien cliquable — pied de page texte seul (`export_commun.py:181` « LABUSE · radar foncier La Réunion · … »). ⇒ pas de risque de mauvais domaine dans les PDF. **Point sain.**

## Liens expirés / invalides (gérés proprement ?)
- `/invitation?token=BAD` → 404 **page HTML LABUSE brandée** (navigateur, `Accept: text/html`). ✓
- `/flash/telecharger?token=BAD` → 404 **page HTML brandée**. ✓
- `/p/BADTOKEN` → en navigateur (Accept text/html) : **page 404 brandée** via handler global `app.py:530-536` (`_NOT_FOUND_HTML`). En client non-HTML (curl `*/*`) : JSON `{"detail":"Lien inconnu"}` — comportement API standard, **pas montré à un humain**. ✓ (page générique, non spécifique « ce lien a expiré » — acceptable).
- `/reset?token=BAD` → 200, la page de reset se charge, le token est validé au POST. ✓

## Page de partage (/p/{token})
- `partners.py:358` `response_class=HTMLResponse` : token valide → page read-only brandée (filigrane horodaté, révocable 30j). Invalide/expiré → 404 brandé en navigateur. ✓

## /flash public + vitrine → app
- `/flash` (`:8770`) : rend « Rapport Flash · 79 € · 11 volets · saisie adresse/IDU · bouton "Voir ma parcelle →" · "Rien n'est débité à cette étape" · "Vendu par LABUSE (CLOSING CREST)" · contact mailto ». Capture `captures/E-flash-public.png`. Flux de paiement NON déclenché (irréversible en aval — relevé sans exécuter).
- `/login` → **302 `/`** (vitrine « Se connecter » → app). ✓
- Vitrine « Commander un Flash » → `/flash` (rend). ✓
- ⚪ **Artefact DEV** : sur `/flash`, 5× 404 `/socle/fonts/*.woff2` — aucun `dist` bâti dans le worktree (vite sert le front sur :5970, l'API sert `/flash` + `/socle` statiques depuis `dist` absent). En prod `dist/fonts` existe (copié de `public/fonts`) → pas de 404. Repli polices système, page fonctionnelle. Non consigné en écart.

## Verdict Lot E
1 écart (**N-1 🟡** digest `#parcelle=`). Tout le reste sain : domaine protégé par garde, PDF sans liens, liens expirés brandés en navigateur, /flash et /login fonctionnels.
