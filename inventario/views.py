# inventario/views.py

from django.shortcuts import render, get_object_or_404, redirect
from autenticacion.views import login_required, admin_required
from django.contrib import messages
from django.db import models, transaction # Importar transaction
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from .models import Producto, MovimientoInventario, EquipoAgricola, DetalleMovimiento
from .forms import (
    ProductoForm, MovimientoInventarioForm, EquipoAgricolaForm,
    DetalleMovimientoFormSet # Importar el FormSet
)


@admin_required
def lista_productos(request):
    """(SIN CAMBIOS)"""
    productos = Producto.objects.all().order_by('nombre')
    
    # Filtros
    tipo = request.GET.get('tipo')
    estado_stock = request.GET.get('estado_stock')
    peligrosidad = request.GET.get('peligrosidad')
    
    if tipo:
        productos = productos.filter(tipo=tipo)
    if estado_stock:
        if estado_stock == 'bajo':
            productos = productos.filter(stock_actual__lt=models.F('stock_minimo'))
        elif estado_stock == 'agotado':
            productos = productos.filter(stock_actual=0)
        elif estado_stock == 'normal':
            productos = productos.filter(stock_actual__gte=models.F('stock_minimo'))
    if peligrosidad:
        productos = productos.filter(nivel_peligrosidad=peligrosidad)
    
    # Estadísticas
    total_productos = Producto.objects.count()
    productos_bajo_stock = Producto.objects.filter(
        stock_actual__lt=models.F('stock_minimo'),
        stock_actual__gt=0
    ).count()
    productos_agotados = Producto.objects.filter(stock_actual=0).count()
    
    # Productos en alerta para mostrar
    productos_alerta = Producto.objects.filter(
        models.Q(stock_actual__lt=models.F('stock_minimo')) | 
        models.Q(stock_actual=0)
    )[:5]
    
    context = {
        'productos': productos,
        'total_productos': total_productos,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_agotados': productos_agotados,
        'productos_alerta': productos_alerta,
        'filtro_tipo': tipo,
        'filtro_estado_stock': estado_stock,
        'filtro_peligrosidad': peligrosidad,
    }
    return render(request, 'inventario/lista_productos.html', context)

# CAMBIADO: Usamos admin_required en lugar de permission_required
@admin_required 
def crear_producto(request):
    """(SIN CAMBIOS)"""
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            # Asignamos el usuario desde la SESIÓN
            producto.creado_por_id = request.session.get('usuario_id') 
            producto.save()
            messages.success(request, f'Producto {producto.nombre} creado exitosamente.')
            return redirect('inventario:lista_productos')
    else:
        form = ProductoForm()
    
    context = {'form': form, 'page_title': 'Crear Producto'} # Añadido page_title
    return render(request, 'inventario/crear_producto.html', context)

@admin_required
def detalle_producto(request, producto_id):
    """(SIN CAMBIOS)"""
    producto = get_object_or_404(Producto, id=producto_id)
    context = {'producto': producto, 'page_title': f'Detalle: {producto.nombre}'} # Añadido page_title
    return render(request, 'inventario/detalle_producto.html', context)


@admin_required
def editar_producto(request, producto_id):
    """(SIN CAMBIOS)"""
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto {producto.nombre} actualizado exitosamente.')
            return redirect('inventario:detalle_producto', producto_id=producto.id)
    else:
        form = ProductoForm(instance=producto)
    
    context = {
        'form': form, 
        'producto': producto,
        'page_title': f'Editar: {producto.nombre}' # Añadido page_title
    }
    return render(request, 'inventario/crear_producto.html', context) # Reusa el template


