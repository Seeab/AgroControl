from django.urls import path
from . import views

app_name = 'riego'

urlpatterns = [
    # Vistas principales
    path('', views.dashboard_riego, name='dashboard'),
    path('lista/', views.lista_riegos, name='riego_lista'),
    path('crear/', views.crear_riego, name='riego_crear'),
    path('<int:riego_id>/', views.detalle_riego, name='detalle'),
    path('editar/<int:pk>/', views.editar_riego, name='editar'),
    path('eliminar/<int:pk>/', views.eliminar_riego, name='eliminar'),
    
    # Fertilizantes
    path('<int:riego_id>/agregar-fertilizante/', views.agregar_fertilizante, name='agregar_fertilizante'),
]