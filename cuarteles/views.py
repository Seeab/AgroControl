from django.shortcuts import render, get_object_or_404, redirect
from autenticacion.views import login_required, admin_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count
from django.utils import timezone
from .models import Cuartel , Hilera, SeguimientoCuartel, RegistroHilera
from .forms import CuartelForm, SeguimientoCuartelForm, RegistroHileraForm, HileraFormSet
from django.forms import inlineformset_factory 
from django.db import transaction

@login_required 
def lista_cuarteles(request):
    # (Sin cambios, esta vista está bien)
    cuarteles = Cuartel.objects.all().order_by('numero')
    tipo_riego = request.GET.get('tipo_riego')
    estado = request.GET.get('estado')
    if tipo_riego:
        cuarteles = cuarteles.filter(tipo_riego=tipo_riego)
    if estado:
        cuarteles = cuarteles.filter(estado_cultivo=estado)
    total_cuarteles = Cuartel.objects.count()
    cuarteles_activos = Cuartel.objects.filter(estado_cultivo='activo').count()
    context = {
        'cuarteles': cuarteles,
        'total_cuarteles': total_cuarteles,
        'cuarteles_activos': cuarteles_activos,
        'filtro_tipo_riego': tipo_riego,
        'filtro_estado': estado,
        'page_title': 'Gestión de Cuarteles'
    }
    return render(request, 'cuarteles/lista_cuarteles.html', context)


@login_required 
def detalle_cuartel(request, cuartel_id):
    # --- VISTA SIMPLIFICADA ---
    # (Se eliminó toda la lógica de formularios POST)
    cuartel = get_object_or_404(Cuartel.objects.prefetch_related('hileras'), id=cuartel_id)
    
    # Obtenemos los últimos 5 batches de seguimiento para mostrar el historial
    seguimientos_batch = cuartel.seguimientos_batch.all().order_by('-fecha_seguimiento')[:5]
    
    context = {
        'cuartel': cuartel,
        'hileras': cuartel.hileras.all(),
        'seguimientos_batch': seguimientos_batch,
        'page_title': f'Detalle Cuartel: {cuartel.nombre}'
    }
    return render(request, 'cuarteles/detalle_cuartel.html', context)

@admin_required
def crear_cuartel(request):
    # (Sin cambios, esta vista está bien)
    if request.method == 'POST':
        form = CuartelForm(request.POST)
        if form.is_valid():
            cuartel = form.save(commit=False)
            cuartel.creado_por_id = request.session.get('usuario_id')
            cuartel = form.save() 
            messages.success(request, f'Cuartel {cuartel.numero} y sus {cuartel.cantidad_hileras} hileras han sido creados.')
            messages.info(request, 'Ahora puede definir las plantas iniciales para cada hilera.')
            return redirect('cuarteles:editar_cuartel', cuartel_id=cuartel.id)
    else:
        form = CuartelForm()
    context = {'form': form, 'page_title': 'Crear Nuevo Cuartel'}
    return render(request, 'cuarteles/crear_cuartel.html', context)

@admin_required
def editar_cuartel(request, cuartel_id):
    cuartel = get_object_or_404(Cuartel, id=cuartel_id)
    
    # Creamos el formset de hileras para editar sus plantas iniciales
    formset_hileras = HileraFormSet(request.POST or None, instance=cuartel)
    
    if request.method == 'POST':
        form = CuartelForm(request.POST, instance=cuartel)
        
        if form.is_valid() and formset_hileras.is_valid():
            with transaction.atomic():
                # Guardamos el cuartel (y actualizamos cantidad de hileras si cambió)
                cuartel = form.save()
                
                # === CORRECCIÓN BUG 1 (SUPERVIVENCIA 0%) ===
                hileras = formset_hileras.save(commit=False)
                for hilera_form_instance in hileras:
                    # Al guardar las plantas iniciales, ASUMIMOS que todas están vivas.
                    hilera_form_instance.plantas_vivas_actuales = hilera_form_instance.plantas_totales_iniciales
                    hilera_form_instance.plantas_muertas_actuales = 0
                    hilera_form_instance.save()
                # ============================================

            messages.success(request, f'Cuartel {cuartel.numero} actualizado exitosamente.')
            return redirect('cuarteles:detalle_cuartel', cuartel_id=cuartel.id)
        else:
            messages.error(request, 'Por favor corrija los errores del formulario.')
    else:
        # Llenamos el 'initial' para el campo no-modelo (si no es POST)
        plantas_por_hilera = 0
        primera_hilera = cuartel.hileras.first()
        if primera_hilera:
            plantas_por_hilera = primera_hilera.plantas_totales_iniciales
        
        form = CuartelForm(instance=cuartel, initial={'plantas_iniciales_predeterminadas': plantas_por_hilera})
    
    context = {
        'form': form, 
        'formset_hileras': formset_hileras, # <-- Pasamos el formset al template
        'cuartel': cuartel,
        'page_title': f'Editar Cuartel: {cuartel.nombre}'
    }
    return render(request, 'cuarteles/editar_cuartel.html', context)

