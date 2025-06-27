import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import re
from urllib.parse import urlencode  # Importação corrigida

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Configurações OAuth
MERCADOLIVRE_CLIENT_ID = os.environ.get('MERCADOLIVRE_CLIENT_ID')
MERCADOLIVRE_CLIENT_SECRET = os.environ.get('MERCADOLIVRE_CLIENT_SECRET')
MERCADOLIVRE_REDIRECT_URI = os.environ.get('MERCADOLIVRE_REDIRECT_URI')
MERCADOLIVRE_AUTH_URL = 'https://auth.mercadolibre.com/authorization'
MERCADOLIVRE_TOKEN_URL = 'https://api.mercadolibre.com/oauth/token'
MERCADOLIVRE_API_URL = 'https://api.mercadolibre.com'

# Rotas principais
@app.route('/')
def index():
    ml_connected = 'mercadolivre_access_token' in session
    return render_template('index.html', ml_connected=ml_connected)

@app.route('/oauth/mercadolivre')
def mercadolivre_auth():
    params = {
        'response_type': 'code',
        'client_id': MERCADOLIVRE_CLIENT_ID,
        'redirect_uri': MERCADOLIVRE_REDIRECT_URI,
        'state': os.urandom(16).hex(),
        'scope': 'offline_access orders_read'
    }
    session['oauth_state'] = params['state']
    return redirect(f"{MERCADOLIVRE_AUTH_URL}?{urlencode(params)}")  # Linha corrigida

@app.route('/oauth/callback/mercadolivre')
def mercadolivre_callback():
    if request.args.get('state') != session.get('oauth_state'):
        return "Erro de segurança", 403
    
    code = request.args.get('code')
    if not code:
        return "Código ausente", 400

    try:
        response = requests.post(
            MERCADOLIVRE_TOKEN_URL,
            data={
                'grant_type': 'authorization_code',
                'client_id': MERCADOLIVRE_CLIENT_ID,
                'client_secret': MERCADOLIVRE_CLIENT_SECRET,
                'code': code,
                'redirect_uri': MERCADOLIVRE_REDIRECT_URI
            },
            headers={'Accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        token_data = response.json()

        session.update({
            'mercadolivre_access_token': token_data['access_token'],
            'mercadolivre_refresh_token': token_data.get('refresh_token'),
            'mercadolivre_user_id': token_data.get('user_id')
        })

        return redirect(url_for('index'))
    except Exception as e:
        return f"Erro: {str(e)}", 500

@app.route('/process_shipment', methods=['POST'])
def process_shipment():
    if 'mercadolivre_access_token' not in session:
        return jsonify({"error": "Não autenticado"}), 401

    barcode = request.json.get('barcode', '')
    shipment_id = re.sub(r'[^0-9]', '', barcode)[-11:]  # Extrai os últimos 11 dígitos

    try:
        headers = {
            'Authorization': f'Bearer {session["mercadolivre_access_token"]}',
            'Accept': 'application/json'
        }

        # Busca o pedido relacionado ao shipment_id
        orders_response = requests.get(
            f"{MERCADOLIVRE_API_URL}/orders/search?seller={session['mercadolivre_user_id']}&q={shipment_id}",
            headers=headers,
            timeout=10
        )
        orders_response.raise_for_status()
        orders = orders_response.json().get('results', [])

        if not orders:
            return jsonify({"error": "Nenhum pedido encontrado"}), 404

        order_id = orders[0]['id']
        
        # Busca detalhes do pedido
        order_response = requests.get(
            f"{MERCADOLIVRE_API_URL}/orders/{order_id}",
            headers=headers,
            timeout=10
        )
        order_response.raise_for_status()

        return jsonify({
            "status": "success",
            "data": order_response.json()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(500)
def internal_error(error):
    return "Erro 500: Verifique os logs do servidor", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)