from django.shortcuts import render
from django.contrib.auth.models import User
from django.utils import timezone

from .models import ForumSection, Post
from accounts.models import Profile

def index(request):
    if request.user.is_authenticated:
        # === Xử lý cho người dùng đã đăng nhập ===
        profile, created = Profile.objects.get_or_create(user=request.user)
        can_checkin = not profile.last_checkin == timezone.now().date()

        # Lấy dữ liệu riêng cho dashboard
        # user_major = profile.major
        # suggested_items = Document.objects.none()
        # if user_major:
        #     suggested_items = Document.objects.filter(major=user_major).order_by('-uploaded_at')[:5]

        # Lấy dữ liệu bài đăng (dùng Thread)
        # latest_threads = Thread.objects.select_related('author', 'forum').order_by('-created_at')[:5]
        # featured_threads = Thread.objects.select_related('author', 'forum').filter(is_featured=True).order_by('-created_at')[:5]

        # TẠO CONTEXT HOÀN CHỈNH
        context = {
            'profile': profile,
            'can_checkin': can_checkin,
            # 'suggested_items': suggested_items,
            # 'latest_posts': latest_threads,     # Gửi threads vào biến template
            # 'featured_posts': featured_threads, # Gửi threads vào biến template
            # Thêm các biến khác nếu template cần (ví dụ: thông báo...)
        }
        return render(request, 'home/index.html', context)

    else:
        # === Xử lý cho khách ===
        post_count = Post.objects.count()
        user_count = User.objects.count()
        latest_user = User.objects.order_by('-date_joined').first()

        # latest_threads = Thread.objects.select_related('author', 'forum').order_by('-created_at')[:5]
        # featured_threads = Thread.objects.select_related('author', 'forum').filter(is_featured=True).order_by('-created_at')[:5]

        context = {
            'post_count': post_count,
            'user_count': user_count,
            'latest_user': latest_user,
        
            # 'trending_posts': featured_threads, # Gửi featured threads vào biến template
            # 'latest_posts': latest_threads,     # Gửi latest threads vào biến template
        }
        return render(request, 'home/index.html', context)