from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import requests
import time
import hashlib
from typing import Dict, Tuple, List, Any

ONECOMPILER_ACCESS_TOKEN = "codegnan8sm0omjk85hndysxodqvvna7h3p1j83vr1fh6217ltyhzn7zkrfzujaj1cbn0z4z"
API_URL = f"https://onecompiler.com/api/v1/run?access_token={ONECOMPILER_ACCESS_TOKEN}"
REQ_TIMEOUT = 15                # seconds
CACHE_TTL   = 30 * 60           # 30 minutes

# ------------------------------------------------------------------  CACHE
_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}     # key -> (expires_at, result)

def cache_get(key: str) -> Dict[str, Any]:
    rec = _cache.get(key)
    if not rec:
        return None
    expires_at, val = rec
    if expires_at < time.time():
        _cache.pop(key, None)
        return None
    return val

def cache_put(key: str, val: Dict[str, Any]) -> None:
    _cache[key] = (time.time() + CACHE_TTL, val)

# ------------------------------------------------------------------  HELPERS
LANG_EXT = {
    "python": "py", "python2": "py", "python3": "py",
    "javascript": "js", "node": "js",
    "java": "java", "c": "c", "c++": "cpp", "cpp": "cpp",
    "ruby": "rb", "go": "go"
}

def normalize_newlines(text: Any) -> str:
    return str(text).replace("↵", "\n").replace("\r\n", "\n").replace("\r", "\n")

def language_to_ext(lang: str) -> Tuple[str, str]:
    lang_l = lang.lower()
    if lang_l == "c++":
        lang_l = "cpp"
    if lang_l not in LANG_EXT:
        raise ValueError(f"Unsupported language '{lang}'")
    return lang_l, LANG_EXT[lang_l]

def run_on_onecompiler(src: str, lang: str, stdin: Any) -> Dict[str, Any]:
    lang_l, ext = language_to_ext(lang)
    payload = {
        "language": lang_l,
        "stdin": stdin if isinstance(stdin, list) else str(stdin),
        "files": [{"name": f"Main.{ext}", "content": src}]
    }
    r = requests.post(API_URL, json=payload, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    return r.json()

def hash_submission(qid: str, lang: str, code: str) -> str:
    h = hashlib.sha1()
    h.update(qid.encode())
    h.update(lang.lower().encode())
    h.update(code.encode())
    return h.hexdigest()

def verdict(actual: str, expected: str) -> str:
    return "Passed" if actual.strip() == expected.strip() else "Failed"

# ------------------------------------------------------------------  RESOURCE
class Submissions(Resource):
    def post(self):
        data = request.get_json() or {}
        print("Recived data:", data)
        qid          = data.get("question_id")
        src_code     = data.get("source_code", "")
        lang         = data.get("language", "")
        sample_in    = data.get("sample_input")
        sample_out   = normalize_newlines(data.get("sample_output", ""))
        hidden_cases = data.get("hidden_test_cases") or []
        custom_on    = data.get("custom_input_enabled")
        custom_in    = data.get("custom_input")

        # Basic validation
        if not all([qid, src_code.strip(), lang]):
            return {"error": "Missing required fields"}, 400

        # Cache lookup
        ck = hash_submission(qid, lang, src_code)
        if not custom_on:
            cached = cache_get(ck)
            if cached:
                cached["from_cache"] = True
                return cached, 200

        results: List[Dict[str, Any]] = []

        # 1. Custom-input mode
        if custom_on:
            rc = run_on_onecompiler(src_code, lang, custom_in)
            out = normalize_newlines(rc.get("stdout") or rc.get("stderr") or "No output")
            results.append({
                "input": custom_in,
                "expected_output": "",
                "actual_output": out,
                "status": "Custom Input",
                "type": "custom"
            })
            return {"message": "Submission processed", "results": results}, 200

        # 2. Sample test
        if sample_in is not None:
            rc = run_on_onecompiler(src_code, lang, sample_in)
            out = normalize_newlines(rc.get("stdout") or rc.get("stderr") or "No output")
            status = verdict(out, sample_out)
            results.append({
                "input": sample_in,
                "expected_output": sample_out,
                "actual_output": out,
                "status": status,
                "type": "sample"
            })
            if status == "Failed":
                # pad skipped hidden tests
                total_hidden = len(hidden_cases)
                for idx in range(total_hidden):
                    tc = hidden_cases[idx]
                    results.append({
                        "index": idx,
                        "input": tc.get("Input"),
                        "expected_output": normalize_newlines(str(tc.get("Output", ""))),
                        "actual_output": None,
                        "status": "Skipped",
                        "type": "hidden"
                    })
                return {"message": "Submission processed", "results": results}, 200

        # 3. Hidden tests (fail-fast)
        ran_hidden = 0
        for idx, tc in enumerate(hidden_cases):
            if not tc:
                continue
            inp = tc.get("Input")
            exp = normalize_newlines(str(tc.get("Output", "")))
            rc  = run_on_onecompiler(src_code, lang, inp)
            out = normalize_newlines(rc.get("stdout") or rc.get("stderr") or "No output")
            status = verdict(out, exp)
            results.append({
                "index": idx,
                "input": inp,
                "expected_output": exp,
                "actual_output": out,
                "status": status,
                "type": "hidden"
            })
            ran_hidden += 1
            if status == "Failed":
                break

        # 4. Pad any remaining hidden tests as skipped
        total_hidden = len(hidden_cases)
        for idx in range(ran_hidden, total_hidden):
            tc = hidden_cases[idx]
            results.append({
                "index": idx,
                "input": tc.get("Input"),
                "expected_output": normalize_newlines(str(tc.get("Output", ""))),
                "actual_output": None,
                "status": "Skipped",
                "type": "hidden"
            })

        # Cache & respond
        resp = {"message": "Submission processed", "results": results}
        cache_put(ck, resp)
        print("response", resp)
        return resp, 200