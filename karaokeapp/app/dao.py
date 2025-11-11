from app.models import TaiKhoan
from app.models import PhongHat
from werkzeug.security import check_password_hash

def get_tai_khoan_by_ten_dang_nhap(username):
    return TaiKhoan.query.filter_by(TenDangNhap=username).first()

def check_login(username, password):
    user = TaiKhoan.query.filter_by(TenDangNhap=username, TrangThai=True).first()
    if user and check_password_hash(user.MatKhau, password):
        return user
    return None

def get_all_phong_hat():
    return PhongHat.query.all()