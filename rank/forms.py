# /forms.py

from django import forms
from .models import Equipe, Membro, Pontuacao, Penalizacao, Circuito, StaffProfile
from django.contrib.auth.models import User

class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = field.widget.attrs.get('class', '')
            if 'form-control' not in css_class:
                field.widget.attrs['class'] = (css_class + ' form-control').strip()

class EquipeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Equipe
        fields = ['circuito', 'nome', 'brasao']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            self.fields['circuito'].queryset = user.staffprofile.circuitos.all()
            if user.staffprofile.circuitos.count() == 1:
                self.fields['circuito'].initial = user.staffprofile.circuitos.first()
                self.fields['circuito'].widget = forms.HiddenInput()

class MembroForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Membro
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.fields['circuito_filtro'] = forms.ModelChoiceField(
            queryset=Circuito.objects.all(),
            label="Filtrar Equipes por Circuito",
            required=False,
            empty_label="Todos os Circuitos"
        )
        self.fields['circuito_filtro'].widget.attrs.update({'onchange': 'filterEquipes(this.value)'})

        if user and not user.is_superuser:
            staff_circuitos_ids = user.staffprofile.circuitos.values_list('id', flat=True)
            self.fields['equipe'].queryset = Equipe.objects.filter(circuito__id__in=staff_circuitos_ids)
        else:
            self.fields['equipe'].queryset = Equipe.objects.all()

        for equipe in self.fields['equipe'].queryset:
            self.fields['equipe'].widget.attrs.update({f'data-circuito-{equipe.id}': equipe.circuito.id if equipe.circuito else ''})

# /forms.py



# /forms.py

from django import forms
from .models import Pontuacao, Equipe, Circuito


class PontuacaoForm(forms.ModelForm):
    horas = forms.IntegerField(min_value=0, required=False, help_text="Horas")
    minutos = forms.IntegerField(min_value=0, max_value=59, required=False, help_text="Minutos")
    segundos = forms.IntegerField(min_value=0, max_value=59, required=False, help_text="Segundos")

    class Meta:
        model = Pontuacao
        exclude = ['tempo_em_segundos']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # … aqui vai sua lógica de filtrar circuitos/equipes …

        if self.instance and self.instance.tempo_em_segundos is not None:
            total = self.instance.tempo_em_segundos
            self.fields['horas'].initial = total // 3600
            self.fields['minutos'].initial = (total % 3600) // 60
            self.fields['segundos'].initial = total % 60

    def clean(self):
        data = super().clean()
        circuito = data.get('circuito')

        if circuito and circuito.modo_ranking == 'tempo':
            h = data.get('horas') or 0
            m = data.get('minutos') or 0
            s = data.get('segundos') or 0
            total = h*3600 + m*60 + s
            if total <= 0:
                raise forms.ValidationError("Para atividades por tempo, o tempo não pode ser zero.")
            data['tempo_calculado'] = total
            data['valor'] = None
        else:
            data['horas'] = data['minutos'] = data['segundos'] = None
            data['tempo_calculado'] = None
            if circuito and not circuito.pontuacao_fixa and data.get('valor') is None:
                self.add_error('valor', "Esta atividade não tem pontuação fixa. Informe o valor.")

        equipe = data.get('equipe')
        if equipe and circuito and equipe.circuito != circuito:
            self.add_error('equipe', "A equipe não pertence ao circuito selecionado.")

        return data

    def _post_clean(self):
        # primeiro injetamos o valor calculado na instância
        tempo = self.cleaned_data.get('tempo_calculado')
        if tempo is not None:
            self.instance.tempo_em_segundos = tempo

        # somente depois chamamos o super, que faz model.full_clean()
        super()._post_clean()

    def save(self, commit=True):
        obj = super().save(commit=False)
        tempo = self.cleaned_data.get('tempo_calculado')
        if tempo is not None:
            obj.tempo_em_segundos = tempo
        if commit:
            obj.save()
        return obj

class PenalizacaoForm(forms.ModelForm):
    horas = forms.IntegerField(min_value=0, required=False, help_text="Horas")
    minutos = forms.IntegerField(min_value=0, max_value=59, required=False, help_text="Minutos")
    segundos = forms.IntegerField(min_value=0, max_value=59, required=False, help_text="Segundos")

    class Meta:
        model = Penalizacao
        exclude = ['tempo_em_segundos']   # removido fields='__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # … sua lógica de filtrar circuitos/equipes …

        if self.instance and self.instance.tempo_em_segundos is not None:
            total = self.instance.tempo_em_segundos
            self.fields['horas'].initial = total // 3600
            self.fields['minutos'].initial = (total % 3600) // 60
            self.fields['segundos'].initial = total % 60

    def clean(self):
        data = super().clean()
        circuito = data.get('circuito')

        if circuito and circuito.modo_ranking == 'tempo':
            h = data.get('horas') or 0
            m = data.get('minutos') or 0
            s = data.get('segundos') or 0
            total = h*3600 + m*60 + s
            if total <= 0:
                raise forms.ValidationError("Para penalizações por tempo, o tempo não pode ser zero.")
            data['tempo_calculado'] = total
            data['valor'] = None
        else:
            data['horas'] = data['minutos'] = data['segundos'] = None
            data['tempo_calculado'] = None
            if data.get('valor') is None:
                self.add_error('valor', "Informe o valor da penalização.")
            elif data.get('valor') >= 0:
                self.add_error('valor', "O valor da penalização deve ser negativo.")

        equipe = data.get('equipe')
        if equipe and circuito and equipe.circuito != circuito:
            self.add_error('equipe', "A equipe não pertence ao circuito selecionado.")

        return data

    def _post_clean(self):
        # injeta o tempo antes de rodar model.full_clean()
        tempo = self.cleaned_data.get('tempo_calculado')
        if tempo is not None:
            self.instance.tempo_em_segundos = tempo
        super()._post_clean()

    def save(self, commit=True):
        obj = super().save(commit=False)
        tempo = self.cleaned_data.get('tempo_calculado')
        if tempo is not None:
            obj.tempo_em_segundos = tempo
        if commit:
            obj.save()
        return obj


class CircuitoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Circuito
        fields =  '__all__'
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['modo_ranking'].widget.attrs.update({'onchange': 'togglePontuacaoFixaFields()'})


class StaffCreationForm(forms.Form):
    username = forms.CharField(max_length=150, label="Usuário")
    password = forms.CharField(widget=forms.PasswordInput, label="Senha", required=False)
    is_superuser = forms.BooleanField(required=False, label="É Superusuário?")


class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = ['circuitos']
        widgets = {
            'circuitos': forms.CheckboxSelectMultiple
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['circuitos'].queryset = Circuito.objects.filter(ativo=True)


class PontuacaoAuthorizationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Pontuacao
        fields = ['status', 'aprovado_por', 'data_aprovacao']
        widgets = {
            'status': forms.Select(choices=Pontuacao.STATUS_CHOICES),
            'aprovado_por': forms.HiddenInput(),
            'data_aprovacao': forms.HiddenInput(),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aprovado_por'].queryset = User.objects.filter(is_superuser=True)

class PenalizacaoAuthorizationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Penalizacao
        fields = ['status', 'aprovado_por', 'data_aprovacao']
        widgets = {
            'status': forms.Select(choices=Penalizacao.STATUS_CHOICES),
            'aprovado_por': forms.HiddenInput(),
            'data_aprovacao': forms.HiddenInput(),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aprovado_por'].queryset = User.objects.filter(is_superuser=True)
