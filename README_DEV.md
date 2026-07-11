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
