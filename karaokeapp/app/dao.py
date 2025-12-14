from app import db
from app.models import TaiKhoan, PhongHat, DatPhong, KhachHang
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from sqlalchemy import or_

# =========================
# AUTH / LOGIN DAO
# =========================

def get_tai_khoan_by_ten_dang_nhap(username):
    return TaiKhoan.query.filter_by(TenDangNhap=username).first()

def check_login(username, password):
    user = TaiKhoan.query.filter_by(TenDangNhap=username).first()

    if not user:
        return None, "❌ Sai tài khoản hoặc mật khẩu!"

    if not check_password_hash(user.MatKhau, password):
        return None, "❌ Sai tài khoản hoặc mật khẩu!"

    if not user.TrangThai:
        return None, "🔒 Tài khoản của bạn đã bị khóa. Vui lòng liên hệ admin!"

    return user, None


# =========================
# PHÒNG HÁT DAO
# =========================

def get_phong_vip():
    return PhongHat.query.filter_by(LoaiPhong="VIP").all()

def get_phong_thuong():
    return PhongHat.query.filter_by(LoaiPhong="THUONG").all()


# =========================
# ĐẶT PHÒNG DAO
# =========================

def cap_nhat_trang_thai_dat_phong():
    now = datetime.now()
    tat_ca_dat = DatPhong.query.filter(DatPhong.TrangThai != "HUY").all()

    for dat in tat_ca_dat:
        if dat.ThoiGianBatDau <= now <= dat.ThoiGianKetThuc:
            dat.TrangThai = "DANG_HAT"
        elif now > dat.ThoiGianKetThuc:
            dat.TrangThai = "DA_THANH_TOAN"

    db.session.commit()

def phong_dang_hat(ma_phong):
    return DatPhong.query.filter_by(
        MaPhong=ma_phong,
        TrangThai="DANG_HAT"
    ).first()


# =========================
# REGISTER DAO
# =========================

def dang_ky_khach_hang(username, password, hoten, sdt, email):
    # kiểm tra trùng username
    if TaiKhoan.query.filter_by(TenDangNhap=username).first():
        return False, "❌ Tên đăng nhập đã tồn tại!"

    kh_exist = KhachHang.query.filter(
        or_(KhachHang.SoDienThoai == sdt, KhachHang.Email == email)
    ).first()

    hashed_password = generate_password_hash(password)

    # đã có KH nhưng chưa có tài khoản
    if kh_exist and kh_exist.MaTaiKhoan is None:
        tai_khoan = TaiKhoan(
            TenDangNhap=username,
            MatKhau=hashed_password,
            VaiTro="KHACHHANG",
            TrangThai=True
        )
        db.session.add(tai_khoan)
        db.session.commit()

        kh_exist.MaTaiKhoan = tai_khoan.MaTaiKhoan
        kh_exist.HoTen = hoten
        kh_exist.SoDienThoai = sdt
        kh_exist.Email = email
        db.session.commit()

        return True, "✅ Đăng ký thành công!"

    # đã có tài khoản rồi
    if kh_exist:
        return False, "❌ SDT hoặc Email đã có tài khoản!"

    # hoàn toàn mới
    tai_khoan = TaiKhoan(
        TenDangNhap=username,
        MatKhau=hashed_password,
        VaiTro="KHACHHANG",
        TrangThai=True
    )
    db.session.add(tai_khoan)
    db.session.commit()

    kh = KhachHang(
        MaTaiKhoan=tai_khoan.MaTaiKhoan,
        HoTen=hoten,
        SoDienThoai=sdt,
        Email=email
    )
    db.session.add(kh)
    db.session.commit()

    return True, "✅ Đăng ký thành công!"

# =========================
# CHI TIẾT PHÒNG DAO
# =========================

def get_phong_by_id(ma_phong):
    return PhongHat.query.get(ma_phong)


