import os
from datetime import datetime
from fastapi import HTTPException, Depends, UploadFile, File
from sqlalchemy import Column, String, Integer, Boolean, DATETIME, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from werkzeug.utils import secure_filename
from database import Base, Sessionlocal
from my_config import api_response, get_db


#########################################################################################

class Post(Base):
    __tablename__ = "post_tb"
    post_id = Column(Integer, primary_key=True, autoincrement=True)
    post_image = Column(String(255))
    user_id = Column(Integer, ForeignKey('users.user_id'))
    is_deleted = Column(Boolean, server_default='0', nullable=False)
    created_on = Column(DATETIME, default=func.now())
    updated_on = Column(TIMESTAMP, server_default=func.now(), onupdate=func.current_timestamp())
    deleted_on = Column(DATETIME)

    creator = relationship("Users", backref="post_tb_user",
                           uselist=False, primaryjoin="Post.user_id==Users.user_id")

    @staticmethod
    def post_insert(user_id, db: Sessionlocal, post_image: UploadFile = File(...)):
        try:
            max_file_size = 1 * 1024 * 1024
            if post_image.size > max_file_size:
                raise HTTPException(status_code=413, detail="File size exceeds 1 MB limit")

            if not os.path.exists('static/post'):
                os.makedirs('static/post')
                raise HTTPException(status_code=413, detail="File size exceeds 1 MB limit")

            image_name = secure_filename(post_image.filename)
            image_path = os.path.join('static/post', image_name)

            with open(image_path, 'wb') as f:
                f.write(post_image.file.read())

            created_on = datetime.now()
            new_post = Post(
                post_image=image_path,
                created_on=created_on,
                user_id=user_id
            )

            db.add(new_post)
            db.commit()

            post_id = new_post.post_id
            response_message = f"Your PostID {post_id} inserted successfully"
            response = api_response(200, message=response_message)
            return response
        except Exception as e:
            return HTTPException(status_code=500, detail=f"Error: {str(e)}")

    ###########################################################################################

    @staticmethod
    def post_delete(post_id: int, db: Sessionlocal):
        try:
            post_query = db.query(Post).filter(Post.post_id == post_id, Post.is_deleted == 0).first()
            if post_query is None:
                return HTTPException(status_code=404, detail=f"Record with id {post_id} not found")

            # Delete the file from local storage
            print('post_query.post_image :', post_query.post_image)
            if os.path.exists(post_query.post_image):
                os.remove(post_query.post_image)

            post_query.is_deleted = True
            post_query.deleted_on = datetime.now()

            db.commit()
            response = api_response(200, message="Data deleted successfully")
            return response
        except Exception as e:
            db.rollback()
            return HTTPException(status_code=500, detail=str(e))

    ############################################################################################

    @staticmethod
    def post_read(user_id, page_num: int = 1, page_size: int = 20, db: Sessionlocal = Depends(get_db)):
        try:
            start = (page_num - 1) * page_size

            base_query = db.query(Post).filter(Post.is_deleted == 0, Post.user_id == user_id)
            # if user_id is not None:
            #     base_query = base_query.filter(Post.user_id == user_id)
            total_post = base_query.count()

            post = base_query.offset(start).limit(page_size).all()
            if post:
                response = api_response(data=post, total=total_post, count=len(post), status_code=200)

                return response
            return HTTPException(status_code=404, detail="No data found")
        except Exception as e:
            return HTTPException(status_code=500, detail=f"Error: {str(e)}")
