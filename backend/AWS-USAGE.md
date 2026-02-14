# AWS — How we could use it (before implementing)

We have **AWS keys** (hackathon-provided or your own). Here’s what we could use them for and whether it’s worth implementing.

---

## Options

### 1. **Backup Method Cards to S3** (recommended if we use AWS)

- **What:** After each write to ClickHouse (or local JSON), upload a snapshot or append-only log of Method Cards to an S3 bucket.
- **Why:** Durability and audit trail. If ClickHouse is down or we lose local state, we can restore from S3.
- **Effort:** Low. We already have `save_to_s3`-style logic in sponsor notes; call it from `save_card()` or on a timer.
- **Should we?** Yes if you want a durable backup and to show “AWS used” to judges. No if you’re fine with ClickHouse + local JSON only.

### 2. **Run artifacts / analytics**

- **What:** Store each run’s input, outputs, scores, and timestamps in S3 (e.g. JSON per run or a daily dump).
- **Why:** Offline analysis, replays, or building a leaderboard later.
- **Effort:** Medium. Need a clear schema and when to write (every run vs batch).
- **Should we?** Optional. Useful for “growth” and “product usage” story; not required for the demo.

### 3. **Static hosting / demo**

- **What:** Host the Streamlit app behind something like EC2, ECS, or Lambda + static front. Or put a demo video/docs on S3 + CloudFront.
- **Why:** Judges can open a link instead of running locally.
- **Effort:** Medium–high. Involves deployment and networking.
- **Should we?** Only if you have time and want a live URL; local run is enough for the pitch.

### 4. **Future: serverless API for Agentwiki**

- **What:** Lambda + API Gateway (or similar) exposing `GET /playbooks?q=...` and `POST /cards` so other agents call Agentwiki over HTTP.
- **Why:** Fits “library for other agents” — anyone can call the API without running our app.
- **Effort:** High. New API layer, auth, rate limits.
- **Should we?** Not for hackathon day; good post-demo roadmap.

---

## Recommendation

- **Implement now (if you want AWS in the demo):** **Option 1 — backup to S3.**  
  On each successful `save_card()` (or every N cards), write a backup to `s3://your-bucket/agentwiki/method_cards_backup.json` (or timestamped file). One extra call, no change to app flow. Shows “we use AWS for durability.”
- **Don’t implement now:** Options 2–4. Document them as “next steps” and keep the app functional without AWS.

If you say **“yes, add S3 backup”**, we can wire it: env vars `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `AWS_BUCKET_NAME` (and `AWS_SESSION_TOKEN` if present), and a single call after `save_card()` to upload the latest Method Cards (e.g. from ClickHouse or local JSON) to S3.
