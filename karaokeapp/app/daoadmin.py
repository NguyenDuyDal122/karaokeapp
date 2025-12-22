from sqlalchemy import func

from app import db
from app.models import *

def thong_ke_doanh_thu_theo_nam():
    label = func.year(HoaDon.NgayLap)

    hd = db.session.query(
        label.label("nam"),
        func.sum(HoaDon.TongTien)
    ).group_by(label).all()

    hdps = db.session.query(
        label.label("nam"),
        func.sum(HoaDonDichVuPhatSinh.TongTien)
    ).join(
        HoaDon,
        HoaDon.MaHoaDon == HoaDonDichVuPhatSinh.MaHoaDon
    ).filter(
        HoaDonDichVuPhatSinh.TrangThai == "DA_THANH_TOAN"
    ).group_by(label).all()

    hd_dict = dict(hd)
    hdps_dict = dict(hdps)

    ket_qua = []
    for nam in sorted(set(hd_dict) | set(hdps_dict)):
        tong = (hd_dict.get(nam) or 0) + (hdps_dict.get(nam) or 0)
        ket_qua.append((nam, tong))

    return ket_qua

# ===== TÀI KHOẢN =====
def get_all_tai_khoan():
    return TaiKhoan.query.all()


def get_tai_khoan_by_id(ma_tk):
    return TaiKhoan.query.get(ma_tk)


def toggle_trang_thai(ma_tk):
    tk = TaiKhoan.query.get(ma_tk)
    if tk:
        tk.TrangThai = not tk.TrangThai
        db.session.commit()


def delete_tai_khoan(ma_tk):
    tk = TaiKhoan.query.get(ma_tk)
    if tk and tk.VaiTro != "ADMIN":
        db.session.delete(tk)
        db.session.commit()

# ===== PHÒNG HÁT =====
def get_all_phong():
    return PhongHat.query.all()

def them_phong(data):
    phong = PhongHat(**data)
    db.session.add(phong)
    db.session.commit()

def xoa_phong(ma_phong):
    phong = PhongHat.query.get(ma_phong)
    if phong:
        db.session.delete(phong)
        db.session.commit()

# ===== KHÁCH HÀNG =====
def get_all_khach_hang(keyword=None):
    query = KhachHang.query

    if keyword:
        keyword = f"%{keyword}%"
        query = query.filter(
            (KhachHang.HoTen.ilike(keyword)) |
            (KhachHang.SoDienThoai.ilike(keyword)) |
            (KhachHang.Email.ilike(keyword))
        )

    return query.all()


def get_khach_hang_by_id(ma_kh):
    return KhachHang.query.get(ma_kh)


def update_khach_hang(ma_kh, data):
    kh = KhachHang.query.get(ma_kh)
    if kh:
        kh.HoTen = data.get("HoTen")
        kh.SoDienThoai = data.get("SoDienThoai")
        kh.Email = data.get("Email")
        db.session.commit()


def toggle_khach_hang(ma_kh):
    kh = KhachHang.query.get(ma_kh)
    if kh and kh.tai_khoan:
        kh.tai_khoan.TrangThai = not kh.tai_khoan.TrangThai
        db.session.commit()

# ===== NHÂN VIÊN =====
def get_all_nhan_vien(keyword=None):
    query = NhanVien.query

    if keyword:
        keyword = f"%{keyword}%"
        query = query.filter(
            (NhanVien.HoTen.ilike(keyword)) |
            (NhanVien.ChucVu.ilike(keyword))
        )

    return query.all()


def get_nhan_vien_by_id(ma_nv):
    return NhanVien.query.get(ma_nv)


def update_nhan_vien(ma_nv, data):
    nv = NhanVien.query.get(ma_nv)
    if nv:
        nv.HoTen = data.get("HoTen")
        nv.ChucVu = data.get("ChucVu")
        db.session.commit()


def toggle_nhan_vien(ma_nv):
    nv = NhanVien.query.get(ma_nv)
    if nv and nv.tai_khoan:
        nv.tai_khoan.TrangThai = not nv.tai_khoan.TrangThai
        db.session.commit()

# ===== PHÒNG HÁT =====
def get_all_phong(keyword=None):
    query = PhongHat.query

    if keyword:
        keyword = f"%{keyword}%"
        query = query.filter(
            PhongHat.TenPhong.ilike(keyword)
        )

    return query.all()


def get_phong_by_id(ma_phong):
    return PhongHat.query.get(ma_phong)


def add_phong(data):
    phong = PhongHat(**data)
    db.session.add(phong)
    db.session.commit()


def update_phong(ma_phong, data):
    phong = PhongHat.query.get(ma_phong)
    if phong:
        phong.TenPhong = data.get("TenPhong")
        phong.SucChua = data.get("SucChua")
        phong.GiaGio = data.get("GiaGio")
        phong.LoaiPhong = data.get("LoaiPhong")
        phong.TrangThai = data.get("TrangThai")
        phong.MoTa = data.get("MoTa")
        db.session.commit()


def delete_phong(ma_phong):
    phong = PhongHat.query.get(ma_phong)
    if phong:
        db.session.delete(phong)
        db.session.commit()

# ===== DỊCH VỤ =====
def get_all_dich_vu():
    return DichVu.query.all()


def get_dich_vu_by_id(ma_dv):
    return DichVu.query.get(ma_dv)


def them_dich_vu(data):
    dv = DichVu(**data)
    db.session.add(dv)
    db.session.commit()


