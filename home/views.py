from django.shortcuts import render
from django.db import connection


def index(request):
    user_id = request.session.get('user_id')

    if not user_id or user_id == 'None':
        # Khách
        context = {'is_authenticated': False}        
        with connection.cursor() as cursor:
            # Đếm users
            cursor.execute("SELECT COUNT(*) FROM users")
            context['user_count'] = cursor.fetchone()[0]

    else:    
        # USER ĐÃ ĐĂNG NHẬP
        context = {
            'is_authenticated': True,
            'username': request.session.get('username'),
        }
    
    with connection.cursor() as cursor:
        # Tìm 5 Bài đăng tài liệu làm gợi ý
        cursor.execute("""
            SELECT p.id, p.title, p.content, s.name, COALESCE(p.updated_at, p.created_at) as updated_at 
            FROM posts p
            JOIN subjects s ON p.subject_id = s.id
            WHERE p.attachment_path IS NOT NULL
            ORDER BY updated_at DESC 
            LIMIT 5
        """)
        context['suggested_posts'] = [
            {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'subject': row[3],
                'updated_at': row[4]
            }
            for row in cursor.fetchall()
        ]

        # Tìm 5 Bài đăng phổ biến nhất và 5 Bài mới nhất
        cursor.execute("""
            WITH merged_posts AS (
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
            )

            SELECT *, 'popular' FROM (
                SELECT * from merged_posts
                ORDER BY view_count DESC
                LIMIT 5
            )
                       
            UNION ALL

            SELECT *, 'latest' FROM (
                SELECT * FROM merged_posts
                ORDER BY created_at DESC
                LIMIT 5
            )
        """)

        context['popular_posts'] = []
        context['latest_posts'] = []
        for row in cursor.fetchall():
            post = {
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
            if row[9] == 'popular':
                context['popular_posts'].append(post)
            else:
                context['latest_posts'].append(post)

        # Tìm 5 bài test mới nhất
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
            LIMIT 5
        """)
        context['latest_tests'] = [
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

    return render(request, 'home/index.html', context)