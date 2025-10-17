from django.db import models
from django.contrib.auth.models import User

# --- Bảng 1: Chuyên mục Diễn đàn ---
# Phải được định nghĩa đầu tiên vì Forum sẽ tham chiếu đến nó.
# Ví dụ: "Học tập & Ôn tập", "Tài liệu & Bài giảng"
class ForumSection(models.Model):
    title = models.CharField(
        "Tên chuyên mục", 
        max_length=150,
        default="Chuyên mục chung" # Thêm default để tránh lỗi khi migrate
    )
    
    def __str__(self):
        return self.title

# --- Bảng 2: Diễn đàn con ---
# Phải được định nghĩa sau ForumSection và trước Post.
# Ví dụ: "Toán cao cấp", "Lập trình Python"
class Forum(models.Model):
    section = models.ForeignKey(
        ForumSection, 
        on_delete=models.CASCADE, 
        verbose_name="Chuyên mục"
    )
    title = models.CharField("Tên diễn đàn", max_length=200)
    description = models.TextField("Mô tả", blank=True, null=True)

    def __str__(self):
        return self.title
    
    # Hàm để lấy bài viết mới nhất trong diễn đàn này
    def get_latest_post(self):
        return self.post_set.order_by('-created_at').first()

    # Hàm để đếm số lượng chủ đề (bài đăng)
    def get_thread_count(self):
        return self.post_set.count()

# --- Bảng 3: Bài đăng (Chủ đề) ---
# Được định nghĩa cuối cùng vì nó tham chiếu đến Forum và User.
# Ví dụ: "Hỏi về tích phân ba lớp", "Tài liệu ôn thi cuối kỳ"
class Post(models.Model):
    forum = models.ForeignKey(
        Forum, 
        on_delete=models.CASCADE, 
        verbose_name="Diễn đàn"
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        verbose_name="Tác giả"
    )
    title = models.CharField("Tiêu đề", max_length=255)
    content = models.TextField("Nội dung", default="") # Thêm trường nội dung cho bài viết
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)

    def __str__(self):
        return self.title