def update_dich_vu(ma_dv, data):
    dv = DichVu.query.get(ma_dv)
    if dv:
        dv.TenDichVu = data.get("TenDichVu")
        dv.DonGia = data.get("DonGia")
        dv.HinhAnh = data.get("HinhAnh")
        dv.MoTa = data.get("MoTa")
        db.session.commit()


def xoa_dich_vu(ma_dv):
    dv = DichVu.query.get(ma_dv)
    if dv:
        db.session.delete(dv)
        db.session.commit()

# ===== ĐẶT PHÒNG =====

def get_all_dat_phong(keyword=None, trang_thai=None):
    query = DatPhong.query.join(KhachHang).join(PhongHat)

    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            KhachHang.HoTen.ilike(kw) |
            PhongHat.TenPhong.ilike(kw)
        )

    if trang_thai:
        query = query.filter(DatPhong.TrangThai == trang_thai)

    return query.order_by(DatPhong.ThoiGianBatDau.desc()).all()


def get_dat_phong_by_id(ma_dp):
    return DatPhong.query.get(ma_dp)


def update_trang_thai_dat_phong(ma_dp, trang_thai_moi):
    dp = DatPhong.query.get(ma_dp)
    if not dp:
        return False

    dp.TrangThai = trang_thai_moi
    db.session.commit()
    return True

def get_all_hoa_don(keyword=None):
    query = HoaDon.query \
        .join(DatPhong) \
        .join(KhachHang)

    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            (KhachHang.HoTen.ilike(kw)) |
            (KhachHang.SoDienThoai.ilike(kw))
        )

    return query.order_by(HoaDon.NgayLap.desc()).all()


def get_hoa_don_by_id(ma_hd):
    return HoaDon.query.get(ma_hd)


def tao_hoa_don_tu_dat_phong(dat_phong, phuong_thuc, ma_nv=None):
    # Tiền phòng = số giờ * giá giờ
    so_gio = (dat_phong.ThoiGianKetThuc - dat_phong.ThoiGianBatDau).total_seconds() / 3600
    tien_phong = Decimal(so_gio) * Decimal(dat_phong.phong.GiaGio)

    # Tiền dịch vụ (nếu có)
    tien_dv = Decimal('0')
    for ct in dat_phong.chi_tiet_dv:
        tien_dv += Decimal(ct.SoLuong) * Decimal(ct.dich_vu.DonGia)

    hd = HoaDon(
        MaDatPhong=dat_phong.MaDatPhong,
        TienPhong=tien_phong,
        TienDichVu=tien_dv,
        PhuongThucThanhToan=phuong_thuc,
        MaNhanVien=ma_nv,
        Nguon='QUAY'
    )

    hd.tinh_tong_tien()
    db.session.add(hd)
    db.session.commit()
    return hd

def thong_ke_doanh_thu_theo_ngay():
    return db.session.query(
        func.date(HoaDon.NgayLap).label("ngay"),
        func.sum(HoaDon.TongTien).label("tong_tien")
    ).group_by(
        func.date(HoaDon.NgayLap)
    ).order_by(
        func.date(HoaDon.NgayLap)
    ).all()


def thong_ke_doanh_thu_theo_thang():
    return db.session.query(
        func.date_format(HoaDon.NgayLap, '%Y-%m').label("thang"),
        func.sum(HoaDon.TongTien).label("tong_tien")
    ).group_by(
        func.date_format(HoaDon.NgayLap, '%Y-%m')
    ).order_by(
        func.date_format(HoaDon.NgayLap, '%Y-%m')
    ).all()


def tong_doanh_thu():
    tong_hd = db.session.query(
        func.sum(HoaDon.TongTien)
    ).scalar() or 0

    tong_hdps = db.session.query(
        func.sum(HoaDonDichVuPhatSinh.TongTien)
    ).filter(
        HoaDonDichVuPhatSinh.TrangThai == "DA_THANH_TOAN"
    ).scalar() or 0

    return tong_hd + tong_hdps


def thong_ke_doanh_thu(loai):
    if loai == "ngay":
        label = func.date(HoaDon.NgayLap)
    elif loai == "thang":
        label = func.date_format(HoaDon.NgayLap, '%Y-%m')
    else:  # nam
        label = func.year(HoaDon.NgayLap)

    # --- Doanh thu hóa đơn chính ---
    hd_query = db.session.query(
        label.label("thoi_gian"),
        func.sum(HoaDon.TongTien).label("tien_phong")
    ).group_by(label)

    # --- Doanh thu dịch vụ phát sinh (chỉ tính đã thanh toán) ---
    hdps_query = db.session.query(
        label.label("thoi_gian"),
        func.sum(HoaDonDichVuPhatSinh.TongTien).label("tien_dv")
    ).join(
        HoaDon,
        HoaDon.MaHoaDon == HoaDonDichVuPhatSinh.MaHoaDon
    ).filter(
        HoaDonDichVuPhatSinh.TrangThai == "DA_THANH_TOAN"
    ).group_by(label)

    # --- Gộp kết quả ---
    hd_data = {tg: tien for tg, tien in hd_query.all()}
    hdps_data = {tg: tien for tg, tien in hdps_query.all()}

    ket_qua = []
    for tg in sorted(set(hd_data) | set(hdps_data)):
        tong = (hd_data.get(tg) or 0) + (hdps_data.get(tg) or 0)
        ket_qua.append((tg, tong))

    return ket_qua



def tong_doanh_thu():
    return db.session.query(func.sum(HoaDon.TongTien)).scalar() or 0
