from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Avg, F, Value
from django.db.models.fields import DecimalField
from django.db.models.functions import Coalesce
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from .models import Usuario, Operario, Rol
from .forms import UsuarioForm, OperarioForm, LoginForm, RecuperarPasswordForm, CambiarPasswordForm
from django.db.models import Sum, Avg, F, Value, ExpressionWrapper, FloatField

# Importamos los modelos de TODAS las apps
from riego.models import ControlRiego
from aplicaciones.models import AplicacionFitosanitaria
from mantenimiento.models import Mantenimiento
from inventario.models import Producto
from cuarteles.models import Cuartel, Hilera

# ==================== AUTENTICACIÓN ====================

def login_view(request):
    """Vista de inicio de sesión"""
    
    if request.session.get('usuario_id'):
        if request.session.get('es_administrador'):
            return redirect('dashboard') 
        rol = request.session.get('usuario_rol', 'Sin rol')
        mapa_redirecciones = {
            'administrador': 'dashboard',
            'aplicador': 'aplicaciones:lista_aplicaciones',
            'regador': 'riego:dashboard', 
            'encargado de mantencion': 'mantenimiento:dashboard',
        }
        destino = mapa_redirecciones.get(rol, 'dashboard') 
        try:
            return redirect(destino)
        except Exception:
            return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data['usuario']
            usuario.actualizar_ultimo_acceso()
            
            request.session['usuario_id'] = usuario.id
            request.session['usuario_nombre'] = usuario.get_full_name()
            request.session['usuario_rol'] = usuario.rol.nombre if usuario.rol else 'Sin rol'
            request.session['es_administrador'] = usuario.es_administrador
            
            messages.success(request, f'Bienvenido, {usuario.get_full_name()}')
            
            return redirigir_por_rol(usuario)
    else:
        form = LoginForm()
    
    return render(request, 'autenticacion/login.html', {'form': form})

def redirigir_por_rol(usuario):
    """Redirige según el rol usando nombres exactos de la BD"""
    if usuario.es_administrador:
        return redirect('dashboard')
    
    if not usuario.rol:
        return redirect('dashboard')
    
    rol_nombre = usuario.rol.nombre.strip()
    
    mapa_redirecciones = {
        'administrador': 'dashboard',
        'aplicador': 'aplicaciones:lista_aplicaciones',
        'regador': 'riego:dashboard', 
        'encargado de mantencion': 'mantenimiento:dashboard',
    }
    
    destino = mapa_redirecciones.get(rol_nombre, 'dashboard')
    
    try:
        return redirect(destino)
    except Exception as e:
        fallbacks = {
            'aplicador': 'aplicaciones_proximamente',
            'regador': 'riego_proximamente', 
            'encargado de mantencion': 'mantencion_proximamente',
        }
        fallback = fallbacks.get(rol_nombre, 'dashboard')
        return redirect(fallback)
    
def logout_view(request):
    """Vista de cierre de sesión"""
    request.session.flush()
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('login')



# ==================== DECORADORES ====================

