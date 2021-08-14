from tinydb import TinyDB

users_db = TinyDB('./db/users.json')
users_db.insert({'user_id': 999, 'name': 'New Person', 'history': [], 'selections': []})