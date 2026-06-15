from pydantic import BaseModel
from typing import Optional

class FolderCreate(BaseModel):
    name: str
    parent_folder_id: Optional[str] = None

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_folder_id: Optional[str] = None

class FolderResponse(BaseModel):
    id: str
    name: str
    parent_folder_id: Optional[str]
    created_by: str

    class Config:
        from_attributes = True

class FolderTreeItem(BaseModel):
    id: str
    name: str
    parent_folder_id: Optional[str]
    created_by: str
    created_at: str

    class Config:
        from_attributes = True

class FolderListResponse(BaseModel):
    folders: list[FolderTreeItem]