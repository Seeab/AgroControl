from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import models
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from .models import Producto, MovimientoInventario
from .forms import ProductoForm, MovimientoInventarioForm

@login_required
def lista_productos(request):
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

@login_required
@permission_required('inventario.add_producto', raise_exception=True)
def crear_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.creado_por = request.user
            producto.save()
            messages.success(request, f'Producto {producto.nombre} creado exitosamente.')
            return redirect('inventario:lista_productos')
    else:
        form = ProductoForm()
    
    context = {'form': form}
    return render(request, 'inventario/crear_producto.html', context)

@login_required
def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    context = {'producto': producto}
    return render(request, 'inventario/detalle_producto.html', context)

@login_required
@permission_required('inventario.change_producto', raise_exception=True)
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto {producto.nombre} actualizado exitosamente.')
            return redirect('inventario:detalle_producto', producto_id=producto.id)
    else:
        form = ProductoForm(instance=producto)
    
    context = {'form': form, 'producto': producto}
    return render(request, 'inventario/crear_producto.html', context)

@login_required
@permission_required('inventario.add_movimientoinventario', raise_exception=True)
def crear_movimiento(request, producto_id=None):
    producto = None
    if producto_id:
        producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        form = MovimientoInventarioForm(request.POST)
        
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.realizado_por = request.user
            
            # ¡ELIMINADO! Ya no calculamos stocks aquí.
            # El método save() del modelo se encargará de todo.
            # movimiento.stock_anterior = ...
            # movimiento.stock_posterior = ...
            
            try:
                movimiento.save() # <-- Esto ahora llama al save() que arreglamos
                messages.success(request, 'Movimiento registrado exitosamente.')
                return redirect('inventario:lista_productos')
            
            except ValidationError as e:
                # Si el save() falla (ej: stock insuficiente), lo capturamos
                messages.error(request, f'Error al guardar: {e.args[0]}')
                # (Podrías ser más elegante y pasarlo al form.add_error)
        
        # (else: el form no es válido, se re-renderiza con errores)

    else:
        initial = {}
        if producto:
            initial['producto'] = producto
        form = MovimientoInventarioForm(initial=initial)
    
    context = {
        'form': form,
        'producto': producto
    }
    return render(request, 'inventario/crear_movimiento.html', context)

@login_required
def historial_movimientos(request):
    movimientos = MovimientoInventario.objects.all().select_related('producto', 'realizado_por').order_by('-fecha_movimiento')
    
    # Filtros
    producto_id = request.GET.get('producto')
    tipo_movimiento = request.GET.get('tipo_movimiento')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if producto_id:
        movimientos = movimientos.filter(producto_id=producto_id)
    if tipo_movimiento:
        movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)
    if fecha_desde:
        movimientos = movimientos.filter(fecha_movimiento__gte=fecha_desde)
    if fecha_hasta:
        movimientos = movimientos.filter(fecha_movimiento__lte=fecha_hasta)
    
    # Paginación
    paginator = Paginator(movimientos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
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
    }
    return render(request, 'inventario/historial_movimientos.html', context)