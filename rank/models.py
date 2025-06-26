from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User 

class Circuito(models.Model):
    nome = models.CharField(max_length=100)
    data_inicio = models.DateField(auto_now_add=True)
    data_encerramento = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)  # True enquanto está ativo

    def __str__(self):
        return self.nome

    @property
    def encerrado(self):
        # Circuito é encerrado se a data de encerramento já passou ou ativo=False
        if self.data_encerramento and self.data_encerramento < timezone.now().date():
            return True
        return not self.ativo

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staffprofile')
    circuitos = models.ManyToManyField(Circuito, related_name='staff_membros', blank=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"

class Equipe(models.Model):
    circuito = models.ForeignKey(Circuito, on_delete=models.CASCADE, null=True, blank=True, related_name='equipes')
    nome = models.CharField(max_length=100)
    cor = models.CharField(max_length=20, blank=True, null=True)

    def pontuacao_total(self):
        ganhos = self.pontuacoes.aggregate(models.Sum('valor'))['valor__sum'] or 0
        perdas = self.penalizacoes.aggregate(models.Sum('valor'))['valor__sum'] or 0
        return ganhos - perdas

    def __str__(self):
        return self.nome

class Membro(models.Model):
    nome = models.CharField(max_length=100)
    equipe = models.ForeignKey(Equipe, related_name='membros', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.nome} ({self.equipe.nome})'

class Atividade(models.Model):
    circuito = models.ForeignKey(Circuito, on_delete=models.CASCADE, null=True, blank=True)
    TIPO_CHOICES = (
        ('prova', 'Prova'),
        ('brincadeira', 'Brincadeira'),
    )
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
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

class Pontuacao(models.Model):
    circuito = models.ForeignKey(Circuito, on_delete=models.CASCADE, null=True, blank=True)
    equipe = models.ForeignKey(Equipe, related_name='pontuacoes', on_delete=models.CASCADE)
    atividade = models.ForeignKey(Atividade, related_name='pontuacoes', on_delete=models.CASCADE)
    valor = models.IntegerField(blank=True, null=True)
    data = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        if not self.atividade:
            return  # evitar erro se atividade ainda não foi escolhida
        if not self.atividade.pontuacao_fixa and self.valor is None:
            raise ValidationError({'valor': "Esta Atividade não tem Pontuação Fixa, favor informar o valor."})
        # Garante que o circuito da pontuação seja o mesmo da atividade e da equipe
        if self.atividade and self.equipe:
            if self.atividade.circuito != self.equipe.circuito:
                raise ValidationError("A atividade e a equipe devem pertencer ao mesmo circuito.")
            self.circuito = self.atividade.circuito # Define o circuito da pontuação

    def save(self, *args, **kwargs):
        # Se a atividade tem pontuação fixa, substitui o valor manual pelo valor_padrao
        if self.atividade.pontuacao_fixa:
            self.valor = self.atividade.valor_padrao
        # Garante que o circuito da pontuação seja o mesmo da atividade
        if self.atividade and not self.circuito:
            self.circuito = self.atividade.circuito
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.equipe.nome} +{self.valor} ({self.atividade.nome})'

class Penalizacao(models.Model):
    circuito = models.ForeignKey(Circuito, on_delete=models.CASCADE, null=True, blank=True)
    equipe = models.ForeignKey(Equipe, related_name='penalizacoes', on_delete=models.CASCADE)
    motivo = models.TextField()
    valor = models.IntegerField(help_text="Valor negativo")
    data = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Garante que o circuito da penalização seja o mesmo da equipe
        if self.equipe:
            self.circuito = self.equipe.circuito # Define o circuito da penalização

    def save(self, *args, **kwargs):
        # Garante que o circuito da penalização seja o mesmo da equipe
        if self.equipe and not self.circuito:
            self.circuito = self.equipe.circuito
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.equipe.nome} {self.valor} ({self.motivo})'
    