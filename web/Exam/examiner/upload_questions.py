from flask import request, jsonify
from flask_restful import Resource
from pymongo import MongoClient
import json

with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
client = MongoClient(MONGO_CONFIG)
db = client["codegnan_product"]

def error_response(message, status_code=400):
    response = jsonify({"success": False, "message": message})
    response.status_code = status_code
    return response

class UploadQuestions(Resource):
    def post(self):
        data = request.json  # Expecting a list of dictionaries (rows from the Excel sheet)

        if not data or not isinstance(data, list):
            return error_response("Invalid data format. Expected a list of JSON objects.", 400)

        try:
            for question in data:
                # Validate required fields and process as needed
                question_type = str(question.get('Question_Type', '')).lower()
                subject = str(question.get('Subject', '')).lower()

                if not question_type:
                    return error_response("Each question must have a 'Question_Type' field.", 422)
                if not subject:
                    return error_response("Each question must have a 'Subject' field.", 422)

                # Determine collection name dynamically
                if question_type == "mcq":
                    collection_name = f"{subject}_mcq"
                elif question_type == "code":
                    collection_name = f"{subject}_code"
                else:
                    return error_response(f"Unsupported Question Type: {question_type}", 422)

                if question_type == "mcq":
                    # Validate required fields for MCQ
                    if not question.get('Score'):
                        return error_response("Each MCQ question must have a 'Score' field.", 422)

                    question_document = {
                        "Question_No": question.get('Question_No'),
                        "Question_Type": question_type,
                        "Subject": subject,
                        "Question": str(question.get('Question', '')),
                        "Options": {
                            "A": str(question.get('A', '')),
                            "B": str(question.get('B', '')),
                            "C": str(question.get('C', '')),
                            "D": str(question.get('D', '')),
                        },
                        "Correct_Option": str(question.get('Correct_Option', '')),
                        "Score": question.get('Score'),
                        "Difficulty": question.get('Difficulty'),
                        "Tags": str(question.get('Tags', '')).lower(),
                        "Text_Explanation": str(question.get('Text_Explanation', '')),
                        "Explanation_URL": str(question.get('Explanation_URL', '')),
                        "image_url": str(question.get('Image_URL', ''))

                    }
                    
                elif question_type == "code":
                    # Build dynamic list for hidden test cases (test cases 1-4)
                    hidden_test_cases = []
                    for i in range(1, 5):
                        test_input = question.get(f'Hidden_Test_case_{i}_Input')
                        test_output = question.get(f'Hidden_Test_case_{i}_Output')
                        # Add the test case if at least one field is provided
                        if test_input is not None or test_output is not None:
                            hidden_test_cases.append({
                                "Input": str(test_input) if test_input is not None else "",
                                # Preserve the original type for output (e.g., boolean)
                                "Output": test_output if test_output is not None else ""
                            })

                    question_document = {
                        "Question_No": question.get('Question_No'),
                        "Question_Type": question_type,
                        "Subject": subject,
                        "Question": str(question.get('Question', '')),
                        "Sample_Input": str(question.get('Sample_Input', '')),
                        # Preserve the original type for Sample_Output
                        "Sample_Output": question.get('Sample_Output', ''),
                        "Constraints": str(question.get('Constraints', '')),
                        "Hidden_Test_Cases": hidden_test_cases,
                        "Score": question.get('Score'),
                        "Tags": str(question.get('Tags', '')).lower(),
                        "Difficulty": question.get('Difficulty'),
                        "Text_Explanation": str(question.get('Text_Explanation', '')),
                        "Explanation_URL": str(question.get('Explanation_URL', ''))
                    }

                # Remove fields that are None or empty strings
                question_document = {k: v for k, v in question_document.items() if v is not None and v != ""}
                if "Options" in question_document:
                    question_document["Options"] = {k: v for k, v in question_document["Options"].items() if v is not None and v != ""}

                # Insert the document into the appropriate collection
                db[collection_name].insert_one(question_document)

            return {"success": True, "message": "Question paper uploaded successfully."}, 201
        except Exception as e:
            return error_response(f"Error uploading question paper: {str(e)}", 500)