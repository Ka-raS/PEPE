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
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')

    user_type = request.session.get('user_type')
    
    if user_type == 'student':
        return redirect('accounts:index_student')
    elif user_type == 'teacher':
        return redirect('accounts:index_teacher')
    
    messages.error(request, 'Loại tài khoản không hợp lệ')
    return redirect('accounts:logout')

# context:
#  profile,
#  avatar_path (có thể None),
#  full_name (first_name + first_name, None được),
#  username,
#  major (kéo từ database bằng major_id, None được)
#  email
#  all_majors (select name from bảng majors)

def index_student(request):
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    if request.session.get('user_type') != 'student':
        messages.error(request, 'Chỉ sinh viên mới có quyền truy cập')
        return redirect('home:index')
    
    user_id = request.session.get('user_id')
    
    # Xử lý POST - cập nhật thông tin
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        major_id = request.POST.get('major_id')
        
        # Tách first_name và last_name
        name_parts = full_name.split(' ', 1) if full_name else ['', '']
        first_name = name_parts[0] if len(name_parts) > 0 else None
        last_name = name_parts[1] if len(name_parts) > 1 else None
        
        with connection.cursor() as cursor:
            # Cập nhật users
            cursor.execute("""
                UPDATE users 
                SET first_name = %s, last_name = %s
                WHERE id = %s
            """, [first_name, last_name, user_id])
            
            # Cập nhật hoặc insert students
            cursor.execute("""
                SELECT id 
                FROM students 
                WHERE id = %s
            """, [user_id])
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE students 
                    SET major_id = %s
                    WHERE id = %s
                """, [major_id if major_id else None, user_id])
            else:
                cursor.execute("""
                    INSERT INTO students (id, major_id) 
                    VALUES (%s, %s)
                """, [user_id, major_id if major_id else None])
        
        messages.success(request, 'Cập nhật thông tin thành công!')
        return redirect('accounts:index_student')
    
    # GET - lấy dữ liệu hiển thị
    context = {'is_authenticated': request.session.get('user_id') is not None}

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                u.username, u.email, u.first_name, u.last_name, u.avatar_path,
                COALESCE(s.coins, 0) AS coins,
                s.major_id,
                m.name AS major_name
            FROM users u
            LEFT JOIN students s ON u.id = s.id
            LEFT JOIN majors m ON s.major_id = m.id
            WHERE u.id = %s
        """, [user_id])
        data = cursor.fetchone()
        
        # Lấy danh sách majors
        cursor.execute("SELECT * FROM majors ORDER BY name")
        context['all_major'] = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

    # Xử lý dữ liệu
    context['username']         = data[0] 
    context['email']            = data[1] 
    context['first_name']       = data[2] or ''
    context['last_name']        = data[3] or ''
    context['full_name']        = f"{context['first_name']} {context['last_name']}".strip()
    context['avatar_path']      = data[4]
    context['coins']            = data[5]
    context['current_major_id'] = data[6]
    context['major_name']       = data[7]

    context['tests_taken']      = 0
    context['uploads_count']    = 0

    # with connection.cursor() as cursor:
    #     # Giả sử bạn có bảng 'forum_testsubmission'
    #     sql_tests = "SELECT COUNT(id) FROM forum_testsubmission WHERE user_id = %s"
    #     cursor.execute(sql_tests, [user_id])
    #     tests_row = cursor.fetchone()
    #     if tests_row:
    #         tests_taken = tests_row[0]

    return render(request, 'accounts/index_student.html', context)

def index_teacher(request):
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    user_id = request.session.get('user_id')

    # POST: cập nhật thông tin giáo viên
    if request.method == 'POST':
        full_name = request.POST.get('full_name','').strip()
        title = request.POST.get('title', '').strip()
        department_id = request.POST.get('department') or None

        # Tách first_name và last_name
        name_parts = full_name.split(' ', 1) if full_name else ['', '']
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        try:
            with connection.cursor() as cursor:
                # Cập nhật profiles
                cursor.execute("""
                    UPDATE profiles
                    SET first_name = %s, last_name = %s
                    WHERE id = %s
                """, [first_name, last_name, user_id])

                # Kiểm tra và insert/update teachers
                cursor.execute("SELECT id FROM teachers WHERE id = %s", [user_id])
                if cursor.fetchone():
                    cursor.execute("""
                        UPDATE teachers
                        SET title = %s, department_id = %s
                        WHERE id = %s
                    """, [title, department_id, user_id])
                else:
                    cursor.execute("""
                        INSERT INTO teachers (id, title, department_id)
                        VALUES (%s, %s, %s)
                    """, [user_id, title, department_id])

            messages.success(request, 'Cập nhật thông tin giáo viên thành công!')
            return redirect('accounts:index_teacher')
        except Exception as e:
            messages.error(request, f'Cập nhật thất bại: {e}')

    # GET: lấy dữ liệu hiển thị
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                p.username, p.email, p.first_name, p.last_name,
                t.title, t.department_id, d.name AS department_name
            FROM profiles p
            LEFT JOIN teachers t ON p.id = t.id
            LEFT JOIN departments d ON t.department_id = d.id
            WHERE p.id = %s
        """, [user_id])
        data = cursor.fetchone()

        # Lấy danh sách tất cả khoa
        cursor.execute("SELECT id, name FROM departments ORDER BY name")
        all_departments = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

    # Xử lý dữ liệu
    username = data[0] if data else ''
    email = data[1] if data else ''
    first_name = data[2] if data else ''
    last_name = data[3] if data else ''
    full_name = f"{first_name} {last_name}".strip() if first_name or last_name else ''
    title = data[4] if data else ''
    current_department_id = data[5] if data else None
    department_name = data[6] if data else ''

    # TODO
    uploads_count = 0
    coins = 0
    tests_taken = 0

    context = {
        'is_authenticated': request.session.get('user_id') is not None,
        'username': username,
        'email': email,
        'full_name': full_name,
        'first_name': first_name,
        'last_name': last_name,
        'title': title,
        'current_department_id': current_department_id,
        'department_name': department_name,
        'all_departments': all_departments,
        'uploads_count': uploads_count,
        'coins': coins,
        'tests_taken': tests_taken,
    }

    return render(request, 'accounts/index_teacher.html', context)


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
        file_name = f"avatar_{user_id}_{hash(avatar_file.name)}{file_ext}"
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
    
    return redirect('accounts:index_student')