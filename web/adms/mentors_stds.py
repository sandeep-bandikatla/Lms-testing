from flask import request
from flask_restful import Resource
from pymongo import MongoClient


class ListofStudentsForMentor(Resource):
    def __init__(self, client, db, collection,student_collection,mentor_collection,classdata_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.student_collection =student_collection
        self.mentor_collection = mentor_collection
        self.daily_class_collection=classdata_collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        self.student_collection = self.db[self.student_collection]
        self.mentor_collection = self.db[self.mentor_collection]
        self.daily_class_collection = self.db[self.daily_class_collection]

    def get(self):
        mentorId = request.args.get('mentorId')
        location = request.args.get('location')
        batch = request.args.get('batch')

        class_data = list(self.daily_class_collection.find({"$and":[{"batch":batch},{"location":location},{"mentorId":mentorId}]},{"password":0}))
        #print('-----------class_data------',class_data)
        for clas in class_data:
            clas["_id"] = str(clas["_id"])
       
        schedule_data = list(self.collection.find({"$and":[{"MentorId":mentorId},{"location":location}]},{"password":0}))
        dat = []
        for data in schedule_data:
            data["_id"] = str(data["_id"])
            for batch in data['batchNo']:
                dat.append(batch)

        mentor_data = list(self.mentor_collection.find({"$and":[{"id":mentorId},{"location":location}]},{"password":0}))
        for mentor in mentor_data:
            mentor["_id"] = str(mentor["_id"])

        student_data = []
        for Ids in dat:
            print('For mentor studentbatch--------',Ids)
            students=list(self.student_collection.find({"$and":[{"BatchNo":Ids},{"location":location}]},{"password":0}))
            for data in students:
                data["_id"] = str(data["_id"])
                student_data.append(data)

        return {"message":"Getting All batches data",
                "schedule_data":schedule_data,
                "mentor_data":mentor_data,
                "student_data":student_data,
                "classes":class_data},200