import requests
import pandas as pd
from datetime import datetime

from datetime import timedelta

def obtener_racha_equipo(team_id):
    """
    Obtiene el récord exacto de victorias y derrotas en los últimos 10 partidos del equipo.
    """
    if not team_id:
        return "5-5", 5

    # Consultamos los últimos 20 días para asegurar obtener al menos 10 juegos concluidos
    hoy = datetime.today()
    hace_20_dias = hoy - timedelta(days=20)
    
    fecha_inicio = hace_20_dias.strftime('%Y-%m-%d')
    fecha_fin = hoy.strftime('%Y-%m-%d')

    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId={team_id}&startDate={fecha_inicio}&endDate={fecha_fin}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            dates = response.json().get('dates', [])
            wins = 0
            total_juegos = 0
            
            # Recorremos los días de más reciente a más antiguo
            for d in reversed(dates):
                for g in d.get('games', []):
                    # Solo contamos juegos finalizados de temporada regular
                    if g['status']['detailedState'] in ['Final', 'Completed Early'] and g.get('gameType') == 'R':
                        is_home = (g['teams']['home']['team']['id'] == team_id)
                        side = 'home' if is_home else 'away'
                        opp_side = 'away' if is_home else 'home'
                        
                        score_team = g['teams'][side].get('score', 0)
                        score_opp = g['teams'][opp_side].get('score', 0)
                        
                        if score_team > score_opp:
                            wins += 1
                        total_juegos += 1
                        
                        if total_juegos == 10:
                            break
                if total_juegos == 10:
                    break
            
            if total_juegos > 0:
                losses = total_juegos - wins
                return f"{wins}-{losses}", wins
    except Exception:
        pass

    return "5-5", 5

def obtener_stats_pitcher(pitcher_id):
    """
    Obtiene ERA, WHIP y calcula el FIP aproximado de la temporada.
    """
    if not pitcher_id:
        return {'ERA': 4.50, 'WHIP': 1.30, 'xFIP': 4.30}

    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}?hydrate=stats(group=[pitching],type=[season])"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            people = response.json().get('people', [])
            if people and people[0].get('stats'):
                stat = people[0]['stats'][0]['splits'][0]['stat']
                era = float(stat.get('era', 4.50))
                whip = float(stat.get('whip', 1.30))
                ip = float(stat.get('inningsPitched', 0.0))
                k = int(stat.get('strikeOuts', 0))
                bb = int(stat.get('baseOnBalls', 0))
                hr = int(stat.get('homeRuns', 0))

                fip = round(((13 * hr) + (3 * bb) - (2 * k)) / ip + 3.20, 2) if ip > 0 else era
                return {'ERA': era, 'WHIP': whip, 'xFIP': fip}
    except Exception:
        pass

    return {'ERA': 4.50, 'WHIP': 1.30, 'xFIP': 4.30}

def obtener_partidos_dia(fecha=None):
    """
    Consulta partidos, abridores y rachas recientes.
    """
    if fecha is None:
        fecha = datetime.today().strftime('%Y-%m-%d')
    
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={fecha}&hydrate=probablePitcher,team"
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error al conectar con la API de MLB. Código HTTP: {response.status_code}")
        return None

    dates = response.json().get('dates', [])
    if not dates:
        print(f"No hay partidos programados para la fecha {fecha}.")
        return None

    games = dates[0].get('games', [])
    lista_partidos = []

    print("Extrayendo estadísticas de abridores y rachas recientes...")

    for game in games:
        # Datos Visita
        visita = game['teams']['away']['team']['name']
        id_team_vis = game['teams']['away']['team']['id']
        pitcher_vis_obj = game['teams']['away'].get('probablePitcher', {})
        pitcher_visita = pitcher_vis_obj.get('fullName', 'Por confirmar')
        stats_vis = obtener_stats_pitcher(pitcher_vis_obj.get('id'))
        racha_str_vis, v_vis = obtener_racha_equipo(id_team_vis)

        # Datos Local
        local = game['teams']['home']['team']['name']
        id_team_loc = game['teams']['home']['team']['id']
        pitcher_loc_obj = game['teams']['home'].get('probablePitcher', {})
        pitcher_local = pitcher_loc_obj.get('fullName', 'Por confirmar')
        stats_loc = obtener_stats_pitcher(pitcher_loc_obj.get('id'))
        racha_str_loc, v_loc = obtener_racha_equipo(id_team_loc)

        # Hora
        game_date_utc = datetime.strptime(game['gameDate'], '%Y-%m-%dT%H:%M:%SZ')
        hora_str = game_date_utc.strftime('%H:%M UTC')

        lista_partidos.append({
            'Hora': hora_str,
            'Visitante': visita,
            'Racha_Vis': racha_str_vis,
            'V_Vis_L10': v_vis,
            'P_Visita': pitcher_visita,
            'FIP_Vis': stats_vis['xFIP'],
            'WHIP_Vis': stats_vis['WHIP'],
            'Local': local,
            'Racha_Loc': racha_str_loc,
            'V_Loc_L10': v_loc,
            'P_Local': pitcher_local,
            'FIP_Loc': stats_loc['xFIP'],
            'WHIP_Loc': stats_loc['WHIP']
        })

    return pd.DataFrame(lista_partidos)