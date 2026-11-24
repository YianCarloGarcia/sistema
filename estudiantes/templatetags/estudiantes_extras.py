from django import template

from estudiantes.views import _es_directivo

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Permite hacer dictionary[key] dentro de una plantilla, con clave dinámica."""
    if not dictionary:
        return None
    return dictionary.get(key)


@register.filter
def contains(contenedor, item):
    """True si item está en contenedor (soporta sets, listas o None)."""
    if not contenedor:
        return False
    return item in contenedor


@register.filter
def es_directivo(usuario):
    """Aplica la misma verificación de permisos que usan las vistas (no adivina
    el rol mirando el primer grupo de la lista, que es un orden no garantizado)."""
    return _es_directivo(usuario)


@register.filter
def etiqueta_grado(valor):
    """'10' -> '10°'; 'OT' -> 'Solo OT'; 'OT-1001' -> 'OT · curso 1001'."""
    valor = str(valor or '')
    if valor == 'OT':
        return 'Solo OT (sin línea)'
    if valor.startswith('OT-'):
        return f'OT · curso {valor[3:]}'
    return f'{valor}°' if valor else ''
