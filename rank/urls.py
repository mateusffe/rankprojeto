from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'), # Dashboard para superuser
    path('staff-dashboard/<int:circuito_id>/', views.staff_dashboard, name='staff_dashboard'), # Dashboard para staff
    path('ranking/<int:circuito_id>/', views.ranking_view, name='ranking'),
    path('cadastrar-equipe/', views.cadastrar_equipe, name='cadastrar_equipe'),
    path('cadastrar-staff/', views.cadastrar_staff, name='cadastrar_staff'),
    path('cadastrar-membro/', views.cadastrar_membro, name='cadastrar_membro'),
    path('cadastrar-atividade/', views.cadastrar_atividade, name='cadastrar_atividade'),
    path('criar-pontuacao/', views.criar_pontuacao, name='criar_pontuacao'),
    path('criar-penalizacao/', views.criar_penalizacao, name='criar_penalizacao'),
    path('criar-circuito/', views.criar_circuito, name='criar_circuito'),
    path('equipe/<int:equipe_id>/', views.equipe_detail_view, name='equipe_detail'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='dashboard'), name='logout'),
    path('listar/<str:modelo>/<int:circuito_id>/', views.listar_modelo, name='listar_modelo'),
    path('excluir/<str:modelo>/<int:pk>/', views.excluir_modelo, name='excluir_modelo'),
    path('editar/<str:modelo>/<int:pk>/', views.editar_modelo, name='editar_modelo'), # Adicionado para edição
    path('circuitos-inativos/', views.listar_circuitos_inativos, name='listar_circuitos_inativos'), # Nova URL
    path('circuitos-ativos/', views.listar_circuitos_ativos, name='listar_circuitos_ativos'),
    path('staff/', views.listar_staff, name='listar_staff'),
    path('staff/editar/<int:pk>/', views.editar_staff, name='editar_staff'),
    path('staff/excluir/<int:pk>/', views.excluir_staff, name='excluir_staff'),
    path('membros/', views.listar_membros, name='listar_membros'),
    path('membros/editar/<int:pk>/', views.editar_membro, name='editar_membro'),
    path('membros/excluir/<int:pk>/', views.excluir_membro, name='excluir_membro'),



]