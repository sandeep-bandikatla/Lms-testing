from flask import Flask, send_file, request
from flask_restful import Resource
from pymongo import MongoClient
from gridfs import GridFS
from io import BytesIO
import zipfile

class DownloadResumes(Resource):
    def __init__(self, client, db, student_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.student_collection_name = student_collection
        self.db = self.client[self.db_name]
        self.student_collection = self.db[self.student_collection_name]
        self.fs = GridFS(self.db)  # Initialize GridFS for retrieving files

    def post(self):
        # Get the list of student IDs from the request body
        student_ids = request.json.get("student_ids", [])
        
        if not student_ids:
            return {"error": "Missing required parameter: student_ids"}, 400

        # Create a BytesIO object to hold the zip archive
        zip_data = BytesIO()

        with zipfile.ZipFile(zip_data, 'w', zipfile.ZIP_DEFLATED) as zip_archive:
            for student_id in student_ids:
                # Find the student document in the student collection by student ID
                student_doc = self.student_collection.find_one({"id": student_id})

                if student_doc:
                    # Get the student's name
                    student_name = student_doc.get("name", "Unknown")

                    # Find the file document in fs.files collection by filename (student ID)
                    file_doc = self.db.fs.files.find_one({"filename": student_id})

                    if file_doc:
                        # Get the file's ID and retrieve the file from GridFS
                        file_id = file_doc["_id"]
                        grid_out = self.fs.get(file_id)

                        # Read the file's content
                        pdf_content = grid_out.read()

                        # Add the content to the zip archive with student name as filename
                        zip_archive.writestr(f"{student_name}.pdf", pdf_content)
                    else:
                        # Log or handle if a file is not found
                        print(f"No file found with filename '{student_id}'")

                else:
                    # Log or handle if a student document is not found
                    print(f"No student found with ID '{student_id}'")

        # Reset the position of the zip_data for reading
        zip_data.seek(0)

        # Return the zip archive with appropriate headers for download
        return send_file(
            zip_data,
            mimetype="application/zip",
            as_attachment=True,
            download_name="resumes.zip"  # Name for the downloaded zip file
        )

