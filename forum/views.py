from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from .models import Subject, Post, Test, Quiz, Question, Option, QuizAttempt, UserAnswer
from .forms import PostForm  
from django.forms import formset_factory

import os
import uuid

from django.conf import settings
from django.db import connection
from django.http import Http404
from django.utils import timezone
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage

def index(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, description FROM subjects")
            subjects = cursor.fetchall()
    except Exception as e:
        subjects = []
    return render(request, 'forum/index.html', {'subjects': subjects})

def subject_detail(request, subject_id):
    """Chi tiết môn học"""
    
    # Lấy thông tin môn học
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description
            FROM subjects
            WHERE id = %s
        """, [subject_id])
        
        row = cursor.fetchone()
        if not row:
            raise Http404("Môn học không tồn tại")
        
        subject = {
            'id': row[0],
            'name': row[1],
            'description': row[2]
        }
        
        # Lấy danh sách bài kiểm tra
        cursor.execute("""
            SELECT 
                id, 
                title, 
                description,
                time_limit, 
                due_date, 
                created_at,
                max_attempts,
                CASE 
                    WHEN due_date IS NULL THEN 1
                    WHEN datetime(due_date) > datetime('now') THEN 1
                    ELSE 0
                END as is_active
            FROM tests
            WHERE subject_id = %s
            ORDER BY created_at DESC
        """, [subject_id])
        
        tests = [
            {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'time_limit': row[3],
                'due_date': row[4],
                'created_at': row[5],
                'max_attempts': row[6],
                'is_active': row[7]
            }
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT 
                p.id, 
                p.title, 
                p.content,
                p.view_count,
                p.created_at,
                p.author_id,
                u.username,
                COUNT(c.id)
            FROM posts p
            LEFT JOIN users u ON p.author_id = u.id
            LEFT JOIN comments c ON p.id = c.post_id
            WHERE p.subject_id = %s
            GROUP BY p.id, p.title, p.content, p.view_count, p.created_at, p.author_id, u.username
            ORDER BY p.created_at
        """, [subject_id])
        
        posts = [
            {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'view_count': row[3],
                'created_at': row[4],
                'author': {
                    'id': row[5],
                    'username': row[6]
                },
                'comment_count': row[7]
            }
            for row in cursor.fetchall()
        ]

        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
    
    context = {
        'is_authenticated': request.session.get('user_id') is not None,
        'username': request.session.get('username'),
        'subject': subject,
        'posts': posts,
        'tests': tests,
        'user_count': user_count
    }
    return render(request, 'forum/subject_detail.html', context)


