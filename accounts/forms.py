# accounts/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Profile, Major # Import thêm Major

# --- FORM CẬP NHẬT USER (Họ, Tên) ---
class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False, label="Họ", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, label="Tên", widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name']

# --- FORM CẬP NHẬT PROFILE (Chuyên ngành, Lớp) ---
class ProfileUpdateForm(forms.ModelForm):
    major = forms.ModelChoiceField(
        queryset=Major.objects.all(), 
        required=False, 
        label="Chuyên ngành",
        empty_label="-- Chọn chuyên ngành --",
        widget=forms.Select(attrs={'class': 'form-select'}) # Thêm class Bootstrap
    )
    # student_class = forms.CharField(max_length=50, required=False, label="Lớp", widget=forms.TextInput(attrs={'class': 'form-control'})) # Bỏ comment nếu bạn đã thêm lại trường này vào model

    class Meta:
        model = Profile
        # fields = ['major', 'student_class'] # Bỏ comment student_class nếu dùng
        fields = ['major'] # Chỉ có major nếu student_class bị comment trong model

# --- FORM CẬP NHẬT AVATAR cho sinh vien---
class AvatarUpdateForm(forms.ModelForm):
    # Dùng widget mặc định hoặc tùy chỉnh nếu cần
    avatar = forms.ImageField(required=True, label="Chọn ảnh đại diện mới") 

    class Meta:
        model = Profile
        fields = ['avatar']


# accounts/forms.py
from django import forms
from django.contrib.auth.models import User
# Import các model mới
from .models import Profile, Major, TeacherProfile, Faculty
# Import model Subject
from forum.models import Subject

# ... (UserUpdateForm, ProfileUpdateForm, AvatarUpdateForm giữ nguyên) ...

# 4. FORM MỚI CHO CẬP NHẬT HỒ SƠ GIẢNG VIÊN
class TeacherProfileForm(forms.ModelForm):
    # Lấy danh sách Khoa
    faculty = forms.ModelChoiceField(
        queryset=Faculty.objects.all(),
        required=False,
        label="Khoa",
        empty_label="-- Chọn Khoa --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Dùng lựa chọn từ model
    degree = forms.ChoiceField(
        choices=TeacherProfile.DEGREE_CHOICES,
        required=False,
        label="Học vị",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    position = forms.CharField(
        max_length=100, 
        required=False, 
        label="Chức danh",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    experience_years = forms.IntegerField(
        min_value=0, 
        required=False, 
        label="Năm kinh nghiệm",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    # Trường chọn nhiều môn học
    subjects_taught = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}), # Hiển thị 5 dòng
        label="Môn học giảng dạy"
    )

    class Meta:
        model = TeacherProfile
        fields = ['faculty', 'degree', 'position', 'experience_years', 'subjects_taught']


class TeacherAvatarUpdateForm(forms.ModelForm):
    avatar = forms.ImageField(required=True, label="Chọn ảnh đại diện mới")
    class Meta:
        model = TeacherProfile # <-- Dùng cho GIẢNG VIÊN
        fields = ['avatar']