from pydantic import BaseModel
from typing import Optional


class ExportResponse(BaseModel):
    document_id: str
    version_no: Optional[int] = None
    format: str  # md / docx
    content: str
    file_name: str

    class Config:
        from_attributes = True
