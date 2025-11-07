from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from .forms import PostForm  
from django.forms import formset_factory

import os
import uuid
import json
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
    context = {
        'subjects': subjects,
        'username': request.session.get('username'),
        'is_authenticated': request.session.get('user_id') is not None
    }

    return render(request, 'forum/index.html', context)

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
def create_test(request, subject_id):
    """Tạo mới bài kiểm tra"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        time_limit = int(request.POST.get('time_limit', '0'))
        due_date_str = request.POST.get('due_date', '')
        max_attempts = int(request.POST.get('max_attempts', '1'))
        
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                messages.error(request, 'Định dạng ngày hết hạn không hợp lệ')
                return redirect('forum:create_test', subject_id=subject_id)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO tests (title, description, time_limit, due_date, max_attempts, subject_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [title, description, time_limit, due_date, max_attempts, subject_id])
        
        messages.success(request, 'Tạo bài kiểm tra thành công')
        return redirect('forum:subject_detail', subject_id=subject_id)
    context = {
        'subject_id': subject_id,
        'username': request.session.get('username'),
        'is_authenticated': request.session.get('user_id') is not None,
    }
    return render(request, 'forum/create_test.html', context)

def test_detail(request, test_id):
    """Chi tiết bài kiểm tra"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    if not test_id:
        raise Http404("Bài kiểm tra không tồn tại")
    
    # Lấy thông tin bài kiểm tra
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id, 
                title, 
                description,  -- ĐỔI TỪ content THÀNH description
                time_limit, 
                due_date, 
                created_at,
                max_attempts,
                subject_id,
                CASE 
                    WHEN due_date IS NULL THEN 1
                    WHEN datetime(due_date) > datetime('now') THEN 1
                    ELSE 0
                END as is_active
            FROM tests
            WHERE id = %s
        """, [test_id])
        
        row = cursor.fetchone()
        if not row:
            raise Http404("Bài kiểm tra không tồn tại")
        
        test = {
            'id': row[0],
            'title': row[1],
            'description': row[2],  # ĐỔI TỪ content THÀNH description
            'time_limit': row[3],
            'due_date': row[4],
            'created_at': row[5],
            'max_attempts': row[6],
            'subject_id': row[7],
            'is_active': row[8]
        }
    
    context = {
        'test': test,
    }
    return render(request, 'forum/test_detail.html', context)

def create_question(request, subject_id):
    """Tạo câu hỏi mới (multiple choice hoặc essay)"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        question_type = request.POST.get('question_type')
        content = request.POST.get('content')
        explanation = request.POST.get('explanation', '')
        attachment = request.FILES.get('attachment')
        
        if not content:
            messages.error(request, 'Nội dung câu hỏi không được để trống')
            return redirect('forum:create_question', subject_id=subject_id)
        
        attachment_path = None
        if attachment:
            attachment_path = default_storage.save(f'questions/{datetime.now().strftime("%Y/%m/%d")}/{attachment.name}', attachment)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO questions (question_type, content, explanation, attachment_path, subject_id)
                VALUES (%s, %s, %s, %s, %s)
            """, [question_type, content, explanation, attachment_path, subject_id])
            question_id = cursor.lastrowid
            
            # Xử lý theo loại câu hỏi
            if question_type == 'multiple_choice':
                options_json = request.POST.get('options', '{}')
                try:
                    # Validate JSON
                    json.loads(options_json)
                except json.JSONDecodeError:
                    options_json = '{}'
                
                allow_multiple = 1 if request.POST.get('allow_multiple') else 0
                randomize_options = 1 if request.POST.get('randomize_options') else 0
                
                cursor.execute("""
                    INSERT INTO multiple_choice_questions (id, options, allow_multiple, randomize_options)
                    VALUES (%s, %s, %s, %s)
                """, [question_id, options_json, allow_multiple, randomize_options])
                
            elif question_type == 'essay':
                word_limit = request.POST.get('word_limit', 0)
                cursor.execute("""
                    INSERT INTO essay_questions (id, word_limit)
                    VALUES (%s, %s)
                """, [question_id, word_limit])
        
        messages.success(request, 'Tạo câu hỏi thành công')
        return redirect('forum:question_bank', subject_id=subject_id)
    context = {
        'subject_id': subject_id,
        'username': request.session.get('username'),
        'is_authenticated': request.session.get('user_id') is not None,
    }
    return render(request, 'forum/create_question.html', context)

def question_bank(request, subject_id):
    """Xem ngân hàng câu hỏi của môn học"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT q.id, q.question_type, q.content, q.explanation, q.created_at,
                   COALESCE(mcq.options, '{}') as options,
                   COALESCE(eq.word_limit, 0) as word_limit
            FROM questions q
            LEFT JOIN multiple_choice_questions mcq ON q.id = mcq.id
            LEFT JOIN essay_questions eq ON q.id = eq.id
            WHERE q.subject_id = %s
            ORDER BY q.created_at DESC
        """, [subject_id])
        
        questions = []
        for row in cursor.fetchall():
            questions.append({
                'id': row[0],
                'type': row[1],
                'content': row[2],
                'explanation': row[3],
                'created_at': row[4],
                'options': row[5],
                'word_limit': row[6]
            })
    context = {
        'subject_id': subject_id,
        'username': request.session.get('username'),
        'is_authenticated': request.session.get('user_id') is not None,
        'questions': questions,
    }
    return render(request, 'forum/question_bank.html', context)

def add_questions_to_test(request, test_id):
    """Thêm câu hỏi vào bài kiểm tra"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    # Lấy thông tin test
    with connection.cursor() as cursor:
        cursor.execute("SELECT subject_id FROM tests WHERE id = %s", [test_id])
        test = cursor.fetchone()
        if not test:
            raise Http404("Bài kiểm tra không tồn tại")
        
        subject_id = test[0]
        
        # Lấy danh sách câu hỏi có sẵn
        cursor.execute("""
            SELECT q.id, q.content, q.question_type
            FROM questions q
            WHERE q.subject_id = %s
            AND q.id NOT IN (
                SELECT question_id FROM test_questions WHERE test_id = %s
            )
        """, [subject_id, test_id])
        
        available_questions = []
        for row in cursor.fetchall():
            available_questions.append({
                'id': row[0],
                'content': row[1],
                'type': row[2]
            })
    
    if request.method == 'POST':
        question_ids = request.POST.getlist('question_ids')
        with connection.cursor() as cursor:
            for i, question_id in enumerate(question_ids):
                cursor.execute("""
                    INSERT INTO test_questions (test_id, question_id, question_order)
                    VALUES (%s, %s, %s)
                """, [test_id, question_id, i])
        
        messages.success(request, 'Thêm câu hỏi vào bài kiểm tra thành công')
        return redirect('forum:test_detail', test_id=test_id)
    context = {
        'test_id': test_id,
        'username': request.session.get('username'),
        'is_authenticated': request.session.get('user_id') is not None,
        'available_questions': available_questions,

    }
    return render(request, 'forum/add_questions_to_test.html', context)

