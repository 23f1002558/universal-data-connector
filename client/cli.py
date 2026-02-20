"""
Simple CLI client to talk to local backend.
"""
import argparse
import requests
import os

BASE = os.environ.get("BACKEND_URL", "http://localhost:8000")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--message", required=True)
    p.add_argument("--user-id", default="user-1")
    args = p.parse_args()

    r = requests.post(f"{BASE}/chat", json={"user_id": args.user_id, "message": args.message})
    print("Status:", r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)

if __name__ == "__main__":
    main()
