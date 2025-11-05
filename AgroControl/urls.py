from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView  # ← AGREGAR ESTA IMPORTACIÓN

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='cuarteles:lista_cuarteles'), name='home'),
    path('cuarteles/', include('cuarteles.urls')),
]
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('autenticacion.urls')),
    path('inventario/', include('inventario.urls')),
    path('aplicaciones/', include('aplicaciones.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
