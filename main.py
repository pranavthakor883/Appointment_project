from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()


@app.get("/")
def home():
    return {"message":"Hello Home!"}