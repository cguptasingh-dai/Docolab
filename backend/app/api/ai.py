import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.database_models import User, Document, Recommendation, Version, Suggestion
from app.schemas.ai import (
    AISuggestRequest, AISuggestResponse, ApplyAIRecommendationRequest,
    ApplyAIRecommendationResponse, AIJobStatusResponse
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


@router.post("/documents/{id}/ai/suggest", response_model=AISuggestResponse)
def suggest_ai(
    id: str,
    data: AISuggestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enqueue AI job; return job id (rate/budget checked)."""
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
    check_permission(db, current_user.id, doc.id, "can_suggest")

    # Check rate limit and budget (placeholder)
    # In production, would check against quotas table

    # Enqueue AI job (placeholder - would integrate with job queue)
    job_id = str(uuid.uuid4())

    # Store job metadata somewhere (job queue table)
    # For now, we'll just return the job_id

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"AI suggestion job enqueued"
    }


@router.post("/recommendations/{id}/ai/apply", response_model=ApplyAIRecommendationResponse)
def apply_ai_recommendation(
    id: str,
    data: ApplyAIRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """AI drafts suggestions for a recommendation."""
    recommendation = db.query(Recommendation).filter(
        Recommendation.id == id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    doc = db.query(Document).filter(
        Document.id == recommendation.document_id,
        Document.org_id == current_user.org_id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check authorization
    check_permission(db, current_user.id, doc.id, "can_suggest")

    # Enqueue AI job for drafting suggestions
    job_id = str(uuid.uuid4())

    # Create suggestion for the recommendation (placeholder)
    suggestion = Suggestion(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        document_id=doc.id,
        author_id=None,  # AI-authored
        origin="ai",
        type="insert",
        anchor=recommendation.anchor,
        status="pending",
        reason="AI-generated suggestion from recommendation"
    )
    db.add(suggestion)
    db.commit()

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"AI drafting suggestions for recommendation"
    }


@router.get("/ai/jobs/{job_id}", response_model=AIJobStatusResponse)
def get_ai_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Poll job status."""
    # Fetch job metadata from job queue table (placeholder)
    # In production, would check a job_queue or similar table

    # For now, return a mock response
    return {
        "job_id": job_id,
        "status": "completed",
        "created_at": None,
        "completed_at": None,
        "result": {
            "suggestions_created": 1,
            "message": "Job completed successfully"
        },
        "error": None
    }
