# aplicaciones/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction # Importante para transacciones

# --- CORRECCIÓN 2: Importar 'admin_required' de tu app autenticacion ---
from autenticacion.views import login_required, admin_required 

# Models and Forms
from .models import AplicacionFitosanitaria, AplicacionProducto
from .forms import AplicacionForm, AplicacionProductoFormSet
from cuarteles.models import Cuartel
from inventario.models import Producto, MovimientoInventario, DetalleMovimiento
from autenticacion.models import Usuario # Necesario para obtener el usuario

# -----------------------------------------------------------------------------
# VISTAS PRINCIPALES
# -----------------------------------------------------------------------------

@login_required
def lista_aplicaciones(request):
    """Muestra un listado de todas las aplicaciones"""
    
    aplicaciones_list = AplicacionFitosanitaria.objects.all().select_related(
        'aplicador', 'equipo_utilizado'
    ).prefetch_related(
        'aplicacionproducto_set__producto'
    ).order_by('-fecha_aplicacion')

    # --- Lógica de Filtros ---
    filtro_estado = request.GET.get('estado')
    filtro_producto_id = request.GET.get('producto')

    if filtro_estado:
        aplicaciones_list = aplicaciones_list.filter(estado=filtro_estado)
    if filtro_producto_id:
        aplicaciones_list = aplicaciones_list.filter(productos__id=filtro_producto_id).distinct()
    
    # --- Estadísticas ---
    total_aplicaciones = AplicacionFitosanitaria.objects.count()
    total_programadas = AplicacionFitosanitaria.objects.filter(estado='programada').count()
    total_realizadas = AplicacionFitosanitaria.objects.filter(estado='realizada').count()
    
    context = {
        'aplicaciones': aplicaciones_list,
        'todos_los_productos': Producto.objects.filter(esta_activo=True).order_by('nombre'), 
        'total_aplicaciones': total_aplicaciones,
        'total_programadas': total_programadas,
        'total_realizadas': total_realizadas,
        'filtro_estado': filtro_estado,
        'filtro_producto': int(filtro_producto_id) if filtro_producto_id else None,
    }
    return render(request, 'aplicaciones/lista_aplicaciones.html', context)


@login_required
@transaction.atomic 
def crear_aplicacion(request):
    """Vista para crear una aplicación (MODIFICADA PARA FILTRAR APLICADOR)"""
    
    # Obtenemos el objeto usuario completo para pasarlo al formulario
    usuario_logueado = get_object_or_404(Usuario, pk=request.session.get('usuario_id'))

    if request.method == 'POST':
        # --- CAMBIO AQUÍ: Pasamos 'usuario_actual' al form ---
        form = AplicacionForm(request.POST, usuario_actual=usuario_logueado)
        formset = AplicacionProductoFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            aplicacion = form.save(commit=False)
            
            aplicacion.creado_por = usuario_logueado
            
            # Asignamos el área calculada en el form.clean()
            aplicacion.area_tratada = form.cleaned_data.get('area_tratada', 0)
            
            aplicacion.save() 
            form.save_m2m() 
            
            formset.instance = aplicacion
            formset.save() 
            
            # Si se creó como "realizada", generar el movimiento AHORA
            if aplicacion.estado == 'realizada':
                try:
                    crear_movimiento_salida_para_app(aplicacion, usuario_logueado.id)
                    messages.success(request, 'Aplicación registrada. Stock descontado.')
                except ValidationError as e:
                    messages.error(request, f'Error de Stock: {e.message}')
                    context = {'form': form, 'formset': formset}
                    return render(request, 'aplicaciones/crear_aplicacion.html', context)
            else:
                 messages.success(request, 'Aplicación programada exitosamente.')

            return redirect('aplicaciones:lista_aplicaciones')
        else:
            messages.error(request, 'Error al registrar la aplicación. Revisa los campos.')
            
    else:
        # --- CAMBIO AQUÍ: Pasamos 'usuario_actual' al form ---
        form = AplicacionForm(usuario_actual=usuario_logueado)
        formset = AplicacionProductoFormSet() 

    context = {
        'form': form,
        'formset': formset,
    }
    return render(request, 'aplicaciones/crear_aplicacion.html', context)

