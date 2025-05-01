from flask import Flask, send_file, request,abort,jsonify
from flask_restful import Resource
from pymongo import MongoClient
from gridfs import GridFS
from io import BytesIO
from PIL import Image
import io

def compress_image(image_bytes, target_size_kb=10):
    """
    Compress the input image bytes so that its size is approximately at most target_size_kb (in KB).
    The function uses Pillow to open, convert, and (if needed) resize the image.
    Returns the compressed image bytes.
    """
    # Open the image from bytes
    image_io = io.BytesIO(image_bytes)
    try:
        image = Image.open(image_io)
    except Exception as e:
        raise ValueError("Invalid image file provided.")
   
    # Convert to RGB if necessary (JPEG requires RGB)
    if image.mode != "RGB":
        image = image.convert("RGB")
   
    quality = 85  # Starting quality setting
    compressed_io = io.BytesIO()
    image.save(compressed_io, format="JPEG", quality=quality)
    size_kb = len(compressed_io.getvalue()) / 1024

    # First, reduce quality until the size is under target_size_kb or quality reaches a threshold.
    while size_kb > target_size_kb and quality > 10:
        quality -= 5
        compressed_io = io.BytesIO()
        image.save(compressed_io, format="JPEG", quality=quality)
        size_kb = len(compressed_io.getvalue()) / 1024

    # If quality reduction alone is insufficient, resize the image.
    if size_kb > target_size_kb:
        width, height = image.size
        # Calculate a scaling factor based on current size versus target size.
        factor = (target_size_kb / size_kb) ** 0.5 
        new_width = max(1, int(width * factor))
        new_height = max(1, int(height * factor))
        image = image.resize((new_width, new_height), Image.LANCZOS) 
        quality = 85  # Reset quality after resizing
        compressed_io = io.BytesIO()
        image.save(compressed_io, format="JPEG", quality=quality)
        size_kb = len(compressed_io.getvalue()) / 1024
       
        # Further reduce quality if needed.
        while size_kb > target_size_kb and quality > 10:
            quality -= 5
            compressed_io = io.BytesIO()
            image.save(compressed_io, format="JPEG", quality=quality)
            size_kb = len(compressed_io.getvalue()) / 1024

    compressed_io.seek(0)
    return compressed_io.getvalue()

class Profile_pic(Resource):
    def __init__(self, client, db, student_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.student_collection_name = student_collection
        self.db = self.client[self.db_name]
        self.student_collection = self.db[self.student_collection_name]
        self.fs = GridFS(self.db)

    def get(self):
        ids = request.args.get('student_id') 

        if not ids :
            return {"error":"missing required fields"},404
            
        if not self.fs.find_one({'filename':ids}):
            return {"error": "For This ID no data Found"}, 404
        
        pics = self.fs.find_one({'filename':ids})
        try:
            pic_data = pics.read()
            pic_file = f"{pics.filename}.png"

            # print('-------------',pic_file)
            return send_file(BytesIO(pic_data),as_attachment=True,download_name=pic_file,mimetype="image/png")
        except Exception as e:
            print(f"Fetching Database query failed: {e}")
            abort(500, description="Database query failed with GridFS files.")
        
        return {"error": "Unknown error occurred."}, 500       
    
    def post(self):
        std_id =request.form.get('studentId')
        profile = request.files.get('profilePic')
        # print('------------p',request.form)
        profile_bytes = profile.read()
        try:
            pro_file = compress_image(profile_bytes, target_size_kb=10)
        except Exception as e:
            print(e)
            return {"error": "Failed to compress profile image: " + str(e)}, 400

        file_pic = self.db.fs.files.find_one({"filename": std_id})
        #print(file_pic)
        if file_pic:
            file_id = file_pic["_id"]
            self.fs.delete(file_id)
            profile_id = self.fs.put(pro_file, filename=std_id)
            file_pic['profile'] = str(profile_id)
            return {"message": "Student profile_pic updated successfully"}, 200