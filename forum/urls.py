from django.urls import path
from . import views


urlpatterns = [
    path('', views.forum_view, name='forum'),
    # path('forums/', views.forum_list, name='forums'),
]