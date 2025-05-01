from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient, ReturnDocument
import json

# Load configuration and connect to MongoDB.
with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
client = MongoClient(MONGO_CONFIG)
db = client["codegnan_product"]

def error_response(message, status_code=400):
    response = jsonify({"success": False, "message": message})
    response.status_code = status_code
    return response

def find_question_by_id(exam_record, question_id):
    """
    Iterates through the exam_record's papers and returns a tuple:
      (question object, question type, subject name)
    If no matching question is found, returns (None, None, None).
    """
    for paper in exam_record.get("paper", []):
        for mcq in paper.get("MCQs", []):
            if mcq.get("questionId") == question_id:
                return mcq, "MCQ", paper.get("subject")
        for coding in paper.get("Coding", []):
            if coding.get("questionId") == question_id:
                return coding, "Coding", paper.get("subject")
    return None, None, None

class SubmitExam(Resource):
    def post(self):
        payload = request.json
        exam_id = payload.get("examId")
        exam_collection_name = payload.get("exam")
        print(payload)  # For debugging; consider removing or using proper logging.

        if not exam_id or not exam_collection_name:
            return error_response("Missing examId or exam collection name.", 400)

        exam_collection = db[exam_collection_name]
        exam_record = exam_collection.find_one({"examId": exam_id})
        if not exam_record:
            return error_response("Exam record not found.", 404)

        # Prevent multiple submissions.
        if exam_record.get("attempt-status"):
            return error_response("Exam already submitted. No further submissions allowed.", 403)

        # Count overall questions and precompute a subject-wise breakdown.
        total_mcq_count = 0
        total_code_count = 0
        subject_breakdown = {}

        for paper in exam_record.get("paper", []):
            subj = paper.get("subject")
            mcq_count = len(paper.get("MCQs", []))
            coding_count = len(paper.get("Coding", []))
            total_questions_in_paper = mcq_count + coding_count

            total_mcq_count += mcq_count
            total_code_count += coding_count

            if subj:
                if subj not in subject_breakdown:
                    subject_breakdown[subj] = {
                        "totalQuestions": total_questions_in_paper,
                        "attempted": 0,
                        "unattempted": total_questions_in_paper,
                        "score": 0,
                        "mcq": {
                            "total": mcq_count,
                            "attempted": 0,
                            "score": 0
                        },
                        "coding": {
                            "total": coding_count,
                            "attempted": 0,
                            "score": 0
                        }
                    }
                else:
                    subject_breakdown[subj]["totalQuestions"] += total_questions_in_paper
                    subject_breakdown[subj]["unattempted"] += total_questions_in_paper
                    subject_breakdown[subj]["mcq"]["total"] += mcq_count
                    subject_breakdown[subj]["coding"]["total"] += coding_count

        total_questions = total_mcq_count + total_code_count

        analysis = {
            "totalScore": 0,
            "correctCount": 0,
            "incorrectCount": 0,
            "attemptedMCQCount": 0,
            "attemptedCodeCount": 0,
            "attemptedCount": 0,
            "totalTimeTaken": 0,
            "details": [],
            "examCompleted": True,
            "totalMCQCount": total_mcq_count,
            "totalCodingCount": total_code_count,
            "totalQuestions": total_questions,
            "subjectBreakdown": subject_breakdown
        }

        attempted_question_ids = set()
        reserved_keys = {"examId", "exam"}

        # Process each submitted answer (key = questionId).
        for key, answer in payload.items():
            if key in reserved_keys:
                continue

            # Find question data, type, and subject.
            question_data, question_type, subject = find_question_by_id(exam_record, key)
            if not question_data:
                continue  # Skip if not found.

            attempted_question_ids.add(key)
            analysis["attemptedCount"] += 1
            awarded = 0  # Initialize awarded score for this question.

            # ------------------------------
            # Handle Coding Questions
            # ------------------------------
            if question_type == "Coding":
                # Ensure valid coding answer format
                if not isinstance(answer, dict) or "testCaseSummary" not in answer:
                    analysis["details"].append({
                        "questionId": key,
                        "type": "code",
                        "error": "Invalid coding question submission format.",
                        "timeTaken": answer.get("timeTaken", 0) if isinstance(answer, dict) else 0
                    })
                    continue

                analysis["attemptedCodeCount"] += 1
                try:
                    question_score = int(question_data.get("Score", 0))
                except Exception:
                    question_score = 0

                test_summary = answer.get("testCaseSummary", {})
                passed_testcases = test_summary.get("passed", 0)
                failed_testcases = test_summary.get("failed", 0)
                total_testcases = passed_testcases + failed_testcases

                # Partial scoring: award points based on fraction of passed testcases
                if total_testcases == 0:
                    # No testcases or no evaluation info
                    status = "Not Evaluated"
                    awarded = 0
                else:
                    # Partial marking based on passed vs total testcases
                    awarded = question_score * (passed_testcases / total_testcases)
                    if failed_testcases == 0:
                        status = "Passed"
                        analysis["correctCount"] += 1
                    else:
                        status = "Partially Passed"
                        # If you'd like, you can increment incorrectCount only if partially passed is still considered "incorrect" overall
                        analysis["incorrectCount"] += 1

                    # Add partial or full credit to totalScore
                    analysis["totalScore"] += awarded

                time_taken = answer.get("timeTaken", 0)
                analysis["totalTimeTaken"] += time_taken

                # Store code details in the analysis
                analysis["details"].append({
                    "questionId": key,
                    "type": "code",
                    "submitted": answer,
                    "sourceCode": answer.get("sourceCode"),  # Storing the submitted source code
                    "scoreAwarded": awarded,
                    "status": status,
                    "timeTaken": time_taken,
                    "question": question_data.get("Question")
                })

                # Subject breakdown for coding
                if subject and subject in analysis["subjectBreakdown"]:
                    analysis["subjectBreakdown"][subject]["attempted"] += 1
                    analysis["subjectBreakdown"][subject]["unattempted"] -= 1
                    analysis["subjectBreakdown"][subject]["score"] += awarded
                    analysis["subjectBreakdown"][subject]["coding"]["attempted"] += 1
                    analysis["subjectBreakdown"][subject]["coding"]["score"] += awarded

            # ------------------------------
            # Handle MCQ Questions
            # ------------------------------
            elif question_type == "MCQ":
                if isinstance(answer, dict):
                    analysis["attemptedMCQCount"] += 1
                    selected_option = answer.get("selectedOption", "")
                    time_taken = answer.get("timeTaken", 0)
                    analysis["totalTimeTaken"] += time_taken

                    correct_answer = question_data.get("Correct_Option")
                    try:
                        question_score = int(question_data.get("Score", 0))
                    except Exception:
                        question_score = 0

                    if str(selected_option).strip().upper() == str(correct_answer).strip().upper():
                        status = "Correct"
                        awarded = question_score
                        analysis["correctCount"] += 1
                        analysis["totalScore"] += awarded
                    else:
                        status = "Incorrect"
                        awarded = 0
                        analysis["incorrectCount"] += 1

                    analysis["details"].append({
                        "questionId": key,
                        "type": "objective",
                        "submitted": selected_option,
                        "correctAnswer": correct_answer,
                        "scoreAwarded": awarded,
                        "status": status,
                        "timeTaken": time_taken,
                        "question": question_data.get("Question"),
                        "options": question_data.get("Options") if question_data.get("Options") else {}
                    })
                else:
                    # If answer is provided as a direct value
                    analysis["attemptedMCQCount"] += 1
                    selected_option = answer
                    time_taken = 0
                    correct_answer = question_data.get("Correct_Option")
                    try:
                        question_score = int(question_data.get("Score", 0))
                    except Exception:
                        question_score = 0

                    if str(selected_option).strip().upper() == str(correct_answer).strip().upper():
                        status = "Correct"
                        awarded = question_score
                        analysis["correctCount"] += 1
                        analysis["totalScore"] += awarded
                    else:
                        status = "Incorrect"
                        awarded = 0
                        analysis["incorrectCount"] += 1

                    analysis["details"].append({
                        "questionId": key,
                        "type": "objective",
                        "submitted": selected_option,
                        "correctAnswer": correct_answer,
                        "scoreAwarded": awarded,
                        "status": status,
                        "timeTaken": time_taken,
                        "question": question_data.get("Question"),
                        "options": question_data.get("Options") if question_data.get("Options") else {}
                    })

                # Subject breakdown for MCQ
                if subject and subject in analysis["subjectBreakdown"]:
                    analysis["subjectBreakdown"][subject]["attempted"] += 1
                    analysis["subjectBreakdown"][subject]["unattempted"] -= 1
                    analysis["subjectBreakdown"][subject]["score"] += awarded
                    analysis["subjectBreakdown"][subject]["mcq"]["attempted"] += 1
                    analysis["subjectBreakdown"][subject]["mcq"]["score"] += awarded

        # Identify unattempted questions (for overall count).
        not_attempted_details = []
        for paper in exam_record.get("paper", []):
            for mcq in paper.get("MCQs", []):
                if mcq.get("questionId") not in attempted_question_ids:
                    not_attempted_details.append({
                        "questionId": mcq.get("questionId"),
                        "question": mcq.get("Question"),
                        "options": mcq.get("Options") if mcq.get("Options") else {},
                        "correctAnswer": mcq.get("Correct_Option") if mcq.get("Correct_Option") else None
                    })
            for coding in paper.get("Coding", []):
                if coding.get("questionId") not in attempted_question_ids:
                    not_attempted_details.append({
                        "questionId": coding.get("questionId"),
                        "question": coding.get("Question")
                    })
        analysis["notAttemptedCount"] = len(not_attempted_details)
        analysis["notAttemptedDetails"] = not_attempted_details

        # Atomically update the exam record to mark it as submitted.
        updated_exam = exam_collection.find_one_and_update(
            {"examId": exam_id, "attempt-status": {"$ne": True}},
            {"$set": {"analysis": analysis, "attempt-status": True}},
            return_document=ReturnDocument.AFTER
        )
        if not updated_exam:
            return error_response("Exam already submitted. No further submissions allowed.", 403)

        return jsonify({
            "success": True,
            "message": "Exam submitted successfully. No further test execution as the exam is complete.",
            "analysis": analysis
        })