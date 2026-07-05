# Deploying Passport (free tier)

Two components can be hosted. For a **clickable public demo, deploy the dashboard** —
it's free, always-public, and self-seeds so it's never empty. The API is optional.

---

## Option A (recommended) — Dashboard on Streamlit Community Cloud · FREE

A public URL judges can open and interact with. Free forever for public apps.

1. Code is already on GitHub: `ShivenduShivu/MemoryLayer_for_Agents` (public).
2. Go to **https://share.streamlit.io** → sign in with GitHub → **New app**.
3. Settings:
   - Repository: `ShivenduShivu/MemoryLayer_for_Agents`
   - Branch: `main`
   - **Main file path: `dashboard/app.py`**
4. Click **Advanced settings → Secrets** and paste (TOML):
   ```toml
   COGNEE_MODE = "cloud"
   COGNEE_API_KEY = "your-cognee-cloud-key"
   COGNEE_CLOUD_URL = "https://your-tenant.aws.cognee.ai"
   PASSPORT_API_KEY = "dev-local-passport-key"
   ```
5. **Deploy.** You get a public URL like `https://<app>.streamlit.app`.

What works:
- **Immediately, no credit:** the provenance graph, timeline, and conflict log render from
  the built-in `dashboard/demo_seed.json` (a sample `demo/webapp` workspace).
- **With the secrets above:** the sidebar's live **Recall** and **Detect conflicts** buttons
  run against your real Cognee tenant.

Note: the first build installs the full stack (incl. Cognee) and can take a few minutes.
The visuals don't need Cognee — only the live buttons do (they degrade gracefully if secrets
are missing).

---

## Option B (optional) — API on Render · FREE

Hosts the FastAPI server (`/remember /recall /conflicts /ledger ...`) as a public endpoint.

1. https://render.com → **New → Web Service** → connect the repo.
2. Settings:
   - Runtime: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn passport.server:app --host 0.0.0.0 --port $PORT`  *(also in `Procfile`)*
3. Add environment variables (same keys as above).
4. Deploy. Free tier **sleeps after ~15 min idle** (first request cold-starts in ~30s).

---

## Security
- **Never commit `.env` or secrets.** Both platforms have a secret manager — use it.
- If your Cognee key was ever shared in plaintext, **rotate it** (platform.cognee.ai → API Keys)
  and update the secret.

## Free-tier summary
| Component | Host | Cost | Notes |
|---|---|---|---|
| Dashboard | Streamlit Community Cloud | Free | Public, self-seeded, always available |
| API | Render Web Service | Free | Sleeps when idle; cold start ~30s |
