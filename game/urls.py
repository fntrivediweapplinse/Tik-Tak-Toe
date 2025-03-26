from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('new/', views.new_game, name='new_game'),
    path('join/<int:game_id>/', views.join_game, name='join_game'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    path('game/<int:game_id>/move/', views.make_move, name='make_move'),
    path('game/<int:game_id>/delete/', views.delete_game, name='delete_game'),
    path('game/<int:game_id>/rematch/', views.request_rematch, name='request_rematch'),
    path('enter-name/', views.enter_name, name='enter_name'),
]
