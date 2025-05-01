from flask import Flask, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import json
from datetime import datetime

# Load configuration
with open('local_config.json', 'r') as f:
    cfg = json.load(f)

client = MongoClient(cfg['MONGO_CONFIG']['url'])
db = client['codegnan_product']
curriculum_collection = db['Mentor_Curriculum_Table']

class GetExamData(Resource):
    def get(self):
        # 1. Validate inputs
        req_date = request.args.get('date')
        batch    = request.args.get('batch')
        location = request.args.get('location')
        if not (req_date and batch and location):
            return {"error": "Missing required parameters: date, batch, location"}, 400
        try:
            datetime.strptime(req_date, "%Y-%m-%d")
        except ValueError:
            return {"error": "Invalid date format, expected YYYY-MM-DD"}, 400

        # 2. Fetch curriculum docs
        docs = list(curriculum_collection.find(
            {"batch": batch, "location": location},
            {"_id": 0, "curriculumTable": 1}
        ))
        if not docs:
            return {"message": "No curriculum found for this batch/location."}, 404

        # 3. Collect only entries whose createdAt == req_date
        subjects = {}
        for doc in docs:
            for _, entry in doc.get("curriculumTable", {}).items():
                created_str = entry.get("createdAt")
                if not created_str:
                    continue
                try:
                    created = datetime.fromisoformat(created_str)
                except ValueError:
                    continue
                if created.strftime("%Y-%m-%d") != req_date:
                    continue

                subj = entry.get("subject", "").strip()
                if not subj:
                    continue

                info = subjects.setdefault(subj, {
                    "topics": [], "subtitles": [], "tags": [], "date": req_date
                })
                topic = entry.get("Topics", "").strip()
                if topic:
                    info["topics"].append(topic)
                for st in entry.get("SubTopics", []):
                    if st.get("status", "").lower() == "true":
                        title = st.get("title", "").strip()
                        tag   = st.get("tag", "").strip()
                        if title:
                            info["subtitles"].append(title)
                        if tag:
                            info["tags"].append(tag)

        if not subjects:
            return {"message": "No curriculum entries for that date with status 'true'."}, 404

        # 4. Build MCQ/Code breakdown, deferring any “no MCQ” errors until after
        data = {}
        missing_mcq = []
        warnings = []

        for subj, info in subjects.items():
            info["topics"] = ", ".join(info["topics"])
            tags = [t.lower() for t in info["tags"] if t]
            mcq_col  = f"{subj.lower()}_mcq"
            code_col = f"{subj.lower()}_code"

            # MCQ count
            mcq_count = 0
            if mcq_col in db.list_collection_names() and tags:
                mcq_count = db[mcq_col].count_documents({"Tags": {"$in": tags}})
            if mcq_count == 0:
                missing_mcq.append(subj)
                continue

            # Code count
            code_count = 0
            if code_col in db.list_collection_names() and tags:
                code_count = db[code_col].count_documents({"Tags": {"$in": tags}})

            # Difficulty breakdown
            breakdown = {"mcq": {"easy": 0,"medium": 0,"hard": 0}, "code": {"easy": 0,"medium": 0,"hard": 0}}
            for doc_item in db[mcq_col].find({"Tags": {"$in": tags}}):
                lvl = doc_item.get("Difficulty", "").capitalize()
                if lvl in ["Easy","Medium","Hard"]:
                    breakdown["mcq"][lvl.lower()] += 1
            if code_col in db.list_collection_names():
                for doc_item in db[code_col].find({"Tags": {"$in": tags}}):
                    lvl = doc_item.get("Difficulty", "").capitalize()
                    if lvl in ["Easy","Medium","Hard"]:
                        breakdown["code"][lvl.lower()] += 1

            info["breakdown"] = breakdown
            if code_count == 0:
                warnings.append(f"{subj} (tags: {', '.join(info['tags'])})")

            data[subj] = info

        # 5. If no subject had any MCQs, error out
        if not data:
            return {
                "error": "No MCQ questions found for any requested subjects; please contact admin.",
                "subjects_without_mcq": missing_mcq
            }, 404

        # 6. Final response
        result = {"data": data}
        if warnings:
            result["warning"] = (
                "No code questions found for the following subject(s): "
                + "; ".join(warnings)
                + ". Please contact admin."
            )
        return result, 200