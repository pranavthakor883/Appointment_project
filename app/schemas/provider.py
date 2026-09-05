from pydantic import BaseModel


class ProviderCreate(BaseModel):
    user_id: int
    specialization: str
    description: str | None = None
