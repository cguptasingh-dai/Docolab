from pydantic import BaseModel
from typing import Optional


class VersionResponse(BaseModel):
    id: str
    document_id: str
    version_no: int
    kind: str  # submission / approved
    created_by: str
    created_at: str
    s3_key: str

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    versions: list[VersionResponse]


class VersionMetadataResponse(BaseModel):
    id: str
    document_id: str
    version_no: int
    kind: str
    created_by: str
    created_at: str
    s3_url: str  # Signed S3 URL

    class Config:
        from_attributes = True


class DiffResponse(BaseModel):
    from_version_no: int
    to_version_no: int
    diff_content: dict  # Diff data structure


class SubmitForApprovalRequest(BaseModel):
    pass


class SubmitForApprovalResponse(BaseModel):
    version_id: str
    version_no: int
    message: str


class ApprovalRequest(BaseModel):
    pass


class ApprovalResponse(BaseModel):
    success: bool
    message: str


class RejectRequest(BaseModel):
    pass


class RejectResponse(BaseModel):
    success: bool
    message: str


class RestoreRequest(BaseModel):
    section_id: str


class RestoreResponse(BaseModel):
    success: bool
    message: str
