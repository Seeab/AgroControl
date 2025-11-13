# aplicaciones/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AplicacionFitosanitaria
# from inventario.models import MovimientoInventario # Ya no se usa aquí

# --- IMPORTANTE: ESTA SEÑAL SE DESACTIVA ---
# La lógica ahora vive en las vistas 'crear_aplicacion' y 'finalizar_aplicacion'
# (dentro de la función 'crear_movimiento_salida_para_app')
# para manejar correctamente la validación de stock de MÚLTIPLES productos
# y la creación del MovimientoInventario y sus DetalleMovimiento.

@receiver(post_save, sender=AplicacionFitosanitaria)
def crear_movimiento_salida(sender, instance, created, **kwargs):
    """
    (DESACTIVADO)
    La lógica de creación de movimientos se maneja en las vistas
    para poder procesar el FormSet de productos.
    """
    pass
    
    # if created and instance.estado == 'realizada' and instance.cantidad_utilizada > 0:
    #     
    #     MovimientoInventario.objects.create(
    #         producto=instance.producto,
    #         tipo_movimiento='salida',
    #         cantidad=instance.cantidad_utilizada,
    #         fecha_movimiento=instance.fecha_aplicacion,
    #         motivo=f"Salida por Aplicación Fitosanitaria ID: {instance.id}",
    #         referencia=f"APL-{instance.id}",
    #         realizado_por_id=instance.creado_por_id, 
    #         aplicacion=instance # ¡La conexión clave!
    #     )