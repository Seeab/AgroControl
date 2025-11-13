# aplicaciones/views.py

from django.shortcuts import render, get_object_or_404, redirect
# --- CORRECCIÓN 1: Quitar el import de Django ---
# from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction # Importante para transacciones

# --- CORRECCIÓN 2: Asegurarse de importar 'admin_required' de tu app ---
from autenticacion.views import login_required, admin_required 

# Models and Forms
from .models import AplicacionFitosanitaria, AplicacionProducto
from .forms import AplicacionForm, AplicacionProductoFormSet # Importar el FormSet
from cuarteles.models import Cuartel
from inventario.models import Producto , MovimientoInventario, DetalleMovimiento # Importar DetalleMovimiento

# -----------------------------------------------------------------------------
# VISTAS PRINCIPALES
# -----------------------------------------------------------------------------

@login_required
def lista_aplicaciones(request):
    """Muestra un listado de todas las aplicaciones (MODIFICADO)"""
    
    # --- MODIFICADO: Usar prefetch_related para la tabla intermedia ---
    aplicaciones_list = AplicacionFitosanitaria.objects.all().select_related(
        'aplicador', 'equipo_utilizado'
    ).prefetch_related(
        'aplicacionproducto_set__producto' # Optimiza la carga de productos
    ).order_by('-fecha_aplicacion')

    # --- Lógica de Filtros (MODIFICADA) ---
    filtro_estado = request.GET.get('estado')
    filtro_producto_id = request.GET.get('producto')

    if filtro_estado:
        aplicaciones_list = aplicaciones_list.filter(estado=filtro_estado)
    if filtro_producto_id:
        # Filtra si CUALQUIERA de los productos en la aplicación coincide
        # .distinct() es importante para evitar duplicados
        aplicaciones_list = aplicaciones_list.filter(productos__id=filtro_producto_id).distinct()
    
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
@transaction.atomic # Asegura que todo se guarde, o nada
def crear_aplicacion(request):
    """Vista para crear una aplicación (MODIFICADA CON FORMSET)"""
    
    if request.method == 'POST':
        form = AplicacionForm(request.POST)
        # Instanciamos el formset CON los datos POST
        formset = AplicacionProductoFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            aplicacion = form.save(commit=False)
            
            # --- CAMBIO IMPORTANTE: Asignar el usuario desde la SESIÓN ---
            aplicacion.creado_por_id = request.session.get('usuario_id')
            
            # Asignamos el área calculada en el form.clean()
            aplicacion.area_tratada = form.cleaned_data.get('area_tratada', 0)
            
            aplicacion.save() # Guardar la aplicación PRIMERO
            form.save_m2m() # Guardar la relación M2M con cuarteles
            
            # --- GUARDAR EL FORMSET ---
            # Asignar la aplicación recién creada al formset
            formset.instance = aplicacion
            formset.save() # Esto guarda las instancias de AplicacionProducto
            
            # Si se creó como "realizada", generar el movimiento AHORA
            # (Se movió la lógica de la señal aquí)
            if aplicacion.estado == 'realizada':
                try:
                    # Llamamos a la nueva función que genera el movimiento
                    crear_movimiento_salida_para_app(aplicacion, request.session.get('usuario_id'))
                    messages.success(request, 'Aplicación registrada. Stock descontado.')
                except ValidationError as e:
                    # Si falla el stock, se revierte la transacción (gracias a @transaction.atomic)
                    messages.error(request, f'Error de Stock: {e.message}')
                    # Devolvemos el form y formset para corregir
                    context = {'form': form, 'formset': formset}
                    return render(request, 'aplicaciones/crear_aplicacion.html', context)
            else:
                 messages.success(request, 'Aplicación programada exitosamente.')

            return redirect('aplicaciones:lista_aplicaciones')
        else:
            # Añadimos el mensaje de error si el form o formset no es válido
            messages.error(request, 'Error al registrar la aplicación. Revisa los campos.')
            
    else:
        form = AplicacionForm()
        formset = AplicacionProductoFormSet() # Formset vacío

    # --- CONTEXTO MODIFICADO ---
    context = {
        'form': form,
        'formset': formset, # Pasamos el formset al template
    }
    return render(request, 'aplicaciones/crear_aplicacion.html', context)

