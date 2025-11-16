# riego/admin.py - CORREGIDO Y OPTIMIZADO
from django.contrib import admin
# Importar AMBOS modelos
from .models import ControlRiego, FertilizanteRiego 

# --- 1. Definir el Inline (como lo hiciste) ---
class FertilizanteRiegoInline(admin.TabularInline):
    """Inline para mostrar fertilizantes dentro de ControlRiego"""
    model = FertilizanteRiego
    extra = 1  # Iniciar con 1 campo vacío para añadir
    fields = ['producto', 'cantidad_kg']
    verbose_name = 'Fertilizante'
    verbose_name_plural = 'Fertilizantes aplicados'
    
    # Optimización: usar autocompletar para buscar productos
    autocomplete_fields = ['producto']


# --- 2. Definir el Admin Principal ---
@admin.register(ControlRiego)
class ControlRiegoAdmin(admin.ModelAdmin):
    """Admin para ControlRiego - RF014, RF015, RF016"""
    
    # Optimización: Carga las relaciones para evitar consultas N+1
    list_select_related = ['cuartel', 'encargado_riego']
    
    list_display = [
        'id',
        'cuartel',              ## <-- CORREGIDO (usa el objeto, no el _id)
        'fecha',
        'estado', 
        'horario_inicio', 
        'horario_fin',
        'get_duracion_display', ## <-- CORREGIDO (usa el método)
        'get_volumen_display',  ## <-- CORREGIDO (usa el método)
        'incluye_fertilizante',
        'encargado_riego',      ## <-- CORREGIDO (usa el objeto)
    ]
    
    list_filter = [
        'estado',
        'fecha',
        'incluye_fertilizante',
        'cuartel'               ## <-- CORREGIDO (usa el objeto)
    ]
    
    search_fields = [
        'cuartel__nombre',          ## <-- CORREGIDO (busca en el nombre)
        'encargado_riego__username',## <-- CORREGIDO (o __email, o lo que uses)
        'observaciones'
    ]
    
    readonly_fields = [
        'duracion_minutos',
        'volumen_total_m3',
        'creado_en'
    ]
    
    fieldsets = (
        ('Información del Riego', {
            'fields': (
                'cuartel',
                'estado',          ## <-- CORREGIDO
                'fecha',
                ('horario_inicio', 'horario_fin'),
                'duracion_minutos'
            )
        }),
        ('Datos Técnicos', {
            'fields': (
                'caudal_m3h',
                'volumen_total_m3',
                'incluye_fertilizante'
            )
        }),
        ('Personal', {
            'fields': (
                'encargado_riego',  ## <-- CORREGIDO
            )
        }),
        ('Observaciones', {
            'fields': (
                'observaciones',
            )
        }),
        ('Auditoría', {
            'fields': (
                'creado_en',
                'creado_por'
            ),
            'classes': ('collapse',)
        })
    )
    
    list_per_page = 20
    
    # --- 3. Añadir el Inline (como lo hiciste) ---
    inlines = [FertilizanteRiegoInline]
    
    # Métodos personalizados (los tuyos estaban bien)
    def get_duracion_display(self, obj):
        return obj.get_duracion_display()
    get_duracion_display.short_description = 'Duración'
    
    def get_volumen_display(self, obj):
        if obj.volumen_total_m3:
            return f"{obj.volumen_total_m3} m³"
        return "No calculado"
    get_volumen_display.short_description = 'Volumen Total'


# --- 4. Definir el Admin Secundario ---
@admin.register(FertilizanteRiego)
class FertilizanteRiegoAdmin(admin.ModelAdmin):
    """Admin para FertilizanteRiego - RF017"""
    
    # Optimización
    list_select_related = ['control_riego', 'producto', 'control_riego__cuartel']
    
    list_display = [
        'id',
        'control_riego',
        'producto',
        'get_cantidad_display', ## <-- CORREGIDO (usa el método)
        'get_fecha_riego'
    ]
    
    list_filter = [
        'producto',
        'control_riego__fecha'  ## <-- Esto estaba bien
    ]
    
    search_fields = [
        'producto__nombre',                 ## <-- CORREGIDO
        'control_riego__cuartel__nombre'  ## <-- CORREGIDO
    ]
    
    list_per_page = 20
    
    # Métodos personalizados (los tuyos estaban bien)
    def get_fecha_riego(self, obj):
        return obj.control_riego.fecha
    get_fecha_riego.short_description = 'Fecha Riego'
    get_fecha_riego.admin_order_field = 'control_riego__fecha'
    
    def get_cantidad_display(self, obj):
        return f"{obj.cantidad_kg} kg"
    get_cantidad_display.short_description = 'Cantidad'