@login_required
def detalle_aplicacion(request, aplicacion_id):
    """Muestra el detalle de una aplicación específica"""
    aplicacion = get_object_or_404(
        AplicacionFitosanitaria.objects.prefetch_related(
            'cuarteles', 
            'aplicacionproducto_set__producto'
        ), 
        id=aplicacion_id
    )
    
    movimiento = aplicacion.movimientos_inventario.first()
    
    context = {
        'aplicacion': aplicacion,
        'movimiento': movimiento,
    }
    return render(request, 'aplicaciones/detalle_aplicacion.html', context)

# =============================================================================
# VISTAS DE ACCIONES (CRUD) - CON SEGURIDAD DE PROPIEDAD
# =============================================================================

@login_required
@transaction.atomic
def editar_aplicacion(request, app_id):
    """Vista para editar una aplicación"""
    aplicacion = get_object_or_404(AplicacionFitosanitaria, id=app_id)
    
    # --- SEGURIDAD: Validar propiedad ---
    usuario_id = request.session.get('usuario_id')
    es_admin = request.session.get('es_administrador')
    
    # Si NO es admin Y el aplicador asignado NO es el usuario actual
    if not es_admin and aplicacion.aplicador.id != usuario_id:
        messages.error(request, 'No tienes permiso para editar tareas de otros aplicadores.')
        return redirect('aplicaciones:lista_aplicaciones')
    # ------------------------------------

    usuario_logueado = get_object_or_404(Usuario, pk=usuario_id)

    if aplicacion.estado != 'programada':
        messages.error(request, 'No se puede editar una aplicación que ya está realizada o cancelada.')
        return redirect('aplicaciones:lista_aplicaciones')

    if request.method == 'POST':
        # Pasamos usuario_actual para que el form sepa qué lista de aplicadores mostrar
        form = AplicacionForm(request.POST, instance=aplicacion, usuario_actual=usuario_logueado)
        formset = AplicacionProductoFormSet(request.POST, instance=aplicacion)
        
        if form.is_valid() and formset.is_valid():
            aplicacion = form.save(commit=False)
            aplicacion.area_tratada = form.cleaned_data.get('area_tratada', 0)
            aplicacion.save()
            form.save_m2m()
            formset.save() 
            
            if aplicacion.estado == 'realizada':
                try:
                    crear_movimiento_salida_para_app(aplicacion, usuario_id)
                    messages.success(request, f'Aplicación APL-{aplicacion.id} actualizada y finalizada. Stock descontado.')
                except ValidationError as e:
                    messages.error(request, f'Error de Stock: {e.message}')
                    context = {'form': form, 'formset': formset, 'aplicacion': aplicacion}
                    return render(request, 'aplicaciones/crear_aplicacion.html', context)
            else:
                messages.success(request, f'Aplicación APL-{aplicacion.id} actualizada.')
                
            return redirect('aplicaciones:lista_aplicaciones')
    else:
        form = AplicacionForm(instance=aplicacion, usuario_actual=usuario_logueado)
        formset = AplicacionProductoFormSet(instance=aplicacion) 

    context = {
        'form': form,
        'formset': formset, 
        'aplicacion': aplicacion,
        'titulo': 'Editar Aplicación' # Agregué título para que se vea bien en el template
    }
    return render(request, 'aplicaciones/crear_aplicacion.html', context)


