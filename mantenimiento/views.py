from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST

from .models import Mantenimiento
from autenticacion.models import Usuario 
from inventario.models import EquipoAgricola
from .forms import MantenimientoForm

# --- Decorador de Login ---
def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login') 
        return view_func(request, *args, **kwargs)
    return wrapper

# ===============================================================
#  VISTA PRINCIPAL: dashboard_mantencion
# ===============================================================
@login_required
def dashboard_mantencion(request):
    """
    Dashboard principal con filtros para TIPO DE EQUIPO y Estado.
    """
    
    tipo_equipo_filtro = request.GET.get('tipo_equipo', '')
    estado_filtro = request.GET.get('estado', '')
    
    mantenimientos_list = Mantenimiento.objects.select_related(
        'maquinaria', 'operario_responsable'
    ).order_by('-fecha_mantenimiento')
    
    if tipo_equipo_filtro:
        mantenimientos_list = mantenimientos_list.filter(maquinaria__tipo=tipo_equipo_filtro)
    if estado_filtro:
        mantenimientos_list = mantenimientos_list.filter(estado=estado_filtro)
    
    total_mantenciones = mantenimientos_list.count()
    mantenciones_programadas = mantenimientos_list.filter(estado='PROGRAMADO').count()
    mantenciones_realizadas = mantenimientos_list.filter(estado='REALIZADO').count()
    
    context = {
        'total_mantenciones': total_mantenciones,
        'mantenciones_programadas': mantenciones_programadas,
        'mantenciones_realizadas': mantenciones_realizadas,
        'mantenimientos_list': mantenimientos_list, 
        'tipo_equipo_choices': EquipoAgricola.TIPO_EQUIPO_CHOICES,
        'tipo_equipo_filtro': tipo_equipo_filtro,
        'estado_filtro': estado_filtro, 
        'titulo': 'Dashboard - Mantenimiento',
        'usuario_nombre': request.session.get('usuario_nombre', 'Usuario')
    }
    return render(request, 'mantenimiento/dashboard_mantencion.html', context)


# ===============================================================
#  VISTAS CRUD (CON SEGURIDAD Y STOCK)
# ===============================================================

@login_required
def crear_mantenimiento(request):
    """
    Crea una nueva mantención.
    Resta la 'cantidad' del 'stock_actual' del equipo.
    """
    
    usuario_id = request.session.get('usuario_id')
    # Obtenemos el usuario completo para pasarlo al form
    usuario_logueado = get_object_or_404(Usuario, pk=usuario_id)
    
    if request.method == 'POST':
        # --- CAMBIO: Pasamos 'usuario_actual' al form ---
        form = MantenimientoForm(request.POST, usuario_actual=usuario_logueado)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    mantenimiento = form.save(commit=False)
                    mantenimiento.creado_por = usuario_logueado 
                    mantenimiento.estado = 'PROGRAMADO'
                    
                    # --- LÓGICA DE STOCK ---
                    equipo = mantenimiento.maquinaria
                    cantidad = mantenimiento.cantidad
                    
                    # 1. Validar stock
                    if cantidad > equipo.stock_actual:
                        raise ValidationError(f'Stock insuficiente para "{equipo.nombre}". Stock operativo: {equipo.stock_actual}, se solicitan: {cantidad}.')
                    
                    # 2. Restar stock
                    equipo.stock_actual -= cantidad
                    
                    # 3. Cambiar estado si stock llega a 0
                    if equipo.stock_actual == 0:
                        equipo.estado = 'mantenimiento'
                    
                    equipo.save(update_fields=['stock_actual', 'estado'])
                    mantenimiento.save() 
                
                messages.success(request, f'Mantención para {cantidad}x "{equipo.nombre}" programada.')
                return redirect('mantenimiento:dashboard')
            
            except (ValidationError, Exception) as e:
                form.add_error(None, f"Error al guardar: {str(e)}")
                messages.error(request, 'No se pudo crear la mantención.')
        else: 
            messages.error(request, 'Por favor corrige los errores del formulario.')

    else: # request.method == 'GET'
        # --- CAMBIO: Pasamos 'usuario_actual' al form ---
        form = MantenimientoForm(usuario_actual=usuario_logueado)
    
    context = {
        'form': form,
        'titulo': 'Programar Mantenimiento',
        'boton_texto': 'Guardar'
    }
    return render(request, 'mantenimiento/mantenimiento_form.html', context)


