# from django.shortcuts import get_object_or_404, render
# from django.core.paginator import Paginator
# from .models import Forum, Thread

# def forum_view(request, forum_id):
#     # Lấy forum theo ID hoặc trả về 404
#     forum = get_object_or_404(Forum, id=forum_id)
    
#     # Lấy danh sách thread trong forum với pagination
#     thread_list = forum.threads.all()
#     paginator = Paginator(thread_list, 10)  # Hiển thị 10 thread mỗi trang
#     page_number = request.GET.get('page')
#     threads = paginator.get_page(page_number)

#     # Lấy các thông tin bổ sung cho forum
#     latest_posts = forum.latest_posts(5)  # 5 bài post mới nhất
#     recent_posts = forum.new_posts()      # Bài post trong 24h qua

#     context = {
#         'forum': forum,
#         'threads': threads,
#         'latest_posts': latest_posts,
#         'recent_posts': recent_posts,
#     }
    
#     return render(request, 'forum/forum.html', context)

from django.http import HttpResponse

def forum_view(request):
    return HttpResponse("Forum Home Page")