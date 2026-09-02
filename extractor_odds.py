import requests
import streamlit as st

# Leer la API Key de forma segura desde los Secrets de Streamlit
API_KEY = st.secrets["ODDS_API_KEY"]
SPORT = "baseball_mlb"
REGIONS = "us"

def convertir_americano_a_decimal(odds_americano):
    if odds_americano > 0:
        return round((odds_americano / 100) + 1, 2)
    else:
        return round((100 / abs(odds_americano)) + 1, 2)

def obtener_momios_f5():
    """
    Consulta The-Odds-API para obtener cuotas específicas de F5 (1st 5 innings).
    Si no están disponibles, intenta con el mercado h2h general.
    """
    # Intentar primero con el mercado de Primeros 5 Innings
    markets_to_try = ["h2h_1st_5_innings", "h2h"]
    dict_momios = {}

    for market in markets_to_try:
        url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={market}&oddsFormat=american"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue

            data = response.json()
            if not data:
                continue

            for game in data:
                home_team = game.get('home_team')
                away_team = game.get('away_team')

                # Evitar sobrescribir si ya obtuvimos el dato de F5 en la primera iteración
                if home_team in dict_momios:
                    continue

                bookmakers = game.get('bookmakers', [])
                if not bookmakers:
                    continue

                markets = bookmakers[0].get('markets', [])
                if not markets:
                    continue

                outcomes = markets[0].get('outcomes', [])
                momio_home, momio_away = None, None

                for outcome in outcomes:
                    if outcome['name'] == home_team:
                        momio_home = outcome['price']
                    elif outcome['name'] == away_team:
                        momio_away = outcome['price']

                if momio_home and momio_away:
                    dict_momios[home_team] = {
                        'momio_amer': momio_home,
                        'momio_dec': convertir_americano_a_decimal(momio_home)
                    }
                    dict_momios[away_team] = {
                        'momio_amer': momio_away,
                        'momio_dec': convertir_americano_a_decimal(momio_away)
                    }

        except Exception as e:
            print(f"Error al consultar el mercado {market}: {e}")

    return dict_momios