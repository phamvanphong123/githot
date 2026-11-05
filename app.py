import os, secrets
from datetime import datetime
from functools import wraps
from flask import Flask, abort, g, redirect, render_template, request, session, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
import db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "doi-khoa-bi-mat-khi-trien-khai")
app.config["DATABASE"] = os.environ.get("DATABASE", os.path.join(app.root_path, "xyz_events.db"))
app.teardown_appcontext(db.close_db)
ROLE_HOME = {"Employee":"employee_home", "Organizer":"organizer_home", "Admin":"admin_home"}
ROLE_LABEL = {"Employee":"Nhân viên", "Organizer":"Người tổ chức", "Admin":"Quản trị viên"}
STATUS_LABEL = {"Open":"Đang mở", "Cancelled":"Đã hủy", "Registered":"Đã đăng ký", "Confirmed":"Đã xác nhận", "Attended":"Đã tham gia", "Cancelled":"Đã hủy"}

@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        g.user = db.query_one("SELECT u.*, d.name AS dept FROM users u JOIN departments d ON d.id=u.department_id WHERE u.id=?", (uid,))
        if g.user is None or not g.user["is_active"]:
            session.clear()
            g.user = None
    if request.method == "POST":
        token = request.form.get("csrf", "")
        if not token or not secrets.compare_digest(token, session.get("csrf", "")):
            abort(400)

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]
app.jinja_env.globals["csrf_token"] = csrf_token
app.jinja_env.globals["ROLE_LABEL"] = ROLE_LABEL
app.jinja_env.globals["STATUS_LABEL"] = STATUS_LABEL

@app.template_filter("vn_time")
def vn_time(value):
    try: return datetime.strptime(value, db.FMT).strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError): return value or ""

