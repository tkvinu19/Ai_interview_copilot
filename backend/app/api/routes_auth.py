from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.user_schema import UserCreate, UserResponse, UserLogin
from app.models.user import User
from app.db.deps import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


# ✅ SIGNUP
@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_pwd = hash_password(user.password)

    # Create new user
    new_user = User(
        email=user.email,
        password=hashed_pwd
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ✅ LOGIN (returns JWT token)
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user.email).first()

    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Verify password
    if not verify_password(user.password, existing_user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Create JWT token
    token = create_access_token({"sub": str(existing_user.id)})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ✅ PROTECTED ROUTE (JWT required)
@router.get("/me")
def get_me(user_id: str = Depends(get_current_user)):
    return {
        "message": "Authenticated user",
        "user_id": user_id
    }