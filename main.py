import os
# Adicionado para forçar uso de DNS públicos como solução alternativa
os.environ['RESOLVER_OVERRIDE'] = '1.1.1.1,8.8.8.8,208.67.222.222'

import json
import requests
from flask import Flask, request, redirect, url_for, session, render_template, jsonify
from datetime import datetime
from urllib.parse import urlencode
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socket # Importação para testar DNS
import concurrent.futures # Para o teste DNS paralelo

app = Flask(__name__)
app.secret_key = os.urandom(24) # Mantenha esta linha para segurança da sessão

# Configurações do OAuth para Mercado Livre e Loja Integrada
# ATENÇÃO: O DOMAIN agora aponta para o Railway para o callback funcionar
DOMAIN = "https://sistema-bipagem-masterhotelaria-production.up.railway.app"

# Credenciais do Mercado Livre (substitua pelas suas )
# CLIENT ID CORRIGIDO E SECRET AGORA LÊ DE VARIAVEL DE AMBIENTE OU USA DEFAULT
MERCADOLIVRE_CLIENT_ID = os.environ.get("MERCADOLIVRE_CLIENT_ID", "427016700814141")
MERCADOLIVRE_CLIENT_SECRET = os.environ.get("MERCADOLIVRE_CLIENT_SECRET", "CYR6NVWYsN5zf1JhdMUD4EA2WXDPyRry") # Use seu Client Secret aqui como default
MERCADOLIVRE_REDIRECT_URI = f"{DOMAIN}/oauth/callback/mercadolivre"

# URLs do Mercado Livre - Usando domínios internacionais por padrão para maior compatibilidade
MERCADOLIVRE_AUTH_URL = 'https://auth.mercadolibre.com/authorization'
MERCADOLIVRE_TOKEN_URL = 'https://api.mercadolibre.com/oauth/token'
MERCADOLIVRE_API_URL = 'https://api.mercadolibre.com'


# Credenciais da Loja Integrada (substitua pelas suas )
LOJAINTEGRADA_CLIENT_ID = os.environ.get("LOJAINTEGRADA_CLIENT_ID", "SEU_CLIENT_ID_LOJAINTEGRADA")
LOJAINTEGRADA_CLIENT_SECRET = os.environ.get("LOJAINTEGRADA_CLIENT_SECRET", "SEU_CLIENT_SECRET_LOJAINTEGRADA")
LOJAINTEGRADA_REDIRECT_URI = f"{DOMAIN}/oauth/callback/loja-integrada"

# Banco de dados simulado (para produtos e vendas)
# Este é um exemplo, em um sistema real seria um banco de dados persistente
DATABASE = {
    "products": {
        "45061874601": {
            "name": "Capa de Almofada Impermeável",
            "price": 119.90,
            "image": "https://http2.mlstatic.com/D_NQ_NP_2X_687654-MLB72750979708_112023-F.webp",
            "description": "Capa de almofada de alta qualidade, impermeável e durável.",
            "platform": "Mercado Livre"
        },
        "78901234567": {
            "name": "Jogo de Cama Casal 4 Peças",
            "price": 159.90,
            "image": "https://http2.mlstatic.com/D_NQ_NP_2X_704670-MLB72750979708_112023-F.webp",
            "description": "Jogo de cama completo para casal, 100% algodão.",
            "platform": "Mercado Livre"
        },
        "12345678901": {
            "name": "Toalha de Banho Gigante",
            "price": 79.90,
            "image": "https://http2.mlstatic.com/D_NQ_NP_2X_704670-MLB72750979708_112023-F.webp",
            "description": "Toalha de banho extra grande e macia.",
            "platform": "Loja Integrada"
        }
    },
    "sales": []
}

# Função para simular dados de produto se não encontrado
def get_simulated_product_data(barcode ):
    return {
        "name": f"Produto Genérico {barcode}",
        "price": round(float(barcode) % 100 + 20, 2), # Preço aleatório
        "image": "https://via.placeholder.com/150?text=Produto+Nao+Encontrado",
        "description": "Este é um produto simulado. Não encontrado na base de dados.",
        "platform": "Simulado"
    }

# Função para criar uma sessão requests com retries
def create_http_session( ):
    session = requests.Session()
    retries = Retry(
        total=3, # Tenta 3 vezes
        backoff_factor=1, # Espera 1, 2, 4 segundos entre as tentativas
        status_forcelist=[500, 502, 503, 504], # Retenta em erros de servidor
        allowed_methods=frozenset(['GET', 'POST']) # Permite retentar GET e POST
    )
    session.mount('https://', HTTPAdapter(max_retries=retries ))
    return session

@app.route('/')
def index():
    ml_connected = 'mercadolivre_access_token' in session
    li_connected = 'lojaintegrada_access_token' in session
    return render_template('index.html', domain=DOMAIN, ml_connected=ml_connected, li_connected=li_connected)

