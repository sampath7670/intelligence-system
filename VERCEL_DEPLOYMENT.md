# Deploy intelligence-system to Vercel

The repository serves its browser UI and FastAPI API from one Vercel project.
`app.py` exports `backend.main:app`; `.python-version` selects Python 3.13.
The root `requirements.txt` contains the deployment dependencies. The larger
`backend/requirements.txt` is for the original local ML/Streamlit setup.

## Deploy

From the repository root:

```powershell
npx --yes vercel login
npx --yes vercel --prod
```

Alternatively, push the deployment files to GitHub and import
https://github.com/sampath7670/intelligence-system at https://vercel.com/new.
Use the repository root, the FastAPI framework preset, and default build settings.
Do not set an output directory or use the Streamlit start command.

## Storage and model behavior

Without DATABASE_URL, Vercel uses SQLite in `/tmp/networking_assistant.db`.
This is demo storage: records can disappear on cold starts and redeployments,
and separate instances do not share records. Local database files and environment
files are excluded from uploads. Startup creates sample data from source code.

For durable storage, configure an external database through DATABASE_URL and add
its SQLAlchemy driver to requirements.txt before redeploying. No external database
is provisioned by this configuration. The app currently has no authentication;
use only demo information on a public deployment.

The lightweight deployment uses template generation and hashed-word vectors with
NumPy/BM25 retrieval. Transformer models, Torch, and FAISS are not installed by the
root requirements file.

## Verify after deployment

- `/` with a browser: web UI
- `/api/health`: JSON status `ok`
- `/docs`: API documentation
- `/api/users`: seeded sample user
- `/api/knowledge/documents`: curated knowledge documents

Vercel reference: https://vercel.com/docs/frameworks/backend/fastapi
