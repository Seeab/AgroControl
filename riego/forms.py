# riego/forms.py
from django import forms
from .models import ControlRiego, FertilizanteRiego
from cuarteles.models import Cuartel
from autenticacion.models import Usuario
from inventario.models import Producto

# ---------------------------------------------------------------
# Formulario Principal (ControlRiego)
# ---------------------------------------------------------------
class ControlRiegoForm(forms.ModelForm):
    """Formulario para ControlRiego con ForeignKey"""
    
    class Meta:
        model = ControlRiego
        fields = [
            'cuartel',
            'estado',  # <--- ¡RE-AGREGADO!
            'fecha',
            'horario_inicio',
            'horario_fin', 
            'caudal_m3h',
            'incluye_fertilizante',
            'encargado_riego',
            'observaciones'
        ]
        widgets = {
            'cuartel': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}), # <--- ¡RE-AGREGADO!
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horario_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'caudal_m3h': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'incluye_fertilizante': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'encargado_riego': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Configurar cuarteles (sin cambios)
        self.fields['cuartel'].queryset = Cuartel.objects.all().order_by('nombre')
        self.fields['cuartel'].empty_label = "Seleccione un cuartel"
        self.fields['cuartel'].label_from_instance = lambda obj: f"{obj.nombre} (Cuartel {obj.numero})"
        
        # 2. Filtrar SÓLO por "Regadores" (tu código ya está aquí)
        try:
            self.fields['encargado_riego'].queryset = Usuario.objects.filter(
                esta_activo=True,
                rol__nombre__in=['regador'] # <-- CORREGIDO A 'regador'
            ).order_by('nombres')
        except Exception:
             self.fields['encargado_riego'].queryset = Usuario.objects.filter(
                esta_activo=True
            ).order_by('nombres')

        self.fields['encargado_riego'].empty_label = "Seleccione un encargado"
        
        # 3. Mostrar nombre completo del usuario (sin cambios)
        if hasattr(Usuario, 'get_full_name') and callable(getattr(Usuario, 'get_full_name')):
             self.fields['encargado_riego'].label_from_instance = lambda obj: obj.get_full_name()
        elif hasattr(Usuario, 'nombres'):
             self.fields['encargado_riego'].label_from_instance = lambda obj: f"{obj.nombres} {obj.apellidos}"


# ---------------------------------------------------------------
# Formulario Secundario (FertilizanteRiego)
# ---------------------------------------------------------------
class FertilizanteRiegoForm(forms.ModelForm):
    """Formulario simple para un solo fertilizante"""
    class Meta:
        model = FertilizanteRiego
        fields = ['producto', 'cantidad_kg']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'cantidad_kg': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar productos para que solo muestre fertilizantes
        self.fields['producto'].queryset = Producto.objects.filter(
            tipo='fertilizante',
            esta_activo=True
        ).order_by('nombre')
        self.fields['producto'].empty_label = "Seleccione fertilizante"

    # ==========================================================
    # --- MÉTODO 'clean' ELIMINADO ---
    # ==========================================================
    # La validación de stock (clean) se eliminó.
    # La validación de 'unidad_medida' también se eliminó para simplificar,
    # pero puedes agregarla de nuevo si es estrictamente necesaria.
    # La validación de stock REAL se hace en 'views.py'
    # (en _crear_movimiento_salida_riego), tal como en tu app 'aplicaciones'.


# ---------------------------------------------------------------
# FormSet (No necesita cambios)
# ---------------------------------------------------------------
FertilizanteRiegoFormSet = forms.inlineformset_factory(
    ControlRiego,           # Modelo Padre
    FertilizanteRiego,      # Modelo Hijo
    form=FertilizanteRiegoForm, # El formulario a usar
    extra=1,                # Cuántos formularios vacíos mostrar
    can_delete=True,        # Permitir al usuario borrar fertilizantes
    fk_name='control_riego'
)