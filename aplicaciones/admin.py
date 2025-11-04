from django.contrib import admin
from .models import AplicacionFitosanitaria
from .forms import AplicacionForm # <-- 1. IMPORTA EL FORMULARIO

@admin.register(AplicacionFitosanitaria)
class AplicacionFitosanitariaAdmin(admin.ModelAdmin):
    # Asignamos el formulario personalizado al admin
    form = AplicacionForm # <-- 2. AÑADE ESTA LÍNEA
    
    list_display = (
        '__str__',
        'aplicador',
        'fecha_aplicacion',
        'producto',
        'dosis_por_hectarea',
        'area_tratada',
        'cantidad_utilizada',
        'estado',
        'creado_por'
    )
    list_filter = ('estado', 'producto', 'aplicador', 'fecha_aplicacion')
    search_fields = (
        'producto__nombre', 
        'aplicador__username', 
        'cuarteles__nombre' # Asumo que Cuartel tiene 'nombre'
    )
    readonly_fields = (
        'area_tratada', 
        'cantidad_utilizada', 
        'fecha_creacion', 
        'fecha_actualizacion'
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
        if not obj.creado_por_id:
            obj.creado_por = request.user
        
        # 3. ACTUALIZA ESTA SECCIÓN
        # Los cálculos ya vienen hechos desde el form.clean()
        if form.is_valid() and 'area_tratada' in form.cleaned_data:
            obj.area_tratada = form.cleaned_data['area_tratada']
            obj.cantidad_utilizada = form.cleaned_data['cantidad_utilizada']
        
        super().save_model(request, obj, form, change)
        # (La señal post_save se disparará después de esto)