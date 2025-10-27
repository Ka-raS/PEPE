from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from .models import Subject, Post, Test, Quiz, Question, Option, QuizAttempt, UserAnswer
from .forms import PostForm  
from django.forms import formset_factory

def index(request):
    subjects = Subject.objects.all()
    return render(request, 'forum/index.html', {'subjects': subjects})

def subject_detail(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)
    posts = Post.objects.filter(subject=subject).order_by('-created_at')
    tests = Test.objects.filter(subject=subject).order_by('-created_at')
    quizzes = Quiz.objects.filter(subject=subject, is_published=True).order_by('-created_at')

    context = {
        'subject': subject,
        'posts': posts,
        'tests': tests,
        'quizzes': quizzes,
    }
    return render(request, 'forum/subject_detail.html', context)

@login_required
def create_post(request):
    """Tạo bài viết mới"""
    subject_id = request.GET.get('subject_id')  # Lấy subject_id từ URL
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Bài viết đã được đăng thành công!')
            return redirect('forum:subject_detail', subject_id=post.subject.id)
    else:
        # Khởi tạo form với subject nếu có
        initial = {}
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
                initial['subject'] = subject
            except Subject.DoesNotExist:
                pass
        form = PostForm(initial=initial)
    
    context = {
        'form': form,
        'title': 'Tạo bài viết mới'
    }
    return render(request, 'forum/post_form.html', context)

@login_required
def edit_post(request, post_id):
    """Chỉnh sửa bài viết"""
    post = get_object_or_404(Post, pk=post_id, author=request.user)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bài viết đã được cập nhật!')
            return redirect('forum:subject_detail', subject_id=post.subject.id)
    else:
        form = PostForm(instance=post)
    
    context = {
        'form': form,
        'title': 'Chỉnh sửa bài viết',
        'post': post
    }
    return render(request, 'forum/post_form.html', context)

@login_required
def delete_post(request, post_id):
    """Xóa bài viết"""
    post = get_object_or_404(Post, pk=post_id, author=request.user)
    subject_id = post.subject.id
    post.delete()
    messages.success(request, 'Bài viết đã được xóa!')
    return redirect('forum:subject_detail', subject_id=subject_id)

def post_detail(request, post_id):
    """Chi tiết bài viết"""
    post = get_object_or_404(Post, pk=post_id, is_published=True)
    
    # Tăng số lượt xem
    post.view_count += 1
    post.save()
    
    # Lấy các bài viết liên quan
    related_posts = Post.objects.filter(
        subject=post.subject, 
        is_published=True
    ).exclude(id=post.id).order_by('-created_at')[:5]
    
    context = {
        'post': post,
        'related_posts': related_posts
    }
    return render(request, 'forum/post_detail.html', context)
@login_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id, is_published=True)
    questions = quiz.questions.all().order_by('order')
    
    # Kiểm tra xem user đã có attempt chưa hoàn thành chưa
    active_attempt = QuizAttempt.objects.filter(
        user=request.user, 
        quiz=quiz, 
        completed_at__isnull=True
    ).first()
    
    context = {
        'quiz': quiz,
        'questions': questions,
        'active_attempt': active_attempt,
    }
    return render(request, 'forum/quiz_detail.html', context)

@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id, is_published=True)
    
    # Tạo attempt mới
    attempt = QuizAttempt.objects.create(
        user=request.user,
        quiz=quiz
    )
    
    return redirect('forum:take_quiz', attempt_id=attempt.id)

@login_required
def take_quiz(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
    
    if attempt.completed_at:
        return redirect('forum:quiz_result', attempt_id=attempt.id)
    
    questions = attempt.quiz.questions.all().order_by('order')
    
    if request.method == 'POST':
        # Xử lý nộp bài
        score = 0
        total_questions = questions.count()
        
        for question in questions:
            if question.question_type == 'multiple_choice':
                selected_option_id = request.POST.get(f'question_{question.id}')
                if selected_option_id:
                    selected_option = Option.objects.get(id=selected_option_id)
                    UserAnswer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_option=selected_option
                    )
                    if selected_option.is_correct:
                        score += 1
            
            elif question.question_type == 'true_false':
                answer = request.POST.get(f'question_{question.id}')
                if answer:
                    # Tìm option đúng
                    correct_option = question.options.filter(is_correct=True).first()
                    if correct_option and answer == correct_option.text:
                        score += 1
                    UserAnswer.objects.create(
                        attempt=attempt,
                        question=question,
                        text_answer=answer
                    )
            
            elif question.question_type == 'short_answer':
                answer = request.POST.get(f'question_{question.id}', '')
                UserAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    text_answer=answer
                )
                # Tạm thời cho điểm tất cả câu trả lời ngắn
                if answer.strip():
                    score += 1
        
        # Tính điểm và hoàn thành attempt
        attempt.score = (score / total_questions) * 100
        attempt.completed_at = timezone.now()
        attempt.save()
        
        return redirect('forum:quiz_result', attempt_id=attempt.id)
    
    context = {
        'attempt': attempt,
        'questions': questions,
    }
    return render(request, 'forum/take_quiz.html', context)

