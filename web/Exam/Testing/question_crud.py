import json
import datetime
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient
from bson.objectid import ObjectId

# ─── App & API setup ─────────────────────────────────────────────────────────────
app = Flask(__name__)
api = Api(app)

# ─── Custom JSON encoder for datetime ────────────────────────────────────────────
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)
app.json_encoder = CustomJSONEncoder

# ─── Load MongoDB config & client ────────────────────────────────────────────────
with open('local_config.json', 'r') as config_file:
    cfg = json.load(config_file)

client           = MongoClient(cfg['MONGO_CONFIG']['url'])
db               = client["codegnan_product"]
VERIF_COLL_NAME  = "InternVerifiedQuestions"
verif_collection = db[VERIF_COLL_NAME]

# ─── Helper for unified data parsing ─────────────────────────────────────────────
def parse_request_data():
    if request.is_json:
        return request.get_json(force=True)
    if request.form:
        return request.form.to_dict()
    return request.args.to_dict()

# ─── Question Resource ──────────────────────────────────────────────────────────
class Question(Resource):
    def get(self):
        subject    = request.args.get("subject", "").strip().lower()
        tags_param = request.args.get("tags", "")
        tags       = [t.strip().lower() for t in tags_param.split(",") if t.strip()]

        if not subject:
            return {"success": False, "message": "'subject' is required."}, 400
        if not tags:
            return {"success": False, "message": "'tags' cannot be empty."}, 400

        mcq_coll  = f"{subject}_mcq_test"
        code_coll = f"{subject}_code_test"
        query     = {"Tags": {"$in": tags}}

        mcq_qs  = list(db[mcq_coll].find(query))
        code_qs = list(db[code_coll].find(query))
        for q in mcq_qs + code_qs:
            q["questionId"] = str(q["_id"])
            del q["_id"]

        return {
            "success": True,
            "subject":       subject,
            "mcqCount":      len(mcq_qs),
            "codeCount":     len(code_qs),
            "mcqQuestions":  mcq_qs,
            "codeQuestions": code_qs
        }, 200

    def put(self):
        data  = parse_request_data()
        qid   = data.pop("questionId", None)
        subj  = data.pop("Subject", data.pop("subject", "")).strip().lower()
        qtype = data.pop("Question_Type", data.pop("questionType", "")).strip().lower()

        if not qid:
            return {"success": False, "message": "questionId is required."}, 400
        if not subj or not qtype:
            return {"success": False, "message": "Subject and Question_Type are required."}, 400

        if qtype == "mcq_test":
            coll_name = f"{subj}_mcq_test"
        elif qtype == "code_test":
            coll_name = f"{subj}_code_test"
        else:
            return {"success": False, "message": "Invalid Question_Type."}, 400

        if "Image_URL" in data:
            data["image_url"] = data.pop("Image_URL")

        try:
            res = db[coll_name].update_one(
                {"_id": ObjectId(qid)},
                {"$set": data}
            )
            if res.matched_count == 0:
                return {"success": False, "message": "No question found."}, 404
            return {"success": True, "message": "Question updated."}, 200
        except Exception as e:
            return {"success": False, "message": f"Update error: {e}"}, 500

    def delete(self):
        data  = parse_request_data()
        qid   = data.get("questionId")
        subj  = data.get("Subject", data.get("subject", "")).strip().lower()
        qtype = data.get("Question_Type", data.get("questionType", "")).strip().lower()

        if not qid:
            return {"success": False, "message": "questionId is required."}, 400
        if not subj or not qtype:
            return {"success": False, "message": "Subject and Question_Type are required."}, 400

        if qtype == "mcq_test":
            coll_name = f"{subj}_mcq_test"
        elif qtype == "code_test":
            coll_name = f"{subj}_code_test"
        else:
            return {"success": False, "message": "Invalid Question_Type."}, 400

        try:
            # 1) Delete from the subject-specific collection
            res = db[coll_name].delete_one({"_id": ObjectId(qid)})
            if res.deleted_count == 0:
                return {"success": False, "message": "No question found."}, 404

            # 2) Also purge any creation/verification records for that question
            verif_collection.delete_many({"questionId": ObjectId(qid)})

            return {"success": True, "message": "Question and related verifications deleted."}, 200
        except Exception as e:
            return {"success": False, "message": f"Deletion error: {e}"}, 500