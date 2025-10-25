from app import app, db

if __name__ == "__main__":
    try:
        with app.app_context():
            db.create_all()
            print("✅ Kết nối MySQL thành công và đã tạo bảng trong cơ sở dữ liệu karaokedb!")
        app.run(debug=True)
    except Exception as e:
        print("❌ Lỗi khi kết nối hoặc khởi tạo database:", e)
