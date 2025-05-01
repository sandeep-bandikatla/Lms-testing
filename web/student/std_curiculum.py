from flask import request
from flask_restful import Resource
from pymongo import MongoClient
import json

with open("local_config.json") as f:
    config = json.load(f)

mongo_config = config.get("MONGO_CONFIG", {})
client = MongoClient(mongo_config.get("url"))
db_name = mongo_config.get("db_name")
db = client[db_name]

class StudentsCurriculum(Resource):
    def __init__(self):
        super().__init__()
  

    def get(self):
        subject = request.args.get('subject')
        location = request.args.get('location')
        batch = request.args.get('batchNo')

        if not (subject and location and batch) :
            return {"error": "Missing required fields"}, 400    
        
        # db.Mentor_Curriculum_Table.find_one(
        #     {"subject": subject, "batch": batch,"location":location},
        #     {"curriculumTable": 1, "_id": 0}
        # )

        curiculum_data = list(db.Mentor_Curriculum_Table.find({"subject": subject, "batch": batch,"location":location}))
        #print('studentsCurriculum-------',curiculum_data)
        for dat in curiculum_data:
            dat["_id"]=str(dat["_id"])

        return {"message":"Daily classes Curriculum","std_curiculum":curiculum_data},200