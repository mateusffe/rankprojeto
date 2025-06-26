from django import forms
from .models import Equipe, Membro, Atividade, Pontuacao, Penalizacao, Circuito, StaffProfile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm


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
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            # Filtra os circuitos disponíveis para o staff
            self.fields['circuito'].queryset = user.staffprofile.circuitos.all()
            # Se o staff só tem um circuito, pré-seleciona e desabilita o campo
            if user.staffprofile.circuitos.count() == 1:
                self.fields['circuito'].initial = user.staffprofile.circuitos.first()
                self.fields['circuito'].widget = forms.HiddenInput() # Esconde o campo se for apenas um

class MembroForm(BootstrapFormMixin ,forms.ModelForm): # Removi BootstrapFormMixin para simplificar, adicione de volta se quiser
    class Meta:
        model = Membro
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) # Recebe o usuário da view
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            # Filtra as equipes disponíveis para o staff (apenas as do seu circuito)
            staff_circuitos_ids = user.staffprofile.circuitos.values_list('id', flat=True)
            self.fields['equipe'].queryset = Equipe.objects.filter(circuito__id__in=staff_circuitos_ids)

class AtividadeForm(forms.ModelForm):
    class Meta:
        model = Atividade
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if 'responsavel' in self.fields:
            self.fields['responsavel'].queryset = User.objects.filter(is_staff=True)
        
        if user and not user.is_superuser:
            # Filtra os circuitos disponíveis para o staff
            self.fields['circuito'].queryset = user.staffprofile.circuitos.all()
            # Se o staff só tem um circuito, pré-seleciona e desabilita o campo
            if user.staffprofile.circuitos.count() == 1:
                self.fields['circuito'].initial = user.staffprofile.circuitos.first()
                self.fields['circuito'].widget = forms.HiddenInput() # Esconde o campo se for apenas um


class PontuacaoForm(forms.ModelForm):
    class Meta:
        model = Pontuacao
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # recebe o user da view
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            # Filtra as atividades e equipes com base nos circuitos do staff
            staff_circuitos_ids = user.staffprofile.circuitos.values_list('id', flat=True)
            self.fields['atividade'].queryset = Atividade.objects.filter(circuito__id__in=staff_circuitos_ids, responsavel=user)
            self.fields['equipe'].queryset = Equipe.objects.filter(circuito__id__in=staff_circuitos_ids)
            # Se o staff só tem um circuito, pré-seleciona e desabilita o campo de circuito
            if user.staffprofile.circuitos.count() == 1:
                self.fields['circuito'].initial = user.staffprofile.circuitos.first()
                self.fields['circuito'].widget = forms.HiddenInput() # Esconde o campo se for apenas um
        elif user and user.is_superuser:
            # Para superusuário, filtra atividades e equipes por circuito se um circuito já estiver selecionado
            # Isso é para o caso de edição, onde o objeto já tem um circuito
            if self.instance and self.instance.circuito:
                self.fields['atividade'].queryset = Atividade.objects.filter(circuito=self.instance.circuito)
                self.fields['equipe'].queryset = Equipe.objects.filter(circuito=self.instance.circuito)
            else:
                # Caso contrário, mostra todas as atividades e equipes
                self.fields['atividade'].queryset = Atividade.objects.all()
                self.fields['equipe'].queryset = Equipe.objects.all()


class PenalizacaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Penalizacao
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            # Filtra as equipes disponíveis para o staff (apenas as do seu circuito)
            staff_circuitos_ids = user.staffprofile.circuitos.values_list('id', flat=True)
            self.fields['equipe'].queryset = Equipe.objects.filter(circuito__id__in=staff_circuitos_ids)
            # Se o staff só tem um circuito, pré-seleciona e desabilita o campo de circuito
            if user.staffprofile.circuitos.count() == 1:
                self.fields['circuito'].initial = user.staffprofile.circuitos.first()
                self.fields['circuito'].widget = forms.HiddenInput() # Esconde o campo se for apenas um


class CircuitoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Circuito
        fields = ['nome', 'data_encerramento', 'ativo']
        widgets = {
            'data_encerramento': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

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