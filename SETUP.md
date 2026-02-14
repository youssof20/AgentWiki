# Agentwiki — ClickHouse setup

We store Method Cards in **ClickHouse** only. Docs: [ClickHouse Documentation](https://clickhouse.com/docs).

**For a full setup guide (all services, real steps, why local save, RAG/vector):** see **[FULL-SETUP.md](FULL-SETUP.md)**.

If ClickHouse is unavailable (no env vars or connection failure), the app falls back to local `method_cards.json`.

---

## Install the Python driver (required)

From the project folder:

```bash
pip install clickhouse-connect
```

Or install everything: `pip install -r requirements.txt`

Without this you’ll see: `No module named 'clickhouse_connect'` and the app will use local JSON only.

---

## Where to go

- **ClickHouse Cloud:** https://clickhouse.com/cloud/  
  Sign up → Create a service → Get **host**, **username**, **password** (and optional port).
- Or use **self‑hosted** ClickHouse: https://clickhouse.com/docs/en/install

---

## Env vars (add to `.env`)

```env
CLICKHOUSE_HOST=your-host.clickhouse.cloud
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your-password
```

- For ClickHouse Cloud, **host** is usually something like `xxx.us-east-1.aws.clickhouse.cloud`.
- **Port** is often **9440** (secure). If your client requires a port in the host string, use `your-host:9440` or check the Cloud dashboard.

---

## Create the table (required)

The app runs `CREATE TABLE IF NOT EXISTS` on first insert, so you usually don’t need to do this manually. If you want to create it yourself (e.g. in the ClickHouse SQL console):

1. In **ClickHouse Cloud:** open your service → **SQL Console** (or “Playground”).
2. Run this SQL:

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

3. When you run the Agentwiki app and use “Run both (Static vs Agentwiki)”, Method Cards will be written to this table.

---

## How to see the data

- In **ClickHouse Cloud:** SQL Console → run:
  ```sql
  SELECT * FROM method_cards ORDER BY timestamp DESC LIMIT 20;
  ```
- Or use any ClickHouse client (e.g. `clickhouse-client`, DBeaver) and query `method_cards`.

---

## If you don’t see data

1. **Table missing:** Run the `CREATE TABLE` SQL above in the ClickHouse SQL console (or let the app create it on first insert).
2. **Env vars:** Ensure `CLICKHOUSE_HOST`, `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD` are set in `.env` and that the app is loading `.env`.
3. **Logs:** Run the app with `LOG_LEVEL=DEBUG` and check the terminal for “Saved Method Card … to ClickHouse” or “ClickHouse insert failed …”.
4. **Fallback:** If ClickHouse isn’t configured or fails, the app uses local `method_cards.json` in the project folder.

---

## Logging

Set in `.env` to see more detail:

```env
LOG_LEVEL=DEBUG
```

Then run the app (e.g. `streamlit run app.py`) and watch the terminal for:

- `Saved Method Card … to ClickHouse`
- `ClickHouse: method_cards table ensured`
- `ClickHouse insert failed …` / `Using local method_cards.json (ClickHouse unavailable)`

This helps confirm whether data is going to ClickHouse or local JSON.
