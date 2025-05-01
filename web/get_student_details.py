import logging
from flask import request, jsonify
from flask_restful import Resource, abort
from bson import ObjectId
from flask_jwt_extended import jwt_required,get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError

# Helper function to convert MongoDB document to JSON-compatible format
def to_json_compatible(data):
    if isinstance(data, dict):
        return {k: to_json_compatible(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [to_json_compatible(i) for i in data]
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data

class GetStudentDetails(Resource):
    #@jwt_required()
    def __init__(self, client, db, student_collection):
        super().__init__()
        self.client = client
        self.db = self.client[db]
        self.student_collection = self.db[student_collection]
        self.logger = logging.getLogger(__name__)

    def get(self):
        # Validate and parse input data
        try:
            #print("Request Headers:", request.headers)
            # access = get_jwt_identity()
            student_id = request.args.get('student_id')
            location = request.args.get('location')
            # print("studnet details------------- ",access,'---------',student_id)
            
            if not student_id:
                self.logger.error("Invalid input: 'student_id' is missing.")
                abort(400, message="Invalid input: 'student_id' is required.")

            # std_email = self.student_collection.find_one({"email":access})  
            # if std_email['email'] != access:
            #     return {"message":"unauthorised access data"},403

        # except NoAuthorizationError:
        #     return {"message": "Missing Authorization Header"}, 401
        
        except Exception as e:
            self.logger.error(f"Failed to parse request data: {e}")
            abort(400, message="Invalid JSON data.")

        # Query the database
        try:
            student_document = self.student_collection.find_one({"$and":[{"id": student_id},{"location":location}]},{"password":0})

            if not student_document:
                self.logger.info(f"Student with ID {student_id} not found.")
                abort(404, message="Student not found.")

            return jsonify(to_json_compatible(student_document))

        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            abort(500, message="Internal server error.")

        return jsonify({"error": "Unknown error occurred."}), 500