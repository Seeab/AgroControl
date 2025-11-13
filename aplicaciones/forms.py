# aplicaciones/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import AplicacionFitosanitaria, AplicacionProducto
from cuarteles.models import Cuartel
from inventario.models import Producto, EquipoAgricola
# --- CORRECCIÓN 1: Importar tu modelo Usuario, NO el de Django ---
from autenticacion.models import Usuario 

class AplicacionForm(forms.ModelForm):
    
    # --- Campos personalizados ---
    aplicador = forms.ModelChoiceField(
        # --- CORRECCIÓN 2: Usar tu 'Usuario' y filtrar por el rol correcto ---
        # Asumo que tienes un Rol con nombre 'aplicador'
        queryset=Usuario.objects.filter(
            esta_activo=True, 
            rol__nombre='aplicador' # O el filtro que definas para "aplicadores"
        ).order_by('nombres', 'apellidos'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # --- CAMPO ELIMINADO ---
    # producto = forms.ModelChoiceField(...)
    
    cuarteles = forms.ModelMultipleChoiceField(
        queryset=Cuartel.objects.all().order_by('nombre'), 
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'})
    )
    fecha_aplicacion = forms.DateTimeField(
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'class': 'form-control', 'type': 'datetime-local'}
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']
    )

    equipo_utilizado = forms.ModelChoiceField(
        queryset=EquipoAgricola.objects.filter(estado='operativo').order_by('nombre'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Equipo Utilizado (Opcional)'
    )

    class Meta:
        model = AplicacionFitosanitaria
        # --- CAMPOS MODIFICADOS ---
        # Quitamos 'producto' y 'cantidad_utilizada'
        fields = [
            'aplicador', 'fecha_aplicacion', 'cuarteles', 
            'objetivo', 'metodo_aplicacion', 'estado',
            'equipo_utilizado'
        ]
        widgets = {
            # 'cantidad_utilizada': forms.NumberInput(...) # ELIMINADO
            'objetivo': forms.TextInput(attrs={'class': 'form-control'}),
            'metodo_aplicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        """
        Validación central (RF020) y cálculos (LÓGICA INVERTIDA)
        (MODIFICADO)
        """
        cleaned_data = super().clean()
        
        # --- LÓGICA DE STOCK ELIMINADA ---
        # La validación de stock ahora se hace en el FormSet.
        
        cuarteles = cleaned_data.get('cuarteles')

        if cuarteles:
            # 1. Calcular área total y guardarla en el form
            try:
                area_total = sum(c.area_hectareas for c in cuarteles if c.area_hectareas)
                if area_total <= 0:
                        raise forms.ValidationError(
                            "El área total de los cuarteles seleccionados debe ser mayor a 0."
                        )
                # Guardamos esto para que el formset lo use
                cleaned_data['area_tratada'] = area_total 
            except Exception as e:
                raise forms.ValidationError(f"Error al calcular el área: {e}")
        else:
             cleaned_data['area_tratada'] = 0
             # Opcional: ¿lanzar error si no hay cuarteles?
             # raise forms.ValidationError("Debe seleccionar al menos un cuartel.")

        # --- LÓGICA DE DOSIS ELIMINADA ---
        # La dosis se calcula por producto en el modelo 'AplicacionProducto'

        return cleaned_data

# --- NUEVO FORMULARIO PARA EL INLINE ---
class AplicacionProductoForm(forms.ModelForm):
    """
    Formulario para la tabla intermedia AplicacionProducto
    """
    
    # Hacemos el queryset más específico
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(esta_activo=True).order_by('nombre'),
        widget=forms.Select(attrs={'class': 'form-control producto-select'})
    )
    
    cantidad_utilizada = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )

    class Meta:
        model = AplicacionProducto
        fields = ['producto', 'cantidad_utilizada']

    def clean(self):
        """Validación de stock por cada producto (RF020)"""
        cleaned_data = super().clean()
        
        producto = cleaned_data.get('producto')
        cantidad_utilizada = cleaned_data.get('cantidad_utilizada')
        
        # Esta validación solo se aplica si el form NO está marcado para borrarse
        if not cleaned_data.get('DELETE', False):
            if producto and cantidad_utilizada:
                if cantidad_utilizada > producto.stock_actual:
                    raise forms.ValidationError(
                        f"No hay stock de '{producto.nombre}'. "
                        f"Requerido: {cantidad_utilizada} {producto.unidad_medida}, "
                        f"Disponible: {producto.stock_actual} {producto.unidad_medida}."
                    )
            
            if not producto:
                raise forms.ValidationError("Debe seleccionar un producto.")
            
            if not cantidad_utilizada or cantidad_utilizada <= 0:
                raise forms.ValidationError("La cantidad debe ser mayor a 0.")

        return cleaned_data

# --- NUEVO FORMSET ---
# Creamos el FormSet que unirá AplicacionFitosanitaria con AplicacionProducto
AplicacionProductoFormSet = inlineformset_factory(
    AplicacionFitosanitaria,       # Modelo Padre
    AplicacionProducto,            # Modelo Hijo (intermedio)
    form=AplicacionProductoForm,   # Formulario para el hijo
    extra=1,                       # Empezar con 1 formulario vacío
    can_delete=True,               # Permitir borrar productos
    fk_name='aplicacion',
    min_num=1,                     # Exigir al menos 1 producto
    validate_min=True,
)