from flask import Flask, jsonify, request, send_file
from pymongo import MongoClient, errors
from dotenv import load_dotenv
import os, io
import base64

load_dotenv()

app = Flask(__name__)
MONGO_URI = os.getenv("MONGO_URI")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info() 
    print("[✓] Successfully connected to MongoDB Atlas.")
except errors.ServerSelectionTimeoutError as err:
    print("[✗] Failed to connect to MongoDB Atlas:", err)
    client = None  # Prevent using an invalid client

db = client["diaryApp"]
collection = db["generateRequests"]
collection2 = db ["images"]

#generate request routes
@app.route('/generate', methods=['POST'])
def queue_request():
    data = request.get_json()

    query_filter = {
        "imageName": data["imageName"],
    }

    required_fields = ["imageName"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        result = collection.replace_one(query_filter, data, upsert=True)

        if result.upserted_id:
            return jsonify({"message": "Request queued successfully (new entry created)."}), 201
        else:
            return jsonify({"message": "Request updated successfully (existing entry replaced)."}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/generate', methods=['GET'])
def get_all_requests():
    try:
        all_requests = list(collection.find())
        for request in all_requests:
            request["_id"] = str(request["_id"])  # Convert ObjectId to string
        return jsonify(all_requests), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/generate', methods=['DELETE'])
def delete_request():
    data = request.get_json()

    if not data or "imageName" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    query_filter = {
        "imageName": data["imageName"],
    }

    try:
        result = collection.delete_one(query_filter)

        if result.deleted_count > 0:
            return jsonify({"message": "Request deleted successfully."}), 200
        else:
            return jsonify({"message": "No matching request found."}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#image directory routes
@app.route('/image', methods=['POST'])
def upload_image():
    if 'image' not in request.files or 'filename' not in request.form:
        return {'error': 'Missing image or filename'}, 400
    
    image = request.files['image']
    filename = request.form['filename']

    query_filter = {
        "filename": filename,
    }

    try:
        image_bytes = image.read()
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')

        data = {
            "filename": filename,
            "image_base64": encoded_image,
        }

        result = collection2.replace_one(query_filter, data, upsert=True)

        if result.upserted_id:
            return jsonify({"message": f'Image saved as - {filename}'}), 201
        else:
            return jsonify({"message": f'Image was updated - {filename}'}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/image', methods=['GET'])
def get_all_images():
    try:
        all_images = list(collection2.find())
        for image in all_images:
            image["_id"] = str(image["_id"])  # Convert ObjectId to string
        return jsonify(all_images), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/image/<filename>', methods=['GET'])
def get_image(filename):
    image_doc = collection2.find_one({'filename': filename})

    if not image_doc:
        return {'error': 'Image not found in database'}, 404
    
    try:
        image_data = base64.b64decode(image_doc['image_base64'])
        return send_file(
            io.BytesIO(image_data),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=filename
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/image/<filename>', methods=['DELETE'])
def delete_image(filename):
    query_filter = {
        "filename": filename,
    }

    try:
        result = collection2.delete_one(query_filter)

        if result.deleted_count > 0:
            return jsonify({"message": f'Image - {filename} deleted successfully.'}), 200
        else:
            return jsonify({"message": f'Image - {filename} not found in database.'}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)