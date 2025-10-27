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

# --- FORM CẬP NHẬT AVATAR ---
class AvatarUpdateForm(forms.ModelForm):
    # Dùng widget mặc định hoặc tùy chỉnh nếu cần
    avatar = forms.ImageField(required=True, label="Chọn ảnh đại diện mới") 

    class Meta:
        model = Profile
        fields = ['avatar']