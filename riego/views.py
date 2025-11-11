from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
<<<<<<< HEAD
from .models import ControlRiego
from .forms import ControlRiegoForm
=======
from .models import ControlRiego , FertilizanteRiego
from .forms import ControlRiegoForm, FertilizanteRiegoForm
>>>>>>> f1fb4d405896851bfb7a50b67ee04c0dbaa27ace
from autenticacion.views import login_required 

# Decorador de login
def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ==================== VISTAS BÁSICAS DE RIEGO ====================

@login_required
def dashboard_riego(request):
    """Dashboard del módulo de riego"""
    hoy = timezone.now().date()
    
    # Estadísticas básicas
    riegos_hoy = ControlRiego.objects.filter(fecha=hoy)
    volumen_hoy = riegos_hoy.aggregate(total=Sum('volumen_total_m3'))['total'] or 0
    
    riegos_mes = ControlRiego.objects.filter(fecha__month=hoy.month)
    volumen_mes = riegos_mes.aggregate(total=Sum('volumen_total_m3'))['total'] or 0
    
    # Últimos riegos
    ultimos_riegos = ControlRiego.objects.order_by('-fecha', '-horario_inicio')[:5]
    
    context = {
        'riegos_hoy': riegos_hoy.count(),
        'volumen_hoy': volumen_hoy,
        'riegos_mes': riegos_mes.count(),
        'volumen_mes': volumen_mes,
        'ultimos_riegos': ultimos_riegos,
        'titulo': 'Dashboard - Control de Riego',
        'usuario_nombre': request.session.get('usuario_nombre', 'Usuario')
    }
    return render(request, 'riego/dashboard.html', context)


@login_required
def lista_riegos(request):
    """Lista simple de controles de riego"""
    query = request.GET.get('q', '')
    
    riegos = ControlRiego.objects.all()
    
    if query:
        riegos = riegos.filter(
            Q(cuartel_id__icontains=query) |
            Q(observaciones__icontains=query)
        )
    
    riegos = riegos.order_by('-fecha', '-horario_inicio')
    
    # Paginación
    paginator = Paginator(riegos, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'titulo': 'Lista de Controles de Riego'
    }
    return render(request, 'riego/riego_lista.html', context)


@login_required
def crear_riego(request):
    """Crear nuevo control de riego"""
    if request.method == 'POST':
        form = ControlRiegoForm(request.POST)
        
        if form.is_valid():
            try:
                riego = form.save(commit=False)
                riego.creado_por = request.session.get('usuario_id')
                riego.save()
                
                messages.success(request, 'Control de riego creado exitosamente.')
                return redirect('riego:lista')
            except Exception as e:
                messages.error(request, f'Error al crear el registro: {str(e)}')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ControlRiegoForm()
    
    context = {
        'form': form,
        'titulo': 'Crear Control de Riego'
    }
    return render(request, 'riego/riego_form.html', context)


@login_required
def editar_riego(request, pk):
    """Editar control de riego existente"""
    riego = get_object_or_404(ControlRiego, pk=pk)
    
    if request.method == 'POST':
        form = ControlRiegoForm(request.POST, instance=riego)
        
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Control de riego actualizado exitosamente.')
                return redirect('riego:lista')
            except Exception as e:
                messages.error(request, f'Error al actualizar: {str(e)}')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ControlRiegoForm(instance=riego)
    
    context = {
        'form': form,
        'riego': riego,
        'titulo': 'Editar Control de Riego'
    }
    return render(request, 'riego/editar_riego.html', context)


@login_required
def detalle_riego(request, riego_id):
    """Detalle de un control de riego"""
    try:
        riego = ControlRiego.objects.get(id=riego_id)
        fertilizantes = riego.fertilizantes.all()
        context = {
            'riego': riego,
            'fertilizantes': fertilizantes,
            'titulo': f'Detalle Riego - {riego.fecha}'
        }
    except ControlRiego.DoesNotExist:
        context = {
            'error': 'Control de riego no encontrado'
        }
    
    return render(request, 'riego/detalle_riego.html', context)


@login_required
def eliminar_riego(request, pk):
    """Eliminar control de riego"""
    riego = get_object_or_404(ControlRiego, pk=pk)
    
    if request.method == 'POST':
        riego.delete()
        messages.success(request, 'Control de riego eliminado exitosamente.')
        return redirect('riego:lista')
    
    context = {'riego': riego}
    return render(request, 'riego/eliminar_riego.html', context)


# ==================== VISTAS PARA FERTILIZANTES ====================

@login_required
def agregar_fertilizante(request, riego_id):
    """Agregar fertilizante a un riego existente"""
    riego = get_object_or_404(ControlRiego, id=riego_id)
    
    if request.method == 'POST':
        form = FertilizanteRiegoForm(request.POST)
        if form.is_valid():
            fertilizante = form.save(commit=False)
            fertilizante.control_riego = riego
            fertilizante.save()
            messages.success(request, 'Fertilizante agregado exitosamente.')
            return redirect('riego:detalle', riego_id=riego_id)
    else:
        form = FertilizanteRiegoForm()
    
    context = {
        'form': form,
        'riego': riego,
        'titulo': 'Agregar Fertilizante'
    }
    return render(request, 'riego/agregar_fertilizante.html', context)