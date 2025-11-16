from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST # ¡Importante!

# Modelos de esta app
from .models import ControlRiego, FertilizanteRiego

# Modelos de otras apps
from autenticacion.models import Usuario 
from cuarteles.models import Cuartel
from inventario.models import MovimientoInventario, DetalleMovimiento, Producto

# Formularios
from .forms import ControlRiegoForm, FertilizanteRiegoFormSet, FertilizanteRiegoForm

# --- Decorador de Login (SIN CAMBIOS) ---
def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login') 
        return view_func(request, *args, **kwargs)
    return wrapper

# ===============================================================
#  FUNCIONES AUXILIARES DE INVENTARIO
# ===============================================================

def _crear_movimiento_salida_riego(riego, usuario_logueado):
    """
    Crea un movimiento de SALIDA y descuenta el stock.
    (Llamado solo por 'finalizar_riego')
    """
    productos_a_descontar = riego.fertilizantes.all()
    
    if not productos_a_descontar.exists():
        raise ValidationError("No se puede finalizar un riego sin fertilizantes.")

    # 1. Validar stock
    for fert in productos_a_descontar:
        fert.producto.refresh_from_db() 
        if fert.cantidad_kg > fert.producto.stock_actual:
            raise ValidationError(
                f"Stock insuficiente para '{fert.producto.nombre}'. "
                f"Requerido: {fert.cantidad_kg}, Disponible: {fert.producto.stock_actual}."
            )

    # 2. Crear encabezado
    movimiento_header = MovimientoInventario.objects.create(
        tipo_movimiento='salida',
        fecha_movimiento=timezone.now(),
        motivo=f"Salida por Riego ID: {riego.id} (Cuartel: {riego.cuartel.nombre})",
        realizado_por=usuario_logueado
    )

    # 3. Crear detalles y actualizar stock
    for fert in productos_a_descontar:
        producto = Producto.objects.select_for_update().get(pk=fert.producto.pk)
        
        stock_anterior = producto.stock_actual
        cantidad = fert.cantidad_kg
        
        if cantidad > stock_anterior:
             raise ValidationError(
                f"Stock insuficiente (concurrencia) para '{producto.nombre}'."
            )
        
        stock_posterior = stock_anterior - cantidad
        
        DetalleMovimiento.objects.create(
            movimiento=movimiento_header,
            producto=producto,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_posterior=stock_posterior
        )
        
        producto.stock_actual = stock_posterior
        producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])

# --- (Función _crear_movimiento_entrada_riego eliminada ya que no se usa) ---


# ===============================================================
#  VISTA PRINCIPAL: dashboard_riego (MODIFICADA)
# ===============================================================
@login_required
def dashboard_riego(request):
    """
    Dashboard principal con filtros (Cuartel y Estado)
    MODIFICADO: Tarjetas de estadísticas corregidas.
    """
    hoy = timezone.now().date()
    
    # --- 1. LÓGICA DE ESTADÍSTICAS (TARJETAS) ---
    # ¡LÓGICA DE TARJETAS ACTUALIZADA!
    todos_los_riegos = ControlRiego.objects.all()
    riegos_realizados = todos_los_riegos.filter(estado='REALIZADO')

    total_riegos = todos_los_riegos.count()
    riegos_programados = todos_los_riegos.filter(estado='PROGRAMADO').count()
    riegos_realizados_count = riegos_realizados.count() # Renombrado para claridad

    # --- CÁLCULO DE VOLUMEN MES (RE-AGREGADO) ---
    riegos_mes = riegos_realizados.filter(fecha__month=hoy.month, fecha__year=hoy.year)
    volumen_mes = riegos_mes.aggregate(total=Sum('volumen_total_m3'))['total'] or 0
    
    # --- 2. LÓGICA DE FILTROS (SIMPLIFICADA) ---
    cuartel_id = request.GET.get('cuartel', '')
    estado_filtro = request.GET.get('estado', '')
    
    # Usamos la lista de 'todos_los_riegos' que ya teníamos
    riegos_list = todos_los_riegos.select_related(
        'cuartel', 'encargado_riego'
    ).order_by('-fecha', '-horario_inicio')
    
    if cuartel_id:
        riegos_list = riegos_list.filter(cuartel_id=cuartel_id)
    if estado_filtro:
        riegos_list = riegos_list.filter(estado=estado_filtro)
    
    # --- 3. LÓGICA DE PAGINACIÓN (ELIMINADA) ---
    
    # --- 4. CONTEXTO PARA LA PLANTILLA ---
    context = {
        # ¡VARIABLES DE TARJETAS ACTUALIZADAS!
        'total_riegos': total_riegos,
        'riegos_programados': riegos_programados,
        'riegos_realizados': riegos_realizados_count, # Usamos la variable renombrada
        'volumen_mes': volumen_mes, # Pasamos el volumen del mes
        
        # Lista (Sin paginación)
        'riegos_list': riegos_list, 
        
        # Datos para rellenar los filtros
        'cuarteles': Cuartel.objects.all().order_by('nombre'),
        'cuartel_id': cuartel_id,
        'estado_filtro': estado_filtro, 
        
        'titulo': 'Dashboard - Control de Riego',
        'usuario_nombre': request.session.get('usuario_nombre', 'Usuario')
    }
    return render(request, 'riego/dashboard.html', context)


