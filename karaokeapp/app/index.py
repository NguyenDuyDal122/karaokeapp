from datetime import datetime
from decimal import Decimal
from os import abort

import paypalrestsdk
from flask import make_response
from app import app, dao, db
from app.models import PhongHat, ChiTietDatDichVu, HoaDon, DatPhong, DichVu, KhachHang, TaiKhoan, NhanVien, \
    ChiTietHoaDonDichVuPhatSinh, HoaDonDichVuPhatSinh
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, flash, redirect, url_for, render_template, request
from xhtml2pdf import pisa
import io
from flask import abort


@app.route("/")
def index():
    rooms_vip = dao.get_phong_vip()
    rooms_thuong = dao.get_phong_thuong()

    # cập nhật trạng thái đặt phòng
    dao.cap_nhat_trang_thai_dat_phong()

    # xác định trạng thái hiển thị
    for r in rooms_vip + rooms_thuong:
        if r.TrangThai == "BAO_TRI":
            r.trang_thai_dat = "BAO_TRI"
        elif dao.phong_dang_hat(r.MaPhong):
            r.trang_thai_dat = "DANG_HAT"
        else:
            r.trang_thai_dat = "TRONG"

    return render_template(
        "home.html",
        rooms_vip=rooms_vip,
        rooms_thuong=rooms_thuong
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user, error = dao.check_login(username, password)

        if error:
            flash(error, "danger")
            return render_template("index.html")

        # ===== ĐĂNG NHẬP THÀNH CÔNG =====
        session["user"] = user.TenDangNhap
        session["role"] = user.VaiTro.lower()

        if session["role"] == "khachhang":
            session["user_id"] = user.khach_hang.MaKhachHang
            return redirect(url_for("index"))

        elif session["role"] == "nhanvien":
            session["user_id"] = user.nhan_vien.MaNhanVien
            return redirect(url_for("index"))

        elif session["role"] == "admin":
            session["user_id"] = user.MaTaiKhoan
            return redirect(url_for("admin_dashboard"))

    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        ok, msg = dao.dang_ky_khach_hang(
            request.form["username"],
            request.form["password"],
            request.form["hoten"],
            request.form["sdt"],
            request.form["email"]
        )

        flash(msg, "success" if ok else "danger")
        return redirect(url_for("login" if ok else "register"))

    return render_template("register.html")

# --- Đăng xuất ---
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/phong/<int:ma_phong>")
def chi_tiet_phong(ma_phong):
    dao.cap_nhat_trang_thai_dat_phong()

    room = dao.get_phong_by_id(ma_phong)
    if not room:
        return "Không tìm thấy phòng", 404

    room.trang_thai_dat = dao.get_trang_thai_hien_thi_phong(room)
    lich_dat = dao.get_lich_dat_phong_hop_le(ma_phong)

    return render_template(
        "chi_tiet_phong.html",
        room=room,
        lich_dat=lich_dat
    )

@app.route("/dat-phong/<int:ma_phong>", methods=["GET", "POST"])
def dat_phong(ma_phong):
    dao.cap_nhat_trang_thai_dat_phong()

    # --- Kiểm tra đăng nhập ---
    if "user" not in session or session.get("role") not in ["khachhang", "nhanvien"]:
        flash("Vui lòng đăng nhập để đặt phòng!", "warning")
        return redirect(url_for("login"))

    room = dao.get_phong_or_404(ma_phong)

    # --- Dịch vụ đã chọn ---
    selected_services_data = session.get("selected_services", [])
    selected_ids = [x["id"] for x in selected_services_data]
    selected_services = (
        DichVu.query.filter(DichVu.MaDichVu.in_(selected_ids)).all()
        if selected_ids else []
    )

    dat_phong_info = session.get("dat_phong_info", {})

    if request.method == "POST":

        # --- Chuyển sang chọn dịch vụ ---
        if "them_dich_vu" in request.form:
            session["dat_phong_info"] = request.form.to_dict()
            return redirect(url_for("them_dich_vu", ma_phong=ma_phong))

        # --- Lấy dữ liệu form ---
        ngay = request.form.get("ngay_dat")
        bd = request.form.get("gio_bat_dau")
        kt = request.form.get("gio_ket_thuc")
        so_nguoi = int(request.form.get("so_nguoi", 1))

        tg_bd = datetime.strptime(f"{ngay} {bd}", "%Y-%m-%d %H:%M")
        tg_kt = datetime.strptime(f"{ngay} {kt}", "%Y-%m-%d %H:%M")

        # --- Không cho đặt quá khứ ---
        hop_le, msg = dao.kiem_tra_thoi_gian_hop_le(tg_bd, tg_kt)
        if not hop_le:
            flash(msg, "danger")
            return redirect(url_for("dat_phong", ma_phong=ma_phong))

        # --- Không cho trùng giờ ---
        if dao.kiem_tra_xung_dot_gio(ma_phong, tg_bd, tg_kt):
            flash("❌ Phòng đã có người đặt trong khung giờ này!", "danger")
            return redirect(url_for("dat_phong", ma_phong=ma_phong))

        if session["role"] == "khachhang":
            ma_khach_hang = session["user_id"]
        else:
            ma_khach_hang = session.get("khachhang_dat_phong")
            if not ma_khach_hang:
                flash("Vui lòng chọn hoặc thêm khách hàng trước khi đặt phòng!", "warning")
                return redirect(url_for("them_khach_hang", ma_phong=ma_phong))

        # --- Tạo đặt phòng ---
        # --- Xác định trạng thái ban đầu ---
        if session["role"] == "nhanvien":
            trang_thai_ban_dau = "DA_XAC_NHAN"
        else:
            trang_thai_ban_dau = "CHO_XAC_NHAN"

        # --- Tạo đặt phòng ---
        dp = dao.tao_dat_phong(
            ma_phong,
            ma_khach_hang,
            tg_bd,
            tg_kt,
            so_nguoi,
            trang_thai_ban_dau
        )

        # --- Lưu dịch vụ ---
        dao.luu_chi_tiet_dich_vu(dp, selected_services, selected_services_data)

        # ✅ Xác định phương thức thanh toán ĐÚNG NGHIỆP VỤ
        if session.get("role") == "nhanvien":
            phuong_thuc_tt = request.form.get("phuong_thuc_tt", "TIEN_MAT")
        else:
            # khách hàng online luôn chuyển khoản
            phuong_thuc_tt = "CHUYEN_KHOAN"

        if session.get("role") == "khachhang":
            # lưu tạm ma_dat_phong để sau MoMo dùng
            session["cho_thanh_toan_dp"] = dp.MaDatPhong

            pay_url = dao.paypal_create_payment(
                ma_dat_phong=dp.MaDatPhong,
                so_tien=dao.tinh_tong_tien_tam(dp),
                return_endpoint="paypal_success",
                cancel_endpoint="paypal_cancel"
            )
            return redirect(pay_url)

        # --- NHÂN VIÊN: CHỈ ĐẶT PHÒNG ---
        flash("✅ Đặt phòng thành công. Khách sẽ thanh toán sau khi hát xong.", "success")

        session.pop("selected_services", None)
        session.pop("dat_phong_info", None)
        session.pop("khachhang_dat_phong", None)

        return redirect(url_for("chi_tiet_dat_phong", ma_dat_phong=dp.MaDatPhong))

    return render_template(
        "dat_phong.html",
        room=room,
        selected_services=selected_services,
        selected_services_data=selected_services_data,
        dat_phong_info=dat_phong_info,
        back_url=url_for("dat_phong", ma_phong=room.MaPhong)
    )

@app.route("/paypal-success")
def paypal_success():
    payment_id = request.args.get("paymentId")
    payer_id = request.args.get("PayerID")

    if not payment_id or not payer_id:
        flash("❌ Thiếu thông tin thanh toán PayPal!", "danger")
        return redirect(url_for("ds_phong"))

    # 1️⃣ Xác thực PayPal
    payment = paypalrestsdk.Payment.find(payment_id)

    if not payment.execute({"payer_id": payer_id}):
        flash("❌ Thanh toán PayPal thất bại!", "danger")
        return redirect(url_for("ds_phong"))

    # 2️⃣ Lấy mã đặt phòng từ SKU
    try:
        sku = payment.transactions[0].item_list.items[0].sku
        ma_dat_phong = int(sku.replace("DP", ""))
    except Exception:
        flash("❌ Không xác định được đơn đặt phòng!", "danger")
        return redirect(url_for("ds_phong"))

    dp = DatPhong.query.get_or_404(ma_dat_phong)

    # 3️⃣ Tạo hóa đơn QUA DAO (DAO sẽ tự gán MaNhanVien = ADMIN)
    hoa_don = dao.tao_hoa_don(
        dp=dp,
        room=dp.phong,
        session=session,
        phuong_thuc_tt="CHUYEN_KHOAN"
    )

    # 4️⃣ Cập nhật trạng thái đặt phòng
    dp.TrangThai = "CHO_XAC_NHAN"

    db.session.commit()

    # 5️⃣ Dọn session
    session.pop("cho_thanh_toan_dp", None)
    session.pop("selected_services", None)
    session.pop("dat_phong_info", None)

    return redirect(url_for("xem_hoa_don", ma_hoa_don=hoa_don.MaHoaDon))


@app.route("/paypal-cancel")
def paypal_cancel():
    ma_dat_phong = session.get("cho_thanh_toan_dp")

    if not ma_dat_phong:
        flash("❌ Không tìm thấy đơn đặt phòng để hủy!", "danger")
        return redirect(url_for("ds_phong"))

    dp = DatPhong.query.get_or_404(ma_dat_phong)

    # ✅ Cập nhật trạng thái
    dp.TrangThai = "HUY"

    db.session.commit()

    # ✅ Dọn session
    session.pop("cho_thanh_toan_dp", None)
    session.pop("selected_services", None)
    session.pop("dat_phong_info", None)

    return redirect(url_for("index"))


@app.route("/thanh-toan-phong")
def thanh_toan_phong():
    if session.get("role") != "nhanvien":
        flash("Bạn không có quyền truy cập!", "danger")
        return redirect(url_for("index"))

    # Lấy các đặt phòng CHƯA THANH TOÁN
    ds_dat_phong = DatPhong.query.filter_by(TrangThai="CHUA_THANH_TOAN").all()

    return render_template(
        "thanh_toan_phong.html",
        ds_dat_phong=ds_dat_phong
    )

@app.route("/lap-hoa-don/<int:ma_dat_phong>", methods=["POST"])
def lap_hoa_don(ma_dat_phong):
    if session.get("role") != "nhanvien":
        flash("Bạn không có quyền!", "danger")
        return redirect(url_for("index"))

    dp = DatPhong.query.get_or_404(ma_dat_phong)

    if dp.TrangThai == "DA_THANH_TOAN":
        flash("Phòng này đã thanh toán!", "warning")
        return redirect(url_for("thanh_toan_phong"))

    phuong_thuc_tt = request.form.get("phuong_thuc_tt")

    if phuong_thuc_tt not in ["TIEN_MAT", "CHUYEN_KHOAN"]:
        flash("Phương thức thanh toán không hợp lệ!", "danger")
        return redirect(url_for("thanh_toan_phong"))

    # ==========================
    # 💵 THANH TOÁN TIỀN MẶT
    # ==========================
    if phuong_thuc_tt == "TIEN_MAT":
        hoa_don = dao.tao_hoa_don(
            dp=dp,
            room=dp.phong,
            session=session,
            phuong_thuc_tt="TIEN_MAT"
        )

        dp.TrangThai = "DA_THANH_TOAN"

        # dịch vụ phát sinh -> đã thanh toán
        for hdps in hoa_don.hoa_don_phat_sinh:
            hdps.TrangThai = "DA_THANH_TOAN"

        db.session.commit()

        flash("✅ Thanh toán tiền mặt thành công!", "success")
        return redirect(url_for("xem_hoa_don", ma_hoa_don=hoa_don.MaHoaDon))

    # ==========================
    # 🌐 THANH TOÁN ONLINE PAYPAL
    # ==========================
    else:
        # lưu để callback paypal dùng
        session["nv_paypal_dp"] = dp.MaDatPhong

        pay_url = dao.paypal_create_payment(
            ma_dat_phong=dp.MaDatPhong,
            so_tien=dao.tinh_tong_tien_tam(dp),
            return_endpoint="paypal_success_nv",
            cancel_endpoint="thanh_toan_phong"
        )

        if not pay_url:
            flash("❌ Không tạo được thanh toán PayPal!", "danger")
            return redirect(url_for("thanh_toan_phong"))

        return redirect(pay_url)

@app.route("/paypal-success-nv")
def paypal_success_nv():
    payment_id = request.args.get("paymentId")
    payer_id = request.args.get("PayerID")

    if not payment_id or not payer_id:
        flash("❌ Thiếu thông tin PayPal!", "danger")
        return redirect(url_for("thanh_toan_phong"))

    payment = paypalrestsdk.Payment.find(payment_id)

    if not payment.execute({"payer_id": payer_id}):
        flash("❌ Thanh toán PayPal thất bại!", "danger")
        return redirect(url_for("thanh_toan_phong"))

    ma_dat_phong = session.get("nv_paypal_dp")
    if not ma_dat_phong:
        flash("❌ Không tìm thấy đặt phòng!", "danger")
        return redirect(url_for("thanh_toan_phong"))

    dp = DatPhong.query.get_or_404(ma_dat_phong)

    hoa_don = dao.tao_hoa_don(
        dp=dp,
        room=dp.phong,
        session=session,
        phuong_thuc_tt="CHUYEN_KHOAN"
    )

    dp.TrangThai = "DA_THANH_TOAN"

    for hdps in hoa_don.hoa_don_phat_sinh:
        hdps.TrangThai = "DA_THANH_TOAN"

    db.session.commit()

    session.pop("nv_paypal_dp", None)

    flash("✅ Thanh toán online thành công!", "success")
    return redirect(url_for("xem_hoa_don", ma_hoa_don=hoa_don.MaHoaDon))

@app.route("/paypal-cancel-nv")
def paypal_cancel_nv():
    session.pop("nv_paypal_dp", None)
    flash("❌ Đã hủy thanh toán PayPal", "warning")
    return redirect(url_for("thanh_toan_phong"))


@app.route("/dat-phong/<int:ma_dat_phong>/chi-tiet")
def chi_tiet_dat_phong(ma_dat_phong):
    dao.cap_nhat_trang_thai_dat_phong()
    dp = DatPhong.query.get_or_404(ma_dat_phong)

    # Chỉ nhân viên được xem màn này
    if session.get("role") != "nhanvien":
        flash("Bạn không có quyền truy cập!", "danger")
        return redirect(url_for("index"))

    return render_template(
        "chi_tiet_dat_phong.html",
        dp=dp
    )

@app.route("/dat-phong/<int:ma_phong>/them-dich-vu", methods=["GET", "POST"])
def them_dich_vu(ma_phong):

    # Lấy toàn bộ dịch vụ từ DAO
    services = dao.get_all_dich_vu()

    selected_services = session.get("selected_services", [])

    if request.method == "POST":
        selected_list = []

        form_services = request.form.getlist("dich_vu")

        for ma_dv in form_services:
            so_luong_key = f"soluong_{ma_dv}"
            so_luong = int(request.form.get(so_luong_key, 1))
            selected_list.append({
                "id": int(ma_dv),
                "so_luong": so_luong
            })

        session["selected_services"] = selected_list

        flash("✅ Dịch vụ đã được thêm vào đơn đặt phòng!", "success")
        return redirect(url_for("dat_phong", ma_phong=ma_phong))

    selected_ids = [item["id"] for item in selected_services]

    return render_template(
        "chon_dich_vu.html",
        services=services,
        selected_ids=selected_ids,
        selected_services=selected_services,
        ma_phong=ma_phong
    )

@app.route("/hoa-don/<int:ma_hoa_don>")
def xem_hoa_don(ma_hoa_don):
    hoa_don = dao.get_hoa_don_by_id(ma_hoa_don)
    if not hoa_don:
        abort(404)

    # lấy chi tiết dịch vụ theo đặt phòng
    chi_tiet_dv = dao.get_chi_tiet_dich_vu_by_dat_phong(
        hoa_don.MaDatPhong
    )

    return render_template(
        "hoa_don.html",
        hoa_don=hoa_don,
        chi_tiet_dv=chi_tiet_dv
    )

@app.route("/nhan-vien/xuat-hoa-don/<int:ma_hoa_don>")
def xuat_hoa_don_pdf(ma_hoa_don):

    if not session.get('role') == 'nhanvien':
        abort(403)

    hoa_don = dao.get_hoa_don_by_id(ma_hoa_don)
    if not hoa_don:
        abort(404)

    chi_tiet_dv = dao.get_chi_tiet_dich_vu_by_dat_phong(
        hoa_don.MaDatPhong
    )

    html = render_template(
        "hoa_don_pdf.html",   # 👈 nên tách file riêng
        hoa_don=hoa_don,
        chi_tiet_dv=chi_tiet_dv
    )

    result = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=result)

    response = make_response(result.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = \
        f"attachment; filename=hoa_don_{ma_hoa_don}.pdf"

    return response

@app.route("/thong-tin-tai-khoan")
def thong_tin_tai_khoan():
    dao.cap_nhat_trang_thai_dat_phong()

    if "user" not in session or session.get("role", "").lower() != "khachhang":
        flash("Vui lòng đăng nhập bằng tài khoản khách hàng để xem thông tin tài khoản.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    khach_hang = dao.get_khach_hang_by_id(user_id)
    if not khach_hang:
        flash("Không tìm thấy thông tin khách hàng!", "danger")
        return redirect(url_for("login"))

    return render_template(
        "thong_tin_tai_khoan.html",
        khach_hang=khach_hang
    )

@app.route("/thong-tin-nhan-vien")
def thong_tin_nhan_vien():
    dao.cap_nhat_trang_thai_dat_phong()

    if "user" not in session or session.get("role") != "nhanvien":
        flash("Bạn phải đăng nhập bằng tài khoản nhân viên.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    nv = dao.get_nhan_vien_by_id(user_id)
    if not nv:
        flash("Không tìm thấy thông tin nhân viên!", "danger")
        return redirect(url_for("index"))

    return render_template(
        "thong_tin_nhan_vien.html",
        nhan_vien=nv
    )

@app.route("/doi-mat-khau", methods=["GET", "POST"])
def doi_mat_khau():

    if "user" not in session:
        flash("Bạn phải đăng nhập để đổi mật khẩu.", "warning")
        return redirect(url_for("login"))

    role = session.get("role", "").lower()
    user_id = session.get("user_id")

    tai_khoan = dao.get_tai_khoan_theo_vai_tro(role, user_id)
    if not tai_khoan:
        flash("Không tìm thấy tài khoản!", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        mat_khau_cu = request.form.get("mat_khau_cu")
        mat_khau_moi = request.form.get("mat_khau_moi")
        nhap_lai = request.form.get("nhap_lai")

        ok, msg = dao.doi_mat_khau(
            tai_khoan,
            mat_khau_cu,
            mat_khau_moi,
            nhap_lai
        )

        if not ok:
            flash(msg, "danger")
            return redirect(url_for("doi_mat_khau"))

        flash(msg, "success")

        return redirect(
            url_for("thong_tin_tai_khoan")
            if role == "khachhang"
            else url_for("thong_tin_nhan_vien")
        )

    return render_template("doi_mat_khau.html")

@app.route("/lich-su-dat-phong")
def lich_su_dat_phong():

    if "user" not in session or session.get("role", "").lower() != "khachhang":
        flash("Vui lòng đăng nhập bằng tài khoản khách hàng để xem lịch sử đặt phòng.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    dat_phongs = dao.get_lich_su_dat_phong(user_id)

    return render_template(
        "lich_su_dat_phong.html",
        dat_phongs=dat_phongs
    )

@app.route("/huy-dat-phong/<int:ma_dat_phong>", methods=["POST"])
def huy_dat_phong(ma_dat_phong):

    if "user" not in session or session.get("role", "").lower() != "khachhang":
        flash("Vui lòng đăng nhập để thực hiện thao tác này.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    ok, msg = dao.huy_dat_phong(ma_dat_phong, user_id)

    flash(msg, "success" if ok else "danger")
    return redirect(url_for("lich_su_dat_phong"))

@app.route("/khach-hang/them/<int:ma_phong>", methods=["GET", "POST"])
def them_khach_hang(ma_phong):

    if request.method == "POST":
        ho_ten = request.form.get("HoTen", "").strip()
        so_dt = request.form.get("SoDienThoai", "").strip()
        email = request.form.get("Email", "").strip()

        if not ho_ten or not so_dt or not email:
            flash("Vui lòng điền đầy đủ các trường dữ liệu.", "danger")
            return redirect(url_for("them_khach_hang", ma_phong=ma_phong))

        kh = dao.tim_khach_hang_theo_sdt_email(so_dt, email)

        if not kh:
            kh = dao.tao_khach_hang(ho_ten, so_dt, email)
            flash("Thêm khách hàng thành công! Mời đặt phòng.", "success")
        else:
            flash("Khách hàng đã tồn tại, chuyển đến đặt phòng!", "success")

        session["khachhang_dat_phong"] = kh.MaKhachHang
        return redirect(url_for("dat_phong", ma_phong=ma_phong))

    return render_template("them_khach_hang.html", ma_phong=ma_phong)


@app.route("/nhan-vien/them-dv-phat-sinh/<int:ma_dat_phong>")
def chon_dich_vu_phat_sinh(ma_dat_phong):
    if session.get("role") != "nhanvien":
        flash("Không có quyền", "danger")
        return redirect(url_for("index"))

    dp = DatPhong.query.get_or_404(ma_dat_phong)
    ds_dich_vu = DichVu.query.all()

    return render_template(
        "chon_dich_vu.html",
        dp=dp,
        services=ds_dich_vu,
        ma_phong=dp.phong.MaPhong,
        back_url = url_for("phong_dang_hat")
    )


@app.route("/nhan-vien/phong-dang-hat")
def phong_dang_hat():
    dao.cap_nhat_trang_thai_dat_phong()
    if session.get("role") != "nhanvien":
        flash("Không có quyền", "danger")
        return redirect(url_for("index"))

    ds_dat_phong = DatPhong.query.filter_by(TrangThai="DANG_HAT").all()

    return render_template(
        "them_dich_vu_phat_sinh.html",
        ds_dat_phong=ds_dat_phong
    )

@app.route("/nhan-vien/luu-dv-phat-sinh/<int:ma_dat_phong>", methods=["POST"])
def luu_dv_phat_sinh(ma_dat_phong):
    dp = DatPhong.query.get_or_404(ma_dat_phong)
    dich_vu_ids = request.form.getlist("dich_vu")

    if not dich_vu_ids:
        flash("⚠️ Chưa chọn dịch vụ", "warning")
        return redirect(url_for("phong_dang_hat"))

    hd = dp.hoa_don  # có hoặc không

    # ===============================
    # TRƯỜNG HỢP 1: ĐÃ CÓ HÓA ĐƠN
    # ===============================
    if hd:
        hdps = HoaDonDichVuPhatSinh(
            MaHoaDon=hd.MaHoaDon,
            MaNhanVien=session["user_id"]
        )
        db.session.add(hdps)
        db.session.flush()

        tong = Decimal("0")

        for dv_id in dich_vu_ids:
            so_luong = int(request.form.get(f"soluong_{dv_id}", 1))
            dv = DichVu.query.get(dv_id)

            ct = ChiTietHoaDonDichVuPhatSinh(
                MaHDPhatSinh=hdps.MaHDPhatSinh,
                MaDichVu=dv_id,
                SoLuong=so_luong,
                ThanhTien=dv.DonGia * so_luong
            )
            tong += ct.ThanhTien
            db.session.add(ct)

        hdps.TongTien = tong
        db.session.commit()

        # 👉 chuyển sang giao diện thanh toán
        return redirect(
            url_for("thanh_toan_dv_phat_sinh", ma_hdps=hdps.MaHDPhatSinh)
        )

    # ===============================
    # TRƯỜNG HỢP 2: CHƯA CÓ HÓA ĐƠN
    # ===============================
    else:
        for dv_id in dich_vu_ids:
            so_luong = int(request.form.get(f"soluong_{dv_id}", 1))
            dv = DichVu.query.get(dv_id)

            ct = ChiTietDatDichVu.query.filter_by(
                MaDatPhong=dp.MaDatPhong,
                MaDichVu=dv_id
            ).first()

            if ct:
                ct.SoLuong += so_luong
                ct.ThanhTien += dv.DonGia * so_luong
            else:
                ct = ChiTietDatDichVu(
                    MaDatPhong=dp.MaDatPhong,
                    MaDichVu=dv_id,
                    SoLuong=so_luong,
                    ThanhTien=dv.DonGia * so_luong
                )
                db.session.add(ct)

        db.session.commit()

        flash("✅ Đã cộng thêm tiền dịch vụ", "success")
        return redirect(url_for("phong_dang_hat"))

@app.route("/nhan-vien/thanh-toan-dv-phat-sinh/<int:ma_hdps>", methods=["GET", "POST"])
def thanh_toan_dv_phat_sinh(ma_hdps):
    if session.get("role") != "nhanvien":
        flash("Không có quyền", "danger")
        return redirect(url_for("index"))

    hdps = HoaDonDichVuPhatSinh.query.get_or_404(ma_hdps)
    dp = hdps.hoa_don.dat_phong
    dao.cap_nhat_trang_thai_dat_phong()

    if request.method == "POST":
        phuong_thuc = request.form.get("phuong_thuc_tt")

        # ====== THANH TOÁN TIỀN MẶT ======
        if phuong_thuc == "TIEN_MAT":
            hdps.TrangThai = "DA_THANH_TOAN"
            db.session.commit()
            flash("✅ Thanh toán tiền mặt thành công", "success")
            return redirect(url_for("phong_dang_hat", ma_hdps=hdps.MaHDPhatSinh))

        # ====== THANH TOÁN ONLINE PAYPAL ======
        elif phuong_thuc == "CHUYEN_KHOAN":
            # lưu session để callback Paypal xử lý
            session["nv_paypal_hdps"] = hdps.MaHDPhatSinh
            so_tien = hdps.TongTien
            pay_url = dao.paypal_create_payment(
                ma_dat_phong=dp.MaDatPhong,
                so_tien=so_tien,
                return_endpoint="paypal_success_dv_nv",
                cancel_endpoint="paypal_cancel_dv_nv"
            )
            if not pay_url:
                flash("❌ Không tạo được thanh toán PayPal!", "danger")
                return redirect(url_for("thanh_toan_dv_phat_sinh", ma_hdps=hdps.MaHDPhatSinh))
            return redirect(pay_url)

    return render_template("thanh_toan_dv_phat_sinh.html", hdps=hdps)


@app.route("/paypal-success-dv-nv")
def paypal_success_dv_nv():
    payment_id = request.args.get("paymentId")
    payer_id = request.args.get("PayerID")

    if not payment_id or not payer_id:
        flash("❌ Thiếu thông tin PayPal!", "danger")
        return redirect(url_for("phong_dang_hat"))

    payment = paypalrestsdk.Payment.find(payment_id)

    if not payment.execute({"payer_id": payer_id}):
        flash("❌ Thanh toán PayPal thất bại!", "danger")
        return redirect(url_for("phong_dang_hat"))

    ma_hdps = session.get("nv_paypal_hdps")
    if not ma_hdps:
        flash("❌ Không tìm thấy hóa đơn dịch vụ!", "danger")
        return redirect(url_for("phong_dang_hat"))

    hdps = HoaDonDichVuPhatSinh.query.get_or_404(ma_hdps)
    hdps.TrangThai = "DA_THANH_TOAN"
    db.session.commit()
    session.pop("nv_paypal_hdps", None)

    flash("✅ Thanh toán Paypal thành công!", "success")
    return redirect(url_for("phong_dang_hat", ma_hdps=hdps.MaHDPhatSinh))

@app.route("/paypal-cancel-dv-nv")
def paypal_cancel_dv_nv():
    session.pop("nv_paypal_hdps", None)
    flash("❌ Đã hủy thanh toán PayPal dịch vụ", "warning")
    return redirect(url_for("phong_dang_hat"))

















