import json
from datetime import datetime, timedelta
from flask import request, jsonify
from flask_restful import Resource
from pymongo import MongoClient

# ─── Config & DB setup ────────────────────────────────────────────────────────
with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

client     = MongoClient(config_data['MONGO_CONFIG']['url'])
db         = client["codegnan_product"]
VERIF_COLL = db["InternVerifiedQuestions"]

def error_response(message, status_code=400):
    response = jsonify({"success": False, "message": message})
    response.status_code = status_code
    return response

class TestUploadQuestions(Resource):
    def post(self):
        payload   = request.get_json(force=True)
        questions = payload if isinstance(payload, list) else [payload]
        if not questions:
            return error_response("Expected a question object or a list.", 400)

        now            = datetime.utcnow()
        today          = now.date()
        start_of_day   = datetime(today.year, today.month, today.day)
        end_of_day     = start_of_day + timedelta(days=1)
        last_intern_id = None
        last_subject   = None
        last_tag       = None

        try:
            for q in questions:
                intern_id     = q.get("internId")
                last_intern_id = intern_id
                question_type = str(q.get('Question_Type', '')).lower()
                subject       = str(q.get('Subject', '')).lower()
                tag           = str(q.get('Tags', '')).lower()
                last_subject  = subject
                last_tag      = tag  # e.g. "day-6:1"

                # ─── validate essentials ──────────────────────────────
                if not intern_id:
                    return error_response("Missing 'internId' field.", 422)
                if not question_type.endswith('_test'):
                    return error_response("Question_Type must end with '_test'.", 422)
                if not subject:
                    return error_response("Missing 'Subject' field.", 422)

                # ─── build question document ──────────────────────────
                if question_type == "mcq_test":
                    if 'Score' not in q:
                        return error_response("MCQ questions must include 'Score'.", 422)
                    collection = f"{subject}_mcq_test"
                    doc = {
                        "Question_No":      q.get('Question_No'),
                        "Question_Type":    question_type,
                        "Subject":          subject,
                        "Question":         q.get('Question', ''),
                        "Options": {
                            "A": q.get('A', ''),
                            "B": q.get('B', ''),
                            "C": q.get('C', ''),
                            "D": q.get('D', ''),
                        },
                        "Correct_Option":   q.get('Correct_Option', ''),
                        "Score":            q.get('Score'),
                        "Difficulty":       q.get('Difficulty', ''),
                        "Tags":             tag,
                        "Text_Explanation": q.get('Text_Explanation', ''),
                        "Explanation_URL":  q.get('Explanation_URL', ''),
                        "image_url":        q.get('Image_URL', '')
                    }
                else:
                    collection = f"{subject}_code_test"
                    hidden = []
                    for i in range(1, 5):
                        inp = q.get(f'Hidden_Test_case_{i}_Input')
                        out = q.get(f'Hidden_Test_case_{i}_Output')
                        if inp is not None or out is not None:
                            hidden.append({"Input": inp or "", "Output": out or ""})
                    doc = {
                        "Question_No":       q.get('Question_No'),
                        "Question_Type":     question_type,
                        "Subject":           subject,
                        "Question":          q.get('Question', ''),
                        "Sample_Input":      q.get('Sample_Input', ''),
                        "Sample_Output":     q.get('Sample_Output', ''),
                        "Constraints":       q.get('Constraints', ''),
                        "Hidden_Test_Cases": hidden,
                        "Score":             q.get('Score'),
                        "Tags":              tag,
                        "Difficulty":        q.get('Difficulty', ''),
                        "Text_Explanation":  q.get('Text_Explanation', ''),
                        "Explanation_URL":   q.get('Explanation_URL', '')
                    }

                # ─── insert into subject-type collection ───────────────
                doc = {k: v for k, v in doc.items() if v not in (None, "", [], {})}
                if "Options" in doc:
                    doc["Options"] = {k: v for k, v in doc["Options"].items() if v}
                res = db[collection].insert_one(doc)
                new_qid = res.inserted_id

                # ─── record creation event ─────────────────────────────
                creation_record = {
                    "id":           intern_id,
                    "questionId":   new_qid,
                    "questionType": question_type,
                    "subject":      subject,
                    "tag":          tag,
                    "verified":     False,
                    "createdAt":    now
                }
                VERIF_COLL.update_one(
                    {"id": intern_id, "questionId": new_qid},
                    {"$setOnInsert": creation_record},
                    upsert=True
                )

            # ─── count only those with exactly that tag and subject ──
            mcq_created_for_tag  = VERIF_COLL.count_documents({
                "id":           last_intern_id,
                "questionType": "mcq_test",
                "subject":      last_subject,
                "tag":          last_tag
            })
            code_created_for_tag = VERIF_COLL.count_documents({
                "id":           last_intern_id,
                "questionType": "code_test",
                "subject":      last_subject,
                "tag":          last_tag
            })

            # ─── count how many created today ────────────────────────
            created_on_date      = VERIF_COLL.count_documents({
                "id":        last_intern_id,
                "createdAt": {"$gte": start_of_day, "$lt": end_of_day}
            })
            created_on_date_mcq  = VERIF_COLL.count_documents({
                "id":           last_intern_id,
                "questionType": "mcq_test",
                "createdAt":    {"$gte": start_of_day, "$lt": end_of_day}
            })
            created_on_date_code = VERIF_COLL.count_documents({
                "id":           last_intern_id,
                "questionType": "code_test",
                "createdAt":    {"$gte": start_of_day, "$lt": end_of_day}
            })

            return {
                "success":               True,
                "message":               "Questions uploaded and creation logged.",
                "mcqCreatedForTag":      mcq_created_for_tag,
                "codeCreatedForTag":     code_created_for_tag,
                "internCreatedOnDate":   created_on_date,
                "mcqCreatedOnDate":      created_on_date_mcq,
                "codeCreatedOnDate":     created_on_date_code
            }, 201

        except Exception as e:
            return error_response(f"Error uploading questions: {e}", 500)
