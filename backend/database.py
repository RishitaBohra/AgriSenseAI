from pymongo import MongoClient

MONGO_URL = "mongodb+srv://rishitabohra1575:ganeshji123@cluster0.9yd9znn.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URL)

db = client["agrisense_ai"]   # our new database
forecast_collection = db["forecasts"]
decision_collection = db["decisions"]
