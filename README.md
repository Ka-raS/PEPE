# PEPE

A web forum

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
    $ source .venv/bin/activate
    $ pip install -r requirements.txt
    ```

3. Run Server:
    ```bash
    $ python manage.py runserver
    ```

## Users in `example.sqlite3`

| Username        | Password  |
|-----------------|-----------|
| student         | 000000    |
| anotherstudent  | 000000    |
| teacher         | 000000    |