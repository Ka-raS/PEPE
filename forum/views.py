
import os
import uuid
import json
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.http import Http404
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
                ends_at, 
                created_at,
                max_attempts,
                CASE 
                    WHEN ends_at IS NULL THEN 1
                    WHEN datetime(ends_at) > datetime('now') THEN 1
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
                'ends_at': row[4],
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
        cursor.execute("SELECT COUNT(*) FROM questions")
        question_count = cursor.fetchone()[0]
    
    context = {
        'is_authenticated': request.session.get('user_id') is not None,
        'username': request.session.get('username'),
        'subject': subject,
        'posts': posts,
        'tests': tests,
        'user_count': user_count,
        'question_count': question_count
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
            'is_authenticated': True,
            'username': request.session.get('username'),
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
            'is_authenticated': True,
            'username': request.session.get('username'),
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
                'is_authenticated': True,
                'username': request.session.get('username'),
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
                'is_authenticated': True,
                'username': request.session.get('username'),
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
            'is_authenticated': True,
            'username': request.session.get('username'),
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
        
        # SELECT * subjects
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
    if not title or title.strip() == '':
        errors.append('Tiêu đề không được để trống')
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
                p.id, p.title, p.content, p.view_count,
                p.created_at, p.updated_at, p.attachment_path,
                p.subject_id, s.name as subject_name,
                p.author_id, u.username, u.first_name, u.last_name, u.avatar_path,
                (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count,
                (SELECT COALESCE(SUM(vote_value), 0) FROM votes WHERE post_id = p.id) as vote_value
            FROM posts p
            JOIN subjects s ON p.subject_id = s.id
            JOIN users u ON p.author_id = u.id
            WHERE p.id = %s
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
        'is_authenticated': request.session.get('user_id') is not None,
        'username': request.session.get('username'),
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
    """Tạo mới bài kiểm tra với câu hỏi"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')

    if request.method != 'POST':
        context = {
            'subject_id': subject_id,
            'username': request.session.get('username'),
            'is_authenticated': True,
        }
        return render(request, 'forum/create_test.html', context)

    user_id = request.session['user_id']
    title = request.POST.get('title')
    description = request.POST.get('description')
    time_limit = int(request.POST.get('time_limit', '0'))
    max_attempts = int(request.POST.get('max_attempts', '1'))
    selected_questions = request.POST.getlist('selected_questions')
        
    ends_at_str = request.POST.get('ends_at', '')
    ends_at = None
    if ends_at_str:
        try:
            ends_at = datetime.strptime(ends_at_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            messages.error(request, 'Định dạng ngày hết hạn không hợp lệ')
            return redirect('forum:create_test', subject_id=subject_id)

    try:
        with connection.cursor() as cursor:
            # Tạo bài kiểm tra
            cursor.execute("""
                INSERT INTO tests (title, description, time_limit, ends_at, max_attempts, subject_id, author_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [title, description, time_limit, ends_at, max_attempts, subject_id, user_id])
            
            test_id = cursor.lastrowid
            
            # Xử lý các câu hỏi đã chọn
            for i, question_data in enumerate(selected_questions):
                try:
                    question = json.loads(question_data)
                    
                    if question['source'] == 'new':
                        # Tạo câu hỏi mới
                        cursor.execute("""
                            INSERT INTO questions (content, subject_id, author_id)
                            VALUES (%s, %s, %s)
                        """, [question['content'], subject_id, user_id])
                        
                        question_id = cursor.lastrowid

                        if question['type'] == 'multiple_choice':
                            # Tạo các options
                            options = question.get('options', [])
                            correct_answer_index = question.get('correct_answer_index', 0)
                            correct_option_id = None
                            
                            # Tạo từng option và lưu ID
                            for idx, option_content in enumerate(options):
                                if option_content and option_content.strip():
                                    cursor.execute("""
                                        INSERT INTO multiple_choice_options (content, question_id)
                                        VALUES (%s, %s)
                                    """, [option_content.strip(), question_id])
                                    
                                    option_id = cursor.lastrowid
                                    
                                    # Lưu ID của đáp án đúng
                                    if idx == correct_answer_index:
                                        correct_option_id = option_id
                            
                            # Tạo multiple choice question với đáp án đúng
                            if correct_option_id:
                                randomize = 1 if question.get('randomize_options', False) else 0
                                cursor.execute("""
                                    INSERT INTO multiple_choice_questions (id, correct_option_id, randomize_options)
                                    VALUES (%s, %s, %s)
                                """, [question_id, correct_option_id, randomize])
                            else:
                                messages.warning(request, f'Câu hỏi "{question["content"][:50]}..." không có đáp án đúng hợp lệ')
                                cursor.execute("DELETE FROM questions WHERE id = %s", [question_id])
                                continue
                        
                        elif question['type'] == 'essay':
                            cursor.execute("""
                                INSERT INTO essay_questions (id, word_limit)
                                VALUES (%s, %s)
                            """, [question_id, question.get('word_limit', 0)])
                    else:
                        # Sử dụng câu hỏi có sẵn
                        question_id = question['id']
                    
                    # Thêm câu hỏi vào bài kiểm tra
                    cursor.execute("""
                        INSERT INTO test_questions (test_id, question_id, question_order)
                        VALUES (%s, %s, %s)
                    """, [test_id, question_id, i])
                    
                except Exception as e:
                    messages.warning(request, f'Có lỗi khi thêm câu hỏi: {str(e)}')
                    continue
        
        messages.success(request, 'Tạo bài kiểm tra thành công')
        return redirect('forum:test_detail', test_id=test_id)
        
    except Exception as e:
        messages.error(request, f'Có lỗi xảy ra: {str(e)}')
        return redirect('forum:create_test', subject_id=subject_id)
    

def test_detail(request, test_id):
    """Chi tiết bài kiểm tra"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id, title, description, time_limit, ends_at, created_at,
                max_attempts, subject_id,
                CASE 
                    WHEN ends_at IS NULL THEN 1
                    WHEN datetime(ends_at) > datetime('now') THEN 1
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
            'description': row[2],
            'time_limit': row[3],
            'ends_at': row[4],
            'created_at': row[5],
            'max_attempts': row[6],
            'subject_id': row[7],
            'is_active': row[8]
        }
    
        user_id = request.session.get('user_id')
        if user_id:
            cursor.execute("""
                SELECT COUNT(*) FROM submissions 
                WHERE test_id = %s AND author_id = %s
            """, [test_id, user_id])
            current_user_attempts = cursor.fetchone()[0]
        else:
            current_user_attempts = 0

    # Tính toán remaining attempts
    remaining_attempts = test['max_attempts'] - current_user_attempts
    progress_percent = (current_user_attempts / test['max_attempts'] * 100) if test['max_attempts'] > 0 else 0

    context = {
        'test': test,
        'current_user_attempts': current_user_attempts,
        'remaining_attempts': remaining_attempts,
        'progress_percent': int(progress_percent),
        'is_authenticated': True,
        'username': request.session.get('username'),
        'is_author': user_id == test.get('author_id')
    }
    return render(request, 'forum/test_detail.html', context)


def create_question(request, subject_id):
    """Tạo câu hỏi mới"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    if request.method != 'POST':
        context = {
            'subject_id': subject_id,
            'is_authenticated': True,
            'username': request.session.get('username'),
        }
        return render(request, 'forum/create_question.html', context)

    user_id = request.session['user_id']
    question_type = request.POST.get('question_type')
    content = request.POST.get('content', '').strip()
    attachment = request.FILES.get('attachment')
    
    if not content:
        messages.error(request, 'Nội dung câu hỏi không được để trống')
        return redirect('forum:create_question', subject_id=subject_id)
    
    # Xử lý file đính kèm
    attachment_path = None
    if attachment:
        allowed_extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
        file_ext = attachment.name.split('.')[-1].lower()
        
        if file_ext not in allowed_extensions:
            messages.error(request, 'Định dạng file không hợp lệ')
            return redirect('forum:create_question', subject_id=subject_id)
        
        if attachment.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            messages.error(request, 'File quá lớn (tối đa 25MB)')
            return redirect('forum:create_question', subject_id=subject_id)
        
        unique_name = f"{uuid.uuid4()}_{attachment.name}"
        upload_path = os.path.join('questions', unique_name)
        full_path = os.path.join(settings.MEDIA_ROOT, upload_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'wb+') as destination:
            for chunk in attachment.chunks():
                destination.write(chunk)
        
        attachment_path = upload_path
    
    try:
        with connection.cursor() as cursor:
            # Tạo câu hỏi
            cursor.execute("""
                INSERT INTO questions (content, attachment_path, subject_id, author_id)
                VALUES (%s, %s, %s, %s)
            """, [content, attachment_path, subject_id, user_id])
            question_id = cursor.lastrowid
            
            if question_type == 'multiple_choice':
                # Lấy danh sách đáp án từ form (dạng JSON array)
                options_json = request.POST.get('options_data')
                
                if not options_json:
                    messages.error(request, 'Vui lòng thêm đáp án')
                    cursor.execute("DELETE FROM questions WHERE id = %s", [question_id])
                    return redirect('forum:create_question', subject_id=subject_id)
                
                try:
                    options_data = json.loads(options_json)
                except:
                    messages.error(request, 'Dữ liệu đáp án không hợp lệ')
                    cursor.execute("DELETE FROM questions WHERE id = %s", [question_id])
                    return redirect('forum:create_question', subject_id=subject_id)
                
                if len(options_data) < 2:
                    messages.error(request, 'Phải có ít nhất 2 đáp án')
                    cursor.execute("DELETE FROM questions WHERE id = %s", [question_id])
                    return redirect('forum:create_question', subject_id=subject_id)
                
                correct_index = int(request.POST.get('correct_answer_index', -1))
                if correct_index < 0 or correct_index >= len(options_data):
                    messages.error(request, 'Vui lòng chọn đáp án đúng')
                    cursor.execute("DELETE FROM questions WHERE id = %s", [question_id])
                    return redirect('forum:create_question', subject_id=subject_id)
                
                # Tạo các options và lưu correct_option_id
                correct_option_id = None
                for idx, option_text in enumerate(options_data):
                    if not option_text.strip():
                        continue
                        
                    cursor.execute("""
                        INSERT INTO multiple_choice_options (content, question_id)
                        VALUES (%s, %s)
                    """, [option_text.strip(), question_id])
                    
                    if idx == correct_index:
                        correct_option_id = cursor.lastrowid
                
                if not correct_option_id:
                    messages.error(request, 'Đáp án đúng không hợp lệ')
                    cursor.execute("DELETE FROM questions WHERE id = %s", [question_id])
                    return redirect('forum:create_question', subject_id=subject_id)
                
                # Tạo multiple choice question
                randomize_options = 1 if request.POST.get('randomize_options') else 0
                cursor.execute("""
                    INSERT INTO multiple_choice_questions (id, correct_option_id, randomize_options)
                    VALUES (%s, %s, %s)
                """, [question_id, correct_option_id, randomize_options])
                
            elif question_type == 'essay':
                word_limit = int(request.POST.get('word_limit', 0))
                cursor.execute("""
                    INSERT INTO essay_questions (id, word_limit)
                    VALUES (%s, %s)
                """, [question_id, word_limit])
        
        messages.success(request, 'Tạo câu hỏi thành công')
        return redirect('forum:question_bank', subject_id=subject_id)
        
    except Exception as e:
        # Xóa file nếu có lỗi
        if attachment_path:
            try:
                os.remove(full_path)
            except:
                pass
        messages.error(request, f'Có lỗi xảy ra: {str(e)}')
        return redirect('forum:create_question', subject_id=subject_id)


def take_test(request, test_id):
    """Làm bài kiểm tra trực tuyến"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    user_id = request.session['user_id']
    
    try:
        with connection.cursor() as cursor:
            # Kiểm tra test
            cursor.execute("SELECT id, title, time_limit, max_attempts FROM tests WHERE id = %s", [test_id])
            test_row = cursor.fetchone()
            
            if not test_row:
                messages.error(request, 'Bài kiểm tra không tồn tại')
                return redirect('forum:index')
            
            test_info = {
                'id': test_row[0],
                'title': test_row[1],
                'time_limit': test_row[2] or 60,
                'max_attempts': test_row[3] or 1
            }
            
            # Kiểm tra số lần nộp
            cursor.execute("""
                SELECT COUNT(*) FROM submissions 
                WHERE test_id = %s AND author_id = %s
            """, [test_id, user_id])
            attempt_count = cursor.fetchone()[0]
            
            if attempt_count >= test_info['max_attempts']:
                messages.error(request, 'Bạn đã vượt quá số lần nộp bài cho phép')
                return redirect('forum:test_detail', test_id=test_id)
        
        # POST - Nộp bài
        if request.method == 'POST':
            return handle_test_submission(request, test_id, user_id, attempt_count)
        
        # GET - Hiển thị bài kiểm tra
        return display_test(request, test_id, user_id, attempt_count, test_info)
    
    except Exception as e:
        messages.error(request, f'Có lỗi xảy ra: {str(e)}')
        return redirect('forum:index')


def handle_test_submission(request, test_id, user_id, attempt_count):
    """Xử lý nộp bài - chấm tự động trắc nghiệm"""
    try:
        with connection.cursor() as cursor:
            # Tạo submission
            time_spent = int(request.POST.get('time_spent', 0))
            cursor.execute("""
                INSERT INTO submissions (test_id, author_id, attempt_number, time_spent)
                VALUES (%s, %s, %s, %s)
            """, [test_id, user_id, attempt_count + 1, time_spent])
            submission_id = cursor.lastrowid
            
            # Lấy danh sách câu hỏi
            cursor.execute("""
                SELECT 
                    tq.question_id,
                    CASE 
                        WHEN mcq.id IS NOT NULL THEN 'multiple_choice'
                        WHEN eq.id IS NOT NULL THEN 'essay'
                        ELSE 'unknown'
                    END as question_type,
                    mcq.correct_option_id
                FROM test_questions tq
                JOIN questions q ON tq.question_id = q.id
                LEFT JOIN multiple_choice_questions mcq ON q.id = mcq.id
                LEFT JOIN essay_questions eq ON q.id = eq.id
                WHERE tq.test_id = %s
                ORDER BY tq.question_order
            """, [test_id])
            
            questions = cursor.fetchall()
            
            for question_id, question_type, correct_option_id in questions:
                user_answer = request.POST.get(f'answer_{question_id}', '').strip()
                
                if question_type == 'multiple_choice' and user_answer:
                    # user_answer giờ đã là option_id
                    try:
                        selected_option_id = int(user_answer)
                    except ValueError:
                        selected_option_id = None
                    
                    if selected_option_id:
                        # Tạo answer
                        cursor.execute("""
                            INSERT INTO answers (submission_id, question_id)
                            VALUES (%s, %s)
                        """, [submission_id, question_id])
                        answer_id = cursor.lastrowid
                        
                        # Tạo multiple choice answer
                        cursor.execute("""
                            INSERT INTO multiple_choice_answers (id, selected_option_id)
                            VALUES (%s, %s)
                        """, [answer_id, selected_option_id])
                        
                elif question_type == 'essay' and user_answer:
                    # Tạo answer
                    cursor.execute("""
                        INSERT INTO answers (submission_id, question_id)
                        VALUES (%s, %s)
                    """, [submission_id, question_id])
                    answer_id = cursor.lastrowid
                    
                    # Tạo essay answer (chưa chấm)
                    cursor.execute("""
                        INSERT INTO essay_answers (id, content, is_corrected)
                        VALUES (%s, %s, NULL)
                    """, [answer_id, user_answer])
        
        messages.success(request, 'Nộp bài thành công!')
        return redirect('forum:submission_detail', submission_id=submission_id)
        
    except Exception as e:
        messages.error(request, f'Có lỗi xảy ra: {str(e)}')
        return redirect('forum:take_test', test_id=test_id)


def display_test(request, test_id, user_id, attempt_count, test_info):
    """Hiển thị bài kiểm tra"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                q.id, 
                q.content,
                CASE 
                    WHEN mcq.id IS NOT NULL THEN 'multiple_choice'
                    WHEN eq.id IS NOT NULL THEN 'essay'
                    ELSE 'unknown'
                END as question_type,
                mcq.randomize_options,
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
            question_id = row[0]
            question_type = row[2]
            
            question_data = {
                'id': question_id,
                'content': row[1],
                'type': question_type,
                'options': {},
                'randomize_options': row[3] or 0,
                'word_limit': row[4] or 0
            }
            
            # Nếu là multiple choice, lấy các options
            if question_type == 'multiple_choice':
                cursor.execute("""
                    SELECT id, content
                    FROM multiple_choice_options
                    WHERE question_id = %s
                    ORDER BY id
                """, [question_id])
                
                options = {}
                option_list = list(cursor.fetchall())
                
                # Xáo trộn nếu cần
                if question_data['randomize_options']:
                    import random
                    random.shuffle(option_list)
                
                for idx, (opt_id, opt_content) in enumerate(option_list):
                    label = chr(65 + idx)  # A, B, C, D...
                    options[label] = {
                        'id': opt_id,
                        'content': opt_content
                    }
                
                question_data['options'] = options
            
            questions.append(question_data)
    
    context = {
        'test': test_info,
        'test_id': test_id,
        'attempt_number': attempt_count + 1,
        'is_authenticated': True,
        'username': request.session.get('username'),
        'questions': questions,
    }
    
    return render(request, 'forum/take_test.html', context)


def question_bank(request, subject_id):
    """Ngân hàng câu hỏi"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                q.id, 
                q.content, 
                q.created_at,
                q.attachment_path,
                CASE 
                    WHEN mcq.id IS NOT NULL THEN 'multiple_choice'
                    WHEN eq.id IS NOT NULL THEN 'essay'
                    ELSE 'unknown'
                END as question_type,
                mcq.correct_option_id,
                mcq.randomize_options,
                eq.word_limit
            FROM questions q
            LEFT JOIN multiple_choice_questions mcq ON q.id = mcq.id
            LEFT JOIN essay_questions eq ON q.id = eq.id
            WHERE q.subject_id = %s
            ORDER BY q.created_at DESC
        """, [subject_id])
        
        questions = []
        for row in cursor.fetchall():
            question_id = row[0]
            question_type = row[4]
            
            question_data = {
                'id': question_id,
                'content': row[1],
                'created_at': row[2],
                'attachment_path': settings.MEDIA_URL + row[3] if row[3] else None,
                'type': question_type,
                'options': {},
                'correct_option_id': row[5],
                'randomize_options': row[6],
                'word_limit': row[7] or 0
            }
            
            # Nếu là multiple choice, lấy các options
            if question_type == 'multiple_choice':
                cursor.execute("""
                    SELECT id, content
                    FROM multiple_choice_options
                    WHERE question_id = %s
                    ORDER BY id
                """, [question_id])
                
                options = {}
                for idx, (opt_id, opt_content) in enumerate(cursor.fetchall()):
                    label = chr(65 + idx)  # A, B, C, D...
                    options[label] = {
                        'id': opt_id,
                        'content': opt_content,
                        'is_correct': opt_id == row[5]  # correct_option_id
                    }
                
                question_data['options'] = options
            
            questions.append(question_data)
    
    context = {
        'subject_id': subject_id,
        'username': request.session.get('username'),
        'is_authenticated': True,
        'questions': questions,
    }
    return render(request, 'forum/question_bank.html', context)


def add_questions_to_test(request, test_id):
    """Thêm câu hỏi vào bài kiểm tra"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT subject_id, title, author_id FROM tests WHERE id = %s", [test_id])
        test_info = cursor.fetchone()
        
        if not test_info:
            raise Http404("Bài kiểm tra không tồn tại")
        
        subject_id, test_title, author_id = test_info
        
        # Kiểm tra quyền tác giả
        if author_id != request.session['user_id']:
            messages.error(request, 'Bạn không có quyền chỉnh sửa bài kiểm tra này')
            return redirect('forum:test_detail', test_id=test_id)
        
        # Lấy câu hỏi chưa có trong bài kiểm tra
        cursor.execute("""
            SELECT 
                q.id, 
                q.content,
                CASE 
                    WHEN mcq.id IS NOT NULL THEN 'multiple_choice'
                    WHEN eq.id IS NOT NULL THEN 'essay'
                    ELSE 'unknown'
                END as question_type,
                eq.word_limit,
                u.username as author_name,
                mcq.correct_option_id
            FROM questions q
            LEFT JOIN multiple_choice_questions mcq ON q.id = mcq.id
            LEFT JOIN essay_questions eq ON q.id = eq.id
            LEFT JOIN users u ON q.author_id = u.id
            WHERE q.subject_id = %s
            AND q.id NOT IN (
                SELECT question_id FROM test_questions WHERE test_id = %s
            )
            ORDER BY q.created_at DESC
        """, [subject_id, test_id])
        
        available_questions = []
        for row in cursor.fetchall():
            question_id = row[0]
            question_type = row[2]
            
            question_data = {
                'id': question_id,
                'content': row[1],
                'type': question_type,
                'word_limit': row[3] or 0,
                'author_name': row[4],
                'options': {}
            }
            
            # Nếu là multiple choice, lấy các options
            if question_type == 'multiple_choice':
                cursor.execute("""
                    SELECT id, content
                    FROM multiple_choice_options
                    WHERE question_id = %s
                    ORDER BY id
                """, [question_id])
                
                options = {}
                for idx, (opt_id, opt_content) in enumerate(cursor.fetchall()):
                    label = chr(65 + idx)  # A, B, C, D...
                    options[label] = {
                        'id': opt_id,
                        'content': opt_content,
                        'is_correct': opt_id == row[5]  # correct_option_id
                    }
                
                question_data['options'] = options
            
            available_questions.append(question_data)
    
    if request.method == 'POST':
        selected_questions = request.POST.getlist('question_ids')
        
        if not selected_questions:
            messages.error(request, 'Vui lòng chọn ít nhất một câu hỏi')
            return redirect('forum:add_questions_to_test', test_id=test_id)
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(MAX(question_order), -1) FROM test_questions 
                    WHERE test_id = %s
                """, [test_id])
                max_order = cursor.fetchone()[0]
                
                for i, question_id in enumerate(selected_questions):
                    cursor.execute("""
                        INSERT INTO test_questions (test_id, question_id, question_order)
                        VALUES (%s, %s, %s)
                    """, [test_id, question_id, max_order + i + 1])
            
            messages.success(request, f'Đã thêm {len(selected_questions)} câu hỏi vào bài kiểm tra')
            return redirect('forum:test_detail', test_id=test_id)
            
        except Exception as e:
            messages.error(request, f'Có lỗi xảy ra: {str(e)}')
            return redirect('forum:add_questions_to_test', test_id=test_id)
    
    context = {
        'test_id': test_id,
        'test_title': test_title,
        'subject_id': subject_id,
        'username': request.session.get('username'),
        'is_authenticated': True,
        'available_questions': available_questions,
    }
    return render(request, 'forum/add_questions_to_test.html', context)

