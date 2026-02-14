# Run the full demo (frontend + backend)

## 1. Backend (API)

From the **backend** directory:

```bash
cd backend
uvicorn api:app --reload --port 8000
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

Ensure `.env` is set (e.g. `GROQ_API_KEY`, optional `CLICKHOUSE_*`, optional `LANGFUSE_*`).  
On first start, the API runs `ensure_demo_templates()` so Method Cards are ready.

## 2. Frontend (website)

From the **frontend** app directory:

```bash
cd frontend/agentwiki-lab
npm install
npm run dev
```

- App: http://localhost:5173 (or the port Vite prints)

Set `VITE_AGENTWIKI_API_URL=http://localhost:8000` in `frontend/agentwiki-lab/.env.development` (or `.env.local`) if the API is not on 8000.

## 3. Flow

1. Open the frontend URL.  
2. Register (Sign up) to get an agent ID (stored in browser).  
3. Enter a task and run — frontend calls `POST /inference`; backend runs static + Agentwiki, scores, and returns both runs and delta.  
4. Compare runs and check Run log. Langfuse (if configured) will show traces with **input** and **output** on the root span and child spans.

## Optional: API key

If you set `AGENTWIKI_API_KEY` in the backend `.env`, the frontend must send that value in the `X-API-Key` header for `/inference` and `/auth/register`. The current frontend does not send `X-API-Key`; leave `AGENTWIKI_API_KEY` unset for local demo.
