# /views.py

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from .models import Equipe, Circuito, Penalizacao, Pontuacao, StaffProfile, Membro
from .forms import (
    EquipeForm, MembroForm, PontuacaoForm, PenalizacaoForm, 
    CircuitoForm, StaffCreationForm, StaffProfileForm, PontuacaoAuthorizationForm, PenalizacaoAuthorizationForm
)
from django.db.models import Sum
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import timedelta, datetime
from django.utils import timezone
from django.db.models import Q

from functools import wraps

def staff_or_superuser_circuito_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        circuito_id = kwargs.get('circuito_id')
        modelo = kwargs.get('modelo')

        if modelo == 'staffprofile' and request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        if not request.user.is_superuser:
            if circuito_id is None:
                messages.error(request, "Circuito não especificado.")
                return redirect('index')
            if not request.user.staffprofile.circuitos.filter(id=circuito_id).exists():
                messages.error(request, "Você não tem permissão para este circuito.")
                return redirect('index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def is_staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def is_superuser(user):
    return user.is_authenticated and user.is_superuser


def index(request):
    circuitos_ativos = Circuito.objects.filter(ativo=True)
    return render(request, 'index.html', {'circuitos_ativos': circuitos_ativos})


@login_required
@user_passes_test(is_superuser)
def dashboard(request):
    circuitos_ativos = Circuito.objects.filter(ativo=True)
    return render(request, 'dashboard.html', {'circuitos_ativos': circuitos_ativos})


@login_required
@user_passes_test(is_staff_or_superuser)
def staff_dashboard(request, circuito_id):
    circuito = get_object_or_404(Circuito, id=circuito_id)
    if not request.user.is_superuser and not request.user.staffprofile.circuitos.filter(id=circuito_id).exists():
        messages.error(request, "Você não tem permissão para acessar este circuito.")
        return redirect('index')
    return render(request, 'staff_dashboard.html', {'circuito': circuito})


def ranking_view(request, circuito_id):
    circuito = get_object_or_404(Circuito, id=circuito_id)
    equipes_circuitos = circuito.equipes.all()

    equipes = circuito.equipes.select_related('circuito').all()
    if circuito.modo_ranking == 'tempo':
        equipes_ordenadas = sorted(
            equipes_circuitos,
            key=lambda e: e.tempo_em_segundos if e.tempo_em_segundos is not None else float('inf') # Alterado para tempo_em_segundos
        )
    else:
        equipes_ordenadas = sorted(
            equipes,
            key=lambda e: e.pontuacao_total(),
            reverse=True
        )
    return render(request, 'ranking.html', {
        'equipes': equipes_ordenadas,
        'circuito': circuito
    })

@login_required
@user_passes_test(is_staff_or_superuser)
def cadastrar_equipe(request):
    form = EquipeForm(request.POST or None, request.FILES or None, user=request.user)
    if form.is_valid():
        equipe = form.save(commit=False)
        if not request.user.is_superuser:
            if not equipe.circuito:
                staff_circuitos = request.user.staffprofile.circuitos.all()
                if staff_circuitos.exists():
                    equipe.circuito = staff_circuitos.first()
                else:
                    messages.error(request, "Você não está associado a nenhum circuito para cadastrar equipes.")
                    return render(request, 'form_generico.html', {'form': form, 'titulo': 'Cadastrar Equipe'})
            elif not request.user.staffprofile.circuitos.filter(id=equipe.circuito.id).exists():
                messages.error(request, "Você não tem permissão para cadastrar equipes neste circuito.")
                return render(request, 'form_generico.html', {'form': form, 'titulo': 'Cadastrar Equipe'})
        equipe.save()
        messages.success(request, "Equipe cadastrada com sucesso!")
        return redirect('cadastrar_equipe')
    return render(request, 'form_generico.html', {'form': form, 'titulo': 'Cadastrar Equipe'})


@login_required
@user_passes_test(is_superuser)
def cadastrar_staff(request):
    if request.method == 'POST':
        form = StaffCreationForm(request.POST)
        staff_profile_form = StaffProfileForm(request.POST)
        if form.is_valid() and staff_profile_form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            is_superuser_flag = form.cleaned_data.get('is_superuser', False)

            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Este nome de usuário já está em uso.')
            else:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    is_staff=True,
                    is_superuser=is_superuser_flag
                )
                staff_profile = staff_profile_form.save(commit=False)
                staff_profile.user = user
                staff_profile.save()
                staff_profile_form.save_m2m()
                messages.success(request, f'Usuário {username} criado com sucesso!')
                return redirect('dashboard')
    else:
        form = StaffCreationForm()
        staff_profile_form = StaffProfileForm()
    
    return render(request, 'form_generico.html', {
        'form': form,
        'staff_profile_form': staff_profile_form,
        'titulo': 'Cadastrar Staff'
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def cadastrar_membro(request):
    form = MembroForm(request.POST or None, user=request.user)
    if form.is_valid():
        membro = form.save(commit=False)
        circuito_id = membro.equipe.circuito.id if membro.equipe else None
        if not request.user.is_superuser and circuito_id and not request.user.staffprofile.circuitos.filter(id=circuito_id).exists():
            messages.error(request, "Você não tem permissão para cadastrar membros para equipes neste circuito.")
            return render(request, 'form_generico.html', {'form': form, 'titulo': 'Cadastrar Membro'})
        membro.save()
        messages.success(request, "Membro cadastrado com sucesso!")
        return redirect('cadastrar_membro')
    return render(request, 'form_generico.html', {'form': form, 'titulo': 'Cadastrar Membro'})

@login_required
@user_passes_test(is_staff_or_superuser)
def criar_pontuacao(request):
    form = PontuacaoForm(request.POST or None, user=request.user)

    if request.method == 'POST':
        if form.is_valid():
            pont = form.save(commit=False)
            pont.usuario = request.user

            # status automático
            if request.user.is_superuser:
                pont.status = form.cleaned_data.get('status', 'aprovado')
                if pont.status == 'aprovado':
                    pont.aprovado_por = request.user
                    pont.data_aprovacao = timezone.now()
            else:
                pont.status = 'pendente'

            # PARA DEBUG: verifique no console se o tempo foi calculado
            print("DEBUG tempo_calculado:", form.cleaned_data.get('tempo_calculado'))

            pont.save()
            msg = "Pontuação criada e aprovada!" if pont.status == 'aprovado' else \
                  "Pontuação criada! Aguardando aprovação."
            messages.success(request, msg)
            return redirect('criar_pontuacao')
        else:
            messages.error(request, "Erro ao criar pontuação. Verifique os campos.")

    return render(request, 'form_generico.html', {
        'form': form,
        'titulo': 'Criar Pontuação'
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def criar_penalizacao(request):
    form = PenalizacaoForm(request.POST or None, user=request.user)
    if request.method == 'POST': # Adicionado para exibir erros apenas após o submit
        if form.is_valid():
            penalizacao = form.save(commit=False)
            penalizacao.usuario = request.user # Define o usuário que criou a penalização

            # A validação de permissão de circuito já está no __init__ do formulário
            # mas é bom ter uma camada extra de segurança aqui também.
            if not request.user.is_superuser:
                # Se o usuário não é superuser, a penalização é sempre pendente
                penalizacao.status = 'pendente'
            else:
                # Superuser pode definir o status diretamente
                penalizacao.status = form.cleaned_data.get('status', 'aprovado')
                if penalizacao.status == 'aprovado':
                    penalizacao.aprovado_por = request.user
                    penalizacao.data_aprovacao = timezone.now()
            
            penalizacao.save()
            messages.success(request, "Penalização criada com sucesso!" if penalizacao.status == 'aprovado' else "Penalização criada com sucesso! Aguardando aprovação do Superusuário.")
            return redirect('criar_penalizacao')
        else:
            # Imprime os erros do formulário para depuração
            print("Erros do formulário de Penalização:", form.errors)
            messages.error(request, "Houve um erro ao criar a penalização. Verifique os campos.")
    return render(request, 'form_generico.html', {'form': form, 'titulo': 'Criar Penalização'})


@login_required
@user_passes_test(is_superuser)
def criar_circuito(request):
    form = CircuitoForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Circuito criado com sucesso!")
        return redirect('index')
    return render(request, 'form_generico.html', {'form': form, 'titulo': 'Criar Circuito'})


MODELOS_MAP = {
    'equipe': (Equipe, EquipeForm, 'nome'),
    'penalizacao': (Penalizacao, PenalizacaoForm, 'motivo'),
    'pontuacao': (Pontuacao, PontuacaoForm, 'valor'),
    'circuito': (Circuito, CircuitoForm, 'nome'), 
    'membro': (Membro, MembroForm, 'nome'),   
    'staffprofile': (StaffProfile, StaffProfileForm, 'user__username'),
}

MODELOS_MAP_AUTH = {
    'pontuacao': (Pontuacao, PontuacaoAuthorizationForm, 'valor'),
    'penalizacao': (Penalizacao, PenalizacaoAuthorizationForm, 'valor'),
}

@login_required
@user_passes_test(is_staff_or_superuser)
def listar_modelo(request, modelo, circuito_id=None):
    ModelClass, FormClass, campo_busca = MODELOS_MAP.get(modelo, (None, None, None))
    if not ModelClass:
        messages.error(request, "Modelo inválido.")
        return redirect('dashboard')

    filtros = Q()
    query = request.GET.get('q', '')

    if modelo == 'staffprofile':
        if not request.user.is_superuser:
            messages.error(request, "Você não tem permissão para listar staff.")
            return redirect('index')
        objetos = StaffProfile.objects.select_related('user')
        if query:
            objetos = objetos.filter(Q(user__username__icontains=query) | Q(user__email__icontains=query))
    else:
        if not request.user.is_superuser:
            if circuito_id is None:
                messages.error(request, "Circuito não especificado para este tipo de listagem.")
                return redirect('index')
            if not request.user.staffprofile.circuitos.filter(id=circuito_id).exists():
                messages.error(request, "Você não tem permissão para listar itens deste circuito.")
                return redirect('index')

        if 'circuito' in [f.name for f in ModelClass._meta.get_fields()]:
            if circuito_id:
                filtros &= Q(circuito_id=circuito_id)
        elif modelo == 'membro':
            if circuito_id:
                filtros &= Q(equipe__circuito_id=circuito_id)
        
        if modelo in ['pontuacao', 'penalizacao'] and not request.user.is_superuser:
            filtros &= Q(status__in=['pendente', 'aprovado'])

        if query:
            filtros &= Q(**{f"{campo_busca}__icontains": query})

        # Ajuste o select_related com base no modelo
        if modelo == 'pontuacao':
            objetos = ModelClass.objects.filter(filtros).select_related('circuito', 'equipe', 'usuario').distinct()
        elif modelo == 'penalizacao':
            objetos = ModelClass.objects.filter(filtros).select_related('circuito', 'equipe', 'usuario').distinct()
        elif modelo == 'equipe':
            objetos = ModelClass.objects.filter(filtros).select_related('circuito').distinct()
        elif modelo == 'circuito':
            objetos = ModelClass.objects.filter(filtros).select_related('responsavel').distinct()
        else: # Caso padrão para outros modelos que não precisam de select_related específico
            objetos = ModelClass.objects.filter(filtros).distinct()


    model_verbose_name = ModelClass._meta.verbose_name.title()

    return render(request, 'listagem_generica.html', {
        'objetos': objetos,
        'modelo': modelo,
        'model_verbose_name': model_verbose_name,
        'circuito_id': circuito_id,
        'campo_busca': query,
    })


def equipe_detail_view(request, equipe_id):
    equipe = get_object_or_404(Equipe, id=equipe_id)
    circuito = equipe.circuito
    membros = Membro.objects.filter(equipe=equipe).order_by('nome')
    pontuacoes = Pontuacao.objects.filter(equipe=equipe, status='aprovado').order_by('-data')
    penalizacoes = Penalizacao.objects.filter(equipe=equipe, status='aprovado').order_by('-data')
    equipes_circuitos = circuito.equipes.all()
    
    if circuito.modo_ranking == 'tempo':
        equipes_ordenadas = sorted(
            equipes_circuitos,
            key=lambda e: e.tempo_em_segundos if e.tempo_em_segundos is not None else float('inf') # Alterado para tempo_em_segundos
        )
    else:
        equipes_ordenadas = sorted(
            equipes_circuitos, # Alterado para equipes_circuitos para garantir que todas as equipes do circuito sejam consideradas
            key=lambda e: e.pontuacao_total(),
            reverse=True
        )
    posicao = next((i + 1 for i, e in enumerate(equipes_ordenadas) if e.id == equipe.id), None)
    context = {
        'equipe': equipe,
        'circuito': circuito,
        'membros': membros,
        'pontuacoes': pontuacoes,
        'penalizacoes': penalizacoes,
        'ranking': equipes_ordenadas,
        'posicao': posicao,
    }
    return render(request, 'equipe_detail.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def editar_modelo(request, modelo, pk):
    ModelClass, FormClass, _ = MODELOS_MAP.get(modelo, (None, None, None))
    if not ModelClass or not FormClass:
        messages.error(request, "Modelo inválido.")
        return redirect('dashboard')
    objeto = get_object_or_404(ModelClass, pk=pk)
    if not request.user.is_superuser:
        circuito = getattr(objeto, 'circuito', None)
        if circuito and not request.user.staffprofile.circuitos.filter(id=circuito.id).exists():
            messages.error(request, "Você não tem permissão para editar esse item.")
            return redirect('index')
        
        if modelo in ['pontuacao', 'penalizacao']:
            messages.error(request, "Você não tem permissão para editar o status de pontuações/penalizações. Contate um superusuário.")
            return redirect('listar_modelo', modelo=modelo, circuito_id=circuito.id if circuito else 0)
    if request.method == 'POST':
        form = FormClass(request.POST, instance=objeto, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"{ModelClass._meta.verbose_name.title()} atualizado com sucesso!")
            return redirect('dashboard')
    else:
        form = FormClass(instance=objeto, user=request.user)
    return render(request, 'form_generico.html', {
        'form': form,
        'titulo': f'Editar {ModelClass._meta.verbose_name.title()}'
    })

@login_required
@user_passes_test(is_staff_or_superuser)
def excluir_modelo(request, modelo, pk):
    ModelClass, _, _ = MODELOS_MAP.get(modelo, (None, None, None))
    if not ModelClass:
        messages.error(request, "Modelo inválido.")
        return redirect('dashboard')
    objeto = get_object_or_404(ModelClass, pk=pk)
    if not request.user.is_superuser:
        circuito = getattr(objeto, 'circuito', None)
        if circuito and not request.user.staffprofile.circuitos.filter(id=circuito.id).exists():
            messages.error(request, "Você não tem permissão para excluir este item.")
            return redirect('index')
        
        if modelo in ['pontuacao', 'penalizacao'] and objeto.status == 'aprovado':
            messages.error(request, "Você não pode excluir uma pontuação/penalização já aprovada. Contate um superusuário.")
            return redirect('listar_modelo', modelo=modelo, circuito_id=circuito.id if circuito else 0)
    if request.method == 'POST':
        circuito_id_redirect = getattr(objeto, 'circuito', None).id if getattr(objeto, 'circuito', None) else 0
        objeto.delete()
        messages.success(request, f"{ModelClass._meta.verbose_name.title()} excluído com sucesso!")
        return redirect('listar_modelo', modelo=modelo, circuito_id=circuito_id_redirect)
    return redirect('dashboard')

@login_required
@user_passes_test(is_staff_or_superuser)
def listar_circuitos_ativos(request):
    circuitos = Circuito.objects.filter(ativo=True)
    return render(request, 'listar_circuitos_ativos.html', {
        'circuitos_ativos': circuitos,
        'titulo': 'Circuitos Ativos',
        'ativo': True,
    })

@login_required
@user_passes_test(is_staff_or_superuser)
def listar_circuitos_inativos(request):
    circuitos = Circuito.objects.filter(ativo=False)
    return render(request, 'listar_circuitos_inativos.html', {
        'circuitos_inativos': circuitos,
        'titulo': 'Circuitos Inativos',
        'ativo': False,
    })

@login_required
@user_passes_test(is_superuser)
def listar_staff(request):
    objeto = User.objects.all()
    return render(request, 'listar_staff.html', {
        'staff_list': objeto,
    })

@login_required
@user_passes_test(is_superuser)
def editar_staff(request, pk):
    user = get_object_or_404(User, pk=pk)
    try:
        staff_profile = user.staffprofile
    except StaffProfile.DoesNotExist:
        staff_profile = None

    if request.method == 'POST':
        form = StaffCreationForm(request.POST, initial={'username': user.username})
        profile_form = StaffProfileForm(request.POST, instance=staff_profile)
        
        if form.is_valid() and profile_form.is_valid():
            user.username = form.cleaned_data['username']
            if form.cleaned_data['password']:
                user.set_password(form.cleaned_data['password'])
            user.is_superuser = form.cleaned_data['is_superuser']
            user.is_staff = True
            user.save()

            staff_profile = profile_form.save(commit=False)
            staff_profile.user = user
            staff_profile.save()
            profile_form.save_m2m()

            messages.success(request, 'Staff atualizado com sucesso!')
            return redirect('listar_staff')
    else:
        form = StaffCreationForm(initial={
            'username': user.username,
            'is_superuser': user.is_superuser,
        })
        profile_form = StaffProfileForm(instance=staff_profile)

    return render(request, 'form_generico.html', {
        'form': form,
        'staff_profile_form': profile_form,
        'titulo': f'Editar Staff: {user.username}',
    })

@login_required
@user_passes_test(is_superuser)
def excluir_staff(request, pk):
    user = get_object_or_404(User, pk=pk)
    username = user.username
    user.delete()
    messages.success(request, f'Usuário staff "{username}" excluído com sucesso.')
    return redirect('listar_staff')

 

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def listar_membros(request):
    query = request.GET.get('q', '')
    membros = Membro.objects.all()

    if query:
        membros = membros.filter(Q(nome__icontains=query) | Q(equipe__nome__icontains=query))

    paginator = Paginator(membros, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'listar_membros.html', {
        'membros': page_obj,
        'query': query,
    })

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def editar_membro(request, pk):
    membro = get_object_or_404(Membro, pk=pk)
    if request.method == 'POST':
        form = MembroForm(request.POST, instance=membro, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Membro atualizado com sucesso!")
            return redirect('listar_membros')
    else:
        form = MembroForm(instance=membro, user=request.user)
    
    return render(request, 'form_generico.html', {
        'form': form,
        'titulo': 'Editar Membro',
    })

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def excluir_membro(request, pk):
    membro = get_object_or_404(Membro, pk=pk)

    membro.delete()
    messages.success(request, "Membro excluído com sucesso!")
    return redirect('listar_membros')


@login_required
@user_passes_test(is_superuser)
def listar_autorizacoes_pendentes(request):
    pontuacoes_pendentes = Pontuacao.objects.filter(status='pendente').select_related('equipe', 'circuito', 'usuario').order_by('data')
    penalizacoes_pendentes = Penalizacao.objects.filter(status='pendente').select_related('equipe', 'circuito', 'usuario').order_by('data')
    context = {
        'pontuacoes_pendentes': pontuacoes_pendentes,
        'penalizacoes_pendentes': penalizacoes_pendentes,
        'titulo': 'Autorizações Pendentes',
    }
    return render(request, 'autorizacao_list.html', context)

@login_required
@user_passes_test(is_superuser)
def autorizar_item(request, modelo, pk):
    ModelClass, FormClass, _ = MODELOS_MAP_AUTH.get(modelo, (None, None, None))
    if not ModelClass or not FormClass:
        messages.error(request, "Modelo inválido para autorização.")
        return redirect('listar_autorizacoes_pendentes')
    objeto = get_object_or_404(ModelClass, pk=pk)
    if request.method == 'POST':
        form = FormClass(request.POST, instance=objeto)
        if form.is_valid():
            objeto.aprovado_por = request.user
            objeto.data_aprovacao = timezone.now()
            form.save()
            messages.success(request, f"{ModelClass._meta.verbose_name.title()} {objeto.get_status_display()} com sucesso!")
            return redirect('listar_autorizacoes_pendentes')
    else:
        form = FormClass(instance=objeto)
    return render(request, 'form_generico.html', {
        'form': form,
        'titulo': f'Autorizar {ModelClass._meta.verbose_name.title()}',
        'objeto': objeto,
    })


def inativar(request, pk):
    objeto = get_object_or_404(Circuito, pk=pk)
    objeto.ativo = False
    objeto.save()
    return redirect( 'dashboard')

from django.http import JsonResponse

@login_required
def get_equipes_by_circuito(request, circuito_id):
    equipes = Equipe.objects.filter(circuito_id=circuito_id).values('id', 'nome')
    return JsonResponse(list(equipes), safe=False)

@login_required
def get_all_equipes(request):
    equipes = Equipe.objects.all().values('id', 'nome')
    return JsonResponse(list(equipes), safe=False)


@login_required
def get_circuito_details(request, circuito_id):
    circuito = get_object_or_404(Circuito, id=circuito_id)
    return JsonResponse({
        'modo_ranking': circuito.modo_ranking,
        'pontuacao_fixa': circuito.pontuacao_fixa,
        'valor_padrao': circuito.valor_padrao,
    })

def excluir_prova(request, pk):
    objeto = get_object_or_404(Circuito, pk=pk)
    objeto.delete()
    return redirect('listar_circuitos_ativos')
