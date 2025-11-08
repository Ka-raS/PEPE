import hashlib
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.db import connection
from django.shortcuts import render, redirect

# index, 
# wallet ưu tiên thấp
# referral ưu tiên thấp
# checkin_view ưu tiên thấp

# login_view xong
# register_view xong
# logout_view xong

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def index(request): 
    # Kiểm tra session
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    context = {
        'is_authenticated': True,
        'user_type': user_type,
        'user_id': user_id,
        'username': request.session.get('username'),
        'email': request.session.get('email', ''),
        'avatar_path': None,
        'full_name': '',
        'all_major': [],
        'all_departments': [],
        'all_subjects': [],
        'current_subject_ids': set(),
        'subjects_taught_names': [],
        'recent_activities': [],  # THÊM: Danh sách hoạt động gần đây
        'stats': {'uploads': 0, 'tests': 0}
    }

    # --- XỬ LÝ POST (Cập nhật thông tin) ---
    if request.method == 'POST':
        full_name = request.POST.get('full_name','').strip()
        name_parts = full_name.split(' ', 1) if full_name else ['', '']
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        try:
            with connection.cursor() as cursor:
                # 1. Cập nhật bảng 'users' (chung cho cả 2)
                cursor.execute("""
                    UPDATE users 
                    SET first_name = %s, last_name = %s 
                    WHERE id = %s
                """, [first_name, last_name, user_id])

                # 2. Cập nhật bảng riêng (students hoặc teachers)
                if user_type == 'student':
                    major_id = request.POST.get('major_id') or None
                    enrollment_year = request.POST.get('enrollment_year') or None
                    
                    cursor.execute("SELECT id FROM students WHERE id = %s", [user_id])
                    if cursor.fetchone():
                        cursor.execute("""
                            UPDATE students 
                            SET major_id = %s, enrollment_year = %s 
                            WHERE id = %s
                        """, [major_id, enrollment_year, user_id])
                    else:
                        cursor.execute("""
                            INSERT INTO students (id, major_id, enrollment_year) 
                            VALUES (%s, %s, %s)
                        """, [user_id, major_id, enrollment_year])
                
                elif user_type == 'teacher':
                    title = request.POST.get('title', '').strip()
                    department_id = request.POST.get('department') or None
                    subjects_taught_ids = request.POST.getlist('subjects_taught')
                    
                    cursor.execute("SELECT id FROM teachers WHERE id = %s", [user_id])
                    if cursor.fetchone():
                        cursor.execute("""
                            UPDATE teachers SET title = %s, department_id = %s WHERE id = %s
                        """, [title, department_id, user_id])
                    else:
                        cursor.execute("""
                            INSERT INTO teachers (id, title, department_id) VALUES (%s, %s, %s, %s)
                        """, [user_id, title, department_id])
                    
                    # Cập nhật bảng N-N teacher_subjects
                    cursor.execute("DELETE FROM teacher_subjects WHERE teacher_id = %s", [user_id])
                    if subjects_taught_ids:
                        insert_data = [(user_id, subject_id) for subject_id in subjects_taught_ids if subject_id]
                        cursor.executemany("""
                            INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (%s, %s)
                        """, insert_data)

            messages.success(request, 'Cập nhật thông tin thành công!')
            return redirect('accounts:index')

        except Exception as e:
            messages.error(request, f'Cập nhật thất bại: {e}')

    # --- XỬ LÝ GET (Hiển thị thông tin) ---
    try:
        with connection.cursor() as cursor:
            # Lấy thông tin chung
            cursor.execute("SELECT username, email, first_name, last_name, avatar_path FROM users WHERE id = %s", [user_id])
            user_base = cursor.fetchone()
            if user_base:
                context['username'] = user_base[0]
                context['email'] = user_base[1]
                context['first_name'] = user_base[2] or ''
                context['last_name'] = user_base[3] or ''
                context['full_name'] = f"{context['first_name']} {context['last_name']}".strip()
                context['avatar_path'] = f"{user_base[4]}" if user_base[4] else None

            if user_type == 'student':
                # Lấy dữ liệu SINH VIÊN
                cursor.execute("""
                    SELECT s.major_id, m.name AS major_name, s.enrollment_year
                    FROM students s
                    LEFT JOIN majors m ON s.major_id = m.id
                    WHERE s.id = %s
                """, [user_id])
                student_data = cursor.fetchone()
                if student_data:
                    context['current_major_id'] = student_data[0]
                    context['major_name'] = student_data[1]
                    context['year_of_study'] = student_data[2]

                # Lấy danh sách majors
                cursor.execute("SELECT id, name FROM majors ORDER BY name")
                context['all_major'] = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
                
                # THÊM: Lấy thống kê thực tế cho sinh viên
                # Số bài kiểm tra đã làm
                cursor.execute("SELECT COUNT(*) FROM submissions WHERE author_id = %s", [user_id])
                tests_taken = cursor.fetchone()[0] or 0
                context['stats']['tests'] = tests_taken
                
                # Số tài liệu đã tải lên
                cursor.execute("SELECT COUNT(*) FROM posts WHERE author_id = %s", [user_id])
                uploads_count = cursor.fetchone()[0] or 0
                context['stats']['uploads'] = uploads_count

                # THÊM: Lấy hoạt động gần đây thực tế
                recent_activities = []
                
                # Lấy bài kiểm tra gần đây
                cursor.execute("""
                    SELECT t.title, s.submitted_at 
                    FROM submissions s
                    JOIN tests t ON s.test_id = t.id
                    WHERE s.author_id = %s
                    ORDER BY s.submitted_at DESC
                    LIMIT 3
                """, [user_id])
                recent_tests = cursor.fetchall()
                for test in recent_tests:
                    recent_activities.append({
                        'icon': 'bi-pencil-square text-success',
                        'text': f'Hoàn thành bài kiểm tra "{test[0]}"',
                        'time': test[1]
                    })
                
                # Lấy tài liệu tải lên gần đây
                cursor.execute("""
                    SELECT title, created_at 
                    FROM posts
                    WHERE author_id = %s
                    ORDER BY created_at DESC
                    LIMIT 3
                """, [user_id])
                recent_posts = cursor.fetchall()
                for post in recent_posts:
                    recent_activities.append({
                        'icon': 'bi-cloud-upload text-primary',
                        'text': f'Tải lên tài liệu "{post[0]}"',
                        'time': post[1]
                    })
                
                # Sắp xếp theo thời gian mới nhất
                recent_activities.sort(key=lambda x: x['time'], reverse=True)
                context['recent_activities'] = recent_activities[:3]  # Lấy 3 hoạt động gần nhất

            elif user_type == 'teacher':
                # Lấy dữ liệu GIẢNG VIÊN
                cursor.execute("""
                    SELECT t.title, t.department_id, d.name AS department_name
                    FROM teachers t
                    LEFT JOIN departments d ON t.department_id = d.id
                    WHERE t.id = %s
                """, [user_id])
                teacher_data = cursor.fetchone()
                
                if teacher_data:
                    context['title'] = teacher_data[0]
                    context['current_department_id'] = teacher_data[1]
                    context['department_name'] = teacher_data[2]
                
                # Lấy danh sách departments
                cursor.execute("SELECT id, name FROM departments ORDER BY name")
                context['all_departments'] = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
                
                # THÊM: Lấy thống kê thực tế cho giảng viên
                # Số bài kiểm tra đã tạo
                cursor.execute("SELECT COUNT(*) FROM tests WHERE author_id = %s", [user_id])
                tests_created = cursor.fetchone()[0] or 0
                context['stats']['tests'] = tests_created
                
                # Số tài liệu đã tải lên
                cursor.execute("SELECT COUNT(*) FROM posts WHERE author_id = %s", [user_id])
                uploads_count = cursor.fetchone()[0] or 0
                context['stats']['uploads'] = uploads_count

                # THÊM: Lấy hoạt động gần đây thực tế
                recent_activities = []
                
                # Lấy bài kiểm tra tạo gần đây
                cursor.execute("""
                    SELECT title, created_at 
                    FROM tests
                    WHERE author_id = %s
                    ORDER BY created_at DESC
                    LIMIT 3
                """, [user_id])
                recent_tests = cursor.fetchall()
                for test in recent_tests:
                    recent_activities.append({
                        'icon': 'bi-plus-circle text-success',
                        'text': f'Tạo bài kiểm tra "{test[0]}"',
                        'time': test[1]
                    })
                
                # Lấy tài liệu tải lên gần đây
                cursor.execute("""
                    SELECT title, created_at 
                    FROM posts
                    WHERE author_id = %s
                    ORDER BY created_at DESC
                    LIMIT 3
                """, [user_id])
                recent_posts = cursor.fetchall()
                for post in recent_posts:
                    recent_activities.append({
                        'icon': 'bi-cloud-upload text-primary',
                        'text': f'Tải lên tài liệu "{post[0]}"',
                        'time': post[1]
                    })
                
                # Sắp xếp theo thời gian mới nhất
                recent_activities.sort(key=lambda x: x['time'], reverse=True)
                context['recent_activities'] = recent_activities[:3]  # Lấy 3 hoạt động gần nhất
            
    except Exception as e:
        messages.error(request, f"Lỗi khi tải dữ liệu trang: {e}")

    return render(request, 'accounts/index.html', context)


