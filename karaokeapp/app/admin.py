from flask import render_template, session, redirect, url_for, flash, request
from app import app, db
import app.daoadmin as dao
import cloudinary.uploader

from app.models import PhongHat


# ===== CHECK ADMIN =====
def admin_required():
    return "user" in session and session.get("role") == "admin"


@app.route("/admin")
def admin_dashboard():
    if not admin_required():
        flash("⚠️ Bạn không có quyền truy cập admin!", "danger")
        return redirect(url_for("login"))

    doanh_thu_nam = dao.thong_ke_doanh_thu_theo_nam()

    # Tách dữ liệu cho chart
    labels = [str(nam) for nam, _ in doanh_thu_nam]
    values = [float(tien) for _, tien in doanh_thu_nam]

    return render_template(
        "admintemplates/dashboard.html",
        labels=labels,
        values=values
    )

# ===== QUẢN LÝ TÀI KHOẢN =====
@app.route("/admin/tai-khoan")
def admin_tai_khoan():
    if not admin_required():
        return redirect(url_for("login"))

    ds_tk = dao.get_all_tai_khoan()
    return render_template(
        "admintemplates/tai_khoan.html",
        ds_tk=ds_tk
    )


@app.route("/admin/tai-khoan/khoa/<int:ma_tk>")
def khoa_tai_khoan(ma_tk):
    if not admin_required():
        return redirect(url_for("login"))

    dao.toggle_trang_thai(ma_tk)
    flash("🔒 Đã thay đổi trạng thái tài khoản", "warning")
    return redirect(url_for("admin_tai_khoan"))


@app.route("/admin/tai-khoan/xoa/<int:ma_tk>")
def xoa_tai_khoan(ma_tk):
    if not admin_required():
        return redirect(url_for("login"))

    dao.delete_tai_khoan(ma_tk)
    flash("🗑️ Đã xóa tài khoản", "danger")
    return redirect(url_for("admin_tai_khoan"))

@app.route("/admin/khach-hang")
def admin_khach_hang():
    if not admin_required():
        return redirect(url_for("login"))

    keyword = request.args.get("keyword")
    ds_khach = dao.get_all_khach_hang(keyword)

    return render_template(
        "admintemplates/khach_hang.html",
        ds_khach=ds_khach,
        keyword=keyword
    )

@app.route("/admin/khach-hang/sua/<int:ma_kh>", methods=["GET", "POST"])
def sua_khach_hang(ma_kh):
    if not admin_required():
        return redirect(url_for("login"))

    kh = dao.get_khach_hang_by_id(ma_kh)

    if request.method == "POST":
        data = {
            "HoTen": request.form["HoTen"],
            "SoDienThoai": request.form["SoDienThoai"],
            "Email": request.form["Email"]
        }
        dao.update_khach_hang(ma_kh, data)
        flash("✅ Cập nhật khách hàng thành công", "success")
        return redirect(url_for("admin_khach_hang"))

    return render_template(
        "admintemplates/khach_hang_sua.html",
        kh=kh
    )

@app.route("/admin/khach-hang/khoa/<int:ma_kh>")
def khoa_khach_hang(ma_kh):
    if not admin_required():
        return redirect(url_for("login"))

    dao.toggle_khach_hang(ma_kh)
    flash("🔒 Đã thay đổi trạng thái tài khoản khách hàng", "warning")
    return redirect(url_for("admin_khach_hang"))



@app.route("/admin/nhan-vien")
def admin_nhan_vien():
    if not admin_required():
        return redirect(url_for("login"))

    keyword = request.args.get("keyword")
    ds_nv = dao.get_all_nhan_vien(keyword)

    return render_template(
        "admintemplates/nhan_vien.html",
        ds_nv=ds_nv,
        keyword=keyword
    )


@app.route("/admin/nhan-vien/sua/<int:ma_nv>", methods=["GET", "POST"])
def sua_nhan_vien(ma_nv):
    if not admin_required():
        return redirect(url_for("login"))

    nv = dao.get_nhan_vien_by_id(ma_nv)

    if request.method == "POST":
        data = {
            "HoTen": request.form["HoTen"],
            "ChucVu": request.form["ChucVu"]
        }
        dao.update_nhan_vien(ma_nv, data)
        flash("✅ Cập nhật nhân viên thành công", "success")
        return redirect(url_for("admin_nhan_vien"))

    return render_template(
        "admintemplates/nhan_vien_sua.html",
        nv=nv
    )


