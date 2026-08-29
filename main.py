from fastapi import FastAPI
from pydantic import BaseModel
from database import conn


app = FastAPI()


@app.get("/")
def home():
    return {"message":"Appointment api is running!"}



