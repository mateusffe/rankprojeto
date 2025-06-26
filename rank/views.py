
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from .models import Equipe, Circuito, Atividade, Penalizacao, Pontuacao, StaffProfile, Membro
from .forms import EquipeForm, MembroForm, AtividadeForm, PontuacaoForm, PenalizacaoForm, CircuitoForm, StaffCreationForm, StaffProfileForm
from django.contrib.auth.models import User
from django.contrib import messages  # para mensagens flash
from django.db.models import Q
from django.contrib.auth.forms import UserChangeForm


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
    # Verifica se o staff tem permissão para acessar este circuito
    if not request.user.is_superuser and not request.user.staffprofile.circuitos.filter(id=circuito_id).exists():
        messages.error(request, "Você não tem permissão para acessar este circuito.")
        return redirect('index')
    return render(request, 'staff_dashboard.html', {'circuito': circuito})



def ranking_view(request, circuito_id):
    circuito = get_object_or_404(Circuito, id=circuito_id)
    equipes = circuito.equipes.all()
    equipes_ordenadas = sorted(equipes, key=lambda e: e.pontuacao_total(), reverse=True)
    return render(request, 'ranking.html', {'equipes': equipes_ordenadas, 'circuito': circuito})


def equipe_detail_view(request, equipe_id):
    equipe = get_object_or_404(Equipe, pk=equipe_id)
    return render(request, 'equipe_detail.html', {'equipe': equipe})

@login_required
@user_passes_test(is_staff_or_superuser)
def cadastrar_equipe(request):
    form = EquipeForm(request.POST or None, user=request.user)
    if form.is_valid():
        equipe = form.save(commit=False)
        # Se for staff, associa ao primeiro circuito disponível ou ao circuito selecionado no formulário
        if not request.user.is_superuser:
            if not equipe.circuito: # Se o circuito não foi selecionado no form (ex: campo oculto)
                staff_circuitos = request.user.staffprofile.circuitos.all()
                if staff_circuitos.exists():
                    equipe.circuito = staff_circuitos.first() # Associa ao primeiro circuito do staff
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
                staff_profile_form.save_m2m()  # Salva a relação ManyToMany para circuitos
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
        # Verifica se a equipe do membro pertence a um circuito que o staff pode acessar
        if not request.user.is_superuser and not request.user.staffprofile.circuitos.filter(id=membro.equipe.circuito.id).exists():
            messages.error(request, "Você não tem permissão para cadastrar membros para equipes neste circuito.")
            return render(request, 'form_generico.html', {'form': form, 'titulo': 'Cadastrar Membro'})
        membro.save()
        messages.success(request, "Membro cadastrado com sucesso!")
        return redirect('cadastrar_membro')
    return render(request, 'form_generico.html', {'form': form, 'titulo': 'Cadastrar Membro'})

@login_required
@user_passes_test(is_staff_or_superuser)
def cadastrar_atividade(request):
    form = AtividadeForm(request.POST or None, user=request.user)
    if form.is_valid():
        atividade = form.save(commit=False)
        # Se for staff, verifica se o circuito da atividade está entre os seus permitidos
        if not request.user.is_superuser and not request.user.staffprofile.circuitos.filter(id=atividade.circuito.id).exists():
            messages.error(request, "Você não tem permissão para criar atividades neste circuito.")
            return render(request, 'form_generico.html', {'form': form, 'titulo': 'Criar Atividade'})
        atividade.save()
        messages.success(request, "Atividade criada com sucesso!")
        return redirect('cadastrar_atividade')
    return render(request, 'form_generico.html', {'form': form, 'titulo': 'Criar Atividade'})

@login_required
@user_passes_test(is_staff_or_superuser)
def criar_pontuacao(request):
    form = PontuacaoForm(request.POST or None, user=request.user)
    
    if form.is_valid():
        pontuacao = form.save(commit=False)

        # Verifica permissões de staff para o circuito da atividade/equipe
        if not request.user.is_superuser:
            if not request.user.staffprofile.circuitos.filter(id=pontuacao.atividade.circuito.id).exists():
                messages.error(request, 'Você não tem permissão para criar pontuações neste circuito.')
                return render(request, 'form_generico.html', {'form': form, 'titulo': 'Criar Pontuação'})
            if pontuacao.atividade.responsavel != request.user:
                messages.error(request, 'Você não é responsável por essa atividade.')
                return render(request, 'form_generico.html', {'form': form, 'titulo': 'Criar Pontuação'})

        pontuacao.save()
        messages.success(request, "Pontuação criada com sucesso!")
        return redirect('criar_pontuacao')

    return render(request, 'form_generico.html', {'form': form, 'titulo': 'Criar Pontuação'})

