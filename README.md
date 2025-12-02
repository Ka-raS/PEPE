# PEPE - Web Forum

|                                                               |                                                              |
|:-------------------------------------------------------------:|:------------------------------------------------------------:|
| ![Homepage](   /media/screenshots/home_index.png)             | ![Profile](      /media/screenshots/accounts_index.png)      |
| ![Post](       /media/screenshots/forum_post_detail.png)      | ![Create Post](  /media/screenshots/forum_post_form.png)     |
| ![Test](       /media/screenshots/forum_test_detail.png)      | ![Take Test](    /media/screenshots/forum_take_test.png)     |
| ![Create Test](/media/screenshots/forum_test_form.png)        | ![Question Bank](/media/screenshots/forum_question_bank.png) |
| ![Grade Test]( /media/screenshots/forum_grade_submission.png) | ![Submission](   /media/screenshots/forum_submission.png)    |

## Contributors

- [karas](https://github.com/Ka-raS)
- [Phạm Quốc Hùng](https://github.com/phamquocdow)
- [Juky](https://github.com/Namtran205)
- [An Phạm](https://github.com/AnPham1820)
- [hastur-78](https://github.com/hastur-78)

## Main Features

- User login and registration for students and teachers.
- Personal profile editing with avatar upload.
- Subject-based discussion forums.
- Creating posts with file attachments.
- Creating tests from the question banks.
- Grading test's submissions both automatically and manually.
- [See more here (Vietnamese)](/docs/Báo_cáo_bài_tập_lớn_môn_cơ_sở_dữ_liệu_nhóm_10.pdf)

## Requirements

- [Python 3.12.3](https://www.python.org/downloads/)
- [Django 5.2.7](https://www.djangoproject.com/download/) - Web Framework

## How to Run

1. Clone:

    From the main branch (with ORM):
    ```bash
    $ git clone --branch main https://github.com/Ka-raS/PEPE.git
    $ cd PEPE
    ```

    Or from the rawsql branch (without ORM):
    ```bash
    $ git clone --branch rawsql https://github.com/Ka-raS/PEPE.git
    $ cd PEPE
    ```

2. Install dependencies:
    ```bash
    $ python -m venv .venv
    $ source .venv/bin/activate # .\.venv\Scripts\activate for Windows
    $ pip install -r requirements.txt
    ```

3. Run Server:
    ```bash
    $ python manage.py runserver
    ```