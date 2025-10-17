from django.shortcuts import render
from django.contrib.auth.models import User

from .models import ForumSection, Post

def home_view(request):
    """
    View này chịu trách nhiệm lấy và hiển thị tất cả dữ liệu
    cho trang chủ PEPE.
    """
    # 1. Lấy tất cả các chuyên mục và các diễn đàn con liên quan
    # prefetch_related giúp tối ưu hóa, giảm số lượng truy vấn CSDL
    sections = ForumSection.objects.prefetch_related('forum_set').all()
    
    # 2. Lấy dữ liệu cho hộp thống kê
    post_count = Post.objects.count()
    user_count = User.objects.count()
    latest_user = User.objects.order_by('-date_joined').first() # Lấy user mới nhất
    
    # 3. Lấy dữ liệu cho hộp "Nội dung nổi bật"
    # Ví dụ: Lấy 5 bài viết mới nhất
    trending_posts = Post.objects.select_related('author', 'forum').order_by('-created_at')[:5]

    # 4. Đóng gói tất cả dữ liệu vào một biến 'context' để gửi ra template
    context = {
        'sections': sections,
        'post_count': post_count,
        'user_count': user_count,
        'latest_user': latest_user,
        'trending_posts': trending_posts,
    }
    
    # 5. Render file HTML và gửi context kèm theo
    return render(request, 'home/home.html', context)