def get_trang_thai_hien_thi_phong(room):
    """
    Trả về: BAO_TRI | DANG_HAT | TRONG
    """
    if room.TrangThai == "BAO_TRI":
        return "BAO_TRI"

    dp = DatPhong.query.filter_by(
        MaPhong=room.MaPhong,
        TrangThai="DANG_HAT"
    ).first()

    return "DANG_HAT" if dp else "TRONG"


def get_lich_dat_phong_hop_le(ma_phong):
    """
    Lấy lịch đặt:
    - Không lấy HUY
    - Không lấy DA_THANH_TOAN
    """
    return DatPhong.query.filter(
        DatPhong.MaPhong == ma_phong,
        DatPhong.TrangThai.notin_(["HUY", "DA_THANH_TOAN"])
    ).order_by(DatPhong.ThoiGianBatDau.asc()).all()

# =========================
# ĐẶT PHÒNG DAO
# =========================

from datetime import datetime
from decimal import Decimal
from sqlalchemy import and_
from app.models import (
    PhongHat, DatPhong, DichVu, ChiTietDatDichVu,
    HoaDon, KhachHang, NhanVien
)
from app import db


def get_phong_or_404(ma_phong):
    return PhongHat.query.get_or_404(ma_phong)


def kiem_tra_xung_dot_gio(ma_phong, tg_bd, tg_kt):
    return DatPhong.query.filter(
        DatPhong.MaPhong == ma_phong,
        DatPhong.ThoiGianBatDau < tg_kt,
        DatPhong.ThoiGianKetThuc > tg_bd
    ).first()


def tao_dat_phong(ma_phong, ma_kh, tg_bd, tg_kt, so_nguoi):
    dp = DatPhong(
        MaPhong=ma_phong,
        MaKhachHang=ma_kh,
        ThoiGianBatDau=tg_bd,
        ThoiGianKetThuc=tg_kt,
        SoNguoi=so_nguoi
    )
    db.session.add(dp)
    db.session.commit()
    return dp


def luu_chi_tiet_dich_vu(dp, selected_services, selected_services_data):
    for dv in selected_services:
        item = next((x for x in selected_services_data if x["id"] == dv.MaDichVu), None)
        so_luong = item["so_luong"] if item else 1

        ct = ChiTietDatDichVu(
            MaDatPhong=dp.MaDatPhong,
            MaDichVu=dv.MaDichVu,
            SoLuong=so_luong,
            ThanhTien=Decimal(dv.DonGia) * so_luong
        )
        db.session.add(ct)

    db.session.commit()


def xac_dinh_nhan_vien_lap_hoa_don(session):
    if session.get("role") == "nhanvien":
        return session.get("user_id")  # ✅ ĐÚNG

    admin = NhanVien.query.filter_by(ChucVu="ADMIN").first()
    return admin.MaNhanVien if admin else None


def tao_hoa_don(dp, room, session, phuong_thuc_tt):
    tg = dp.ThoiGianKetThuc - dp.ThoiGianBatDau
    so_gio = Decimal(tg.seconds) / Decimal(3600)
    tien_dv = sum(ct.ThanhTien for ct in dp.chi_tiet_dv)

    ma_nv = xac_dinh_nhan_vien_lap_hoa_don(session)
    nguon = "QUAY" if session.get("role") == "nhanvien" else "ONLINE"

    # 1️⃣ Tạo hóa đơn
    hd = HoaDon(
        MaDatPhong=dp.MaDatPhong,
        TienPhong=Decimal(room.GiaGio) * so_gio,
        TienDichVu=tien_dv,
        PhuongThucThanhToan=phuong_thuc_tt,
        Nguon=nguon,
        MaNhanVien=ma_nv,
        GiamGia=Decimal("0.00")
    )

    hd.tinh_tong_tien()
    db.session.add(hd)

    # 3️⃣ Cộng lượt đặt tháng cho khách hàng
    kh = dp.khach_hang
    if kh:
        kh.SoLuotDatThang = (kh.SoLuotDatThang or 0) + 1

    # 4️⃣ Commit 1 lần
    db.session.commit()

    return hd

