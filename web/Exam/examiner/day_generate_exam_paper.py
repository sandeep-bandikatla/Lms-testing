# your Flask app file
from flask import Flask, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import json, uuid, concurrent.futures
from datetime import datetime
from zoneinfo import ZoneInfo

from web.Exam.examiner.whatsapp_trigger import trigger_whatsapp

# ─── Load configuration ──────────────────────────────────────────────────────
with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

client = MongoClient(config_data['MONGO_CONFIG']['url'])
db     = client['codegnan_product']
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

app = Flask(__name__)
api = Api(app)

class GenerateExamPaper(Resource):
    def post(self):
        data        = request.get_json(force=True)
        exam_type   = data.get("type")
        batch       = data.get("batch")
        subjects    = data.get("subjects")
        total_time  = data.get("totalExamTime")
        start_date  = data.get("startDate")
        start_time  = data.get("startTime")
        manager_loc = data.get("managerLocation")

        # Validate required fields
        if not all([exam_type, batch, subjects, total_time, start_date, start_time, manager_loc]):
            return {"error": "Missing required fields."}, 400

        # Fetch students from student_login_details
        students = list(db['student_login_details'].find({
            "BatchNo": batch,
            "location": manager_loc
        }))
        if not students:
            return {"message": "No students found for this batch/location."}, 404

        exam_collection = db[exam_type]

        # Determine next examName suffix
        max_num = 0
        for e in exam_collection.find({
            "batch": batch,
            "examName": {"$regex": f"^{exam_type}-"}
        }):
            try:
                num = int(e["examName"].rsplit("-", 1)[-1])
                max_num = max(max_num, num)
            except:
                continue
        next_num = max_num + 1
        exam_name_to_use = f"{exam_type}-{next_num}"

        created_count = 0

        for student in students:
            sid = student.get("id")  # <-- this is your studentId
            if not sid:
                continue

            # Skip if already scheduled
            if exam_collection.find_one({"studentId": sid, "startDate": start_date}):
                continue

            # Insert exam doc
            exam_doc = {
                "examId":        str(uuid.uuid4()),
                "studentId":     sid,
                "subjects":      subjects,
                "totalExamTime": total_time,
                "startDate":     start_date,
                "startTime":     start_time,
                "examName":      exam_name_to_use,
                "batch":         batch,
                "location":      manager_loc
            }
            exam_collection.insert_one(exam_doc)
            created_count += 1

            # Prepare WhatsApp notification
            name  = student.get("name")
            phone = student.get("studentPhNumber")
            subs  = ", ".join([s.get("subject", "") for s in subjects])

            if name and phone:
                # Pass sid as the second argument into trigger_whatsapp
                fut = executor.submit(
                    trigger_whatsapp,
                    name,      # student_name
                    sid,       # student_id
                    phone,     # whatsapp_number
                    exam_name_to_use,
                    start_date,
                    start_time,
                    total_time,
                    subs,
                    batch
                )

                def _on_done(fut):
                    metrics = fut.result()
                    if not metrics:
                        return
                    # Store per-date & per-batch as before
                    rec_ts   = metrics["recorded_at"]
                    date_key = rec_ts.strftime("%Y-%m-%d")
                    record = {
                        "id":               metrics["id"],
                        "studentId":        metrics["studentId"],
                        "first_name":       metrics["first_name"],
                        "last_sent":        metrics["last_sent"],
                        "last_delivered":   metrics["last_delivered"],
                        "last_seen":        metrics["last_seen"],
                        "last_interaction": metrics["last_interaction"],
                        "recorded_at":      rec_ts
                    }
                    db["whatsapp_stats"].update_one(
                        {"date": date_key},
                        {
                            "$setOnInsert": {"date": date_key},
                            "$push": {f"batches.{metrics['batch']}": record}
                        },
                        upsert=True
                    )

                fut.add_done_callback(_on_done)
            else:
                print(f"Skipping WhatsApp for student {sid} (missing name or phone)")

        return {"message": f"Exam papers generated for {created_count} students."}, 201