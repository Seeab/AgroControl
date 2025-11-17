# AgroControl/urls.py (Este es el archivo central)

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- 1. RUTAS DE APPS (con prefijo) ---
    path('aplicaciones/', include('aplicaciones.urls', namespace='aplicaciones')),
    path('riego/', include('riego.urls', namespace='riego')),
    path('mantenimiento/', include('mantenimiento.urls', namespace='mantenimiento')),
    
    path('cuarteles/', include('cuarteles.urls', namespace='cuarteles')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    
    # <-- CORRECCIÓN: Añadido 'namespace' para consistencia
    path('ordenes/', include('ordenes_trabajo.urls', namespace='ordenes_trabajo')),
    
    # --- 2. RUTA RAÍZ (al final) ---
    path('', include('autenticacion.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)