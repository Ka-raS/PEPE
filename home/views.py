from datetime import datetime

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
        return render(request, 'home/index.html', context)
    
    # USER ĐÃ ĐĂNG NHẬP
    context = {
        'is_authenticated': True,
        'username': request.session.get('username'),
        'email': request.session.get('email'),
        'user_type': request.session.get('user_type'),
        'first_name': request.session.get('first_name', ''),
        'last_name': request.session.get('last_name', ''),
    }
    
    # Tạo full_name
    full_name = f"{context['first_name']} {context['last_name']}".strip()
    context['full_name'] = full_name or context['username']
        
    # Query chỉ dữ liệu người dùng không có trong session
    with connection.cursor() as cursor:
        if context['user_type'] == 'student':
            cursor.execute("""
                SELECT 
                    u.avatar_path,
                    s.student_code, 
                    s.enrollment_year,
                    m.name as major_name
                FROM users u
                LEFT JOIN students s ON u.id = s.id
                LEFT JOIN majors m ON s.major_id = m.id
                WHERE u.id = %s
            """, [user_id])
            
            row = cursor.fetchone()
            if row:
                context['avatar_path'] = row[0]
                context['student_code'] = row[1]
                context['enrollment_year'] = row[2]
                context['major_name'] = row[3]
            
        elif context['user_type'] == 'teacher':
            # Query thông tin giảng viên nếu cần
            cursor.execute("""
                SELECT 
                    u.avatar_path,
                    d.name as department_name,
                    t.title
                FROM users u
                LEFT JOIN teachers t ON u.id = t.id
                LEFT JOIN departments d ON t.department_id = d.id
                WHERE u.id = %s
            """, [user_id])
            
            row = cursor.fetchone()
            if row:
                context['avatar_path'] = row[0]
                context['department'] = row[1]
                context['title'] = row[2]
    
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
                t.created_at,
                t.due_date,
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
                'created_at': row[3],
                'due_date': row[4],
                'author_name': row[5],
                'author_avatar_path': row[6],
                'subject_name': row[7],
                'question_count': row[8],
            }
            for row in cursor.fetchall()
        ]
    print(*context['latest_tests'], sep='\n')
    return render(request, 'home/index.html', context)