@admin_required
def eliminar_cuartel(request, cuartel_id):
    # (Sin cambios, esta vista está bien)
    cuartel = get_object_or_404(Cuartel, id=cuartel_id)
    if request.method == 'POST':
        numero = cuartel.numero
        cuartel.delete()
        messages.success(request, f'Cuartel {numero} eliminado exitosamente.')
        return redirect('cuarteles:lista_cuarteles')
    context = {'cuartel': cuartel, 'page_title': f'Eliminar Cuartel: {cuartel.nombre}'}
    return render(request, 'cuarteles/eliminar_cuartel.html', context)

@login_required
def registrar_seguimiento(request, cuartel_id):
    cuartel = get_object_or_404(Cuartel.objects.prefetch_related('hileras'), id=cuartel_id)
    hileras_del_cuartel = cuartel.hileras.all()
    numero_de_hileras = hileras_del_cuartel.count()

    # --- MODIFICACIÓN 3: Creamos la *clase* del formset dinámicamente ---
    # El 'extra' va aquí, en la fábrica, no en el constructor.
    RegistroHileraFormSet_Clase = inlineformset_factory(
        SeguimientoCuartel,
        RegistroHilera,
        form=RegistroHileraForm,
        fields=['hilera', 'plantas_vivas_registradas', 'plantas_muertas_registradas', 'observaciones_hilera'],
        extra=numero_de_hileras, # <-- Esta es la corrección
        can_delete=False
    )

    # Tu lógica 'initial' está perfecta
    initial_data_para_seguimiento = [
        {
            'hilera': hilera,
            'plantas_vivas_registradas': hilera.plantas_vivas_actuales,
            'plantas_muertas_registradas': hilera.plantas_muertas_actuales,
        } for hilera in hileras_del_cuartel
    ]

    if request.method == 'POST':
        form_seguimiento = SeguimientoCuartelForm(request.POST)
        
        # --- MODIFICACIÓN 4: Usamos la clase dinámica que creamos ---
        formset_registro_hileras = RegistroHileraFormSet_Clase(
            request.POST,
            instance=SeguimientoCuartel(), # Instancia vacía para 'create'
            queryset=RegistroHilera.objects.none()
        )
        
        if form_seguimiento.is_valid() and formset_registro_hileras.is_valid():
            try:
                with transaction.atomic():
                    seguimiento_batch = form_seguimiento.save(commit=False)
                    seguimiento_batch.cuartel = cuartel
                    seguimiento_batch.responsable_id = request.session.get('usuario_id')
                    seguimiento_batch.save()

                    registros = formset_registro_hileras.save(commit=False)
                    for registro in registros:
                        registro.seguimiento_batch = seguimiento_batch
                        registro.save() 
                        # La señal 'post_save' se dispara aquí

                    messages.success(request, 'Seguimiento por hileras registrado exitosamente.')
                    return redirect('cuarteles:detalle_cuartel', cuartel_id=cuartel.id)
            except Exception as e:
                messages.error(request, f'Error al guardar el seguimiento: {e}')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    
    else: # Método GET
        form_seguimiento = SeguimientoCuartelForm(initial={'fecha_seguimiento': timezone.now().date()})
        
        # --- MODIFICACIÓN 5: Instanciamos la clase dinámica para el GET ---
        formset_registro_hileras = RegistroHileraFormSet_Clase(
            instance=SeguimientoCuartel(),
            queryset=RegistroHilera.objects.none(),
            initial=initial_data_para_seguimiento # <-- 'initial' sí va en el constructor
        )
    
    context = {
        'cuartel': cuartel,
        'form_seguimiento': form_seguimiento,
        'formset_registro_hileras': formset_registro_hileras,
        'page_title': f'Registrar Seguimiento: {cuartel.nombre}'
    }
    return render(request, 'cuarteles/registrar_seguimiento.html', context)

@login_required 
def dashboard_cuarteles(request):
    # (Toda tu lógica de dashboard está bien)
    total_cuarteles = Cuartel.objects.count()
    cuarteles_activos = Cuartel.objects.filter(estado_cultivo='activo').count()
    riego_stats = Cuartel.objects.values('tipo_riego').annotate(total=Count('id'))
    
    baja_supervivencia = []
    # ¡ACTUALIZADO! Usamos el nuevo método get_porcentaje_supervivencia
    for cuartel in Cuartel.objects.all():
        if cuartel.get_porcentaje_supervivencia() < 80:
            baja_supervivencia.append(cuartel)
    
    context = {
        'total_cuarteles': total_cuarteles,
        'cuarteles_activos': cuarteles_activos,
        'riego_stats': riego_stats,
        'baja_supervivencia': baja_supervivencia,
        'page_title': 'Dashboard de Cuarteles' 
    }
    return render(request, 'cuarteles/dashboard.html', context)

@login_required 
def api_estadisticas_cuarteles(request):
    data = {
        'total': Cuartel.objects.count(),
        'activos': Cuartel.objects.filter(estado_cultivo='activo').count(),
        'por_tipo_riego': list(Cuartel.objects.values('tipo_riego').annotate(total=Count('id'))),
    }
    return JsonResponse(data)


# (No es necesario cambiar 'eliminar_cuartel', 'dashboard_cuarteles' o 'api_estadisticas_cuarteles'
# ya que 'eliminar' funciona en cascada y los otros ya fueron adaptados a los nuevos métodos)