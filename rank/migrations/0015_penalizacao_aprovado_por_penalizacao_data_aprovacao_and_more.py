# Generated by Django 5.2.3 on 2025-06-30 17:27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rank', '0014_equipe_tempo_total'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='penalizacao',
            name='aprovado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='penalizacoes_aprovadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='penalizacao',
            name='data_aprovacao',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='penalizacao',
            name='status',
            field=models.CharField(choices=[('pendente', 'Pendente'), ('aprovado', 'Aprovado'), ('rejeitado', 'Rejeitado')], default='pendente', max_length=10),
        ),
        migrations.AddField(
            model_name='pontuacao',
            name='aprovado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pontuacoes_aprovadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='pontuacao',
            name='data_aprovacao',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pontuacao',
            name='status',
            field=models.CharField(choices=[('pendente', 'Pendente'), ('aprovado', 'Aprovado'), ('rejeitado', 'Rejeitado')], default='pendente', max_length=10),
        ),
    ]
