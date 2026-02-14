# Agentwiki — Full setup guide (all services, real steps, real outputs)

This guide covers **every service** the app uses, **where to go**, **what to run**, and **why data was saving locally** instead of sponsor ClickHouse. No fluff — actual commands and expected outputs.

---

## Why was data saving to `method_cards.json` instead of ClickHouse?

**Short answer:** ClickHouse Cloud expects **hostname + port**, not a full URL. If `CLICKHOUSE_HOST` was set to something like `https://xxx.clickhouse.cloud:8443`, the Python client was given that whole string as the host and the connection failed, so the app fell back to local JSON.

**What we fixed in code:** The app now **parses** `CLICKHOUSE_HOST`:
- Strips `https://` or `http://`
- Splits `hostname:port` and uses port **8443** for Cloud if not specified
- Passes **hostname only** and **port** (and `secure=True` for 8443) to the driver

**What you do:** Set `CLICKHOUSE_HOST` to one of:
- `your-service.me-central-1.aws.clickhouse.cloud` (recommended), or
- `your-service.me-central-1.aws.clickhouse.cloud:8443`, or
- `https://your-service.me-central-1.aws.clickhouse.cloud:8443` (we strip scheme and port)

Then ensure `CLICKHOUSE_USER` and `CLICKHOUSE_PASSWORD` are set. Restart the app; new Method Cards should go to ClickHouse. Check logs for:
```text
Saved Method Card xxxxx to ClickHouse
```
If you still see:
```text
Using local method_cards.json (ClickHouse unavailable)
ClickHouse client failed: ...
```
then the failure message tells you why (e.g. wrong password, network, SSL).

---

## Architecture: keyword retrieval vs RAG / vector / ANN

| Aspect | Current Agentwiki | RAG-style (vector + ANN) |
|--------|-------------------|---------------------------|
| **Storage** | ClickHouse: structured table `method_cards` (id, task_intent, plan, tags, outcome_score, etc.) | Same + embedding column (e.g. `Array(Float32)`) |
| **Retrieval** | **Keyword / substring**: search in `task_intent`, `plan`, `tags`; sort by score and time | **Vector similarity**: embed query and stored text; approximate nearest neighbour (ANN) by cosine/L2 |
| **Use case** | “Find playbooks that mention this task” (exact/substring match) | “Find playbooks semantically similar to this task” (embedding similarity) |

**Current:** We do **not** use vector storage or ANN. We use ClickHouse as a **structured store** and filter by text (substring) in Python after fetching the last 50 rows by score/time. So: **sponsor ClickHouse is used for storage and querying**, but retrieval is **keyword-based**, not RAG/vector/ANN.