def login_required(view_func):
    """Decorador para requerir autenticación"""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    """Decorador para requerir permisos de administrador"""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login')
        if not request.session.get('es_administrador'):
            messages.error(request, 'No tiene permisos para acceder a esta página.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def perfil_usuario(request):
    """
    Muestra el perfil del usuario logueado.
    """
    usuario = get_object_or_404(Usuario, pk=request.session.get('usuario_id'))
    
    # Intentamos obtener el operario asociado (si existe)
    operario = None
    try:
        operario = usuario.operario
    except Operario.DoesNotExist:
        pass

    context = {
        'usuario': usuario,
        'operario': operario, # Pasamos los datos extra si es operario
        'titulo': 'Mi Perfil'
    }
    return render(request, 'autenticacion/perfil.html', context)
# ==================== DASHBOARD (COMBINADO Y ACTUALIZADO) ====================

@admin_required 
def dashboard(request): # O como se llame tu vista de dashboard principal
    """
    Vista principal del dashboard (COMBINADA).
    Muestra estadísticas de usuarios, métricas de apps, y alertas.
    """
    
    # --- 1. DATOS ORIGINALES DE TU DASHBOARD (Usuarios/Operarios) ---
    total_usuarios = Usuario.objects.filter(esta_activo=True).count()
    total_operarios = Operario.objects.filter(esta_activo=True).count()
    usuarios_recientes = Usuario.objects.order_by('-fecha_registro')[:5] 

    # --- 2. DATOS NUEVOS (Métricas, Alertas, Actividades) ---
    
    hoy = timezone.now().date()
    ahora = timezone.now()
    treinta_dias_despues = hoy + timedelta(days=30)
    
    # --- RF029: Actividades en Tiempo Real ---
    actividades_riego = ControlRiego.objects.filter(fecha=hoy).order_by('-fecha')
    actividades_apps = AplicacionFitosanitaria.objects.filter(fecha_aplicacion__date=hoy).order_by('-fecha_aplicacion')
    actividades_mant = Mantenimiento.objects.filter(fecha_mantenimiento__date=hoy).order_by('-fecha_mantenimiento')
    
    # --- RF031: Métricas de Riego del Día (Realizados) ---
    riegos_realizados_hoy = ControlRiego.objects.filter(fecha=hoy, estado='REALIZADO')
    
    volumen_total_dia = riegos_realizados_hoy.aggregate(total=Sum('volumen_total_m3'))['total'] or 0
    caudal_promedio_dia = riegos_realizados_hoy.aggregate(avg=Avg('caudal_m3h'))['avg'] or 0.0
    
    # --- RF031 (extendido): Métricas de Apps y Mantención ---
    apps_realizadas_hoy = AplicacionFitosanitaria.objects.filter(fecha_aplicacion__date=hoy, estado='realizada').count()
    mant_realizadas_hoy = Mantenimiento.objects.filter(fecha_mantenimiento__date=hoy, estado='REALIZADO').count()

    
    # --- RF032: Alertas y Notificaciones Prioritarias ---
    
    # Alerta 1: Stock Bajo (RF028)
    alertas_stock = Producto.objects.filter(esta_activo=True, stock_actual__lt=F('stock_minimo'))
    
    # Alerta 2: Tareas de Mantenimiento Atrasadas
    alertas_mantencion = Mantenimiento.objects.filter(
        estado='PROGRAMADO', 
        fecha_mantenimiento__lt=ahora
    ).order_by('fecha_mantenimiento')

    # Alerta 3: Riegos Atrasados
    alertas_riego = ControlRiego.objects.filter(
        estado='PROGRAMADO',
        fecha__lt=hoy # Riegos programados para antes de hoy
    ).order_by('fecha')
    
    # Alerta 4: Aplicaciones Atrasadas
    alertas_aplicaciones = AplicacionFitosanitaria.objects.filter(
        estado='programada',
        fecha_aplicacion__lt=ahora
    ).order_by('fecha_aplicacion')

    # Alerta 5: Certificaciones por Vencer (RF008)
    alertas_certificaciones = Operario.objects.filter(
        esta_activo=True,
        fecha_vencimiento_certificacion__range=[hoy, treinta_dias_despues]
    ).order_by('fecha_vencimiento_certificacion')
    
    # Alerta 6: Mortalidad de Plantas (RF013) - ¡CORREGIDO!
    
    # 1. Anotamos cada cuartel con la suma de sus hileras
    cuarteles_con_conteo = Cuartel.objects.annotate(
        # --- ¡CORRECCIÓN AQUÍ! ---
        # Forzamos la SUMA a ser un DecimalField
        total_muertas=Coalesce(
            Sum('hileras__plantas_muertas_actuales', output_field=DecimalField()), 
            Value(0, output_field=DecimalField())
        ),
        # --- ¡Y CORRECCIÓN AQUÍ! ---
        total_iniciales=Coalesce(
            Sum('hileras__plantas_totales_iniciales', output_field=DecimalField()), 
            Value(0, output_field=DecimalField())
        )
    )

    # 2. Filtramos para evitar división por cero
    cuarteles_con_conteo = cuarteles_con_conteo.filter(total_iniciales__gt=0)

    # 3. Calculamos el porcentaje
    alertas_mortalidad = cuarteles_con_conteo.annotate(
        porcentaje_mortalidad=ExpressionWrapper(
            (F('total_muertas') * 100.0 / F('total_iniciales')),
            output_field=FloatField() # Le decimos a Django que el resultado es un Float
        )
    ).filter(
        porcentaje_mortalidad__gt=5 # <-- UMBRAL DE ALERTA (5%)
    ).order_by('-porcentaje_mortalidad')
        
    # --- 3. CONSTRUIR EL CONTEXTO FINAL ---
    context = {
        'titulo': 'Dashboard Administrativo',
        'usuario_nombre': request.session.get('usuario_nombre', 'Usuario'),
        
        'total_usuarios': total_usuarios,
        'total_operarios': total_operarios,
        'usuarios_recientes': usuarios_recientes,

        'actividades_riego': actividades_riego,
        'actividades_apps': actividades_apps,
        'actividades_mant': actividades_mant,
        
        'volumen_total_dia': volumen_total_dia,
        'caudal_promedio_dia': caudal_promedio_dia,
        'apps_realizadas_hoy': apps_realizadas_hoy,
        'mant_realizadas_hoy': mant_realizadas_hoy,
        
        'alertas_stock': alertas_stock,
        'alertas_mantencion': alertas_mantencion,
        'alertas_riego': alertas_riego,
        'alertas_aplicaciones': alertas_aplicaciones,
        'alertas_certificaciones': alertas_certificaciones,
        'alertas_mortalidad': alertas_mortalidad,
    }
    
    return render(request, 'autenticacion/dashboard.html', context)


# ==================== GESTIÓN DE USUARIOS ====================
# (Todas tus vistas de 'usuario_lista', 'usuario_crear', etc. van aquí sin cambios)

@admin_required
def usuario_lista(request):
    query = request.GET.get('q', '')
    usuarios = Usuario.objects.select_related('rol').all()
    if query:
        usuarios = usuarios.filter(
            Q(nombre_usuario__icontains=query) |
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(correo_electronico__icontains=query)
        )
    usuarios = usuarios.order_by('-fecha_registro')
    paginator = Paginator(usuarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = { 'page_obj': page_obj, 'query': query, }
    return render(request, 'autenticacion/usuario_lista.html', context)

@admin_required
def usuario_crear(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST, is_new=True)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.nombre_usuario}" creado correctamente.')
            return redirect('usuario_lista')
    else:
        form = UsuarioForm(is_new=True)
    context = { 'form': form, 'titulo': 'Crear Usuario', 'boton_texto': 'Crear Usuario' }
    return render(request, 'autenticacion/usuario_form.html', context)

@admin_required
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario, is_new=False)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.nombre_usuario}" actualizado correctamente.')
            return redirect('usuario_lista')
    else:
        form = UsuarioForm(instance=usuario, is_new=False)
    context = { 'form': form, 'usuario': usuario, 'titulo': 'Editar Usuario', 'boton_texto': 'Guardar Cambios' }
    return render(request, 'autenticacion/usuario_form.html', context)

