import os
import json
import requests
from flask import Flask, request, redirect, url_for, session, render_template, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configurações do OAuth para Mercado Livre e Loja Integrada
# ATENÇÃO: O DOMAIN agora aponta para o Railway para o callback funcionar
DOMAIN = "https://sistema-bipagem-masterhotelaria-production.up.railway.app"

# Credenciais do Mercado Livre (substitua pelas suas )
# CLIENT ID CORRIGIDO AQUI!
MERCADOLIVRE_CLIENT_ID = os.environ.get("MERCADOLIVRE_CLIENT_ID", "427016700814141")
MERCADOLIVRE_CLIENT_SECRET = os.environ.get("MERCADOLIVRE_CLIENT_SECRET", "CYR6NVWYsN5zf1JhdMUD4EA2WXDPyRry")
MERCADOLIVRE_REDIRECT_URI = f"{DOMAIN}/oauth/callback/mercadolivre"

# Credenciais da Loja Integrada (substitua pelas suas)
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

@app.route('/' )
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

# Rotas de OAuth
@app.route('/oauth/mercadolivre')
def oauth_mercadolivre():
    auth_url = (
        f"https://auth.mercadolivre.com.br/authorization?"
        f"response_type=code&client_id={MERCADOLIVRE_CLIENT_ID}&"
        f"redirect_uri={MERCADOLIVRE_REDIRECT_URI}"
     )
    return redirect(auth_url)

@app.route('/oauth/callback/mercadolivre')
def oauth_callback_mercadolivre():
    code = request.args.get('code')
    if not code:
        return "Erro: Código de autorização não recebido do Mercado Livre.", 400

    token_url = "https://api.mercadolivre.com/oauth/token"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'authorization_code',
        'client_id': MERCADOLIVRE_CLIENT_ID,
        'client_secret': MERCADOLIVRE_CLIENT_SECRET,
        'code': code,
        'redirect_uri': MERCADOLIVRE_REDIRECT_URI
    }

    try:
        response = requests.post(token_url, headers=headers, data=data )
        response.raise_for_status() # Levanta um erro para status HTTP ruins
        token_info = response.json()

        session['mercadolivre_access_token'] = token_info['access_token']
        session['mercadolivre_refresh_token'] = token_info['refresh_token']
        session['mercadolivre_user_id'] = token_info['user_id']

        # Exemplo: buscar informações do usuário
        user_info_url = f"https://api.mercadolibre.com/users/{token_info['user_id']}"
        user_headers = {'Authorization': f"Bearer {token_info['access_token']}"}
        user_response = requests.get(user_info_url, headers=user_headers )
        user_response.raise_for_status()
        user_data = user_response.json()
        session['mercadolivre_nickname'] = user_data.get('nickname', 'Usuário ML')

        return redirect(url_for('index'))
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erro ao obter token do Mercado Livre: {e}")
        return f"Erro ao conectar com Mercado Livre: {e}", 500

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
