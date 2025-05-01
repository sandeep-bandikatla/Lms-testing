from flask import Flask, send_file, request,abort,jsonify
from flask_restful import Resource
from pymongo import MongoClient
from gridfs import GridFS
from io import BytesIO
import zipfile

class AllResumes(Resource):
    def __init__(self, client, db, student_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.student_collection_name = student_collection
        self.db = self.client[self.db_name]
        self.student_collection = self.db[self.student_collection_name]
        self.fs = GridFS(self.db)

    def get(self):
        try:
            zip_data = BytesIO()
            
            with zipfile.ZipFile(zip_data, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file in self.fs.find():
                    file_data = file.read()
                    files = f"{file.filename}_{file._id}.pdf"
                    zip_file.writestr(files, file_data)

            zip_data.seek(0)

            return send_file(zip_data,
                            as_attachment=True,
                            download_name="all_resumes.zip",
                            mimetype="application/zip")

        except Exception as e:
            print(f"Fetching Database query failed: {e}")
            abort(500, description="Database query failed with GridFS files.")
        
        return jsonify({"error": "Unknown error occurred."}), 500