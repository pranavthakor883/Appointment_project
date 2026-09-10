from pydantic import BaseModel, Field


#the limits mirror the CHECK constraints in schema.sql so a bad value is a
#clean 422 at the edge instead of a database error travelling back to the client
class ServiceCreate(BaseModel):
    provider_id:int
    name:str = Field(min_length=1)
    description:str | None=None
    duration_minutes:int = Field(gt=0, le=480)
    price:float = Field(ge=0)

class ServiceUpdate(BaseModel):
    name : str | None = Field(default=None, min_length=1)
    description : str | None = None
    duration_minutes : int |None = Field(default=None, gt=0, le=480)
    price : float | None = Field(default=None, ge=0)
