from fastapi import FastAPI

from app.api.routers import auth, availability, providers, services, users

app = FastAPI()

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(providers.router)
app.include_router(services.router)
app.include_router(availability.router)


@app.get("/")
def home():
    return {"message":"Appointment api is running!"}
