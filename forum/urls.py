from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.index, name='index'),
    path('subject/<int:subject_id>/', views.subject_detail, name='subject_detail'),
    path('quiz/<int:quiz_id>/', views.quiz_detail, name='quiz_detail'),
    path('quiz/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('attempt/<int:attempt_id>/', views.take_quiz, name='take_quiz'),
    path('attempt/<int:attempt_id>/result/', views.quiz_result, name='quiz_result'),
    path('post/new/', views.create_post, name='create_post'),
    path('post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('test/new/', views.create_test, name='create_test'),
    path('quiz/new/', views.create_quiz, name='create_quiz'),
    path('test/<int:test_id>/take/', views.take_test, name='take_test'),
]