@app.route("/admin/nhan-vien/khoa/<int:ma_nv>")
def khoa_nhan_vien(ma_nv):
    if not admin_required():
        return redirect(url_for("login"))

    dao.toggle_nhan_vien(ma_nv)
    flash("🔒 Đã thay đổi trạng thái tài khoản nhân viên", "warning")
    return redirect(url_for("admin_nhan_vien"))

@app.route("/admin/phong-hat")
def admin_phong_hat():
    if not admin_required():
        return redirect(url_for("login"))

    keyword = request.args.get("keyword")
    ds_phong = dao.get_all_phong(keyword)

    return render_template(
        "admintemplates/phong_hat.html",
        ds_phong=ds_phong,
        keyword=keyword
    )


@app.route("/admin/phong-hat/them", methods=["GET", "POST"])
def them_phong_hat():
    if request.method == "POST":
        hinh_anh = request.files.get("HinhAnh")
        image_url = None

        if hinh_anh:
            result = cloudinary.uploader.upload(
                hinh_anh,
                folder="karaoke/phong_hat"
            )
            image_url = result["secure_url"]

        phong = PhongHat(
            TenPhong=request.form["TenPhong"],
            SucChua=request.form["SucChua"],
            GiaGio=request.form["GiaGio"],
            LoaiPhong=request.form["LoaiPhong"],
            TrangThai=request.form["TrangThai"],
            MoTa=request.form["MoTa"],
            HinhAnh=image_url
        )

        db.session.add(phong)
        db.session.commit()
        return redirect(url_for("admin_phong_hat"))

    return render_template("admintemplates/phong_hat_them.html")


@app.route("/admin/phong-hat/sua/<int:ma_phong>", methods=["GET", "POST"])
def sua_phong_hat(ma_phong):
    phong = PhongHat.query.get_or_404(ma_phong)

    if request.method == "POST":
        phong.TenPhong = request.form["TenPhong"]
        phong.SucChua = request.form["SucChua"]
        phong.GiaGio = request.form["GiaGio"]
        phong.LoaiPhong = request.form["LoaiPhong"]
        phong.TrangThai = request.form["TrangThai"]
        phong.MoTa = request.form["MoTa"]

        hinh_anh = request.files.get("HinhAnh")
        if hinh_anh:
            result = cloudinary.uploader.upload(
                hinh_anh,
                folder="karaoke/phong_hat"
            )
            phong.HinhAnh = result["secure_url"]

        db.session.commit()
        return redirect(url_for("admin_phong_hat"))

    return render_template(
        "admintemplates/phong_hat_sua.html",
        phong=phong
    )


@app.route("/admin/phong-hat/xoa/<int:ma_phong>")
def xoa_phong_hat(ma_phong):
    if not admin_required():
        return redirect(url_for("login"))

    dao.delete_phong(ma_phong)
    flash("🗑️ Đã xóa phòng hát", "danger")
    return redirect(url_for("admin_phong_hat"))

@app.route("/admin/dich-vu")
def admin_dich_vu():
    if not admin_required():
        return redirect(url_for("login"))

    ds_dv = dao.get_all_dich_vu()
    return render_template("admintemplates/dich_vu.html", ds_dv=ds_dv)

@app.route("/admin/dich-vu/them", methods=["GET", "POST"])
def add_dich_vu():
    if not admin_required():
        return redirect(url_for("login"))

    if request.method == "POST":
        hinh = request.files.get("HinhAnh")
        hinh_url = None

        if hinh:
            upload = cloudinary.uploader.upload(hinh)
            hinh_url = upload["secure_url"]

        data = {
            "TenDichVu": request.form["TenDichVu"],
            "DonGia": request.form["DonGia"],
            "HinhAnh": hinh_url,
            "MoTa": request.form["MoTa"]
        }

        dao.them_dich_vu(data)
        flash("✅ Thêm dịch vụ thành công", "success")
        return redirect(url_for("admin_dich_vu"))

    return render_template("admintemplates/dich_vu_them.html")

