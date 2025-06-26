import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, timedelta
import re # Importar regex para extração de IDs

# Configurações do Flask
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_chave_secreta_padrao_muito_segura')

# Configurações OAuth atualizadas conforme documentação
# Usando APENAS os endpoints internacionais (100% estáveis)
MERCADOLIVRE_CLIENT_ID = os.environ.get('MERCADOLIVRE_CLIENT_ID', '427016700814141')
MERCADOLIVRE_CLIENT_SECRET = os.environ.get('MERCADOLIVRE_CLIENT_SECRET', '')
MERCADOLIVRE_REDIRECT_URI = os.environ.get('MERCADOLIVRE_REDIRECT_URI', 'https://sistema-bipagem-masterhotelaria-production.up.railway.app/oauth/callback/mercadolivre' )
MERCADOLIVRE_AUTH_URL = 'https://auth.mercadolibre.com/authorization'
MERCADOLIVRE_TOKEN_URL = 'https://api.mercadolibre.com/oauth/token'
MERCADOLIVRE_API_URL = 'https://api.mercadolibre.com'

# Headers padrão para todas as requisições do Mercado Livre
MERCADOLIVRE_HEADERS = {
    'X-Client': 'SistemaBipagem/1.0',
    'Accept': 'application/json',
    'X-Meli-Site': 'MLB'  # Força o endpoint brasileiro mesmo no domínio internacional
}

# Configuração de timeout para requisições HTTP
REQUEST_TIMEOUT = (3.05, 27 ) # 3.05s para conexão, 27s para leitura

# Variáveis de ambiente para teste de DNS (para debug, pode ser removido em produção)
# os.environ['RESOLVER_OVERRIDE'] = '1.1.1.1,8.8.8.8,208.67.222.222'

# --- Funções Auxiliares para Mercado Livre ---

