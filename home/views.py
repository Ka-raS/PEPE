from django.shortcuts import render
from django.db import connection

def index(request):
    user_id = request.session.get('user_id')
    
    if user_id:
        # USER ĐÃ ĐĂNG NHẬP
        context = {
            'is_authenticated': True,
            'user_id': user_id,
            'username': request.session.get('username'),
            'email': request.session.get('email'),
            'user_type': request.session.get('user_type'),
            'first_name': request.session.get('first_name', ''),
            'last_name': request.session.get('last_name', ''),
        }
        
        # Tạo full_name
        full_name = f"{context['first_name']} {context['last_name']}".strip()
        context['full_name'] = full_name or context['username']
        
        # Query chỉ dữ liệu KHÔNG có trong session
        with connection.cursor() as cursor:
            if context['user_type'] == 'student':
                cursor.execute("""
                    SELECT 
                        p.avatar_path,
                        s.coins, 
                        s.student_id, 
                        s.enrollment_year,
                        m.name as major_name
                    FROM profiles p
                    LEFT JOIN students s ON p.id = s.id
                    LEFT JOIN majors m ON s.major_id = m.id
                    WHERE p.id = %s
                """, [user_id])
                
                row = cursor.fetchone()
                if row:
                    context['avatar_path'] = row[0]
                    context['coins'] = row[1] or 0
                    context['student_id'] = row[2]
                    context['enrollment_year'] = row[3]
                    context['major_name'] = row[4]
            
            elif context['user_type'] == 'teacher':
                # Query thông tin giảng viên nếu cần
                cursor.execute("""
                    SELECT 
                        p.avatar_path,
                        t.department,
                        t.title
                    FROM profiles p
                    LEFT JOIN teachers t ON p.id = t.id
                    WHERE p.id = %s
                """, [user_id])
                
                row = cursor.fetchone()
                if row:
                    context['avatar_path'] = row[0]
                    context['department'] = row[1]
                    context['title'] = row[2]
        
        return render(request, 'home/index.html', context)
    
    else:
        # Khách
        context = {'is_authenticated': False}
        
        with connection.cursor() as cursor:
            # Đếm users
            cursor.execute("SELECT COUNT(*) FROM profiles")
            context['user_count'] = cursor.fetchone()[0]
            
            # Lấy user mới nhất (optional)
            cursor.execute("""
                SELECT username, first_name, last_name
                FROM profiles 
                ORDER BY id DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if row:
                context['latest_user'] = {
                    'username': row[0],
                    'full_name': f"{row[1] or ''} {row[2] or ''}".strip() or row[0]
                }
        
        return render(request, 'home/index.html', context)