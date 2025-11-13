from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session
from app import app, dao, db
from app.models import PhongHat, ChiTietDatDichVu, HoaDon, DatPhong, DichVu, KhachHang, TaiKhoan, NhanVien
from werkzeug.security import generate_password_hash
from decimal import Decimal


@app.route("/")
def index():
    rooms_vip = PhongHat.query.filter_by(LoaiPhong='VIP').all()
    rooms_thuong = PhongHat.query.filter_by(LoaiPhong='THUONG').all()
    return render_template("home.html",
                           rooms_vip=rooms_vip,
                           rooms_thuong=rooms_thuong)

# --- Trang đăng nhập ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = dao.check_login(username, password)

        if user:
            session["user"] = user.TenDangNhap
            session["role"] = user.VaiTro

            # Lấy MaKhachHang từ user.khach_hang
            if user.khach_hang:  # kiểm tra có tồn tại KhachHang không
                session["user_id"] = user.khach_hang.MaKhachHang
            else:
                session["user_id"] = None  # hoặc xử lý báo lỗi nếu chưa có KhachHang

            flash(f"🎉 Chào mừng {user.TenDangNhap} ({user.VaiTro}) đăng nhập thành công!", "success")

            # Phân quyền điều hướng
            if user.VaiTro.lower() == "khachhang":
                return redirect(url_for("index"))
            elif user.VaiTro.lower() == "nhanvien":
                return redirect(url_for("staff_dashboard"))
            elif user.VaiTro.lower() == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                flash("❌ Không xác định được vai trò người dùng!", "danger")
                return redirect(url_for("login"))
        else:
            flash("❌ Sai tên đăng nhập hoặc mật khẩu, hoặc tài khoản bị khóa!", "danger")

    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hoten = request.form.get("hoten")
        sdt = request.form.get("sdt")
        email = request.form.get("email")

        # ✅ Kiểm tra tài khoản đã tồn tại chưa
        exist = TaiKhoan.query.filter_by(TenDangNhap=username).first()
        if exist:
            flash("❌ Tên đăng nhập đã tồn tại!", "danger")
            return redirect(url_for("register"))

        # ✅ Băm mật khẩu trước khi lưu (quan trọng)
        hashed_password = generate_password_hash(password)

        tai_khoan = TaiKhoan(
            TenDangNhap=username,
            MatKhau=hashed_password,  # ✅ Lưu password dạng hash
            VaiTro="KHACHHANG",
            TrangThai=True
        )

        db.session.add(tai_khoan)
        db.session.commit()  # Để có MaTaiKhoan trước khi tạo KhachHang

        # ✅ Tạo khách hàng liên kết với tài khoản
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


# --- Trang sau khi đăng nhập (dành chung nếu cần) ---
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("⚠️ Vui lòng đăng nhập trước!", "warning")
        return redirect(url_for("login"))

    return f"""
        <h2>Xin chào {session['user']} ({session['role']})!</h2>
        <p>Bạn đã đăng nhập thành công 🎉</p>
        <a href='/logout'>Đăng xuất</a>
    """

@app.route("/phong/<int:ma_phong>")
def chi_tiet_phong(ma_phong):
    from app.models import PhongHat
    room = PhongHat.query.get(ma_phong)

    if not room:
        return "Không tìm thấy phòng", 404

    return render_template("chi_tiet_phong.html", room=room)

@app.route("/dat-phong/<int:ma_phong>", methods=["GET", "POST"])
def dat_phong(ma_phong):
    # Kiểm tra đăng nhập và vai trò
    if "user" not in session or session["role"].lower() != "khachhang":
        flash("Vui lòng đăng nhập bằng tài khoản khách hàng để đặt phòng.", "warning")
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

            admin_nv = NhanVien.query.filter_by(ChucVu='ADMIN').first()
            ma_nhan_vien = admin_nv.MaNhanVien if admin_nv else None

            hoa_don = HoaDon(
                MaDatPhong=dp.MaDatPhong,
                TienPhong=Decimal(room.GiaGio) * so_gio,
                TienDichVu=tien_dich_vu,
                PhuongThucThanhToan='TIEN_MAT',
                Nguon='ONLINE',
                MaNhanVien=ma_nhan_vien
            )
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


