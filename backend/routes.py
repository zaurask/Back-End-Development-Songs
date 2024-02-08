from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"

print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)


def parse_json(data):
    return json.loads(json_util.dumps(data))


######################################################################
# INSERT CODE HERE
######################################################################
@app.route('/health')
def health():
    return {'status': 'OK'}


@app.route('/count')
def count():
    count = db.songs.count_documents({})
    return {'count': count}


@app.route('/song')
def songs():
    songs = db.songs.find({})

    return {"songs": json_util.dumps(songs)}


@app.route('/song/<int:song_id>')
def get_song_by_id(song_id):
    song = db.songs.find_one({'id': song_id})
    if song is None:
        return {"message": "song with id not found"}, 404

    return jsonify(json_util.dumps(song))

@app.route('/song', methods=['POST'])
def create_song():
    song_data = request.get_json()
    if db.songs.find_one({'id': song_data['id']}):
        return {"Message": f"song with id {song_data['id']} already present"}, 302

    oid = db.songs.insert_one(song_data).inserted_id

    return {"inserted id": {"$oid": str(oid)}}, 201

@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    song_data = request.get_json()
    result = db.songs.update_one({"id": id}, {"$set": song_data})

    if result.matched_count == 0:
        return {"message": "song not found"}, 404
    if result.modified_count == 0:
        return {"message": "song found, but nothing updated"}

    updated_song = db.songs.find_one({'id': id})
    return json_util.dumps(updated_song)

@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    result = db.songs.delete_one({'id': id})
    if result.deleted_count == 0:
        return {"message": "song not found"}, 404
    if result.deleted_count == 1:
        return '', 204

    return {"message": "internal server error"}, 500