# ===============================================================
#  VISTAS CRUD (Lógica de Aplicaciones)
# ===============================================================

@login_required
def crear_riego(request):
    """
    Crear nuevo control de riego.
    Descuenta stock SÓLO SI el estado es 'REALIZADO'.
    (Sigue la lógica de crear_aplicacion).
    """
    
    usuario_id = request.session.get('usuario_id')
    try:
        usuario_logueado = Usuario.objects.get(id=usuario_id)
    except (Usuario.DoesNotExist, TypeError):
        messages.error(request, 'Error de autenticación. Inicia sesión de nuevo.')
        return redirect('login')
    
    if request.method == 'POST':
        form = ControlRiegoForm(request.POST)
        formset = FertilizanteRiegoFormSet(request.POST)
        
        form_valid = form.is_valid()
        formset_valid = formset.is_valid()

        if form_valid and form.cleaned_data.get('incluye_fertilizante'):
            if not formset_valid:
                form.add_error(None, 'Hay errores en los fertilizantes. Por favor, revísalos.')
                form_valid = False
            elif not formset.has_changed():
                form.add_error('incluye_fertilizante', 
                    "Marcaste 'Incluye Fertilizante' pero no añadiste ningún producto.")
                form_valid = False
        
        if form_valid and formset_valid:
            try:
                with transaction.atomic():
                    riego = form.save(commit=False)
                    riego.creado_por = usuario_logueado 
                    riego.save() 
                    
                    if riego.incluye_fertilizante:
                        formset.instance = riego
                        formset.save() 
                    
                    if riego.estado == 'REALIZADO':
                        if not riego.incluye_fertilizante:
                            raise ValidationError("Marcaste 'Realizado' pero no se añadieron fertilizantes.")
                        
                        _crear_movimiento_salida_riego(riego, usuario_logueado)
                        messages.success(request, f'Riego "{riego.id}" guardado y stock descontado.')
                    else:
                        messages.success(request, f'Riego "{riego.id}" programado exitosamente.')
                
                return redirect('riego:dashboard')
            
            except (ValidationError, Exception) as e:
                form.add_error(None, f"Error al procesar el inventario: {str(e)}")
                messages.error(request, 'No se pudo crear el riego. Revisa los errores.')
        
        else: 
            messages.error(request, 'Por favor corrige los errores del formulario.')

    else: # request.method == 'GET'
        form = ControlRiegoForm()
        formset = FertilizanteRiegoFormSet(instance=ControlRiego())
    
    context = {
        'form': form,
        'formset': formset,
        'usuario_logueado': usuario_logueado,
        'titulo': 'Crear Control de Riego',
        'boton_texto': 'Guardar Riego'
    }
    return render(request, 'riego/riego_form.html', context)


