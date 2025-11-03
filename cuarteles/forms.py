from django import forms
from .models import Cuartel, SeguimientoCuartel

class CuartelForm(forms.ModelForm):
    class Meta:
        model = Cuartel
        fields = [
            'numero', 'nombre', 'ubicacion', 'variedad', 'tipo_planta',
            'año_plantacion', 'tipo_riego', 'estado_cultivo', 'area_hectareas',
            'plantas_vivas', 'plantas_muertas', 'observaciones'  # ← Quitamos total_plantas
        ]
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: C-001'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre descriptivo'}),
            'ubicacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'variedad': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_planta': forms.TextInput(attrs={'class': 'form-control'}),
            'año_plantacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 2000, 'max': 2030}),
            'tipo_riego': forms.Select(attrs={'class': 'form-control'}),
            'estado_cultivo': forms.Select(attrs={'class': 'form-control'}),
            'area_hectareas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'plantas_vivas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'plantas_muertas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'numero': 'Número único de cuartel *',
            'nombre': 'Nombre del cuartel *',
            'año_plantacion': 'Año de plantación *',
        }

    def clean_numero(self):
        numero = self.cleaned_data['numero']
        if Cuartel.objects.filter(numero=numero).exists():
            if not self.instance or self.instance.numero != numero:
                raise forms.ValidationError("Este número de cuartel ya existe.")
        return numero

    def save(self, commit=True):
        # Calcular automáticamente el total de plantas
        instance = super().save(commit=False)
        instance.total_plantas = (instance.plantas_vivas or 0) + (instance.plantas_muertas or 0)
        
        if commit:
            instance.save()
        return instance

class SeguimientoCuartelForm(forms.ModelForm):
    class Meta:
        model = SeguimientoCuartel
        fields = ['fecha_seguimiento', 'plantas_vivas_registro', 'plantas_muertas_registro', 'observaciones']
        widgets = {
            'fecha_seguimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'plantas_vivas_registro': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'plantas_muertas_registro': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }