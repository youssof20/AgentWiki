"""
Smoke test: env load, imports, optional live Groq check.
Run: python test.py
"""
import os
import sys


def main() -> None:
    errors: list[str] = []

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError as e:
        errors.append(str(e))
        print("FAIL: pip install python-dotenv")
        sys.exit(1)

    required = ["GROQ_API_KEY"]
    optional = [
        "OPENAI_API_KEY", "OPENAI_KEY", "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "GEMINI_API_KEY",
        "CLICKHOUSE_HOST", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD",
        "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"FAIL: Missing env: {', '.join(missing)}")
        errors.append("Missing env")
    else:
        print("OK: Required env present")

    libs = ["groq", "openai", "google.generativeai", "clickhouse_connect", "fastapi"]
    for mod in libs:
        try:
            __import__(mod)
            print(f"OK: import {mod}")
        except ImportError as e:
            errors.append(f"Import {mod}: {e}")
            print(f"FAIL: import {mod} — {e}")

    if errors:
        print("\nFix: pip install -r requirements.txt and set .env (GROQ_API_KEY)")
        sys.exit(1)

    if os.getenv("GROQ_API_KEY"):
        try:
            from groq import Groq
            r = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            )
            text = (r.choices[0].message.content or "").strip()
            print(f"OK: Groq live — {text[:40]}")
        except Exception as e:
            print(f"WARN: Groq live check — {e}")

    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
