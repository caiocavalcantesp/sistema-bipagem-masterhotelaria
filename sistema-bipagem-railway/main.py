import os
import json
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import requests
from datetime import datetime

# --- Configuração Inicial ---
app = Flask(__name__, static_folder='static', template_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# --- Credenciais do Mercado Livre ---
ML_CLIENT_ID = "427016700814141"
ML_CLIENT_SECRET = "CYR6NVWYsN5zf1JhdMUD4EA2WXDPyRry"

# --- Configuração de Domínio ---
# IMPORTANTE: Detecta automaticamente se está no Railway ou desenvolvimento local
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Produção no Railway - usar domínio personalizado
    PRODUCTION_DOMAIN = "https://bipagem.masterhotelaria.com.br"
else:
    # Desenvolvimento local
    PRODUCTION_DOMAIN = "http://localhost:5000"

# --- Banco de Dados ---
DB_FILE = "bipagem_master.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Tabela para armazenar os tokens OAuth
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            platform TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tabela para armazenar as bipagens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bipagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,
            platform TEXT NOT NULL,
            product_name TEXT,
            sku TEXT,
            price REAL,
            buyer_name TEXT,
            order_id TEXT,
            image_url TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# --- Rotas da Interface ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config.html')
def config_page():
    return render_template('config.html')

@app.route('/reports.html')
def reports_page():
    return render_template('reports.html')

# --- Rotas da API ---

# --- OAuth Routes ---
@app.route('/oauth/platforms')
def get_oauth_platforms():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    platforms_config = [
        {"id": "mercadolivre", "name": "Mercado Livre"},
        {"id": "shopee", "name": "Shopee"},
        {"id": "loja_integrada", "name": "Loja Integrada"}
    ]
    
    response_data = []
    for p_config in platforms_config:
        cursor.execute("SELECT access_token FROM oauth_tokens WHERE platform = ?", (p_config['id'],))
        token_data = cursor.fetchone()
        
        p_data = {
            "id": p_config['id'],
            "name": p_config['name'],
            "connected": bool(token_data and token_data['access_token'])
        }
        response_data.append(p_data)
        
    conn.close()
    return jsonify(response_data)

@app.route('/oauth/authorize/<platform>')
def oauth_authorize(platform):
    if platform == 'mercadolivre':
        # SOLUÇÃO: Usar domínio fixo do cliente
        redirect_uri = f"{PRODUCTION_DOMAIN}/oauth/callback/mercadolivre"
        
        # Log para depuração
        print("--- INICIANDO AUTORIZAÇÃO OAUTH (RAILWAY) ---")
        print(f"Ambiente: {'RAILWAY' if os.environ.get('RAILWAY_ENVIRONMENT') else 'LOCAL'}")
        print(f"Domínio de Produção: {PRODUCTION_DOMAIN}")
        print(f"URL de Retorno (redirect_uri): {redirect_uri}")
        print("---------------------------------------------")

        auth_url = (
            f"https://auth.mercadolivre.com.br/authorization"
            f"?response_type=code"
            f"&client_id={ML_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
        )
        return redirect(auth_url)
    return "Plataforma não suportada", 404

@app.route('/oauth/callback/<platform>')
def oauth_callback(platform):
    if platform == 'mercadolivre':
        code = request.args.get('code')
        state = request.args.get('state')

        print(f"--- CALLBACK OAUTH MERCADO LIVRE (RAILWAY) ---")
        print(f"URL Completa do Callback: {request.url}")
        print(f"Código de autorização recebido: {code}")
        print(f"Estado (state) recebido: {state}")

        if not code:
            error = request.args.get('error')
            error_description = request.args.get('error_description')
            print(f"ERRO: Código de autorização não recebido no callback. Erro: {error}, Descrição: {error_description}")
            return f"Erro na autorização: {error_description or error or 'Código de autorização não recebido.'}", 400

        # IMPORTANTE: A redirect_uri aqui DEVE ser a mesma usada na autorização
        redirect_uri = f"{PRODUCTION_DOMAIN}/oauth/callback/mercadolivre"
        print(f"Redirect URI usada para troca de token: {redirect_uri}")

        token_url = "https://api.mercadolibre.com/oauth/token"
        payload = {
            'grant_type': 'authorization_code',
            'client_id': ML_CLIENT_ID,
            'client_secret': ML_CLIENT_SECRET,
            'code': code,
            'redirect_uri': redirect_uri
        }
        print(f"Payload para troca de token (sem client_secret para segurança): {{'grant_type': '{payload['grant_type']}', 'client_id': '{payload['client_id']}', 'code': '{payload['code']}', 'redirect_uri': '{payload['redirect_uri']}'}}")
        
        try:
            response = requests.post(token_url, json=payload, headers={'Accept': 'application/json'})
            print(f"Resposta da API de token - Status: {response.status_code}")
            print(f"Resposta da API de token - Texto: {response.text}")
            response.raise_for_status() 
            token_data = response.json()
            print(f"Dados do token recebidos (parcial): {{'access_token': '...', 'refresh_token': '...', 'expires_in': {token_data.get('expires_in')}}}")

            # Salvar token no banco de dados
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO oauth_tokens (platform, access_token, refresh_token, expires_at)
                VALUES (?, ?, ?, ?)
            ''', ('mercadolivre', token_data['access_token'], token_data['refresh_token'], datetime.now().timestamp() + token_data['expires_in']))
            conn.commit()
            conn.close()

            print("Token salvo com sucesso. Redirecionando para config_page.")
            # Redirecionar para a página de configurações
            return redirect(f"{PRODUCTION_DOMAIN}/config.html")
        except requests.exceptions.RequestException as e:
            print(f"ERRO ao obter token: {e}")
            if e.response is not None:
                print(f"Detalhes do erro da resposta: {e.response.text}")
                return f"Erro ao obter token: {e.response.text}", 500
            else:
                return f"Erro ao obter token: {e}", 500
    print("Plataforma não suportada no callback.")
    return "Plataforma não suportada", 404

# --- Bipagem e Relatórios ---
@app.route('/api/bip', methods=['POST'])
def handle_bip():
    data = request.get_json()
    barcode = data.get('barcode')
    if not barcode:
        return jsonify({"status": "error", "message": "Código de barras não fornecido."}), 400

    platform = "Mercado Livre" # Simplificado por enquanto

    # Tenta buscar informações reais se o token do ML existir
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT access_token FROM oauth_tokens WHERE platform = 'mercadolivre'")
    token_row = cursor.fetchone()
    ml_access_token = token_row[0] if token_row else None
    
    product_info = get_product_info_ml(barcode, ml_access_token)

    # Salva a bipagem no banco
    cursor.execute('''
        INSERT INTO bipagens (barcode, platform, product_name, sku, price, buyer_name, order_id, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (barcode, platform, product_info.get('product_name'), product_info.get('sku'), product_info.get('price'), product_info.get('buyer_name'), product_info.get('order_id'), product_info.get('image_url')))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "data": product_info})