def refresh_mercadolivre_token():
    """Atualiza o token de acesso usando refresh token conforme documentação"""
    if 'mercadolivre_refresh_token' not in session:
        return False
    
    data = {
        'grant_type': 'refresh_token',
        'client_id': MERCADOLIVRE_CLIENT_ID,
        'client_secret': MERCADOLIVRE_CLIENT_SECRET,
        'refresh_token': session['mercadolivre_refresh_token']
    }
    
    try:
        response = requests.post(MERCADOLIVRE_TOKEN_URL, data=data, headers=MERCADOLIVRE_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        token_data = response.json()
        
        session['mercadolivre_access_token'] = token_data['access_token']
        session['mercadolivre_refresh_token'] = token_data.get('refresh_token', session['mercadolivre_refresh_token']) # Refresh token pode não ser retornado sempre
        session['mercadolivre_expires_in'] = token_data.get('expires_in')
        session['mercadolivre_token_obtained_at'] = datetime.now().timestamp() # Atualiza o timestamp
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao renovar token do ML: {e}")
        return False

def is_mercadolivre_token_valid():
    """Verifica se o token de acesso do Mercado Livre é válido ou tenta renovar"""
    if 'mercadolivre_access_token' not in session:
        return False
    
    # Verifica se o token está perto de expirar (ex: 5 minutos antes)
    expires_at = session.get('mercadolivre_token_obtained_at', 0) + session.get('mercadolivre_expires_in', 0)
    if datetime.now().timestamp() < expires_at - 300: # 300 segundos = 5 minutos
        return True
    
    # Se expirou ou está perto de expirar, tenta renovar
    return refresh_mercadolivre_token()

def get_mercadolivre_user_info(access_token):
    """Obtém informações do usuário autenticado conforme API"""
    try:
        response = requests.get(
            f"{MERCADOLIVRE_API_URL}/users/me",
            headers={'Authorization': f'Bearer {access_token}', **MERCADOLIVRE_HEADERS},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter info do usuário ML: {e}")
        return None

def format_ml_shipment_id(input_id):
    """
    Formata o ID de envio para o padrão MLB20000XXXXXXXXXX.
    Aceita:
    - "20000XXXXXXXXXX" (13 dígitos)
    - "MLB20000XXXXXXXXXX" (16 caracteres)
    - "08311396659" (11 dígitos, sufixo de Pack ID)
    """
    input_id = input_id.strip()

    # Caso 1: Já está no formato MLB20000...
    if input_id.startswith('MLB20000') and len(input_id) == 16 and input_id[3:].isdigit():
        return input_id
    
    # Caso 2: É o formato 20000... (13 dígitos)
    if input_id.startswith('20000') and len(input_id) == 13 and input_id.isdigit():
        return f"MLB{input_id}"
    
    # Caso 3: É o formato de 11 dígitos que vem depois do 20000 (ex: 08311396659)
    if len(input_id) == 11 and input_id.isdigit():
        return f"MLB20000{input_id}"

    return None

def format_address(address_data):
    """Formata os dados de endereço para exibição."""
    if not address_data:
        return {}
    
    parts = [
        address_data.get('street_name', ''),
        str(address_data.get('street_number', '')),
        address_data.get('comment', '')
    ]
    
    full_address = " ".join(filter(None, parts)).strip()
    
    return {
        "street": full_address,
        "city": address_data.get('city', {}).get('name'),
        "state": address_data.get('state', {}).get('id'),
        "zip_code": address_data.get('zip_code'),
        "complement": address_data.get('comment')
    }

def format_product_item(item_data):
    """Formata os dados de um item de pedido."""
    if not item_data:
        return {}
    return {
        "id": item_data.get('item', {}).get('id'),
        "title": item_data.get('item', {}).get('title'),
        "quantity": item_data.get('quantity'),
        "unit_price": item_data.get('unit_price'),
        "full_unit_price": item_data.get('full_unit_price'),
        "barcode": item_data.get('item', {}).get('barcode') # Pode não existir
    }

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    ml_connected = is_mercadolivre_token_valid()
    li_connected = False # Exemplo para Loja Integrada
    
    ml_user_nickname = session.get('mercadolivre_user_nickname') if ml_connected else None

    return render_template('index.html', 
                           ml_connected=ml_connected, 
                           li_connected=li_connected,
                           ml_user_nickname=ml_user_nickname)

@app.route('/oauth/mercadolivre')
def mercadolivre_auth():
    # Parâmetros obrigatórios conforme documentação
    params = {
        'response_type': 'code',
        'client_id': MERCADOLIVRE_CLIENT_ID,
        'redirect_uri': MERCADOLIVRE_REDIRECT_URI,
        'state': os.urandom(16).hex(), # Adicionando state para proteção CSRF
        'scope': 'offline_access read write' # Adicionando scopes necessários
    }
    session['oauth_state'] = params['state']
    
    auth_url = f"{MERCADOLIVRE_AUTH_URL}?{requests.utils.urlencode(params)}"
    return redirect(auth_url)

@app.route('/oauth/callback/mercadolivre')
def mercadolivre_callback():
    # Verificação do state para proteção CSRF
    if request.args.get('state') != session.get('oauth_state'):
        return "Erro de segurança: state inválido", 403
    
    error = request.args.get('error')
    if error:
        error_description = request.args.get('error_description', '')
        return f"Erro na autenticação: {error} - {error_description}", 400
    
    code = request.args.get('code')
    if not code:
        return "Código de autorização não recebido", 400
    
    data = {
        'grant_type': 'authorization_code',
        'client_id': MERCADOLIVRE_CLIENT_ID,
        'client_secret': MERCADOLIVRE_CLIENT_SECRET,
        'code': code,
        'redirect_uri': MERCADOLIVRE_REDIRECT_URI
    }
    
    try:
        response = requests.post(
            MERCADOLIVRE_TOKEN_URL,
            data=data,
            headers=MERCADOLIVRE_HEADERS,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        token_data = response.json()
        
        session['mercadolivre_access_token'] = token_data['access_token']
        session['mercadolivre_refresh_token'] = token_data.get('refresh_token')
        session['mercadolivre_expires_in'] = token_data.get('expires_in')
        session['mercadolivre_token_obtained_at'] = datetime.now().timestamp() # Guarda o timestamp
        session['mercadolivre_user_id'] = token_data.get('user_id')
        
        user_info = get_mercadolivre_user_info(token_data['access_token'])
        if user_info:
            session['mercadolivre_user_nickname'] = user_info.get('nickname')
        
        return redirect(url_for('index'))
    except requests.exceptions.RequestException as e:
        return f"Erro na comunicação com o Mercado Livre: {str(e)}", 500

@app.route('/mercadolivre/disconnect')
def mercadolivre_disconnect():
    session.pop('mercadolivre_access_token', None)
    session.pop('mercadolivre_refresh_token', None)
    session.pop('mercadolivre_expires_in', None)
    session.pop('mercadolivre_token_obtained_at', None)
    session.pop('mercadolivre_user_id', None)
    session.pop('mercadolivre_user_nickname', None)
    return redirect(url_for('index'))

@app.route('/mercadolivre/test')
def test_mercadolivre_connection():
    """Rota de teste para verificar conexão com API"""
    if not is_mercadolivre_token_valid():
        return jsonify({'error': 'Não autenticado ou token expirado/inválido'}), 401
    
    try:
        response = requests.get(
            f"{MERCADOLIVRE_API_URL}/users/me",
            headers={'Authorization': f'Bearer {session['mercadolivre_access_token']}', **MERCADOLIVRE_HEADERS},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process_shipment', methods=['POST'])
def process_shipment():
    barcode_input = request.json.get('barcode')
    
    if not barcode_input:
        return jsonify({"error": "Código de barras não fornecido"}), 400

    shipment_id_mlb = format_ml_shipment_id(barcode_input)
    
    if not shipment_id_mlb:
        return jsonify({"error": "Código não é uma etiqueta válida do Mercado Livre (formato inválido)"}), 400

    if not is_mercadolivre_token_valid():
        return jsonify({"error": "Não autenticado no Mercado Livre ou token expirado"}), 401

    try:
        access_token = session['mercadolivre_access_token']
        seller_id = session['mercadolivre_user_id']

        # 1. Busca a ordem relacionada ao shipment_id_mlb
        # O parâmetro 'q' para orders/search espera o ID do envio sem o prefixo 'MLB'
        # Ex: MLB2000008311396659 -> 2000008311396659
        order_search_id = shipment_id_mlb[3:] 
        
        order_response = requests.get(
            f"{MERCADOLIVRE_API_URL}/orders/search?seller={seller_id}&q={order_search_id}",
            headers={'Authorization': f'Bearer {access_token}', **MERCADOLIVRE_HEADERS},
            timeout=REQUEST_TIMEOUT
        )
        order_response.raise_for_status()
        
        orders_data = order_response.json().get('results')
        if not orders_data:
            return jsonify({"error": f"Nenhum pedido encontrado para a etiqueta {barcode_input} na sua conta."}), 404

        # Pega o primeiro pedido encontrado (assumindo que o Pack ID é único por pedido)
        order_id = orders_data[0]['id']

        # 2. Busca detalhes completos da ordem
        order_details_response = requests.get(
            f"{MERCADOLIVRE_API_URL}/orders/{order_id}",
            headers={'Authorization': f'Bearer {access_token}', **MERCADOLIVRE_HEADERS},
            timeout=REQUEST_TIMEOUT
        )
        order_details_response.raise_for_status()
        order_details = order_details_response.json()

        # 3. Busca detalhes completos do envio
        shipping_id = order_details.get('shipping', {}).get('id')
        shipping_details = {}
        if shipping_id:
            shipping_details_response = requests.get(
                f"{MERCADOLIVRE_API_URL}/shipments/{shipping_id}",
                headers={'Authorization': f'Bearer {access_token}', **MERCADOLIVRE_HEADERS},
                timeout=REQUEST_TIMEOUT
            )
            shipping_details_response.raise_for_status()
            shipping_details = shipping_details_response.json()

        # Formata os dados para exibição
        formatted_data = {
            "order": {
                "id": order_details.get('id'),
                "date_created": order_details.get('date_created'),
                "status": order_details.get('status'),
                "total_amount": order_details.get('total_amount'),
                "buyer_nickname": order_details.get('buyer', {}).get('nickname')
            },
            "shipping": {
                "id": shipping_details.get('id'),
                "status": shipping_details.get('status'),
                "shipping_method": shipping_details.get('shipping_option', {}).get('shipping_method', {}).get('name'),
                "estimated_delivery": shipping_details.get('estimated_delivery_final', {}).get('date'),
                "receiver_name": shipping_details.get('receiver_address', {}).get('receiver_name'),
                "receiver_address": format_address(shipping_details.get('receiver_address')),
                "receiver_phone": shipping_details.get('receiver_address', {}).get('phone', {}).get('number')
            },
            "items": [format_product_item(item) for item in order_details.get('order_items', [])]
        }
        
        return jsonify({"status": "success", "data": formatted_data})

    except requests.exceptions.HTTPError as e:
        print(f"Erro HTTP ao buscar dados do ML: {e.response.status_code} - {e.response.text}")
        return jsonify({
            "error": f"Erro na API do Mercado Livre: {e.response.status_code}",
            "details": e.response.json() if e.response.text else "Nenhum detalhe adicional"
        }), e.response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão ao buscar dados do ML: {e}")
        return jsonify({"error": f"Erro de conexão: {str(e)}"}), 500
    except Exception as e:
        print(f"Erro inesperado ao processar envio: {e}")
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

# --- Rota de Teste de DNS (para debug) ---
@app.route('/test-dns')
def test_dns():
    try:
        import socket
        import concurrent.futures

        endpoints = {
            'API Internacional': 'api.mercadolibre.com',
            'API Nacional': 'api.mercadolivre.com',
            'Auth Internacional': 'auth.mercadolibre.com',
            'Auth Nacional': 'auth.mercadolivre.com.br'
        }

        def check_dns(endpoint):
            try:
                socket.gethostbyname(endpoint)
                return "✅ Resolvido"
            except socket.gaierror:
                return "❌ Falha"

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = dict(zip(
                endpoints.keys(),
                executor.map(check_dns, endpoints.values())
            ))

        return jsonify({
            "status": "success" if "✅" in "".join(results.values()) else "warning",
            "results": results,
            "recommendation": "Use os endpoints internacionais caso haja falhas" 
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

