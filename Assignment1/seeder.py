import os
import requests
import threading
import hashlib
import bencodepy
import shutil

from flask import Flask, request, send_file, Response

TRACKER_URL = "http://127.0.0.1:5001"
app = Flask(__name__)

def get_peer_folder(port):
    folder = f"peer_{port}"
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder

def create_torrent(file_name):
    """Create a .torrent file for the given file."""
    if not os.path.exists(file_name):
        print(f" File {file_name} does not exist.")
        return

    with open(file_name, "rb") as f:
        file_data = f.read()

    piece_length = 1024 * 1024  # 1MB
    pieces = []

    for i in range(0, len(file_data), piece_length):
        piece = file_data[i:i+piece_length]
        sha1_hash = hashlib.sha1(piece).digest()
        pieces.append(sha1_hash)

    info_dict = {
        b"name": file_name.encode(),  # file name only (no path)
        b"length": len(file_data),
        b"piece length": piece_length,
        b"pieces": b"".join(pieces)
    }

    torrent_data = {
        b"announce": TRACKER_URL.encode(),
        b"info": info_dict
    }

    encoded_info = bencodepy.encode(info_dict)
    info_hash = hashlib.sha1(encoded_info).hexdigest()

    torrent_file_name = f"{file_name}.torrent"
    with open(torrent_file_name, "wb") as f:
        f.write(bencodepy.encode(torrent_data))

    print(f" .torrent file created: {torrent_file_name}")
    print(f" info_hash: {info_hash}")

def get_info_hash(torrent_file_path):
    """Returns the info_hash and piece list of the torrent file."""
    try:
        with open(torrent_file_path, "rb") as f:
            torrent_data = f.read()
        decoded_data = bencodepy.decode(torrent_data)
        info_dict = decoded_data[b"info"]
        encoded_info = bencodepy.encode(info_dict)
        info_hash = hashlib.sha1(encoded_info).hexdigest()
        pieces = info_dict[b"pieces"]
        piece_list = [pieces[i:i + 20] for i in range(0, len(pieces), 20)]
        return info_hash, piece_list
    except Exception as e:
        print(f"Error getting info_hash: {e}")
        return None, []

def announce_to_tracker(info_hash, port, shared_files):
    params = {
        "info_hash": info_hash,
        "file_names": ",".join(shared_files),
        "ip": "127.0.0.1",
        "port": port
    }
    try:
        response = requests.post(f"{TRACKER_URL}/announce", json=params)
        if response.status_code == 200:
            print(" Successfully registered with tracker.")
        else:
            print(f" Tracker registration failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f" Failed to announce to tracker: {e}")

@app.route("/download", methods=["GET"])
def download():
    file_name = request.args.get("file")
    port = 6881
    folder = get_peer_folder(port)
    file_path = os.path.join(folder, file_name)

    print(f" Received download request: {file_name}")
    print(f" Full path: {file_path}")

    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            print(f" File read successfully. Size: {len(data)} bytes")
            return Response(data, mimetype="application/octet-stream")
        else:
            print(f" File not found: {file_path}")
            return "File not found", 404
    except Exception as e:
        print(f" Error while sending file: {e}")
        return "Internal Server Error", 500

def run_peer():
    port = 6881
    file_name = input("Enter the file name to share: ").strip() #change
    peer_folder = get_peer_folder(port)

    dst_path = os.path.join(peer_folder, file_name)
    if not os.path.exists(dst_path):
        if os.path.exists(file_name):
            shutil.copy(file_name, dst_path)
            print(f" Copied {file_name} to shared folder: {peer_folder}")
        else:
            print(f" {file_name} not found. Cannot share.")
            return

    create_torrent(file_name)

    # Copy .torrent file to requester folder
    torrent_file = f"{file_name}.torrent"
    requester_folder = get_peer_folder(6882)
    shutil.copy(torrent_file, requester_folder)
    print(f".torrent file copied to requester folder: {requester_folder}")

    # Extract info_hash and announce to tracker
    info_hash, _ = get_info_hash(torrent_file)
    print(f"Info hash: {info_hash}")
    announce_to_tracker(info_hash, port, [file_name])

    # Start Flask download server
    threading.Thread(target=lambda: app.run(
        host="0.0.0.0", port=port, debug=False, use_reloader=False
    )).start()

    # input("Seeder running. Press Enter to exit...\n")

if __name__ == "__main__":
    run_peer()
