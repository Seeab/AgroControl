# ordenes_trabajo/urls.py
from django.urls import path
from . import views

app_name = 'ordenes_trabajo'

urlpatterns = [
    # RF037, RF038, RF039: Vista principal que unifica todas las tareas
    path(
        '', 
        views.lista_ordenes_trabajo, 
        name='lista_ordenes'
    ),
    
    # Vista "Hub" para decidir qué tipo de orden crear
    path(
        'crear/', 
        views.crear_orden_trabajo, 
        name='crear_orden'
    ),
]