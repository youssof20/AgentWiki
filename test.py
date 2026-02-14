"""
Smoke test before game day: env load, imports, optional live API check.
Run: python test.py
"""
import os
import sys

def main() -> None:
    errors: list[str] = []

    # 1. Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError as e:
        errors.append(f"python-dotenv not installed: {e}")
        print("FAIL: Install with pip install python-dotenv")
        sys.exit(1)

    # 2. Env vars (present or missing — we don't print values)
    expected_keys = [
        "GROQ_API_KEY",       # primary LLM
        "ELEVENLABS_API_KEY",
    ]
    optional_keys = [
        "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "GEMINI_API_KEY",
        "CLICKHOUSE_HOST", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD",
        "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST",
        "GITHUB_USERNAME", "REPO_NAME", "REPO_URL",
    ]
    missing = [k for k in expected_keys if not os.getenv(k)]
    if missing:
        print(f"FAIL: Missing required env vars: {', '.join(missing)}")
        errors.append("Missing env vars")
    else:
        print("OK: Required env vars present")
    for k in optional_keys:
        if os.getenv(k):
            print(f"OK: Optional {k} set")
        else:
            print(f"Note: Optional {k} not set (fallback LLM)")

    # 3. Imports
    libs = [
        ("streamlit", "st"),
        ("google.generativeai", "genai"),
        ("groq", "Groq"),
        ("elevenlabs", "ElevenLabs"),
        ("clickhouse_connect", "get_client"),
    ]
    for mod, attr in libs:
        try:
            __import__(mod)
            print(f"OK: import {mod}")
        except ImportError as e:
            errors.append(f"Import {mod}: {e}")
            print(f"FAIL: import {mod} — {e}")

    if errors:
        print("\nFix with: pip install -r requirements.txt")
        sys.exit(1)

    # 4. Live check: Groq (primary — must work for game day)
    if os.getenv("GROQ_API_KEY"):
        try:
            from groq import Groq
            r = Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Reply with exactly: GROQ WORKS"}],
            )
            text = (r.choices[0].message.content or "").strip()
            print(f"OK: Groq live check — {text[:60]}")
        except Exception as e:
            errors.append(f"Groq live check failed: {e}")
            print(f"FAIL: Groq live check — {e}")
    else:
        errors.append("GROQ_API_KEY not set (primary LLM)")
        print("FAIL: GROQ_API_KEY not set (primary for game day)")

    if errors:
        print("\nFix: pip install -r requirements.txt and set .env (especially GROQ_API_KEY)")
        sys.exit(1)

    print("\nSmoke test passed. Ready for game day.")

if __name__ == "__main__":
    main()
