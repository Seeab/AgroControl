# aplicaciones/admin.py

from django.contrib import admin
from .models import AplicacionFitosanitaria
from .forms import AplicacionForm
# --- CORRECCIÓN 1: Importar tu modelo Usuario ---
from autenticacion.models import Usuario 

@admin.register(AplicacionFitosanitaria)
class AplicacionFitosanitariaAdmin(admin.ModelAdmin):
    form = AplicacionForm
    
    list_display = (
        '__str__', 'aplicador', 'fecha_aplicacion', 'producto',
        'dosis_por_hectarea', 'area_tratada', 'cantidad_utilizada',
        'estado', 'creado_por'
    )
    list_filter = ('estado', 'producto', 'aplicador', 'fecha_aplicacion')
    search_fields = (
        'producto__nombre', 
        # --- CORRECCIÓN 2: Asumir que tu 'Usuario' tiene 'nombre_usuario' y 'nombres' ---
        'aplicador__nombre_usuario', 
        'aplicador__nombres',
        'aplicador__apellidos',
        'cuarteles__nombre'
    )
    readonly_fields = (
        'area_tratada', 'cantidad_utilizada', 
        'fecha_creacion', 'fecha_actualizacion'
    )
    
    filter_horizontal = ('cuarteles',)

    fieldsets = (
        ('Detalles de la Aplicación', {
            'fields': (
                'producto', 'fecha_aplicacion', 'aplicador', 'estado', 
                'objetivo', 'metodo_aplicacion'
            )
        }),
        ('Dosis y Cuarteles', {
            'fields': ('dosis_por_hectarea', 'cuarteles')
        }),
        ('Totales Calculados (Automático)', {
            'fields': ('area_tratada', 'cantidad_utilizada'),
            'classes': ('collapse',) 
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        # --- CORRECCIÓN 3: 'request.user' es un usuario de Django, no tu 'Usuario' custom ---
        if not obj.creado_por_id:
            try:
                # Intentamos buscar tu Usuario custom usando el username del admin de Django
                usuario_custom = Usuario.objects.get(nombre_usuario=request.user.username)
                obj.creado_por = usuario_custom
            except Usuario.DoesNotExist:
                # Si no existe, no lo asignamos.
                # El formulario fallará si 'creado_por' es obligatorio y no se seleccionó manualmente.
                pass 
        
        if form.is_valid() and 'area_tratada' in form.cleaned_data:
            obj.area_tratada = form.cleaned_data['area_tratada']
            obj.cantidad_utilizada = form.cleaned_data['cantidad_utilizada']
        
        super().save_model(request, obj, form, change)