@login_required
@user_passes_test(is_staff_or_superuser)
def criar_penalizacao(request):
    form = PenalizacaoForm(request.POST or None, user=request.user)
    if form.is_valid():
        penalizacao = form.save(commit=False)
        # Verifica permissões de staff para o circuito da equipe
        if not request.user.is_superuser and not request.user.staffprofile.circuitos.filter(id=penalizacao.equipe.circuito.id).exists():
            messages.error(request, "Você não tem permissão para criar penalizações neste circuito.")
            return render(request, 'form_generico.html', {'form': form, 'titulo': 'Criar Penalização'})
        penalizacao.save()
        messages.success(request, "Penalização criada com sucesso!")
        return redirect('criar_penalizacao')
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
    'atividade': (Atividade, AtividadeForm, 'nome'),
    'penalizacao': (Penalizacao, PenalizacaoForm, 'motivo'),
    'pontuacao': (Pontuacao, PontuacaoForm, 'atividade__nome'),
    'circuito': (Circuito, CircuitoForm, 'nome'), 
    'membro': (Membro, MembroForm, 'nome'),   
}

def listar_modelo(request, modelo, circuito_id):
    ModelClass, FormClass, campo_busca = MODELOS_MAP.get(modelo, (None, None, None))
    if not ModelClass:
        messages.error(request, "Modelo inválido.")
        return redirect('dashboard')

    # Verifica permissão de staff para o circuito
    if not request.user.is_superuser and not request.user.staffprofile.circuitos.filter(id=circuito_id).exists():
        messages.error(request, "Você não tem permissão para listar itens deste circuito.")
        return redirect('index')

    query = request.GET.get('q', '')
    filtros = Q()

    # Aplica filtro circuito apenas se o modelo tiver esse campo
    if 'circuito' in [f.name for f in ModelClass._meta.get_fields()]:
        filtros &= Q(circuito_id=circuito_id)

    if query:
        filtros &= Q(**{f"{campo_busca}__icontains": query})

    objetos = ModelClass.objects.filter(filtros)
    model_verbose_name = ModelClass._meta.verbose_name.title()

    return render(request, 'listagem_generica.html', {
        'objetos': objetos,
        'modelo': modelo,
        'model_verbose_name': model_verbose_name,
        'circuito_id': circuito_id,
        'campo_busca': query,
    })

@login_required
@user_passes_test(is_staff_or_superuser)
def excluir_modelo(request, modelo, pk):
    ModelClass, _, _ = MODELOS_MAP.get(modelo, (None, None, None))
    if not ModelClass:
        messages.error(request, "Modelo inválido.")
        return redirect('dashboard')
    
    obj = get_object_or_404(ModelClass, pk=pk)
    circuito_id = getattr(obj, 'circuito_id', None)

    # Verifica permissão de staff para o circuito
    if not request.user.is_superuser and circuito_id and not request.user.staffprofile.circuitos.filter(id=circuito_id).exists():
        messages.error(request, "Você não tem permissão para excluir itens deste circuito.")
        return redirect('index')

    obj.delete()
    messages.success(request, f'{modelo.title()} excluído com sucesso!')
    return redirect('listar_modelo', modelo=modelo, circuito_id=circuito_id or 1) # Redireciona para a listagem do circuito

@login_required
@user_passes_test(is_staff_or_superuser)
def editar_modelo(request, modelo, pk):
    ModelClass, FormClass, _ = MODELOS_MAP.get(modelo, (None, None, None))
    if not ModelClass:
        messages.error(request, "Modelo inválido.")
        return redirect('dashboard')

    obj = get_object_or_404(ModelClass, pk=pk)
    circuito_id = getattr(obj, 'circuito_id', None)

    # Verifica permissão de staff para o circuito (quando aplicável)
    if not request.user.is_superuser and circuito_id and not request.user.staffprofile.circuitos.filter(id=circuito_id).exists():
        messages.error(request, "Você não tem permissão para editar itens deste circuito.")
        return redirect('index')

    # Instancia o form com ou sem user, conforme necessário
    form = None
    if request.method == 'POST':
        try:
            form = FormClass(request.POST, instance=obj, user=request.user)
        except TypeError:
            form = FormClass(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'{modelo.title()} atualizado com sucesso!')
            return redirect('dashboard')
    else:
        try:
            form = FormClass(instance=obj, user=request.user)
        except TypeError:
            form = FormClass(instance=obj)

    return render(request, 'form_generico.html', {
        'form': form,
        'titulo': f'Editar {modelo.title()}'
    })


@login_required
@user_passes_test(is_superuser)
def listar_circuitos_inativos(request):
    circuitos_inativos = Circuito.objects.filter(ativo=False)
    return render(request, 'listar_circuitos_inativos.html', {'circuitos_inativos': circuitos_inativos})

@login_required
@user_passes_test(is_superuser)
def listar_circuitos_ativos(request):
    circuitos_ativos = Circuito.objects.filter(ativo=True)
    return render(request, 'listar_circuitos_ativos.html', {'circuitos_ativos': circuitos_ativos})



