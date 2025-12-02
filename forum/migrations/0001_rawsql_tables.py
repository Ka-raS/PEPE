from django.db import migrations

class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL("""
            -- Thực thể mạnh
            CREATE TABLE tests (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                max_attempts INTEGER DEFAULT 1,
                time_limit INTEGER,  -- minutes
                ends_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),

                author_id INTEGER,
                subject_id INTEGER,
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL, -- Nếu giáo viên bị xóa thì bài kiểm tra vẫn giữ lại
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL -- Nếu môn học bị xóa thì bài kiểm tra vẫn giữ lại
            );

            -- Thực thể mạnh
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                attachment_path TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                question_type TEXT NOT NULL CHECK(question_type IN ('multiple_choice', 'essay')),

                author_id INTEGER,
                subject_id INTEGER,
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL, -- Nếu giáo viên bị xóa thì câu hỏi vẫn giữ lại
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL -- Nếu môn học bị xóa thì câu hỏi vẫn giữ lại
            );

            -- Quan hệ nhiều-nhiều giữa tests và questions
            CREATE TABLE test_questions (
                question_order INTEGER NOT NULL DEFAULT 0,
                test_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                PRIMARY KEY (test_id, question_id),
                UNIQUE (test_id, question_order),
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE, -- Nếu xóa bài kiểm tra thì các câu hỏi không có trong bài kiểm tra đó
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE -- Nếu xóa câu hỏi thì các bài kiểm tra không có câu hỏi đó nữa
            );

            -- Thực thể yếu phụ thuộc vào questions
            CREATE TABLE essay_questions (
                word_limit INTEGER,
                id INTEGER PRIMARY KEY,
                FOREIGN KEY (id) REFERENCES questions(id) ON DELETE CASCADE -- Nếu xóa câu hỏi thì câu hỏi tự luận cũng bị xóa
            );

            -- Thực thể yếu phụ thuộc vào questions
            CREATE TABLE multiple_choice_options (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                UNIQUE(question_id, content),
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE -- Nếu xóa câu hỏi thì các lựa chọn cũng bị xóa
            );

            -- Thực thể yếu phụ thuộc vào questions
            CREATE TABLE multiple_choice_questions (
                randomize_options INTEGER DEFAULT 1,

                id INTEGER PRIMARY KEY,
                correct_option_id INTEGER UNIQUE NOT NULL,
                FOREIGN KEY (id) REFERENCES questions(id) ON DELETE CASCADE, -- Nếu xóa câu hỏi thì câu hỏi trắc nghiệm cũng bị xóa
                FOREIGN KEY (correct_option_id) REFERENCES multiple_choice_options(id) ON DELETE RESTRICT -- Không thể xóa lựa chọn đúng, chỉ được chỉnh sửa
            );

            -- Quan hệ nhiều-nhiều giữa users và tests
            CREATE TABLE submissions (
                id INTEGER PRIMARY KEY,
                time_spent INTEGER NOT NULL CHECK (time_spent >= 0), -- seconds
                attempt_number INTEGER DEFAULT 1 CHECK (attempt_number > 0),
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),

                test_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                UNIQUE(test_id, author_id, attempt_number),
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE, -- Nếu xóa bài kiểm tra thì các bài nộp cũng bị xóa
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE -- Nếu xóa user thì các bài nộp cũng bị xóa
            );

            -- Quan hệ nhiều-nhiều giữa submissions và multiple_choice_questions
            CREATE TABLE multiple_choice_answers (
                selected_option_id INTEGER NOT NULL, -- Bắc cầu sang mutiple_choice_questions
                submission_id INTEGER NOT NULL,
                PRIMARY KEY (selected_option_id, submission_id),
                FOREIGN KEY (selected_option_id) REFERENCES multiple_choice_options(id) ON DELETE RESTRICT, -- Không thể xóa lựa chọn đúng, chỉ được chỉnh sửa
                FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE -- Nếu xóa bài nộp thì các câu trả lời cũng bị xóa
            );

            -- Quan hệ nhiều-nhiều giữa submissions và essay_questions
            CREATE TABLE essay_answers (
                content TEXT,
                is_correct INTEGER CHECK(is_correct IN (0,1)), -- NULL: chưa chấm

                submission_id INTEGER NOT NULL,
                essay_question_id INTEGER NOT NULL,
                PRIMARY KEY (submission_id, essay_question_id),
                FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,   -- Nếu xóa bài nộp thì các câu trả lời cũng bị xóa
                FOREIGN KEY (essay_question_id) REFERENCES essay_questions(id) ON DELETE CASCADE    -- Nếu xóa câu hỏi tự luận thì các câu trả lời cũng bị xóa
            );


            -- Thực thể mạnh
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                attachment_path TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at DATETIME,
                view_count INTEGER NOT NULL DEFAULT 0,

                author_id INTEGER,
                subject_id INTEGER,
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL, -- Nếu user bị xóa thì bài viết vẫn giữ lại
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL -- Nếu môn học bị xóa thì bài viết vẫn giữ lại
            );

            -- Chỉ comment và vote được cho post

            -- Quan hệ nhiều-nhiều giữa users và posts
            -- Một user có thể comment nhiều post, một post có thể có nhiều comment từ nhiều user khác nhau
            CREATE TABLE comments (
                content TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),

                commenter_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                PRIMARY KEY(commenter_id, post_id, created_at),
                FOREIGN KEY (commenter_id) REFERENCES users(id) ON DELETE CASCADE, -- Nếu user bị xóa thì các comment của user đó cũng bị xóa
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE -- Nếu post bị xóa thì các comment của post đó cũng bị xóa
            );

            -- Quan hệ nhiều-nhiều giữa users và posts với ràng buộc duy nhất:
            -- Một user có thể vote nhiều post, một post có thể có nhiều vote từ nhiều user khác nhau, và chỉ 1 vote từ 1 user
            CREATE TABLE votes (
                vote_value INTEGER NOT NULL CHECK(vote_value IN (1, -1)),
                voter_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,

                PRIMARY KEY(voter_id, post_id),
                FOREIGN KEY (voter_id) REFERENCES users(id) ON DELETE CASCADE, -- Nếu user bị xóa thì các vote của user đó cũng bị xóa
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE -- Nếu post bị xóa thì các vote của post đó cũng bị xóa
            );
                          
            CREATE TABLE post_buy (
                post_id INTEGER NOT NULL,
                buyer_id INTEGER NOT NULL,
                PRIMARY KEY (post_id, buyer_id),
                FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY(buyer_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE test_payments (
                test_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                paid_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                PRIMARY KEY (test_id, user_id),
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
                          
            CREATE TABLE IF NOT EXISTS token_rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reward_amount INTEGER NOT NULL DEFAULT 0,
                tx_hash VARCHAR(255),
                reward_type VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES auth_user (id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_token_rewards_user_id ON token_rewards(user_id);
            CREATE INDEX IF NOT EXISTS idx_token_rewards_submission_id ON token_rewards(submission_id);
            CREATE INDEX IF NOT EXISTS idx_token_rewards_created_at ON token_rewards(created_at);
        """),
    ]