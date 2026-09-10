from pydantic import BaseModel, Field


#day_of_week 1-7 mirrors the CHECK constraint in schema.sql (ISO: 1=Monday)
class AvailabilityCreate(BaseModel):
    provider_id:int
    day_of_week:int = Field(ge=1, le=7)
    start_time:str
    end_time:str


class AvailabilityUpdate(BaseModel):
    day_of_week : int | None = Field(default=None, ge=1, le=7)
    start_time : str | None = None
    end_time : str | None = None
