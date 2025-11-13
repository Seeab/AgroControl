# inventario/urls.py (Ejemplo de cómo debería quedar)

from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    # Rutas de Productos
    path('', views.lista_productos, name='lista_productos'),
    path('producto/crear/', views.crear_producto, name='crear_producto'),
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    path('producto/<int:producto_id>/editar/', views.editar_producto, name='editar_producto'),

    # Rutas de Movimientos
    path('movimientos/', views.historial_movimientos, name='historial_movimientos'),
    
    # --- ✨ URL NUEVA AÑADIDA AQUÍ ✨ ---
    path('movimientos/<int:movimiento_id>/', views.detalle_movimiento, name='detalle_movimiento'),
    
    path('movimientos/crear/', views.crear_movimiento, name='crear_movimiento'),
    path('movimientos/crear/<int:producto_id>/', views.crear_movimiento, name='crear_movimiento_producto'),

    # Rutas de Maquinaria
    path('maquinaria/', views.lista_maquinaria, name='lista_maquinaria'),
    path('maquinaria/crear/', views.crear_maquinaria, name='crear_maquinaria'),
    path('maquinaria/<int:equipo_id>/', views.detalle_maquinaria, name='detalle_maquinaria'),
    path('maquinaria/<int:equipo_id>/editar/', views.editar_maquinaria, name='editar_maquinaria'),
]