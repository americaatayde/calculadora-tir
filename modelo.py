"""Modelo de bonos traducido de TIR_Duración_campus_2627.xlsx."""
from calendar import monthrange
from datetime import date
from math import exp, log1p, fsum, isfinite


def validar(nominal, tasa_cupon):
    if not isfinite(nominal) or nominal <= 0:
        raise ValueError('El nominal debe ser positivo.')
    if not isfinite(tasa_cupon) or tasa_cupon < 0:
        raise ValueError('La tasa de cupón debe ser cero o positiva.')


def por_periodos(nominal, tasa_cupon, frecuencia, periodo_valoracion, amortizacion):
    validar(nominal, tasa_cupon)
    if frecuencia not in (1, 2, 4, 12):
        raise ValueError('Frecuencia no válida.')
    n = amortizacion - periodo_valoracion
    if n < 1 or int(n) != n or n > 1000:
        raise ValueError('Deben quedar entre 1 y 1000 periodos completos.')
    cupon = nominal * tasa_cupon / frecuencia
    flujos = [{'Periodo': k, 'Tiempo': float(k), 'Cupón': cupon,
               'Capital': nominal if k == n else 0.0} for k in range(1, int(n) + 1)]
    return flujos, 0.0


def desplazar_anios(fecha, anios):
    year = fecha.year + anios
    # Calendario anual anclado al vencimiento; conserva fin de mes.
    fin_mes = fecha.day == monthrange(fecha.year, fecha.month)[1]
    ultimo = monthrange(year, fecha.month)[1]
    return date(year, fecha.month, ultimo if fin_mes else min(fecha.day, ultimo))


def por_fechas(nominal, tasa_cupon, valoracion, ultimo, proximo, vencimiento):
    validar(nominal, tasa_cupon)
    if not ultimo <= valoracion < proximo <= vencimiento:
        raise ValueError('Se requiere: último cupón ≤ valoración < próximo cupón ≤ vencimiento.')
    fechas = []
    for i in range(101):
        d = desplazar_anios(vencimiento, -i)
        if d <= valoracion:
            break
        fechas.append(d)
    else:
        raise ValueError('El plazo máximo es de 100 años.')
    fechas.reverse()
    if not fechas or fechas[0] != proximo or desplazar_anios(vencimiento, -len(fechas)) != ultimo:
        raise ValueError('Las fechas de cupón deben coincidir con el calendario anual del vencimiento.')
    dias = (proximo - ultimo).days
    fraccion = (proximo - valoracion).days / dias
    cupon = nominal * tasa_cupon
    corrido = cupon * (valoracion - ultimo).days / dias
    flujos = [{'Periodo': k + 1, 'Fecha': d, 'Tiempo': fraccion + k,
               'Cupón': cupon, 'Capital': nominal if d == vencimiento else 0.0}
              for k, d in enumerate(fechas)]
    return flujos, corrido


def precio(flujos, tir):
    if not isfinite(tir) or tir <= -1:
        raise ValueError('La TIR por periodo debe ser mayor que -100 %.')
    return fsum((f['Cupón'] + f['Capital']) * exp(-f['Tiempo'] * log1p(tir)) for f in flujos)


def resolver_tir(flujos, precio_total):
    if not isfinite(precio_total) or precio_total <= 0:
        raise ValueError('El precio total debe ser positivo.')
    # Resolver en log(1+TIR) evita limitar artificialmente tasas negativas o altas.
    def pv(x):
        try:
            return fsum((f['Cupón'] + f['Capital']) * exp(-f['Tiempo'] * x) for f in flujos)
        except OverflowError:
            return float('inf')
    lo, hi = -1.0, 1.0
    while pv(lo) < precio_total:
        lo *= 2
    while pv(hi) > precio_total:
        hi *= 2
    for _ in range(220):
        mid = (lo + hi) / 2
        if pv(mid) > precio_total:
            lo = mid
        else:
            hi = mid
    from math import expm1
    try:
        tir = expm1((lo + hi) / 2)
    except OverflowError:
        raise ValueError('La TIR excede la capacidad numérica; revisa el precio.')
    if tir <= -1 or not isfinite(tir):
        raise ValueError('La TIR excede la precisión numérica; revisa los datos.')
    return tir


def detalle(flujos, tir):
    return [dict(f, **{'Pago total': f['Cupón'] + f['Capital'],
                      'Valor presente': (f['Cupón'] + f['Capital']) * exp(-f['Tiempo'] * log1p(tir))})
            for f in flujos]
