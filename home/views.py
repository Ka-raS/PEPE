from django.shortcuts import render
from django.db import connection

import accounts.sql
import forum.sql


def index(request):
    user_id = request.session.get('user_id')

    if not user_id or user_id == 'None':
        # Khách
        context = {'is_authenticated': False}        
        context['user_count'] = accounts.sql.user_count()

    else:    
        # USER ĐÃ ĐĂNG NHẬP
        context = {
            'is_authenticated': True,
            'username': request.session.get('username'),
        }
    
    context['suggested_posts'] = forum.sql.posts_with_attachment(5)
    context['popular_posts'] = forum.sql.popular_posts(5)
    context['latest_posts'] = forum.sql.latest_posts(5)
    context['latest_tests'] = forum.sql.latest_tests(5)

    return render(request, 'home/index.html', context)