@login_required
def detalle_aplicacion(request, aplicacion_id):
    """Muestra el detalle de una aplicación específica (MODIFICADO)"""
    aplicacion = get_object_or_404(
        AplicacionFitosanitaria.objects.prefetch_related(
            'cuarteles', 
            'aplicacionproducto_set__producto' # Carga productos y detalles
        ), 
        id=aplicacion_id
    )
    
    # --- MODIFICADO: Buscar el movimiento asociado ---
    # Una aplicación ahora puede tener UN movimiento
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
@transaction.atomic
def editar_aplicacion(request, app_id):
    """Vista para editar una aplicación (MODIFICADA CON FORMSET)"""
    aplicacion = get_object_or_404(AplicacionFitosanitaria, id=app_id)

    if aplicacion.estado != 'programada':
        # Añadimos el mensaje de error que faltaba
        messages.error(request, 'No se puede editar una aplicación que ya está realizada o cancelada.')
        return redirect('aplicaciones:lista_aplicaciones')

    if request.method == 'POST':
        form = AplicacionForm(request.POST, instance=aplicacion)
        # Pasamos la instancia al formset también
        formset = AplicacionProductoFormSet(request.POST, instance=aplicacion)
        
        if form.is_valid() and formset.is_valid():
            aplicacion = form.save(commit=False)
            
            # Re-calculamos y asignamos
            aplicacion.area_tratada = form.cleaned_data.get('area_tratada', 0)
            
            aplicacion.save()
            form.save_m2m()
            formset.save() # Guardar los cambios del formset
            
            # Si la aplicación editada se marca como 'realizada'
            if aplicacion.estado == 'realizada':
                try:
                    crear_movimiento_salida_para_app(aplicacion, request.session.get('usuario_id'))
                    messages.success(request, f'Aplicación APL-{aplicacion.id} actualizada y finalizada. Stock descontado.')
                except ValidationError as e:
                    messages.error(request, f'Error de Stock: {e.message}')
                    # Revertir transacción y volver al form
                    context = {'form': form, 'formset': formset, 'aplicacion': aplicacion}
                    return render(request, 'aplicaciones/crear_aplicacion.html', context)
            else:
                messages.success(request, f'Aplicación APL-{aplicacion.id} actualizada.')
                
            return redirect('aplicaciones:lista_aplicaciones')
    else:
        form = AplicacionForm(instance=aplicacion)
        formset = AplicacionProductoFormSet(instance=aplicacion) # Formset con datos existentes

    # --- CONTEXTO MODIFICADO ---
    context = {
        'form': form,
        'formset': formset, # Pasamos el formset
        'aplicacion': aplicacion,
    }
    return render(request, 'aplicaciones/crear_aplicacion.html', context) # Reusa el template


@login_required
@transaction.atomic # Importante
def finalizar_aplicacion(request, app_id):
    """
    Marca una aplicación 'programada' como 'realizada' y descuenta stock.
    (LÓGICA CENTRAL MODIFICADA)
    """
    if request.method != 'POST':
        return redirect('aplicaciones:lista_aplicaciones')

    aplicacion = get_object_or_404(AplicacionFitosanitaria, id=app_id)

    if aplicacion.estado != 'programada':
        messages.error(request, 'Esta aplicación no se puede finalizar.')
        return redirect('aplicaciones:lista_aplicaciones')

    try:
        # --- NUEVA FUNCIÓN ---
        # Esta función hace todo: valida stock, crea movimiento y detalles,
        # y actualiza el stock de los productos.
        crear_movimiento_salida_para_app(aplicacion, request.session.get('usuario_id'))
        
        # Si todo va bien, actualizamos el estado
        aplicacion.estado = 'realizada'
        aplicacion.save(update_fields=['estado', 'fecha_actualizacion'])
        messages.success(request, f'Aplicación APL-{aplicacion.id} finalizada. Stock descontado.')

    except ValidationError as e:
        # La función crear_movimiento_salida_para_app lanza ValidationError si falla el stock
        messages.error(request, f'Error al descontar stock: {e.message}')
    
    return redirect('aplicaciones:lista_aplicaciones')


