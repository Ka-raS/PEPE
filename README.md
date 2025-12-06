# PEPE - Web Forum

> **Also see the [no-token branch](https://github.com/Ka-raS/PEPE/tree/no-token) for a simpler "How to run" setup**

| ![Homepage](/media/screenshots/home_index.png)               | ![Profile](/media/screenshots/accounts_index.png)            |
|:------------------------------------------------------------:|:------------------------------------------------------------:|
| ![Post](/media/screenshots/forum_post_detail.png)            | ![Create Post](/media/screenshots/forum_post_form.png)       |
| ![Test](/media/screenshots/forum_test_detail.png)            | ![Take Test](/media/screenshots/forum_take_test.png)         |
| ![Create Test](/media/screenshots/forum_test_form.png)       | ![Question Bank](/media/screenshots/forum_question_bank.png) |
| ![Grade Test](/media/screenshots/forum_grade_submission.png) | ![Submission](/media/screenshots/forum_submission.png)       |
| ![Wallet](/media/screenshots/wallet_index.png)               | ![Referral](/media/screenshots/wallet_referral.png)         |

## Contributors

- karas ([Ka-raS](https://github.com/Ka-raS))  
- Phạm Quốc Hùng ([phamquocdow](https://github.com/phamquocdow))  
- Juky ([Namtran205](https://github.com/Namtran205))  
- An Phạm ([AnPham1820](https://github.com/AnPham1820))
- hastur-78 ([hastur-78](https://github.com/hastur-78))

## Main Features

- User login and registration for students and teachers.
- Personal profile editing with avatar upload.
- Subject-based discussion forums.
- Creating posts with file attachments.
- Creating tests from the question banks.
- Grading test's submissions both automatically and manually.

- Gemini chatbot integrated.
- Use [HSCoin](https://hsc-w3oq.onrender.com) as token supplier.
- Token reward system for daily check-ins, friend referrals, and acing a test.
- Spend tokens by downloading study materials attached to posts, or unlocking a test.

## Documentation (Vietnamese)

- [Database](/docs/Báo_cáo_bài_tập_lớn_môn_cơ_sở_dữ_liệu_nhóm_10.pdf)
- [Information Security](/docs/BÁO_CÁO_CSATTT.pdf)

## How to Run

### Requirements

- [Python 3.12.3](https://www.python.org/downloads/)
- [Django 5.2.7](https://www.djangoproject.com/download/) - Web Framework

1. Git Clone:

    ```bash
    git clone https://github.com/Ka-raS/PEPE.git
    cd PEPE
    ```

2. Install dependencies:

    ```bash
    python -m venv .venv
    source .venv/bin/activate # .\.venv\Scripts\activate for Windows
    pip install -r requirements.txt
    ```

3. Set up environment variables:

    Open [`.env`](/.env) to see the instructions.

4. Run Server:

    ```bash
    python manage.py runserver
    ```

## Users in `example.sqlite3`

| Username        | Password  |
|-----------------|-----------|
| hung            | 24092005  |
| linh            | 24092005  |
