from pydantic import BaseModel
from typing import Optional

class DocumentCreate(BaseModel):
    folder_id: str
    title: str

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    folder_id: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    folder_id: str
    title: str
    status: str
    current_version_no: int
    yjs_doc_key: str
    created_by: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class DocumentListItem(BaseModel):
    id: str
    title: str
    status: str
    current_version_no: int
    created_by: str

    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]

class AuthorizeCheckResponse(BaseModel):
    allowed: bool
    resolved_role: str | None
    via_scope: str | None