@app.route("/admin/dich-vu/sua/<int:ma_dv>", methods=["GET", "POST"])
def sua_dich_vu(ma_dv):
    if not admin_required():
        return redirect(url_for("login"))

    dv = dao.get_dich_vu_by_id(ma_dv)

    if request.method == "POST":
        hinh = request.files.get("HinhAnh")
        hinh_url = dv.HinhAnh

        if hinh:
            upload = cloudinary.uploader.upload(hinh)
            hinh_url = upload["secure_url"]

        data = {
            "TenDichVu": request.form["TenDichVu"],
            "DonGia": request.form["DonGia"],
            "HinhAnh": hinh_url,
            "MoTa": request.form["MoTa"]
        }

        dao.update_dich_vu(ma_dv, data)
        flash("✅ Cập nhật dịch vụ thành công", "success")
        return redirect(url_for("admin_dich_vu"))

    return render_template("admintemplates/dich_vu_sua.html", dv=dv)

@app.route("/admin/dich-vu/xoa/<int:ma_dv>")
def xoa_dich_vu(ma_dv):
    if not admin_required():
        return redirect(url_for("login"))

    dao.xoa_dich_vu(ma_dv)
    flash("🗑️ Đã xóa dịch vụ", "danger")
    return redirect(url_for("admin_dich_vu"))

@app.route("/admin/dat-phong")
def admin_dat_phong():
    if not admin_required():
        return redirect(url_for("login"))

    keyword = request.args.get("keyword")
    trang_thai = request.args.get("trang_thai")

    ds_dat = dao.get_all_dat_phong(keyword, trang_thai)

    return render_template(
        "admintemplates/dat_phong.html",
        ds_dat=ds_dat,
        keyword=keyword,
        trang_thai=trang_thai
    )


@app.route("/admin/dat-phong/trang-thai/<int:ma_dp>/<trang_thai>")
def cap_nhat_trang_thai_dat_phong(ma_dp, trang_thai):
    if not admin_required():
        return redirect(url_for("login"))

    TRANG_THAI_HOP_LE = [
        'CHO_XAC_NHAN',
        'DA_XAC_NHAN',
        'DANG_HAT',
        'CHUA_THANH_TOAN',
        'DA_THANH_TOAN',
        'HUY'
    ]

    if trang_thai not in TRANG_THAI_HOP_LE:
        flash("❌ Trạng thái không hợp lệ", "danger")
        return redirect(url_for("admin_dat_phong"))

    dp = dao.get_dat_phong_by_id(ma_dp)
    if not dp:
        flash("❌ Không tìm thấy đặt phòng", "danger")
        return redirect(url_for("admin_dat_phong"))

    dao.update_trang_thai_dat_phong(ma_dp, trang_thai)
    flash("✅ Cập nhật trạng thái đặt phòng thành công", "success")

    return redirect(url_for("admin_dat_phong"))

@app.route("/admin/hoa-don")
def admin_hoa_don():
    if not admin_required():
        return redirect(url_for("login"))

    keyword = request.args.get("keyword")

    hoa_dons = dao.get_all_hoa_don(keyword)

    return render_template(
        "admintemplates/hoa_don.html",
        hoa_dons=hoa_dons,
        keyword=keyword
    )

@app.route("/admin/thong-ke", methods=["GET", "POST"])
def admin_thong_ke():
    if not admin_required():
        return redirect(url_for("login"))

    loai = request.form.get("loai", "ngay")

    thong_ke = dao.thong_ke_doanh_thu(loai)
    tong_dt = dao.tong_doanh_thu()

    # Tách dữ liệu cho biểu đồ
    labels = [str(tg) for tg, _ in thong_ke]
    values = [float(tien) for _, tien in thong_ke]

    return render_template(
        "admintemplates/thong_ke.html",
        thong_ke=thong_ke,
        labels=labels,
        values=values,
        loai=loai,
        tong_dt=tong_dt
    )