def create_post(request):
    """Tạo bài viết mới - Raw SQL"""
    
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập để đăng bài')
        return redirect('accounts:login')
    
    user_id = request.session['user_id']
    subject_id = request.GET.get('subject_id')
    
    # Lấy danh sách subjects
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM subjects ORDER BY name")
        subjects = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    
    if request.method != 'POST':
        context = {
            'subjects': subjects,
            'title': 'Tạo bài viết mới',
            'selected_subject_id': int(subject_id) if subject_id else None
        }
        return render(request, 'forum/post_form.html', context)

    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    subject_id = request.POST.get('subject')
    attachment = request.FILES.get('attachment')
        
    errors = []
    if not title:
        errors.append('Tiêu đề không được để trống')
    elif len(title) < 5:
        errors.append('Tiêu đề phải có ít nhất 5 ký tự')
    elif len(title) > 200:
        errors.append('Tiêu đề không được quá 200 ký tự')
        
    if content and len(content) > 50000:
        errors.append('Nội dung quá dài (tối đa 50,000 ký tự)')
        
    if not subject_id:
        errors.append('Vui lòng chọn môn học')
    else:
        # Validate subject_id tồn tại
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM subjects WHERE id = %s", [subject_id])
            if not cursor.fetchone():
                errors.append('Môn học không tồn tại')
    
    if errors:
        for error in errors:
            messages.error(request, error)
        context = {
            'subjects': subjects,
            'title': 'Tạo bài viết mới',
            'selected_subject_id': int(subject_id) if subject_id else None,
            'form_data': {
                'title': title,
                'content': content,
                'subject': subject_id
            }
        }
        return render(request, 'forum/post_form.html', context)
        
    # file upload
    attachment_path = None
    if attachment:
        # Validate file
        allowed_extensions = ['pdf', 'doc', 'docx', 'txt', 'zip', 'rar']
        file_ext = attachment.name.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            messages.error(request, 'Định dạng file không hợp lệ')
            context = {
                'subjects': subjects,
                'title': 'Tạo bài viết mới',
                'selected_subject_id': int(subject_id) if subject_id else None,
                'form_data': {
                    'title': title,
                    'content': content,
                    'subject': subject_id
                }
            }
            return render(request, 'forum/post_form.html', context)
            
        # Check file size (max 25MB)
        if attachment.size > 25 * 1024 * 1024:
            messages.error(request, 'File quá lớn (tối đa 25MB)')
            context = {
                'subjects': subjects,
                'title': 'Tạo bài viết mới',
                'selected_subject_id': int(subject_id) if subject_id else None,
                'form_data': {
                    'title': title,
                    'content': content,
                    'subject': subject_id
                }
            }
            return render(request, 'forum/post_form.html', context)
        
        # Generate unique filename
        unique_name = f"{uuid.uuid4()} {attachment.name}"
        upload_path = os.path.join('posts', unique_name)
        full_path = os.path.join(settings.MEDIA_ROOT, upload_path)
        
        # Create directory if not exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Save file
        with open(full_path, 'wb+') as destination:
            for chunk in attachment.chunks():
                destination.write(chunk)
        
        attachment_path = upload_path
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO posts (title, content, subject_id, author_id, attachment_path)
                VALUES (%s, %s, %s, %s, %s)
            """, [title, content, subject_id, user_id, attachment_path])
        
        messages.success(request, 'Bài viết đã được đăng thành công!')
        return redirect('forum:subject_detail', subject_id=subject_id)
        
    except Exception as e:
        # Xóa file nếu insert failed
        if attachment_path:
            try:
                os.remove(full_path)
            except:
                pass
        
        messages.error(request, f'Có lỗi xảy ra: {str(e)}')
        context = {
            'subjects': subjects,
            'title': 'Tạo bài viết mới',
            'selected_subject_id': int(subject_id) if subject_id else None,
            'form_data': {
                'title': title,
                'content': content,
                'subject': subject_id
            }
        }
        return render(request, 'forum/post_form.html', context)


def edit_post(request, post_id):
    """Chỉnh sửa bài viết"""
    
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập')
        return redirect('accounts:login')
    
    user_id = request.session['user_id']
    
    # Kiểm tra quyền sở hữu bài viết
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                p.id, p.title, p.content, p.subject_id, 
                p.attachment_path, p.author_id,
                s.name as subject_name
            FROM posts p
            LEFT JOIN subjects s ON p.subject_id = s.id
            WHERE p.id = %s
        """, [post_id])
        
        row = cursor.fetchone()
        if not row:
            raise Http404("Bài viết không tồn tại")
        
        if row[5] != user_id:  # author_id
            messages.error(request, 'Bạn không có quyền chỉnh sửa bài viết này')
            return redirect('forum:post_detail', post_id=post_id)
        
        post = {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'subject_id': row[3],
            'attachment_path': row[4],
            'author_id': row[5],
            'subject': {
                'id': row[3],
                'name': row[6]
            }
        }
        
        # Lấy danh sách subjects
        cursor.execute("SELECT id, name FROM subjects ORDER BY name")
        subjects = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    
    if request.method != 'POST':
        context = {
            'is_authenticated': True,
            'username': request.session.get('username'),
            'subjects': subjects,
            'title': 'Chỉnh sửa bài viết',
            'post': post,
            'form_data': post
        }
        return render(request, 'forum/post_form.html', context)
    
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    subject_id = request.POST.get('subject')
    attachment = request.FILES.get('attachment')
    
    errors = []
    if not title:
        errors.append('Tiêu đề không được để trống')
    elif len(title) < 5:
        errors.append('Tiêu đề phải có ít nhất 5 ký tự')
    elif len(title) > 200:
        errors.append('Tiêu đề không được quá 200 ký tự')
        
    if content and len(content) > 50000:
        errors.append('Nội dung quá dài')
        
    if not subject_id:
        errors.append('Vui lòng chọn môn học')
    
    if errors:
        for error in errors:
            messages.error(request, error)
        context = {
            'is_authenticated': True,
            'username': request.session.get('username'),
            'subjects': subjects,
            'title': 'Chỉnh sửa bài viết',
            'post': post,
            'form_data': {
                'title': title,
                'content': content,
                'subject_id': subject_id
            }
        }
        return render(request, 'forum/post_form.html', context)
    
    # Xử lý file mới nếu có
    attachment_path = post['attachment_path']
    if attachment:
        allowed_extensions = ['pdf', 'doc', 'docx', 'txt', 'zip', 'rar']
        file_ext = attachment.name.split('.')[-1].lower()
        
        if file_ext in allowed_extensions and attachment.size <= 25 * 1024 * 1024:
            # Xóa file cũ
            if attachment_path:
                try:
                    old_file = os.path.join(settings.MEDIA_ROOT, attachment_path)
                    if os.path.exists(old_file):
                        os.remove(old_file)
                except:
                    pass
            
            # Lưu file mới
            unique_name = f"{uuid.uuid4()} {attachment.name}"
            upload_path = os.path.join('posts', unique_name)
            full_path = os.path.join(settings.MEDIA_ROOT, upload_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'wb+') as destination:
                for chunk in attachment.chunks():
                    destination.write(chunk)
            
            attachment_path = upload_path
        else:
            messages.error(request, 'File không hợp lệ hoặc quá lớn')
            return redirect('forum:edit_post', post_id=post_id)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE posts 
                SET title = %s, content = %s, subject_id = %s, attachment_path = %s, updated_at = (datetime('now', 'localtime'))
                WHERE id = %s
            """, [title, content, subject_id, attachment_path, post_id])
        
        messages.success(request, 'Bài viết đã được cập nhật!')
        return redirect('forum:post_detail', post_id=post_id)
        
    except Exception as e:
        messages.error(request, f'Có lỗi xảy ra: {str(e)}')
        return redirect('forum:edit_post', post_id=post_id)


def delete_post(request, post_id):
    """Xóa bài viết"""
    
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập')
        return redirect('accounts:login')
    
    user_id = request.session['user_id']
    
    with connection.cursor() as cursor:
        # Kiểm tra quyền sở hữu
        cursor.execute("""
            SELECT author_id, attachment_path, subject_id
            FROM posts 
            WHERE id = %s
        """, [post_id])
        
        row = cursor.fetchone()
        if not row:
            raise Http404("Bài viết không tồn tại")
        
        if row[0] != user_id:
            messages.error(request, 'Bạn không có quyền xóa bài viết này')
            return redirect('forum:post_detail', post_id=post_id)
        
        attachment_path = row[1]
        subject_id = row[2]
        
        # Xóa file đính kèm nếu có
        if attachment_path:
            try:
                file_path = os.path.join(settings.MEDIA_ROOT, attachment_path)
                os.remove(file_path)
            except:
                pass
        
        # Xóa bài viết
        cursor.execute("DELETE FROM posts WHERE id = %s", [post_id])
    
    messages.success(request, 'Bài viết đã được xóa')
    return redirect('forum:subject_detail', subject_id=subject_id)


def post_detail(request, post_id):
    """Chi tiết bài viết"""
    
    with connection.cursor() as cursor:
        # Lấy thông tin bài viết với comment_count và vote_value
        cursor.execute("""
            SELECT 
                p.id, 
                p.title, 
                p.content,
                p.view_count,
                p.created_at,
                p.updated_at,
                p.attachment_path,
                p.subject_id,
                s.name as subject_name,
                p.author_id,
                u.username,
                u.first_name,
                u.last_name,
                u.avatar_path,
                COUNT(DISTINCT c.id) as comment_count,
                COALESCE(SUM(v.vote_value), 0) as vote_value
            FROM posts p
            LEFT JOIN subjects s ON p.subject_id = s.id
            LEFT JOIN users u ON p.author_id = u.id
            LEFT JOIN comments c ON p.id = c.post_id
            LEFT JOIN votes v ON p.id = v.post_id
            WHERE p.id = %s
            GROUP BY p.id, p.title, p.content, p.view_count, p.created_at, 
                     p.attachment_path, p.subject_id, s.name, p.author_id, 
                     u.username, u.first_name, u.last_name, u.avatar_path
        """, [post_id])
        
        row = cursor.fetchone()
        if not row:
            raise Http404("Bài viết không tồn tại")
        
        # Lấy extension và filename từ attachment_path
        attachment_path = row[6]
        file_extension = ''
        filename = ''
        file_size = 0
        
        if attachment_path:
            filename = os.path.basename(attachment_path)
            file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
            parts = filename.split(' ', 1)
            filename = parts[1] if len(parts) > 1 else ''
            # Lấy kích thước file
            try:
                full_path = os.path.join(settings.MEDIA_ROOT, attachment_path)
                file_size = os.path.getsize(full_path)
            except:
                file_size = 0
        
        post = {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'view_count': row[3],
            'created_at': row[4],
            'updated_at': row[5],
            'attachment': {
                'url': f"{settings.MEDIA_URL}/{attachment_path}" if attachment_path else None,
                'size': file_size
            } if attachment_path else None,
            'filename': filename,
            'file_extension': file_extension,
            'subject': {
                'id': row[7],
                'name': row[8]
            },
            'author': {
                'id': row[9],
                'username': row[10],
                'first_name': row[11],
                'last_name': row[12],
                'avatar_path': row[13],
                'get_full_name': f"{row[11]} {row[12]}".strip() or row[10]
            },
            'comment_count': row[14],
            'vote_value': row[15]
        }
        
        # Lấy vote của post
        cursor.execute("""
            SELECT COALESCE(SUM(vote_value), 0) as vote_value
            FROM votes
            WHERE post_id = %s
        """, [post_id])
        post['vote_value'] = cursor.fetchone()[0]


        # Lấy danh sách comments
        cursor.execute("""
            SELECT 
                c.id,
                c.content,
                c.created_at,
                c.commenter_id,
                u.username,
                u.first_name,
                u.last_name,
                u.avatar_path
            FROM comments c
            LEFT JOIN users u ON c.commenter_id = u.id
            WHERE c.post_id = %s
            ORDER BY c.created_at ASC
        """, [post_id])
        
        comments = [
            {
                'id': row[0],
                'content': row[1],
                'created_at': row[2],
                'commenter': {
                    'id': row[3],
                    'username': row[4],
                    'first_name': row[5],
                    'last_name': row[6],
                    'avatar_path': row[7],
                    'get_full_name': f"{row[5]} {row[6]}".strip() if row[5] and row[6] else row[4]
                }
            }
            for row in cursor.fetchall()
        ]

        # Tăng số lượt xem
        cursor.execute("""
            UPDATE posts 
            SET view_count = view_count + 1 
            WHERE id = %s
        """, [post_id])
        
        post['view_count'] += 1
        
        # Lấy các bài viết liên quan
        cursor.execute("""
            SELECT 
                p.id, 
                p.title, 
                p.view_count,
                p.created_at,
                u.username,
                u.first_name,
                u.last_name
            FROM posts p
            LEFT JOIN users u ON p.author_id = u.id
            WHERE p.subject_id = %s AND p.id != %s
            ORDER BY p.created_at DESC
            LIMIT 5
        """, [post['subject']['id'], post_id])
        
        related_posts = [
            {
                'id': row[0],
                'title': row[1],
                'view_count': row[2],
                'created_at': row[3],
                'author': {
                    'username': row[4],
                    'get_full_name': f"{row[5]} {row[6]}".strip() or row[4]
                }
            }
            for row in cursor.fetchall()
        ]
        
        # Đếm số bài viết của tác giả
        cursor.execute("""
            SELECT COUNT(*) FROM posts WHERE author_id = %s
        """, [post['author']['id']])
        author_post_count = cursor.fetchone()[0]
        
    context = {
        'post': post,
        'comments': comments,
        'related_posts': related_posts,
        'is_authenticated': request.session.get('user_id') is not None,
        'current_user_id': request.session.get('user_id'),
        'author_post_count': author_post_count
    }
    return render(request, 'forum/post_detail.html', context)


def add_comment(request, post_id):
    """Thêm bình luận"""
    
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập để bình luận')
        return redirect('accounts:login')
    
    if request.method != 'POST':
        return redirect('forum:post_detail', post_id=post_id)
    
    user_id = request.session['user_id']
    content = request.POST.get('content', '').strip()
    
    if not content:
        messages.error(request, 'Nội dung bình luận không được để trống')
        return redirect('forum:post_detail', post_id=post_id)
    
    if len(content) > 5000:
        messages.error(request, 'Bình luận quá dài (tối đa 5000 ký tự)')
        return redirect('forum:post_detail', post_id=post_id)
    
    try:
        with connection.cursor() as cursor:
            # Kiểm tra post tồn tại
            cursor.execute("SELECT id FROM posts WHERE id = %s", [post_id])
            if not cursor.fetchone():
                raise Http404("Bài viết không tồn tại")
            
            # Thêm comment
            cursor.execute("""
                INSERT INTO comments (content, commenter_id, post_id)
                VALUES (%s, %s, %s)
            """, [content, user_id, post_id])
        
        messages.success(request, 'Bình luận đã được đăng!')
    except Exception as e:
        messages.error(request, f'Có lỗi xảy ra: {str(e)}')
    
    return redirect('forum:post_detail', post_id=post_id)


def delete_comment(request, comment_id):
    """Xóa bình luận"""
    
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập')
        return redirect('accounts:login')
    
    user_id = request.session['user_id']
    
    with connection.cursor() as cursor:
        # Kiểm tra quyền sở hữu
        cursor.execute("""
            SELECT commenter_id, post_id
            FROM comments 
            WHERE id = %s
        """, [comment_id])
        
        row = cursor.fetchone()
        if not row:
            raise Http404("Bình luận không tồn tại")
        
        if row[0] != user_id:
            messages.error(request, 'Bạn không có quyền xóa bình luận này')
            return redirect('forum:post_detail', post_id=row[1])
        
        post_id = row[1]
        
        # Xóa comment
        cursor.execute("DELETE FROM comments WHERE id = %s", [comment_id])
    
    messages.success(request, 'Bình luận đã được xóa')
    return redirect('forum:post_detail', post_id=post_id)


def vote_post(request, post_id):
    """Vote cho bài viết (upvote = 1, downvote = -1)"""
    
    if not request.session.get('user_id'):
        messages.error(request, 'Vui lòng đăng nhập để vote')
        return redirect('accounts:login')
    
    if request.method != 'POST':
        return redirect('forum:post_detail', post_id=post_id)
    
    user_id = request.session['user_id']
    vote_value = request.POST.get('vote_value')
    
    # Validate vote_value
    try:
        vote_value = int(vote_value)
        if vote_value not in (1, -1):
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, 'Giá trị vote không hợp lệ')
        return redirect('forum:post_detail', post_id=post_id)
    
    with connection.cursor() as cursor:
        # Kiểm tra post tồn tại
        cursor.execute("SELECT id FROM posts WHERE id = %s", [post_id])
        if not cursor.fetchone():
            raise Http404("Bài viết không tồn tại")
        
        # Kiểm tra user đã vote chưa
        cursor.execute("""
            SELECT vote_value FROM votes 
            WHERE voter_id = %s AND post_id = %s
        """, [user_id, post_id])
        
        existing_vote = cursor.fetchone()
        
        if existing_vote:
            # Nếu đã vote
            if existing_vote[0] == vote_value:
                # Nếu vote giống nhau -> xóa vote (toggle)
                cursor.execute("""
                    DELETE FROM votes 
                    WHERE voter_id = %s AND post_id = %s
                """, [user_id, post_id])
                messages.info(request, 'Đã hủy vote')
            else:
                # Nếu khác -> update vote
                cursor.execute("""
                    UPDATE votes 
                    SET vote_value = %s 
                    WHERE voter_id = %s AND post_id = %s
                """, [vote_value, user_id, post_id])
                messages.success(request, 'Đã cập nhật vote')
        else:
            # Chưa vote -> insert mới
            cursor.execute("""
                INSERT INTO votes (vote_value, voter_id, post_id)
                VALUES (%s, %s, %s)
            """, [vote_value, user_id, post_id])
            messages.success(request, 'Đã vote thành công')
    
    
    return redirect('forum:post_detail', post_id=post_id)






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


def create_test(request):
    """Tạo bài kiểm tra mới"""
    
    if not request.session.get('user_id'):
        return redirect('accounts:login')
    
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
        'is_authenticated': request.session.get('user_id') is not None,
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