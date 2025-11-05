from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# class Profile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     coins = models.IntegerField(default=10)
#     last_checkin = models.DateField(null=True, blank=True)

#     def __str__(self):
#         return f'{self.user.username} Profile'

# # == Rất quan trọng: Tự động tạo Profile khi User được tạo ==
# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)

# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     instance.profile.save()

# from django.db import models
# from django.contrib.auth.models import AbstractUser

# class Account(AbstractUser):
#     USER_TYPE_CHOICES = (
#         ('student', 'Student'),
#         ('teacher', 'Teacher'),
#     )
    
#     # Thêm các trường mới
#     user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
#     is_admin = models.BooleanField(default=False)
    
#     # Ghi đè các trường cần thiết
#     email = models.EmailField(unique=True)
#     first_name = models.CharField(max_length=100, blank=True)
#     last_name = models.CharField(max_length=100, blank=True)

#     class Meta:
#         db_table = 'users'

# class Major(models.Model):
#     name = models.CharField(max_length=100)
    
#     class Meta:
#         db_table = 'majors'
    
#     def __str__(self):
#         return self.name

# class Department(models.Model):
#     name = models.CharField(max_length=100)
    
#     class Meta:
#         db_table = 'departments'
    
#     def __str__(self):
#         return self.name

# class Student(models.Model):
#     user = models.OneToOneField(
#         Account, 
#         on_delete=models.CASCADE, 
#         primary_key=True
#     )
#     student_id = models.CharField(max_length=20, unique=True)
#     enrollment_year = models.IntegerField()
#     major = models.ForeignKey(
#         Major, 
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True
#     )
    
#     class Meta:
#         db_table = 'students'
    
#     def __str__(self):
#         return self.student_id

# class Teacher(models.Model):
#     user = models.OneToOneField(
#         Account, 
#         on_delete=models.CASCADE, 
#         primary_key=True
#     )
#     teacher_id = models.CharField(max_length=20, unique=True)
#     title = models.CharField(max_length=100, blank=True)
#     department = models.ForeignKey(
#         Department, 
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True
#     )
    
#     class Meta:
#         db_table = 'teachers'
    
#     def __str__(self):
#         return self.teacher_id