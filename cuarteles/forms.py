from django import forms
from .models import Cuartel, Hilera, SeguimientoCuartel, RegistroHilera
from django.forms import inlineformset_factory

class CuartelForm(forms.ModelForm):
    plantas_iniciales_predeterminadas = forms.IntegerField(
        min_value=0, 
        label="Plantas Iniciales por Hilera (Opcional)",
        help_text="Valor inicial para todas las hileras. Podrá editarlo individualmente después.",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        initial=0,
        required=False
    )

    class Meta:
        model = Cuartel
        fields = [
            'numero', 'nombre', 'ubicacion', 'variedad', 'tipo_planta',
            'año_plantacion', 'tipo_riego', 'estado_cultivo', 'area_hectareas',
            'cantidad_hileras', 'plantas_iniciales_predeterminadas', 'observaciones'
        ]
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: C-001'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre descriptivo'}),
            'ubicacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'variedad': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_planta': forms.TextInput(attrs={'class': 'form-control'}),
            'año_plantacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 2000, 'max': 2030}),
            'tipo_riego': forms.Select(attrs={'class': 'form-select'}),
            'estado_cultivo': forms.Select(attrs={'class': 'form-select'}),
            'area_hectareas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cantidad_hileras': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'numero': 'Número único de cuartel *',
            'nombre': 'Nombre del cuartel *',
            'año_plantacion': 'Año de plantación *',
            'cantidad_hileras': 'Cantidad de Hileras *',
        }

    def clean_numero(self):
        numero = self.cleaned_data['numero']
        # (self.instance.pk is None) significa que es un objeto NUEVO
        if Cuartel.objects.filter(numero=numero).exists() and self.instance.pk is None:
            raise forms.ValidationError("Este número de cuartel ya existe.")
        return numero

    def save(self, commit=True):
        cuartel = super().save(commit=False)
        if commit:
            cuartel.save()
            self.crear_actualizar_hileras(cuartel)
        return cuartel

    def crear_actualizar_hileras(self, cuartel):
        cantidad_nueva = self.cleaned_data.get('cantidad_hileras', cuartel.cantidad_hileras)
        plantas_ini = self.cleaned_data.get('plantas_iniciales_predeterminadas', 0)
        hileras_actuales = list(cuartel.hileras.all())
        count_actual = len(hileras_actuales)

        if cantidad_nueva > count_actual:
            for i in range(count_actual + 1, cantidad_nueva + 1):
                Hilera.objects.create(
                    cuartel=cuartel,
                    numero_hilera=i,
                    plantas_totales_iniciales=plantas_ini if self.instance.pk is None else 0,
                    plantas_vivas_actuales=plantas_ini if self.instance.pk is None else 0,
                    plantas_muertas_actuales=0
                )
        elif cantidad_nueva < count_actual:
            for hilera in hileras_actuales[cantidad_nueva:]:
                hilera.delete()

class HileraForm(forms.ModelForm):
    class Meta:
        model = Hilera
        fields = ['plantas_totales_iniciales']
        widgets = {
            'plantas_totales_iniciales': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0}),
        }

HileraFormSet = inlineformset_factory(
    Cuartel, Hilera, form=HileraForm,
    fields=['plantas_totales_iniciales'],
    extra=0, can_delete=False
)

class SeguimientoCuartelForm(forms.ModelForm):
    class Meta:
        model = SeguimientoCuartel
        fields = ['fecha_seguimiento', 'observaciones']
        widgets = {
            'fecha_seguimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones generales del seguimiento...'}),
        }
        labels = {
            'fecha_seguimiento': 'Fecha del Seguimiento *'
        }

# === CORREGIDO (para arreglar FieldError) ===
class RegistroHileraForm(forms.ModelForm):
    class Meta:
        model = RegistroHilera
        fields = ['hilera', 'plantas_vivas_registradas', 'plantas_muertas_registradas', 'observaciones_hilera']
        
        # --- AÑADE ESTO ---
        widgets = {
            'plantas_vivas_registradas': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0}),
            'plantas_muertas_registradas': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0}),
            'observaciones_hilera': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Opcional'}),
            
            # --- LA CLAVE ESTÁ AQUÍ ---
            # Le decimos a Django que este campo es oculto.
            'hilera': forms.HiddenInput(),
        }

# # === CORREGIDO (para arreglar FieldError) ===
# RegistroHileraFormSet = inlineformset_factory(
#     SeguimientoCuartel,
#     RegistroHilera,
#     form=RegistroHileraForm,
#     fields=['hilera', 'plantas_vivas_registradas', 'plantas_muertas_registradas', 'observaciones_hilera'],
#     extra=0,
#     can_delete=False
# )