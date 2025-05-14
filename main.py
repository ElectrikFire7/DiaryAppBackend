from flask import Flask, jsonify, request
from pymongo import MongoClient, errors
import os

app = Flask(__name__)
MONGO_URI = "mongodb+srv://firstUser:falooc03@cluster0.n7ftekv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info() 
    print("[✓] Successfully connected to MongoDB Atlas.")
except errors.ServerSelectionTimeoutError as err:
    print("[✗] Failed to connect to MongoDB Atlas:", err)
    client = None  # Prevent using an invalid client

db = client["diaryApp"]
collection = db["generateRequests"]

@app.route('/generate', methods=['POST'])
def queue_request():
    data = request.get_json()

    query_filter = {
        "username": data["username"],
        "date": data["date"],
        "serial_number": data["serial_number"]
    }

    required_fields = ["username", "date", "serial_number", "text_payload"]
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

if __name__ == "__main__":
    app.run(debug=True)