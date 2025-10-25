from app.models import TaiKhoan

def get_tai_khoan_by_ten_dang_nhap(username):
    return TaiKhoan.query.filter_by(TenDangNhap=username).first()

def check_login(username, password):
    user = get_tai_khoan_by_ten_dang_nhap(username)
    if user and user.MatKhau == password and user.TrangThai:  # TrangThai = True => tài khoản đang hoạt động
        return user
    return None
