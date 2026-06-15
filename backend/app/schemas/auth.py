from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    display_name: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_color: Optional[str] = None
    status: Optional[str] = None

class UserResponse(UserBase):
    id: str
    avatar_color: Optional[str]
    status: str
    created_at: str

    class Config:
        from_attributes = True

class UserListItem(BaseModel):
    id: str
    email: str
    display_name: str
    avatar_color: Optional[str]
    status: str
    created_at: str

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: list[UserListItem]

class Token(BaseModel):
    user: UserResponse
    token: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str