def get_product_info_ml(barcode, access_token):
    # Códigos de teste hardcoded
    if barcode == "45061874601":
        return {
            "platform": "Mercado Livre", "product_name": "Capa de Almofada Impermeável 45x45 Acquablock Original",
            "sku": "KIT-4-CAPAS-ACQUA-01", "price": 119.90, "buyer_name": "João da Silva",
            "order_id": "2000006543210987", "image_url": "https://http2.mlstatic.com/D_NQ_NP_898278-MLB74139880956_012024-O.webp"
        }
    if barcode == "45061714627":
        return {
            "platform": "Mercado Livre", "product_name": "Kit 4 Capas De Almofada Decorativa Veludo Com Zíper 45x45",
            "sku": "VEL-KIT-4-ALMO-02", "price": 89.90, "buyer_name": "Maria Oliveira",
            "order_id": "2000006543210988", "image_url": "https://http2.mlstatic.com/D_NQ_NP_983224-MLB73113533689_112023-O.webp"
        }

    # Se tiver token, busca na API real
    if access_token:
        try:
            # Exemplo: Tenta buscar um item com ID do barcode
            item_id = f"MLB{barcode}" # Simulação
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(f'https://api.mercadolibre.com/items/{item_id}', headers=headers)
            if response.ok:
                item_data = response.json()
                return {
                    "platform": "Mercado Livre", "product_name": item_data.get('title', 'Produto Real'),
                    "sku": item_data.get('seller_sku', 'N/A'), "price": item_data.get('price', 0.0),
                    "buyer_name": "Comprador Real", "order_id": "Ordem Real", "image_url": item_data.get('thumbnail', '/static/images/placeholder.png')
                }
        except Exception as e:
            print(f"Erro na API do ML: {e}")
    
    # Fallback se não houver token ou não for código de teste
    return {
        "platform": "Desconhecida", "product_name": f"Produto não encontrado ({barcode})",
        "sku": "N/A", "price": 0.00, "buyer_name": "N/A", "order_id": "N/A",
        "image_url": "/static/images/placeholder.png"
    }

@app.route('/api/reports')
def get_reports():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Bipagens por dia
    cursor.execute("SELECT date(timestamp) as day, COUNT(*) as count FROM bipagens GROUP BY day ORDER BY day DESC")
    bipagens_por_dia = [dict(row) for row in cursor.fetchall()]
    
    # Bipagens por plataforma
    cursor.execute("SELECT platform, COUNT(*) as count FROM bipagens GROUP BY platform")
    bipagens_por_plataforma = [dict(row) for row in cursor.fetchall()]
    
    # Bipagens recentes
    cursor.execute("SELECT * FROM bipagens ORDER BY timestamp DESC LIMIT 5")
    recentes = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        "bipagensPorDia": bipagens_por_dia,
        "bipagensPorPlataforma": bipagens_por_plataforma,
        "recentes": recentes
    })

# --- Inicialização ---
if __name__ == '__main__':
    init_db()
    
    # Configuração para Railway
    port = int(os.environ.get('PORT', 5000))
    
    print("=== SISTEMA DE BIPAGEM MASTER HOTELARIA v3.0 (RAILWAY) ===")
    print(f"🌐 Ambiente: {'RAILWAY' if os.environ.get('RAILWAY_ENVIRONMENT') else 'LOCAL'}")
    print(f"🔗 Domínio: {PRODUCTION_DOMAIN}")
    print(f"🚀 Porta: {port}")
    print("")
    print("📋 CONFIGURAÇÃO MERCADO LIVRE:")
    print(f"   Redirect URI: {PRODUCTION_DOMAIN}/oauth/callback/mercadolivre")
    print("")
    print("🚀 Rotas disponíveis:")
    print(f"   GET  /oauth/platforms")
    print(f"   GET  /oauth/authorize/<platform>")
    print(f"   GET  /oauth/callback/<platform>")
    print(f"   GET  /api/reports")
    
    app.run(debug=False, host='0.0.0.0', port=port)

