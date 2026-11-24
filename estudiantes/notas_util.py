"""Regla única para toda calificación del sistema: solo se admiten notas entre 0,00 y 5,00."""
from decimal import Decimal, InvalidOperation

NOTA_MIN = Decimal('0')
NOTA_MAX = Decimal('5')
MENSAJE_RANGO = 'La nota debe estar entre 0,0 y 5,0.'


def parsear_nota(texto):
    """Convierte '4,5' / '4.5' en Decimal con dos decimales.

    Devuelve None si el texto no es un número o si está FUERA del rango 0–5 (no se acota ni se
    corrige en silencio: una nota fuera de rango nunca se guarda)."""
    try:
        valor = Decimal(str(texto).strip().replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None
    if not valor.is_finite() or valor < NOTA_MIN or valor > NOTA_MAX:
        return None
    return valor.quantize(Decimal('0.01'))
