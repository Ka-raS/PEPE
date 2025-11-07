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
        """),

        migrations.RunSQL("""
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );
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
                coins INTEGER DEFAULT 0,
                          
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