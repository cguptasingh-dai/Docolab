import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.database_models import Folder, User, Document
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate, FolderTreeItem, FolderListResponse
from app.services.auth_service import authorize

router = APIRouter()

@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(data: FolderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.parent_folder_id:
        parent = db.query(Folder).filter(Folder.id == data.parent_folder_id).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent folder not found")

    folder = Folder(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        parent_folder_id=data.parent_folder_id,
        name=data.name,
        created_by=current_user.id
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder

@router.get("", response_model=FolderListResponse)
def list_folders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all folders in the current user's organization"""
    folders = db.query(Folder).filter(Folder.org_id == current_user.org_id).all()
    items = [
        FolderTreeItem(
            id=str(f.id),
            name=f.name,
            parent_folder_id=str(f.parent_folder_id) if f.parent_folder_id else None,
            created_by=str(f.created_by),
            created_at=f.created_at.isoformat()
        )
        for f in folders
    ]
    return {"folders": items}

@router.get("/{id}", response_model=FolderResponse)
def get_folder(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a single folder by ID"""
    folder = db.query(Folder).filter(Folder.id == id, Folder.org_id == current_user.org_id).first()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder

@router.patch("/{id}", response_model=FolderResponse)
def update_folder(
    id: str, 
    data: FolderUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Update folder (rename or move to different parent)"""
    folder = db.query(Folder).filter(Folder.id == id, Folder.org_id == current_user.org_id).first()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    
    # Update name
    if data.name is not None:
        folder.name = data.name
    
    # Update parent folder
    if data.parent_folder_id is not None:
        if data.parent_folder_id:
            parent = db.query(Folder).filter(Folder.id == data.parent_folder_id, Folder.org_id == current_user.org_id).first()
            if not parent:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent folder not found")
        folder.parent_folder_id = data.parent_folder_id
    
    db.commit()
    db.refresh(folder)
    return folder

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete an empty folder"""
    folder = db.query(Folder).filter(Folder.id == id, Folder.org_id == current_user.org_id).first()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    
    # Check if folder has any subfolders or documents
    has_children = db.query(Folder).filter(Folder.parent_folder_id == id).first() is not None
    has_documents = db.query(Document).filter(Document.folder_id == id).first() is not None
    
    if has_children or has_documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cannot delete folder with children or documents"
        )
    
    db.delete(folder)
    db.commit()