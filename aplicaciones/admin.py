# aplicaciones/admin.py

from django.contrib import admin
from .models import AplicacionFitosanitaria, AplicacionProducto
from .forms import AplicacionProductoForm # Usamos el form customizado
# --- CORRECCIÓN 1: Importar tu modelo Usuario ---
from autenticacion.models import Usuario 

# --- NUEVO INLINE ---
class AplicacionProductoInline(admin.TabularInline):
    model = AplicacionProducto
    form = AplicacionProductoForm # Usamos el form que valida stock
    extra = 1
    readonly_fields = ('dosis_por_hectarea',)
    autocomplete_fields = ['producto'] # Mejor para muchos productos


@admin.register(AplicacionFitosanitaria)
class AplicacionFitosanitariaAdmin(admin.ModelAdmin):
    # form = AplicacionForm # El form de admin es complejo con M2M
    
    list_display = (
        '__str__', 'aplicador', 'fecha_aplicacion', 
        'get_productos_display', # Helper del modelo
        'area_tratada',
        'estado', 'creado_por'
    )
    list_filter = ('estado', 'aplicador', 'fecha_aplicacion')
    search_fields = (
        'productos__nombre', # Búsqueda en M2M
        'aplicador__nombre_usuario', 
        'aplicador__nombres',
        'aplicador__apellidos',
        'cuarteles__nombre'
    )
    readonly_fields = (
        'area_tratada', 
        'fecha_creacion', 'fecha_actualizacion'
    )
    
    filter_horizontal = ('cuarteles',)
    
    # --- AÑADIR EL INLINE ---
    inlines = [AplicacionProductoInline]

    fieldsets = (
        ('Detalles de la Aplicación', {
            'fields': (
                'fecha_aplicacion', 'aplicador', 'estado', 
                'objetivo', 'metodo_aplicacion'
            )
        }),
        ('Dosis y Cuarteles', {
            'fields': ('cuarteles',) # 'productos' se maneja en el inline
        }),
        ('Totales Calculados (Automático)', {
            'fields': ('area_tratada',),
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
                pass 
        
        super().save_model(request, obj, form, change)
        
        # Recalcular área después de guardar (los inlines se guardan después)
        # obj.save() # Llama al save() del modelo

    def save_related(self, request, form, formsets, change):
        """
        Recalcula el área después de guardar los M2M (cuarteles)
        y los inlines (productos).
        """
        super().save_related(request, form, formsets, change)
        # Asegurar que el área se recalcule después de guardar M2M
        form.instance.save() # Esto llama al save() del modelo


    def get_queryset(self, request):
        # Optimizar la carga
        return super().get_queryset(request).prefetch_related('aplicacionproducto_set__producto')