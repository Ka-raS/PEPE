from django.db import migrations

class Migration(migrations.Migration):

    initial = True

    dependencies = []
    
    operations = [
        migrations.RunSQL("""
            CREATE TABLE majors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );
            INSERT INTO majors (name)
            VALUES
                ('Công nghệ Thông tin'),
                ('Kỹ thuật Điện tử'),
                ('Công nghệ Đa phương tiện'),
                ('Kỹ thuật Điện tử Viễn thông'),
                ('Truyền thông Đa phương tiện'),
                ('Marketing'),
                ('Thuơng mại Điện tử'),
                ('Logistics và Quản lý Chuỗi cung ứng'),
                ('Công nghệ Tài chính'),
                ('Công nghệ Điện tử');
        """),

        migrations.RunSQL("""
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );
            INSERT INTO departments (name)
            VALUES
                ('Công nghệ Thông tin'),
                ('Điện Điện tử'),
                ('Đa phương tiện'),
                ('Viễn thông'),
                ('Quản trị Kinh doanh'),
                ('Tài chính Kế toán');
        """),

        migrations.RunSQL("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                user_type TEXT NOT NULL CHECK(user_type IN ('student', 'teacher')),
                
                first_name TEXT,
                last_name TEXT,
                avatar_path TEXT
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE students (
                student_id TEXT UNIQUE,
                enrollment_year INTEGER,
                          
                id INTEGER PRIMARY KEY,
                major_id INTEGER,
                FOREIGN KEY (id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (major_id) REFERENCES majors(id)
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE teachers (
                id INTEGER PRIMARY KEY,
                teacher_id TEXT UNIQUE,
                title TEXT,
                department_id INTEGER,
                FOREIGN KEY (id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (department_id) REFERENCES departments(id)
            );
        """),
    ]