from django.db import migrations

class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL("""
            CREATE TABLE subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT
            );

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
        """),

        migrations.RunSQL("""
            CREATE TABLE tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                time_limit INTEGER,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                due_date DATETIME,
                max_attempts INTEGER DEFAULT 1,

                subject_id INTEGER NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_type TEXT NOT NULL CHECK(question_type IN ('multiple_choice', 'essay')),
                content TEXT NOT NULL,
                explanation TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                attachment_path TEXT,

                subject_id INTEGER NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE test_questions (
                question_order INTEGER NOT NULL DEFAULT 0,
                test_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                PRIMARY KEY (test_id, question_id),
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE multiple_choice_questions (
                options TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(options)),
                allow_multiple INTEGER DEFAULT 0,
                randomize_options INTEGER DEFAULT 1,

                id INTEGER PRIMARY KEY,
                FOREIGN KEY (id) REFERENCES questions(id) ON DELETE CASCADE
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE essay_questions (
                word_limit INTEGER DEFAULT 0,

                id INTEGER PRIMARY KEY,
                FOREIGN KEY (id) REFERENCES questions(id) ON DELETE CASCADE
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                answer_content TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(answer_content)),
                score REAL, -- NULL nếu chưa chấm

                submission_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                UNIQUE(submission_id, question_id),
                FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            );
        """),

        migrations.RunSQL("""    
            CREATE TABLE submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submitted_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                time_spent INTEGER DEFAULT 0,
                attempt_number INTEGER DEFAULT 1,
                total_score REAL,
                
                test_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                UNIQUE(test_id, author_id, attempt_number),
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                attachment_path TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at DATETIME,
                view_count INTEGER NOT NULL DEFAULT 0,

                author_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
        """),

        # Chỉ comment và vote được cho post

        migrations.RunSQL("""
            CREATE TABLE comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
    
                commenter_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                FOREIGN KEY (commenter_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            );
        """),

        migrations.RunSQL("""
            CREATE TABLE votes (
                vote_value INTEGER NOT NULL CHECK(vote_value IN (1, -1)),
                voter_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,

                PRIMARY KEY(voter_id, post_id),
                FOREIGN KEY (voter_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            );
        """),
    ]
