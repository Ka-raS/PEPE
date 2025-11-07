import os

from django import forms
from django.conf import settings
from django.forms import inlineformset_factory
from .models import Post, Subject, Test, Quiz, Question, Option

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'subject', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập tiêu đề bài viết...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập nội dung bài viết...',
                'rows': 10
            }),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.txt,.zip,.rar'
            })
        }
        labels = {
            'title': 'Tiêu đề',
            'content': 'Nội dung',
            'subject': 'Môn học',
            'attachment': 'File đính kèm'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject'].queryset = Subject.objects.all()
        
    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            if attachment.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
                raise forms.ValidationError(f"File không được lớn hơn {settings.FILE_UPLOAD_MAX_MEMORY_SIZE / (1024 ** 2)}MB.")
            
            # Kiểm tra phần mở rộng
            allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.zip', '.rar']
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    f"Chỉ chấp nhận các file: {', '.join(allowed_extensions)}"
                )
        return attachment
class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['title', 'description', 'subject', 'file', 'time_limit', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập tiêu đề bài kiểm tra...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Mô tả bài kiểm tra...',
                'rows': 4
            }),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.txt'
            }),
            'time_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Thời gian làm bài (phút)'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }
        labels = {
            'title': 'Tiêu đề',
            'description': 'Mô tả',
            'subject': 'Môn học',
            'file': 'File bài kiểm tra',
            'time_limit': 'Thời gian làm bài (phút)',
            'due_date': 'Hạn nộp bài'
        }

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'subject', 'time_limit']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập tiêu đề bài trắc nghiệm...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Mô tả bài trắc nghiệm...',
                'rows': 4
            }),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'time_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Thời gian làm bài (phút)'
            })
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'explanation', 'order']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control question-text',
                'placeholder': 'Nhập câu hỏi...',
                'rows': 3
            }),
            'question_type': forms.Select(attrs={'class': 'form-control question-type'}),
            'explanation': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Giải thích đáp án (tùy chọn)...',
                'rows': 2
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control order-input',
                'min': 1
            })
        }

class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ['text', 'is_correct', 'order']
        widgets = {
            'text': forms.TextInput(attrs={
                'class': 'form-control option-text',
                'placeholder': 'Nhập lựa chọn...'
            }),
            'is_correct': forms.CheckboxInput(attrs={
                'class': 'form-check-input correct-option'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control option-order',
                'min': 1
            })
        }

# Tạo formsets
QuestionFormSet = inlineformset_factory(
    Quiz, Question,
    form=QuestionForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)

OptionFormSet = inlineformset_factory(
    Question, Option,
    form=OptionForm,
    extra=4,
    max_num=6,
    can_delete=True
)