@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
    
    if not attempt.completed_at:
        return redirect('forum:take_quiz', attempt_id=attempt.id)
    
    user_answers = attempt.user_answers.select_related(
        'question', 
        'selected_option'
    ).prefetch_related('question__options')
    
    # Chuẩn bị dữ liệu cho template
    answers_with_correct = []
    for user_answer in user_answers:
        correct_option = None
        if user_answer.question.question_type == 'multiple_choice':
            correct_option = user_answer.question.options.filter(is_correct=True).first()
        
        answers_with_correct.append({
            'user_answer': user_answer,
            'correct_option': correct_option
        })
    
    context = {
        'attempt': attempt,
        'answers_with_correct': answers_with_correct,
    }
    return render(request, 'forum/quiz_result.html', context)
# Thêm vào views.py
from .forms import TestForm, QuizForm, QuestionForm, OptionForm
from django.forms import formset_factory

@login_required
def create_test(request):
    """Tạo bài kiểm tra mới"""
    # Lấy subject_id từ URL parameter
    subject_id = request.GET.get('subject_id')
    
    if request.method == 'POST':
        form = TestForm(request.POST, request.FILES)
        if form.is_valid():
            test = form.save()
            messages.success(request, 'Bài kiểm tra đã được đăng thành công!')
            return redirect('forum:subject_detail', subject_id=test.subject.id)
    else:
        # Khởi tạo form với subject nếu có
        initial = {}
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
                initial['subject'] = subject
            except Subject.DoesNotExist:
                pass
        
        form = TestForm(initial=initial)
    
    context = {
        'form': form,
        'title': 'Đăng bài kiểm tra'
    }
    return render(request, 'forum/test_form.html', context)

@login_required
def create_quiz(request):
    """Tạo bài trắc nghiệm mới với nhiều câu hỏi"""
    subject_id = request.GET.get('subject_id')
    
    # Tạo formset cho questions
    QuestionFormSet = formset_factory(QuestionForm, extra=1, can_delete=True)
    # Tạo formset cho options (sẽ được xử lý thủ công)
    OptionFormSet = formset_factory(OptionForm, extra=4, max_num=6)
    
    if request.method == 'POST':
        quiz_form = QuizForm(request.POST)
        question_formset = QuestionFormSet(request.POST, prefix='questions')
        
        if quiz_form.is_valid() and question_formset.is_valid():
            # Lưu quiz
            quiz = quiz_form.save()
            
            # Lưu questions và options
            for i, question_form in enumerate(question_formset):
                if question_form.cleaned_data and not question_form.cleaned_data.get('DELETE', False):
                    # Lưu question
                    question = question_form.save(commit=False)
                    question.quiz = quiz
                    question.order = i + 1
                    question.save()
                    
                    # Xử lý options cho question này
                    option_prefix = f'options_{i}'
                    option_texts = request.POST.getlist(f'{option_prefix}-text')
                    option_corrects = request.POST.getlist(f'{option_prefix}-correct')
                    
                    for j, (text, is_correct) in enumerate(zip(option_texts, option_corrects)):
                        if text.strip():  # Chỉ lưu nếu có nội dung
                            Option.objects.create(
                                question=question,
                                text=text,
                                is_correct=(is_correct == 'on'),
                                order=j + 1
                            )
            
            messages.success(request, 'Bài trắc nghiệm đã được tạo thành công!')
            return redirect('forum:subject_detail', subject_id=quiz.subject.id)
        else:
            messages.error(request, 'Có lỗi xảy ra khi tạo bài trắc nghiệm!')
    else:
        # Khởi tạo form với subject nếu có
        initial = {}
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
                initial['subject'] = subject
            except Subject.DoesNotExist:
                pass
        
        quiz_form = QuizForm(initial=initial)
        question_formset = QuestionFormSet(prefix='questions')
    
    context = {
        'quiz_form': quiz_form,
        'question_formset': question_formset,
        'title': 'Tạo bài trắc nghiệm'
    }
    return render(request, 'forum/quiz_form.html', context)

@login_required
def take_test(request, test_id):
    """Làm bài kiểm tra"""
    test = get_object_or_404(Test, pk=test_id)
    
    # Kiểm tra thời hạn
    if not test.is_active():
        messages.error(request, 'Bài kiểm tra đã hết hạn!')
        return redirect('forum:subject_detail', subject_id=test.subject.id)
    
    if request.method == 'POST':
        # Xử lý nộp bài kiểm tra
        answer_file = request.FILES.get('answer_file')
        notes = request.POST.get('notes', '')
        
        if answer_file:
            # Ở đây bạn có thể lưu bài làm vào database
            # Tạo model mới cho bài nộp nếu cần
            messages.success(request, 'Bài làm của bạn đã được nộp thành công!')
            return redirect('forum:subject_detail', subject_id=test.subject.id)
        else:
            messages.error(request, 'Vui lòng chọn file bài làm!')
    
    context = {
        'test': test,
    }
    return render(request, 'forum/take_test.html', context)