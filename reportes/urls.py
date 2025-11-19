from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    # 1. La página que muestra el formulario para elegir el reporte
    path('', views.pagina_reportes, name='pagina_reportes'),
    
    # 2. La URL a la que el formulario envía los datos para generar el archivo
    path('generar/', views.generar_reporte, name='generar_reporte'),
]