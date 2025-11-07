CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
);

CREATE TABLE IF NOT EXISTS test_questions (
    question_order INTEGER NOT NULL DEFAULT 0,
    test_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    PRIMARY KEY (test_id, question_id),
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    time_limit INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date DATETIME,
    max_attempts INTEGER DEFAULT 1,

    subject_id INTEGER NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_type TEXT NOT NULL CHECK(question_type IN ('multiple_choice', 'essay')),
    content TEXT NOT NULL,
    explanation TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    attachment_path TEXT,

    subject_id INTEGER NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(id)
);

CREATE TABLE IF NOT EXISTS multiple_choice_questions (
    options TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(options)),
    allow_multiple INTEGER DEFAULT 0,
    randomize_options INTEGER DEFAULT 1,

    id INTEGER PRIMARY KEY,
    FOREIGN KEY (id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS essay_questions (
    word_limit INTEGER DEFAULT 0,

    id INTEGER PRIMARY KEY,
    FOREIGN KEY (id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_content TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(answer_content)),
    score REAL, -- NULL nếu chưa chấm

    submission_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    UNIQUE(submission_id, question_id),
    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    time_spent INTEGER DEFAULT 0,
    attempt_number INTEGER DEFAULT 1,
    total_score REAL,
    
    test_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    UNIQUE(test_id, author_id, attempt_number)
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    attachment_path TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    view_count INTEGER NOT NULL DEFAULT 0,
    like_count INTEGER NOT NULL DEFAULT 0,

    author_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    FOREIGN KEY (author_id) REFERENCES users(id),     
    FOREIGN KEY (subject_id) REFERENCES subjects(id) 
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    
    author_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    parent_id INTEGER, 
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
);