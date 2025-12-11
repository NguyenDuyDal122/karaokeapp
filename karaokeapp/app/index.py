from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session
from app import app, dao, db
from app.models import PhongHat, ChiTietDatDichVu, HoaDon, DatPhong, DichVu, KhachHang, TaiKhoan, NhanVien
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal


@app.route("/")
def index():
    from app.models import PhongHat, DatPhong
    from datetime import datetime

    rooms_vip = PhongHat.query.filter_by(LoaiPhong='VIP').all()
    rooms_thuong = PhongHat.query.filter_by(LoaiPhong='THUONG').all()

    now = datetime.now()

    # ---------- CẬP NHẬT TỰ ĐỘNG TRẠNG THÁI ĐẶT PHÒNG ----------
    tat_ca_dat = DatPhong.query.filter(DatPhong.TrangThai != "HUY").all()

    for dat in tat_ca_dat:
        if dat.ThoiGianBatDau <= now <= dat.ThoiGianKetThuc:
            if dat.TrangThai != "DANG_HAT":
                dat.TrangThai = "DANG_HAT"
        elif now > dat.ThoiGianKetThuc:
            if dat.TrangThai != "DA_THANH_TOAN":
                dat.TrangThai = "DA_THANH_TOAN"

    db.session.commit()

    # ---------- XÁC ĐỊNH TRẠNG THÁI HIỂN THỊ CHO TỪNG PHÒNG ----------
    for r in rooms_vip + rooms_thuong:

        # Nếu phòng bảo trì thì giữ nguyên và bỏ qua
        if r.TrangThai == "BAO_TRI":
            r.trang_thai_dat = "BAO_TRI"
            continue

        # Mặc định phòng trống
        r.trang_thai_dat = "TRONG"

        # Kiểm tra có lịch đặt đang hát không
        dp = DatPhong.query.filter(
            DatPhong.MaPhong == r.MaPhong,
            DatPhong.TrangThai == "DANG_HAT"
        ).first()

        if dp:
            r.trang_thai_dat = "DANG_HAT"

    return render_template(
        "home.html",
        rooms_vip=rooms_vip,
        rooms_thuong=rooms_thuong
    )

