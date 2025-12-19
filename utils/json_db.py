import json, os

DATA_FOLDER = "data"

def load_json(file_name):
    path = os.path.join(DATA_FOLDER, file_name)
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump([], f)
    with open(path, "r") as f:
        return json.load(f)

def save_json(file_name, data):
    path = os.path.join(DATA_FOLDER, file_name)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
