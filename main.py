from flask import Flask, jsonify, request, send_file
from pymongo import MongoClient, errors
from dotenv import load_dotenv
import os, subprocess
import base64

load_dotenv()

app = Flask(__name__)
MONGO_URI = os.getenv("MONGO_URI")
KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME")
KAGGLE_KEY = os.getenv("KAGGLE_KEY")

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
usersCollections = db["users"]

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
        return jsonify({
            'filename': image_doc['filename'],
            'image_base64': image_doc['image_base64']
        }), 200

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
    
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    query_filter = {
        "username": data["username"],
        "password": data["password"]
    }

    try:
        user = usersCollections.find_one(query_filter)

        if user:
            return jsonify({"message": "Login successful."}), 200
        else:
            return jsonify({"message": "Invalid username or password."}), 401
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    query_filter = {
        "username": data["username"],
    }

    try:
        existing_user = usersCollections.find_one(query_filter)

        if existing_user:
            return jsonify({"message": "Username already exists."}), 409

        new_user = {
            "username": data["username"],
            "password": data["password"]
        }

        result = usersCollections.insert_one(new_user)
        print(f"New user created with ID: {result}")

        return jsonify({"message": "User created successfully."}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/generationscript', methods=['POST'])
def run_generation_script():
    try:
        # Ensure the environment variables are set
        if not KAGGLE_USERNAME or not KAGGLE_KEY:
            return jsonify({"error": "Kaggle credentials are not set."}), 400
        
        env = os.environ.copy()
        env['KAGGLE_USERNAME'] = KAGGLE_USERNAME
        env['KAGGLE_KEY'] = KAGGLE_KEY

        # Run the Kaggle command to generate images
        subprocess.run(["kaggle", "kernels", "push", "-p", "notebooks"], check=True, env=env)

        return jsonify({"message": "Generation script started successfully."}), 200
    
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Script execution failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)