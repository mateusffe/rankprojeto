from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),

    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),  # Superusuário
    path('staff-dashboard/<int:circuito_id>/', views.staff_dashboard, name='staff_dashboard'),

    # Ranking
    path('ranking/<int:circuito_id>/', views.ranking_view, name='ranking'),

    # Cadastro
    path('cadastrar-equipe/', views.cadastrar_equipe, name='cadastrar_equipe'),
    path('cadastrar-membro/', views.cadastrar_membro, name='cadastrar_membro'),
    path('cadastrar-staff/', views.cadastrar_staff, name='cadastrar_staff'),
    path('cadastrar-circuito/', views.criar_circuito, name='cadastrar_circuito'),
    path('criar-pontuacao/', views.criar_pontuacao, name='criar_pontuacao'),
    path('criar-penalizacao/', views.criar_penalizacao, name='criar_penalizacao'),

    # Detalhes
    path('equipe/<int:equipe_id>/', views.equipe_detail_view, name='equipe_detail'),

    # Autenticação
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='dashboard'), name='logout'),

    # Listagem genérica
    path('listar/<str:modelo>/<int:circuito_id>/', views.listar_modelo, name='listar_modelo'),
    path('editar/<str:modelo>/<int:pk>/', views.editar_modelo, name='editar_modelo'),
    path('excluir/<str:modelo>/<int:pk>/', views.excluir_modelo, name='excluir_modelo'),

    # Circuitos ativos/inativos agora representam o que eram antes as "atividades"
    path('circuitos-ativos/', views.listar_circuitos_ativos, name='listar_circuitos_ativos'),
    path('circuitos-inativos/', views.listar_circuitos_inativos, name='listar_circuitos_inativos'),

    # Staff
    path('staff/', views.listar_staff, name='listar_staff'),
    path('staff/editar/<int:pk>/', views.editar_staff, name='editar_staff'),
    path('staff/excluir/<int:pk>/', views.excluir_staff, name='excluir_staff'),

    # Membros
    path('membros/', views.listar_membros, name='listar_membros'),
    path('membros/editar/<int:pk>/', views.editar_membro, name='editar_membro'),
    path('membros/excluir/<int:pk>/', views.excluir_membro, name='excluir_membro'),
    path('autorizacoes/', views.listar_autorizacoes_pendentes, name='listar_autorizacoes_pendentes'),
    path('autorizar/<str:modelo>/<int:pk>/', views.autorizar_item, name='autorizar_item'),
    path('inativar/<int:pk>', views.inativar, name='inativar'),
    path('excluir_prova/<int:pk>', views.excluir_prova, name='exc_pr'),
      # URLs para AJAX
    path('api/equipes_by_circuito/<int:circuito_id>/', views.get_equipes_by_circuito, name='api_equipes_by_circuito'),
    path('api/all_equipes/', views.get_all_equipes, name='api_all_equipes'),
    path('api/circuito_details/<int:circuito_id>/', views.get_circuito_details, name='api_circuito_details'),
] 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)