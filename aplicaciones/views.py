from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from autenticacion.views import login_required 

# Models and Forms
from .models import AplicacionFitosanitaria
from .forms import AplicacionForm
from cuarteles.models import Cuartel
from inventario.models import Producto , MovimientoInventario

# -----------------------------------------------------------------------------
# VISTAS PRINCIPALES
# -----------------------------------------------------------------------------

@login_required
def lista_aplicaciones(request):
    """Muestra un listado de todas las aplicaciones"""
    
    aplicaciones_list = AplicacionFitosanitaria.objects.all().select_related(
        'producto', 'aplicador'
    ).order_by('-fecha_aplicacion')

    # --- Lógica de Filtros ---
    filtro_estado = request.GET.get('estado')
    filtro_producto_id = request.GET.get('producto')

    if filtro_estado:
        aplicaciones_list = aplicaciones_list.filter(estado=filtro_estado)
    if filtro_producto_id:
        aplicaciones_list = aplicaciones_list.filter(producto_id=filtro_producto_id)
    
    # --- Estadísticas (como en tu lista de inventario) ---
    total_aplicaciones = AplicacionFitosanitaria.objects.count()
    total_programadas = AplicacionFitosanitaria.objects.filter(estado='programada').count()
    total_realizadas = AplicacionFitosanitaria.objects.filter(estado='realizada').count()
    
    context = {
        'aplicaciones': aplicaciones_list, # La lista filtrada
        
        # Datos para los filtros
        'todos_los_productos': Producto.objects.filter(esta_activo=True).order_by('nombre'), 
        
        # Datos para las tarjetas de estadísticas
        'total_aplicaciones': total_aplicaciones,
        'total_programadas': total_programadas,
        'total_realizadas': total_realizadas,
        
        # Valores actuales de los filtros
        'filtro_estado': filtro_estado,
        'filtro_producto': int(filtro_producto_id) if filtro_producto_id else None,
    }
    return render(request, 'aplicaciones/lista_aplicaciones.html', context)

@login_required
@permission_required('aplicaciones.add_aplicacionfitosanitaria', raise_exception=True)
def crear_aplicacion(request):
    
    if request.method == 'POST':
        form = AplicacionForm(request.POST)
        
        if form.is_valid():
            aplicacion = form.save(commit=False)
            aplicacion.creado_por = request.user
            
            # Asignamos los valores calculados en el form.clean()
            aplicacion.area_tratada = form.cleaned_data.get('area_tratada', 0)
            aplicacion.dosis_por_hectarea = form.cleaned_data.get('dosis_por_hectarea', 0)
            
            aplicacion.save() 
            form.save_m2m()
            
            messages.success(request, 'Aplicación registrada. Stock descontado.')
            return redirect('aplicaciones:lista_aplicaciones')
        else:
            # Añadimos el mensaje de error si el form no es válido
            messages.error(request, 'Error al registrar la aplicación. Revisa los campos.')
            
    else:
        form = AplicacionForm()

    # --- CONTEXTO LIMPIADO ---
    # Ya no pasamos los datos JSON
    context = {
        'form': form,
    }
    return render(request, 'aplicaciones/crear_aplicacion.html', context)

@login_required
def detalle_aplicacion(request, aplicacion_id):
    """Muestra el detalle de una aplicación específica"""
    aplicacion = get_object_or_404(
        AplicacionFitosanitaria.objects.prefetch_related('cuarteles'), 
        id=aplicacion_id
    )
    
    # Opcional: buscar el movimiento de inventario asociado
    movimiento = aplicacion.movimientos_inventario.first()
    
    context = {
        'aplicacion': aplicacion,
        'movimiento': movimiento,
    }
    return render(request, 'aplicaciones/detalle_aplicacion.html', context)

# -----------------------------------------------------------------------------
# VISTAS DE ACCIONES (CRUD)
# -----------------------------------------------------------------------------

