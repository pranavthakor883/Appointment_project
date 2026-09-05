from pydantic import BaseModel


class ServiceCreate(BaseModel):
    provider_id:int
    name:str
    description:str | None=None
    duration_minutes:int
    price:float
