import os
import sqlite3
from datetime import datetime, timedelta
from flask import current_app, g
from werkzeug.security import generate_password_hash

HERE = os.path.dirname(os.path.abspath(__file__))
FMT = "%Y-%m-%d %H:%M"
DEMO_PASSWORD = "Employee@123"

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn:
        conn.close()

def query(sql, args=()):
    return get_db().execute(sql, args).fetchall()

def query_one(sql, args=()):
    return get_db().execute(sql, args).fetchone()

def execute(sql, args=()):
    conn = get_db()
    cur = conn.execute(sql, args)
    conn.commit()
    return cur

def init_db(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    with open(os.path.join(HERE, "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    seed(conn)
    conn.commit()
    conn.close()

def ensure_db(path):
    if not os.path.exists(path):
        init_db(path)

def seed(conn):
    depts = ["Phòng IT", "Phòng Nhân sự", "Phòng Tài chính", "Phòng Marketing"]
    for name in depts:
        conn.execute("INSERT INTO departments(name) VALUES (?)", (name,))
    pw = generate_password_hash(DEMO_PASSWORD)
    def user(email, name, role, dept):
        return conn.execute(
            "INSERT INTO users(email,password_hash,full_name,role,department_id) VALUES (?,?,?,?,?)",
            (email, pw, name, role, dept)).lastrowid
    user("admin@xyz.com", "Quản trị viên", "Admin", 1)
    org1 = user("organizer@xyz.com", "Lê Minh Tuấn", "Organizer", 1)
    org2 = user("organizer.hr@xyz.com", "Trần Thu Hà", "Organizer", 2)
    user("employee@xyz.com", "Nguyễn Văn An", "Employee", 1)
    staff = [("nv01@xyz.com","Phạm Quốc Bảo",1),("nv02@xyz.com","Võ Thanh Châu",2),
             ("nv03@xyz.com","Đặng Mỹ Dung",3),("nv04@xyz.com","Hoàng Gia Huy",4),
             ("nv05@xyz.com","Bùi Khánh Linh",2),("nv06@xyz.com","Ngô Đức Minh",3)]
    staff_ids = [user(email, name, "Employee", dept) for email,name,dept in staff]
    locked = user("locked@xyz.com", "Tài khoản bị khóa", "Employee", 1)
    conn.execute("UPDATE users SET is_active=0 WHERE id=?", (locked,))
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    def at(days, hour=9):
        return (now + timedelta(days=days)).replace(hour=hour).strftime(FMT)
    events = [
        ("Workshop AI","Giới thiệu ứng dụng AI trong công việc hằng ngày.",at(5),"Meeting Hall",1,org1,50,at(3,17),None,"Open",3),
        ("Khám sức khỏe định kỳ","Khám tổng quát cho toàn bộ nhân viên.",at(9,8),"Phòng y tế tầng 2",2,org2,20,at(7,17),None,"Open",2),
        ("Team building Đà Lạt","Chuyến đi gắn kết 2 ngày 1 đêm.",at(20,6),"Đà Lạt",2,org2,60,at(14,17),None,"Open",2),
        ("Đào tạo an toàn thông tin","Nhận diện email lừa đảo và bảo vệ tài khoản.",at(2,14),"Phòng họp A",1,org1,40,at(1,17),None,"Open",1),
        ("Hội thảo chuyển đổi số","Hoãn theo kế hoạch quý mới.",at(30,9),"Meeting Hall",1,org1,80,at(25,17),None,"Cancelled",0),
        ("Lớp quản lý ngân sách","Dành riêng cho Phòng Tài chính.",at(7,10),"Phòng họp C",3,org2,20,at(5,17),3,"Open",1),
    ]
    for ev in events:
        eid = conn.execute(
            "INSERT INTO events(name,description,start_time,location,department_id,organizer_id,max_participants,registration_deadline,target_department_id,status) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ev[:10]).lastrowid
        for uid in staff_ids[:ev[10]]:
            conn.execute("INSERT INTO registrations(event_id,user_id,status,created_at) VALUES (?,?,?,?)",
                         (eid,uid,"Registered",now.strftime(FMT)))
