PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS departments (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 email TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 full_name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('Employee','Organizer','Admin')),
 department_id INTEGER NOT NULL,
 is_active INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(department_id) REFERENCES departments(id)
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 start_time TEXT NOT NULL,
 location TEXT NOT NULL,
 department_id INTEGER NOT NULL,
 organizer_id INTEGER NOT NULL,
 max_participants INTEGER NOT NULL CHECK(max_participants > 0),
 registration_deadline TEXT NOT NULL,
 target_department_id INTEGER,
 status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','Cancelled')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(department_id) REFERENCES departments(id),
 FOREIGN KEY(organizer_id) REFERENCES users(id),
 FOREIGN KEY(target_department_id) REFERENCES departments(id)
);
CREATE TABLE IF NOT EXISTS registrations (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 event_id INTEGER NOT NULL,
 user_id INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'Registered' CHECK(status IN ('Registered','Confirmed','Attended','Cancelled')),
 created_at TEXT NOT NULL,
 checked_in_at TEXT,
 UNIQUE(event_id,user_id),
 FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