@admin_required
def usuario_eliminar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.esta_activo = False
        usuario.save()
        messages.success(request, f'Usuario "{usuario.nombre_usuario}" desactivado correctamente.')
        return redirect('usuario_lista')
    context = {'usuario': usuario}
    return render(request, 'autenticacion/usuario_confirmar_eliminar.html', context)


# ==================== GESTIÓN DE OPERARIOS ====================

@admin_required
def operario_lista(request):
    query = request.GET.get('q', '')
    operarios = Operario.objects.select_related('usuario').all()
    if query:
        operarios = operarios.filter(
            Q(nombre_completo__icontains=query) |
            Q(cargo__icontains=query) |
            Q(rut__icontains=query)
        )
    operarios = operarios.order_by('-creado_en')
    paginator = Paginator(operarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    operarios_por_vencer = Operario.objects.filter(
        fecha_vencimiento_certificacion__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento_certificacion__gte=timezone.now().date(),
        esta_activo=True
    ).count()
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'operarios_por_vencer': operarios_por_vencer,
    }
    return render(request, 'autenticacion/operario_lista.html', context)

@admin_required
def operario_crear(request):
    if request.method == 'POST':
        form = OperarioForm(request.POST, request.FILES)
        if form.is_valid():
            operario = form.save(commit=False)
            usuario_id = request.POST.get('usuario_id')
            if usuario_id:
                try:
                    usuario = Usuario.objects.get(id=usuario_id)
                    operario.usuario = usuario
                except Usuario.DoesNotExist:
                    pass
            operario.save()
            messages.success(request, f'Operario "{operario.nombre_completo}" creado correctamente.')
            return redirect('operario_lista')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = OperarioForm()
    
    usuarios_disponibles = Usuario.objects.filter(
        esta_activo=True
    ).exclude(
        operario__isnull=False
    )
    
    context = {
        'form': form,
        'usuarios_disponibles': usuarios_disponibles,
        'titulo': 'Crear Operario',
        'boton_texto': 'Crear Operario'
    }
    return render(request, 'autenticacion/operario_form.html', context)

