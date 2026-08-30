from django import template

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