@login_required
def editar_riego(request, pk):
    """
    Editar control de riego.
    1. Solo se editan 'PROGRAMADOS'.
    2. Si se cambia a 'REALIZADO', descuenta stock.
    """
    riego = get_object_or_404(ControlRiego.objects.prefetch_related('fertilizantes__producto'), pk=pk)
    
    old_estado = riego.estado
    
    if riego.estado != 'PROGRAMADO':
        messages.error(request, f'El Riego ID {riego.id} no se puede editar (estado: {riego.get_estado_display()}).')
        return redirect('riego:dashboard')

    usuario_id = request.session.get('usuario_id')
    try:
        usuario_logueado = Usuario.objects.get(id=usuario_id)
    except (Usuario.DoesNotExist, TypeError):
        messages.error(request, 'Error de autenticación. Inicia sesión de nuevo.')
        return redirect('login')

    if request.method == 'POST':
        form = ControlRiegoForm(request.POST, instance=riego)
        formset = FertilizanteRiegoFormSet(request.POST, instance=riego)
        
        form_valid = form.is_valid()
        formset_valid = formset.is_valid()

        if form_valid and form.cleaned_data.get('incluye_fertilizante'):
            if not formset_valid:
                form.add_error(None, 'Hay errores en los fertilizantes.')
                form_valid = False
            elif not formset.total_form_count(): 
                form.add_error('incluye_fertilizante', "Añade al menos un producto.")
                form_valid = False

        if form_valid and formset_valid:
            try:
                with transaction.atomic():
                    riego_guardado = form.save()
                    formset.save() 
                    
                    if old_estado == 'PROGRAMADO' and riego_guardado.estado == 'REALIZADO':
                        if not riego_guardado.incluye_fertilizante:
                            raise ValidationError("Marcaste 'Realizado' pero no se añadieron fertilizantes.")
                        
                        _crear_movimiento_salida_riego(riego_guardado, usuario_logueado)
                        messages.success(request, f'Riego ID {riego.id} finalizado y stock descontado.')
                    else:
                        messages.success(request, 'Riego programado actualizado exitosamente.')

                return redirect('riego:dashboard')
                
            except (ValidationError, Exception) as e:
                form.add_error(None, f"Error al procesar el inventario: {str(e)}")
                messages.error(request, 'No se pudo actualizar el riego. Revisa los errores.')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ControlRiegoForm(instance=riego)
        formset = FertilizanteRiegoFormSet(instance=riego)
    
    context = {
        'form': form,
        'formset': formset,
        'riego': riego,
        'titulo': 'Editar Control de Riego',
        'boton_texto': 'Actualizar Riego'
    }
    return render(request, 'riego/riego_form.html', context)


@login_required
def detalle_riego(request, pk):
    """Detalle de un control de riego (Sin cambios)"""
    riego = get_object_or_404(
        ControlRiego.objects.select_related('cuartel', 'encargado_riego', 'creado_por'), 
        pk=pk
    )
    fertilizantes = riego.fertilizantes.select_related('producto').all()
    
    context = {
        'riego': riego,
        'fertilizantes': fertilizantes,
        'titulo': f'Detalle Riego - {riego.fecha}'
    }
    return render(request, 'riego/detalle_riego.html', context)


# ===============================================================
#  VISTAS DE ACCIÓN (Lógica de Aplicaciones)
# ===============================================================

@login_required
@require_POST 
def finalizar_riego(request, pk):
    """
    Cambia el estado de 'PROGRAMADO' a 'REALIZADO'
    y DESCUENTA el inventario.
    """
    riego = get_object_or_404(ControlRiego, pk=pk)
    
    usuario_id = request.session.get('usuario_id')
    try:
        usuario_logueado = Usuario.objects.get(id=usuario_id)
    except (Usuario.DoesNotExist, TypeError):
        messages.error(request, 'Error de autenticación. Inicia sesión de nuevo.')
        return redirect('login')

    if riego.estado != 'PROGRAMADO':
        messages.warning(request, f'El Riego ID {riego.id} no se puede finalizar.')
        return redirect('riego:dashboard')

    try:
        with transaction.atomic():
            if riego.incluye_fertilizante:
                _crear_movimiento_salida_riego(riego, usuario_logueado)
            
            riego.estado = 'REALIZADO'
            riego.save(update_fields=['estado'])
        
        messages.success(request, f'Riego ID {riego.id} finalizado. Stock descontado.')
    
    except (ValidationError, Exception) as e:
        messages.error(request, f'Error al finalizar Riego ID {riego.id}: {str(e)}')
    
    return redirect('riego:dashboard')


@login_required
@require_POST 
def cancelar_riego(request, pk):
    """
    MODIFICADO: Cambia el estado a 'CANCELADO'.
    NO TOCA EL INVENTARIO.
    """
    riego = get_object_or_404(ControlRiego, pk=pk)
    
    if riego.estado != 'PROGRAMADO':
        messages.warning(f'Este riego ya no se puede cancelar.', 'warning')
        return redirect('riego:dashboard')

    try:
        riego.estado = 'CANCELADO'
        riego.save(update_fields=['estado'])
        
        messages.success(request, f'Riego ID {riego.id} cancelado.')
            
        return redirect('riego:dashboard')
    
    except (ValidationError, Exception) as e:
        messages.error(request, f'Error al cancelar: {str(e)}')
        return redirect('riego:dashboard')