**RAG / vector / ANN with ClickHouse:** ClickHouse supports [vector search](https://clickhouse.com/docs/use-cases/AI/qbit-vector-search): columns like `Array(Float32)` for embeddings, functions like `cosineDistance`, `L2Distance`, and indexes (e.g. for approximate NN). So you *can* build a RAG pipeline: embed `task_intent` (and optionally `plan`), store the vector in ClickHouse, and run ANN queries. That would be an **optional upgrade** on top of the current keyword retrieval.

**Summary:**  
- **Storage:** ClickHouse (sponsor).  
- **Retrieval today:** Keyword/substring, no vectors, no ANN.  
- **RAG/vector/ANN:** Possible with ClickHouse; not implemented in the app yet; see “Optional: RAG / vector search in ClickHouse” below.

---

## Services we use (in code)

| Service | Used for | Required? |
|---------|----------|-----------|
| **Groq** | LLM (agent + evaluator) | Yes (primary) |
| **ElevenLabs** | Voice (optional in UI) | No |
| **ClickHouse** | Method Cards storage + query | Yes (we want sponsor DB) |
| **Langfuse** | LLM tracing (optional) | No |
| **AWS** | Backup/storage (optional) | No |

---

## 1. Groq (LLM)

**Where:** https://console.groq.com/  
**Get:** API key (e.g. Keys → Create API Key).

**.env:**
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

**Verify (real output):**
```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from groq import Groq
r = Groq().chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':'Say OK'}])
print(r.choices[0].message.content)
"
```
Expected: something like `OK` or a short reply (not an error).

---

## 2. ClickHouse (sponsor — Method Cards)

**Where:** https://clickhouse.com/cloud/  
**Do:** Sign up → Create service → choose region → set password. Note **host**, **user** (usually `default`), **password**.

**Docs:** https://clickhouse.com/docs

**.env:**
```env
CLICKHOUSE_HOST=your-service.region.aws.clickhouse.cloud
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your-password
```
Use **hostname only** (no `https://`, no `:8443`). The app will use port **8443** and HTTPS automatically. If you prefer to set port explicitly:
```env
CLICKHOUSE_PORT=8443
```

**Create table (once).** Either let the app create it on first insert, or in ClickHouse Cloud SQL Console run:

```sql
CREATE TABLE IF NOT EXISTS method_cards (
    id String,
    timestamp String,
    task_intent String,
    context String,
    plan String,
    tool_calls String,
    mistakes String,
    fixes String,
    outcome_score Float64,
    tags String
) ENGINE = MergeTree()
ORDER BY (timestamp, id);
```

**Verify (real output).** In SQL Console:
```sql
SELECT count() FROM method_cards;
```
Expected: `0` at first, then increases after you run the app and “Run both”.

**From Python (real output):**
```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from memory import get_clickhouse_client
c = get_clickhouse_client()
print('OK' if c else 'FAIL')
if c: print(c.query('SELECT 1').result_rows)
"
```
Expected: `OK` and `[(1,)]`. If `FAIL` or exception, fix host/user/password/port (see “Why was data saving locally?” above).

---

## 3. ElevenLabs (voice, optional)

**Where:** https://elevenlabs.io/  
**Get:** API key (Profile → API Key).

**.env:**
```env
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxx
```

**Verify:** The app uses this only if you add voice playback; no extra CLI check needed.

---

## 4. Langfuse (tracing, optional)

**Where:** https://cloud.langfuse.com/  
**Get:** Project → API keys (public + secret).

**.env:**
```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 5. AWS (optional)

**Where:** Hackathon-provided keys or your own.  
**.env:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, optional `AWS_SESSION_TOKEN`, `AWS_BUCKET_NAME`.

---

## Full local run (actual commands)

**1. Clone / open project, create venv, install deps:**
```bash
cd c:\Users\youss\OneDrive\Documents\RuyaHackathon
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**2. Copy `.env.example` to `.env` and fill (at least GROQ_API_KEY, CLICKHOUSE_HOST, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD).**

**3. Smoke test:**
```bash
python test.py
```
Expected (example):
```text
OK: Required env vars present
OK: Optional CLICKHOUSE_HOST set
...
OK: import clickhouse_connect
OK: Groq live check — GROQ WORKS
Smoke test passed. Ready for game day.
```

**4. Run app:**
```bash
streamlit run app.py
```
**5. In UI:** Enter a task → “Run both (Static vs Agentwiki)”. In terminal you should see:
```text
Saved Method Card xxxxx to ClickHouse
```
If you see `Using local method_cards.json (ClickHouse unavailable)` then ClickHouse connection failed; fix host/user/password and parsing (see top of this doc).

**6. Confirm in ClickHouse:** In SQL Console:
```sql
SELECT id, task_intent, outcome_score, timestamp FROM method_cards ORDER BY timestamp DESC LIMIT 5;
```
You should see the rows you just wrote.

---

## Optional: RAG / vector search in ClickHouse

We do **not** use vector storage or ANN in the app today. If you want to add RAG-style retrieval (embedding + ANN) using the same sponsor ClickHouse:

**1. Add an embedding column and optional index.** In ClickHouse SQL Console (example with Float32 vectors; dimension 384 or 768 depending on your model):

```sql
ALTER TABLE method_cards ADD COLUMN IF NOT EXISTS embedding Array(Float32);
```

**2. Generate embeddings** for `task_intent` (and optionally `plan`) with your chosen model (e.g. sentence-transformers, or an API that returns a vector), and **insert** them into `method_cards` along with the existing columns.

**3. Query by similarity** (e.g. cosine distance, approximate NN). Example for exact search (no index):

```sql
SELECT id, task_intent, outcome_score,
       cosineDistance(embedding, [0.1, ...]) AS dist
FROM method_cards
WHERE length(embedding) > 0
ORDER BY dist
LIMIT 5;
```

For **ANN** (fast approximate nearest neighbour), use ClickHouse’s vector index support (e.g. HNSW) as in the [vector search docs](https://clickhouse.com/docs/use-cases/AI/qbit-vector-search); that typically involves a specific table engine or index type and depends on your ClickHouse version.

**4. In the app:** You’d add a path that (a) embeds the user query, (b) runs a similarity query in ClickHouse, (c) returns the top‑k Method Cards. That would be a second retrieval path alongside the current keyword path.

---

## Checklist: “Data must go to ClickHouse”

- [ ] `CLICKHOUSE_HOST` = hostname only (e.g. `xxx.me-central-1.aws.clickhouse.cloud`) or URL that we can parse (we strip scheme and port).
- [ ] `CLICKHOUSE_USER` and `CLICKHOUSE_PASSWORD` set in `.env`.
- [ ] `pip install clickhouse-connect` (or `pip install -r requirements.txt`).
- [ ] Table `method_cards` exists (app creates it on first insert, or you ran the `CREATE TABLE` above).
- [ ] No firewall blocking outbound **8443** to your ClickHouse Cloud host.
- [ ] After “Run both”, logs show `Saved Method Card ... to ClickHouse` and `SELECT * FROM method_cards` in SQL Console returns rows.

If all are true and you still see local save, the log line `ClickHouse client failed: ...` or `ClickHouse insert failed: ...` is the next place to look (e.g. SSL, auth, or network).
