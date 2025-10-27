from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('',views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('referral/',views.referral, name='referral'),
    path('wallet/',views.wallet, name='wallet'),
    path('checkin/', views.checkin_view, name='checkin'),
]