# --- Trang đăng nhập ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = dao.check_login(username, password)

        if user:
            # Lưu username và vai trò
            session["user"] = user.TenDangNhap
            session["role"] = user.VaiTro.lower()  # chuyển về chữ thường cho chắc chắn

            # Lưu đúng user_id theo vai trò
            if session["role"] == "khachhang":
                if user.khach_hang:
                    session["user_id"] = user.khach_hang.MaKhachHang
                else:
                    flash("Tài khoản không có dữ liệu khách hàng!", "danger")
                    return redirect(url_for("login"))

            elif session["role"] == "nhanvien":

                if user.nhan_vien:

                    session["nhanvien_id"] = user.nhan_vien.MaNhanVien

                    session["user_id"] = user.nhan_vien.MaNhanVien  # vẫn giữ nếu cần

                else:

                    flash("Tài khoản không có dữ liệu nhân viên!", "danger")

                    return redirect(url_for("login"))

            elif session["role"] == "admin":
                # admin không cần MaKhachHang / MaNhanVien
                session["user_id"] = user.MaTaiKhoan

            else:
                flash("❌ Vai trò không hợp lệ!", "danger")
                return redirect(url_for("login"))

            # Điều hướng theo vai trò
            if session["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("index"))

        # Nếu login sai
        flash("❌ Sai tên đăng nhập hoặc mật khẩu, hoặc tài khoản bị khóa!", "danger")

    # Hiện trang login
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hoten = request.form.get("hoten")
        sdt = request.form.get("sdt")
        email = request.form.get("email")

        # --- 1) Kiểm tra trùng username ---
        exist = TaiKhoan.query.filter_by(TenDangNhap=username).first()
        if exist:
            flash("❌ Tên đăng nhập đã tồn tại!", "danger")
            return redirect(url_for("register"))

        # --- 2) Kiểm tra SDT hoặc Email đã tồn tại trong bảng KhachHang ---
        kh_exist = KhachHang.query.filter(
            (KhachHang.SoDienThoai == sdt) | (KhachHang.Email == email)
        ).first()

        if kh_exist:
            # --- A) Đã có tài khoản ---
            if kh_exist.MaTaiKhoan is not None:
                flash("❌ Số điện thoại hoặc email đã có tài khoản trước đó!", "danger")
                return redirect(url_for("register"))

            # --- B) Chưa có tài khoản → cập nhật luôn ---
            hashed_password = generate_password_hash(password)

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

            flash("✅ Đăng ký thành công! Tài khoản đã được gắn với thông tin của bạn.", "success")
            return redirect(url_for("login"))

        # --- 3) Trường hợp hoàn toàn mới → tạo mới cả 2 bảng ---
        hashed_password = generate_password_hash(password)

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

        flash("✅ Đăng ký thành công! Hãy đăng nhập.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# --- Đăng xuất ---
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# --- Trang của nhân viên ---
@app.route("/staff")
def staff_dashboard():
    if "user" not in session or session["role"].lower() != "nhanvien":
        flash("⚠️ Bạn không có quyền truy cập trang nhân viên!", "warning")
        return redirect(url_for("login"))
    return f"""
        <h2>Xin chào {session['user']} (Nhân viên)</h2>
        <p>Đây là trang dành cho nhân viên.</p>
        <a href='/logout'>Đăng xuất</a>
    """


# --- Trang của admin ---
@app.route("/admin")
def admin_dashboard():
    if "user" not in session or session["role"].lower() != "admin":
        flash("⚠️ Bạn không có quyền truy cập trang admin!", "warning")
        return redirect(url_for("login"))
    return f"""
        <h2>Xin chào {session['user']} (Admin)</h2>
        <p>Đây là trang quản trị hệ thống.</p>
        <a href='/logout'>Đăng xuất</a>
    """

@app.route("/phong/<int:ma_phong>")
def chi_tiet_phong(ma_phong):
    from app.models import PhongHat, DatPhong

    room = PhongHat.query.get(ma_phong)
    if not room:
        return "Không tìm thấy phòng", 404

    # ---------- XÁC ĐỊNH TRẠNG THÁI HIỂN THỊ ----------
    if room.TrangThai == "BAO_TRI":
        room.trang_thai_dat = "BAO_TRI"
    else:
        dp = DatPhong.query.filter(
            DatPhong.MaPhong == ma_phong,
            DatPhong.TrangThai == "DANG_HAT"
        ).first()

        room.trang_thai_dat = "DANG_HAT" if dp else "TRONG"

    # ---------- DANH SÁCH LỊCH ĐẶT (LOẠI BỎ HỦY + ĐÃ THANH TOÁN) ----------
    lich_dat = DatPhong.query.filter(
        DatPhong.MaPhong == ma_phong,
        DatPhong.TrangThai.notin_(["HUY", "DA_THANH_TOAN"])
    ).order_by(DatPhong.ThoiGianBatDau.asc()).all()

    return render_template("chi_tiet_phong.html",
                           room=room,
                           lich_dat=lich_dat)

@app.route("/dat-phong/<int:ma_phong>", methods=["GET", "POST"])
def dat_phong(ma_phong):
    # Kiểm tra đăng nhập và vai trò
    if "user" not in session or session["role"].lower() != "khachhang" and session["role"].lower() != "nhanvien":
        flash("Vui lòng đăng nhập bằng tài khoản khách hàng hoặc nhân viên để đặt phòng.", "warning")
        return redirect(url_for("login"))

    room = PhongHat.query.get_or_404(ma_phong)

    # Lấy danh sách dịch vụ đã chọn từ session
    selected_services_data = session.get("selected_services", [])
    selected_ids = [item["id"] for item in selected_services_data]
    selected_services = DichVu.query.filter(DichVu.MaDichVu.in_(selected_ids)).all()

    # Lấy dữ liệu tạm từ session (ngày, giờ, số người)
    dat_phong_info = session.get("dat_phong_info", {})

    if request.method == "POST":
        if "them_dich_vu" in request.form:
            # Lưu thông tin tạm vào session và chuyển sang chọn dịch vụ
            session["dat_phong_info"] = {
                "ngay_dat": request.form.get("ngay_dat"),
                "gio_bat_dau": request.form.get("gio_bat_dau"),
                "gio_ket_thuc": request.form.get("gio_ket_thuc"),
                "so_nguoi": request.form.get("so_nguoi"),
            }
            return redirect(url_for("them_dich_vu", ma_phong=ma_phong))

        elif "thanh_toan" in request.form:
            # --- Lấy thông tin đặt phòng ---
            try:
                ngay_dat = request.form["ngay_dat"]
                gio_bat_dau = request.form["gio_bat_dau"]
                gio_ket_thuc = request.form["gio_ket_thuc"]
                so_nguoi = int(request.form["so_nguoi"])
            except (KeyError, ValueError):
                flash("Vui lòng nhập đầy đủ thông tin hợp lệ!", "danger")
                return redirect(url_for("dat_phong", ma_phong=ma_phong))

            # --- Gộp ngày và giờ ---
            thoi_gian_bd = datetime.strptime(f"{ngay_dat} {gio_bat_dau}", "%Y-%m-%d %H:%M")
            thoi_gian_kt = datetime.strptime(f"{ngay_dat} {gio_ket_thuc}", "%Y-%m-%d %H:%M")

            # --- Không cho đặt ngày/giờ trong quá khứ ---
            now = datetime.now()
            if thoi_gian_bd < now:
                flash("❌ Không thể đặt phòng trong quá khứ!", "danger")
                return redirect(url_for("dat_phong", ma_phong=ma_phong))

            if thoi_gian_kt <= thoi_gian_bd:
                flash("❌ Giờ kết thúc phải lớn hơn giờ bắt đầu!", "danger")
                return redirect(url_for("dat_phong", ma_phong=ma_phong))

            # --- Kiểm tra trùng khung giờ ---
            xung_dot = DatPhong.query.filter(
                DatPhong.MaPhong == ma_phong,
                DatPhong.ThoiGianBatDau < thoi_gian_kt,
                DatPhong.ThoiGianKetThuc > thoi_gian_bd
            ).first()
            if xung_dot:
                flash("❌ Phòng này đã có người đặt trong khung giờ bạn chọn! Vui lòng chọn thời gian khác.", "danger")
                return redirect(url_for("dat_phong", ma_phong=ma_phong))

            # --- Lấy số lượng dịch vụ từ form ---
            so_luong_map = {}
            for dv in selected_services:
                key = f"soluong_{dv.MaDichVu}"
                try:
                    so_luong_map[dv.MaDichVu] = int(request.form.get(key, 1))
                    if so_luong_map[dv.MaDichVu] < 1:
                        so_luong_map[dv.MaDichVu] = 1
                except ValueError:
                    so_luong_map[dv.MaDichVu] = 1

            # --- Lưu DatPhong ---
            khach_hang_id = session.get("user_id")
            if not khach_hang_id:
                flash("Không xác định được khách hàng!", "danger")
                return redirect(url_for("login"))

            dp = DatPhong(
                MaKhachHang=khach_hang_id,
                MaPhong=ma_phong,
                ThoiGianBatDau=thoi_gian_bd,
                ThoiGianKetThuc=thoi_gian_kt,
                SoNguoi=so_nguoi
            )
            db.session.add(dp)
            db.session.commit()

            # --- Thêm chi tiết dịch vụ ---
            for dv in selected_services:
                # Lấy số lượng từ session
                item = next((x for x in selected_services_data if x['id'] == dv.MaDichVu), None)
                so_luong = item['so_luong'] if item else 1

                ctdv = ChiTietDatDichVu(
                    MaDatPhong=dp.MaDatPhong,
                    MaDichVu=dv.MaDichVu,
                    SoLuong=so_luong,
                    ThanhTien=Decimal(dv.DonGia) * so_luong
                )
                db.session.add(ctdv)

            db.session.commit()

            # --- Tính tiền ---
            so_gio = Decimal((thoi_gian_kt - thoi_gian_bd).seconds) / Decimal(3600)
            tien_dich_vu = sum(ct.ThanhTien for ct in dp.chi_tiet_dv)

            # --- Xác định mã nhân viên lập hóa đơn ---
            ma_nhan_vien = None

            if session.get("role") == "nhanvien":
                # Nhân viên STAFF đang đăng nhập -> gán chính nhân viên này
                ma_nhan_vien = session.get("nhanvien_id")

            elif session.get("role") == "khachhang":
                # Nếu khách đặt -> tự động lấy nhân viên có chức vụ ADMIN
                admin_nv = NhanVien.query.filter_by(ChucVu="ADMIN").first()
                if admin_nv:
                    ma_nhan_vien = admin_nv.MaNhanVien

            hoa_don = HoaDon(
                MaDatPhong=dp.MaDatPhong,
                TienPhong=Decimal(room.GiaGio) * so_gio,
                TienDichVu=tien_dich_vu,
                PhuongThucThanhToan='TIEN_MAT',
                Nguon='ONLINE',
                MaNhanVien=ma_nhan_vien  # <-- dùng đúng nhân viên đang thao tác
            )

            # --- Giảm 5% nếu khách đã đặt >= 10 lần ---
            kh = KhachHang.query.get(khach_hang_id)
            if kh:
                kh.SoLuotDatThang = (kh.SoLuotDatThang or 0) + 1
                db.session.commit()

                if kh.SoLuotDatThang >= 10:
                    tong_truoc_giam = hoa_don.TienPhong + hoa_don.TienDichVu
                    giam_gia = tong_truoc_giam * Decimal('0.05')
                    hoa_don.GiamGia = giam_gia  # nếu model HoaDon có cột GiamGia
                    # 🔁 Reset lại số lượt đặt trong tháng
                    kh.SoLuotDatThang = 0
                    db.session.commit()
                else:
                    hoa_don.GiamGia = Decimal('0.00')
            else:
                hoa_don.GiamGia = Decimal('0.00')

            # --- Tính tổng sau khi giảm và VAT ---
            hoa_don.tinh_tong_tien()
            db.session.add(hoa_don)
            db.session.commit()

            # --- Dọn session ---
            session.pop("selected_services", None)
            session.pop("dat_phong_info", None)

            return redirect(url_for("xem_hoa_don", ma_hoa_don=hoa_don.MaHoaDon))

    # Nếu là GET: render giao diện
    return render_template(
        "dat_phong.html",
        room=room,
        selected_services=selected_services,
        selected_services_data=selected_services_data,
        dat_phong_info=dat_phong_info
    )

@app.route("/dat-phong/<int:ma_phong>/them-dich-vu", methods=["GET", "POST"])
def them_dich_vu(ma_phong):
    # Lấy toàn bộ dịch vụ từ CSDL
    services = DichVu.query.all()

    # Lấy danh sách dịch vụ đã chọn từ session (dạng list chứa dict)
    selected_services = session.get("selected_services", [])

    if request.method == "POST":
        selected_list = []

        # Lấy danh sách các dịch vụ được chọn từ form
        form_services = request.form.getlist("dich_vu")

        for ma_dv in form_services:
            so_luong_key = f"soluong_{ma_dv}"
            so_luong = int(request.form.get(so_luong_key, 1))
            selected_list.append({"id": int(ma_dv), "so_luong": so_luong})

        # Lưu vào session
        session["selected_services"] = selected_list

        flash("✅ Dịch vụ đã được thêm vào đơn đặt phòng!", "success")
        return redirect(url_for("dat_phong", ma_phong=ma_phong))

    # Chuẩn bị danh sách ID dịch vụ đã chọn để đánh dấu checked
    selected_ids = [item["id"] for item in selected_services]

    return render_template(
        "chon_dich_vu.html",
        services=services,
        selected_ids=selected_ids,
        selected_services=selected_services,  # thêm dòng này
        ma_phong=ma_phong
    )

@app.route("/hoa-don/<int:ma_hoa_don>")
def xem_hoa_don(ma_hoa_don):
    hoa_don = HoaDon.query.get_or_404(ma_hoa_don)
    chi_tiet_dv = ChiTietDatDichVu.query.filter_by(MaDatPhong=hoa_don.MaDatPhong).all()
    return render_template("hoa_don.html", hoa_don=hoa_don, chi_tiet_dv=chi_tiet_dv)

@app.route("/thong-tin-tai-khoan")
def thong_tin_tai_khoan():
    # Kiểm tra đăng nhập
    if "user" not in session or session.get("role", "").lower() != "khachhang":
        flash("Vui lòng đăng nhập bằng tài khoản khách hàng để xem thông tin tài khoản.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    khach_hang = KhachHang.query.get(user_id)
    if not khach_hang:
        flash("Không tìm thấy thông tin khách hàng!", "danger")
        return redirect(url_for("login"))

    return render_template("thong_tin_tai_khoan.html", khach_hang=khach_hang)

@app.route("/thong-tin-nhan-vien")
def thong_tin_nhan_vien():
    if "user" not in session or session.get("role") != "nhanvien":
        flash("Bạn phải đăng nhập bằng tài khoản nhân viên.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")  # đây là MaNhanVien
    nv = NhanVien.query.get(user_id)  # lấy đúng theo khóa chính MaNhanVien

    if not nv:
        flash("Không tìm thấy thông tin nhân viên!", "danger")
        return redirect(url_for("index"))

    return render_template("thong_tin_nhan_vien.html", nhan_vien=nv)

@app.route("/doi-mat-khau", methods=["GET", "POST"])
def doi_mat_khau():

    # Kiểm tra đăng nhập
    if "user" not in session:
        flash("Bạn phải đăng nhập để đổi mật khẩu.", "warning")
        return redirect(url_for("login"))

    role = session.get("role", "").lower()
    user_id = session.get("user_id")

    # Lấy đúng tài khoản theo vai trò
    tai_khoan = None

    if role == "khachhang":
        kh = KhachHang.query.get(user_id)
        if not kh:
            flash("Không tìm thấy thông tin khách hàng!", "danger")
            return redirect(url_for("login"))
        tai_khoan = kh.tai_khoan

    elif role == "nhanvien":
        nv = NhanVien.query.get(user_id)
        if not nv:
            flash("Không tìm thấy thông tin nhân viên!", "danger")
            return redirect(url_for("login"))
        tai_khoan = nv.tai_khoan

    else:
        flash("Vai trò không hợp lệ!", "danger")
        return redirect(url_for("login"))

    # Nếu POST: xử lý đổi mật khẩu
    if request.method == "POST":
        mat_khau_cu = request.form.get("mat_khau_cu")
        mat_khau_moi = request.form.get("mat_khau_moi")
        nhap_lai = request.form.get("nhap_lai")

        # Kiểm tra mật khẩu cũ
        if not check_password_hash(tai_khoan.MatKhau, mat_khau_cu):
            flash("❌ Mật khẩu cũ không đúng!", "danger")
            return redirect(url_for("doi_mat_khau"))

        # Kiểm tra mật khẩu mới
        if mat_khau_moi != nhap_lai:
            flash("❌ Mật khẩu mới và xác nhận không trùng khớp!", "danger")
            return redirect(url_for("doi_mat_khau"))

        # Lưu mật khẩu mới
        tai_khoan.MatKhau = generate_password_hash(mat_khau_moi)
        db.session.commit()

        flash("✅ Đổi mật khẩu thành công!", "success")

        # Điều hướng quay lại đúng trang thông tin
        if role == "khachhang":
            return redirect(url_for("thong_tin_tai_khoan"))
        else:
            return redirect(url_for("thong_tin_nhan_vien"))

    return render_template("doi_mat_khau.html")

from flask import session, flash, redirect, url_for, render_template
from decimal import Decimal

@app.route("/lich-su-dat-phong")
def lich_su_dat_phong():
    # --- Kiểm tra đăng nhập khách hàng ---
    if "user" not in session or session.get("role", "").lower() != "khachhang":
        flash("Vui lòng đăng nhập bằng tài khoản khách hàng để xem lịch sử đặt phòng.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    khach_hang = KhachHang.query.get(user_id)
    if not khach_hang:
        flash("Không tìm thấy thông tin khách hàng!", "danger")
        return redirect(url_for("login"))

    # --- Lấy danh sách đặt phòng theo khách hàng ---
    dat_phongs = DatPhong.query.filter_by(MaKhachHang=user_id).order_by(DatPhong.ThoiGianBatDau.desc()).all()

    return render_template("lich_su_dat_phong.html", dat_phongs=dat_phongs)

@app.route("/huy-dat-phong/<int:ma_dat_phong>", methods=["POST"])
def huy_dat_phong(ma_dat_phong):
    if "user" not in session or session.get("role", "").lower() != "khachhang":
        flash("Vui lòng đăng nhập để thực hiện thao tác này.", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    dp = DatPhong.query.get(ma_dat_phong)

    if not dp or dp.MaKhachHang != user_id:
        flash("Không tìm thấy đặt phòng này!", "danger")
        return redirect(url_for("lich_su_dat_phong"))

    if dp.TrangThai != "CHO_XAC_NHAN":
        flash("Chỉ có thể hủy các đặt phòng đang chờ xác nhận.", "warning")
        return redirect(url_for("lich_su_dat_phong"))

    # Cập nhật trạng thái hủy
    dp.TrangThai = "HUY"
    db.session.commit()
    flash("✅ Hủy đặt phòng thành công.", "success")
    return redirect(url_for("lich_su_dat_phong"))

@app.route("/khach-hang/them/<int:ma_phong>", methods=["GET", "POST"])
def them_khach_hang(ma_phong):
    if request.method == "POST":
        ho_ten = request.form.get("HoTen", "").strip()
        so_dt = request.form.get("SoDienThoai", "").strip()
        email = request.form.get("Email", "").strip()

        # Kiểm tra các trường bắt buộc
        if not ho_ten or not so_dt or not email:
            flash("Vui lòng điền đầy đủ các trường dữ liệu.", "danger")
            return redirect(url_for("them_khach_hang", ma_phong=ma_phong))

        # 1. Tìm khách đã có
        kh = KhachHang.query.filter(
            (KhachHang.SoDienThoai == so_dt) | (KhachHang.Email == email)
        ).first()

        if kh:
            session["khachhang_dat_phong"] = kh.MaKhachHang
            flash("Khách hàng đã tồn tại, chuyển đến đặt phòng!", "success")
            return redirect(url_for("dat_phong", ma_phong=ma_phong))

        # 2. Chưa có -> tạo mới
        kh = KhachHang(HoTen=ho_ten, SoDienThoai=so_dt, Email=email)
        db.session.add(kh)
        db.session.commit()

        session["khachhang_dat_phong"] = kh.MaKhachHang
        flash("Thêm khách hàng thành công! Mời đặt phòng.", "success")
        return redirect(url_for("dat_phong", ma_phong=ma_phong))

    return render_template("them_khach_hang.html", ma_phong=ma_phong)










