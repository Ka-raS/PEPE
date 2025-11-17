from django.db import connection
from django.shortcuts import render
from django.core.paginator import Paginator


def index(request):
    query = request.GET.get('q', '').strip()
    results = {
        'users': [],
        'posts': [],
        'tests': []
    }
    
    if query:
        # Reuse the individual search functions with detailed=False for performance
        results['users'] = _search_users(query, detailed=False)
        results['posts'] = _search_posts(query, detailed=False) 
        results['tests'] = _search_tests(query, detailed=False)

    # Pagination
    users_paginator = Paginator(results['users'], 10)
    posts_paginator = Paginator(results['posts'], 10)
    tests_paginator = Paginator(results['tests'], 10)
    
    page = request.GET.get('page', 1)
    
    context = {
        'query': query,
        'current_tab': 'all',
        'users': users_paginator.get_page(page),
        'posts': posts_paginator.get_page(page),
        'tests': tests_paginator.get_page(page),
        'users_count': len(results['users']),
        'posts_count': len(results['posts']),
        'tests_count': len(results['tests']),
        'total_count': len(results['users']) + len(results['posts']) + len(results['tests'])
    }
    
    return render(request, 'search/index.html', context)

def search_users(request):
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', 'all')
    department_filter = request.GET.get('department', '')
    enrollment_year_filter = request.GET.get('enrollment_year', '')
    search_in = request.GET.getlist('search_in')
    sort_by = request.GET.get('sort', 'username')
    
    # Only search if there's a query
    if query:
        results = _search_users(
            query, 
            detailed=True,
            role_filter=role_filter,
            department_filter=department_filter,
            enrollment_year_filter=enrollment_year_filter,
            search_in=search_in,
            sort_by=sort_by
        )
    else:
        results = []

    # Get departments for filter dropdown - include both teacher departments and student major departments
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT d.id, d.name 
            FROM departments d
            WHERE d.id IN (
                SELECT department_id FROM teachers WHERE department_id IS NOT NULL
                UNION
                SELECT m.department_id FROM majors m WHERE m.department_id IS NOT NULL
            )
            ORDER BY d.name
        """)
        departments = [dict(zip(['id', 'name'], row)) for row in cursor.fetchall()]

    # Get enrollment years for filter dropdown
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT enrollment_year FROM students WHERE enrollment_year IS NOT NULL ORDER BY enrollment_year DESC")
        enrollment_years = [row[0] for row in cursor.fetchall()]

    paginator = Paginator(results, 10)
    page = request.GET.get('page', 1)
    
    context = {
        'query': query,
        'current_tab': 'users',
        'users': paginator.get_page(page),
        'users_count': len(results),
        'total_count': len(results),
        'departments': departments,
        'enrollment_years': enrollment_years,
        'search_in': search_in,
    }
    
    return render(request, 'search/search_users.html', context)

def search_posts(request):
    query = request.GET.get('q', '').strip()
    subject_filter = request.GET.get('subject', '')
    author_filter = request.GET.get('author', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_in = request.GET.getlist('search_in')
    sort_by = request.GET.get('sort', 'created_at')
    min_views = request.GET.get('min_views', '')
    min_comments = request.GET.get('min_comments', '')
    
    # Only search if there's a query
    if query:
        results = _search_posts(
            query, 
            detailed=True,
            subject_filter=subject_filter,
            author_filter=author_filter,
            date_from=date_from,
            date_to=date_to,
            search_in=search_in,
            sort_by=sort_by,
            min_views=min_views,
            min_comments=min_comments
        )
    else:
        results = []

    # Get subjects for filter dropdown
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM subjects ORDER BY name")
        subjects = [dict(zip(['id', 'name'], row)) for row in cursor.fetchall()]

    paginator = Paginator(results, 10)
    page = request.GET.get('page', 1)
    
    context = {
        'query': query,
        'current_tab': 'posts',
        'posts': paginator.get_page(page),
        'posts_count': len(results),
        'total_count': len(results),
        'subjects': subjects,
        'search_in': search_in,
    }
    
    return render(request, 'search/search_posts.html', context)

def search_tests(request):
    query = request.GET.get('q', '').strip()
    subject_filter = request.GET.get('subject', '')
    author_filter = request.GET.get('author', '')
    time_limit_filter = request.GET.get('time_limit', '')
    sort_by = request.GET.get('sort', 'created_at')
    
    # Only search if there's a query
    if query:
        results = _search_tests(
            query, 
            detailed=True,
            subject_filter=subject_filter,
            author_filter=author_filter,
            time_limit_filter=time_limit_filter,
            sort_by=sort_by
        )
    else:
        results = []

    # Get subjects for filter dropdown
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM subjects ORDER BY name")
        subjects = [dict(zip(['id', 'name'], row)) for row in cursor.fetchall()]

    paginator = Paginator(results, 10)
    page = request.GET.get('page', 1)
    
    context = {
        'query': query,
        'current_tab': 'tests',
        'tests': paginator.get_page(page),
        'tests_count': len(results),
        'total_count': len(results),
        'subjects': subjects
    }
    
    return render(request, 'search/search_tests.html', context)

# Helper functions
def _search_users(query, detailed=False, **filters):
    with connection.cursor() as cursor:
        # Base query - tối giản nhưng vẫn đủ thông tin
        base_query = """
            SELECT 
                u.id, u.username, u.email, 
                u.avatar_path,
                -- Full name xử lý NULL
                CASE 
                    WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL 
                    THEN u.last_name || ' ' || u.first_name
                    WHEN u.first_name IS NOT NULL THEN u.first_name
                    WHEN u.last_name IS NOT NULL THEN u.last_name
                    ELSE NULL
                END as full_name,
                -- Role detection
                CASE 
                    WHEN s.id IS NOT NULL THEN 'student'
                    WHEN t.id IS NOT NULL THEN 'teacher'
                    ELSE 'user'
                END as role
        """
        
        # Thêm các trường chi tiết nếu cần
        if detailed:
            base_query += """,
                -- Student info
                s.student_code, s.enrollment_year, m.name as major_name,
                -- Teacher info  
                t.teacher_code, t.title, t.degree, d.name as department_name
            """
        else:
            base_query += """,
                s.student_code, t.teacher_code
            """
        
        # FROM và JOINs
        base_query += """
            FROM users u
            LEFT JOIN students s ON u.id = s.id
            LEFT JOIN teachers t ON u.id = t.id
        """
        
        # Chỉ JOIN các bảng bổ sung khi cần detailed hoặc filter
        if detailed or filters.get('department_filter'):
            base_query += """
                LEFT JOIN departments d ON t.department_id = d.id
                LEFT JOIN majors m ON s.major_id = m.id
                LEFT JOIN departments md ON m.department_id = md.id
            """
        elif detailed:
            base_query += """
                LEFT JOIN departments d ON t.department_id = d.id
                LEFT JOIN majors m ON s.major_id = m.id
            """

        # Build WHERE conditions
        where_conditions = []
        params = []

        # Search conditions
        if query:
            search_parts = []
            search_in = filters.get('search_in', ['username', 'name', 'email', 'code'])
            
            if not search_in:
                search_in = ['username', 'name', 'email', 'code']
            
            if 'username' in search_in:
                search_parts.append("u.username LIKE %s")
                params.append(f'%{query}%')
            if 'name' in search_in:
                search_parts.append("(u.first_name LIKE %s OR u.last_name LIKE %s)")
                params.extend([f'%{query}%', f'%{query}%'])
            if 'email' in search_in:
                search_parts.append("u.email LIKE %s")
                params.append(f'%{query}%')
            if 'code' in search_in:
                search_parts.append("(s.student_code LIKE %s OR t.teacher_code LIKE %s)")
                params.extend([f'%{query}%', f'%{query}%'])
            
            if search_parts:
                where_conditions.append(f"({' OR '.join(search_parts)})")
        else:
            where_conditions.append("1=0")

        # Role filter
        role_filter = filters.get('role_filter', 'all')
        if role_filter == 'student':
            where_conditions.append("s.id IS NOT NULL")
        elif role_filter == 'teacher':
            where_conditions.append("t.id IS NOT NULL")

        # Department filter
        department_filter = filters.get('department_filter')
        if department_filter:
            where_conditions.append("(d.id = %s OR md.id = %s)")
            params.extend([department_filter, department_filter])

        # Enrollment year filter
        enrollment_year_filter = filters.get('enrollment_year_filter')
        if enrollment_year_filter:
            where_conditions.append("s.enrollment_year = %s")
            params.append(enrollment_year_filter)

        # Build final query
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Sorting - đơn giản hóa
        sort_by = filters.get('sort_by', 'username')
        sort_mapping = {
            'username': 'u.username',
            'full_name': """
                CASE WHEN u.first_name IS NULL AND u.last_name IS NULL THEN 1 ELSE 0 END,
                COALESCE(u.last_name || ' ' || u.first_name, u.first_name, u.last_name, '')
            """, 
            'email': 'u.email',
            'student_code': 's.student_code',
            'teacher_code': 't.teacher_code'
        }
        sort_field = sort_mapping.get(sort_by, 'u.username')
        order_clause = f" ORDER BY {sort_field}"

        final_query = base_query + where_clause + order_clause
        
        cursor.execute(final_query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def _search_posts(query, detailed=False, **filters):
    with connection.cursor() as cursor:
        # Base query
        base_query = """
            SELECT p.id, p.title, p.content, p.created_at, p.view_count, p.updated_at,
                   u.username as author_name, u.id as author_id,
                   s.name as subject_name, s.id as subject_id,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comment_count,
                   (SELECT COALESCE(SUM(v.vote_value), 0) FROM votes v WHERE v.post_id = p.id) as vote_score
            FROM posts p
            JOIN users u ON p.author_id = u.id
            JOIN subjects s ON p.subject_id = s.id
        """
        
        # Build WHERE conditions
        where_conditions = []
        params = []

        # Search conditions
        if query:
            search_parts = []
            search_in = filters.get('search_in', ['title', 'content'])
            
            if not search_in:
                search_in = ['title', 'content']
            
            if 'title' in search_in:
                search_parts.append("p.title LIKE %s")
                params.append(f'%{query}%')
            if 'content' in search_in:
                search_parts.append("p.content LIKE %s")
                params.append(f'%{query}%')
            if 'author' in search_in:
                search_parts.append("u.username LIKE %s")
                params.append(f'%{query}%')
            
            if search_parts:
                where_conditions.append(f"({' OR '.join(search_parts)})")
        else:
            where_conditions.append("1=0")

        # Subject filter
        subject_filter = filters.get('subject_filter')
        if subject_filter:
            where_conditions.append("p.subject_id = %s")
            params.append(subject_filter)

        # Author filter
        author_filter = filters.get('author_filter')
        if author_filter:
            where_conditions.append("p.author_id = %s")
            params.append(author_filter)

        # Date range filter
        date_from = filters.get('date_from')
        date_to = filters.get('date_to')
        if date_from:
            where_conditions.append("DATE(p.created_at) >= %s")
            params.append(date_from)
        if date_to:
            where_conditions.append("DATE(p.created_at) <= %s")
            params.append(date_to)

        # Minimum views filter
        min_views = filters.get('min_views')
        if min_views:
            where_conditions.append("p.view_count >= %s")
            params.append(min_views)

        # Minimum comments filter
        min_comments = filters.get('min_comments')
        if min_comments:
            where_conditions.append("(SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) >= %s")
            params.append(min_comments)

        # Build final query
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Sorting
        sort_by = filters.get('sort_by', 'created_at')
        sort_mapping = {
            'created_at': 'p.created_at DESC',
            'updated_at': 'p.updated_at DESC',
            'view_count': 'p.view_count DESC',
            'comment_count': 'comment_count DESC',
            'vote_score': 'vote_score DESC',
            'title': 'p.title ASC'
        }
        order_clause = " ORDER BY " + sort_mapping.get(sort_by, 'p.created_at DESC')

        final_query = base_query + where_clause + order_clause
        
        cursor.execute(final_query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
def _search_tests(query, detailed=False, **filters):
    with connection.cursor() as cursor:
        # Base query
        base_query = """
            SELECT 
                t.id, t.title, t.description, t.time_limit, t.max_attempts, 
                t.created_at, t.ends_at, u.username as author_name, 
                s.name as subject_name,
                (SELECT COUNT(*) FROM test_questions tq WHERE tq.test_id = t.id) as question_count
            FROM tests t
            JOIN users u ON t.author_id = u.id
            JOIN subjects s ON t.subject_id = s.id
        """
        
        # Build WHERE conditions
        where_conditions = []
        params = []

        # Search conditions
        if query:
            where_conditions.append("(t.title LIKE %s OR t.description LIKE %s)")
            params.extend([f'%{query}%', f'%{query}%'])
        else:
            where_conditions.append("1=0")

        # Subject filter
        subject_filter = filters.get('subject_filter')
        if subject_filter:
            where_conditions.append("t.subject_id = %s")
            params.append(subject_filter)

        # Author filter
        author_filter = filters.get('author_filter')
        if author_filter:
            where_conditions.append("t.author_id = %s")
            params.append(author_filter)

        # Time limit filter
        time_limit_filter = filters.get('time_limit_filter')
        if time_limit_filter:
            if time_limit_filter == 'short':
                where_conditions.append("t.time_limit <= 30")
            elif time_limit_filter == 'medium':
                where_conditions.append("t.time_limit > 30 AND t.time_limit <= 60")
            elif time_limit_filter == 'long':
                where_conditions.append("t.time_limit > 60")

        # Build final query
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Sorting
        sort_by = filters.get('sort_by', 'created_at')
        sort_mapping = {
            'title': 't.title',
            'created_at': 't.created_at DESC',
            'time_limit': 't.time_limit',
            'question_count': 'question_count DESC',
            'author': 'u.username'
        }
        sort_field = sort_mapping.get(sort_by, 't.created_at DESC')
        order_clause = f" ORDER BY {sort_field}"

        final_query = base_query + where_clause + order_clause
        
        cursor.execute(final_query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]