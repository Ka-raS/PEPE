from django.urls import path

from . import views

app_name = 'search'

urlpatterns = [
    path('', views.index, name='index'),
    path('users/', views.search_users, name='users'),
    path('posts/', views.search_posts, name='posts'),
    path('tests/', views.search_tests, name='tests'),
]