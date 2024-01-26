# Import necessary modules
from fastapi import FastAPI, Depends, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from auth.auth_bearer import JWTBearer, get_user_id_from_token
from database import Sessionlocal, engine, Base
from model.users import Users, LoginInput
from model.post import Post
from my_config import get_db
from cachetools import TTLCache
from functools import wraps

# Create a FastAPI instance
app = FastAPI()

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Create instances of Users and Post classes
user_ops = Users()
pot = Post()

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

# In-memory cache with a TTL (time-to-live) of 5 minutes
cache = TTLCache(maxsize=100, ttl=300)


# Define a decorator for caching responses
def cache_response(cache_key_prefix: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id")
            cache_key = f"{cache_key_prefix}:{user_id}"

            # Check if the result is already in the cache
            if cache_key in cache:
                return cache[cache_key]

            # If not, call the function to get the result
            result = await func(*args, **kwargs)

            # Store the result in the cache
            cache[cache_key] = result
            return result

        return wrapper

    return decorator


# Define a route for user login
@app.post('/api/login')
def login(credential: LoginInput):
    return user_ops.login(credential)


# Define a route for user signup
@app.post("/api/insert/signup")
async def signup(data: LoginInput, db: Session = Depends(get_db)):
    return user_ops.signup(data.model_dump(), db)


# Define a route for inserting a new post
@app.post("/api/insert/addPost", dependencies=[Depends(JWTBearer())])
async def post_insert(user_id: int = Depends(get_user_id_from_token), db: Sessionlocal = Depends(get_db),
                      post_image: UploadFile = File(...)):
    return pot.post_insert(user_id, db, post_image)


# Define a route for deleting a post
@app.delete("/api/delete/deletePost/{post_id}", dependencies=[Depends(JWTBearer())])
async def post_delete(post_id: int, db: Sessionlocal = Depends(get_db)):
    return pot.post_delete(post_id, db)


# Define a route for reading posts with caching
@app.get("/api/read/getPosts", dependencies=[Depends(JWTBearer())])
@cache_response("getPosts")
async def post_read(user_id: int = Depends(get_user_id_from_token), page_num: int = 1, page_size: int = 20,
                    db: Sessionlocal = Depends(get_db)):
    return pot.post_read(user_id, page_num, page_size, db)


# Run the FastAPI app if the script is executed directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=5000)
