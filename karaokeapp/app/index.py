from flask import render_template, request, redirect, url_for, flash, session
from app import app, dao


# --- Trang chủ ---
@app.route("/")
def index():
    from app import dao
    rooms = dao.get_all_phong_hat()
    return render_template("home.html", rooms=rooms)


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

            flash(f"🎉 Chào mừng {user.TenDangNhap} ({user.VaiTro}) đăng nhập thành công!", "success")

            # 🔹 Phân quyền điều hướng
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

    # GET → hiển thị form đăng nhập
    return render_template("index.html")


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


# --- Đăng xuất ---
@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Bạn đã đăng xuất thành công!", "info")
    return redirect(url_for("index"))


# --- Trang đăng ký (tạm thời) ---
@app.route("/register")
def register():
    return "<h3>Trang đăng ký đang được phát triển...</h3>"

@app.route("/dat-phong/<int:ma_phong>")
def dat_phong(ma_phong):
    if "user" not in session or session["role"].lower() != "khachhang":
        flash("⚠️ Bạn cần đăng nhập bằng tài khoản khách hàng để đặt phòng!", "warning")
        return redirect(url_for("login"))

    from app.models import PhongHat
    room = PhongHat.query.get(ma_phong)
    if not room:
        flash("❌ Không tìm thấy phòng!", "danger")
        return redirect(url_for("index"))

    return render_template("dat_phong.html", room=room)

@app.route("/phong/<int:ma_phong>")
def chi_tiet_phong(ma_phong):
    from app.models import PhongHat
    room = PhongHat.query.get(ma_phong)

    if not room:
        return "Không tìm thấy phòng", 404

    return render_template("chi_tiet_phong.html", room=room)

