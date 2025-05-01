from flask import Flask,send_file,request,abort
from flask_restful import Resource
from pymongo import MongoClient
from gridfs import GridFS
from io import BytesIO

class UpdateResume(Resource):
    def __init__(self,client,db,student_collection) -> None:
        super().__init__()
        self.client = client
        self.db_name = db
        self.student_update_resume = student_collection
        self.db = self.client[self.db_name]
        self.student_collection = self.db[self.student_update_resume]
        self.fs = GridFS(self.db)
    #post method to getting data
    def post(self):
        student_id = request.form["student_id"]
        resume_file = request.files.get('resume')
        pdf_content = resume_file.read()

        if not student_id:
            return {"error": "Missing required parameter: student_id"}, 400
        else:
            student_doc = self.student_collection.find_one({"id":student_id})

            if student_doc:
                # Find the file document in fs.files collection by filename (student ID)
                file_doc = self.db.fs.files.find_one({"filename": student_id})
                print(file_doc)
                if file_doc:
                    file_id = file_doc["_id"]
                    self.fs.delete(file_id)
                    resume_id = self.fs.put(pdf_content, filename=student_id)
                    student_doc['resume_id'] = str(resume_id)
                    #print("resume updated",resume_id)
                    return {"message": "Resume Updated successful", "userType":"student","student_id":student_id}, 200
                else:
                        print(f"File Not found with filename '{file_doc}'")
                        return {"message": "File Not found with student_id","student_id":student_id}, 404
            else:
                    print(f"No student found with ID '{student_id}'")
                    return {"message": "No student found","student_id":student_id}, 404
    
    def get(self):
        ids = request.args.get('resumeId') 

        if not ids :
            return {"error":"missing required fields"},404
       
        pics = self.fs.find_one({'filename':ids})     
        if not pics :
            return {"error": "For This ID no data Found"}, 404
        try:
            resum_data = pics.read()
            resum_file = f"{pics.filename}.pdf"

            print('Resumee-------------',resum_file)
            return send_file(BytesIO(resum_data),as_attachment=True,download_name=resum_file,mimetype="application/pdf")
        except Exception as e:
            print(f"Fetching Database query failed: {e}")
            abort(500, description="Database query failed with GridFS files.")
        
        return {"error": "Unknown error occurred."}, 500       