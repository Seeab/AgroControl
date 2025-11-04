from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from .models import Usuario, Operario, Rol
from django.http import JsonResponse
from .forms import UsuarioForm, OperarioForm, LoginForm, RecuperarPasswordForm, CambiarPasswordForm

# ==================== AUTENTICACIÓN ====================

def login_view(request):
    """Vista de inicio de sesión"""
    if request.session.get('usuario_id'):
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
            
            # Redirigir según el rol
            if usuario.es_administrador or (usuario.rol and usuario.rol.nombre == 'administrador'):
                return redirect('dashboard')
            elif usuario.rol and usuario.rol.nombre == 'aplicador':
                return redirect('aplicaciones_proximamente')
            elif usuario.rol and usuario.rol.nombre == 'regador':
                return redirect('riego_proximamente')
            elif usuario.rol and usuario.rol.nombre == 'encargado':
                return redirect('mantencion_proximamente')
            else:
                return redirect('dashboard')
    else:
        form = LoginForm()
    
    return render(request, 'autenticacion/login.html', {'form': form})


def logout_view(request):
    """Vista de cierre de sesión"""
    request.session.flush()
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('login')


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


# ==================== DASHBOARD ====================

@login_required
def dashboard(request):
    """Vista principal del dashboard"""
    context = {
        'total_usuarios': Usuario.objects.filter(esta_activo=True).count(),
        'total_operarios': Operario.objects.filter(esta_activo=True).count(),
        'usuarios_recientes': Usuario.objects.order_by('-fecha_registro')[:5],
    }
    return render(request, 'autenticacion/dashboard.html', context)

@login_required
def dashboard_alertas(request):
    """Endpoint para AJAX - alertas para el dashboard (RF008)"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from datetime import timedelta
        
        operarios_por_vencer = Operario.objects.filter(
            fecha_vencimiento_certificacion__lte=timezone.now().date() + timedelta(days=30),
            fecha_vencimiento_certificacion__gte=timezone.now().date(),
            esta_activo=True
        ).count()
        
        operarios_vencidos = Operario.objects.filter(
            fecha_vencimiento_certificacion__lt=timezone.now().date(),
            esta_activo=True
        ).count()
        
        data = {
            'por_vencer': operarios_por_vencer,
            'vencidos': operarios_vencidos,
            'total_alertas': operarios_por_vencer + operarios_vencidos
        }
        return JsonResponse(data)
    
    # Si no es AJAX, redirigir al dashboard
    return redirect('dashboard')

# ==================== GESTIÓN DE USUARIOS ====================

@admin_required
def usuario_lista(request):
    """Lista de usuarios con búsqueda y paginación"""
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
    
    context = {
        'page_obj': page_obj,
        'query': query,
    }
    return render(request, 'autenticacion/usuario_lista.html', context)


@admin_required
def usuario_crear(request):
    """Crear nuevo usuario"""
    if request.method == 'POST':
        form = UsuarioForm(request.POST, is_new=True)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.nombre_usuario}" creado correctamente.')
            return redirect('usuario_lista')
    else:
        form = UsuarioForm(is_new=True)
    
    context = {
        'form': form,
        'titulo': 'Crear Usuario',
        'boton_texto': 'Crear Usuario'
    }
    return render(request, 'autenticacion/usuario_form.html', context)


@admin_required
def usuario_editar(request, pk):
    """Editar usuario existente"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario, is_new=False)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.nombre_usuario}" actualizado correctamente.')
            return redirect('usuario_lista')
    else:
        form = UsuarioForm(instance=usuario, is_new=False)
    
    context = {
        'form': form,
        'usuario': usuario,
        'titulo': 'Editar Usuario',
        'boton_texto': 'Guardar Cambios'
    }
    return render(request, 'autenticacion/usuario_form.html', context)


@admin_required
def usuario_eliminar(request, pk):
    """Eliminar (desactivar) usuario"""
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
    """Lista de operarios"""
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
    
    # ✅ NUEVO: Contar operarios con certificaciones por vencer (RF008)
    operarios_por_vencer = Operario.objects.filter(
        fecha_vencimiento_certificacion__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento_certificacion__gte=timezone.now().date(),
        esta_activo=True
    ).count()
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'operarios_por_vencer': operarios_por_vencer,  # ✅ Para mostrar en template
    }
    return render(request, 'autenticacion/operario_lista.html', context)


@admin_required
def operario_crear(request):
    """Crear nuevo operario"""
    if request.method == 'POST':
        # ✅ CORREGIDO: Agregar request.FILES para subir documentos (RF009)
        form = OperarioForm(request.POST, request.FILES)
        if form.is_valid():
            operario = form.save(commit=False)
            
            # Verificar si tiene usuario asociado
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
    
    # Obtener usuarios disponibles (que no sean operarios)
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
    """Editar operario existente"""
    operario = get_object_or_404(Operario, pk=pk)
    
    if request.method == 'POST':
        # ✅ CORREGIDO: Agregar request.FILES para subir documentos (RF009)
        form = OperarioForm(request.POST, request.FILES, instance=operario)
        if form.is_valid():
            operario = form.save()
            messages.success(request, f'Operario "{operario.nombre_completo}" actualizado correctamente.')
            return redirect('operario_lista')
    else:
        form = OperarioForm(instance=operario)
    
    context = {
        'form': form,
        'operario': operario,
        'titulo': 'Editar Operario',
        'boton_texto': 'Guardar Cambios'
    }
    return render(request, 'autenticacion/operario_form.html', context)


