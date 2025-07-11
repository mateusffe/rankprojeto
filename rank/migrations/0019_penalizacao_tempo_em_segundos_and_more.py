# Generated by Django 5.2.3 on 2025-07-03 16:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rank', '0018_rename_tempo_em_minutos_equipe_tempo_em_segundos_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='penalizacao',
            name='tempo_em_segundos',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='penalizacao',
            name='valor',
            field=models.IntegerField(blank=True, help_text='Valor negativo (se não for por tempo)', null=True),
        ),
    ]