@admin_required
def operario_editar(request, pk):
    operario = get_object_or_404(Operario, pk=pk)
    if request.method == 'POST':
        form = OperarioForm(request.POST, request.FILES, instance=operario)
        if form.is_valid():
            operario = form.save()
            messages.success(request, f'Operario "{operario.nombre_completo}" actualizado correctamente.')
            return redirect('operario_lista')
    else:
        form = OperarioForm(instance=operario)
    context = { 'form': form, 'operario': operario, 'titulo': 'Editar Operario', 'boton_texto': 'Guardar Cambios' }
    return render(request, 'autenticacion/operario_form.html', context)

@admin_required
def operario_eliminar(request, pk):
    operario = get_object_or_404(Operario, pk=pk)
    if request.method == 'POST':
        if operario.certificacion_documento:
            operario.certificacion_documento.delete(save=False)
        operario.esta_activo = False
        operario.save()
        messages.success(request, f'Operario "{operario.nombre_completo}" desactivado correctamente.')
        return redirect('operario_lista')
    context = {'operario': operario}
    return render(request, 'autenticacion/operario_confirmar_eliminar.html', context)

# ==================== RECUPERACIÓN DE CONTRASEÑA ====================

def recuperar_password(request):
    if request.method == 'POST':
        form = RecuperarPasswordForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo_electronico']
            usuario = Usuario.objects.get(correo_electronico=correo)
            token = get_random_string(64)
            request.session[f'reset_token_{token}'] = {
                'usuario_id': usuario.id,
                'expira': (timezone.now() + timedelta(hours=1)).isoformat()
            }
            reset_link = request.build_absolute_uri(f'/password/reset/{token}/')
            try:
                send_mail(
                    'Recuperación de Contraseña - AgroControl',
                    f'Hola {usuario.get_full_name()},\n\n'
                    f'Has solicitado recuperar tu contraseña.\n\n'
                    f'Haz clic en el siguiente enlace para crear una nueva contraseña:\n'
                    f'{reset_link}\n\n'
                    f'Este enlace expirará en 1 hora.\n\n'
                    f'Si no solicitaste este cambio, ignora este mensaje.\n\n'
                    f'Saludos,\nEquipo AgroControl',
                    settings.DEFAULT_FROM_EMAIL,
                    [correo],
                    fail_silently=False,
                )
                messages.success(request, 'Se ha enviado un correo con instrucciones para recuperar tu contraseña.')
            except Exception as e:
                if settings.DEBUG:
                    messages.warning(request, f'Email no configurado. Link de recuperación: {reset_link}')
                else:
                    messages.error(request, 'Error al enviar el correo. Intenta nuevamente.')
            return redirect('login')
    else:
        form = RecuperarPasswordForm()
    return render(request, 'autenticacion/recuperar_password.html', {'form': form})


def reset_password(request, token):
    token_data = request.session.get(f'reset_token_{token}')
    if not token_data:
        messages.error(request, 'El enlace de recuperación no es válido o ha expirado.')
        return redirect('login')
    
    expira = timezone.datetime.fromisoformat(token_data['expira'])
    if timezone.now() > expira:
        del request.session[f'reset_token_{token}']
        messages.error(request, 'El enlace de recuperación ha expirado.')
        return redirect('recuperar_password')
    
    usuario = get_object_or_404(Usuario, id=token_data['usuario_id'])
    
    if request.method == 'POST':
        form = CambiarPasswordForm(request.POST)
        if form.is_valid():
            usuario.set_password(form.cleaned_data['password'])
            usuario.save()
            del request.session[f'reset_token_{token}']
            messages.success(request, 'Tu contraseña ha sido actualizada correctamente. Ahora puedes iniciar sesión.')
            return redirect('login')
    else:
        form = CambiarPasswordForm()
    context = { 'form': form, 'usuario': usuario }
    return render(request, 'autenticacion/reset_password.html', context)