def take_test(request, test_id):
    """Làm bài kiểm tra trực tuyến"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    user_id = request.session['user_id']
    
    # Kiểm tra số lần nộp bài
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM submissions 
            WHERE test_id = %s AND author_id = %s
        """, [test_id, user_id])
        attempt_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT max_attempts FROM tests WHERE id = %s
        """, [test_id])
        max_attempts_result = cursor.fetchone()
        max_attempts = max_attempts_result[0] if max_attempts_result else 1
        
        if attempt_count >= max_attempts:
            messages.error(request, 'Bạn đã vượt quá số lần nộp bài cho phép')
            return redirect('forum:test_detail', test_id=test_id)
    
    if request.method == 'POST':
        # Xử lý nộp bài
        with connection.cursor() as cursor:
            # Tạo submission
            cursor.execute("""
                INSERT INTO submissions (test_id, author_id, attempt_number, time_spent)
                VALUES (%s, %s, %s, %s)
            """, [test_id, user_id, attempt_count + 1, request.POST.get('time_spent', 0)])
            submission_id = cursor.lastrowid
            
            # Lưu câu trả lời
            for key, value in request.POST.items():
                if key.startswith('answer_'):
                    question_id = key.replace('answer_', '')
                    # Đóng gói câu trả lời dưới dạng JSON
                    answer_data = json.dumps({'answer': value})
                    cursor.execute("""
                        INSERT INTO answers (submission_id, question_id, answer_content)
                        VALUES (%s, %s, %s)
                    """, [submission_id, question_id, answer_data])
        
        messages.success(request, 'Nộp bài thành công')
        return redirect('forum:submissions_history', test_id=test_id)
    
    # Lấy câu hỏi của bài kiểm tra
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT q.id, q.question_type, q.content, q.explanation,
                   mcq.options, mcq.allow_multiple, mcq.randomize_options,
                   eq.word_limit
            FROM test_questions tq
            JOIN questions q ON tq.question_id = q.id
            LEFT JOIN multiple_choice_questions mcq ON q.id = mcq.id
            LEFT JOIN essay_questions eq ON q.id = eq.id
            WHERE tq.test_id = %s
            ORDER BY tq.question_order
        """, [test_id])
        
        questions = []
        for row in cursor.fetchall():
            questions.append({
                'id': row[0],
                'type': row[1],
                'content': row[2],
                'explanation': row[3],
                'options': row[4],
                'allow_multiple': bool(row[5]),
                'randomize_options': bool(row[6]),
                'word_limit': row[7]
            })
    context = {
        'test_id': test_id,
        'attempt_number': attempt_count + 1,
        'is_authenticated': request.session.get('user_id') is not None,
        'questions': questions,
    }
    return render(request, 'forum/take_test.html', context)

