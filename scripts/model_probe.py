"""Explicit, synthetic model acceptance probe; never reads workspace data."""

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="Send a small synthetic request to the configured AI Gateway model")
    args = parser.parse_args()
    model = os.environ.get("AI_GATEWAY_MODEL")
    token = os.environ.get("AI_GATEWAY_API_KEY") or os.environ.get("VERCEL_OIDC_TOKEN")
    if not args.live:
        print(json.dumps({"model": model, "credential_present": bool(token),
                          "live_request": False}))
        return 0
    if not model or not token:
        print(json.dumps({"ok": False, "reason": "model_or_credential_missing"}))
        return 1
    payload = {"model": model, "max_tokens": 80,
               "messages": [{"role": "system", "content": "This is a synthetic connectivity test."},
                            {"role": "user", "content": "Reply with READY and one short sentence about reviewing evidence."}]}
    request = urllib.request.Request(
        "https://ai-gateway.vercel.sh/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.load(response)
        text = body["choices"][0]["message"]["content"]
        ok = isinstance(text, str) and "READY" in text
        print(json.dumps({"ok": ok, "model": body.get("model", model),
                          "seconds": round(time.perf_counter() - started, 2),
                          "reply": text[:400] if isinstance(text, str) else "",
                          "usage": body.get("usage")}))
        return 0 if ok else 1
    except urllib.error.HTTPError as error:
        # The synthetic request has no workspace content. Return only the
        # provider's error code/message, with credentials redacted.
        detail = {}
        try:
            problem = json.loads(error.read(8192)).get("error", {})
            if isinstance(problem, dict):
                for key in ("code", "message"):
                    value = str(problem.get(key, "")).replace(token, "[redacted]")
                    detail[key] = re.sub(r"eyJ[\w-]+\.[\w-]+\.[\w-]+", "[redacted]", value)[:600]
        except (ValueError, AttributeError):
            pass
        print(json.dumps({"ok": False, "http_status": error.code,
                          "provider_error": detail,
                          "seconds": round(time.perf_counter() - started, 2)}))
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        print(json.dumps({"ok": False, "reason": "connection_or_response_error",
                          "seconds": round(time.perf_counter() - started, 2)}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
