from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient
import random
import json
import copy
import datetime

# Load configuration and setup MongoDB client
with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)
MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
client = MongoClient(MONGO_CONFIG)
db = client["codegnan_product"]

# Custom JSON encoder to handle datetime objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)
    
# Helper function: error_response
def error_response(message, status_code=400):
    response = jsonify({"success": False, "message": message})
    response.status_code = status_code
    return response

# Helper function: fetch_questions
def fetch_questions(collection_name, tags, difficulty, count):
    """
    Fetch questions from the specified collection based on tags and difficulty.
    The exam document's tags are assumed to be strings and are compared in lowercase.
    Returns a random subset if more questions are available than needed.
    """
    # Convert all tags to lowercase for matching
    search_tags = [tag.lower() for tag in tags]
    diff_value = difficulty.capitalize()  # e.g. Easy, Medium, Hard
    # Query: Check if the question's Tags field (assumed to be a string) is in the search_tags list,
    # and if the Difficulty matches.
    query = {
        "Tags": {"$in": search_tags},
        "Difficulty": diff_value
    }
    questions = list(db[collection_name].find(query))
    if questions and len(questions) > count:
        questions = random.sample(questions, count)
    # Replace _id with questionId for each question
    for question in questions:
        if "_id" in question:
            question["questionId"] = str(question["_id"])
            del question["_id"]
    return questions

# Resource to append questions as "paper" to an existing exam document.
class StartExam(Resource):
    def post(self):
        try:
            data = request.json
            # Ensure required fields are provided
            if "examId" not in data:
                return error_response("'examId' is required.", 400)
            if "collectionName" not in data:
                return error_response("'collectionName' is required.", 400)

            exam_id = data["examId"]
            collection_name = data["collectionName"]

            # Find the exam document by examId field (as a string)
            exam_doc = db[collection_name].find_one({"examId": exam_id})
            if not exam_doc:
                return error_response("Exam document not found.", 404)

            paper = []  # This will hold the list of subject papers

            # Process each subject in the exam document
            for subject_data in exam_doc.get("subjects", []):
                subject_name = subject_data.get("subject", "").strip()
                # Use the tags provided in the exam document; convert them to lowercase.
                tags = [tag.lower() for tag in subject_data.get("tags", [])]
                mcq_questions = []
                coding_questions = []

                # Fetch MCQ questions based on selectedMCQs counts per difficulty.
                selected_mcqs = subject_data.get("selectedMCQs", {})
                for difficulty in ["easy", "medium", "hard"]:
                    count = int(selected_mcqs.get(difficulty, 0))
                    if count > 0:
                        # Collection name is assumed to be {subject}_mcq in lowercase.
                        mcq_collection = f"{subject_name.lower()}_mcq"
                        fetched_mcqs = fetch_questions(mcq_collection, tags, difficulty, count)
                        mcq_questions.extend(fetched_mcqs)

                # Fetch Coding questions based on selectedCoding counts per difficulty.
                selected_coding = subject_data.get("selectedCoding", {})
                for difficulty in ["easy", "medium", "hard"]:
                    count = int(selected_coding.get(difficulty, 0))
                    if count > 0:
                        # Collection name is assumed to be {subject}_code in lowercase.
                        coding_collection = f"{subject_name.lower()}_code"
                        fetched_coding = fetch_questions(coding_collection, tags, difficulty, count)
                        coding_questions.extend(fetched_coding)

                subject_paper = {
                    "subject": subject_name,
                    "MCQs": mcq_questions,
                    "Coding": coding_questions,
                    "totalTime": subject_data.get("totalTime", None)
                }
                paper.append(subject_paper)

            # Update the exam document by appending the "paper" field.
            db[collection_name].update_one(
                {"examId": exam_id},
                {"$set": {"paper": paper}}
            )

            # Retrieve the updated document without the MongoDB _id field.
            updated_exam_doc = db[collection_name].find_one({"examId": exam_id}, {"_id": 0})
            return jsonify({"success": True, "exam": updated_exam_doc})

        except Exception as e:
            return error_response(f"Error appending paper: {str(e)}", 500)