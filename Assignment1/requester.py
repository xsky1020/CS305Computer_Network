import os
import requests
import hashlib
import bencodepy
from flask import Flask, request, send_file

TRACKER_URL = "http://127.0.0.1:5001"

app = Flask(__name__)


def get_peer_folder(port):
    """ Returns the folder path for a specific peer and ensures it exists. """
    folder = f"peer_{port}"
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


def get_info_hash(torrent_file_path):
    """Returns the info_hash and piece list of the torrent file."""
    try:
        with open(torrent_file_path, "rb") as f:
            torrent_data = f.read()

        # Decode the torrent data (bencode format)
        decoded_data = bencodepy.decode(torrent_data)

        # Extract the 'info' dictionary
        info_dict = decoded_data[b"info"]

        # Generate the SHA1 hash of the 'info' part of the torrent
        encoded_info = bencodepy.encode(info_dict)
        info_hash = hashlib.sha1(encoded_info).hexdigest()

        # Extract the pieces in the torrent
        pieces = info_dict[b"pieces"]  # all pieces hashed and concatenated
        piece_list = [pieces[i:i + 20] for i in range(0, len(pieces), 20)]

        return info_hash, piece_list

    except Exception as e:
        print(f"Error getting info_hash from {torrent_file_path}: {e}")
        return None, []


def get_peers_from_tracker(info_hash):
    """ Requests the tracker for a list of seeders with the given info_hash. """
    try:
        response = requests.get(f"{TRACKER_URL}/get_peers", params={"info_hash": info_hash})

        if response.status_code == 200:
            return response.json()
        else:
            print(f" Tracker returned error status: {response.status_code}")
            return []

    except Exception as e:
        print(f"Error retrieving peers from tracker: {e}")
        return []


def download_file(file_name, peer_ip, peer_port, local_port):
    """ Downloads a file from another peer and saves it in this peer's folder. """
    try:
        print(f" Requesting file: {file_name} from {peer_ip}:{peer_port}")
        url = f"http://{peer_ip}:{peer_port}/download"
        params = {"file": file_name}

        response = requests.get(url, params=params)

        if response.status_code == 200:
            folder = get_peer_folder(local_port)
            file_path = os.path.join(folder, file_name)

            with open(file_path, "wb") as f:
                f.write(response.content)

            print(f" File downloaded: {file_name}, saved to: {file_path}")

        else:
            print(f" Download failed, status code: {response.status_code}")
    except Exception as e:
        print(f"️ Error downloading file: {e}")


def request_file(info_hash):
    """ Requests a file from other peers based on info_hash. """
    print(f" Fetching peers for info_hash: {info_hash}...")

    # Step 1: Get the list of seeders from the tracker
    seeders = get_peers_from_tracker(info_hash)

    if not seeders:
        print(" No available seeders found.")
        return

    print(f" Found {len(seeders)} seeder(s), starting download...")

    # Step 2: Download the shared file from the first seeder
    selected_seeder = seeders[0]
    file_name = selected_seeder["file_names"][0]
    peer_ip = selected_seeder["ip"]
    peer_port = selected_seeder["port"]

    print(f" Downloading {file_name} from Seeder {peer_ip}:{peer_port}")
    download_file(file_name, peer_ip, peer_port, local_port=6882)


def run_peer():
    """ Starts the requester's peer logic. """
    port = 6882
    peer_folder = get_peer_folder(port)

    print(f" Requester running on port {port}, download folder: {peer_folder}")
    print("Ready to request and download a file.")

    # Step 1: Ask user to provide .torrent file path
    torrent_file_path = input("Enter the path to the .torrent file (e.g. peer_6882/example.txt.torrent): ")
    if not os.path.exists(torrent_file_path):
        print(" The specified .torrent file does not exist. Please check the path.")
        return

    # Step 2: Parse info_hash from torrent
    info_hash, _ = get_info_hash(torrent_file_path)

    if not info_hash:
        print(" Could not parse info_hash from .torrent file.")
        return

    print(f" Retrieved info_hash: {info_hash}")

    # Step 3: Start requesting the file
    request_file(info_hash)


if __name__ == "__main__":
    run_peer()