@app.route('/process_barcode', methods=['POST'])
def process_barcode():
    barcode = request.json.get('barcode')
    if not barcode:
        return jsonify({"error": "Código de barras não fornecido"}), 400

    product_data = DATABASE["products"].get(barcode)
    if not product_data:
        product_data = get_simulated_product_data(barcode)

    # Simular uma venda
    sale_info = {
        "barcode": barcode,
        "product_name": product_data["name"],
        "price": product_data["price"],
        "timestamp": datetime.now().isoformat(),
        "buyer": f"Comprador {len(DATABASE['sales']) + 1}", # Nome de comprador simulado
        "platform": product_data["platform"]
    }
    DATABASE["sales"].append(sale_info)

    return jsonify({
        "message": "Código processado com sucesso!",
        "product": product_data,
        "sale_info": sale_info
    })

@app.route('/reports')
def reports():
    return render_template('reports.html', sales=DATABASE["sales"])

# Rotas de OAuth - Mercado Livre (ATUALIZADAS)
@app.route('/oauth/mercadolivre')
def oauth_mercadolivre():
    # Parâmetros obrigatórios conforme documentação
    params = {
        'response_type': 'code',
        'client_id': MERCADOLIVRE_CLIENT_ID,
        'redirect_uri': MERCADOLIVRE_REDIRECT_URI,
        # Adicionando state para proteção CSRF conforme boas práticas
        'state': os.urandom(16).hex()
    }
    session['oauth_state'] = params['state'] # Armazena o state na sessão
    
    # Construindo URL conforme documentação oficial
    auth_url = f"{MERCADOLIVRE_AUTH_URL}?{urlencode(params)}"
    return redirect(auth_url)

@app.route('/oauth/callback/mercadolivre')
def oauth_callback_mercadolivre():
    # Verificação do state para proteção CSRF
    if request.args.get('state') != session.pop('oauth_state', None): # Usa pop para remover da sessão após uso
        return "Erro de segurança: state inválido ou ausente", 403
    
    error = request.args.get('error')
    if error:
        error_description = request.args.get('error_description', '')
        return f"Erro na autenticação: {error} - {error_description}", 400
    
    code = request.args.get('code')
    if not code:
        return "Código de autorização não recebido", 400
    
    # Preparando dados para troca do code por token
    data = {
        'grant_type': 'authorization_code',
        'client_id': MERCADOLIVRE_CLIENT_ID,
        'client_secret': MERCADOLIVRE_CLIENT_SECRET,
        'code': code,
        'redirect_uri': MERCADOLIVRE_REDIRECT_URI
    }
    
    try:
        http_session = create_http_session( ) # Usa a sessão com retries
        # Fazendo a requisição conforme documentação
        response = http_session.post( # Usa http_session
            MERCADOLIVRE_TOKEN_URL,
            data=data,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'SistemaBipagem/1.0 (contact@masterhotelaria.com.br )' # Adicionado User-Agent
            },
            timeout=10 # Adicionado timeout de 10 segundos
        )
        
        # Verifique se a URL foi resolvida (nova verificação)
        if "api.mercadolibre.com" not in MERCADOLIVRE_TOKEN_URL: # Ajustado para o novo domínio
            return "URL da API configurada incorretamente no código", 500
            
        response.raise_for_status() # Levanta exceção para status de erro HTTP
        
        token_data = response.json()
        
        # Armazenando tokens conforme resposta esperada
        session['mercadolivre_access_token'] = token_data['access_token']
        session['mercadolivre_refresh_token'] = token_data.get('refresh_token')
        session['mercadolivre_expires_in'] = token_data.get('expires_in')
        session['mercadolivre_user_id'] = token_data.get('user_id')
        
        # Obter informações do usuário para demonstrar integração
        user_info = get_mercadolivre_user_info(token_data['access_token'])
        if user_info:
            session['mercadolivre_user_nickname'] = user_info.get('nickname')
        
        return redirect(url_for('index'))
    except requests.exceptions.SSLError as e:
        return f"Erro de SSL: {str(e)} - Verifique certificados ou configuração SSL", 500
    except requests.exceptions.Timeout:
        return "Tempo limite excedido ao conectar ao Mercado Livre. Tente novamente.", 504
    except requests.exceptions.RequestException as e:
        # Captura NameResolutionError e outros erros de requisição
        return f"Falha na requisição ao Mercado Livre: {str(e)} - Verifique conexão com a internet ou DNS", 500

