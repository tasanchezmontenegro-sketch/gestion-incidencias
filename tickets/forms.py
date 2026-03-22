from dataclasses import field

from django import forms
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm, UserCreationForm
from .models import CustomUser, Incidencia

# 1. FORMULARIO DE PERFIL
# 1. FORMULARIO DE PERFIL (Para que el usuario edite sus propios datos)
class CustomUserChangeForm(UserChangeForm):
    password = None 
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'telefono', 'foto') 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Aplicamos Bootstrap a los campos de perfil
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.FileInput):
                field.widget.attrs['class'] = 'form-control'
        
        # 2. Lógica de seguridad: Si no es admin, no puede cambiarse el nombre/apellido
        # (Esto evita que un trabajador se cambie la identidad)
        if self.instance and self.instance.role != 'administrador':
            self.fields['first_name'].widget.attrs['readonly'] = True
            self.fields['last_name'].widget.attrs['readonly'] = True


# 2. FORMULARIO DE CONTRASEÑA
import re
from django.core.exceptions import ValidationError

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = "Contraseña actual"
        self.fields['new_password1'].label = "Nueva contraseña"
        self.fields['new_password2'].label = "Confirmar nueva contraseña"
        
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = '••••••••'
            field.help_text = None

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if len(password) < 10:
            raise ValidationError("La contraseña debe tener al menos 10 caracteres.")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Debe incluir al menos una letra mayúscula.")
        if not re.search(r'[a-z]', password):
            raise ValidationError("Debe incluir al menos una letra minúscula.")
        if not re.search(r'[0-9]', password):
            raise ValidationError("Debe incluir al menos un número.")
        if not re.search(r'[@#$%^&+=.!*?]', password):
            raise ValidationError("Debe incluir al menos un carácter especial (@#$%^&+=.!*?).")
        return password


# 3. FORMULARIO PARA CREAR INCIDENCIAS (USUARIO)
class IncidenciaForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ['categoria', 'prioridad', 'area', 'descripcion', 'imagen_adjunta']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe el problema...'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'area': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) 
        super().__init__(*args, **kwargs)
        
        # Aplicar clases de Bootstrap
        for field in self.fields.values():
            if not isinstance(field.widget, forms.FileInput):
                field.widget.attrs['class'] = 'form-control'

        if user:
            # Si el rol es usuario (trabajador), bloqueamos el área
            if user.role == 'usuario':
                # 1. Filtramos el queryset para que solo aparezca su área
                self.fields['area'].queryset = self.fields['area'].queryset.filter(id=user.area.id)
                # 2. Establecemos el valor inicial
                self.fields['area'].initial = user.area
                # 3. BLOQUEO CRÍTICO: Evita que el usuario cambie el valor en el navegador
                self.fields['area'].disabled = True


# 4. FORMULARIO PARA CERRAR INCIDENCIAS (TÉCNICO)
class IncidenciaCierreForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ['solucion_aplicada', 'evidencia_solucion']
        widgets = {
            'solucion_aplicada': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe detalladamente la solución...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        
        # ✔ Solo este obligatorio
        self.fields['solucion_aplicada'].required = True
        
        # ✔ Este opcional (CLAVE)
        self.fields['evidencia_solucion'].required = False


# 5. FORMULARIO ADMIN (CREAR Y EDITAR INCIDENCIAS)
class IncidenciaAdminForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = [
            'categoria', 'prioridad', 'area', 'descripcion', 'imagen_adjunta',
            'tecnico_asignado', 'fecha_programada_atencion', 
            'hora_programada_atencion', 'observaciones_internas', 'estado'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripción...'}),
            'observaciones_internas': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notas...'}),
            'fecha_programada_atencion': forms.DateInput(attrs={'type': 'date'}),
            'hora_programada_atencion': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Aplicar Bootstrap
        for field in self.fields.values():
            if not isinstance(field.widget, forms.FileInput):
                field.widget.attrs['class'] = 'form-control'
        
        # --- LÓGICA DE OBLIGATORIEDAD ---
        self.fields['categoria'].required = True
        self.fields['prioridad'].required = True
        self.fields['area'].required = True
        self.fields['descripcion'].required = True
        self.fields['estado'].required = False 

        # 2. BLOQUEO DE CAMPOS Y ESTADOS
        if self.instance and self.instance.pk:
            # Si ya está resuelto/cerrado, bloqueamos la gestión técnica también
            if self.instance.estado.name in ['Resuelto', 'Cerrado']:
                for f in ['tecnico_asignado', 'fecha_programada_atencion', 'hora_programada_atencion', 'estado']:
                    self.fields[f].disabled = True

            # Bloqueo de campos de origen (lectura)
            campos_lectura = ['categoria', 'prioridad', 'area', 'descripcion', 'imagen_adjunta']
            for campo in campos_lectura:
                if campo in self.fields:
                    self.fields[campo].disabled = True
        else:
            # Si es NUEVA incidencia creada por Admin, ocultamos el selector de estado
            self.fields['estado'].widget = forms.HiddenInput()

        # 3. Filtro de Técnicos
        self.fields['tecnico_asignado'].queryset = CustomUser.objects.filter(
            role__in=['tecnico', 'administrador']
        )
        self.fields['tecnico_asignado'].label_from_instance = lambda obj: (
            f"{obj.first_name} {obj.last_name}".strip() or obj.username
        ) + f" ({obj.get_role_display()})"

# 6. FORMULARIO PARA CREAR USUARIOS
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'area', 'telefono')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'