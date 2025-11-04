# aplicaciones/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AplicacionFitosanitaria
from inventario.models import MovimientoInventario

@receiver(post_save, sender=AplicacionFitosanitaria)
def crear_movimiento_salida(sender, instance, created, **kwargs):
    """
    RF021: Descontar automáticamente del inventario.
    Se activa después de crear una nueva aplicación 'realizada'.
    """
    
    # Solo actuar si es una NUEVA creación (created=True)
    # y si la aplicación está marcada como 'realizada'
    # y si la cantidad es mayor a 0.
    if created and instance.estado == 'realizada' and instance.cantidad_utilizada > 0:
        
        # Creamos el movimiento de inventario.
        # La lógica en MovimientoInventario.save() (que tú ya tienes)
        # se encargará de actualizar el stock_actual del Producto.
        MovimientoInventario.objects.create(
            producto=instance.producto,
            tipo_movimiento='salida',
            cantidad=instance.cantidad_utilizada,
            fecha_movimiento=instance.fecha_aplicacion,
            motivo=f"Salida por Aplicación Fitosanitaria ID: {instance.id}",
            referencia=f"APL-{instance.id}",
            realizado_por=instance.creado_por, # La persona que registró la app
            aplicacion=instance # ¡La conexión clave!
        )