import uuid
import json
from flask import Flask, request
from flask_restful import Resource, Api
from pymongo import MongoClient


# Load configuration from local_config.json
with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)


class ScheduleBatches(Resource):
    def __init__(self, client, db, schedule_collection, mentor_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.schedule_collection_name = schedule_collection
        self.mentor_collection_name = mentor_collection
        self.db = self.client[self.db_name]
        self.schedule_collection = self.db[self.schedule_collection_name]
        self.mentor_collection = self.db[self.mentor_collection_name]
        # Mentor Curriculum Table collection is assumed to be named as below.
        self.mentor_curriculum_collection = self.db["Mentor_Curriculum_Table"]

    def post(self):
        data = request.get_json()
        # print('Received data:', data)
        course = data.get('techStack')
        batches = data.get('batches')
        subject = data.get('subject')
        mentor_name = data.get('mentorName')
        room_no = data.get('roomNo')
        start = data.get('startTime')
        end = data.get('endTime')
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        location = data.get('location')
        mentor_id = data.get('mentorId')

        # Generate a unique id for the schedule entry.
        schedule_id = str(uuid.uuid4())

        # Validate required fields for schedule.
        if not (course and batches and subject and location):
            return {"error": "Missing required fields for schedule"}, 400
    
        time_overlap_condition = {
            "$or": [
                {"$and": [{"StartTime": {"$lt": start}}, {"EndTime": {"$gt": start}}]},  # New start time is strictly inside an existing slot
                {"$and": [{"StartTime": {"$gt": start}}, {"StartTime": {"$lt": end}}]},  # Existing start time is strictly inside new slot
                {"$and": [{"StartTime": {"$lt": end}}, {"EndTime": {"$gt": end}}]}  # New end time is strictly inside an existing slot
            ] }
        # if self.schedule_collection.find_one({"$and": [{"MentorName": mentor_name},time_overlap_condition ]}):
        #     return {"error": "For this Time,  mentor already have a class."}, 404
        
        if self.schedule_collection.find_one({
            "$and": [
                {"subject": subject},
                {"batchNo": {"$in": batches}},
                {"MentorName": mentor_name},
                {"StartDate":start_date},
                {"EndDate":end_date},
                time_overlap_condition  
            ]}):
            return {"error": "For this batch, this subject already exists with a mentor in the given time slot"}, 404

        if self.schedule_collection.find_one({
            "$and": [
                {"subject": subject},
                {"batchNo": {"$in": batches}},
                {"location": location}
            ]}):
            return {"error": "For this batch and course, a batch already exists at this location"}, 404

        if self.schedule_collection.find_one({
            "$and": [
                {"subject": subject},
                {"batchNo": {"$in": batches}},
                {"MentorName": mentor_name},
                {"location": location}]}):
            return {"error": "For this course, the batch already exists at this location"}, 404

        if self.schedule_collection.find_one({
            "$and": [
                {"RoomNo": room_no},
                {"location": location},
                {"MentorName": mentor_name},
                {"StartDate":start_date},
                {"EndDate":end_date},
                time_overlap_condition  
            ]}):
            return {"error": "For this day time slot, the room is already assigned for another class"}, 404

        schedule = {
            "id": schedule_id,
            "course": course,
            "batchNo": batches,
            "subject": subject,
            "MentorName": mentor_name,
            "RoomNo": room_no,
            "StartDate": start_date,
            "EndDate": end_date,
            "StartTime": start,
            "EndTime": end,
            "location": location,
            "MentorId": mentor_id
        }
        result = self.schedule_collection.insert_one(schedule)
        schedule['_id'] = str(result.inserted_id)

        # ----------------- Mentor Curriculum Table Creation ----------------- #
        if not batches or not mentor_id or not subject:
            curriculum_response = {"error": "Missing required fields for mentor curriculum table: batches, mentorId, subject."}
        else:

            if isinstance(batches, str):
                batches = [batch.strip() for batch in batches.split(",") if batch.strip()]

            # Fetch curriculum documents based on subject.
            curriculum_documents = list(self.db.Curriculum.find(
                {"subject": subject},
                {"subject": 1, "Topics": 1, "SubTopics": 1, "DayOrder": 1}
            ))

            # Build the curriculum table structure.
            curriculum_table = {}
            for doc in curriculum_documents:
                day_order = doc.get("DayOrder", "Day-Unknown")
                subtopics_array = []
                for index, subtopic in enumerate(doc.get("SubTopics", [])):
                    subtopics_array.append({
                        "title": subtopic,
                        "status": "false",
                        "tag": f"{day_order}:{index+1}"
                    })
                curriculum_table[str(doc["_id"])] = {
                    "subject": doc.get("subject"),
                    "Topics": doc.get("Topics"),
                    "SubTopics": subtopics_array
                }

            mentor_curriculum_docs = []
            for batch in batches:
                exists = self.mentor_curriculum_collection.find_one({
                    "mentorId": mentor_id,
                    "subject": subject,
                    "batch": batch
                })
                if not exists:
                    new_doc = {
                        "mentorId": mentor_id,
                        "mentorName":mentor_name,
                        "subject": subject,
                        "batch": batch,
                        "location":location,
                        "curriculumTable": curriculum_table
                    }
                    mentor_curriculum_docs.append(new_doc)

            if mentor_curriculum_docs:
                self.mentor_curriculum_collection.insert_many(mentor_curriculum_docs)
                inserted_docs = list(self.mentor_curriculum_collection.find({
                    "mentorId": mentor_id,
                    "subject": subject,
                    "batch": {"$in": batches}
                }))
                for doc in inserted_docs:
                    doc["_id"] = str(doc["_id"])
                curriculum_response = {
                    "inserted_data": inserted_docs,
                    "message": "Curriculum has been assigned to mentor Successfully."
                }
            else:
                curriculum_response = {
                    "message": "No new mentor curriculum(s) were created. All documents already exist."
                }

        # ----------------- Combined Response ----------------- #
        return {
            "message": "New Batch Added Successfully!",
            "schedule_data": schedule,
            "mentor_curriculum": curriculum_response
        }, 200

    def get(self):
        location = request.args.get('location')
        if location == 'all':
            schedule_data = list(self.schedule_collection.find({}))
            for data in schedule_data:
                data["_id"] = str(data["_id"])

            mentor_data = list(self.mentor_collection.find({}))
            for data in mentor_data:
                data["_id"] = str(data["_id"])
            return {
                "message": "Getting all scheduled data",
                "schedule_data": schedule_data,
                "mentor_data": mentor_data
            }, 200
        else:
            schedule_data = list(self.schedule_collection.find({"location": location}))
            for data in schedule_data:
                data["_id"] = str(data["_id"])

            mentor_data = list(self.mentor_collection.find({"location": location}))
            for data in mentor_data:
                data["_id"] = str(data["_id"])
            return {
                "message": f"Getting scheduled data for location: {location}",
                "schedule_data": schedule_data,
                "mentor_data": mentor_data
            }, 200

    def put(self):
        data = request.get_json()
        print('Received update data:', data)
        schedule_id = data.get("id")
        if not schedule_id:
            return {"error": "ID is required to update a record"}, 400

        schedule_doc = self.schedule_collection.find_one({"id": schedule_id})
        if not schedule_doc:
            return {"error": "Schedule with the specified ID not found"}, 404

        update_fields = {}
        if "mentorName" in data:
            update_fields["MentorName"] = data["mentorName"]
        if "techStack" in data:
            update_fields["course"] = data["techStack"]
        if "roomNo" in data:
            update_fields["RoomNo"] = data["roomNo"]
        if "subject" in data:
            update_fields["subject"] = data["subject"]
        if "startDate" in data:
            update_fields["StartDate"] = data["startDate"]
        if "endDate" in data:
            update_fields["EndDate"] = data["endDate"]
        if "startTime" in data:
            update_fields["StartTime"] = data["startTime"]
        if "endTime" in data:
            update_fields["EndTime"] = data["endTime"]
        if "batches" in data:
            update_fields["batchNo"] = data["batches"]
        if "location" in data:
            update_fields["location"] = data["location"]

        if update_fields:
            self.schedule_collection.update_one({"id": schedule_id}, {"$set": update_fields})

        updated_schedule = self.schedule_collection.find_one({"id": schedule_id})
        updated_schedule["_id"] = str(updated_schedule["_id"])

        return {
            "message": "Schedule updated successfully",
            "schedule": updated_schedule
        }, 200

    def delete(self):
        # First, retrieve the schedule document based on the provided id.
        schedule_id = request.args.get('id')
        if not schedule_id:
            return {"error": "ID is required to delete a record"}, 400

        schedule_doc = self.schedule_collection.find_one({"id": schedule_id})
        if not schedule_doc:
            return {"error": "Schedule with the specified ID not found"}, 404

        # Delete the schedule document.
        result = self.schedule_collection.delete_one({"id": schedule_id})
        if result.deleted_count == 0:
            return {"error": "Schedule with the specified ID not found"}, 404

        # Also delete the corresponding Mentor Curriculum Table document(s)
        # using mentorId, subject, and batchNo from the schedule.
        mentor_id = schedule_doc.get("MentorId")
        subject = schedule_doc.get("subject")
        batches = schedule_doc.get("batchNo")
        # Ensure batches is a list.
        if isinstance(batches, str):
            batches = [batches]
        mentor_curr_result = self.mentor_curriculum_collection.delete_many({
            "mentorId": mentor_id,
            "subject": subject,
            "batch": {"$in": batches}
        })

        return {
            "message": "Schedule and corresponding Mentor Curriculum Table deleted successfully",
            "deleted_schedule_id": schedule_id,
            "mentor_curriculum_deleted_count": mentor_curr_result.deleted_count
        }, 200

