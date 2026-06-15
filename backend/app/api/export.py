from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.database_models import User, Document, Version
from app.schemas.export import ExportResponse
from app.services.auth_service import authorize

router = APIRouter()


def check_permission(db: Session, user_id: str, doc_id: str, permission: str):
    """Helper to check permission and raise 403 if denied."""
    has_perm, _, _ = authorize(db, user_id, permission, "document", doc_id)
    if not has_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to {permission}"
        )


@router.get("/documents/{id}/export", response_model=ExportResponse)
def export_document(
    id: str,
    format: str = Query(..., regex="^(md|docx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Render current document (markdown or docx format)."""
    doc = db.query(Document).filter(
        Document.id == id,
        Document.org_id == current_user.org_id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check authorization
    check_permission(db, current_user.id, doc.id, "can_view_history")

    # Fetch current content from Hocuspocus/Yjs
    # In production, would fetch from yjs_doc_key
    content = f"# {doc.title}\n\nDocument content would be fetched from Hocuspocus"

    if format == "docx":
        # Convert to docx using @platejs/docx
        content = f"DOCX: {content}"
        file_name = f"{doc.title}.docx"
    else:
        # Markdown format using @platejs/markdown
        file_name = f"{doc.title}.md"

    return {
        "document_id": str(doc.id),
        "version_no": None,  # Current document has no specific version
        "format": format,
        "content": content,
        "file_name": file_name
    }


@router.get("/versions/{id}/export", response_model=ExportResponse)
def export_version(
    id: str,
    format: str = Query(..., regex="^(md|docx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Render an approved version (markdown or docx format)."""
    version = db.query(Version).filter(Version.id == id).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    doc = db.query(Document).filter(
        Document.id == version.document_id,
        Document.org_id == current_user.org_id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check authorization
    check_permission(db, current_user.id, doc.id, "can_view_history")

    # Fetch version content from S3
    # In production, would fetch and parse from version.s3_key
    content = f"# {doc.title}\n\nVersion {version.version_no} content from S3"

    if format == "docx":
        # Convert to docx using @platejs/docx
        content = f"DOCX: {content}"
        file_name = f"{doc.title}_v{version.version_no}.docx"
    else:
        # Markdown format using @platejs/markdown
        file_name = f"{doc.title}_v{version.version_no}.md"

    return {
        "document_id": str(doc.id),
        "version_no": version.version_no,
        "format": format,
        "content": content,
        "file_name": file_name
    }
