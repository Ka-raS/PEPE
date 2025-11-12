from django.db import connection


def user_count():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]


# PRESENT
def one_user(user_id=None, username=None, email=None):
    query_conditions = []
    if user_id is not None:
        query_conditions.append("id = %s")
    if username is not None:
        query_conditions.append("username = %s")
    if email is not None:
        query_conditions.append("email = %s")

    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT id, username, password, email, first_name, last_name, avatar_path
            FROM users 
            WHERE {' OR '.join(query_conditions)}
        """, [i for i in (user_id, username, email) if i is not None])

        row = cursor.fetchone()
        return {
            'id': row[0],
            'username': row[1],
            'password': row[2],
            'email': row[3],
            'first_name': row[4],
            'last_name': row[5],
            'avatar_path': row[6]
        } if row else None

def one_student(user_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT s.major_id, m.name AS major_name, s.enrollment_year, s.student_code
            FROM students s
            LEFT JOIN majors m ON s.major_id = m.id
            WHERE s.id = %s
        """, [user_id])
        row = cursor.fetchone()
        return {
            'major_id': row[0],
            'major_name': row[1],
            'enrollment_year': row[2],
            'student_code': row[3]
        } if row else None

def one_teacher(user_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT t.title, t.department_id, d.name AS department_name, t.degree, t.teacher_code
            FROM teachers t
            LEFT JOIN departments d ON t.department_id = d.id
            WHERE t.id = %s
        """, [user_id])
        row = cursor.fetchone()
        return {
            'title': row[0],
            'department_id': row[1],
            'department_name': row[2],
            'degree': row[3],
            'teacher_code': row[4]
        } if row else None

# PRESENT
def insert_user(username, email, password, first_name, last_name, user_type):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO users
                (username, email, password, first_name, last_name)
            VALUES (%s, %s, %s, %s, %s)
        """, [username, email, password, first_name, last_name])

        if user_type == 'student':
            cursor.execute("""
                INSERT INTO students (id) 
                VALUES (%s)
            """, [cursor.lastrowid])
        elif user_type == 'teacher':
            cursor.execute("""
                INSERT INTO teachers (id) 
                VALUES (%s)
            """, [cursor.lastrowid])

def update_user_name(first_name, last_name, user_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE users 
            SET first_name = %s, last_name = %s 
            WHERE id = %s
        """, [first_name, last_name, user_id])

def update_user_avatar(avatar_path, user_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE users
            SET avatar_path = %s 
            WHERE id = %s
        """, [avatar_path, user_id])        

def update_student(user_id, major_id, enrollment_year, student_code):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM students WHERE id = %s", [user_id])
        
        if cursor.fetchone():
            cursor.execute("""
                UPDATE students 
                SET major_id = %s, enrollment_year = %s, student_code = %s
                WHERE id = %s
            """, [major_id, enrollment_year, student_code, user_id])
        else:
            cursor.execute("""
                INSERT INTO students (id, student_code, enrollment_year, major_id) 
                VALUES (%s, %s, %s, %s)
            """, [user_id, student_code, major_id, enrollment_year])

def update_teacher(user_id, title, teacher_code, degree, department_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM teachers WHERE id = %s", [user_id])

        if cursor.fetchone():
            cursor.execute("""
                UPDATE teachers 
                SET title = %s, teacher_code = %s, degree = %s, department_id = %s
                WHERE id = %s
            """, [title, teacher_code, degree, department_id, user_id])
        else:
            cursor.execute("""
                INSERT INTO teachers (id, teacher_code, title, degree, department_id) VALUES (%s, %s, %s, %s, %s)
            """, [user_id, teacher_code, title, degree, department_id])




def all_subject():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM subjects")
        return [
            {
                'id': row[0],
                'name': row[1],
                'description': row[2]
            }
            for row in cursor.fetchall()
        ]
    
def one_subject(subject_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM subjects WHERE id = %s", [subject_id])
        row = cursor.fetchone()
        return {
            'id': row[0],
            'name': row[1],
            'description': row[2]
        } if row else None
    
def all_major():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM majors")
        return [
            {
                'id': row[0],
                'name': row[1],
                'department_id': row[2]
            }
            for row in cursor.fetchall()
        ]
        
def all_department():
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM departments ORDER BY name")
        return [
            {
                'id': row[0],
                'name': row[1]
            }
            for row in cursor.fetchall()
        ]

def user_submission_count(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM submissions WHERE author_id = %s", [user_id])
        return cursor.fetchone()[0] or 0
    
def user_post_count(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM posts WHERE author_id = %s", [user_id])
        return cursor.fetchone()[0] or 0
    
def user_test_count(user_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM tests WHERE author_id = %s", [user_id])
        return cursor.fetchone()[0] or 0


def user_recent_submissions(user_id, count):
    count = max(count, -1)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT t.title, s.created_at
            FROM submissions s
            JOIN tests t ON s.test_id = t.id
            WHERE s.author_id = %s
            ORDER BY s.created_at DESC
            LIMIT %s
        """, [user_id, count])
        return [
            {
                'title': row[0],
                'created_at': row[1]
            }
            for row in cursor.fetchall()
        ]
    
# PRESENT
def user_recent_posts(user_id, count):
    count = max(count, -1)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT title, created_at 
            FROM posts
            WHERE author_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, [user_id, count])
        return [    
            {
                'title': row[0],
                'created_at': row[1]
            }
            for row in cursor.fetchall()
        ]
    
def user_recent_tests(user_id, count):
    count = max(count, -1)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT title, created_at 
            FROM tests
            WHERE author_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, [user_id, count])
        return [
            {
                'title': row[0],
                'created_at': row[1]
            }
            for row in cursor.fetchall()
        ]
    