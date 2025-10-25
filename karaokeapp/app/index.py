from flask import render_template, request, redirect, url_for, flash, session
from app import app
from app import dao

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = dao.check_login(username, password)
        if user:
            session["user"] = user.TenDangNhap
            session["role"] = user.VaiTro
            flash(f"Chào mừng {user.TenDangNhap} ({user.VaiTro}) đăng nhập thành công!", "success")
            return redirect(url_for("home"))
        else:
            flash("❌ Sai tên đăng nhập hoặc mật khẩu, hoặc tài khoản bị khóa!", "danger")
    return render_template("index.html")

@app.route("/home")
def home():
    if "user" not in session:
        flash("⚠️ Vui lòng đăng nhập trước!", "warning")
        return redirect(url_for("login"))
    return f"""
        <h2>Xin chào {session['user']} ({session['role']})!</h2>
        <p>Bạn đã đăng nhập thành công 🎉</p>
        <a href='/logout'>Đăng xuất</a>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/register")
def register():
    return "<h3>Trang đăng ký đang được phát triển...</h3>"
