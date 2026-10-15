import pandas as pd
import streamlit as st
from datetime import date
from modelo import por_periodos, por_fechas, precio, resolver_tir, detalle

st.set_page_config(page_title='Calculadora TIR y pagos', page_icon='📊', layout='wide')
st.title('Calculadora de bonos')
st.caption('TIR, precio y calendario de pagos · Basada en tu Excel de obligaciones y bonos')

with st.sidebar:
    st.header('Modelo')
    modelo = st.radio('Forma de cálculo', ['Fechas de mercado', 'Periodos completos'])
    objetivo = st.radio('¿Qué quieres calcular?', ['TIR a partir del precio', 'Precio a partir de la TIR'])
    st.caption('Los importes se expresan en la misma moneda que el nominal.')

st.subheader('Datos del bono')
c1, c2, c3 = st.columns(3)
nominal = c1.number_input('Nominal / capital al vencimiento', min_value=0.01, value=1000.0, step=100.0)
tasa = c2.number_input('Tasa de cupón anual (%)', min_value=0.0,
                       value=4.5 if modelo == 'Fechas de mercado' else 6.0, step=0.25,
                       key='cupon_' + modelo) / 100
frecuencia = 1
try:
    if modelo == 'Fechas de mercado':
        c3.write('Frecuencia: anual, como en la hoja Fecha Mercado')
        d1, d2, d3, d4 = st.columns(4)
        valoracion = d1.date_input('Fecha de valoración', value=date(2026, 4, 15))
        ultimo = d2.date_input('Último cupón cobrado', value=date(2026, 1, 31))
        proximo = d3.date_input('Próximo cupón', value=date(2027, 1, 31))
        vencimiento = d4.date_input('Vencimiento', value=date(2031, 1, 31),
                                    min_value=date(1900, 1, 1), max_value=date(2200, 12, 31))
        flujos, corrido = por_fechas(nominal, tasa, valoracion, ultimo, proximo, vencimiento)
        st.caption('Convención del Excel: primer periodo = días hasta el próximo cupón / días del periodo de cupón; los siguientes aumentan en 1. Calendario anual regular.')
    else:
        frecuencia = c3.selectbox('Cupones por año', [1, 2, 4, 12])
        d1, d2 = st.columns(2)
        r = d1.number_input('Periodo de valoración (r)', min_value=0, max_value=999, value=0)
        n = d2.number_input('Periodo de amortización (n)', min_value=1, max_value=1000, value=8)
        flujos, corrido = por_periodos(nominal, tasa, frecuencia, r, n)
        st.caption('Valoración en una fecha de cupón. Los periodos corresponden a la frecuencia seleccionada; cupón = nominal × tasa anual / frecuencia.')

    st.subheader('Variable conocida')
    if objetivo == 'TIR a partir del precio':
        tipo = st.selectbox('Tipo de precio', ['Precio ex-cupón', 'Precio total (incluye cupón corrido)'])
        conocido = st.number_input('Precio conocido (importe, no porcentaje del nominal)', min_value=0.01,
                                   value=1048.5 if modelo == 'Fechas de mercado' else 984.6279623815838,
                                   step=1.0, format='%.6f', key='precio_' + modelo)
        total = conocido + corrido if tipo == 'Precio ex-cupón' else conocido
        tir = resolver_tir(flujos, total)
    else:
        tir = st.number_input('TIR por periodo de cupón (%)', min_value=-99.0,
                              value=3.3850272175518857 if modelo == 'Fechas de mercado' else 6.25,
                              step=0.1, format='%.8f', key='tir_' + modelo) / 100
        total = precio(flujos, tir)
    limpio = total - corrido
    tabla = pd.DataFrame(detalle(flujos, tir))
    st.subheader('Resultados')
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('TIR por periodo', f'{tir * 100:,.6f} %')
    m2.metric('Precio ex-cupón', f'{limpio:,.4f}')
    m3.metric('Cupón corrido', f'{corrido:,.4f}')
    m4.metric('Precio total', f'{total:,.4f}')
    p1, p2, p3, p4 = st.columns(4)
    p1.metric('Cada cupón', f'{flujos[0]["Cupón"]:,.2f}')
    p2.metric('Pago al vencimiento', f'{tabla.iloc[-1]["Pago total"]:,.2f}')
    p3.metric('Suma de pagos futuros', f'{tabla["Pago total"].sum():,.2f}')
    p4.metric('Pagos pendientes', len(tabla))
    if frecuencia != 1:
        st.caption(f'TIR anual efectiva: {((1 + tir) ** frecuencia - 1) * 100:,.6f} % · TIR anual nominal: {tir * frecuencia * 100:,.6f} %')
    st.caption('Precio total = valor presente de los pagos. Suma de pagos futuros = cupones + capital sin descuento.')
    st.subheader('Calendario de pagos')
    st.dataframe(tabla, hide_index=True, width='stretch',
                 column_config={k: st.column_config.NumberColumn(k, format='%.4f')
                                for k in ['Tiempo', 'Cupón', 'Capital', 'Pago total', 'Valor presente']})
    st.bar_chart(tabla.set_index('Periodo')[['Cupón', 'Capital']])
    st.download_button('Descargar calendario CSV', tabla.to_csv(index=False).encode('utf-8-sig'),
                       file_name='calendario_pagos.csv', mime='text/csv')
    with st.expander('Cómo se calcula'):
        st.latex(r'P_{total}=\sum_{k=1}^{N}\frac{Cupón_k+Capital_k}{(1+TIR)^{t_k}}')
        st.write('Para calcular la TIR, la app busca la tasa que hace que el valor presente coincida con el precio total. En el modelo de fechas se descuenta con periodos fraccionarios, igual que en el Excel; no se usa XIRR.')
        st.write('El precio ex-cupón es el precio total menos el cupón corrido. El capital se devuelve completo en el último pago.')
except (ValueError, OverflowError) as error:
    st.error(str(error))
