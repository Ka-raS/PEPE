from django.db import migrations

class Migration(migrations.Migration):

    initial = True

    dependencies = []
    
    operations = [
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
                student_code TEXT UNIQUE,
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
                student_code TEXT UNIQUE,
                title TEXT,
                department_id INTEGER,
                FOREIGN KEY (id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (department_id) REFERENCES departments(id)
            );
        """),


        migrations.RunSQL("""
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE majors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department_id INTEGER NOT NULL,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE major_subjects (
                major_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                PRIMARY KEY (major_id, subject_id),
                FOREIGN KEY (major_id) REFERENCES majors(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
        """),


        migrations.RunSQL("""
            INSERT INTO departments (name)
            VALUES
                ('Công nghệ Thông tin'),
                ('Điện Điện tử'),
                ('Đa phương tiện'),
                ('Viễn thông'),
                ('Quản trị Kinh doanh'),
                ('Tài chính Kế toán');

            INSERT INTO majors (name, department_id)
            VALUES
                ('Công nghệ Thông tin', 1),
                ('Kỹ thuật Điện tử', 2),
                ('Công nghệ Đa phương tiện', 3),
                ('Kỹ thuật Điện tử Viễn thông', 4),
                ('Truyền thông Đa phương tiện', 3),
                ('Marketing', 5),
                ('Thương mại Điện tử', 5),
                ('Logistics và Quản lý Chuỗi cung ứng', 5),
                ('Công nghệ Tài chính', 6),
                ('Công nghệ Điện tử', 2);

            INSERT INTO subjects (name, description) 
            VALUES
                ('Lập trình C', 'Học các khái niệm lập trình cơ bản nhất thông qua ngôn ngữ C (biến, vòng lặp, hàm, con trỏ).'),
                ('Cấu trúc dữ liệu và giải thuật', 'Nghiên cứu cách tổ chức dữ liệu (mảng, danh sách, cây, đồ thị) và các phương pháp giải quyết bài toán hiệu quả.'),
                ('Lập trình hướng đối tượng', 'Học các nguyên lý lập trình hiện đại (Java/C#/C++) như lớp, đối tượng, kế thừa, đa hình.'),
                ('Cơ sở dữ liệu', 'Tìm hiểu về hệ quản trị cơ sở dữ liệu quan hệ (RDBMS), ngôn ngữ truy vấn SQL, và thiết kế cơ sở dữ liệu.'),
                ('Mạng máy tính', 'Khám phá các nguyên tắc và giao thức mạng, bao gồm mô hình OSI, TCP/IP, định tuyến và bảo mật mạng.'),
                ('Hệ điều hành', 'Nghiên cứu các khái niệm về hệ điều hành như quản lý tiến trình, bộ nhớ, hệ thống tập tin.'),
                ('Kiến trúc máy tính', 'Nghiên cứu cấu trúc và hoạt động của phần cứng máy tính (CPU, bộ nhớ, các thành phần khác).'),
                ('Cơ sở An toàn thông tin', 'Tìm hiểu về các nguyên tắc bảo mật, mã hóa, xác thực và các biện pháp bảo vệ hệ thống thông tin.'),
                ('Trí tuệ nhân tạo', 'Giới thiệu về các khái niệm và kỹ thuật trong trí tuệ nhân tạo, bao gồm học máy, xử lý ngôn ngữ tự nhiên.');

            -- Công nghệ Thông tin (major_id = 1)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (1, 1), -- Lập trình C
                (1, 2), -- Cấu trúc dữ liệu và giải thuật
                (1, 3), -- Lập trình hướng đối tượng
                (1, 4), -- Cơ sở dữ liệu
                (1, 5), -- Mạng máy tính
                (1, 6), -- Hệ điều hành
                (1, 7), -- Kiến trúc máy tính
                (1, 8), -- Cơ sở An toàn thông tin
                (1, 9); -- Trí tuệ nhân tạo

            -- Kỹ thuật Điện tử (major_id = 2)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (2, 1), -- Lập trình C
                (2, 7); -- Kiến trúc máy tính

            -- Công nghệ Đa phương tiện (major_id = 3)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (3, 1), -- Lập trình C
                (3, 3), -- Lập trình hướng đối tượng
                (3, 4); -- Cơ sở dữ liệu

            -- Kỹ thuật Điện tử Viễn thông (major_id = 4)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (4, 1), -- Lập trình C
                (4, 5), -- Mạng máy tính
                (4, 7); -- Kiến trúc máy tính

            -- Truyền thông Đa phương tiện (major_id = 5)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (5, 1), -- Lập trình C
                (5, 3), -- Lập trình hướng đối tượng
                (5, 4); -- Cơ sở dữ liệu

            -- Marketing (major_id = 6)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (6, 4); -- Cơ sở dữ liệu

            -- Thương mại Điện tử (major_id = 7)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (7, 1), -- Lập trình C
                (7, 3), -- Lập trình hướng đối tượng
                (7, 4), -- Cơ sở dữ liệu
                (7, 5), -- Mạng máy tính
                (7, 8); -- Cơ sở An toàn thông tin

            -- Logistics và Quản lý Chuỗi cung ứng (major_id = 8)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (8, 4); -- Cơ sở dữ liệu

            -- Công nghệ Tài chính (major_id = 9)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (9, 1), -- Lập trình C
                (9, 2), -- Cấu trúc dữ liệu và giải thuật
                (9, 3), -- Lập trình hướng đối tượng
                (9, 4), -- Cơ sở dữ liệu
                (9, 8), -- Cơ sở An toàn thông tin
                (9, 9); -- Trí tuệ nhân tạo

            -- Công nghệ Điện tử (major_id = 10)
            INSERT INTO major_subjects (major_id, subject_id)
            VALUES
                (10, 1), -- Lập trình C
                (10, 7); -- Kiến trúc máy tính
        """),
            
    ]