def submissions_history(request, test_id):
    """Lịch sử nộp bài"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    user_id = request.session['user_id']
    
    with connection.cursor() as cursor:
        # Lấy thông tin test
        cursor.execute("""
            SELECT title FROM tests WHERE id = %s
        """, [test_id])
        test_row = cursor.fetchone()
        if not test_row:
            raise Http404("Bài kiểm tra không tồn tại")
        test_title = test_row[0]
        
        # Lấy danh sách submissions
        cursor.execute("""
            SELECT id, created_at, time_spent, attempt_number
            FROM submissions
            WHERE test_id = %s AND author_id = %s
            ORDER BY created_at DESC
        """, [test_id, user_id])
        
        submissions = []
        for row in cursor.fetchall():
            submission_id = row[0]
            
            # True Hell  |
            #           \|/

            # Tính điểm cho từng submission
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_questions,
                    COALESCE(SUM(
                        CASE 
                            WHEN mcq.id IS NOT NULL AND mca.selected_option_id = mcq.correct_option_id THEN 1
                            WHEN eq.id IS NOT NULL AND ea.is_corrected = 1 THEN 1
                            ELSE 0
                        END
                    ), 0) as score
                FROM answers a
                INNER JOIN questions q ON a.question_id = q.id
                LEFT JOIN multiple_choice_questions mcq ON q.id = mcq.id
                LEFT JOIN essay_questions eq ON q.id = eq.id
                LEFT JOIN multiple_choice_answers mca ON a.id = mca.id AND mcq.id IS NOT NULL
                LEFT JOIN essay_answers ea ON a.id = ea.id AND eq.id IS NOT NULL
                WHERE a.submission_id = %s
            """, [submission_id])
            
            score_row = cursor.fetchone()
            total_questions = score_row[0] or 0
            total_score = score_row[1]
            
            submissions.append({
                'id': submission_id,
                'created_at': row[1],
                'time_spent': row[2],
                'attempt_number': row[3],
                'total_score': int(total_score) if total_score is not None else None,
                'max_score': total_questions
            })
    
    context = {
        'is_authenticated': True,
        'username': request.session.get('username'),
        'submissions': submissions,
        'test_id': test_id,
        'test_title': test_title,
    }
    return render(request, 'forum/submissions_history.html', context)


