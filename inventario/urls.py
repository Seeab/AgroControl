from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    # Productos
    path('', views.lista_productos, name='lista_productos'),
    path('crear/', views.crear_producto, name='crear_producto'),
    path('<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    path('<int:producto_id>/editar/', views.editar_producto, name='editar_producto'),
    
    # Movimientos
    path('movimientos/crear/', views.crear_movimiento, name='crear_movimiento'),
    path('movimientos/crear/<int:producto_id>/', views.crear_movimiento, name='crear_movimiento_producto'),
    path('movimientos/historial/', views.historial_movimientos, name='historial_movimientos'),
    
    # --- AÑADIR ESTAS LÍNEAS ---
    path('maquinaria/', views.lista_maquinaria, name='lista_maquinaria'),
    path('maquinaria/crear/', views.crear_maquinaria, name='crear_maquinaria'),
    path('maquinaria/<int:equipo_id>/', views.detalle_maquinaria, name='detalle_maquinaria'),
    path('maquinaria/<int:equipo_id>/editar/', views.editar_maquinaria, name='editar_maquinaria'),
]