@login_required
@permission_required('aplicaciones.change_aplicacionfitosanitaria', raise_exception=True)
def editar_aplicacion(request, app_id):
    aplicacion = get_object_or_404(AplicacionFitosanitaria, id=app_id)

    if aplicacion.estado != 'programada':
        # Añadimos el mensaje de error que faltaba
        messages.error(request, 'No se puede editar una aplicación que ya está realizada o cancelada.')
        return redirect('aplicaciones:lista_aplicaciones')

    if request.method == 'POST':
        form = AplicacionForm(request.POST, instance=aplicacion)
        if form.is_valid():
            aplicacion = form.save(commit=False)
            
            # Re-calculamos y asignamos
            aplicacion.area_tratada = form.cleaned_data.get('area_tratada', 0)
            aplicacion.dosis_por_hectarea = form.cleaned_data.get('dosis_por_hectarea', 0)
            
            aplicacion.save()
            form.save_m2m()
            messages.success(request, f'Aplicación APL-{aplicacion.id} actualizada.')
            return redirect('aplicaciones:lista_aplicaciones')
    else:
        form = AplicacionForm(instance=aplicacion)

    # --- CONTEXTO LIMPIADO ---
    # Ya no pasamos los datos JSON
    context = {
        'form': form,
        'aplicacion': aplicacion,
    }
    return render(request, 'aplicaciones/crear_aplicacion.html', context)


@login_required
@permission_required('aplicaciones.change_aplicacionfitosanitaria', raise_exception=True)
def finalizar_aplicacion(request, app_id):
    """
    Marca una aplicación 'programada' como 'realizada' y descuenta stock.
    """
    if request.method != 'POST':
        return redirect('aplicaciones:lista_aplicaciones')

    aplicacion = get_object_or_404(AplicacionFitosanitaria, id=app_id)

    if aplicacion.estado != 'programada':
        messages.error(request, 'Esta aplicación no se puede finalizar.')
        return redirect('aplicaciones:lista_aplicaciones')

    # RF020 (Re-validación): Validar stock OTRA VEZ antes de finalizar
    producto = aplicacion.producto
    producto.refresh_from_db() # Nos aseguramos de tener el stock más reciente
    
    if aplicacion.cantidad_utilizada > producto.stock_actual:
        messages.error(
            request, 
            f"No se puede finalizar. Stock insuficiente para '{producto.nombre}'. "
            f"Requerido: {aplicacion.cantidad_utilizada} {producto.unidad_medida}, "
            f"Disponible: {producto.stock_actual} {producto.unidad_medida}."
        )
        return redirect('aplicaciones:lista_aplicaciones')

    try:
        # RF021: Crear el movimiento de inventario manualmente
        # (La señal 'post_save' solo funciona en 'created=True')
        MovimientoInventario.objects.create(
            producto=aplicacion.producto,
            tipo_movimiento='salida',
            cantidad=aplicacion.cantidad_utilizada,
            fecha_movimiento=aplicacion.fecha_aplicacion,
            motivo=f"Salida por Aplicación Fitosanitaria ID: {aplicacion.id}",
            referencia=f"APL-{aplicacion.id}",
            realizado_por=request.user, 
            aplicacion=aplicacion
        )
        
        # Si todo va bien, actualizamos el estado
        aplicacion.estado = 'realizada'
        aplicacion.save(update_fields=['estado', 'fecha_actualizacion'])
        messages.success(request, f'Aplicación APL-{aplicacion.id} finalizada. Stock descontado.')

    except ValidationError as e:
        messages.error(request, f'Error al descontar stock: {e}')
    
    return redirect('aplicaciones:lista_aplicaciones')


@login_required
@permission_required('aplicaciones.change_aplicacionfitosanitaria', raise_exception=True)
def cancelar_aplicacion(request, app_id):
    """
    Marca una aplicación 'programada' como 'cancelada'.
    """
    if request.method != 'POST':
        return redirect('aplicaciones:lista_aplicaciones')
        
    aplicacion = get_object_or_404(AplicacionFitosanitaria, id=app_id)

    if aplicacion.estado != 'programada':
        messages.error(request, 'Esta aplicación no se puede cancelar.')
    else:
        aplicacion.estado = 'cancelada'
        aplicacion.save(update_fields=['estado', 'fecha_actualizacion'])
        messages.info(request, f'Aplicación APL-{aplicacion.id} ha sido cancelada.')
        
    return redirect('aplicaciones:lista_aplicaciones')