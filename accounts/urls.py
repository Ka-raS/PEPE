from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('',views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('update-avatar/', views.update_avatar, name='update_avatar'),

    # path('teacher/', views.index_teacher, name='index_teacher'),
    # path('referral/',views.referral, name='referral'),
    # path('wallet/',views.wallet, name='wallet'),
    # path('checkin/', views.checkin_view, name='checkin'),
    # path('profile/update-avatar/', views.update_avatar_view, name='update_avatar'),
]