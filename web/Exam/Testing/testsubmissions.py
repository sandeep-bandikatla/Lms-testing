# test_submission.py

import json
import datetime
import requests
from flask import request
from flask_restful import Resource
from pymongo import MongoClient
from bson.objectid import ObjectId

# ─── 1. Config & DB setup ───────────────────────────────────────────────────
with open("local_config.json", "r") as f:
    cfg = json.load(f)

client     = MongoClient(cfg["MONGO_CONFIG"]["url"])
db         = client["codegnan_product"]
VERIF_COLL = "InternVerifiedQuestions"
db[VERIF_COLL].create_index([("id", 1), ("questionId", 1)], unique=True)

# ─── 1.a OneCompiler token ──────────────────────────────────────────────────
ONECOMPILER_ACCESS_TOKEN = "codegnan8sm0omjk85hndysxodqvvna7h3p1j83vr1fh6217ltyhzn7zkrfzujaj1cbn0z4z"

# ─── 2. Helpers ────────────────────────────────────────────────────────────
def normalize_newlines(text):
    if isinstance(text, str):
        return text.replace("↵", "\n") \
                   .replace("\r\n", "\n") \
                   .replace("\r", "\n")
    return str(text)

def process_submission(source_code, language, input_data):
    """
    Run one or more inputs through OneCompiler.
    """
    api_url = (
      "https://onecompiler.com/api/v1/run"
      f"?access_token={ONECOMPILER_ACCESS_TOKEN}"
    )
    lang = (language or "").lower()
    if lang == "c++":
        lang = "cpp"
    ext_map = {
      "python":"py", "python2":"py", "javascript":"js",
      "java":"java",  "c":"c",        "cpp":"cpp",
      "ruby":"rb",    "go":"go"
    }
    ext = ext_map.get(lang, "txt")

    def make_payload(stdin):
        return {
            "language": lang,
            "stdin":    str(stdin),
            "files":    [{"name": f"Main.{ext}", "content": source_code}]
        }

    payload = (
        [make_payload(i) for i in input_data]
        if isinstance(input_data, list)
        else make_payload(input_data)
    )

    resp = requests.post(api_url, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()

def _total_questions(subject: str, tag: str) -> int:
    mcq  = db[f"{subject}_mcq_test"].count_documents({"Tags": tag})
    code = db[f"{subject}_code_test"].count_documents({"Tags": tag})
    return mcq + code

def _error(msg: str, code: int = 400):
    return {"success": False, "message": msg}, code

def mark_subtopic_done(intern_id: str, subject: str, tag: str):
    """
    Case‑insensitive lookup of the subject key, then flip
    the matching SubTopics[].status to True.
    """
    tester = db["Testers"].find_one(
        {"id": intern_id},
        {"curriculumTable": 1}
    )
    if not tester:
        return

    ct = tester.get("curriculumTable", {})
    # find the real key (e.g. "Python" vs "python")
    subject_key = next(
        (k for k in ct.keys() if k.lower() == subject.lower()),
        None
    )
    if subject_key is None:
        return

    for qid, block in ct[subject_key].items():
        subs = block.get("SubTopics", [])
        for idx, st in enumerate(subs):
            if st.get("tag") == tag:
                path = f"curriculumTable.{subject_key}.{qid}.SubTopics.{idx}.status"
                db["Testers"].update_one(
                    {"id": intern_id},
                    {"$set": {path: True}}
                )
                return

# ─── 3. Resource ───────────────────────────────────────────────────────────
class TestSubmission(Resource):
    """
    POST /api/v1/test-submission
      • Runs payload tests (preferred) or DB tests (fallback).
      • Auto‑verifies code_test and upserts into InternVerifiedQuestions.
      • Updates Testers.curriculumTable via mark_subtopic_done().
    """
    def post(self):
        data         = request.get_json(force=True)
        intern_id    = data.get("internId")
        raw_qid      = data.get("question_id")
        source_code  = data.get("source_code")
        language     = data.get("language")
        problem_type = (data.get("type") or "").strip().lower()

        # ── 3.1 Validate required fields ───────────────────────────────
        if not (intern_id and raw_qid and source_code and language and problem_type):
            return _error("internId, question_id, source_code, language and type are required.")

        try:
            qid = ObjectId(raw_qid)
        except:
            return _error("question_id must be a valid ObjectId.")

        # ── 3.2 Fetch question metadata ───────────────────────────────
        candidate = [
            c for c in db.list_collection_names()
            if c.endswith(f"_{problem_type}")
        ]
        question = None
        for coll in candidate:
            question = db[coll].find_one(
                {"_id": qid},
                {
                    "Hidden_Test_Cases": 1,
                    "Sample_Input":      1,
                    "Sample_Output":     1,
                    "Tags":              1,
                    "Subject":           1
                }
            )
            if question:
                break
        if not question:
            return _error("Question not found.", 404)

        # ── 3.3 Prepare tests ──────────────────────────────────────────
        payload_tests = data.get("hidden_test_cases")
        sample_in     = data.get("sample_input", question.get("Sample_Input"))
        sample_out    = normalize_newlines(
                           str(data.get("sample_output", question.get("Sample_Output", "")))
                        ).strip()
        tag           = question.get("Tags")
        subject       = question.get("Subject", "").lower()

        results = []

        if payload_tests is not None:
            # sample vs hidden
            sample_cases = [tc for tc in payload_tests if tc.get("type") == "sample"]
            hidden_cases = [tc for tc in payload_tests if tc.get("type") != "sample"]

            def run_one(tc):
                inp    = tc["Input"]
                expect = normalize_newlines(str(tc.get("Output", ""))).strip()
                raw    = process_submission(source_code, language, inp)
                resp   = raw if isinstance(raw, dict) else raw[-1]
                out    = resp.get("stdout") or resp.get("stderr") or ""
                actual = normalize_newlines(out).strip()
                return {
                    "input":           inp,
                    "expected_output": expect,
                    "actual_output":   actual,
                    "status":          "Passed" if actual == expect else "Failed",
                    "type":            tc.get("type", "hidden")
                }

            for tc in sample_cases + hidden_cases:
                results.append(run_one(tc))

        else:
            # run DB sample test
            if sample_in is not None:
                raw  = process_submission(source_code, language, sample_in)
                resp = raw if isinstance(raw, dict) else raw[-1]
                out  = resp.get("stdout") or resp.get("stderr") or ""
                actual = normalize_newlines(out).strip()
                results.append({
                    "input":           sample_in,
                    "expected_output": sample_out,
                    "actual_output":   actual,
                    "status":          "Passed" if actual == sample_out else "Failed",
                    "type":            "sample"
                })

            # run all hidden tests in batch
            hidden_tests = question.get("Hidden_Test_Cases", [])
            inputs      = [tc["Input"] for tc in hidden_tests if tc.get("Input") is not None]
            if inputs:
                batch = process_submission(source_code, language, inputs)
                batch = batch if isinstance(batch, list) else [batch]
                for idx, resp in enumerate(batch):
                    tc     = hidden_tests[idx]
                    expect = normalize_newlines(str(tc.get("Output", ""))).strip()
                    out    = resp.get("stdout") or resp.get("stderr") or ""
                    actual = normalize_newlines(out).strip()
                    results.append({
                        "input":           tc["Input"],
                        "expected_output": expect,
                        "actual_output":   actual,
                        "status":          "Passed" if actual == expect else "Failed",
                        "type":            "hidden"
                    })

        # ── 3.4 Auto‑verify & update curriculum ─────────────────────────
        verified = False
        if problem_type == "code_test":
            hidden_only = [r for r in results if r["type"] == "hidden"]
            if hidden_only and all(r["status"] == "Passed" for r in hidden_only):
                verified = True
                now = datetime.datetime.utcnow()
                record = {
                    "id":           intern_id,
                    "questionId":   qid,
                    "questionType": problem_type,
                    "subject":      subject,
                    "tag":          tag,
                    "verified":     True,
                    "timestamp":    now,
                    "sourceCode":   source_code
                }
                db[VERIF_COLL].update_one(
                    {"id": intern_id, "questionId": qid},
                    {"$set": record},
                    upsert=True
                )
                mark_subtopic_done(intern_id, subject, tag)

        print("Results:", results)
        return {
            "message":  "Submission processed",
            "results":  results,
            "verified": verified
        }, 200
