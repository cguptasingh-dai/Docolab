from pydantic import BaseModel
from typing import Optional


class AIJobResponse(BaseModel):
    job_id: str
    status: str  # pending / processing / completed / failed
    created_at: str
    result: Optional[dict] = None

    class Config:
        from_attributes = True


class AISuggestRequest(BaseModel):
    pass


class AISuggestResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ApplyAIRecommendationRequest(BaseModel):
    pass


class ApplyAIRecommendationResponse(BaseModel):
    job_id: str
    status: str
    message: str


class AIJobStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True
