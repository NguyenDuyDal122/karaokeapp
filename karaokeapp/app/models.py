from sqlalchemy import Enum, DECIMAL, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app import db
from decimal import Decimal

class TaiKhoan(db.Model):
    __tablename__ = "tai_khoan"

    MaTaiKhoan = db.Column(db.Integer, primary_key=True)
    TenDangNhap = db.Column(db.String(50), unique=True, nullable=False)
    MatKhau = db.Column(db.String(300), nullable=False)
    VaiTro = db.Column(Enum('ADMIN', 'NHANVIEN', 'KHACHHANG', name='vaitro_enum'), nullable=False)
    TrangThai = db.Column(db.Boolean, default=True)

    khach_hang = relationship("KhachHang", back_populates="tai_khoan", uselist=False)
    nhan_vien = relationship("NhanVien", back_populates="tai_khoan", uselist=False)


class KhachHang(db.Model):
    __tablename__ = "khach_hang"

    MaKhachHang = db.Column(db.Integer, primary_key=True)
    MaTaiKhoan = db.Column(db.Integer, ForeignKey("tai_khoan.MaTaiKhoan"), nullable=True)
    HoTen = db.Column(db.String(100), nullable=False)
    SoDienThoai = db.Column(db.String(15), nullable=False)
    Email = db.Column(db.String(100))
    SoLuotDatThang = db.Column(db.Integer, default=0)

    tai_khoan = relationship("TaiKhoan", back_populates="khach_hang")
    dat_phong = relationship("DatPhong", back_populates="khach_hang")


class NhanVien(db.Model):
    __tablename__ = "nhan_vien"

    MaNhanVien = db.Column(db.Integer, primary_key=True)
    MaTaiKhoan = db.Column(db.Integer, ForeignKey("tai_khoan.MaTaiKhoan"), nullable=False)
    HoTen = db.Column(db.String(100), nullable=False)
    ChucVu = db.Column(db.String(50))
    NgayVaoLam = db.Column(db.Date, default=datetime.utcnow)

    tai_khoan = relationship("TaiKhoan", back_populates="nhan_vien")
    hoa_don = relationship("HoaDon", back_populates="nhan_vien")


class PhongHat(db.Model):
    __tablename__ = "phong_hat"

    MaPhong = db.Column(db.Integer, primary_key=True)
    TenPhong = db.Column(db.String(50), nullable=False)
    SucChua = db.Column(db.Integer, nullable=False)
    GiaGio = db.Column(DECIMAL(10, 2), nullable=False)
    LoaiPhong = db.Column(Enum('VIP', 'THUONG', name='loaiphong_enum'), default='THUONG', nullable=False)
    TrangThai = db.Column(Enum('TRONG', 'DANG_HAT', 'BAO_TRI', name='trangthaiphong_enum'), default='TRONG')
    HinhAnh = db.Column(db.String(255))
    MoTa = db.Column(db.String(255))

    dat_phong = relationship("DatPhong", back_populates="phong")


class DatPhong(db.Model):
    __tablename__ = "dat_phong"

    MaDatPhong = db.Column(db.Integer, primary_key=True)
    MaKhachHang = db.Column(db.Integer, ForeignKey("khach_hang.MaKhachHang"), nullable=False)
    MaPhong = db.Column(db.Integer, ForeignKey("phong_hat.MaPhong"), nullable=False)
    ThoiGianBatDau = db.Column(db.DateTime, nullable=False)
    ThoiGianKetThuc = db.Column(db.DateTime, nullable=False)
    SoNguoi = db.Column(db.Integer, nullable=False)
    TrangThai = db.Column(
        Enum('CHO_XAC_NHAN', 'DA_XAC_NHAN', 'DANG_HAT', 'DA_THANH_TOAN', 'HUY', name='trangthaidat_enum'),
        default='CHO_XAC_NHAN'
    )
    GiamGia = db.Column(DECIMAL(5, 2), default=0.00)

    __table_args__ = (
        UniqueConstraint("MaPhong", "ThoiGianBatDau", "ThoiGianKetThuc", name="unique_phong_thoigian"),
    )

    khach_hang = relationship("KhachHang", back_populates="dat_phong")
    phong = relationship("PhongHat", back_populates="dat_phong")
    chi_tiet_dv = relationship("ChiTietDatDichVu", back_populates="dat_phong")
    hoa_don = relationship("HoaDon", back_populates="dat_phong", uselist=False)


class DichVu(db.Model):
    __tablename__ = "dich_vu"

    MaDichVu = db.Column(db.Integer, primary_key=True)
    TenDichVu = db.Column(db.String(100), nullable=False)
    DonGia = db.Column(DECIMAL(10, 2), nullable=False)
    HinhAnh = db.Column(db.String(255))
    MoTa = db.Column(db.String(255))

    chi_tiet_dv = relationship("ChiTietDatDichVu", back_populates="dich_vu")


class ChiTietDatDichVu(db.Model):
    __tablename__ = "ct_dat_dich_vu"

    MaCTDV = db.Column(db.Integer, primary_key=True)
    MaDatPhong = db.Column(db.Integer, ForeignKey("dat_phong.MaDatPhong"), nullable=False)
    MaDichVu = db.Column(db.Integer, ForeignKey("dich_vu.MaDichVu"), nullable=False)
    SoLuong = db.Column(db.Integer, nullable=False, default=1)
    ThanhTien = db.Column(DECIMAL(10, 2), nullable=False)

    dat_phong = relationship("DatPhong", back_populates="chi_tiet_dv")
    dich_vu = relationship("DichVu", back_populates="chi_tiet_dv")

    def tinh_tien(self):
        if self.dich_vu:
            self.ThanhTien = self.SoLuong * self.dich_vu.DonGia


class HoaDon(db.Model):
    __tablename__ = "hoa_don"

    MaHoaDon = db.Column(db.Integer, primary_key=True)
    MaDatPhong = db.Column(db.Integer, ForeignKey("dat_phong.MaDatPhong"), nullable=False)
    NgayLap = db.Column(db.DateTime, default=datetime.utcnow)
    TienPhong = db.Column(DECIMAL(10, 2), default=0.00)
    TienDichVu = db.Column(DECIMAL(10, 2), default=0.00)
    VAT = db.Column(DECIMAL(5, 2), default=10.00)
    GiamGia = db.Column(DECIMAL(10, 2), default=0.00)
    TongTien = db.Column(DECIMAL(10, 2), default=0.00)
    PhuongThucThanhToan = db.Column(
        Enum('TIEN_MAT', 'CHUYEN_KHOAN', name='thanhtoan_enum'),
        nullable=False
    )
    Nguon = db.Column(Enum('ONLINE', 'QUAY', name='nguon_hoa_don_enum'), default='ONLINE')
    MaNhanVien = db.Column(db.Integer, ForeignKey("nhan_vien.MaNhanVien"), nullable=True)

    dat_phong = relationship("DatPhong", back_populates="hoa_don")
    nhan_vien = relationship("NhanVien", back_populates="hoa_don")

    def tinh_tong_tien(self):
        tong = (self.TienPhong or Decimal('0')) + (self.TienDichVu or Decimal('0'))
        giam_gia = self.GiamGia or Decimal('0')
        vat = self.VAT or Decimal('10.0')
        tong_sau_giam = tong - giam_gia
        tong_co_vat = tong_sau_giam + tong_sau_giam * vat / Decimal('100')
        self.TongTien = tong_co_vat
