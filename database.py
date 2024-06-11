import sqlite3

def init_db():
    conn = sqlite3.connect('ege_scores.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            first_name TEXT,
            last_name TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            score INTEGER,
            FOREIGN KEY (user_id) REFERENCES students (user_id)
        )
    ''')
    conn.commit()
    conn.close()

def register_student(user_id, first_name, last_name):
    conn = sqlite3.connect('ege_scores.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM students WHERE user_id = ?', (user_id,))
        existing_user = cursor.fetchone()
        if existing_user:
            pass
        else:
            cursor.execute('''
                INSERT INTO students (user_id, first_name, last_name)
                VALUES (?, ?, ?)
            ''', (user_id, first_name, last_name))
            conn.commit()
    finally:
        conn.close()

def enter_score(user_id, subject, score):
    conn = sqlite3.connect('ege_scores.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO scores (user_id, subject, score)
        VALUES (?, ?, ?)
    ''', (user_id, subject, score))
    conn.commit()
    conn.close()

def get_scores(user_id):
    conn = sqlite3.connect('ege_scores.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT subject, score FROM scores WHERE user_id = ?
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def is_registered(user_id):
    conn = sqlite3.connect('ege_scores.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM students WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None
