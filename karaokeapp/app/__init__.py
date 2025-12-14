from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.config(
    cloud_name="dj0oslp3a",
    api_key="393547919889753",
    api_secret="6_mEs6LTpPUCRXuglyGoMy4meg4",
    secure=True
)

app = Flask(__name__) # ❌ BỎ template_folder ở đây
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:123456789@localhost/karaokedb?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "karaoke_secret_key"

db = SQLAlchemy(app)

# ✅ IMPORT ROUTES
from app import index
from app import admin   # 👈 THÊM DÒNG NÀY
