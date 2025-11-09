from django.db import migrations

class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL("""
            CREATE TABLE tests (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                max_attempts INTEGER DEFAULT 1,
                time_limit INTEGER,  -- minutes
                ends_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),

                author_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                FOREIGN KEY (author_id) REFERENCES users(id),
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            );

            CREATE TABLE questions (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                attachment_path TEXT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                
                author_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                FOREIGN KEY (author_id) REFERENCES users(id),
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            );

            CREATE TABLE test_questions (
                question_order INTEGER NOT NULL DEFAULT 0,
                test_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                PRIMARY KEY (test_id, question_id),
                UNIQUE (test_id, question_order),
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            );

            CREATE TABLE essay_questions (
                word_limit INTEGER,
                id INTEGER PRIMARY KEY,
                FOREIGN KEY (id) REFERENCES questions(id) ON DELETE CASCADE
            );

            CREATE TABLE multiple_choice_options (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                
                question_id INTEGER NOT NULL,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            );

            CREATE TABLE multiple_choice_questions (
                randomize_options INTEGER DEFAULT 1,
                
                id INTEGER PRIMARY KEY,
                correct_option_id INTEGER UNIQUE NOT NULL,
                FOREIGN KEY (id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY (correct_option_id) REFERENCES multiple_choice_options(id) ON DELETE CASCADE
            );


            CREATE TABLE submissions (
                id INTEGER PRIMARY KEY,
                time_spent INTEGER NOT NULL CHECK (time_spent >= 0), -- seconds
                attempt_number INTEGER DEFAULT 1 CHECK (attempt_number > 0),
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
                
                test_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                UNIQUE(test_id, author_id, attempt_number),
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE answers (
                id INTEGER PRIMARY KEY,
                submission_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                UNIQUE(submission_id, question_id),
                FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            );

            CREATE TABLE multiple_choice_answers (
                id INTEGER PRIMARY KEY,
                selected_option_id INTEGER NOT NULL,
                FOREIGN KEY (id) REFERENCES answers(id) ON DELETE CASCADE,
                FOREIGN KEY (selected_option_id) REFERENCES multiple_choice_options(id) ON DELETE CASCADE
            );

            CREATE TABLE essay_answers (
                id INTEGER PRIMARY KEY,
                content TEXT,
                is_corrected INTEGER CHECK(is_corrected IN (0,1)), -- NULL: chưa chấm
                FOREIGN KEY (id) REFERENCES answers(id) ON DELETE CASCADE
            ); 
                          

            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
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

            -- Chỉ comment và vote được cho post

            CREATE TABLE comments (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT (datetime('now', 'localtime')),
    
                commenter_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                FOREIGN KEY (commenter_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            );

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