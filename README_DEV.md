# Démarrer en dev (shell vierge)

```bash
conda activate labusedb                 # env conda du poste
pip install -r requirements.txt         # cœur (+ requirements-ml.txt pour la cascade juges)
labuse api                              # → http://127.0.0.1:8000
```

**Connexion base** : la config a pour défaut le rôle PostgreSQL `labuse`. S'il n'existe
pas sur le poste (erreur `FATAL: role "labuse" does not exist`), renseigner le rôle réel
dans `.env` (déjà fait ici avec le rôle OS `openclaw`, auth trust localhost) :
`LABUSE_DATABASE_URL=postgresql+psycopg://VOTRE_USER_OS@localhost:5432/labuse` — voir `.env.example`.

## Les DEUX environnements Python du poste (et qui fait quoi) — BLOC B

Constat consigné (revue UI/UX + BLOC B) : deux env coexistent sur ce poste, avec un piège.

| Env | Où | Sert à | Piège connu |
|---|---|---|---|
| `labusedb` (conda) | `~/miniforge3/envs/labusedb` | serveur de dev (`labuse api`), golden, scripts | **weasyprint ne s'importe PAS** (libs natives pango/gdk-pixbuf absentes de l'env conda) → les endpoints PDF (banquier, dossier) renvoient 500 |
| `.venv` (repo) | `./.venv` | suite pytest (`.venv/bin/python -m pytest tests`), serveur PDF-capable | l'URL DB doit être `postgresql+psycopg://…` (le schéma `postgresql://` nu tombe sur le dialecte psycopg2, non installé) |

Règles pratiques :
- **Tester un PDF en local** → serveur `.venv` (`.venv/bin/labuse api`), pas conda.
- **Unifier** (optionnel) : `conda install -c conda-forge pango gdk-pixbuf` dans `labusedb`
  rend weasyprint importable partout — non appliqué d'office (l'env conda du poste n'est
  pas versionné) ; le VPS, lui, a pango installé au vps_setup (incident M7 n°2).
- Toujours exporter `PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj` pour pytest
  (dette pyproj connue) et `LABUSE_DATABASE_URL=postgresql+psycopg://…`.
