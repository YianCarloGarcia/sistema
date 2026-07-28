from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Permite hacer dictionary[key] dentro de una plantilla, con clave dinámica."""
    if not dictionary:
        return None
    return dictionary.get(key)