@admin_required
@transaction.atomic # Importante para la lógica de stock
def crear_movimiento(request, producto_id=None):
    """(MODIFICADO) Vista para crear movimientos manuales (Entrada/Ajuste) con FORMSET"""
    
    producto_inicial = None
    if producto_id:
        producto_inicial = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        form = MovimientoInventarioForm(request.POST)
        formset = DetalleMovimientoFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            movimiento = form.save(commit=False)
            movimiento.realizado_por_id = request.session.get('usuario_id')
            movimiento.save() # Guardar el encabezado
            
            formset.instance = movimiento
            detalles_a_guardar = formset.save(commit=False) # No guardar aún
            
            # --- Lógica de Stock ---
            for detalle in detalles_a_guardar:
                # Omitir si está marcado para borrarse
                if detalle in formset.deleted_objects:
                    continue

                producto = detalle.producto
                cantidad = detalle.cantidad
                
                # Refrescar producto para evitar concurrencia
                producto.refresh_from_db() 
                
                stock_anterior = producto.stock_actual
                
                if movimiento.tipo_movimiento == 'entrada':
                    stock_posterior = stock_anterior + cantidad
                elif movimiento.tipo_movimiento == 'ajuste':
                    stock_posterior = cantidad # Ajuste define el stock
                else:
                    # Esto no debería pasar gracias al form
                    stock_posterior = stock_anterior 
                
                # Asignar stocks al detalle
                detalle.stock_anterior = stock_anterior
                detalle.stock_posterior = stock_posterior
                detalle.save() # Guardar el detalle
                
                # Actualizar el producto
                producto.stock_actual = stock_posterior
                producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])
            
            # Manejar objetos borrados (si se edita un movimiento)
            for detalle in formset.deleted_objects:
                # (Aquí iría la lógica para revertir el stock si editáramos,
                # pero para 'crear' no es necesario)
                detalle.delete()
            
            messages.success(request, 'Movimiento registrado exitosamente.')
            return redirect('inventario:historial_movimientos')
        else:
             messages.error(request, 'Error al registrar el movimiento. Revisa los campos.')

    else:
        initial_data = [] # Debe ser una lista para el formset
        if producto_inicial:
            # Pre-llenar el primer form del formset
            initial_data = [{
                'producto': producto_inicial
            }]
            
        form = MovimientoInventarioForm()
        formset = DetalleMovimientoFormSet(initial=initial_data)
    
    context = {
        'form': form,
        'formset': formset, # Pasar el formset al template
        'producto': producto_inicial, # Para el título si aplica
        'page_title': 'Registrar Movimiento'
    }
    return render(request, 'inventario/crear_movimiento.html', context)

