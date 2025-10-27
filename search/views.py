# # search/views.py
# from django.shortcuts import render
# from django.db.models import Q
# from django.core.paginator import Paginator
# from forum.models import Thread, Subject # Import model của bạn
# from django.contrib.auth.models import User
# from urllib.parse import urlparse # Cần để phân tích URL
# from forum.models import Forum  # <-- Import thêm Forum
# from django.contrib.auth.models import User # <-- Import User
# from django.db.models.functions import Lower

# def search_home_view(request):
#     """
#     Xử lý logic cho trang Tìm kiếm Nâng cao.
#     """
#     # 1. Bắt đầu với tất cả các Thread
#     results = Thread.objects.select_related(
#         'forum__subject', 'author'
#     ).all()

#     # 2. Lấy các giá trị lọc từ GET
#     query = request.GET.get('q', '')
#     subject_id = request.GET.get('subject', '')
#     forum_id = request.GET.get('forum', '')
#     author_id = request.GET.get('author', '')
#     date_from = request.GET.get('date_from', '')
#     date_to = request.GET.get('date_to', '')
#     sort_by = request.GET.get('sort', 'newest')

#     # 3. Áp dụng các bộ lọc
#     if query:
#         results = results.filter(
#             Q(title__icontains=query) | Q(content__icontains=query)
#         )
#     if subject_id:
#         results = results.filter(forum__subject_id=subject_id)
#     if forum_id:
#         results = results.filter(forum_id=forum_id)
#     if author_id:
#         results = results.filter(author_id=author_id)
#     if date_from:
#         results = results.filter(created_at__gte=date_from)
#     if date_to:
#         results = results.filter(created_at__lte=date_to)

#     # 4. Sắp xếp (Đã cập nhật)
#     if sort_by == 'oldest':
#         results = results.order_by('created_at')
#     elif sort_by == 'a-z':
#         results = results.order_by(Lower('title'))  # <-- Sắp xếp A-Z
#     elif sort_by == 'z-a':
#         results = results.order_by(Lower('title').desc())  # <-- Sắp xếp Z-A
#     else: # Mặc định là 'newest'
#         results = results.order_by('-created_at')
    
#     # Áp dụng distinct() sau khi lọc
#     results = results.distinct()

#     # 5. Phân trang
#     paginator = Paginator(results, 10)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
    
#     # 6. Lấy dữ liệu cho các dropdown trong bộ lọc
#     context = {
#         'results': page_obj,
#         'all_subjects': Subject.objects.all(),
#         'all_forums': Forum.objects.all(),
#         'all_authors': User.objects.filter(is_active=True).order_by('username'),
#     }

#     return render(request, 'search/search_home.html', context)