def kiem_tra_thoi_gian_hop_le(tg_bd, tg_kt):
    now = datetime.now()

    if tg_bd < now:
        return False, "❌ Không thể đặt phòng trong quá khứ!"

    if tg_kt <= tg_bd:
        return False, "❌ Giờ kết thúc phải lớn hơn giờ bắt đầu!"

    return True, None

# =========================
# DỊCH VỤ DAO
# =========================

from app.models import DichVu

def get_all_dich_vu():
    return DichVu.query.all()

# =========================
# HÓA ĐƠN DAO
# =========================

from app.models import HoaDon, ChiTietDatDichVu

def get_hoa_don_by_id(ma_hoa_don):
    return HoaDon.query.get(ma_hoa_don)

def get_chi_tiet_dich_vu_by_dat_phong(ma_dat_phong):
    return ChiTietDatDichVu.query.filter_by(
        MaDatPhong=ma_dat_phong
    ).all()

# =========================
# KHÁCH HÀNG DAO
# =========================

from app.models import KhachHang

def get_khach_hang_by_id(ma_khach_hang):
    return KhachHang.query.get(ma_khach_hang)

# =========================
# NHÂN VIÊN DAO
# =========================

from app.models import NhanVien

def get_nhan_vien_by_id(ma_nhan_vien):
    return NhanVien.query.get(ma_nhan_vien)

from app import db
from app.models import KhachHang, NhanVien
from werkzeug.security import check_password_hash, generate_password_hash

def get_tai_khoan_theo_vai_tro(role, user_id):
    """
    Trả về TaiKhoan tương ứng với vai trò
    """
    if role == "khachhang":
        kh = KhachHang.query.get(user_id)
        return kh.tai_khoan if kh else None

    if role == "nhanvien":
        nv = NhanVien.query.get(user_id)
        return nv.tai_khoan if nv else None

    return None


def doi_mat_khau(tai_khoan, mat_khau_cu, mat_khau_moi, nhap_lai):
    """
    Xử lý đổi mật khẩu
    """
    if not check_password_hash(tai_khoan.MatKhau, mat_khau_cu):
        return False, "❌ Mật khẩu cũ không đúng!"

    if mat_khau_moi != nhap_lai:
        return False, "❌ Mật khẩu mới và xác nhận không trùng khớp!"

    tai_khoan.MatKhau = generate_password_hash(mat_khau_moi)
    db.session.commit()

    return True, "✅ Đổi mật khẩu thành công!"

from app.models import DatPhong

def get_lich_su_dat_phong(ma_khach_hang):
    return DatPhong.query.filter_by(
        MaKhachHang=ma_khach_hang
    ).order_by(
        DatPhong.ThoiGianBatDau.desc()
    ).all()

from app import db
from app.models import DatPhong

def get_dat_phong_by_id(ma_dat_phong):
    return DatPhong.query.get(ma_dat_phong)


def huy_dat_phong(ma_dat_phong, ma_khach_hang):
    dp = DatPhong.query.get(ma_dat_phong)

    if not dp or dp.MaKhachHang != ma_khach_hang:
        return False, "Không tìm thấy đặt phòng này!"

    if dp.TrangThai != "CHO_XAC_NHAN":
        return False, "Chỉ có thể hủy các đặt phòng đang chờ xác nhận."

    # 1️⃣ Hủy đặt phòng
    dp.TrangThai = "HUY"

    # 2️⃣ Trừ lượt đặt tháng
    kh = dp.khach_hang
    if kh and kh.SoLuotDatThang and kh.SoLuotDatThang > 0:
        kh.SoLuotDatThang -= 1

    db.session.commit()

    return True, "✅ Hủy đặt phòng thành công."

from app import db
from app.models import KhachHang

def tim_khach_hang_theo_sdt_email(so_dt, email):
    return KhachHang.query.filter(
        (KhachHang.SoDienThoai == so_dt) |
        (KhachHang.Email == email)
    ).first()


def tao_khach_hang(ho_ten, so_dt, email):
    kh = KhachHang(
        HoTen=ho_ten,
        SoDienThoai=so_dt,
        Email=email
    )
    db.session.add(kh)
    db.session.commit()
    return kh

