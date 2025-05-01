import json
from flask import request
from flask_restful import Resource
from pymongo import MongoClient

# Load config & connect
with open('local_config.json', 'r') as f:
    cfg = json.load(f)

client = MongoClient(cfg['MONGO_CONFIG']['url'])
db = client["codegnan_product"]
testers_collection = db["Testers"]

class TesterCurriculum(Resource):
    def get(self):
        tester_id     = request.args.get("id")
        subject_param = request.args.get("subject", None)

        if not tester_id:
            return {"message": "'id' query parameter is required"}, 400

        # fetch only curriculumTable
        doc = testers_collection.find_one(
            {"id": tester_id},
            {"_id": 0, "curriculumTable": 1}
        )
        if not doc:
            return {"message": "Tester not found"}, 404

        # defensive fetch and lowercase all subject‐keys
        raw_ct = doc.get("curriculumTable", {})
        curriculum = { k.lower(): v for k, v in raw_ct.items() }

        # optional ?subject=python
        if subject_param:
            key = subject_param.lower()
            if key not in curriculum:
                return {"message": f"Subject '{subject_param}' not found"}, 404
            curriculum = { key: curriculum[key] }

        return {
            "id": tester_id,
            "curriculumTable": curriculum
        }, 200