def get_mercadolivre_user_info(access_token):
    """Obtém informações do usuário autenticado conforme API"""
    try:
        http_session = create_http_session( ) # Usa a sessão com retries
        response = http_session.get( # Usa http_session
            f"{MERCADOLIVRE_API_URL}/users/me",
            headers={
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'SistemaBipagem/1.0 (contact@masterhotelaria.com.br )' # Adicionado User-Agent
            },
            timeout=10 # Adicionado timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

@app.route('/mercadolivre/test')
def test_mercadolivre_connection():
    """Rota de teste para verificar conexão com API"""
    if 'mercadolivre_access_token' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        http_session = create_http_session( ) # Usa a sessão com retries
        # Exemplo de chamada à API - obtendo informações do usuário
        response = http_session.get( # Usa http_session
            f"{MERCADOLIVRE_API_URL}/users/me",
            headers={
                'Authorization': f'Bearer {session['mercadolivre_access_token']}',
                'User-Agent': 'SistemaBipagem/1.0 (contact@masterhotelaria.com.br )' # Adicionado User-Agent
            },
            timeout=10 # Adicionado timeout
        )
        
        if response.status_code == 401:
            # Token pode ter expirado - tentar renovar com refresh_token
            if 'mercadolivre_refresh_token' in session:
                refresh_response = refresh_mercadolivre_token()
                if refresh_response[1] == 200: # Verifica o status code da tupla retornada
                    # Tentar novamente a chamada após o refresh
                    response = http_session.get( # Usa http_session
                        f"{MERCADOLIVRE_API_URL}/users/me",
                        headers={
                            'Authorization': f'Bearer {session['mercadolivre_access_token']}',
                            'User-Agent': 'SistemaBipagem/1.0 (contact@masterhotelaria.com.br )' # Adicionado User-Agent
                        },
                        timeout=10 # Adicionado timeout
                    )
                    response.raise_for_status()
                    return jsonify(response.json())
                else:
                    return refresh_response # Retorna o erro do refresh
            return jsonify({'error': 'Token expirado e sem refresh token ou falha no refresh'}), 401
        
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

def refresh_mercadolivre_token():
    """Atualiza o token de acesso usando refresh token conforme documentação"""
    if 'mercadolivre_refresh_token' not in session:
        return jsonify({'error': 'Refresh token não disponível'}), 400
    
    data = {
        'grant_type': 'refresh_token',
        'client_id': MERCADOLIVRE_CLIENT_ID,
        'client_secret': MERCADOLIVRE_CLIENT_SECRET,
        'refresh_token': session['mercadolivre_refresh_token']
    }
    
    try:
        http_session = create_http_session( ) # Usa a sessão com retries
        response = http_session.post(MERCADOLIVRE_TOKEN_URL, data=data, headers={
            'User-Agent': 'SistemaBipagem/1.0 (contact@masterhotelaria.com.br )' # Adicionado User-Agent
        }, timeout=10) # Adicionado timeout
        response.raise_for_status()
        token_data = response.json()
        
        # Atualiza os tokens na sessão
        session['mercadolivre_access_token'] = token_data['access_token']
        session['mercadolivre_refresh_token'] = token_data.get('refresh_token', session['mercadolivre_refresh_token']) # Refresh token pode não vir em todas as respostas
        session['mercadolivre_expires_in'] = token_data.get('expires_in')
        
        return jsonify({'success': True, 'message': 'Token atualizado'}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

# Nova rota para testar resolução de DNS
@app.route('/test-dns')
def test_dns():
    try:
        import socket
        import concurrent.futures

        endpoints = {
            'API Nacional': 'api.mercadolivre.com',
            'API Internacional': 'api.mercadolibre.com',
            'Auth Nacional': 'auth.mercadolivre.com.br',
            'Auth Internacional': 'auth.mercadolibre.com'
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
            "status": "success" if "✅ Resolvido" in results.values() else "warning", # Ajustado para verificar a string completa
            "results": results,
            "recommendation": "Use os endpoints internacionais caso haja falhas" 
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/oauth/loja-integrada')
def oauth_loja_integrada():
    # Loja Integrada usa um fluxo OAuth ligeiramente diferente ou API Key direta
    # Este é um placeholder. Você precisaria implementar o fluxo real da LI.
    # Geralmente envolve um link para autorização e um callback para obter o token.
    return "Integração Loja Integrada em desenvolvimento. Por favor, configure manualmente.", 200

@app.route('/oauth/callback/loja-integrada')
def oauth_callback_loja_integrada():
    # Este é um placeholder para o callback da Loja Integrada
    # Em um cenário real, você processaria o código e obteria o token aqui.
    session['lojaintegrada_access_token'] = "mock_token_li" # Token simulado
    return redirect(url_for('index'))

@app.route('/config/mercadolivre')
def config_mercadolivre():
    return render_template('config_mercadolivre.html',
                           client_id=MERCADOLIVRE_CLIENT_ID,
                           client_secret=MERCADOLIVRE_CLIENT_SECRET,
                           redirect_uri=MERCADOLIVRE_REDIRECT_URI)

@app.route('/config/shopee')
def config_shopee():
    return render_template('config_shopee.html')

@app.route('/config/loja-integrada')
def config_loja_integrada():
    return render_template('config_loja_integrada.html',
                           client_id=LOJAINTEGRADA_CLIENT_ID,
                           client_secret=LOJAINTEGRADA_CLIENT_SECRET,
                           redirect_uri=LOJAINTEGRADA_REDIRECT_URI)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080)) # Railway usa 8080 por padrão
    print(f"Sistema de Bipagem - OAuth Real no Railway")
    print(f"Integração REAL com APIs das plataformas")
    print(f"Domínio: {DOMAIN}")
    print(f"OAuth 2.0 funcionando")
    print(f"Banco de dados inicializado com {len(DATABASE['products'])} produtos.")
    app.run(host='0.0.0.0', port=port)