@login_required
def historial_movimientos(request):
    """(MODIFICADO) Vista de historial con prefetch"""
    
    # --- MODIFICADO: Usar prefetch_related para detalles ---
    movimientos = MovimientoInventario.objects.all().select_related(
        'realizado_por', 'aplicacion'
    ).prefetch_related(
        'detalles__producto' # Optimiza la carga para el tooltip
    ).order_by('-fecha_movimiento')
    
    # --- Filtros (MODIFICADOS) ---
    producto_id = request.GET.get('producto')
    tipo_movimiento = request.GET.get('tipo_movimiento')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if producto_id:
        # Filtrar si CUALQUIER detalle coincide
        movimientos = movimientos.filter(detalles__producto_id=producto_id).distinct()
    if tipo_movimiento:
        movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)
    if fecha_desde:
        movimientos = movimientos.filter(fecha_movimiento__gte=fecha_desde)
    if fecha_hasta:
        # Añadir +1 día para incluir el día completo
        # O asumir que el datepicker lo maneja. Por simpleza, lo dejamos así.
        movimientos = movimientos.filter(fecha_movimiento__lte=fecha_hasta)
    
    paginator = Paginator(movimientos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    total_movimientos = movimientos.count()
    total_entradas = movimientos.filter(tipo_movimiento='entrada').count()
    total_salidas = movimientos.filter(tipo_movimiento='salida').count()
    total_ajustes = movimientos.filter(tipo_movimiento='ajuste').count()
    
    context = {
        'movimientos': page_obj,
        'productos': Producto.objects.all(),
        'total_movimientos': total_movimientos,
        'total_entradas': total_entradas,
        'total_salidas': total_salidas,
        'total_ajustes': total_ajustes,
        'filtro_producto': producto_id,
        'filtro_tipo': tipo_movimiento,
        'filtro_fecha_desde': fecha_desde,
        'filtro_fecha_hasta': fecha_hasta,
        'page_title': 'Historial de Movimientos' # Añadido page_title
    }
    return render(request, 'inventario/historial_movimientos.html', context)


@admin_required
def detalle_movimiento(request, movimiento_id):
    """(NUEVA VISTA) Muestra el detalle de un movimiento y todos sus productos"""
    movimiento = get_object_or_404(
        MovimientoInventario.objects.prefetch_related('detalles__producto', 'realizado_por'),
        id=movimiento_id
    )
    
    context = {
        'movimiento': movimiento,
        'detalles': movimiento.detalles.all(), # Pasamos los detalles
        'page_title': f'Detalle Movimiento #{movimiento.id}'
    }
    return render(request, 'inventario/detalle_movimiento.html', context)


@admin_required
def lista_maquinaria(request):
    """
    Vista para listar Maquinaria y Herramientas (RF026).
    (SIN CAMBIOS)
    """
    equipos = EquipoAgricola.objects.all().order_by('nombre')
    
    # Filtros
    tipo = request.GET.get('tipo')
    estado = request.GET.get('estado')
    
    if tipo:
        equipos = equipos.filter(tipo=tipo)
    if estado:
        equipos = equipos.filter(estado=estado)
    
    # Estadísticas
    total_equipos = EquipoAgricola.objects.count()
    equipos_operativos = EquipoAgricola.objects.filter(estado='operativo').count()
    equipos_mantenimiento = EquipoAgricola.objects.filter(estado='mantenimiento').count()
    
    context = {
        'equipos': equipos,
        'total_equipos': total_equipos,
        'equipos_operativos': equipos_operativos,
        'equipos_mantenimiento': equipos_mantenimiento,
        'filtro_tipo': tipo,
        'filtro_estado': estado,
        'page_title': 'Maquinaria y Herramientas'
    }
    return render(request, 'inventario/lista_maquinaria.html', context)

@admin_required
def crear_maquinaria(request):
    """
    Vista para registrar una nueva Maquinaria o Herramienta (RF026).
    (SIN CAMBIOS)
    """
    if request.method == 'POST':
        form = EquipoAgricolaForm(request.POST)
        if form.is_valid():
            equipo = form.save(commit=False)
            
            # --- CAMBIO: Línea eliminada ---
            # Ya no asignamos 'creado_por_id' porque no está en el modelo
            # equipo.creado_por_id = request.session.get('usuario_id') 
            
            equipo.save()
            messages.success(request, f'Equipo "{equipo.nombre}" creado exitosamente.')
            return redirect('inventario:lista_maquinaria')
    else:
        form = EquipoAgricolaForm()
    
    context = {
        'form': form, 
        'page_title': 'Registrar Maquinaria o Herramienta'
    }
    return render(request, 'inventario/crear_maquinaria.html', context)

@login_required
def detalle_maquinaria(request, equipo_id):
    """(SIN CAMBIOS)"""
    equipo = get_object_or_404(EquipoAgricola, id=equipo_id)
    context = {
        'equipo': equipo, 
        'page_title': f'Detalle Equipo: {equipo.nombre}'
    }
    return render(request, 'inventario/detalle_maquinaria.html', context)

@admin_required
def editar_maquinaria(request, equipo_id):
    """(SIN CAMBIOS)"""
    equipo = get_object_or_404(EquipoAgricola, id=equipo_id)
    
    if request.method == 'POST':
        form = EquipoAgricolaForm(request.POST, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Equipo "{equipo.nombre}" actualizado exitosamente.')
            return redirect('inventario:detalle_maquinaria', equipo_id=equipo.id)
    else:
        form = EquipoAgricolaForm(instance=equipo)
    
    context = {
        'form': form, 
        'equipo': equipo, # Lo pasamos para el título
        'page_title': f'Editar Equipo: {equipo.nombre}'
    }
    # Reutilizamos el template de 'crear'
    return render(request, 'inventario/crear_maquinaria.html', context)