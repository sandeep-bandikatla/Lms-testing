from flask import request,jsonify
from flask_restful import Resource
from pymongo import MongoClient
import uuid

class CurriCulum(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
    
    def post(self):
        data = request.json  

        if isinstance(data, list):
            responses = []
            for item in data:
                subject = item.get('subject')
                day = item.get('dayOrder')
                topic = item.get('topic')
                subtopics = item.get('subTopics')
                id = str(uuid.uuid4())

                if not (subject and day and topic):
                    responses.append({"error": "Missing required fields", "data": item})
                    continue

                if self.collection.find_one({"DayOrder": day, "subject": subject}):  
                    responses.append({"error": "Data already exists", "data": item})
                    continue

                curriculam = {
                    "id": id,
                    "subject": subject,
                    "DayOrder": day,
                    "Topics": topic,
                    "SubTopics":subtopics
                }
                #print('Excel-curriculam-----', curriculam)

                result = self.collection.insert_one(curriculam)
                curriculam['_id'] = str(result.inserted_id)

                responses.append({"message": "Curriculum Updated Successfully", "data": curriculam})

            return {"responses": responses}, 200

        elif isinstance(data, dict):
            subject = data.get('subject')
            day = data.get('dayOrder')
            topic = data.get('topic')
            subtopics = data.get('subTopics')
            id = str(uuid.uuid4())

            if not (subject and day and topic):
                return {"error": "Missing required fields"}, 400

            if self.collection.find_one({"DayOrder": day, "subject": subject}):  
                return {"error": "Data already exists"}, 409

            curriculam = {
                "id": id,
                "subject": subject,
                "DayOrder": day,
                "Topics": topic,
                "SubTopics":subtopics
            }
            #print('P-M-curriculam-----', curriculam)

            result = self.collection.insert_one(curriculam)
            curriculam['_id'] = str(result.inserted_id)

            return {"message": "Curriculum Updated Successfully", "data": curriculam}, 200

        else:
            return {"error": "Invalid input format. Must be a dictionary or a list of dictionaries"}, 400
    
    def get(self):
        Curriculum = list(self.collection.find({}))
        for data in Curriculum:
            data["_id"] = str(data["_id"])
        return {"message":"All Curriculums with location ","data": Curriculum}, 200                             

    """def post(self):
        file = request.files.get('file')

        subject = request.json.get('subject')
        day = request.json.get('dayOrder')
        topic = request.json.get('topic')
        topicCover = request.json.get('topicsToCover')
        id = str(uuid.uuid4())

        if not file and not (subject and day and topic):
            return {"error": "No file or manual entry provided"}, 400

        if file and self.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join('uploads', filename)
            file.save(file_path)

            # Read the file
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif filename.endswith('.xls') or filename.endswith('.xlsx'):
                df = pd.read_excel(file_path)

            for _,row in df.iterrows():
                subject = row.get('subject')
                day = row.get('dayOrder')
                topic = row.get('topic')
                topicCover = row.get('topicsToCover')

                if not (subject and day and topic):
                    return {"error": "Missing required fields in file"}, 400

                if self.collection.find_one({"DayOrder": day, "subject": subject}):  
                    return {"error": f"Data for {subject} on day {day} already exists"}, 409

                curriculum = {
                    "id": id,
                    "subject": subject,
                    "DayOrder": day,
                    "Topics": topic,
                    "TopicsToCover": topicCover
                }
                print('Excel-curriculam-----', curriculum)
                result = self.collection.insert_one(curriculum)
                curriculum['_id'] = str(result.inserted_id)

            return {"message": "Curriculum Updated Successfully from file", "data": curriculum}, 200


        if self.collection.find_one({"DayOrder": day, "subject": subject}):  
            return {"error": "Data already exists For this subject and day"}, 409

        curriculam = {
            "id": id,
            "subject": subject,
            "DayOrder": day,
            "Topics": topic,
            "TopicsToCover": topicCover
        }
        print('PM-MA-curriculam-----', curriculam)

        result = self.collection.insert_one(curriculam)
        curriculam['_id'] = str(result.inserted_id)

        return {"message": "Curriculum Updated Successfully","data": curriculam}, 200"""

