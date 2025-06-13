from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import sys
import os

# Add project root to path for imports if needed
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import directly since we've ensured the path is correct
from models.user_models import UserRegister, UserLogin
from utils.auth_utils import hash_password, verify_password, create_access_token
from database.connection import get_db_session
from database.models import User

router = APIRouter(tags=["authentication"])

@router.post("/register")
def register_user(user: UserRegister, db: Session = Depends(get_db_session)):
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create new user
        hashed_password = hash_password(user.password)
        new_user = User(email=user.email, password=hashed_password)

        db.add(new_user)
        db.commit()

        return {"message": "User registered successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db_session)):
    # Find user
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}
