# app/main.py
from fastapi import FastAPI
from sqlalchemy import select  # <-- Added for async queries
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.models.database_models import Role, RolePermission, User, Assignment
from app.core.security import get_password_hash
from app.api import auth, roles, folders, assignments, documents, users, versions, notifications, ai, export

app = FastAPI(title=settings.PROJECT_NAME)

# Mount Routers (using flat routes under app.api)
app.include_router(auth.router, prefix=f"{settings.API_STR}/auth", tags=["Authentication"])
app.include_router(roles.router, prefix=f"{settings.API_STR}/roles", tags=["Roles"])
app.include_router(folders.router, prefix=f"{settings.API_STR}/folders", tags=["Folders"])
app.include_router(assignments.router, prefix=f"{settings.API_STR}/assignments", tags=["Assignments"])
app.include_router(documents.router, prefix=f"{settings.API_STR}/documents", tags=["Documents"])
app.include_router(users.router, prefix=f"{settings.API_STR}/users", tags=["Users"])
app.include_router(versions.router, prefix=f"{settings.API_STR}/versions", tags=["Versioning & Approval"])
app.include_router(notifications.router, prefix=f"{settings.API_STR}/notifications", tags=["Notifications"])
app.include_router(ai.router, prefix=f"{settings.API_STR}/ai", tags=["AI Suggestions"])
app.include_router(export.router, prefix=f"{settings.API_STR}/export", tags=["Export"])

@app.on_event("startup")
async def startup_event():
    # 1. Create tables asynchronously
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Use an async session context manager (handles closing automatically)
    async with SessionLocal() as db:
        try:
            # Seed Roles (Async query syntax)
            role_query = await db.execute(select(Role))
            if role_query.scalars().first() is None:
                owner = Role(id="role-owner", name="owner")
                editor = Role(id="role-editor", name="editor")
                viewer = Role(id="role-viewer", name="viewer")
                db.add_all([owner, editor, viewer])
                await db.commit()  # <-- Must be awaited

                # Seed Permissions
                owner_perms = [
                    "can_edit_direct", "can_suggest", "can_resolve_suggestion",
                    "can_submit_for_approval", "can_give_final_approval",
                    "can_approve_level", "can_manage_approval_policy",
                    "can_view_history", "can_manage_members"
                ]
                editor_perms = ["can_edit_direct", "can_suggest", "can_view_history"]
                
                for p in owner_perms:
                    db.add(RolePermission(role_id=owner.id, permission=p))
                for p in editor_perms:
                    db.add(RolePermission(role_id=editor.id, permission=p))
                    
                await db.commit()  # <-- Must be awaited
                
            # Seed Admin User
            admin_query = await db.execute(select(User).where(User.email == "admin@acme.com"))
            if admin_query.scalars().first() is None:
                admin_user = User(
                    id="user-admin-id",
                    org_id="org-acme-id",
                    email="admin@acme.com",
                    password_hash=get_password_hash("adminsecret"),
                    display_name="Admin User",
                    status="active"
                )
                db.add(admin_user)
                await db.commit()  # <-- Must be awaited

                # Seed bootstrap role assignment
                root_assignment = Assignment(
                    id="assignment-admin-root",
                    org_id="org-acme-id",
                    user_id=admin_user.id,
                    role_id="role-owner",
                    scope_type="folder",
                    scope_id="root-folder-id"
                )
                db.add(root_assignment)
                await db.commit()  # <-- Must be awaited

        except Exception as e:
            await db.rollback()  # <-- Rollback must be awaited on error
            raise e