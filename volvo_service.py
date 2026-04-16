import json
import time
import logging
import requests
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import paho.mqtt.publish as publish
import base64
import hashlib
import secrets
import os

# Load config
with open('config.json') as f:
    config = json.load(f)

# Setup logging
logging.basicConfig(filename='logs/volvo_service.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_pkce():
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip('=')
    return code_verifier, code_challenge

def start_oauth():
    code_verifier, code_challenge = generate_pkce()
    params = {
        'response_type': 'code',
        'client_id': config['client_id'],
        'redirect_uri': 'https://volvo-service.local',  # dummy redirect URI
        'scope': (
            'openid '
            'conve:battery_charge_level conve:vehicle_relation conve:engine_status '
            'conve:doors_status conve:lock_status conve:odometer_status '
            'conve:tyre_status conve:windows_status conve:fuel_status '
            'energy:state:read location:read'
        ),
        'state': 'state123',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }
    url = 'https://volvoid.eu.volvocars.com/as/authorization.oauth2'
    full_url = requests.Request('GET', url, params=params).prepare().url
    print(f"Visit this URL to authenticate: {full_url}")
    print("After login and OTP validation, you will be redirected to http://localhost?code=... Copy the 'code' parameter.")
    print("Save the code to otp.txt file in the service directory.")
    return code_verifier

def wait_for_otp():
    while not os.path.exists('otp.txt'):
        time.sleep(1)
    with open('otp.txt') as f:
        code = f.read().strip()
    os.remove('otp.txt')
    return code

def exchange_code(code, code_verifier):
    data = {
        'grant_type': 'authorization_code',
        'code': code.strip(), 
        'code': code,
        'redirect_uri': 'https://volvo-service.local',
        'code_verifier': code_verifier,
        'client_id': config['client_id'],
        'client_secret': config['client_secret']
    }
    # La vcc-api-key est obligatoire ici pour éviter le 403
    headers = {
        'vcc-api-key': config['vcc_api_key'],
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(
        'https://volvoid.eu.volvocars.com/as/token.oauth2', 
        data=data, 
        headers=headers
    )
    
    response.raise_for_status()
    tokens = response.json()
    tokens['expires_at'] = time.time() + tokens['expires_in']
    with open('tokens.json', 'w') as f:
        json.dump(tokens, f)
    logging.info("Tokens obtained and saved")
    return tokens


def refresh_token():
    with open('tokens.json') as f:
        tokens = json.load(f)
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token']
    }
    auth = (config['client_id'], config['client_secret'])
    response = requests.post('https://volvoid.eu.volvocars.com/as/token.oauth2', data=data, auth=auth)
    response.raise_for_status()
    new_tokens = response.json()
    new_tokens['expires_at'] = time.time() + new_tokens['expires_in']
    with open('tokens.json', 'w') as f:
        json.dump(new_tokens, f)
    logging.info("Tokens refreshed")
    return new_tokens

def get_access_token():
    with open('tokens.json') as f:
        tokens = json.load(f)
    if time.time() > tokens['expires_at'] - 300:  # Refresh 5 minutes before expiry
        tokens = refresh_token()
    return tokens['access_token']

def fetch_vehicle_data(vin):
    token = get_access_token()
    headers = {
        'accept': 'application/json',
        'vcc-api-key': config['vcc_api_key'],
        'authorization': f'Bearer {token}'
    }
    data = {}
    base_url = f'https://api.volvocars.com/connected-vehicle/v2/vehicles/{vin}'

    # Liste complète des points d'accès basés sur vos scopes
    endpoints = {
        'doors': '/doors',
        'windows': '/windows',
        'tyres': '/tyres',
        'engine': '/engine-status',
        'odometer': '/odometer',
        'fuel': '/fuel',
        'brakes': '/brakes',
        'warnings': '/warnings',
        'diagnostics': '/diagnostics',
        'commands': '/commands',
        'location': '/location',
        'environment': '/environment',
        'statistics': '/statistics',  # Très probable pour le range essence
        'trips': '/trips' 
    }
        # Ajoute ces lignes dans ta boucle d'endpoints ou à la fin
    additional_endpoints = {
        'location': '/location',
        'statistics': '/statistics',
        'connectivity': '/connectivity-status',
        'environment': '/environment'
    }

    for key, path in additional_endpoints.items():
        try:
            r = requests.get(f"{base_url}{path}", headers=headers)
            if r.status_code == 200:
                data[key] = r.json().get('data', {})
                print(f"DEBUG {key.upper()}: {data[key]}", flush=True)
        except Exception: pass

     # Récupération des infos de base
    try:
        r = requests.get(base_url, headers=headers)
        if r.status_code == 200: data.update(r.json().get('data', {}))
    except Exception: pass

    for key, path in endpoints.items():
        try:
            r = requests.get(f"{base_url}{path}", headers=headers)
            if r.status_code == 200:
                res_json = r.json().get('data', {})
                if key == 'base': data.update(res_json)
                else: data[key] = res_json
            else:
                 print(f"Échec sur {key}: Code {r.status_code}", flush=True)
        except Exception as e:
            print(f"Erreur sur {key}: {e}")
    

     # Appel spécifique pour la LOCALISATION (en v1 selon ta doc)
    location_url = f'https://api.volvocars.com/location/v1/vehicles/{vin}/location'
    try:
        r_loc = requests.get(location_url, headers=headers)
        if r_loc.status_code == 200:
            data['location'] = r_loc.json().get('data', {})
            print("Succès : Position GPS récupérée !", flush=True)
        else:
            print(f"Info Location : Code {r_loc.status_code}", flush=True)
    except Exception as e:
        print(f"Exception Location : {e}")

    # On interroge d'abord les capacités (pour réveiller l'API)
    cap_energy_url = f'https://api.volvocars.com/energy/v2/vehicles/{vin}/capabilities'
    try:
        r_cap = requests.get(cap_energy_url, headers=headers)
       # if r_cap.status_code == 200:
           # print(f"DEBUG CAPABILITIES: {r_cap.json()}", flush=True)
    except Exception as e:
        print(f"Erreur Capabilities: {e}")

    # 2. Appel pour l'ÉNERGIE (Batterie) - Basé sur ta doc
    energy_url = f'https://api.volvocars.com/energy/v2/vehicles/{vin}/state'
    try:
        r_energy = requests.get(energy_url, headers=headers)
        if r_energy.status_code == 200:
            res = r_energy.json()
            # On stocke les données brutes
            data['energy'] = res.get('data', res)
            #print(f"DEBUG ENERGY DATA: {data['energy']}", flush=True)
    except Exception as e:
        print(f"Exception Energy : {e}")

    return data


import paho.mqtt.publish as publish

def publish_mqtt(data):
    vin = config['vin']
    msgs = []
    
        # --- Section Énergie (Batterie & Charge) ---
    if 'energy' in data:
        e = data['energy']
        
        # Niveau et Autonomie
        lvl = e.get('batteryChargeLevel', {}).get('value')
        rng = e.get('electricRange', {}).get('value')
        if lvl is not None: msgs.append({'topic': f'volvo/{vin}/battery/level', 'payload': str(lvl), 'retain': True})
        if rng is not None: msgs.append({'topic': f'volvo/{vin}/battery/range', 'payload': str(rng), 'retain': True})
        
        # État de la charge (Branché ? En charge ?)
        conn = e.get('chargerConnectionStatus', {}).get('value')
        stat = e.get('chargingStatus', {}).get('value')
        target = e.get('targetBatteryChargeLevel', {}).get('value')
        
        if conn: msgs.append({'topic': f'volvo/{vin}/battery/connected', 'payload': str(conn), 'retain': True})
        if stat: msgs.append({'topic': f'volvo/{vin}/battery/charging_status', 'payload': str(stat), 'retain': True})
        if target: msgs.append({'topic': f'volvo/{vin}/battery/target_limit', 'payload': str(target), 'retain': True})


        # --- Kilométrage (Odometer) ---
    if 'odometer' in data:
        # On suit la structure vue dans ton debug : odometer -> odometer -> value
        odo_val = data['odometer'].get('odometer', {}).get('value')
        if odo_val is not None:
            msgs.append({'topic': f'volvo/{vin}/info/odometer', 'payload': str(odo_val), 'retain': True})

   
        # --- Essence (Fuel) ---
    if 'fuel' in data:
        lvl = data['fuel'].get('fuelAmount', {}).get('value')
        if lvl is not None:
            msgs.append({'topic': f'volvo/{vin}/fuel/level', 'payload': str(lvl), 'retain': True})

    # --- Freins (Brakes) ---
    if 'brakes' in data:
        fluid = data['brakes'].get('brakeFluidLevel', {}).get('value')
        msgs.append({'topic': f'volvo/{vin}/brakes/fluid', 'payload': str(fluid), 'retain': True})
    # --- Température Extérieure (Environment) ---
    if 'environment' in data:
        temp = data['environment'].get('externalTemperature', {}).get('value')
        if temp: msgs.append({'topic': f'volvo/{vin}/environment/external_temp', 'payload': str(temp), 'retain': True})

    # --- Diagnostics & Connectivité ---
    if 'connectivity' in data:
        conn = data['connectivity'].get('connectivityStatus', {}).get('value')
        msgs.append({'topic': f'volvo/{vin}/status/connectivity', 'payload': str(conn), 'retain': True})

    if 'diagnostics' in data:
        # On publie l'état général des diagnostics
        for diag, status in data['diagnostics'].items():
            val = status.get('value') if isinstance(status, dict) else status
            msgs.append({'topic': f'volvo/{vin}/diagnostics/{diag}', 'payload': str(val), 'retain': True})

    # --- Climatisation ---
    if 'climatization' in data:
        state = data['climatization'].get('climatizationStatus', {}).get('value')
        msgs.append({'topic': f'volvo/{vin}/climatization/status', 'payload': str(state), 'retain': True})
        # --- Infos Statiques ---
    for field in ['modelYear', 'gearbox', 'fuelType', 'externalColour', 'batteryCapacityKWH']:
        if field in data:
            msgs.append({'topic': f'volvo/{vin}/info/{field}', 'payload': str(data[field]), 'retain': True})

        # --- Localisation (GPS) ---
    if 'location' in data:
        # Structure GeoJSON : [longitude, latitude, altitude]
        coords = data['location'].get('geometry', {}).get('coordinates', [])
        
        if len(coords) >= 2:
            lon = coords[0]
            lat = coords[1]
            msgs.append({'topic': f'volvo/{vin}/location/lat', 'payload': str(lat), 'retain': True})
            msgs.append({'topic': f'volvo/{vin}/location/lon', 'payload': str(lon), 'retain': True})
            
        # Optionnel : On récupère aussi l'orientation (heading)
        heading = data['location'].get('properties', {}).get('heading')
        if heading:
            msgs.append({'topic': f'volvo/{vin}/location/heading', 'payload': str(heading), 'retain': True})

    # --- Température (Environment) ---
    if 'environment' in data:
        temp = data['environment'].get('externalTemperature', {}).get('value')
        if temp:
            msgs.append({'topic': f'volvo/{vin}/environment/temp_ext', 'payload': str(temp), 'retain': True})

    # --- Boucle pour Doors, Windows, Tyres (déjà fonctionnelle) ---
    for key in ['doors', 'windows', 'tyres']:
        if key in data:
            for item, status in data[key].items():
                val = status.get('value') if isinstance(status, dict) else status
                msgs.append({'topic': f'volvo/{vin}/{key}/{item}', 'payload': str(val), 'retain': True})

    if msgs:
        publish.multiple(msgs, hostname=config['mqtt_host'], port=config['mqtt_port'])

def main():
    print("--- Démarrage du script Volvo-Service ---", flush=True)
    
    # 1. Vérification / Authentification
    token_file = 'tokens.json'
    needs_auth = True
    
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                t = json.load(f)
                if t.get('access_token'):
                    needs_auth = False
                    print("Token trouvé, passage à la boucle de données.", flush=True)
        except Exception:
            pass

    if needs_auth:
        print("Aucun token valide. Lancement de l'authentification...", flush=True)
        code_verifier = start_oauth()
        code = wait_for_otp()
        exchange_code(code, code_verifier)
    
    # 2. Boucle de récupération
    print(f"Début de la boucle (intervalle: {config['polling_interval_seconds']}s)", flush=True)
    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Récupération des données pour {config['vin']}...", flush=True)
            data = fetch_vehicle_data(config['vin'])
            
            if data:
                print(f"Données reçues (clés: {list(data.keys())}). Envoi MQTT...", flush=True)
                publish_mqtt(data)
                logging.info("Vehicle data fetched and published to MQTT")
            else:
                print("Attention: Volvo a renvoyé des données vides.", flush=True)
                
        except Exception as e:
            print(f"ERREUR dans la boucle: {e}", flush=True)
            logging.error(f"Error in main loop: {e}")
        
        print(f"Sommeil pour {config['polling_interval_seconds']} secondes...", flush=True)
        time.sleep(config['polling_interval_seconds'])

if __name__ == '__main__':
    main()