def register_view(request):
    if request.method != 'POST':
        return render(request, 'accounts/register.html')
    
    username           = request.POST.get('username')
    email              = request.POST.get('email')
    password           = request.POST.get('password')
    password_confirm   = request.POST.get('password_confirm')
    first_name         = request.POST.get('first_name') or None
    last_name          = request.POST.get('last_name') or None
    user_type          = request.POST.get('user_type', 'student')
    
    # Validation
    if password != password_confirm:
        messages.error(request, 'Mật khẩu không khớp')
        return render(request, 'accounts/register.html')
    
    if len(password) < 6:
        messages.error(request, 'Mật khẩu phải có ít nhất 6 ký tự')
        return render(request, 'accounts/register.html')
    
    hashed_password = hash_password(password)
    
    try:
        with connection.cursor() as cursor:
            # Kiểm tra username/email đã tồn tại
            cursor.execute("""
                SELECT id 
                FROM users
                WHERE username = %s 
                OR email = %s
            """, [username, email])
            if cursor.fetchone():
                messages.error(request, 'Tên đăng nhập hoặc email đã tồn tại')
                return render(request, 'accounts/register.html')
            
            # Tạo profile mới
            cursor.execute("""
                INSERT INTO users
                    (username, email, password, first_name, last_name, user_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [username, email, hashed_password, first_name, last_name, user_type])
            
        messages.success(request, 'Đăng ký thành công! Vui lòng đăng nhập.')
        return redirect('accounts:login')
        
    except Exception as e:
        messages.error(request, f'Lỗi: {str(e)}')
        return render(request, 'accounts/register.html')    


def login_view(request):
    if request.method != 'POST':
        return render(request, 'accounts/login.html')

    username = request.POST.get('username')
    password = request.POST.get('password')
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, username, password, email, first_name, last_name, user_type 
            FROM users
            WHERE username = %s
        """, [username])
        user_data = cursor.fetchone()
        
    if not user_data or not verify_password(password, user_data[2]):
        messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng')
        return render(request, 'accounts/login.html')
    
    # Lưu thông tin user vào session
    request.session['is_authenticated'] = request.session.get('user_id') is not None
    request.session['user_id']   = user_data[0]
    request.session['username']  = user_data[1]
    request.session['email']     = user_data[3]
    request.session['user_type'] = user_data[6]
    
    messages.success(request, f'Xin chào {request.session['username']}!')
    return redirect('home:index')


