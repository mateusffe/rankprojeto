from django.contrib import admin
from .models import Equipe, Membro, Atividade, Pontuacao, Penalizacao, Circuito
from django.contrib.admin import AdminSite


admin.site.site_header = "Painel Administrativo"
admin.site.site_title = "Administração"
admin.site.index_title = "Bem-vindo ao painel"

admin.site.register(Equipe)
admin.site.register(Membro)
admin.site.register(Atividade)
admin.site.register(Pontuacao)
admin.site.register(Penalizacao)
admin.site.register(Circuito)