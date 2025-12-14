from datetime import datetime
from os import abort
from flask import make_response
from app import app, dao, db
from app.models import PhongHat, ChiTietDatDichVu, HoaDon, DatPhong, DichVu, KhachHang, TaiKhoan, NhanVien
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
        dp = dao.tao_dat_phong(
            ma_phong,
            ma_khach_hang,
            tg_bd,
            tg_kt,
            so_nguoi
        )

        # --- Lưu dịch vụ ---
        dao.luu_chi_tiet_dich_vu(dp, selected_services, selected_services_data)

        # ✅ Xác định phương thức thanh toán ĐÚNG NGHIỆP VỤ
        if session.get("role") == "nhanvien":
            phuong_thuc_tt = request.form.get("phuong_thuc_tt", "TIEN_MAT")
        else:
            # khách hàng online luôn chuyển khoản
            phuong_thuc_tt = "CHUYEN_KHOAN"

        # --- Tạo hóa đơn ---
        hoa_don = dao.tao_hoa_don(dp, room, session, phuong_thuc_tt)

        # --- Dọn session ---
        session.pop("selected_services", None)
        session.pop("dat_phong_info", None)
        session.pop("khachhang_dat_phong", None)

        return redirect(url_for("xem_hoa_don", ma_hoa_don=hoa_don.MaHoaDon))

    return render_template(
        "dat_phong.html",
        room=room,
        selected_services=selected_services,
        selected_services_data=selected_services_data,
        dat_phong_info=dat_phong_info
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