def logout_view(request):
    request.session.flush()
    messages.success(request, 'Đã đăng xuất!')
    return redirect('home:index')


def update_avatar(request):
    """Xử lý upload avatar cho student"""
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập')
        return redirect('accounts:login')
    
    if request.method != 'POST':        
        return redirect('accounts:index_student')
    user_id = request.session.get('user_id')
    avatar_file = request.FILES.get('avatar')
    
    if not avatar_file:
        messages.error(request, 'Vui lòng chọn ảnh')
        return redirect('accounts:index_student')
    
    # Validate file
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    file_ext = Path(avatar_file.name).suffix.lower()
    
    if file_ext not in allowed_extensions:
        messages.error(request, 'Chỉ chấp nhận file ảnh (jpg, jpeg, png, gif)')
        return redirect('accounts:index_student')
    
    if avatar_file.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
        messages.error(request, f'Kích thước file không được vượt quá {settings.FILE_UPLOAD_MAX_MEMORY_SIZE // (1024 ** 2)}MB')
        return redirect('accounts:index_student')
    
    try:
        # Tạo tên file unique
        file_name = f"{user_id}_{hash(avatar_file.name)}{file_ext}"
        file_path = Path('avatars') / file_name

        # Xóa avatar cũ nếu có
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT avatar_path 
                FROM users
                WHERE id = %s
            """, [user_id])
            old_avatar = cursor.fetchone()
            
            if old_avatar and old_avatar[0]:
                old_path = settings.MEDIA_ROOT / old_avatar[0]
                if old_path.exists():
                    old_path.unlink()
        
        # Lưu file mới
        full_path = default_storage.save(str(file_path), avatar_file)
        
        # Cập nhật database
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users
                SET avatar_path = %s 
                WHERE id = %s
            """, ['/media/' + full_path, user_id])
        
        messages.success(request, 'Cập nhật ảnh đại diện thành công!')
        
    except Exception as e:
        messages.error(request, f'Lỗi khi tải ảnh: {str(e)}')

    return redirect('accounts:index')