@login_required
@transaction.atomic 
def finalizar_aplicacion(request, app_id):
    """Marca una aplicación 'programada' como 'realizada'"""
    if request.method != 'POST':
        return redirect('aplicaciones:lista_aplicaciones')

    aplicacion = get_object_or_404(AplicacionFitosanitaria, id=app_id)

    # --- SEGURIDAD: Validar propiedad ---
    usuario_id = request.session.get('usuario_id')
    es_admin = request.session.get('es_administrador')
    
    if not es_admin and aplicacion.aplicador.id != usuario_id:
        messages.error(request, 'No tienes permiso para finalizar tareas de otros.')
        return redirect('aplicaciones:lista_aplicaciones')
    # ------------------------------------

    if aplicacion.estado != 'programada':
        messages.error(request, 'Esta aplicación no se puede finalizar.')
        return redirect('aplicaciones:lista_aplicaciones')

    try:
        crear_movimiento_salida_para_app(aplicacion, usuario_id)
        
        aplicacion.estado = 'realizada'
        aplicacion.save(update_fields=['estado', 'fecha_actualizacion'])
        messages.success(request, f'Aplicación APL-{aplicacion.id} finalizada. Stock descontado.')

    except ValidationError as e:
        messages.error(request, f'Error al descontar stock: {e.message}')
    
    return redirect('aplicaciones:lista_aplicaciones')


@login_required
def cancelar_aplicacion(request, app_id):
    """Marca una aplicación 'programada' como 'cancelada'."""
    if request.method != 'POST':
        return redirect('aplicaciones:lista_aplicaciones')
        
    aplicacion = get_object_or_404(AplicacionFitosanitaria, id=app_id)

    # --- SEGURIDAD: Validar propiedad ---
    usuario_id = request.session.get('usuario_id')
    es_admin = request.session.get('es_administrador')
    
    if not es_admin and aplicacion.aplicador.id != usuario_id:
        messages.error(request, 'No tienes permiso para cancelar tareas de otros.')
        return redirect('aplicaciones:lista_aplicaciones')
    # ------------------------------------

    if aplicacion.estado != 'programada':
        messages.error(request, 'Esta aplicación no se puede cancelar.')
    else:
        aplicacion.estado = 'cancelada'
        aplicacion.save(update_fields=['estado', 'fecha_actualizacion'])
        messages.info(request, f'Aplicación APL-{aplicacion.id} ha sido cancelada.')
        
    return redirect('aplicaciones:lista_aplicaciones')


# --- FUNCIÓN AUXILIAR (REUTILIZABLE) ---
def crear_movimiento_salida_para_app(aplicacion, usuario_id):
    """
    Función reutilizable que valida stock y crea el MovimientoInventario
    y sus DetalleMovimiento asociados.
    """
    
    if aplicacion.movimientos_inventario.exists():
        return 

    productos_a_descontar = aplicacion.aplicacionproducto_set.all()
    
    if not productos_a_descontar.exists():
        raise ValidationError("No se puede finalizar una aplicación sin productos.")

    # 1. Validar stock
    for app_prod in productos_a_descontar:
        producto = app_prod.producto
        producto.refresh_from_db() 
        
        if app_prod.cantidad_utilizada > producto.stock_actual:
            raise ValidationError(
                f"Stock insuficiente para '{producto.nombre}'. "
                f"Requerido: {app_prod.cantidad_utilizada} {producto.unidad_medida}, "
                f"Disponible: {producto.stock_actual} {producto.unidad_medida}."
            )

    # 2. Crear el movimiento
    movimiento = MovimientoInventario.objects.create(
        tipo_movimiento='salida',
        fecha_movimiento=aplicacion.fecha_aplicacion,
        motivo=f"Salida por Aplicación Fitosanitaria ID: {aplicacion.id}",
        referencia=f"APL-{aplicacion.id}",
        realizado_por_id=usuario_id,
        aplicacion=aplicacion
    )

    # 3. Crear detalles y actualizar stock
    for app_prod in productos_a_descontar:
        producto = app_prod.producto
        cantidad = app_prod.cantidad_utilizada
        
        producto.refresh_from_db()
        stock_anterior = producto.stock_actual
        
        if cantidad > stock_anterior:
             raise ValidationError(f"Stock insuficiente (concurrencia) para '{producto.nombre}'.")

        stock_posterior = stock_anterior - cantidad
        
        DetalleMovimiento.objects.create(
            movimiento=movimiento,
            producto=producto,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_posterior=stock_posterior
        )
        
        producto.stock_actual = stock_posterior
        producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])