import streamlit as st
import pandas as pd
from datetime import datetime
from extractor_mlb import obtener_partidos_dia
from extractor_odds import obtener_momios_f5
from generar_excel import calcular_probabilidad_f5

st.set_page_config(page_title="MLB F5 Predictor", page_icon="⚾", layout="wide")

st.title("⚾ MLB F5 Analytics & +EV Predictor")
st.write("Sistema de predicción para el mercado Primeros 5 Innings (F5)")

# Botón para actualizar datos
if st.button("🔄 Cargar / Actualizar Partidos de Hoy"):
    st.cache_data.clear()

fecha_hoy = datetime.today().strftime('%Y-%m-%d')

with st.spinner("Consultando APIs de MLB y The-Odds-API..."):
    df = obtener_partidos_dia(fecha_hoy)

if df is None or df.empty:
    st.warning("No hay partidos programados o disponibles para hoy.")
else:
    dict_odds = obtener_momios_f5()
    resultados = []

    for _, row in df.iterrows():
        equipo_f5, prob_est = calcular_probabilidad_f5(row)
        datos_odds = dict_odds.get(equipo_f5, {'momio_amer': -110, 'momio_dec': 1.91})
        momio_amer = datos_odds['momio_amer']
        momio_dec = datos_odds['momio_dec']
        
        prob_imp = round((1 / momio_dec) * 100, 1)
        ev_val = round(prob_est - prob_imp, 1)

        resultados.append({
            'Hora': row['Hora'],
            'Visitante': row['Visitante'],
            'L10 Vis': row['Racha_Vis'],
            'Pitcher Vis': row['P_Visita'],
            'Local': row['Local'],
            'L10 Loc': row['Racha_Loc'],
            'Pitcher Loc': row['P_Local'],
            'Recomendación F5': equipo_f5,
            'Prob Modelo (%)': prob_est,
            'Momio Amer': momio_amer if momio_amer else "-110",
            'Momio Dec': momio_dec,
            'Prob Casa (%)': prob_imp,
            '+EV (%)': ev_val
        })

    df_res = pd.DataFrame(resultados).sort_values(by='+EV (%)', ascending=False)

    # --- RECUADRO TOP 3 PARLAY ---
    top_3 = df_res.head(3)
    if len(top_3) == 3:
        st.subheader("🔥 Parlay Sugerido del Día (Top 3 +EV)")
        cols = st.columns(3)
        cuota_parlay = 1.0
        prob_parlay = 1.0

        for i, (_, row) in enumerate(top_3.iterrows()):
            cuota_parlay *= row['Momio Dec']
            prob_parlay *= (row['Prob Modelo (%)'] / 100.0)
            with cols[i]:
                st.metric(
                    label=f"Selección {i+1}", 
                    value=f"{row['Recomendación F5']} (F5)", 
                    delta=f"+EV: {row['+EV (%)']}% | Momio: {row['Momio Amer']}"
                )

        st.info(f"**Cuota Total Combinada:** `{round(cuota_parlay, 2)}` | **Probabilidad Conjunta:** `{round(prob_parlay * 100, 1)}%`")

    st.markdown("---")
    st.subheader("📊 Tabla de Partidos y Opciones de Valor (+EV)")

    # Función para dar color en Streamlit
    def resaltar_ev(val):
        if val >= 8.0:
            return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif val >= 3.0:
            return 'background-color: #fff3cd; color: #856404;'
        return ''

    df_display = df_res.drop(columns=['Momio Dec'])
    # Dar formato limpio a los números
    df_clean = df_res.drop(columns=['Momio Dec']).copy()
    
    st.dataframe(
        df_clean.style.map(resaltar_ev, subset=['+EV (%)'])
                .format({
                    'Prob Modelo (%)': '{:.1f}%',
                    'Prob Casa (%)': '{:.1f}%',
                    '+EV (%)': '{:.1f}%'
                }),
        use_container_width=True,
        hide_index=True,
        height=500
    )