def submission_detail(request, submission_id):
    """Chi tiết bài nộp"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    with connection.cursor() as cursor:
        # Lấy thông tin submission
        cursor.execute("""
            SELECT s.id, s.created_at, s.time_spent, s.attempt_number,
                   s.test_id, s.author_id, t.title
            FROM submissions s
            JOIN tests t ON s.test_id = t.id
            WHERE s.id = %s
        """, [submission_id])
        
        submission_row = cursor.fetchone()
        if not submission_row:
            raise Http404("Bài nộp không tồn tại")
        
        # Lấy danh sách câu trả lời với thông tin chi tiết
        cursor.execute("""
            SELECT 
                a.id,
                q.id as question_id,
                q.content as question_content,
                CASE 
                    WHEN mcq.id IS NOT NULL THEN 'multiple_choice'
                    WHEN eq.id IS NOT NULL THEN 'essay'
                    ELSE 'unknown'
                END as question_type,
                mcq.correct_option_id,
                mca.selected_option_id,
                ea.content as essay_content,
                ea.is_corrected
            FROM answers a
            JOIN questions q ON a.question_id = q.id
            LEFT JOIN multiple_choice_questions mcq ON q.id = mcq.id
            LEFT JOIN essay_questions eq ON q.id = eq.id
            LEFT JOIN multiple_choice_answers mca ON a.id = mca.id
            LEFT JOIN essay_answers ea ON a.id = ea.id
            WHERE a.submission_id = %s
            ORDER BY a.id
        """, [submission_id])
        
        answers = []
        total_score = 0
        total_questions = 0
        
        for row in cursor.fetchall():
            question_type = row[3]
            score = None
            answer_content = ''
            is_correct = False
            correct_answer_text = ''
            user_answer_text = ''
            
            if question_type == 'multiple_choice':
                correct_option_id = row[4]
                selected_option_id = row[5]
                
                # Lấy text của đáp án
                cursor.execute("""
                    SELECT id, content
                    FROM multiple_choice_options
                    WHERE question_id = %s
                    ORDER BY id
                """, [row[1]])
                
                options = list(cursor.fetchall())
                for idx, (opt_id, opt_content) in enumerate(options):
                    label = chr(65 + idx)
                    if opt_id == selected_option_id:
                        user_answer_text = f"{label}. {opt_content}"
                    if opt_id == correct_option_id:
                        correct_answer_text = f"{label}. {opt_content}"
                
                # Chấm điểm
                is_correct = (selected_option_id == correct_option_id)
                score = 1 if is_correct else 0
                answer_content = user_answer_text
                total_score += score
                total_questions += 1
                
            elif question_type == 'essay':
                answer_content = row[6] or ''
                is_corrected = row[7]
                
                if is_corrected is not None:
                    score = 1 if is_corrected == 1 else 0
                    total_score += score
                    total_questions += 1
                else:
                    score = None  # Chưa chấm
                    total_questions += 1
            
            answers.append({
                'id': row[0],
                'question_id': row[1],
                'question_content': row[2],
                'question_type': question_type,
                'answer_content': answer_content,
                'score': score,
                'is_correct': is_correct,
                'correct_answer': correct_answer_text,
                'is_corrected': row[7] if question_type == 'essay' else True
            })
    
        # Kiểm tra xem người xem có phải là tác giả bài kiểm tra không
        cursor.execute("SELECT author_id FROM tests WHERE id = %s", [submission_row[4]])
        is_test_author = (cursor.fetchone()[0] == request.session['user_id'])

    context = {
        'username': request.session.get('username'),
        'is_authenticated': True,
        'is_test_author': is_test_author,
        'submission': {
            'id': submission_row[0],
            'created_at': submission_row[1],
            'time_spent': submission_row[2],
            'attempt_number': submission_row[3],
            'test_id': submission_row[4],
            'author_id': submission_row[5],
            'test_title': submission_row[6],
            'total_score': total_score,
            'max_score': total_questions
        },
        'answers': answers,
        'total_questions': total_questions
    }
    return render(request, 'forum/submission_detail.html', context)


def grade_submission(request, submission_id):
    """Chấm điểm bài nộp (chỉ tác giả bài kiểm tra)"""
    if not request.session.get('user_id'):
        messages.warning(request, 'Vui lòng đăng nhập để tiếp tục')
        return redirect('accounts:login')
    
    user_id = request.session['user_id']
    
    with connection.cursor() as cursor:
        # Kiểm tra quyền chấm bài (phải là tác giả của test)
        cursor.execute("""
            SELECT t.id, t.title, t.author_id, s.author_id as student_id
            FROM submissions s
            JOIN tests t ON s.test_id = t.id
            WHERE s.id = %s
        """, [submission_id])
        
        row = cursor.fetchone()
        if not row:
            raise Http404("Bài nộp không tồn tại")
        
        test_id, test_title, test_author_id, student_id = row
        
        if test_author_id != user_id:
            messages.error(request, 'Bạn không có quyền chấm bài này')
            return redirect('forum:submission_detail', submission_id=submission_id)
        
        # Xử lý POST - lưu điểm chấm
        if request.method == 'POST':
            try:
                # Lấy điểm chấm cho từng câu tự luận
                for key, value in request.POST.items():
                    if key.startswith('grade_'):
                        answer_id = int(key.split('_')[1])
                        is_correct = int(value)  # 1 = đúng, 0 = sai
                        
                        cursor.execute("""
                            UPDATE essay_answers
                            SET is_corrected = %s
                            WHERE id = %s
                        """, [is_correct, answer_id])
                
                messages.success(request, 'Đã chấm bài thành công!')
                return redirect('forum:submission_detail', submission_id=submission_id)
            
            except Exception as e:
                messages.error(request, f'Lỗi khi chấm bài: {str(e)}')
        
        # Lấy danh sách câu hỏi tự luận chưa chấm
        cursor.execute("""
            SELECT 
                a.id,
                q.content as question_content,
                ea.content as answer_content,
                ea.is_corrected,
                eq.word_limit
            FROM answers a
            JOIN questions q ON a.question_id = q.id
            JOIN essay_questions eq ON q.id = eq.id
            JOIN essay_answers ea ON a.id = ea.id
            WHERE a.submission_id = %s
            ORDER BY a.id
        """, [submission_id])
        
        essay_answers = []
        for row in cursor.fetchall():
            essay_answers.append({
                'answer_id': row[0],
                'question_content': row[1],
                'answer_content': row[2],
                'is_corrected': row[3],
                'word_limit': row[4]
            })
        
        # Lấy thông tin sinh viên
        cursor.execute("""
            SELECT u.username, u.first_name, u.last_name
            FROM users u
            WHERE u.id = %s
        """, [student_id])
        
        student_row = cursor.fetchone()
        student_name = f"{student_row[1]} {student_row[2]}".strip() or student_row[0]
    
    context = {
        'is_authenticated': True,
        'username': request.session.get('username'),
        'submission_id': submission_id,
        'test_title': test_title,
        'student_name': student_name,
        'essay_answers': essay_answers
    }
    
    return render(request, 'forum/grade_submission.html', context)