@login_required
def editar_mantenimiento(request, pk):
    """
    Edita una mantención 'PROGRAMADA'.
    Maneja cambios de stock y seguridad.
    """
    mantenimiento = get_object_or_404(Mantenimiento.objects.select_related('maquinaria'), pk=pk)
    
    # --- SEGURIDAD DE PROPIEDAD (Igual que Riego) ---
    usuario_id = request.session.get('usuario_id')
    es_admin = request.session.get('es_administrador')
    
    # Si NO es admin Y (tiene responsable asignado Y no es el usuario actual)
    if not es_admin and (mantenimiento.operario_responsable and mantenimiento.operario_responsable.id != usuario_id):
        messages.error(request, 'No tienes permiso para editar mantenciones de otros encargados.')
        return redirect('mantenimiento:dashboard')
    # ------------------------------
    
    if mantenimiento.estado != 'PROGRAMADO':
        messages.error(request, f'Esta mantención no se puede editar (estado: {mantenimiento.get_estado_display()}).')
        return redirect('mantenimiento:dashboard')

    usuario_logueado = get_object_or_404(Usuario, pk=usuario_id)
    
    # Guardamos valores originales para reversión de stock
    equipo_original = mantenimiento.maquinaria
    cantidad_original = mantenimiento.cantidad

    if request.method == 'POST':
        # --- CAMBIO: Pasamos 'usuario_actual' al form ---
        form = MantenimientoForm(request.POST, instance=mantenimiento, usuario_actual=usuario_logueado)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Devolver el stock original
                    equipo_original.stock_actual += cantidad_original
                    if equipo_original.stock_actual > 0:
                        equipo_original.estado = 'operativo'
                    equipo_original.save(update_fields=['stock_actual', 'estado'])

                    # 2. Procesar nuevos datos
                    mantenimiento_editado = form.save(commit=False)
                    equipo_nuevo = mantenimiento_editado.maquinaria
                    cantidad_nueva = mantenimiento_editado.cantidad
                    
                    # Refrescar si es el mismo equipo
                    if equipo_nuevo.id == equipo_original.id:
                        equipo_nuevo.refresh_from_db() 

                    if cantidad_nueva > equipo_nuevo.stock_actual:
                        raise ValidationError(f'Stock insuficiente para "{equipo_nuevo.nombre}".')

                    equipo_nuevo.stock_actual -= cantidad_nueva
                    if equipo_nuevo.stock_actual == 0:
                        equipo_nuevo.estado = 'mantenimiento'
                    equipo_nuevo.save(update_fields=['stock_actual', 'estado'])
                    
                    mantenimiento_editado.save()

                messages.success(request, 'Mantención actualizada exitosamente.')
                return redirect('mantenimiento:dashboard')
                
            except (ValidationError, Exception) as e:
                form.add_error(None, f"Error al actualizar: {str(e)}")
                messages.error(request, 'No se pudo actualizar la mantención.')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        # --- CAMBIO: Pasamos 'usuario_actual' al form ---
        form = MantenimientoForm(instance=mantenimiento, usuario_actual=usuario_logueado)
    
    context = {
        'form': form,
        'mantenimiento': mantenimiento,
        'titulo': 'Editar Mantenimiento',
        'boton_texto': 'Actualizar'
    }
    return render(request, 'mantenimiento/mantenimiento_form.html', context)


@login_required
def detalle_mantenimiento(request, pk):
    mantenimiento = get_object_or_404(
        Mantenimiento.objects.select_related(
            'maquinaria', 'operario_responsable', 'creado_por'
        ), 
        pk=pk
    )
    context = {
        'mantenimiento': mantenimiento,
        'titulo': f'Detalle Mantención #{mantenimiento.id}'
    }
    return render(request, 'mantenimiento/detalle_mantenimiento.html', context)


# ===============================================================
#  VISTAS DE ACCIÓN (CON SEGURIDAD Y STOCK)
# ===============================================================

@login_required
@require_POST 
def finalizar_mantenimiento(request, pk):
    """
    Cambia el estado a 'REALIZADO' y devuelve el stock.
    """
    mantenimiento = get_object_or_404(Mantenimiento.objects.select_related('maquinaria'), pk=pk)
    
    # --- SEGURIDAD DE PROPIEDAD ---
    usuario_id = request.session.get('usuario_id')
    es_admin = request.session.get('es_administrador')
    
    if not es_admin and (mantenimiento.operario_responsable and mantenimiento.operario_responsable.id != usuario_id):
        messages.error(request, 'No tienes permiso para finalizar mantenciones de otros.')
        return redirect('mantenimiento:dashboard')
    # ------------------------------

    if mantenimiento.estado != 'PROGRAMADO':
        messages.warning(request, f'La Tarea ID {mantenimiento.id} no se puede finalizar.')
        return redirect('mantenimiento:dashboard')

    try:
        with transaction.atomic():
            mantenimiento.estado = 'REALIZADO'
            mantenimiento.save(update_fields=['estado'])
            
            # Devolver stock
            equipo = mantenimiento.maquinaria
            equipo.stock_actual += mantenimiento.cantidad
            equipo.estado = 'operativo'
            equipo.save(update_fields=['stock_actual', 'estado'])
        
        messages.success(request, f'Mantención ID {mantenimiento.id} finalizada. Stock devuelto.')
    
    except Exception as e:
        messages.error(request, f'Error al finalizar Tarea ID {mantenimiento.id}: {str(e)}')
    
    return redirect('mantenimiento:dashboard')


@login_required
@require_POST 
def cancelar_mantenimiento(request, pk):
    """
    Cambia el estado a 'CANCELADO' y devuelve el stock.
    """
    mantenimiento = get_object_or_404(Mantenimiento.objects.select_related('maquinaria'), pk=pk)
    
    # --- SEGURIDAD DE PROPIEDAD ---
    usuario_id = request.session.get('usuario_id')
    es_admin = request.session.get('es_administrador')
    
    if not es_admin and (mantenimiento.operario_responsable and mantenimiento.operario_responsable.id != usuario_id):
        messages.error(request, 'No tienes permiso para cancelar mantenciones de otros.')
        return redirect('mantenimiento:dashboard')
    # ------------------------------
    
    if mantenimiento.estado != 'PROGRAMADO':
        messages.warning(f'Esta tarea ya no se puede cancelar.', 'warning')
        return redirect('mantenimiento:dashboard')

    try:
        with transaction.atomic():
            mantenimiento.estado = 'CANCELADO'
            mantenimiento.save(update_fields=['estado'])

            # Devolver stock
            equipo = mantenimiento.maquinaria
            equipo.stock_actual += mantenimiento.cantidad
            equipo.estado = 'operativo'
            equipo.save(update_fields=['stock_actual', 'estado'])
            
        messages.success(request, f'Mantención ID {mantenimiento.id} cancelada. Stock devuelto.')
            
        return redirect('mantenimiento:dashboard')
    
    except Exception as e:
        messages.error(request, f'Error al cancelar: {str(e)}')
        return redirect('mantenimiento:dashboard')