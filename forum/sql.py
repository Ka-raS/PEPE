from django.db import connection


def question_count():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM questions")
        return cursor.fetchone()[0]

def subject_tests(subject_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id, 
                title, 
                description,
                time_limit, 
                ends_at, 
                created_at,
                max_attempts,
                CASE 
                    WHEN ends_at IS NULL THEN 1
                    WHEN datetime(ends_at) > datetime('now') THEN 1
                    ELSE 0
                END as is_active
            FROM tests
            WHERE subject_id = %s
            ORDER BY created_at DESC
        """, [subject_id])
        
        return [
            {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'time_limit': row[3],
                'ends_at': row[4],
                'created_at': row[5],
                'max_attempts': row[6],
                'is_active': row[7]
            }
            for row in cursor.fetchall()
        ]
    
def subject_posts(subject_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                p.id, 
                p.title, 
                p.content,
                p.view_count,
                p.created_at,
                p.author_id,
                u.username,
                COUNT(c.id)
            FROM posts p
            LEFT JOIN users u ON p.author_id = u.id
            LEFT JOIN comments c ON p.id = c.post_id
            WHERE p.subject_id = %s
            GROUP BY p.id, p.title, p.content, p.view_count, p.created_at, p.author_id, u.username
            ORDER BY p.created_at
        """, [subject_id])
        
        return [
            {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'view_count': row[3],
                'created_at': row[4],
                'author': {
                    'id': row[5],
                    'username': row[6]
                },
                'comment_count': row[7]
            }
            for row in cursor.fetchall()
        ]
    
def posts_with_attachment(count):
    if count < 0:
        count = 'NULL'

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.id, p.title, p.content, s.name, COALESCE(p.updated_at, p.created_at) as updated_at 
            FROM posts p
            JOIN subjects s ON p.subject_id = s.id
            WHERE p.attachment_path IS NOT NULL
            ORDER BY updated_at DESC 
            LIMIT %s
        """, [count])
        return [
            {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'subject': row[3],
                'updated_at': row[4]
            }
            for row in cursor.fetchall()
        ]
    
def popular_posts(count):
    if count < 0:
        count = 'NULL'

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                p.id,
                p.title,
                p.created_at,
                u.username,
                u.avatar_path,
                s.name as subject_name,
                p.view_count,
                (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comment_count,
                COALESCE((SELECT SUM(vote_value) FROM votes v WHERE v.post_id = p.id), 0) as vote_value
            FROM posts p
            JOIN users u ON p.author_id = u.id
            JOIN subjects s ON p.subject_id = s.id
            ORDER BY view_count DESC
            LIMIT %s
        """, [count])
        return [
            {
                'id': row[0],
                'title': row[1],
                'created_at': row[2],
                'username': row[3],
                'author_avatar_path': row[4],
                'subject_name': row[5],
                'view_count': row[6],
                'comment_count': row[7],
                'vote_value': row[8],
            }
            for row in cursor.fetchall()
        ]
    
def latest_posts(count):
    if (count < 0):
        count = 'NULL'

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                p.id,
                p.title,
                p.created_at,
                u.username,
                u.avatar_path,
                s.name as subject_name,
                p.view_count,
                (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comment_count,
                COALESCE((SELECT SUM(vote_value) FROM votes v WHERE v.post_id = p.id), 0) as vote_value
            FROM posts p
            JOIN users u ON p.author_id = u.id
            JOIN subjects s ON p.subject_id = s.id
            ORDER BY p.created_at DESC
            LIMIT %s
        """, [count])
        return [
            {
                'id': row[0],
                'title': row[1],
                'created_at': row[2],
                'username': row[3],
                'author_avatar_path': row[4],
                'subject_name': row[5],
                'view_count': row[6],
                'comment_count': row[7],
                'vote_value': row[8],
            }
            for row in cursor.fetchall()
        ]
    
def latest_tests(count):
    if count < 0:
        count = 'NULL'

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                t.id,
                t.title,
                t.description,
                t.time_limit,
                t.created_at,
                t.ends_at,
                u.username AS author_name,
                u.avatar_path AS author_avatar_path,
                s.name as subject_name,
                (SELECT COUNT(*) FROM test_questions tq WHERE tq.test_id = t.id) as question_count
            FROM tests t
            JOIN users u ON t.author_id = u.id
            JOIN subjects s ON t.subject_id = s.id
            ORDER BY t.created_at DESC
            LIMIT %s
        """, [count])
        return [
            {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'time_limit': row[3],
                'created_at': row[4],
                'ends_at': row[5],
                'author_name': row[6],
                'author_avatar_path': row[7],
                'subject_name': row[8],
                'question_count': row[9],
            }
            for row in cursor.fetchall()
        ]
    
def insert_post(title, content, subject_id, user_id, attachment_path):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO posts (title, content, subject_id, author_id, attachment_path)
            VALUES (%s, %s, %s, %s, %s)
        """, [title, content, subject_id, user_id, attachment_path])