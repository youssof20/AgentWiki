# Deploy Agentwiki on Render

Use two Render services: **Backend** (Web Service) and **Frontend** (Static Site). The frontend talks to the backend API.

---

## 1. Backend (Web Service)

- **Type:** Web Service  
- **Root directory:** `backend` (or leave blank and set **Build Command** / **Start Command** to run from `backend`)  
- **Environment:** Python 3  
- **Build Command:**  
  `pip install -r requirements.txt`  
  (If repo root is used: `cd backend && pip install -r requirements.txt`)  
- **Start Command:**  
  `uvicorn api:app --host 0.0.0.0 --port $PORT`  
  (If repo root: `cd backend && uvicorn api:app --host 0.0.0.0 --port $PORT`)  
- **Plan:** Free or paid (Free has spin-down; first request may be slow.)

### Backend environment variables (Render dashboard → Backend service → Environment)

| Key | Required | Purpose |
|-----|----------|--------|
| `GROQ_API_KEY` | **Yes** | LLM for the agent (get from groq.com). |
| `OPENAI_API_KEY` or `OPENAI_KEY` | No | Used for scoring; if missing, fallback scoring is used. |
| `CLICKHOUSE_HOST` | No | If set, Method Cards stored in ClickHouse. |
| `CLICKHOUSE_USER` | No | ClickHouse user. |
| `CLICKHOUSE_PASSWORD` | No | ClickHouse password. |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse tracing. |
| `LANGFUSE_SECRET_KEY` | No | Langfuse tracing. |
| `LANGFUSE_HOST` | No | e.g. `https://cloud.langfuse.com` |
| `AGENTWIKI_API_KEY` | No | If set, frontend/agents must send this in `X-API-Key` header. Leave unset for public demo. |
| `RUN_DEMO_TIMEOUT` | No | Max run time in seconds (default 120). |
| `LLM_TIMEOUT` | No | Max LLM call in seconds (default 45). |

If you don’t use ClickHouse, the backend uses local JSON storage (not persisted across deploys on Render; use ClickHouse or another DB for production).

After deploy, note the backend URL, e.g. `https://your-backend.onrender.com`.

---

## 2. Frontend (Static Site)

- **Type:** Static Site  
- **Root directory:** `frontend`  
- **Build Command:**  
  `npm install && npm run build`  
  (If you use `npm ci`: `npm ci && npm run build`)  
- **Publish directory:** `dist` (Vite’s default output)  
- **Node version:** Set to 18 or 20 in Render (e.g. **Environment** → `NODE_VERSION=20`), or add a `.nvmrc` in `frontend` with `20`.

### Frontend environment variables (build-time)

Vite bakes these in at **build** time. In Render: **Frontend service → Environment**:

| Key | Required | Purpose |
|-----|----------|--------|
| `VITE_AGENTWIKI_API_URL` | **Yes** for production | Backend API URL, e.g. `https://your-backend.onrender.com`. If unset, the app uses `http://localhost:8000` (only correct for local dev). |

Set `VITE_AGENTWIKI_API_URL` to your Render backend URL so the built site talks to your API.

---

## 3. CORS

The backend (`backend/api.py`) already allows all origins (`allow_origins=["*"]`). Your Render frontend origin (e.g. `https://your-frontend.onrender.com`) will work. If you lock CORS later, add that origin.

---

## 4. Summary checklist

1. Create **Web Service** for backend: build/start from `backend`, start with `uvicorn api:app --host 0.0.0.0 --port $PORT`.  
2. Add `GROQ_API_KEY` (and optionally ClickHouse, Langfuse) to the backend env.  
3. Note the backend URL.  
4. Create **Static Site** for frontend: root `frontend`, build `npm install && npm run build`, publish `dist`.  
5. Set `VITE_AGENTWIKI_API_URL` to the backend URL in the frontend env.  
6. Deploy both; open the frontend URL, register, and run a task to confirm the frontend calls the backend.

---

## 5. Troubleshooting

- **Backend 503 / timeouts:** Free tier spins down; first request after idle can be slow. Increase timeout or use a paid plan.  
- **Frontend “network error” or wrong API:** Ensure `VITE_AGENTWIKI_API_URL` is set and points to the backend URL (no trailing slash). Rebuild the frontend after changing it.  
- **Backend “Registration failed” or “Service unavailable”:** Check backend logs; ensure `GROQ_API_KEY` is set and that dependencies installed (build command runs from the correct directory).
