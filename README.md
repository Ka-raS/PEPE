# PEPE - Web Forum

> **Also see the main branch [here](https://github.com/Ka-raS/PEPE.git)**

| ![Homepage](/media/screenshots/home_index.png)               | ![Profile](/media/screenshots/accounts_index.png)            |
|:------------------------------------------------------------:|:------------------------------------------------------------:|
| ![Post](/media/screenshots/forum_post_detail.png)            | ![Create Post](/media/screenshots/forum_post_form.png)       |
| ![Test](/media/screenshots/forum_test_detail.png)            | ![Take Test](/media/screenshots/forum_take_test.png)         |
| ![Create Test](/media/screenshots/forum_test_form.png)       | ![Question Bank](/media/screenshots/forum_question_bank.png) |
| ![Grade Test](/media/screenshots/forum_grade_submission.png) | ![Submission](/media/screenshots/forum_submission.png)       |

## Contributors

- karas ([Ka-raS](https://github.com/Ka-raS))  
- Phạm Quốc Hùng ([phamquocdow](https://github.com/phamquocdow))  
- Juky ([Namtran205](https://github.com/Namtran205))  
- An Phạm ([AnPham1820](https://github.com/AnPham1820))

## Main Features

- User login and registration for students and teachers.
- Personal profile editing with avatar upload.
- Subject-based discussion forums.
- Creating posts with file attachments.
- Creating tests from the question banks.
- Grading test's submissions both automatically and manually.

## Documentation (Vietnamese)

- [Database](/docs/Báo_cáo_bài_tập_lớn_môn_cơ_sở_dữ_liệu_nhóm_10.pdf)

## How to Run

### Requirements

- [Python 3.12.3](https://www.python.org/downloads/)
- [Django 5.2.7](https://www.djangoproject.com/download/) - Web Framework

1. Git Clone:

    ```bash
    git clone --branch no-token https://github.com/Ka-raS/PEPE.git
    cd PEPE
    ```

2. Install dependencies:

    ```bash
    python -m venv .venv
    source .venv/bin/activate # .\.venv\Scripts\activate for Windows
    pip install -r requirements.txt
    ```

3. Run Server:

    ```bash
    python manage.py runserver
    ```

## Users in `example.sqlite3`

| Username        | Password  |
|-----------------|-----------|
| student         | 000000    |
| anotherstudent  | 000000    |
| teacher         | 000000    |
