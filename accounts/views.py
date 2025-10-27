from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.utils import timezone

def index(request):
    return render(request, 'accounts/index.html')

def wallet(request):
    return render(request, 'accounts/wallet.html')

def referral(request):
    return render(request, 'accounts/referral.html')

def login_view(request):
    if request.method == 'POST':
        # 1. Đây là khi user nhấn nút submit
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, 'Vui lòng nhập tên đăng nhập và mật khẩu.')
            return render(request, 'accounts/login.html')

        # 2. Xác thực
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # 3. Đăng nhập
            login(request, user)
            # 4. Chuyển hướng về trang chủ
            return redirect('home:index') 
        else:
            # 5. Báo lỗi
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không chính xác.')
            return render(request, 'accounts/login.html')

    else:
        # 2. Đây là khi user mới vào trang (GET request)
        #    Chỉ cần hiển thị template
        return render(request, 'accounts/login.html')

# API mà JavaScript sẽ gọi
def register_view(request):
    if request.method != 'POST':
        return render(request, 'accounts/register.html')
    
    # Nếu là POST (user đã nhấn nút submit)

    # 1. Lấy dữ liệu từ form (dùng request.POST)
    username = request.POST.get('username')
    email = request.POST.get('email')
    password = request.POST.get('password')
    password_confirm = request.POST.get('password_confirm')
    first_name = request.POST.get('first_name', '')
    last_name = request.POST.get('last_name', '')

    # 2. Xác thực (Validation)
    has_errors = False
    
    if not username:
        messages.error(request, 'Tên đăng nhập là bắt buộc.')
        has_errors = True
    if not email:
        messages.error(request, 'Email là bắt buộc.')
        has_errors = True
    if not password:
        messages.error(request, 'Mật khẩu là bắt buộc.')
        has_errors = True
    if len(password) < 6:
        messages.error(request, 'Mật khẩu phải có ít nhất 6 ký tự.')
        has_errors = True
    if password != password_confirm:
        messages.error(request, 'Mật khẩu không khớp.')
        has_errors = True
    
    # Kiểm tra username đã tồn tại
    if User.objects.filter(username=username).exists():
        messages.error(request, 'Tên đăng nhập này đã được sử dụng.')
        has_errors = True

    # Kiểm tra email hợp lệ và đã tồn tại
    try:
        validate_email(email)
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Địa chỉ email này đã được đăng ký.')
            has_errors = True
    except ValidationError:
        messages.error(request, 'Vui lòng nhập một địa chỉ email hợp lệ.')
        has_errors = True

    # 3. Nếu có lỗi, render lại trang và hiển thị lỗi
    if has_errors:
        # Dữ liệu cũ sẽ không bị mất (nhưng bạn cần thêm
        # value="{{ request.POST.username }}" vào thẻ input nếu muốn)
        return render(request, 'accounts/register.html')
    
    # 4. Nếu không có lỗi, tạo User
    user = User.objects.create_user(username=username, email=email, password=password)
    user.first_name = first_name
    user.last_name = last_name
    user.save()

    # 5. Gửi thông báo thành công và chuyển hướng
    messages.success(request, 'Đăng ký thành công! Vui lòng đăng nhập.')
    return redirect('accounts:login') # Chuyển về trang login
    
def logout_view(request):
    logout(request)
    messages.success(request, "Bạn đã đăng xuất thành công.")
    return redirect('home:index') # Chuyển hướng về trang chủ

@login_required
@require_POST # Chỉ cho phép truy cập bằng POST
def checkin_view(request):
    # Lấy profile, tự động tạo nếu chưa có
    profile = request.user.profile
    today = timezone.now().date()
    COIN_REWARD = 10 

    # 1. Kiểm tra logic
    if profile.last_checkin == today:
        # Gửi thông báo lỗi
        messages.error(request, 'Bạn đã điểm danh hôm nay rồi!')
    else:
        # 2. Cộng coin, cập nhật ngày và lưu
        profile.coins += COIN_REWARD
        profile.last_checkin = today
        profile.save()
        # Gửi thông báo thành công
        messages.success(request, f'Bạn đã điểm danh thành công và nhận được {COIN_REWARD} coin!')

    # 3. Luôn luôn chuyển hướng về trang chủ
    # Trình duyệt sẽ tải lại trang chủ
    return redirect('home:index')