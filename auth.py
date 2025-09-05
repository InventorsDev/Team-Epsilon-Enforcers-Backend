import os
from fastapi import Depends, HTTPException, status
import uuid
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from supabase import create_client, AuthError, Client
import models, schemas
from database import get_db

load_dotenv()

SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_PROJECT_URL, SUPABASE_KEY)


# Reusable security scheme
oauth2_scheme = HTTPBearer()


def get_current_user(
        token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> schemas.User:
    """
    Dependency to verify Supabase JWT and get/create the user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Use the Supabase client to verify the token and get user data
        response = supabase.auth.get_user(token.credentials)

        supabase_user = response.user
        if not supabase_user:
            raise credentials_exception

        # The user ID from Supabase is a string, convert it to a UUID object.
        user_id = uuid.UUID(supabase_user.id)

    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e), headers={"WWW-Authenticate": "Bearer"})
    except (ValueError):  # Catch potential error from uuid.UUID() conversion
        raise credentials_exception
    

    # Check if user exists in our database
    user = db.query(models.User).filter(models.User.id == user_id).first()

    # If user does not exist, create a new user record (first-time login)
    if user is None:
        email = supabase_user.email
        # Supabase stores name in user_metadata by default
        name = supabase_user.user_metadata.get("name")

        if not email:
            raise credentials_exception

        new_user = models.User(id=user_id, email=email, name=name)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    return user
