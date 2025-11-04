from django.contrib import admin
from .models import Rol, Usuario, Operario

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'creado_en')
    search_fields = ('nombre',)
    readonly_fields = ('creado_en',)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre_usuario', 'get_full_name', 'correo_electronico', 
                    'rol', 'esta_activo', 'es_administrador', 'fecha_registro')
    list_filter = ('esta_activo', 'es_administrador', 'rol', 'fecha_registro')
    search_fields = ('nombre_usuario', 'nombres', 'apellidos', 'correo_electronico')
    readonly_fields = ('fecha_registro', 'ultimo_acceso')
    
    fieldsets = (
        ('Información de Acceso', {
            'fields': ('nombre_usuario', 'contraseña')
        }),
        ('Información Personal', {
            'fields': ('nombres', 'apellidos', 'correo_electronico')
        }),
        ('Permisos', {
            'fields': ('rol', 'esta_activo', 'es_administrador')
        }),
        ('Fechas', {
            'fields': ('fecha_registro', 'ultimo_acceso'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Operario)
class OperarioAdmin(admin.ModelAdmin):
    # ✅ CORREGIDO: Usar los campos actuales
    list_display = ('nombre_completo', 'cargo', 'rut', 
                    'fecha_vencimiento_certificacion',  # ✅ CAMBIADO
                    'certificacion_por_vencer', 'certificacion_vencida',
                    'esta_activo', 'creado_en')
    list_filter = ('esta_activo', 'cargo', 'creado_en')
    search_fields = ('nombre_completo', 'rut', 'cargo')
    readonly_fields = ('creado_en', 'actualizado_en', 'certificacion_por_vencer', 'certificacion_vencida')
    
    fieldsets = (
        ('Información del Operario', {
            'fields': ('usuario', 'nombre_completo', 'cargo', 'telefono')
        }),
        ('RUT', {
            'fields': ('rut',)  
        }),
        ('Certificación Profesional', {
            'fields': (
                'fecha_emision_certificacion', 'fecha_vencimiento_certificacion',
                'certificacion_documento'
            )
        }),
        ('Estado', {
            'fields': ('esta_activo',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )

    def certificacion_por_vencer(self, obj):
        return obj.certificacion_por_vencer()
    certificacion_por_vencer.boolean = True
    certificacion_por_vencer.short_description = 'Cert. Por Vencer'

    def certificacion_vencida(self, obj):
        return obj.certificacion_vencida()
    certificacion_vencida.boolean = True
    certificacion_vencida.short_description = 'Cert. Vencida'