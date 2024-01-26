# Import necessary modules
import re
from datetime import datetime
import bcrypt
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Boolean, DateTime, TIMESTAMP
from sqlalchemy.sql import func
from auth.auth_handler import signJWT
from database import Base, Sessionlocal


# Define a Pydantic model for login input
class LoginInput(BaseModel):
    email: str
    password: str

    class Config:
        from_attributes = True  # Config setting for Pydantic to enable conversion from attribute names


# Define a SQLAlchemy model for the Users table
class Users(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True)
    password = Column(String(255))

    is_deleted = Column(Boolean, server_default='0', nullable=False)
    created_on = Column(DateTime, default=func.now())
    updated_on = Column(TIMESTAMP, server_default=func.now(), onupdate=func.current_timestamp())
    deleted_on = Column(DateTime)

    # Define a method to check the validity of a password format
    def is_valid_password(password: str):
        # Password should have at least one uppercase character, one special character, and one numerical character
        return bool(re.match(r'^(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<>])(?=.*\d).+$', password))

    # Define a static method for user signup
    @staticmethod
    def signup(data: dict, db: Sessionlocal):
        try:
            # Create a Users instance with the provided data
            usr = Users(**data)
            usr.created_on = datetime.now()

            # Check if the password format is valid
            if not Users.is_valid_password(usr.password):
                return HTTPException(status_code=400, detail="Invalid password format")

            # Hash the password before storing it in the database
            usr.password = bcrypt.hashpw(usr.password.encode('utf-8'), bcrypt.gensalt())

            # Check if the email already exists in the database
            if db.query(Users).filter(Users.email == usr.email).first():
                return HTTPException(status_code=400, detail="Email already exists")

            # Add the user to the database, commit changes, and refresh the user instance
            db.add(usr)
            db.commit()
            db.refresh(usr)

            # Generate a JWT token for the user
            token, exp = signJWT(usr.user_id)

            # Create a response with the token and a success message
            response = {
                "token": token,
                "message": "User created successfully"
            }
            return response

        except Exception as e:
            # Rollback changes in case of an exception and return an HTTPException with the error details
            db.rollback()
            return HTTPException(status_code=500, detail=str(e))

    # Define a static method for user login
    @staticmethod
    def login(credential: LoginInput):
        try:
            # Create a new database session
            session = Sessionlocal()

            # Query the database for a user with the provided email and not marked as deleted
            user = session.query(Users).filter(Users.email == credential.email, Users.is_deleted == 0).first()

            # Check if the user exists
            if not user:
                return HTTPException(status_code=404, detail="Invalid email or password")

            # Check if the provided password matches the stored hashed password
            if bcrypt.checkpw(credential.password.encode('utf-8'), user.password.encode('utf-8')):
                # Generate a JWT token for the user
                token, exp = signJWT(user.user_id)

                # Create a response with the token, expiration time, and a success message
                response = {
                    'token': token,
                    'exp': exp,
                    'message': "Login successful"
                }

                return response
            else:
                # Return an HTTPException for an invalid email or password
                return HTTPException(status_code=401, detail='Invalid email or password')

        except Exception as e:
            # Return an HTTPException for any other errors during the login process
            return HTTPException(status_code=500, detail=f"Error: {str(e)}")