@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_staff(request):
    staff_list = User.objects.filter(is_staff=True).order_by('username')
    
    # Filtros
    superuser_filter = request.GET.get('superuser')
    if superuser_filter in ['true', 'false']:
        staff_list = staff_list.filter(is_superuser=(superuser_filter == 'true'))
    
    # Pesquisa
    search_query = request.GET.get('search')
    if search_query:
        staff_list = staff_list.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filtro por circuito
    circuito_id = request.GET.get('circuito')
    if circuito_id:
        staff_list = staff_list.filter(
            staffprofile__circuitos__id=circuito_id
        )
    
    # Contexto
    context = {
        'staff_list': staff_list,
        'circuitos': Circuito.objects.filter(ativo=True),
        'current_search': search_query if search_query else '',
        'current_superuser': superuser_filter if superuser_filter else '',
        'current_circuito': int(circuito_id) if circuito_id else None
    }
    
    return render(request, 'listar_staff.html', context)


    


@login_required
@user_passes_test(lambda u: u.is_superuser)
def editar_staff(request, pk):
    staff = get_object_or_404(User, pk=pk, is_staff=True)
    profile, created = StaffProfile.objects.get_or_create(user=staff)
    if request.method == 'POST':
        # Formulário de Edição de Staff
        staff_form = StaffCreationForm(request.POST)
        profile_form = StaffProfileForm(request.POST, instance=profile)
        if staff_form.is_valid() and profile_form.is_valid():
            # Atualiza o usuário
            staff.username = staff_form.cleaned_data['username']
            if staff_form.cleaned_data['password']:
                staff.set_password(staff_form.cleaned_data['password'])
            staff.is_superuser = staff_form.cleaned_data['is_superuser']
            staff.save()
            # Salva o perfil
            profile_form.save()
            messages.success(request, "Alterações salvas com sucesso!")
            return redirect('listar_staff')
    else:
        # Preenche os formulários com os dados existentes
        staff_form = StaffCreationForm(initial={
            'username': staff.username,
            'is_superuser': staff.is_superuser
        })
        profile_form = StaffProfileForm(instance=profile)
    return render(request, 'editar_staff.html', {
        'staff_form': staff_form,
        'profile_form': profile_form,
        'staff': staff
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def excluir_staff(request, pk):
    staff = get_object_or_404(User, pk=pk, is_staff=True)
    staff.delete()
    messages.success(request, f"Staff {staff.username} excluído com sucesso!")
    return redirect('listar_staff')
 

@login_required
@user_passes_test(is_staff_or_superuser)
def listar_membros(request):
    membros = Membro.objects.all().order_by('equipe__nome', 'nome')
    
    # Filtro por equipe
    equipe_id = request.GET.get('equipe')
    if equipe_id:
        membros = membros.filter(equipe_id=equipe_id)
    
    # Pesquisa por nome
    pesquisa = request.GET.get('pesquisa')
    if pesquisa:
        membros = membros.filter(nome__icontains=pesquisa)
    
    # Pegar todas as equipes para o dropdown de filtro
    equipes = Equipe.objects.all().order_by('nome')
    
    return render(request, 'listar_membros.html', {
        'membros': membros,
        'equipes': equipes,
        'equipe_filtrada': int(equipe_id) if equipe_id else None,
        'termo_pesquisa': pesquisa if pesquisa else ''
    })

@login_required
@user_passes_test(is_staff_or_superuser)
def editar_membro(request, pk):
    membro = get_object_or_404(Membro, pk=pk)
    # Verifica permissão do staff para editar este membro
    if not request.user.is_superuser:
        if not request.user.staffprofile.circuitos.filter(id=membro.equipe.circuito.id).exists():
            messages.error(request, "Você não tem permissão para editar membros desta equipe.")
            return redirect('listar_membros') # Ou para uma página de erro
    if request.method == 'POST':
        form = MembroForm(request.POST, instance=membro, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Membro atualizado com sucesso!")
            return redirect('listar_membros')
    else:
        form = MembroForm(instance=membro, user=request.user)
    return render(request, 'editar_membro.html', {'form': form, 'membro': membro})

@login_required
@user_passes_test(is_staff_or_superuser)
def excluir_membro(request, pk):
    membro = get_object_or_404(Membro, pk=pk)
    # Verifica permissão do staff para excluir este membro
    if not request.user.is_superuser:
        if not request.user.staffprofile.circuitos.filter(id=membro.equipe.circuito.id).exists():
            messages.error(request, "Você não tem permissão para excluir membros desta equipe.")
            return redirect('listar_membros')
    if request.method == 'POST':
        membro.delete()
        messages.success(request, "Membro excluído com sucesso!")
        return redirect('listar_membros')
    
    return redirect('dashboard')