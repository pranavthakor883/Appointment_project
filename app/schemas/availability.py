from pydantic import BaseModel


class AvailabilityCreate(BaseModel):
    provider_id:int
    day_of_week:int
    start_time:str
    end_time:str
