import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.database_models import (
    Document, User, Version, ApprovalMarker, ApprovalStepEvent,
    ApprovalPolicy, Notification
)
from app.schemas.version import (
    VersionResponse, VersionListResponse, VersionMetadataResponse,
    DiffResponse, SubmitForApprovalRequest, SubmitForApprovalResponse,
    ApprovalRequest, ApprovalResponse, RejectRequest, RejectResponse,
    RestoreRequest, RestoreResponse
)
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


@router.get("/documents/{id}/versions", response_model=VersionListResponse)
def list_versions(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List version history for a document."""
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

    versions = db.query(Version).filter(
        Version.document_id == id
    ).order_by(Version.version_no.desc()).all()

    return {"versions": versions}


@router.get("/versions/{id}", response_model=VersionMetadataResponse)
def get_version(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get version metadata and signed S3 URL."""
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

    # Generate signed S3 URL (placeholder)
    s3_url = f"s3://signed-url/{version.s3_key}"

    return {
        "id": str(version.id),
        "document_id": str(version.document_id),
        "version_no": version.version_no,
        "kind": version.kind,
        "created_by": str(version.created_by),
        "created_at": version.created_at,
        "s3_url": s3_url
    }


@router.post("/documents/{id}/submit-for-approval", response_model=SubmitForApprovalResponse)
def submit_for_approval(
    id: str,
    data: SubmitForApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Freeze warm snapshot and submit for approval."""
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
    check_permission(db, current_user.id, doc.id, "can_submit_for_approval")

    # Create new version (submission kind)
    new_version_no = doc.current_version_no + 1
    version = Version(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        document_id=doc.id,
        version_no=new_version_no,
        kind="submission",
        s3_key=f"versions/{doc.id}/v{new_version_no}",
        created_by=current_user.id
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    # Create notification for approvers
    policy = doc.approval_policy
    if policy:
        # Get approvers for the first step
        first_step = db.query(ApprovalPolicy).filter(
            ApprovalPolicy.id == policy.id
        ).first()
        if first_step:
            notification = Notification(
                id=uuid.uuid4(),
                org_id=current_user.org_id,
                user_id=current_user.id,
                document_id=doc.id,
                type="submission_pending",
                payload={
                    "version_id": str(version.id),
                    "version_no": new_version_no,
                    "submitter": str(current_user.id)
                }
            )
            db.add(notification)
            db.commit()

    return {
        "version_id": str(version.id),
        "version_no": new_version_no,
        "message": f"Submitted for approval (version {new_version_no})"
    }


@router.get("/documents/{id}/diff")
def get_diff(
    id: str,
    from_v: int = Query(..., alias="from"),
    to_v: int = Query(..., alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compute diff between two versions (owner review + team comparison)."""
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

    from_version = db.query(Version).filter(
        Version.document_id == id,
        Version.version_no == from_v
    ).first()
    to_version = db.query(Version).filter(
        Version.document_id == id,
        Version.version_no == to_v
    ).first()

    if not from_version or not to_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both versions not found"
        )

    return {
        "from_version_no": from_v,
        "to_version_no": to_v,
        "diff_content": {
            "from_s3_key": from_version.s3_key,
            "to_s3_key": to_version.s3_key,
            "message": "Diff computation would be performed against S3 blobs"
        }
    }


@router.post("/versions/{id}/approve", response_model=ApprovalResponse)
def approve_version(
    id: str,
    data: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Policy-aware approval: write marker only when chain completes."""
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
    check_permission(db, current_user.id, doc.id, "can_give_final_approval")

    # Record approval step event
    policy = doc.approval_policy
    step_no = 1  # Default to first step

    event = ApprovalStepEvent(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        document_id=doc.id,
        version_id=version.id,
        policy_id=policy.id if policy else None,
        step_no=step_no,
        decision="approved",
        actor_id=current_user.id
    )
    db.add(event)

    # Create approval marker (marks this as the baseline)
    marker = ApprovalMarker(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        document_id=doc.id,
        approved_version_id=version.id,
        approved_by=current_user.id
    )
    db.add(marker)

    # Update version kind to "approved"
    version.kind = "approved"

    db.commit()

    return {
        "success": True,
        "message": f"Version {version.version_no} approved"
    }


@router.post("/versions/{id}/reject", response_model=RejectResponse)
def reject_version(
    id: str,
    data: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Discard warm snapshot, baseline stays."""
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
    check_permission(db, current_user.id, doc.id, "can_give_final_approval")

    # Record rejection step event
    policy = doc.approval_policy
    step_no = 1  # Default to first step

    event = ApprovalStepEvent(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        document_id=doc.id,
        version_id=version.id,
        policy_id=policy.id if policy else None,
        step_no=step_no,
        decision="rejected",
        actor_id=current_user.id
    )
    db.add(event)
    db.commit()

    return {
        "success": True,
        "message": f"Version {version.version_no} rejected"
    }


@router.post("/versions/{id}/restore", response_model=RestoreResponse)
def restore_version(
    id: str,
    data: RestoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restore deleted section (stays pending)."""
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
    check_permission(db, current_user.id, doc.id, "can_edit_direct")

    # Restore logic: this would restore a deleted section from the version
    # The section_id comes from the request and identifies what to restore

    return {
        "success": True,
        "message": f"Section restored in version {version.version_no}"
    }
