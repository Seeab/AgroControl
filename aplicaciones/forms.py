# aplicaciones/forms.py

from django import forms
from .models import AplicacionFitosanitaria
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
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(esta_activo=True).order_by('nombre'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
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
        fields = [
            'aplicador', 'fecha_aplicacion', 'producto', 'cantidad_utilizada',
            'cuarteles', 'objetivo', 'metodo_aplicacion', 'estado',
            'equipo_utilizado'
        ]
        widgets = {
            'cantidad_utilizada': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}
            ),
            'objetivo': forms.TextInput(attrs={'class': 'form-control'}),
            'metodo_aplicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        """
        Validación central (RF020) y cálculos (LÓGICA INVERTIDA)
        """
        cleaned_data = super().clean()
        
        producto = cleaned_data.get('producto')
        cantidad_utilizada = cleaned_data.get('cantidad_utilizada')
        cuarteles = cleaned_data.get('cuarteles')

        if producto and cantidad_utilizada and cuarteles:
            
            # 1. Validar stock (RF020)
            if cantidad_utilizada > producto.stock_actual:
                raise forms.ValidationError({
                    'cantidad_utilizada': (
                        f"No hay suficiente stock. Requerido: {cantidad_utilizada} {producto.unidad_medida}, "
                        f"Disponible: {producto.stock_actual} {producto.unidad_medida}."
                    )
                })

            # 2. Calcular área total
            try:
                area_total = sum(c.area_hectareas for c in cuarteles if c.area_hectareas)
                if area_total <= 0:
                        raise forms.ValidationError(
                            "El área total de los cuarteles seleccionados debe ser mayor a 0."
                        )
                cleaned_data['area_tratada'] = area_total
            except Exception as e:
                raise forms.ValidationError(f"Error al calcular el área: {e}")

            # 3. Calcular Dosis/Ha
            if area_total > 0:
                dosis_calculada = cantidad_utilizada / area_total
                cleaned_data['dosis_por_hectarea'] = dosis_calculada
            else:
                cleaned_data['dosis_por_hectarea'] = 0

        return cleaned_data