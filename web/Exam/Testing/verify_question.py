# verify_question.py

import json
from datetime import datetime
from flask import request
from flask_restful import Resource
from pymongo import MongoClient
from bson.objectid import ObjectId

# ─── Config & DB setup ────────────────────────────────────────────────────────
with open("local_config.json", "r") as f:
    cfg = json.load(f)

client           = MongoClient(cfg["MONGO_CONFIG"]["url"])
db               = client["codegnan_product"]
VERIF_COLL_NAME  = "InternVerifiedQuestions"
verif_collection = db[VERIF_COLL_NAME]
verif_collection.create_index([("id", 1), ("questionId", 1)], unique=True)

# ─── Helpers ─────────────────────────────────────────────────────────────────
def _error(msg: str, code: int = 400):
    return {"success": False, "message": msg}, code

def _total_questions(subject: str, tag: str) -> int:
    mcq_count  = db[f"{subject}_mcq_test"].count_documents({"Tags": tag})
    code_count = db[f"{subject}_code_test"].count_documents({"Tags": tag})
    return mcq_count + code_count

def mark_subtopic_done(intern_id: str, subject: str, tag: str):
    tester = db["Testers"].find_one(
        {"id": intern_id},
        {"curriculumTable": 1}
    )
    if not tester:
        return

    ct = tester.get("curriculumTable", {})
    subject_key = next((k for k in ct if k.lower() == subject.lower()), None)
    if subject_key is None:
        return

    for block_id, block in ct[subject_key].items():
        for idx, st in enumerate(block.get("SubTopics", [])):
            if st.get("tag") == tag:
                path = f"curriculumTable.{subject_key}.{block_id}.SubTopics.{idx}.status"
                db["Testers"].update_one(
                    {"id": intern_id},
                    {"$set": {path: True}}
                )
                return

# ─── Resource ────────────────────────────────────────────────────────────────
class VerifyQuestion(Resource):
    """
    PUT  /api/v1/verify-question
      Manually toggle MCQ or code-test questions (and persist sourceCode for code tests).

    GET  /api/v1/verify-question
      List all creation+verification events for an intern.
    """

    def put(self):
        data      = request.get_json(force=True)
        intern_id = data.get("internId")
        qid_raw   = data.get("questionId")
        qtype     = (data.get("questionType") or "").strip().lower()
        subject   = (data.get("subject")      or "").strip().lower()
        tag       = (data.get("tag")          or "").strip()
        verified  = bool(data.get("verified", True))

        # ─── validate input ──────────────────────────────────────────────
        if not all([intern_id, qid_raw, qtype, subject, tag]):
            return _error("internId, questionId, questionType, subject & tag are required.", 400)

        # allow both MCQ and code tests
        if qtype not in ("mcq_test", "code_test"):
            return _error("Manual verification only supports mcq_test and code_test.", 422)

        try:
            qid = ObjectId(qid_raw)
        except:
            return _error("questionId must be a valid ObjectId.", 400)

        now = datetime.utcnow()

        # ─── build update payload ───────────────────────────────────────
        update_fields = {
            "verified":   verified,
            "verifiedAt": now
        }
        # persist sourceCode if provided (for code tests)
        if qtype == "code_test" and data.get("sourceCode"):
            update_fields["sourceCode"] = data["sourceCode"]

        # ─── flip verified flag & set verifiedAt (& sourceCode) ─────────
        result = verif_collection.update_one(
            {"id": intern_id, "questionId": qid},
            {"$set": update_fields}
        )
        if result.matched_count == 0:
            return _error("No creation record found for this internId/questionId.", 404)

        # ─── if fully verified for this tag, mark curriculum done ─────────
        total_q    = _total_questions(subject, tag)
        verified_q = verif_collection.count_documents({
            "id":       intern_id,
            "subject":  subject,
            "tag":      tag,
            "verified": True
        })
        if total_q and verified_q >= total_q and verified:
            try:
                mark_subtopic_done(intern_id, subject, tag)
            except Exception as e:
                print(f"[WARNING] Couldn't update curriculumTable: {e}")

        return {
            "success": True,
            "verification": {
                "internId":     intern_id,
                "questionId":   qid_raw,
                "questionType": qtype,
                "subject":      subject,
                "tag":          tag,
                "verified":     verified,
                "verifiedAt":   now.isoformat() + "Z"
            }
        }, 200

    def get(self):
        intern_id = request.args.get("internId")
        if not intern_id:
            return _error("internId query param is required.", 400)

        match = {"id": intern_id}
        subj  = request.args.get("subject")
        if subj:
            match["subject"] = subj.strip().lower()

        cursor  = verif_collection.find(match, {"_id": 0})
        results = []
        for rec in cursor:
            results.append({
                "internId":     rec["id"],
                "questionId":   str(rec["questionId"]),
                "questionType": rec.get("questionType"),
                "subject":      rec.get("subject"),
                "tag":          rec.get("tag"),
                "createdAt":    rec.get("createdAt").isoformat() + "Z" if rec.get("createdAt") else None,
                "verified":     rec.get("verified", False),
                "verifiedAt":   rec.get("verifiedAt").isoformat() + "Z" if rec.get("verifiedAt") else None,
                "sourceCode":   rec.get("sourceCode")  # include sourceCode in GET response
            })

        return {"success": True, "verifications": results}, 200
