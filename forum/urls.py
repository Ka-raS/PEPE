from django.urls import path, re_path
from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.index, name='index'),
    path('subject/<int:subject_id>/', views.subject_detail, name='subject_detail'),

    path('post/new/', views.create_post, name='create_post'),
    path('post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/<int:post_id>/vote/', views.vote_post, name='vote_post'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    re_path(r'^comment/(?P<comment_id>[^/]+)/delete/$', views.delete_comment, name='delete_comment'),

    path('create_test/<int:subject_id>/', views.create_test, name='create_test'),
    path('take_test/<int:test_id>/', views.take_test, name='take_test'),
    path('test/<int:test_id>/', views.test_detail, name='test_detail'),
    
    path('create_question/<int:subject_id>/', views.create_question, name='create_question'),
    path('question_bank/<int:subject_id>/', views.question_bank, name='question_bank'),
    path('add_questions_to_test/<int:test_id>/', views.add_questions_to_test, name='add_questions_to_test'),

    path('submission/<int:submission_id>/', views.submission_detail, name='submission_detail'),
    path('submissions_history/<int:test_id>/', views.submissions_history, name='submissions_history'),
    path('submission/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
]