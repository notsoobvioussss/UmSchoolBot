import certifi
from pymongo import MongoClient

ca = certifi.where()
client = MongoClient(config.MONGODB_URI, tlsCAFile=ca)
db = client.ege_scores

def init_db():
    db.students.create_index("user_id", unique=True)
    db.scores.create_index([("user_id", 1), ("subject", 1)], unique=True)

def register_student(user_id, first_name, last_name):
    db.students.insert_one({"user_id": user_id, "first_name": first_name, "last_name": last_name})

def is_registered(user_id):
    return db.students.find_one({"user_id": user_id}) is not None

def enter_score(user_id, subject, score):
    db.scores.update_one(
        {"user_id": user_id, "subject": subject},
        {"$set": {"score": score}},
        upsert=True
    )

def get_scores(user_id):
    return list(db.scores.find({"user_id": user_id}, {"_id": 0, "subject": 1, "score": 1}))
