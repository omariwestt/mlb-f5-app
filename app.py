import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from extractor_mlb import obtener_partidos_dia
from extractor_odds import obtener_momios_f5
from generar_excel import calcular_probabilidad_f5

st.set_page_config(page_title="MLB F5 Predictor", page_icon="⚾", layout="wide")

# Estructura de pestañas principales
tab_hoy, tab_historial = st.tabs(["⚾ Pronósticos de Hoy", "📜 Probador Histórico (Backtest)"])

# ==========================================
# PESTAÑA 1: PRONÓSTICOS DEL DÍA
# ==========================================
with tab_hoy:
    st.title("⚾ MLB F5 Analytics & +EV Predictor")
    st.write("Sistema de predicción para el mercado Primeros 5 Innings (F5)")

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

        def resaltar_ev(val):
            if val >= 8.0:
                return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val >= 3.0:
                return 'background-color: #fff3cd; color: #856404;'
            return ''

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

# ==========================================
# PESTAÑA 2: PROBADOR HISTÓRICO (BACKTEST)
# ==========================================
with tab_historial:
    st.title("📜 Evaluación de Resultados Pasados")
    st.write("Selecciona una fecha anterior para comparar las predicciones del algoritmo contra los marcadores reales F5.")

    fecha_seleccionada = st.date_input("Selecciona la fecha a evaluar:", datetime.today() - timedelta(days=1))
    fecha_str = fecha_seleccionada.strftime('%Y-%m-%d')

    if st.button("🔎 Evaluar Fecha"):
        with st.spinner(f"Evaluando rendimiento del {fecha_str}..."):
            df_pred = obtener_partidos_dia(fecha_str)
            
            if df_pred is None or df_pred.empty:
                st.warning("No se encontraron datos o partidos para esa fecha.")
            else:
                url_mlb = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha_str}&hydrate=linescore"
                res = requests.get(url_mlb)
                datos = res.json()
                
                resultados_reales = {}
                dates = datos.get('dates', [])
                if dates:
                    for game in dates[0].get('games', []):
                        if game['status']['detailedState'] in ['Final', 'Completed Early']:
                            visita = game['teams']['away']['team']['name']
                            local = game['teams']['home']['team']['name']
                            innings = game.get('linescore', {}).get('innings', [])[:5]
                            
                            runs_vis = sum(i.get('away', {}).get('runs', 0) for i in innings)
                            runs_loc = sum(i.get('home', {}).get('runs', 0) for i in innings)
                            
                            ganador = local if runs_loc > runs_vis else (visita if runs_vis > runs_loc else "Empate F5")
                            resultados_reales[f"{visita} vs {local}"] = {
                                'ganador': ganador,
                                'score': f"{runs_vis}-{runs_loc}"
                            }

                evaluaciones = []
                aciertos, empates, total = 0, 0, 0

                for _, row in df_pred.iterrows():
                    rec_f5, prob = calcular_probabilidad_f5(row)
                    llave = f"{row['Visitante']} vs {row['Local']}"
                    info_real = resultados_reales.get(llave)

                    if info_real:
                        total += 1
                        ganador_real = info_real['ganador']
                        score = info_real['score']

                        if ganador_real == rec_f5:
                            estado = "✅ GANADA"
                            aciertos += 1
                        elif ganador_real == "Empate F5":
                            estado = "⚪ EMPATE (Push)"
                            empates += 1
                        else:
                            estado = "❌ PERDIDA"

                        evaluaciones.append({
                            'Partido': llave,
                            'Recomendación F5': rec_f5,
                            'Resultado Real': f"{estado} ({score})"
                        })

                if total > 0:
                    validos = total - empates
                    winrate = round((aciertos / validos) * 100, 1) if validos > 0 else 0
                    
                    st.success(f"**Efectividad Real F5:** `{winrate}%` ({aciertos} Ganadas | {total - aciertos - empates} Perdidas | {empates} Empates)")
                    st.dataframe(pd.DataFrame(evaluaciones), use_container_width=True, hide_index=True)
                else:
                    st.error("No hay marcadores o datos disponibles para la fecha seleccionada.")