def submit_test(request, test_id):
    """Nộp bài kiểm tra dạng file"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        user_id = request.session['user_id']
        answer_file = request.FILES.get('answer_file')
        notes = request.POST.get('notes', '')
        time_spent = int(request.POST.get('time_spent', '0'))
        
        if not answer_file:
            messages.error(request, 'Vui lòng tải lên file đáp án')
            return redirect('forum:test_detail', test_id=test_id)
        
        # Lưu file đáp án
        file_path = default_storage.save(f'test_submissions/{datetime.now().strftime("%Y/%m/%d")}/{answer_file.name}', answer_file)
        
        # Lưu thông tin nộp bài vào cơ sở dữ liệu
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO submissions (test_id, author_id, time_spent, submitted_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """, [test_id, user_id, time_spent])
        
        messages.success(request, 'Nộp bài kiểm tra thành công')
        return redirect('forum:test_detail', test_id=test_id)
    
    return redirect('forum:test_detail', test_id=test_id)

def grade_submission(request, submission_id):
    """Chấm điểm bài nộp"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        with connection.cursor() as cursor:
            total_score = 0
            for key, value in request.POST.items():
                if key.startswith('score_'):
                    answer_id = key.replace('score_', '')
                    score = float(value) if value else 0
                    total_score += score
                    
                    cursor.execute("""
                        UPDATE answers SET score = %s WHERE id = %s
                    """, [score, answer_id])
            
            # Cập nhật tổng điểm
            cursor.execute("""
                UPDATE submissions SET total_score = %s WHERE id = %s
            """, [total_score, submission_id])
        
        messages.success(request, 'Chấm điểm thành công')
        return redirect('forum:submission_detail', submission_id=submission_id)
    
    return redirect('forum:submission_detail', submission_id=submission_id)

def submission_detail(request, submission_id):
    """Xem chi tiết bài nộp"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT s.id, s.submitted_at, s.time_spent, s.total_score,
                   s.test_id, s.author_id, t.title
            FROM submissions s
            JOIN tests t ON s.test_id = t.id
            WHERE s.id = %s
        """, [submission_id])
        
        submission = cursor.fetchone()
        if not submission:
            raise Http404("Bài nộp không tồn tại")
        
        # Lấy câu trả lời
        cursor.execute("""
            SELECT a.id, a.answer_content, a.score, 
                   q.id as question_id, q.content as question_content,
                   q.question_type
            FROM answers a
            JOIN questions q ON a.question_id = q.id
            WHERE a.submission_id = %s
        """, [submission_id])
        
        answers = []
        for row in cursor.fetchall():
            answers.append({
                'id': row[0],
                'answer_content': row[1],
                'score': row[2],
                'question_id': row[3],
                'question_content': row[4],
                'question_type': row[5]
            })
    context = {
        'username': request.session.get('username'),
        'is_authenticated': request.session.get('user_id') is not None,
        'submission': {
            'id': submission[0],
            'submitted_at': submission[1],
            'time_spent': submission[2],
            'total_score': submission[3],
            'test_id': submission[4],
            'author_id': submission[5],
            'test_title': submission[6]
        },
        'answers': answers
    }
    return render(request, 'forum/submission_detail.html', context)

def submissions_history(request, test_id):
    """Xem lịch sử nộp bài kiểm tra"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    user_id = request.session['user_id']
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id, 
                submitted_at, 
                time_spent, 
                total_score
            FROM submissions
            WHERE test_id = %s AND author_id = %s
            ORDER BY submitted_at DESC
        """, [test_id, user_id])
        
        submissions = []
        for row in cursor.fetchall():
            submissions.append({
                'id': row[0],
                'submitted_at': row[1],
                'time_spent': row[2],
                'total_score': row[3]
            })
    
    context = {
        'submissions': submissions,
        'test_id': test_id,
    }
    return render(request, 'forum/submissions_history.html', context)





