from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('',views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('update-avatar/', views.update_avatar, name='update_avatar'),

    path('api/link-wallet/', views.api_link_wallet, name='api_link_wallet'),
    path('api/unlink-wallet/', views.unlink_wallet, name='unlink_wallet'),
    path('api/get-balance/', views.api_get_balance, name='api_get_balance'),
    path('api/checkin', views.api_checkin, name='api_checkin'),
    path('api/deposit/', views.api_deposit, name='api_deposit'),
    path('api/withdraw/', views.api_withdraw, name='api_withdraw'),
    path('api/transfer/', views.api_transfer_p2p, name='api_transfer_p2p'),
    path('api/buy-content/', views.api_buy_content, name='api_buy_content'),
    path('api/claim-referral/', views.api_claim_referral_reward, name='api_claim_referral_reward'),
]