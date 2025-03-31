from flask import Flask, request, jsonify
import hashlib
import json

app = Flask(__name__)

# This will act as our in-memory tracker database
TRACKER_DB = {}

@app.route("/announce", methods=["GET", "POST"])
def announce():
    """ Handle announcements from seeders. """
    # Define a structure to store announcement information of seeders
    try:
        if request.method == "POST":
            data = request.get_json(force=True)
        else:
            data = request.args

        info_hash = data.get("info_hash")
        file_names = data.get("file_names")
        ip = data.get("ip")
        port = data.get("port")

        if not all([info_hash, file_names, ip, port]):
            return jsonify({"error": "Missing parameters"}), 400

        if isinstance(file_names, str):
            file_names = file_names.split(",")

        if info_hash not in TRACKER_DB:
            TRACKER_DB[info_hash] = []

        peer_info = {"ip": ip, "port": port, "file_names": file_names}

        if peer_info not in TRACKER_DB[info_hash]:
            TRACKER_DB[info_hash].append(peer_info)

        return jsonify({"status": "Seeder registered successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    # Process the announcement received and store the received information

@app.route("/get_peers", methods=["GET"])
def get_seeders():
    """ Get the list of seeders for a given info_hash. """
    info_hash = request.args.get("info_hash")
    if info_hash is None:
        return jsonify({"error": "Missing info_hash"}), 400

    seeders = TRACKER_DB.get(info_hash, [])
    return jsonify(seeders)

@app.route("/show_tracker_data", methods=["GET"])
def show_tracker_data():
    """ Show the entire tracker data. """
    return jsonify(TRACKER_DB)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)