@admin_required
def operario_eliminar(request, pk):
    """Eliminar (desactivar) operario"""
    operario = get_object_or_404(Operario, pk=pk)
    
    if request.method == 'POST':
        # ✅ NUEVO: Eliminar también el archivo físico si existe
        if operario.certificacion_documento:
            operario.certificacion_documento.delete(save=False)
        
        operario.esta_activo = False
        operario.save()
        messages.success(request, f'Operario "{operario.nombre_completo}" desactivado correctamente.')
        return redirect('operario_lista')
    
    context = {'operario': operario}
    return render(request, 'autenticacion/operario_confirmar_eliminar.html', context)

# ==================== ALERTAS DE CERTIFICACIONES ====================

@login_required
def alertas_certificaciones(request):
    """Vista para mostrar alertas de certificaciones por vencer (RF008)"""
    from datetime import timedelta
    
    # Operarios con certificaciones por vencer (30 días)
    operarios_por_vencer = Operario.objects.filter(
        fecha_vencimiento_certificacion__lte=timezone.now().date() + timedelta(days=30),
        fecha_vencimiento_certificacion__gte=timezone.now().date(),
        esta_activo=True
    ).order_by('fecha_vencimiento_certificacion')
    
    # Operarios con certificaciones vencidas
    operarios_vencidos = Operario.objects.filter(
        fecha_vencimiento_certificacion__lt=timezone.now().date(),
        esta_activo=True
    ).order_by('fecha_vencimiento_certificacion')
    
    context = {
        'operarios_por_vencer': operarios_por_vencer,
        'operarios_vencidos': operarios_vencidos,
    }
    return render(request, 'autenticacion/alertas_certificaciones.html', context)


@login_required
def dashboard_alertas(request):
    """Endpoint para AJAX - alertas para el dashboard (RF008)"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from datetime import timedelta
        
        operarios_por_vencer = Operario.objects.filter(
            fecha_vencimiento_certificacion__lte=timezone.now().date() + timedelta(days=30),
            fecha_vencimiento_certificacion__gte=timezone.now().date(),
            esta_activo=True
        ).count()
        
        operarios_vencidos = Operario.objects.filter(
            fecha_vencimiento_certificacion__lt=timezone.now().date(),
            esta_activo=True
        ).count()
        
        data = {
            'por_vencer': operarios_por_vencer,
            'vencidos': operarios_vencidos,
            'total_alertas': operarios_por_vencer + operarios_vencidos
        }
        return JsonResponse(data)

# ==================== RECUPERACIÓN DE CONTRASEÑA ====================

def recuperar_password(request):
    """Solicitud de recuperación de contraseña"""
    if request.method == 'POST':
        form = RecuperarPasswordForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo_electronico']
            usuario = Usuario.objects.get(correo_electronico=correo)
            
            # Generar token único
            token = get_random_string(64)
            
            # Guardar el token en la sesión temporal (en producción usar Redis o base de datos)
            request.session[f'reset_token_{token}'] = {
                'usuario_id': usuario.id,
                'expira': (timezone.now() + timedelta(hours=1)).isoformat()
            }
            
            # Crear enlace de recuperación
            reset_link = request.build_absolute_uri(f'/password/reset/{token}/')
            
            # Enviar email (configurar en settings.py)
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
                # Si falla el envío de email, mostrar el link (solo para desarrollo)
                if settings.DEBUG:
                    messages.warning(request, f'Email no configurado. Link de recuperación: {reset_link}')
                else:
                    messages.error(request, 'Error al enviar el correo. Intenta nuevamente.')
            
            return redirect('login')
    else:
        form = RecuperarPasswordForm()
    
    return render(request, 'autenticacion/recuperar_password.html', {'form': form})


def reset_password(request, token):
    """Restablecer contraseña con token"""
    # Verificar token
    token_data = request.session.get(f'reset_token_{token}')
    
    if not token_data:
        messages.error(request, 'El enlace de recuperación no es válido o ha expirado.')
        return redirect('login')
    
    # Verificar expiración
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
            
            # Eliminar token usado
            del request.session[f'reset_token_{token}']
            
            messages.success(request, 'Tu contraseña ha sido actualizada correctamente. Ahora puedes iniciar sesión.')
            return redirect('login')
    else:
        form = CambiarPasswordForm()
    
    context = {
        'form': form,
        'usuario': usuario
    }
    return render(request, 'autenticacion/reset_password.html', context)


# ==================== RUTAS PRÓXIMAMENTE ====================

@login_required
def aplicaciones_proximamente(request):
    """Página de módulo en desarrollo - Aplicaciones"""
    context = {
        'modulo': 'Aplicaciones Fitosanitarias',
        'descripcion': 'Módulo para el registro y control de aplicaciones fitosanitarias.'
    }
    return render(request, 'autenticacion/proximamente.html', context)


@login_required
def riego_proximamente(request):
    """Página de módulo en desarrollo - Riego"""
    context = {
        'modulo': 'Control de Riego',
        'descripcion': 'Módulo para el registro y control de actividades de riego.'
    }
    return render(request, 'autenticacion/proximamente.html', context)


@login_required
def mantencion_proximamente(request):
    """Página de módulo en desarrollo - Mantención"""
    context = {
        'modulo': 'Mantención y Calibración',
        'descripcion': 'Módulo para el registro de mantenimientos y calibraciones de equipos.'
    }
    return render(request, 'autenticacion/proximamente.html', context)