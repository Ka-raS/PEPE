import os
import hashlib
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.db import connection
from django.http import Http404
from django.shortcuts import render, redirect

from . import sql


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
                sql.update_user_name(first_name, last_name, user_id)

                if user_type == 'student':
                    major_id = request.POST.get('major_id') or None
                    student_code = request.POST.get('student_code').strip() or None
                    enrollment_year = request.POST.get('enrollment_year') or None
                    sql.update_student(user_id, major_id, enrollment_year, student_code)
                
                elif user_type == 'teacher':
                    title = request.POST.get('title', '').strip()
                    degree = request.POST.get('degree', '').strip()
                    department_id = request.POST.get('department') or None
                    teacher_code = request.POST.get('teacher_code').strip() or None
                    sql.update_teacher(user_id, title, teacher_code, degree, department_id)


            messages.success(request, 'Cập nhật thông tin thành công!')
            return redirect('accounts:index')

        except Exception as e:
            messages.error(request, f'Cập nhật thất bại: {e}')

    # --- XỬ LÝ GET (Hiển thị thông tin) ---
    try:
        # Lấy thông tin chung
        user_base = sql.one_user(user_id=user_id)
        if not user_base:
            raise Http404("Môn học không tồn tại")
            
        context['username'] = user_base['username']
        context['email'] = user_base['email']
        context['first_name'] = user_base['first_name'] or ''
        context['last_name'] = user_base['last_name'] or ''
        context['full_name'] = f"{context['first_name']} {context['last_name']}".strip()
        context['avatar_path'] = f"{user_base['avatar_path']}" if user_base['avatar_path'] else None

        if user_type == 'student':
            student_data = sql.one_student(user_id)
            if student_data:
                context['current_major_id'] = student_data['major_id']
                context['major_name'] = student_data['major_name']
                context['enrollment_year'] = student_data['enrollment_year']
                context['student_code'] = student_data['student_code']

            # Lấy danh sách majors
            context['all_major'] = sql.all_major()
            
            # THÊM: Lấy thống kê thực tế cho sinh viên
            # Số bài kiểm tra đã làm
            context['stats']['tests'] = sql.user_submission_count(user_id)
            
            # Số bài đã đăng
            context['stats']['uploads'] = sql.user_post_count(user_id)

            # Lấy hoạt động gần đây thực tế
            recent_activities = []
            for test in sql.user_recent_submissions(user_id, 3):
                recent_activities.append({
                    'icon': 'bi-pencil-square text-success',
                    'text': f'Hoàn thành bài kiểm tra "{test['title']}"',
                    'time': test['created_at']
                })
            
            # Lấy tài liệu tải lên gần đây
            for post in sql.user_recent_posts(user_id, 3):
                recent_activities.append({
                    'icon': 'bi-cloud-upload text-primary',
                    'text': f'Tải lên Bài đăng "{post['title']}"',
                    'time': post['created_at']
                })
                
            # Sắp xếp theo thời gian mới nhất
            recent_activities.sort(key=lambda x: x['time'], reverse=True)
            context['recent_activities'] = recent_activities[:3]  # Lấy 3 hoạt động gần nhất

        elif user_type == 'teacher':
            # Lấy dữ liệu GIẢNG VIÊN
            teacher_data = sql.one_teacher(user_id)
            if teacher_data:
                context['title'] = teacher_data['title']
                context['current_department_id'] = teacher_data['department_id']
                context['department_name'] = teacher_data['department_name']
                context['degree'] = teacher_data['degree']
                context['teacher_code'] = teacher_data['teacher_code']
            
            # Lấy danh sách departments
            context['all_departments'] = sql.all_department()
            
            # THÊM: Lấy thống kê thực tế cho giảng viên
            # Số bài kiểm tra đã tạo
            context['stats']['tests'] = sql.user_test_count(user_id)
            
            # Số tài liệu đã tải lên
            context['stats']['uploads'] = sql.user_post_count(user_id)

            # THÊM: Lấy hoạt động gần đây thực tế
            recent_activities = []
            
            # Lấy bài kiểm tra tạo gần đây
            for test in sql.user_recent_tests(user_id, 3):
                recent_activities.append({
                    'icon': 'bi-plus-circle text-success',
                    'text': f'Tạo bài kiểm tra "{test['title']}"',
                    'time': test['created_at']
                })
            
            for post in sql.user_recent_posts(user_id, 3):
                recent_activities.append({
                    'icon': 'bi-cloud-upload text-primary',
                    'text': f'Tải lên Bài đăng "{post['title']}"',
                    'time': post['created_at']
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
    user_type          = request.POST.get('user_type')
    
    # Validation
    if password != password_confirm:
        messages.error(request, 'Mật khẩu không khớp')
        return render(request, 'accounts/register.html')
    
    if len(password) < 6:
        messages.error(request, 'Mật khẩu phải có ít nhất 6 ký tự')
        return render(request, 'accounts/register.html')
    
    hashed_password = hash_password(password)
    
    try:
        # Kiểm tra user đã tồn tại
        if sql.is_user_exist(username, email):
            messages.error(request, 'Tên đăng nhập hoặc email đã tồn tại')
            return render(request, 'accounts/register.html')
        
        # Tạo profile mới
        sql.insert_user(username, email, hashed_password, first_name, last_name, user_type)

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
    user_data = sql.one_user(username=username)
        
    if not user_data or not verify_password(password, user_data['password']):
        messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng')
        return render(request, 'accounts/login.html')
    
    # Lưu thông tin user vào session
    request.session['is_authenticated'] = request.session.get('user_id') is not None
    request.session['user_id']   = user_data['id']
    request.session['username']  = user_data['username']
    request.session['email']     = user_data['email']
    request.session['user_type'] = 'student' if sql.one_student(user_data['id']) else 'teacher'

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
        user_data = sql.one_user(user_id=user_id)
        if user_data and user_data['avatar_path']:        
            old_path = settings.MEDIA_ROOT / user_data['avatar_path']
            if old_path.exists():
                try:
                    os.remove(old_path)
                except:
                    pass
        
        # Lưu file mới
        full_path = default_storage.save(str(file_path), avatar_file)
        sql.update_user_avatar(settings.MEDIA_URL + full_path, user_id)
        
        messages.success(request, 'Cập nhật ảnh đại diện thành công!')
        
    except Exception as e:
        messages.error(request, f'Lỗi khi tải ảnh: {str(e)}')

    return redirect('accounts:index')