"""Perfil del docente: datos personales, fotografía y contraseña."""
from django import forms
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .views import _es_docente, _es_estudiante

FOTO_MAX_MB = 3


class PerfilDocenteForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {'first_name': 'Nombres', 'last_name': 'Apellidos', 'email': 'Correo electrónico'}
        widgets = {c: forms.TextInput(attrs={'class': 'form-control'}) for c in ('first_name', 'last_name')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['class'] = 'form-control'
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class FotoDocenteForm(forms.Form):
    foto = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))
    quitar = forms.BooleanField(required=False)

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and foto.size > FOTO_MAX_MB * 1024 * 1024:
            raise forms.ValidationError(f'La fotografía no puede superar {FOTO_MAX_MB} MB.')
        return foto


def _borrar_foto(perfil):
    if perfil.foto and perfil.foto.name:
        try:
            perfil.foto.storage.delete(perfil.foto.name)
        except Exception:
            pass


@login_required
def mi_perfil(request):
    user = request.user
    if _es_estudiante(user) or not _es_docente(user):
        return redirect('inicio')

    perfil = getattr(user, 'docente_perfil', None)
    accion = request.POST.get('accion') if request.method == 'POST' else None

    datos = PerfilDocenteForm(request.POST if accion == 'datos' else None, instance=user)
    foto_form = FotoDocenteForm(request.POST if accion == 'foto' else None,
                                request.FILES if accion == 'foto' else None)
    clave = PasswordChangeForm(user, request.POST if accion == 'clave' else None)
    for c in clave.fields.values():
        c.widget.attrs['class'] = 'form-control'

    if accion == 'datos' and datos.is_valid():
        datos.save()
        messages.success(request, 'Datos actualizados.')
        return redirect('mi_perfil')

    if accion == 'foto' and perfil is not None and foto_form.is_valid():
        nueva = foto_form.cleaned_data['foto']
        if nueva:
            _borrar_foto(perfil)
            perfil.foto = nueva
            perfil.save()
            messages.success(request, 'Fotografía actualizada.')
        elif foto_form.cleaned_data['quitar'] and perfil.foto:
            _borrar_foto(perfil)
            perfil.foto = None
            perfil.save()
            messages.success(request, 'Fotografía eliminada.')
        else:
            messages.info(request, 'Selecciona una imagen primero.')
        return redirect('mi_perfil')

    if accion == 'clave' and clave.is_valid():
        user = clave.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Contraseña actualizada.')
        return redirect('mi_perfil')

    return render(request, 'estudiantes/mi_perfil.html', {
        'datos': datos, 'foto_form': foto_form, 'clave': clave, 'perfil': perfil, 'accion': accion,
        'foto_max': FOTO_MAX_MB,
    })
