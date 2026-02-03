from pydantic import BaseModel

class AppError(BaseModel):
    code: str
    message: str
