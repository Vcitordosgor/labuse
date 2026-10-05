# Rejouer le parcours

Pré-requis : dépôt principal `~/Desktop/labuse` avec `.venv` (PDF-capable) et `frontend/node_modules`.

```bash
# 1) node_modules symlinké pour le front de CE worktree
ln -sfn ~/Desktop/labuse/frontend/node_modules frontend/node_modules
# 2) build (pour servir /socle en single-origin ; voir RAPPORT BLOQUANT-1 si page blanche)
(cd frontend && npm run build)
# 3) API single-origin DRY-RUN (vide SMTP + BREVO + Stripe), port 5995
bash scripts/run-api.sh &
# 4) dev server single-origin (contourne la page blanche du build prod), port 8795
cp scripts/vite.parcours.config.mjs frontend/vite.parcours.config.mjs
(cd frontend && LABUSE_API_DEV=http://127.0.0.1:5995 node_modules/.bin/vite --config vite.parcours.config.mjs &)

# 5) jouer une phase (captures + run-logs/steps.jsonl)
export PW_PKG=~/Desktop/labuse/frontend/node_modules/playwright/index.js
bash scripts/run.sh vicB.mjs          # Section B — création + validations + fiche
bash scripts/run.sh bLifecycle.mjs    # Section B — cycle de vie (captures)
bash scripts/run.sh clientC.mjs       # Section C — mot de passe, login, 1re entrée, 403, gestes, Mon compte
bash scripts/run.sh sectionD.mjs      # Section D — expiration + dashboard activité
bash scripts/run.sh mobilePublic.mjs  # mobiles pages publiques
~/Desktop/labuse/.venv/bin/python scripts/render_mails.py       # Section A — rend les 16 mails (lecture seule Brevo)
bash scripts/run.sh capture_mails.mjs                            # Section A — capture PNG desktop+mobile
~/Desktop/labuse/.venv/bin/python scripts/make_mails_csv.py      # MAILS.csv
~/Desktop/labuse/.venv/bin/python scripts/make_parcours_csv.py   # PARCOURS.csv
~/Desktop/labuse/.venv/bin/python scripts/purge_verify.py        # purge RGPD + preuve 0 ligne
```

Note importante : `scripts/run-api.sh` vide **BREVO_API_KEY** en plus du SMTP — sinon
`config.load_dotenv(.env)` réinjecte la clé et les mails du cycle de vie **partent pour de vrai**
(voir RAPPORT, G1). Lanceurs Lecture seule : `render_mails.py` fait des GET Brevo (aucun envoi).