def role_required(*roles):
    def deco(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if g.user is None: return redirect(url_for("login"))
            if g.user["role"] not in roles: abort(403)
            return view(*args, **kwargs)
        return wrapper
    return deco

def current_status(event, now=None):
    now = now or datetime.now()
    if event["status"] == "Cancelled": return "Cancelled"
    if datetime.strptime(event["start_time"], db.FMT) <= now: return "Ended"
    count = event["registered"] if "registered" in event.keys() else 0
    if count >= event["max_participants"]: return "Full"
    if datetime.strptime(event["registration_deadline"], db.FMT) < now: return "Closed"
    return "Open"

def event_query(where="", args=()):
    sql = """SELECT e.*, d.name AS dept, u.full_name AS organizer_name,
      (SELECT COUNT(*) FROM registrations r WHERE r.event_id=e.id AND r.status IN ('Registered','Confirmed','Attended')) AS registered
      FROM events e JOIN departments d ON d.id=e.department_id JOIN users u ON u.id=e.organizer_id """
    if where: sql += " WHERE " + where
    sql += " ORDER BY e.start_time"
    return [dict(r) for r in db.query(sql, args)]

@app.route("/")
def index():
    return redirect(url_for(ROLE_HOME[g.user["role"]])) if g.user else redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if g.user: return redirect(url_for(ROLE_HOME[g.user["role"]]))
    error, email = None, ""
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        user = db.query_one("SELECT * FROM users WHERE email=?", (email,)) if email and password else None
        if not email or not password: error = "Vui lòng nhập email và mật khẩu."
        elif not user or not check_password_hash(user["password_hash"], password): error = "Email hoặc mật khẩu không chính xác."
        elif not user["is_active"]: error = "Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên."
        else:
            session.clear(); session["uid"] = user["id"]
            return redirect(url_for(ROLE_HOME[user["role"]]))
    return render_template("login.html", error=error, email=email)

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/employee")
@role_required("Employee")
def employee_home():
    q = request.args.get("q","").strip()[:100]
    date_from, date_to = request.args.get("from",""), request.args.get("to","")
    dept, status = request.args.get("dept",""), request.args.get("status","")
    errors, conditions, args = [], [], []
    if q:
        conditions.append("e.name LIKE ?"); args.append("%" + q.replace("%","\\%").replace("_","\\_") + "%")
    try:
        if date_from: datetime.strptime(date_from,"%Y-%m-%d")
        if date_to: datetime.strptime(date_to,"%Y-%m-%d")
        if date_from and date_to and date_from > date_to: raise ValueError
        if date_from: conditions.append("e.start_time >= ?"); args.append(date_from+" 00:00")
        if date_to: conditions.append("e.start_time <= ?"); args.append(date_to+" 23:59")
    except ValueError:
        errors.append("Khoảng ngày không hợp lệ; vui lòng kiểm tra lại.")
        conditions, args = [], []
    if dept.isdigit(): conditions.append("e.department_id=?"); args.append(int(dept))
    events = event_query(" AND ".join(conditions), args)
    for ev in events:
        ev["state"] = current_status(ev)
        ev["state_label"] = {"Open":"Đang mở","Full":"Hết chỗ","Closed":"Đã đóng đăng ký","Ended":"Đã kết thúc","Cancelled":"Đã hủy"}[ev["state"]]
    if status: events = [e for e in events if e["state"] == status]
    mine = {r["event_id"]:r["status"] for r in db.query("SELECT event_id,status FROM registrations WHERE user_id=? AND status!='Cancelled'",(g.user["id"],))}
    return render_template("events.html", events=events, errors=errors, departments=db.query("SELECT * FROM departments ORDER BY name"),
                           f={"q":q,"from":date_from,"to":date_to,"dept":dept,"status":status}, mine=mine)

@app.route("/event/<int:event_id>")
@role_required("Employee","Organizer","Admin")
def event_detail(event_id):
    rows = event_query("e.id=?", (event_id,))
    if not rows: abort(404)
    ev=rows[0]; ev["state"]=current_status(ev)
    registration = db.query_one("SELECT * FROM registrations WHERE event_id=? AND user_id=?", (event_id,g.user["id"]))
    return render_template("event_detail.html", event=ev, registration=registration)

@app.post("/event/<int:event_id>/register")
@role_required("Employee")
def register_event(event_id):
    rows=event_query("e.id=?", (event_id,))
    if not rows: abort(404)
    ev=rows[0]; now=datetime.now()
    if ev["status"]=="Cancelled": flash("Sự kiện đã bị hủy.","error")
    elif ev["target_department_id"] and ev["target_department_id"] != g.user["department_id"]: flash("Sự kiện chỉ dành cho phòng ban được chỉ định.","error")
    elif datetime.strptime(ev["registration_deadline"],db.FMT) < now: flash("Đã quá hạn đăng ký.","error")
    elif datetime.strptime(ev["start_time"],db.FMT) <= now: flash("Sự kiện đã bắt đầu hoặc kết thúc.","error")
    elif ev["registered"] >= ev["max_participants"]: flash("Sự kiện đã hết chỗ.","error")
    else:
        old=db.query_one("SELECT * FROM registrations WHERE event_id=? AND user_id=?", (event_id,g.user["id"]))
        if old and old["status"]!="Cancelled": flash("Bạn đã đăng ký sự kiện này rồi.","error")
        elif old:
            db.execute("UPDATE registrations SET status='Registered',created_at=?,checked_in_at=NULL WHERE id=?", (now.strftime(db.FMT),old["id"]))
            flash("Đăng ký tham gia thành công.")
        else:
            db.execute("INSERT INTO registrations(event_id,user_id,status,created_at) VALUES (?,?,?,?)",(event_id,g.user["id"],"Registered",now.strftime(db.FMT)))
            flash("Đăng ký tham gia thành công.")
    return redirect(url_for("event_detail",event_id=event_id))

@app.post("/event/<int:event_id>/cancel-registration")
@role_required("Employee")
def cancel_registration(event_id):
    reg=db.query_one("SELECT * FROM registrations WHERE event_id=? AND user_id=?",(event_id,g.user["id"]))
    if not reg or reg["status"]=="Cancelled": flash("Không tìm thấy đăng ký đang hoạt động.","error")
    else:
        ev=db.query_one("SELECT registration_deadline,start_time FROM events WHERE id=?",(event_id,))
        if datetime.now() > datetime.strptime(ev["registration_deadline"],db.FMT): flash("Đã quá hạn hủy đăng ký.","error")
        else:
            db.execute("UPDATE registrations SET status='Cancelled' WHERE id=?",(reg["id"],)); flash("Đã hủy đăng ký.")
    return redirect(url_for("my_events"))

@app.route("/my-events")
@role_required("Employee")
def my_events():
    rows=db.query("""SELECT e.*, d.name AS dept, r.status AS registration_status, r.created_at,
      (SELECT COUNT(*) FROM registrations x WHERE x.event_id=e.id AND x.status IN ('Registered','Confirmed','Attended')) AS registered
      FROM registrations r JOIN events e ON e.id=r.event_id JOIN departments d ON d.id=e.department_id
      WHERE r.user_id=? AND r.status!='Cancelled' ORDER BY e.start_time""",(g.user["id"],))
    return render_template("my_events.html",events=rows)

@app.route("/organizer")
@role_required("Organizer","Admin")
def organizer_home():
    return redirect(url_for("manage_events"))

@app.route("/manage/events")
@role_required("Organizer","Admin")
def manage_events():
    if g.user["role"]=="Admin": events=event_query()
    else: events=event_query("e.organizer_id=?",(g.user["id"],))
    for ev in events: ev["state"]=current_status(ev)
    return render_template("manage_events.html",events=events)

def parse_event_form(form):
    name=form.get("name","").strip()
    description=form.get("description","").strip()
    location=form.get("location","").strip()
    start=form.get("start_time","").strip()
    deadline=form.get("registration_deadline","").strip()
    dept=form.get("department_id","")
    maximum=form.get("max_participants","")
    target=form.get("target_department_id","")
    errors=[]
    if not name: errors.append("Tên sự kiện là bắt buộc.")
    if not location: errors.append("Địa điểm là bắt buộc.")
    try:
        datetime.strptime(start,db.FMT)
    except ValueError: errors.append("Thời gian bắt đầu không hợp lệ.")
    try:
        datetime.strptime(deadline,db.FMT)
    except ValueError: errors.append("Hạn đăng ký không hợp lệ.")
    try:
        maximum=int(maximum)
        if maximum<=0: raise ValueError
    except ValueError:
        maximum=0; errors.append("Số lượng tối đa phải là số nguyên dương.")
    if start and deadline:
        try:
            if datetime.strptime(deadline,db.FMT) > datetime.strptime(start,db.FMT):
                errors.append("Hạn đăng ký không được sau thời gian bắt đầu.")
        except ValueError: pass
    department_exists = bool(dept.isdigit() and db.query_one("SELECT id FROM departments WHERE id=?", (int(dept),)))
    if not department_exists:
        errors.append("Vui lòng chọn phòng ban tổ chức.")
    target_id=int(target) if target.isdigit() else None
    return {"name":name,"description":description,"location":location,"start_time":start,"registration_deadline":deadline,
            "department_id":int(dept) if dept.isdigit() else 0,"max_participants":maximum,"target_department_id":target_id}, errors

@app.route("/manage/events/new", methods=["GET","POST"])
@role_required("Organizer","Admin")
def create_event():
    if request.method=="POST":
        data,errors=parse_event_form(request.form)
        if not errors:
            data["organizer_id"]=g.user["id"]
            db.execute("""INSERT INTO events(name,description,start_time,location,department_id,organizer_id,max_participants,registration_deadline,target_department_id,status)
              VALUES (:name,:description,:start_time,:location,:department_id,:organizer_id,:max_participants,:registration_deadline,:target_department_id,'Open')""",data)
            flash("Đã tạo sự kiện."); return redirect(url_for("manage_events"))
        for error in errors: flash(error,"error")
    return render_template("event_form.html",event=None,departments=db.query("SELECT * FROM departments ORDER BY name"))

def can_manage_event(event_id):
    ev=db.query_one("SELECT * FROM events WHERE id=?",(event_id,))
    if not ev: abort(404)
    if g.user["role"]!="Admin" and ev["organizer_id"]!=g.user["id"]: abort(403)
    return ev

@app.route("/manage/events/<int:event_id>/edit", methods=["GET","POST"])
@role_required("Organizer","Admin")
def edit_event(event_id):
    ev=can_manage_event(event_id)
    if request.method=="POST":
        data,errors=parse_event_form(request.form)
        count=db.query_one("SELECT COUNT(*) n FROM registrations WHERE event_id=? AND status IN ('Registered','Confirmed','Attended')",(event_id,))["n"]
        if data["max_participants"] < count: errors.append("Số lượng tối đa không thể nhỏ hơn số người đã đăng ký.")
        if not errors:
            data["id"]=event_id
            db.execute("""UPDATE events SET name=:name,description=:description,start_time=:start_time,location=:location,
             department_id=:department_id,max_participants=:max_participants,registration_deadline=:registration_deadline,
             target_department_id=:target_department_id WHERE id=:id""",data)
            flash("Đã cập nhật sự kiện."); return redirect(url_for("manage_events"))
        for error in errors: flash(error,"error")
    return render_template("event_form.html",event=ev,departments=db.query("SELECT * FROM departments ORDER BY name"))

@app.post("/manage/events/<int:event_id>/cancel")
@role_required("Organizer","Admin")
def cancel_event(event_id):
    ev=can_manage_event(event_id)
    db.execute("UPDATE events SET status='Cancelled' WHERE id=?",(event_id,))
    flash("Đã hủy sự kiện.")
    return redirect(url_for("manage_events"))

@app.route("/manage/events/<int:event_id>/participants")
@role_required("Organizer","Admin")
def participants(event_id):
    ev=can_manage_event(event_id)
    rows=db.query("""SELECT r.id AS registration_id,r.status,r.created_at,r.checked_in_at,u.full_name,u.email,d.name AS dept
       FROM registrations r JOIN users u ON u.id=r.user_id JOIN departments d ON d.id=u.department_id
       WHERE r.event_id=? AND r.status!='Cancelled' ORDER BY u.full_name""",(event_id,))
    return render_template("participants.html",event=ev,participants=rows)

@app.post("/manage/registrations/<int:registration_id>/status")
@role_required("Organizer","Admin")
def update_registration(registration_id):
    row=db.query_one("SELECT event_id FROM registrations WHERE id=?",(registration_id,))
    if not row: abort(404)
    can_manage_event(row["event_id"])
    status=request.form.get("status")
    if status not in ("Registered","Confirmed","Attended"): abort(400)
    checked=datetime.now().strftime(db.FMT) if status=="Attended" else None
    db.execute("UPDATE registrations SET status=?,checked_in_at=? WHERE id=?",(status,checked,registration_id))
    flash("Đã cập nhật trạng thái người tham gia.")
    return redirect(url_for("participants",event_id=row["event_id"]))

@app.route("/organizer/dashboard")
@role_required("Organizer","Admin")
def dashboard():
    where="" if g.user["role"]=="Admin" else " WHERE organizer_id=?"
    args=() if g.user["role"]=="Admin" else (g.user["id"],)
    stats=db.query("SELECT COUNT(*) total, SUM(CASE WHEN status='Open' THEN 1 ELSE 0 END) open_count FROM events"+where,args)[0]
    regwhere="" if g.user["role"]=="Admin" else " JOIN events e ON e.id=r.event_id WHERE e.organizer_id=?"
    regargs=() if g.user["role"]=="Admin" else (g.user["id"],)
    regs=db.query("SELECT COUNT(*) total FROM registrations r"+regwhere+" AND r.status!='Cancelled'" if g.user["role"]!="Admin" else "SELECT COUNT(*) total FROM registrations WHERE status!='Cancelled'",regargs)[0]["total"]
    attendees=db.query("SELECT COUNT(*) total FROM registrations r"+regwhere+" AND r.status='Attended'" if g.user["role"]!="Admin" else "SELECT COUNT(*) total FROM registrations WHERE status='Attended'",regargs)[0]["total"]
    rate=round(attendees/regs*100,1) if regs else 0
    return render_template("dashboard.html",stats=stats,regs=regs,attendees=attendees,rate=rate)

@app.route("/admin")
@role_required("Admin")
def admin_home():
    return redirect(url_for("admin_users"))

@app.route("/admin/users", methods=["GET","POST"])
@role_required("Admin")
def admin_users():
    if request.method=="POST":
        uid=request.form.get("user_id","")
        if not uid.isdigit(): abort(400)
        user=db.query_one("SELECT * FROM users WHERE id=?",(int(uid),))
        if not user: abort(404)
        if user["id"]==g.user["id"]: flash("Không thể khóa chính tài khoản đang sử dụng.","error")
        else:
            db.execute("UPDATE users SET is_active=? WHERE id=?",(0 if user["is_active"] else 1,user["id"]))
            flash("Đã cập nhật trạng thái tài khoản.")
        return redirect(url_for("admin_users"))
    users=db.query("SELECT u.*,d.name AS dept FROM users u JOIN departments d ON d.id=u.department_id ORDER BY u.role,u.full_name")
    return render_template("admin_users.html",users=users)

@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
def http_error(err):
    msg={400:"Yêu cầu không hợp lệ. Vui lòng tải lại trang.",403:"Bạn không có quyền truy cập chức năng này.",404:"Không tìm thấy trang bạn yêu cầu."}[err.code]
    return render_template("error.html",code=err.code,message=msg),err.code

db.ensure_db(app.config["DATABASE"])
if __name__=="__main__":
    app.run(debug=True)
