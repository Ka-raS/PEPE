from django.shortcuts import render
from django.db import connection
from django.shortcuts import render
from django.db import connection

def index(request):
    # Kiểm tra session thay vì request.user
    user_id = request.session.get('user_id')
    
    if user_id:
        # Người dùng đã đăng nhập
        context = {'is_authenticated': True}
        
        with connection.cursor() as cursor:
            # Query user data với JOIN
            cursor.execute("""
                SELECT 
                    p.id, p.username, p.email, p.first_name, p.last_name, 
                    p.user_type, p.avatar_path,
                    s.coins, s.student_id, s.enrollment_year,
                    m.name as major_name
                FROM profiles p
                LEFT JOIN students s ON p.id = s.id
                LEFT JOIN majors m ON s.major_id = m.id
                WHERE p.id = %s
            """, [user_id])
            
            row = cursor.fetchone()
            
            if row:
                # Parse data từ tuple
                context['user_id'] = row[0]
                context['username'] = row[1]
                context['email'] = row[2]
                context['first_name'] = row[3] or ''
                context['last_name'] = row[4] or ''
                context['user_type'] = row[5]
                context['avatar_path'] = row[6]
                
                # Tạo full_name
                context['full_name'] = f"{row[3] or ''} {row[4] or ''}".strip() or row[1]
                
                # Nếu là student
                if row[5] == 'student':
                    context['coins'] = row[7] or 0
                    context['student_id'] = row[8]
                    context['enrollment_year'] = row[9]
                    context['major_name'] = row[10]
                
                # # Check điểm danh hôm nay
                # from datetime import date
                # today = date.today()
                # cursor.execute("""
                #     SELECT id FROM checkins 
                #     WHERE user_id = %s AND checkin_date = %s
                # """, [user_id, today])
                # context['can_checkin'] = cursor.fetchone() is None
        print(context)
        
        return render(request, 'home/index.html', context)
    
    else:
        # Khách
        context = {'is_authenticated': False}
        
        with connection.cursor() as cursor:
            # Đếm users
            cursor.execute("SELECT COUNT(*) FROM profiles")
            user_count = cursor.fetchone()[0]
            
            # Lấy user mới nhất
            cursor.execute("""
                SELECT id, username, email, first_name, last_name 
                FROM profiles 
                ORDER BY id DESC 
                LIMIT 1
            """)
            latest_user_row = cursor.fetchone()
            
            latest_user = None
            if latest_user_row:
                latest_user = {
                    'id': latest_user_row[0],
                    'username': latest_user_row[1],
                    'email': latest_user_row[2],
                    'first_name': latest_user_row[3],
                    'last_name': latest_user_row[4],
                }
        
        context['user_count'] = user_count
        context['latest_user'] = latest_user
        
        return render(request, 'home/index.html', context)