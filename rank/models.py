# /models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User

class Circuito(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(max_length=500, null=True, blank=True)
    ativo = models.BooleanField(default=True)

    TIPO_CHOICES = (
        ('prova', 'Prova'),
        ('brincadeira', 'Brincadeira'),
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='prova')

    MODO_RANKING = (
        ('pontuacao', 'Por Pontuação'),
        ('tempo', 'Por Tempo (quanto menor, melhor)'),
    )
    modo_ranking = models.CharField(
        max_length=20,
        choices=MODO_RANKING,
        default='pontuacao',
        help_text="Define como o ranking será ordenado: por pontos ou por tempo"
    )

    pontuacao_fixa = models.BooleanField(default=False)
    valor_padrao = models.IntegerField(default=0, help_text="Usado se a pontuação for fixa")

    responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_staff': True},
        related_name='atividades_responsaveis'
    )

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_display()})'

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staffprofile')
    circuitos = models.ManyToManyField(Circuito, related_name='staff_membros', blank=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"

class Equipe(models.Model):
    circuito = models.ForeignKey(Circuito, on_delete=models.CASCADE, null=True, blank=True, related_name='equipes')
    nome = models.CharField(max_length=100)
    brasao = models.ImageField(upload_to='brasoes/', blank=True, null=True)
    tempo_em_segundos = models.PositiveIntegerField(null=True, blank=True) # NOVO CAMPO

    def pontuacao_total(self):
        ganhos = self.pontuacoes.filter(status='aprovado').aggregate(models.Sum('valor'))['valor__sum'] or 0
        perdas = self.penalizacoes.filter(status='aprovado').aggregate(models.Sum('valor'))['valor__sum'] or 0
        return ganhos - perdas

    @property
    def tempo_formatado(self):
        if self.tempo_em_segundos is not None:
            total_seconds = self.tempo_em_segundos
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "N/A" # Alterado para N/A para clareza

    def __str__(self):
        return self.nome

class Membro(models.Model):
    nome = models.CharField(max_length=100)
    equipe = models.ForeignKey(Equipe, related_name='membros', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.nome} ({self.equipe.nome})'

class Pontuacao(models.Model):
    circuito = models.ForeignKey(Circuito, on_delete=models.CASCADE, null=True, blank=True)
    equipe = models.ForeignKey(Equipe, related_name='pontuacoes', on_delete=models.CASCADE)
    valor = models.IntegerField(blank=True, null=True)
    data = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    tempo_em_segundos = models.PositiveIntegerField(null=True, blank=True) # NOVO CAMPO

    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    aprovado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pontuacoes_aprovadas')
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if not self.circuito:
            raise ValidationError("É necessário informar a atividade (circuito).")
        # A validação do valor só ocorre se o circuito não for por tempo E não tiver pontuação fixa
        if self.circuito and self.circuito.modo_ranking != 'tempo' and not self.circuito.pontuacao_fixa and self.valor is None:
            raise ValidationError({'valor': "Esta atividade não tem pontuação fixa. Informe o valor."})
        
        # Se o modo de ranking for 'tempo', o valor não é obrigatório
        if self.circuito and self.circuito.modo_ranking == 'tempo' and self.valor is not None:
            self.valor = None # Limpar o valor se for por tempo e um valor foi acidentalmente inserido
        
        # Validação para tempo_em_segundos
        if self.circuito and self.circuito.modo_ranking == 'tempo' and self.tempo_em_segundos is None:
            raise ValidationError("Esta atividade é por tempo. Informe o tempo em horas, minutos ou segundos.")
        
        if self.equipe and self.equipe.circuito != self.circuito:
            raise ValidationError("A equipe e a pontuação devem estar ligadas à mesma atividade.")
        
    def save(self, *args, **kwargs):
        if self.circuito:
            if self.circuito.pontuacao_fixa and self.circuito.modo_ranking != 'tempo':
                self.valor = self.circuito.valor_padrao
            elif self.circuito.modo_ranking == 'tempo':
                self.valor = None # Garante que valor é None se for por tempo

        # Atualiza o tempo da equipe quando status for 'aprovado' e modo de ranking for 'tempo'
        if self.status == 'aprovado' and self.circuito.modo_ranking == 'tempo':
            # Verifica se o tempo atual da equipe é None ou se o novo tempo é menor
            if self.equipe.tempo_em_segundos is None or self.tempo_em_segundos < self.equipe.tempo_em_segundos:
                self.equipe.tempo_em_segundos = self.tempo_em_segundos
                self.equipe.save()
        
        # Garante a coerência
        if self.equipe and not self.circuito:
            self.circuito = self.equipe.circuito
            
        super().save(*args, **kwargs)

    def __str__(self):
        status_display = self.get_status_display()
        if self.circuito and self.circuito.modo_ranking == 'tempo':
            return f'{self.equipe.nome} ({self.tempo_formatado()}) ({self.circuito.nome}) - {status_display}'
        return f'{self.equipe.nome} +{self.valor} ({self.circuito.nome}) - {status_display}'
    
    def tempo_formatado(self):
        if self.tempo_em_segundos is not None:
            total_seconds = self.tempo_em_segundos
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "N/A"

class Penalizacao(models.Model):
    circuito = models.ForeignKey(Circuito, on_delete=models.CASCADE, null=True, blank=True)
    equipe = models.ForeignKey(Equipe, related_name='penalizacoes', on_delete=models.CASCADE)
    motivo = models.TextField()
    valor = models.IntegerField(blank=True, null=True, help_text="Valor negativo (se não for por tempo)") # Alterado para blank=True, null=True
    data = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    tempo_em_segundos = models.PositiveIntegerField(null=True, blank=True) # NOVO CAMPO PARA PENALIZAÇÃO DE TEMPO

    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    aprovado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='penalizacoes_aprovadas')
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if not self.circuito:
            raise ValidationError("É necessário informar a atividade (circuito).")

        if self.circuito.modo_ranking == 'tempo':
            if self.tempo_em_segundos is None:
                raise ValidationError({'tempo_em_segundos': "Esta penalização é por tempo. Informe o tempo em horas, minutos ou segundos."})
            if self.valor is not None:
                self.valor = None # Garante que valor é None se for por tempo
        else: # Modo de ranking é 'pontuacao'
            if self.valor is None:
                raise ValidationError({'valor': "Informe o valor da penalização."})
            if self.valor >= 0:
                raise ValidationError({'valor': "O valor da penalização deve ser negativo."})
            if self.tempo_em_segundos is not None:
                self.tempo_em_segundos = None # Garante que tempo é None se for por pontuação

        if self.equipe and self.equipe.circuito != self.circuito:
            raise ValidationError("A equipe e a penalização devem estar ligadas à mesma atividade.")
        
    
    def save(self, *args, **kwargs):
        # garante circuito vindo da equipe
        if not self.circuito and self.equipe:
            self.circuito = self.equipe.circuito
        
        super().save(*args, **kwargs)  # primeiro salva a penalização em si

        # se for aprovada e por tempo, *subtrai* o tempo da equipe
        if self.status == 'aprovado' and self.circuito.modo_ranking == 'tempo' and self.tempo_em_segundos is not None:
            # busca o tempo atual da equipe (pode ser None)
            atual = self.equipe.tempo_em_segundos or 0
            novo = atual + self.tempo_em_segundos
            # opcional: não deixar negativo
            self.equipe.tempo_em_segundos = max(novo, 0)
            self.equipe.save()

    def __str__(self):
        status_display = self.get_status_display()
        if self.circuito and self.circuito.modo_ranking == 'tempo':
            return f'{self.equipe.nome} -{self.tempo_formatado()} ({self.motivo}) - {status_display}'
        return f'{self.equipe.nome} {self.valor} ({self.motivo}) - {status_display}'

    def tempo_formatado(self):
        if self.tempo_em_segundos is not None:
            total_seconds = self.tempo_em_segundos
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "N/A"