@login_required
def cancelar_aplicacion(request, app_id):
    """
    Marca una aplicación 'programada' como 'cancelada'.
    (SIN CAMBIOS)
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


# --- NUEVA FUNCIÓN AUXILIAR ---
def crear_movimiento_salida_para_app(aplicacion, usuario_id):
    """
    Función reutilizable que valida stock y crea el MovimientoInventario
    y sus DetalleMovimiento asociados.
    Lanza ValidationError si el stock falla.
    
    (LÓGICA MOVIDA DESDE 'signals.py' Y 'finalizar_aplicacion')
    """
    
    # Evitar crear movimientos duplicados si ya existe uno
    if aplicacion.movimientos_inventario.exists():
        # Esto puede pasar si se edita una app 'realizada'
        # O si se da doble click al botón.
        # Simplemente no hacemos nada.
        return 

    productos_a_descontar = aplicacion.aplicacionproducto_set.all()
    
    if not productos_a_descontar.exists():
        raise ValidationError("No se puede finalizar una aplicación sin productos.")

    # 1. RF020 (Re-validación): Validar stock OTRA VEZ antes de finalizar
    for app_prod in productos_a_descontar:
        producto = app_prod.producto
        producto.refresh_from_db() # Nos aseguramos de tener el stock más reciente
        
        if app_prod.cantidad_utilizada > producto.stock_actual:
            raise ValidationError(
                f"Stock insuficiente para '{producto.nombre}'. "
                f"Requerido: {app_prod.cantidad_utilizada} {producto.unidad_medida}, "
                f"Disponible: {producto.stock_actual} {producto.unidad_medida}."
            )

    # 2. RF021: Crear el movimiento de inventario (el "encabezado")
    movimiento = MovimientoInventario.objects.create(
        tipo_movimiento='salida',
        fecha_movimiento=aplicacion.fecha_aplicacion,
        motivo=f"Salida por Aplicación Fitosanitaria ID: {aplicacion.id}",
        referencia=f"APL-{aplicacion.id}",
        realizado_por_id=usuario_id,
        aplicacion=aplicacion
    )

    # 3. Crear los detalles del movimiento y ACTUALIZAR STOCK
    for app_prod in productos_a_descontar:
        producto = app_prod.producto
        cantidad = app_prod.cantidad_utilizada
        
        # Leemos el stock de nuevo POR SI ACASO
        # (Aunque @transaction.atomic debería bastar)
        producto.refresh_from_db()
        stock_anterior = producto.stock_actual
        
        # Validar de nuevo por si el mismo producto está 2 veces en la lista
        if cantidad > stock_anterior:
             raise ValidationError(
                f"Stock insuficiente (concurrencia) para '{producto.nombre}'. "
                f"Requerido: {cantidad}, Disponible: {stock_anterior}."
            )

        stock_posterior = stock_anterior - cantidad
        
        # Crear el detalle
        DetalleMovimiento.objects.create(
            movimiento=movimiento,
            producto=producto,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_posterior=stock_posterior
        )
        
        # Actualizar el stock del producto
        producto.stock_actual = stock_posterior
        producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])

    # Si todo salió bien, la transacción se completará.
    # Si algo falló (ej: ValidationError), @transaction.atomic revertirá todo.