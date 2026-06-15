# 🏗️ Docolab API Architecture & Communication Flow

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Request Lifecycle](#request-lifecycle)
3. [Authentication Flow](#authentication-flow)
4. [Authorization System](#authorization-system)
5. [API Communication Patterns](#api-communication-patterns)
6. [Detailed Examples](#detailed-examples)
7. [Error Handling](#error-handling)

---

## System Architecture

### Technology Stack
```
┌─────────────────────────────────────────────────────┐
│                    CLIENT (Browser/App)             │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP/HTTPS + JSON
                   │
┌──────────────────▼──────────────────────────────────┐
│              FastAPI Web Server                     │
│  (app/main.py) - Entry point, router registration  │
└──────────┬─────────────────────────────────┬────────┘
           │                                 │
    ┌──────▼──────┐              ┌──────────▼──────┐
    │   API Routes│              │  Middleware     │
    │  (/api/*)   │              │  (Auth, CORS)   │
    └──────┬──────┘              └──────────┬──────┘
           │                                │
    ┌──────▼──────────────────────────────▼──────┐
    │    Request → Endpoint Handler             │
    │    (app/api/*.py routers)                 │
    └──────┬──────────────────────────────────┬─┘
           │                                  │
    ┌──────▼────────────┐           ┌────────▼────────┐
    │  Authentication   │           │  Authorization  │
    │  (get_current_    │           │  (authorize())  │
    │   user via JWT)   │           │                 │
    └──────┬────────────┘           └────────┬────────┘
           │                                  │
    ┌──────▼──────────────────────────────────▼──────┐
    │    Business Logic Layer                       │
    │    (app/services/*.py)                        │
    └──────┬────────────────────────────────────────┘
           │
    ┌──────▼──────────────────────────────────────┐
    │    SQLAlchemy ORM                           │
    │    (app/models/database_models.py)          │
    └──────┬────────────────────────────┬─────────┘
           │                            │
    ┌──────▼─────────────────────────────▼──────┐
    │       PostgreSQL Database                 │
    │  (18 tables: users, documents, etc.)      │
    └──────────────────────────────────────────┘
```

### Directory Structure
```
app/
├── main.py                          # 1️⃣ Entry point - registers all routes
├── core/
│   ├── config.py                   # Settings (API_STR, DATABASE_URL, etc.)
│   ├── database.py                 # SQLAlchemy setup & session management
│   └── security.py                 # Password hashing & JWT token creation
├── api/
│   ├── deps.py                     # 2️⃣ Dependency injection (get_current_user)
│   ├── auth.py                     # /api/auth/* endpoints
│   ├── users.py                    # /api/users/* endpoints
│   ├── folders.py                  # /api/folders/* endpoints
│   ├── documents.py                # /api/documents/* endpoints
│   ├── assignments.py              # /api/assignments/* endpoints
│   └── roles.py                    # /api/roles/* endpoints
├── models/
│   └── database_models.py          # SQLAlchemy table definitions
├── schemas/
│   ├── auth.py                     # Pydantic models for request/response
│   ├── folder.py
│   ├── document.py
│   ├── assignment.py
│   ├── role.py
│   └── user.py
└── services/
    └── auth_service.py             # 3️⃣ Authorization logic (authorize())
```

---

## Request Lifecycle

### Step-by-Step Flow of a Request

```
CLIENT REQUEST
    │
    ├─ POST /api/auth/signup
    │  {
    │    "email": "alice@test.com",
    │    "password": "hunter2",
    │    "display_name": "Alice"
    │  }
    │
    ▼
FASTAPI ROUTER RECEIVES REQUEST
    │
    ├─ URL matches: POST /api/auth/signup
    ├─ FastAPI routes it to: app/api/auth.py → signup()
    │
    ▼
VALIDATION LAYER (Pydantic)
    │
    ├─ Pydantic schema validates input
    │  ├─ email: EmailStr (must be valid email format)
    │  ├─ password: str (required)
    │  └─ display_name: str (required)
    │
    ├─ If invalid: return 422 Validation Error
    │
    ▼
ENDPOINT HANDLER (signup function)
    │
    ├─ Get database session: db: Session = Depends(get_db)
    │
    ├─ Execute business logic:
    │  ├─ Query: SELECT * FROM users WHERE email = ?
    │  ├─ If exists: return 409 Conflict
    │  ├─ Hash password: bcrypt.hash(password)
    │  ├─ Create User object
    │  ├─ db.add(user)
    │  ├─ db.commit()
    │  └─ db.refresh(user) [reload from DB]
    │
    ├─ Create JWT token:
    │  ├─ Encode: {"exp": expiry, "sub": user_id}
    │  ├─ Sign with SECRET_KEY using HS256
    │
    ├─ Return response:
    │  └─ {
    │       "user": {...},
    │       "token": "eyJhbGciOiJIUzI1NiIs..."
    │     }
    │
    ▼
PYDANTIC SERIALIZATION
    │
    ├─ response_model=Token tells FastAPI:
    │  "Validate output matches Token schema"
    │
    ├─ Return: 201 Created (HTTP status code)
    │
    ▼
CLIENT RECEIVES RESPONSE
    │
    └─ {
        "user": {
          "id": "uuid-1234",
          "email": "alice@test.com",
          "display_name": "Alice",
          "avatar_color": "#7aa2f7",
          "status": "active",
          "created_at": "2026-06-15T10:30:00Z"
        },
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      }
```

---

## Authentication Flow

### JWT Token-Based Authentication

```
SIGNUP/LOGIN
    │
    ├─ User provides: email + password
    ├─ Server verifies password: bcrypt.verify()
    ├─ If valid, generates JWT token
    │
    ▼
JWT TOKEN STRUCTURE
    │
    ├─ Header:     {"alg": "HS256", "typ": "JWT"}
    ├─ Payload:    {"sub": "user-id", "exp": 1718443800}
    ├─ Signature:  HMACSHA256(base64(header) + "." + base64(payload), SECRET_KEY)
    │
    ├─ Full Token: header.payload.signature
    │             (all base64url encoded)
    │
    ▼
CLIENT STORES TOKEN
    │
    ├─ localStorage.setItem("token", token)
    │
    ▼
SUBSEQUENT REQUESTS (authenticated endpoints)
    │
    ├─ POST /api/folders
    │  Headers: {
    │    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIs..."
    │  }
    │
    ▼
SERVER RECEIVES REQUEST WITH TOKEN
    │
    ├─ Extract token from: "Authorization: Bearer <token>"
    ├─ FastAPI's OAuth2PasswordBearer dependency extracts it
    ├─ Call: jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    │
    ├─ If decode fails (invalid signature/expired):
    │  └─ Return 401 Unauthorized
    │
    ├─ Extract: user_id = payload["sub"]
    ├─ Query: SELECT * FROM users WHERE id = ?
    ├─ If not found: return 401 Unauthorized
    │
    ├─ If user.status == "disabled":
    │  └─ Return 403 Forbidden
    │
    ▼
get_current_user() RETURNS USER OBJECT
    │
    └─ Now the endpoint handler has authenticated user context
```

### Code Flow Example

```python
# 1️⃣ CLIENT SENDS LOGIN REQUEST
POST /api/auth/login
{
  "email": "alice@test.com",
  "password": "hunter2"
}

# 2️⃣ SERVER RECEIVES & PROCESSES
@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(subject=user.id)
    return {"user": user, "token": token}

# 3️⃣ SERVER RETURNS TOKEN
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLWlkLTEyMzQiLCJleHAiOjE3MTg0NDM4MDB9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "user": {...}
}

# 4️⃣ CLIENT SENDS SUBSEQUENT REQUEST WITH TOKEN
GET /api/folders
Headers: {
  "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

# 5️⃣ SERVER PROCESSES AUTHENTICATED REQUEST
@router.get("", response_model=FolderListResponse)
def list_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # ← Token validated here
):
    # current_user is NOW populated with the authenticated user
    folders = db.query(Folder).filter(Folder.org_id == current_user.org_id).all()
    return {"folders": folders}
```

---

## Authorization System

### Role-Based Access Control (RBAC)

```
DATABASE SCHEMA
    │
    ├─ users table: id, email, status, org_id, ...
    ├─ roles table: id, org_id, name (owner/editor/viewer)
    ├─ role_permissions table: role_id, permission
    │  └─ Permissions: can_edit_direct, can_manage_members, etc.
    ├─ assignments table: user_id, role_id, scope_type, scope_id
    │  └─ Scopes: folder_id or document_id
    │
    ▼
EXAMPLE HIERARCHY
    │
    User: Alice (user-id-1234)
    Org: ACME Corp (org-acme)
    │
    ├─ Folder: "Projects" (folder-001)
    │  │
    │  ├─ Assignment: Alice → owner → folder-001
    │  │            (due to root role)
    │  │
    │  └─ Document: "Q1 Roadmap" (doc-001)
    │     │
    │     └─ Assignment: Bob → editor → doc-001
    │        (through folder inherited)
    │
    ├─ Role: owner
    │  └─ Permissions:
    │     ├─ can_edit_direct
    │     ├─ can_manage_members
    │     ├─ can_give_final_approval
    │     └─ ... (9 total)
    │
    └─ Role: editor
       └─ Permissions:
          ├─ can_edit_direct
          ├─ can_suggest
          └─ can_view_history
    │
    ▼
AUTHORIZATION CHECK FLOW
    │
    ├─ API receives request: DELETE /api/assignments/:id
    ├─ Has current_user (from JWT token)
    ├─ Check permission: authorize(db, user_id, "can_manage_members", "folder", folder_id)
    │
    ├─ authorize() function does:
    │  ├─ Query assignments where user_id=user_id AND scope_id=folder_id
    │  ├─ Find user's role in that scope
    │  ├─ Get all permissions for that role
    │  ├─ Check if "can_manage_members" is in permissions
    │  ├─ Return (allowed: bool, role_name: str, via_scope: str)
    │
    ├─ If allowed == False:
    │  └─ Return 403 Forbidden
    │
    ├─ If allowed == True:
    │  └─ Proceed with operation
    │
    ▼
EXAMPLE REQUEST WITH AUTH CHECK
    │
    └─ DELETE /api/assignments/{id}
       Endpoint checks: can_manage_members on scope
       │
       ├─ Get assignment: user_id=Bob, role_id=editor, scope=folder-001
       ├─ Check: Does Alice have can_manage_members on folder-001?
       ├─ Alice has assignment: owner role on folder-001
       ├─ Owner role has: can_manage_members ✅
       ├─ Authorization PASSED
       └─ Delete assignment & log audit event
```

### Code Example

```python
# FROM: app/services/auth_service.py
def authorize(db, user_id, permission, scope_type, scope_id):
    """
    Check if user has permission on a specific scope.
    Returns: (allowed: bool, resolved_role: str, via_scope: str)
    """
    # 1. Find user's assignment on this scope
    assignment = db.query(Assignment).filter(
        Assignment.user_id == user_id,
        Assignment.scope_type == scope_type,
        Assignment.scope_id == scope_id
    ).first()
    
    if not assignment:
        return (False, None, None)
    
    # 2. Get user's role
    role = db.query(Role).filter(Role.id == assignment.role_id).first()
    
    # 3. Get all permissions for this role
    permissions = db.query(RolePermission).filter(
        RolePermission.role_id == role.id
    ).all()
    
    # 4. Check if required permission exists
    permission_names = [p.permission for p in permissions]
    
    if permission in permission_names:
        return (True, role.name, scope_id)
    else:
        return (False, role.name, scope_id)


# USAGE IN ENDPOINT
@router.delete("/{id}", status_code=204)
def delete_assignment(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get assignment to revoke
    assignment = db.query(Assignment).filter(Assignment.id == id).first()
    
    # CHECK AUTHORIZATION
    allowed, _, _ = authorize(
        db,
        current_user.id,
        "can_manage_members",  # Required permission
        assignment.scope_type,
        assignment.scope_id
    )
    
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="You don't have can_manage_members permission on this scope"
        )
    
    # Authorization passed, proceed
    db.delete(assignment)
    db.commit()
```

---

## API Communication Patterns

### 1️⃣ Simple CRUD with Authentication

```
POST /api/folders
├─ Input: { "name": "Projects", "parent_folder_id": null }
├─ Dependencies:
│  ├─ get_db: Provides SQLAlchemy session
│  └─ get_current_user: Validates JWT, returns User object
├─ Business Logic:
│  ├─ Generate UUID for new folder
│  ├─ Set org_id from current_user.org_id (org isolation)
│  ├─ db.add(folder)
│  ├─ db.commit()
│  └─ db.refresh(folder)
└─ Output: { "id": "uuid-abc", "name": "Projects", ... }
```

### 2️⃣ Nested Resource Creation

```
POST /api/documents
├─ Input: { "folder_id": "uuid-abc", "title": "Roadmap" }
├─ Validation:
│  ├─ Check folder exists: db.query(Folder).filter(Folder.id == folder_id)
│  ├─ If not found: return 400 Bad Request
│  ├─ If found: proceed
├─ Create Document:
│  ├─ Generate Yjs doc key (for live editing)
│  ├─ Set status = "working"
│  ├─ Link to folder
│  └─ Link to creator (current_user.id)
└─ Output: Document with Yjs doc key
```

### 3️⃣ Authorization-Gated Operation

```
POST /api/assignments (assign role to user)
├─ Input: { "user_id": "...", "role_id": "...", "scope_type": "folder", "scope_id": "..." }
├─ Authentication: JWT decoded → current_user
├─ Authorization Check:
│  └─ authorize(db, current_user.id, "can_manage_members", scope_type, scope_id)
│     └─ If False: return 403 Forbidden
│     └─ If True: proceed
├─ Validation:
│  ├─ Does user exist?
│  ├─ Does role exist?
│  ├─ Does scope (folder/document) exist?
│  ├─ Is this assignment unique? (no duplicates)
├─ Create & Commit:
│  ├─ db.add(Assignment)
│  ├─ db.add(AuditLog) [for audit trail]
│  ├─ db.commit()
└─ Output: Assignment object with IDs
```

### 4️⃣ List with Filtering

```
GET /api/users
├─ No body needed (all data in headers)
├─ Authentication: JWT decoded → current_user
├─ Filter by org:
│  └─ db.query(User).filter(User.org_id == current_user.org_id)
├─ Return all users in same org:
│  └─ [UserListItem{id, email, display_name, ...}, ...]
└─ Org isolation: Users only see other users in their org
```

### 5️⃣ Update with Conditional Fields

```
PATCH /api/users/{id}
├─ Input: { "display_name": "Alice Updated", "avatar_color": "#FF5733" }
├─ Fetch user: db.query(User).filter(User.id == id)
├─ Conditional updates:
│  ├─ if data.display_name: user.display_name = data.display_name
│  ├─ if data.avatar_color: user.avatar_color = data.avatar_color
│  ├─ if data.status: validate and set status
├─ db.commit()
├─ db.refresh(user) [get fresh data from DB]
└─ Output: Updated User object
```

---

## Detailed Examples

### Example 1: Complete User Registration & Folder Creation Flow

```
TIMELINE OF EVENTS
│
├─ T0: Client clicks "Sign Up"
│      POST /api/auth/signup
│      {
│        "email": "alice@test.com",
│        "password": "hunter2",
│        "display_name": "Alice"
│      }
│
├─ T1: FastAPI receives request
│      ├─ Pydantic validates schema
│      ├─ Calls auth.signup(data, db)
│
├─ T2: Signup handler executes
│      ├─ Query: SELECT * FROM users WHERE email='alice@test.com'
│      ├─ Result: None (user doesn't exist yet)
│      ├─ Hash password: bcrypt.hash("hunter2") → "$2b$12$..."
│      ├─ Create User:
│      │  ├─ id = uuid.uuid4()
│      │  ├─ org_id = uuid.uuid4() [new org for Alice]
│      │  ├─ email = "alice@test.com"
│      │  ├─ password_hash = "$2b$12$..."
│      │  ├─ display_name = "Alice"
│      │  ├─ status = "active"
│      │  ├─ avatar_color = "#7aa2f7"
│      │  ├─ created_at = now()
│      │
│      ├─ db.add(user)
│      ├─ db.commit()
│      ├─ db.refresh(user) [reload to get created_at]
│      │
│      ├─ Generate JWT token:
│      │  ├─ payload = {"sub": user.id, "exp": now + 24h}
│      │  ├─ token = jwt.encode(payload, SECRET_KEY, "HS256")
│      │
│      ├─ Return:
│      │  └─ {
│      │      "user": {...user object...},
│      │      "token": "eyJhbGc..."
│      │    }
│
├─ T3: Client receives response (201 Created)
│      ├─ localStorage.setItem("token", "eyJhbGc...")
│      ├─ Navigate to main dashboard
│
├─ T4: Client loads dashboard
│      └─ Makes multiple API requests WITH token in header
│
├─ T5: Client clicks "Create Folder"
│      └─ POST /api/folders
│         Headers: {"Authorization": "Bearer eyJhbGc..."}
│         Body: {"name": "Projects", "parent_folder_id": null}
│
├─ T6: Server receives request
│      ├─ Extract token: "eyJhbGc..."
│      ├─ jwt.decode(token, SECRET_KEY, "HS256")
│      ├─ Extract user_id from payload["sub"]
│      ├─ Query: SELECT * FROM users WHERE id=user_id
│      ├─ Check: user.status != "disabled"
│      ├─ get_current_user() returns User object ✅
│
├─ T7: Folder creation endpoint
│      ├─ Create Folder object:
│      │  ├─ id = uuid.uuid4()
│      │  ├─ org_id = current_user.org_id [org isolation]
│      │  ├─ name = "Projects"
│      │  ├─ parent_folder_id = null [root folder]
│      │  ├─ created_by = current_user.id
│      │
│      ├─ db.add(folder)
│      ├─ db.commit()
│      ├─ db.refresh(folder)
│      │
│      └─ Return: 201 Created
│         {
│           "id": "folder-uuid-123",
│           "name": "Projects",
│           "parent_folder_id": null,
│           "created_by": "user-id"
│         }
│
└─ T8: Client receives folder created
       ├─ UI updates with new folder
       └─ User can now create documents inside it
```

### Example 2: Authorization Check Flow

```
SCENARIO: Alice tries to delete Bob's assignment on a folder

1. Alice wants to remove Bob as editor on "Projects" folder
   DELETE /api/assignments/{bob-assignment-id}
   Token: Alice's JWT

2. Server validates JWT → current_user = Alice

3. Server looks up assignment:
   SELECT * FROM assignments WHERE id = {bob-assignment-id}
   Result: {
     id: "asg-123",
     user_id: Bob,
     role_id: editor,
     scope_type: "folder",
     scope_id: "folder-projects"
   }

4. Server checks: Can Alice manage members on folder-projects?
   
   authorize(db, alice_id, "can_manage_members", "folder", "folder-projects")
   
   a) Query Alice's assignment on folder-projects:
      SELECT * FROM assignments WHERE user_id=Alice AND scope_id=folder-projects
      Result: {role_id: "role-owner"}
      
   b) Get permissions for owner role:
      SELECT * FROM role_permissions WHERE role_id="role-owner"
      Result: [
        {permission: "can_edit_direct"},
        {permission: "can_manage_members"}, ✅
        ... 9 more
      ]
      
   c) Check if "can_manage_members" in permissions:
      ✅ YES → return (True, "owner", "folder-projects")

5. Authorization PASSED ✅

6. Delete Bob's assignment:
   DELETE FROM assignments WHERE id="asg-123"

7. Log audit event:
   INSERT INTO audit_log (
     action: "role_revoke",
     actor_id: Alice,
     target_type: "assignment",
     metadata: {user_id: Bob, role_id: editor, scope: "folder-projects"}
   )

8. Return: 204 No Content

9. If Alice didn't have can_manage_members:
   → Return: 403 Forbidden
   → Message: "You don't have can_manage_members permission"
```

---

## Error Handling

### Error Response Patterns

```
VALIDATION ERROR (400)
POST /api/folders
Body: {"name": ""}  ← Empty name

Response: 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.string.min_length"
    }
  ]
}

─────────────────────────────────────────

NOT FOUND ERROR (404)
GET /api/documents/{invalid-id}

Response: 404 Not Found
{
  "detail": "Document not found"
}

─────────────────────────────────────────

AUTHENTICATION ERROR (401)
POST /api/folders
Headers: {"Authorization": "Bearer invalid-token"}

Response: 401 Unauthorized
{
  "detail": "Could not validate credentials",
  "headers": {"WWW-Authenticate": "Bearer"}
}

─────────────────────────────────────────

AUTHORIZATION ERROR (403)
DELETE /api/assignments/{id}
(User doesn't have can_manage_members)

Response: 403 Forbidden
{
  "detail": "Forbidden: Lacks 'can_manage_members' on this scope"
}

─────────────────────────────────────────

CONFLICT ERROR (409)
POST /api/auth/signup
Body: {"email": "alice@test.com", ...}
(Email already registered)

Response: 409 Conflict
{
  "detail": "Email already registered"
}

─────────────────────────────────────────

CONSTRAINT ERROR (400)
DELETE /api/folders/{folder-id}
(Folder has documents inside)

Response: 400 Bad Request
{
  "detail": "Cannot delete folder with children or documents"
}
```

---

## Key Concepts Summary

### 1. Dependency Injection
```python
# FastAPI automatically injects dependencies
def endpoint(
    db: Session = Depends(get_db),          # Database session
    current_user: User = Depends(get_current_user)  # Authenticated user
):
    # db and current_user are automatically provided
    # FastAPI manages their lifecycle
```

### 2. Org Isolation
```python
# Every query filters by current_user.org_id
folders = db.query(Folder).filter(Folder.org_id == current_user.org_id).all()
# Users only see resources in their organization
```

### 3. JWT Token Lifecycle
```
Login ────→ Generate Token ────→ Client Stores ────→ Sent in Headers
                   ↓
          Expires after 24h
                   ↓
           Client needs new token
                   ↓
         (Later: Implement refresh token)
```

### 4. Authorization Guard
```python
# EVERY state-changing operation checks authorization
allowed, _, _ = authorize(db, user_id, permission, scope_type, scope_id)
if not allowed:
    raise HTTPException(403, "Forbidden")
```

### 5. Audit Logging
```python
# EVERY role assignment/revocation is logged
audit_entry = AuditLog(
    action="role_change",
    actor_id=current_user.id,
    target_type="assignment",
    metadata_json=json.dumps({...})
)
db.add(audit_entry)
```

---

## Data Flow Diagram

```
┌────────────┐
│   CLIENT   │
│  (Browser) │
└──────┬─────┘
       │
       │ 1. POST /api/auth/signup
       │    {email, password, name}
       ▼
┌──────────────┐     ┌─────────────┐
│  FastAPI    │────→│   Pydantic  │  Validate input schema
│  Router     │     │  Schemas    │
└──────┬───────┘     └─────────────┘
       │
       │ 2. Endpoint Handler
       ▼
┌──────────────────┐
│  auth.signup()   │──────────────┐
│                  │              │
│  ├─ Query DB     │              │
│  ├─ Hash pwd     │              │
│  ├─ Create User  │              │
│  └─ Gen JWT      │              │
└──────┬───────────┘              │
       │                          │
       │ 3. Database Query        │ 4. Password Hashing
       ▼                          ▼
┌──────────────────┐      ┌─────────────┐
│   SQLAlchemy     │      │   Passlib   │  bcrypt hashing
│    ORM Layer     │      │   (Bcrypt)  │
│                  │      └─────────────┘
│  ├─ SQL queries  │
│  ├─ Transactions │      ┌─────────────┐
│  └─ Commits      │      │     JWT     │  5. Token Creation
└──────┬───────────┘      │   (PyJWT)   │
       │                  └─────────────┘
       │ 6. Execute SQL
       ▼
┌─────────────────────┐
│  PostgreSQL         │
│  ├─ INSERT users    │
│  ├─ Return inserted │
│  └─ rows            │
└──────┬──────────────┘
       │
       │ 7. Return data + token
       ▼
┌──────────────┐
│  Pydantic    │  Serialize response
│  Serialize   │  (Match response_model)
└──────┬───────┘
       │
       │ 8. HTTP Response
       │    201 Created
       │    {user, token}
       ▼
┌────────────┐
│   CLIENT   │
│  Received! │
│ Store token│
└────────────┘
```

---

## Summary: How APIs Communicate

1. **Client → Server**: HTTP request (URL, method, headers, body)
2. **FastAPI Router**: Routes request to appropriate endpoint handler
3. **Validation**: Pydantic validates request schema
4. **Authentication**: JWT token validated, user identified
5. **Authorization**: Check user permissions on resource
6. **Business Logic**: Execute CRUD operations
7. **Database**: Execute SQL via SQLAlchemy ORM
8. **Response**: Pydantic serializes response, FastAPI sends HTTP response
9. **Client ← Server**: HTTP response (status code, headers, JSON body)

**All database operations are transactional** - either all succeed or all fail, ensuring data consistency.
