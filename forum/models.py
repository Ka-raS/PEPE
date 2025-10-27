import os

from django.db import models
from django.contrib.auth.models import User

class Subject(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    attachment = models.FileField(
        upload_to='post_attachments/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='File đính kèm'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    def filename(self):
        """Lấy tên file từ đường dẫn"""
        if self.attachment:
            return os.path.basename(self.attachment.name)
        return None

    def file_extension(self):
        """Lấy phần mở rộng của file"""
        if self.attachment:
            filename = self.filename()
            return filename.split('.')[-1].lower() if '.' in filename else ''
        return ''

    class Meta:
        ordering = ['-created_at']

class Test(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    file = models.FileField(upload_to='tests/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Quiz(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField()
    time_limit = models.IntegerField(help_text="Thời gian làm bài (phút)", default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    QUESTION_TYPES = [
        ('multiple_choice', 'Trắc nghiệm'),
        ('true_false', 'Đúng/Sai'),
        ('short_answer', 'Trả lời ngắn'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    text = models.TextField()
    explanation = models.TextField(blank=True, help_text="Giải thích đáp án")
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - Câu {self.order}"

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)  # Thêm trường order
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title}"

class UserAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.attempt.user.username} - {self.question.text[:50]}"
# Trong models.py, cập nhật model Test
class Test(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    file = models.FileField(upload_to='tests/')
    time_limit = models.IntegerField(
        help_text="Thời gian làm bài (phút)", 
        default=60,
        blank=True,
        null=True
    )
    due_date = models.DateTimeField(
        help_text="Hạn nộp bài",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def is_active(self):
        """Kiểm tra xem bài kiểm tra còn hiệu lực không"""
        if self.due_date:
            from django.utils import timezone
            return timezone.now() <= self.due_date
        return True
    
class TestSubmission(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer_file = models.FileField(upload_to='test_submissions/%Y/%m/%d/')
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    time_spent = models.IntegerField(help_text="Thời gian làm bài (giây)", default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.test.title}"
    
    class Meta:
        ordering = ['-submitted_at']