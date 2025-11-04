from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.lista_productos, name='lista_productos'),
    path('crear/', views.crear_producto, name='crear_producto'),
    path('<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    path('<int:producto_id>/editar/', views.editar_producto, name='editar_producto'),
    path('movimientos/crear/', views.crear_movimiento, name='crear_movimiento'),
    path('movimientos/crear/<int:producto_id>/', views.crear_movimiento, name='crear_movimiento_producto'),
    path('movimientos/historial/', views.historial_movimientos, name='historial_movimientos'),
]