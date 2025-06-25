#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Bipagem Master Hotelaria - OAUTH REAL
Deploy no Railway com domínio www.masterhotelaria.com.br
"""

import os
import sys
import json
import sqlite3
import threading
import webbrowser
import time
import requests
import base64
import urllib.parse
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, redirect, session, url_for
from flask_cors import CORS

# Configuração do Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bipagem_master_hotelaria_2024_oauth_real')
CORS(app)

# Configurações do domínio público
DOMAIN = "https://www.masterhotelaria.com.br"
PORT = int(os.environ.get('PORT', 5000))

# URLs base das APIs
MERCADO_LIVRE_API = "https://api.mercadolibre.com"
SHOPEE_API = "https://partner.shopeemobile.com"
LOJA_INTEGRADA_API = "https://api.awsli.com.br"

# Banco de dados
DB_FILE = "bipagem_oauth_real.db"

def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabela para bipagens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bipagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,
            platform TEXT NOT NULL,
            product_id TEXT,
            product_name TEXT,
            sku TEXT,
            price REAL,
            buyer_name TEXT,
            order_id TEXT,
            image_url TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela para configurações OAuth
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            platform TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at DATETIME,
            user_id TEXT
        )
    ''')
    
    # Tabela para configurações das plataformas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS platform_configs (
            platform TEXT PRIMARY KEY,
            client_id TEXT,
            client_secret TEXT,
            redirect_uri TEXT,
            is_configured BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def save_platform_config(platform, client_id, client_secret):
    """Salva configurações da plataforma com domínio público"""
    redirect_uri = f"{DOMAIN}/oauth/callback/{platform}"
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO platform_configs 
        (platform, client_id, client_secret, redirect_uri, is_configured)
        VALUES (?, ?, ?, ?, 1)
    ''', (platform, client_id, client_secret, redirect_uri))
    conn.commit()
    conn.close()
    
    return redirect_uri

def get_platform_config(platform):
    """Busca configurações da plataforma"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM platform_configs WHERE platform = ?', (platform,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'platform': result[0],
            'client_id': result[1],
            'client_secret': result[2],
            'redirect_uri': result[3],
            'is_configured': bool(result[4])
        }
    return None

def save_oauth_token(platform, access_token, refresh_token=None, expires_in=None, user_id=None):
    """Salva token OAuth"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    expires_at = None
    if expires_in:
        expires_at = datetime.now() + timedelta(seconds=expires_in)
    
    cursor.execute('''
        INSERT OR REPLACE INTO oauth_tokens 
        (platform, access_token, refresh_token, expires_at, user_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (platform, access_token, refresh_token, expires_at, user_id))
    conn.commit()
    conn.close()

def get_oauth_token(platform):
    """Busca token OAuth"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM oauth_tokens WHERE platform = ?', (platform,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'platform': result[0],
            'access_token': result[1],
            'refresh_token': result[2],
            'expires_at': result[3],
            'user_id': result[4]
        }
    return None

class MercadoLivreAPI:
    """Integração com API do Mercado Livre"""
    
    def __init__(self):
        self.base_url = MERCADO_LIVRE_API
        
    def get_auth_url(self, client_id, redirect_uri):
        """Gera URL de autorização"""
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri
        }
        return f"{self.base_url}/authorization?{urllib.parse.urlencode(params)}"
    
    def exchange_code_for_token(self, code, client_id, client_secret, redirect_uri):
        """Troca código por token"""
        data = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        try:
            response = requests.post(f"{self.base_url}/oauth/token", data=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Erro ML token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Erro ML token exception: {e}")
            return None
    
    def search_product_by_barcode(self, barcode, access_token):
        """Busca produto por código de barras"""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            # Buscar por GTIN (código de barras)
            url = f"{self.base_url}/sites/MLB/search"
            params = {'q': barcode}
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    product = data['results'][0]
                    return {
                        'product_id': product['id'],
                        'title': product['title'],
                        'price': product['price'],
                        'thumbnail': product['thumbnail'],
                        'permalink': product['permalink']
                    }
            return None
        except Exception as e:
            print(f"Erro ML search: {e}")
            return None
    
    def get_user_info(self, access_token):
        """Busca informações do usuário"""
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{self.base_url}/users/me", headers=headers)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Erro ML user info: {e}")
            return None

class LojaIntegradaAPI:
    """Integração com API da Loja Integrada"""
    
    def __init__(self):
        self.base_url = LOJA_INTEGRADA_API
    
    def get_auth_url(self, client_id, redirect_uri):
        """Gera URL de autorização"""
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'read_products read_orders'
        }
        return f"{self.base_url}/v1/oauth/authorize?{urllib.parse.urlencode(params)}"
    
    def exchange_code_for_token(self, code, client_id, client_secret, redirect_uri):
        """Troca código por token"""
        data = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        try:
            response = requests.post(f"{self.base_url}/v1/oauth/token", data=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Erro Loja token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Erro Loja token exception: {e}")
            return None
    
    def search_product_by_sku(self, sku, access_token):
        """Busca produto por SKU"""
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{self.base_url}/v1/produto", 
                                  params={'sku': sku}, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('objects'):
                    return data['objects'][0]
            return None
        except Exception as e:
            print(f"Erro Loja search: {e}")
            return None

# Instâncias das APIs
ml_api = MercadoLivreAPI()
loja_api = LojaIntegradaAPI()

# Template HTML Principal
INDEX_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Bipagem - OAuth Real</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 900px;
            width: 100%;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .header h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header .version {
            background: linear-gradient(45deg, #28a745, #20c997);
            color: white;
            padding: 8px 20px;
            border-radius: 25px;
            font-size: 1em;
            display: inline-block;
            margin-bottom: 15px;
            font-weight: bold;
        }
        
        .domain-info {
            background: linear-gradient(135deg, #d1ecf1, #bee5eb);
            border: 2px solid #17a2b8;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .domain-info h3 {
            color: #0c5460;
            margin-bottom: 10px;
        }
        
        .domain-info code {
            background: white;
            padding: 5px 10px;
            border-radius: 5px;
            color: #0c5460;
            font-weight: bold;
        }
        
        .platforms-status {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .platform-card {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s;
        }
        
        .platform-card:hover {
            transform: translateY(-5px);
        }
        
        .platform-card h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .status-connected {
            background: linear-gradient(45deg, #28a745, #20c997);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .status-disconnected {
            background: linear-gradient(45deg, #dc3545, #c82333);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s;
            font-weight: bold;
            margin-top: 15px;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #007bff, #0056b3);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,123,255,0.3);
        }
        
        .barcode-section {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .barcode-display {
            font-size: 2.2em;
            font-weight: bold;
            color: #333;
            background: white;
            padding: 25px;
            border-radius: 15px;
            margin: 25px 0;
            border: 3px dashed #007bff;
            min-height: 90px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .digit-counter {
            color: #666;
            font-size: 1.3em;
            margin-bottom: 25px;
            font-weight: bold;
        }
        
        .action-buttons {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-top: 25px;
        }
        
        .result-section {
            margin-top: 30px;
        }
        
        .result-success {
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            border: 2px solid #28a745;
            border-radius: 20px;
            padding: 30px;
            animation: slideIn 0.6s ease-out;
        }
        
        .result-error {
            background: linear-gradient(135deg, #f8d7da, #f1b0b7);
            border: 2px solid #dc3545;
            border-radius: 20px;
            padding: 30px;
            animation: slideIn 0.6s ease-out;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .navigation {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 40px;
        }
        
        .nav-link {
            color: #007bff;
            text-decoration: none;
            padding: 15px 30px;
            border: 3px solid #007bff;
            border-radius: 15px;
            transition: all 0.3s;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .nav-link:hover {
            background: linear-gradient(45deg, #007bff, #0056b3);
            color: white;
            transform: translateY(-3px);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="version">OAUTH REAL - RAILWAY</div>
            <h1>🏨 Sistema de Bipagem</h1>
            <p>Integração Real com APIs das Plataformas</p>
        </div>
        
        <div class="domain-info">
            <h3>🌐 Domínio Configurado para OAuth</h3>
            <p>Callbacks configurados para: <code>www.masterhotelaria.com.br</code></p>
            <small>Sistema rodando no Railway com OAuth funcional</small>
        </div>
        
        <div class="platforms-status">
            <div class="platform-card">
                <h3>🛒 Mercado Livre</h3>
                <div id="ml-status" class="status-disconnected">Desconectado</div>
                <a href="/setup" class="btn btn-primary">Configurar OAuth</a>
            </div>
            
            <div class="platform-card">
                <h3>🛍️ Shopee</h3>
                <div id="shopee-status" class="status-disconnected">Em Desenvolvimento</div>
                <button class="btn btn-primary" disabled>Em Breve</button>
            </div>
            
            <div class="platform-card">
                <h3>🏪 Loja Integrada</h3>
                <div id="loja-status" class="status-disconnected">Desconectado</div>
                <a href="/setup" class="btn btn-primary">Configurar OAuth</a>
            </div>
        </div>
        
        <div class="barcode-section">
            <h2>📱 Leitura de Código de Barras</h2>
            <div id="barcode-display" class="barcode-display">
                Aguardando código de barras...
            </div>
            <div id="digit-counter" class="digit-counter">0/11 dígitos</div>
            
            <div class="action-buttons">
                <button id="process-btn" class="btn btn-primary" disabled>
                    🔍 Processar Código
                </button>
                <button id="clear-btn" class="btn btn-secondary">
                    🗑️ Limpar
                </button>
            </div>
        </div>
        
        <div id="bip-result" class="result-section" style="display: none;"></div>
        
        <div class="navigation">
            <a href="/setup" class="nav-link">⚙️ Configurações OAuth</a>
            <a href="/reports" class="nav-link">📊 Relatórios</a>
        </div>
    </div>

    <script>
        // Sistema de Bipagem com OAuth Real
        class BipagemSystemOAuth {
            constructor() {
                this.currentBarcode = '';
                this.isProcessing = false;
                this.init();
            }

            init() {
                this.setupEventListeners();
                this.checkPlatformStatus();
                
                document.body.focus();
                document.body.setAttribute('tabindex', '0');
            }

            async checkPlatformStatus() {
                try {
                    const response = await fetch('/api/platform-status');
                    const status = await response.json();
                    
                    // Atualizar status das plataformas
                    this.updatePlatformStatus('ml-status', status.mercadolivre);
                    this.updatePlatformStatus('loja-status', status.loja_integrada);
                } catch (error) {
                    console.error('Erro ao verificar status:', error);
                }
            }
            
            updatePlatformStatus(elementId, isConnected) {
                const element = document.getElementById(elementId);
                if (isConnected) {
                    element.textContent = 'Conectado ✓';
                    element.className = 'status-connected';
                } else {
                    element.textContent = 'Desconectado';
                    element.className = 'status-disconnected';
                }
            }

            setupEventListeners() {
                document.addEventListener('keydown', (e) => {
                    if (e.key >= '0' && e.key <= '9') {
                        this.addDigit(e.key);
                        e.preventDefault();
                    } else if (e.key === 'Enter') {
                        this.processBip();
                        e.preventDefault();
                    } else if (e.key === 'Backspace') {
                        this.removeLastDigit();
                        e.preventDefault();
                    } else if (e.key === 'Escape') {
                        this.clearBarcode();
                        e.preventDefault();
                    }
                });

                document.getElementById('clear-btn').addEventListener('click', () => this.clearBarcode());
                document.getElementById('process-btn').addEventListener('click', () => this.processBip());
            }

            addDigit(digit) {
                if (this.isProcessing) return;
                
                if (this.currentBarcode.length < 11) {
                    this.currentBarcode += digit;
                    this.updateBarcodeDisplay();
                    
                    if (this.currentBarcode.length === 11) {
                        setTimeout(() => this.processBip(), 800);
                    }
                }
            }

            removeLastDigit() {
                if (this.isProcessing) return;
                this.currentBarcode = this.currentBarcode.slice(0, -1);
                this.updateBarcodeDisplay();
            }

            clearBarcode() {
                if (this.isProcessing) return;
                this.currentBarcode = '';
                this.updateBarcodeDisplay();
                this.clearResult();
            }

            updateBarcodeDisplay() {
                const display = document.getElementById('barcode-display');
                
                if (this.currentBarcode) {
                    display.textContent = this.currentBarcode;
                } else {
                    display.textContent = 'Aguardando código de barras...';
                }

                document.getElementById('digit-counter').textContent = `${this.currentBarcode.length}/11 dígitos`;
                document.getElementById('process-btn').disabled = this.currentBarcode.length !== 11;
            }

            async processBip() {
                if (this.isProcessing || this.currentBarcode.length !== 11) {
                    return;
                }

                this.isProcessing = true;
                this.showProcessing();

                try {
                    const response = await fetch('/api/bip', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify({
                            barcode: this.currentBarcode
                        })
                    });

                    const result = await response.json();

                    if (result.status === 'success') {
                        this.showSuccess(result.data);
                    } else {
                        this.showError(result.message || 'Erro desconhecido');
                    }

                } catch (error) {
                    console.error('Erro no processamento:', error);
                    this.showError('Erro de conexão: ' + error.message);
                } finally {
                    this.isProcessing = false;
                    this.hideProcessing();
                    
                    setTimeout(() => {
                        this.clearBarcode();
                    }, 8000);
                }
            }

            showProcessing() {
                const display = document.getElementById('barcode-display');
                display.innerHTML = `
                    <div style="color: #007bff;">
                        🔍 Buscando nas APIs reais...<br>
                        <small style="font-size: 0.7em;">Consultando Mercado Livre e Loja Integrada</small>
                    </div>
                `;

                const processBtn = document.getElementById('process-btn');
                processBtn.disabled = true;
                processBtn.innerHTML = '⏳ Processando...';
            }

            hideProcessing() {
                const processBtn = document.getElementById('process-btn');
                processBtn.disabled = false;
                processBtn.innerHTML = '🔍 Processar Código';
            }

            showSuccess(data) {
                const resultDiv = document.getElementById('bip-result');
                resultDiv.innerHTML = `
                    <div class="result-success">
                        <h3>✅ Produto Encontrado nas APIs Reais!</h3>
                        <p><strong>Plataforma:</strong> ${data.platform}</p>
                        <p><strong>Produto:</strong> ${data.product_name}</p>
                        <p><strong>Preço:</strong> R$ ${parseFloat(data.price || 0).toFixed(2)}</p>
                        <p><strong>SKU:</strong> ${data.sku}</p>
                        ${data.buyer_name ? `<p><strong>Comprador:</strong> ${data.buyer_name}</p>` : ''}
                        ${data.order_id ? `<p><strong>Pedido:</strong> ${data.order_id}</p>` : ''}
                        <small style="color: #155724;">✓ Dados obtidos via OAuth das APIs reais</small>
                    </div>
                `;
                resultDiv.style.display = 'block';
            }

            showError(message) {
                const resultDiv = document.getElementById('bip-result');
                resultDiv.innerHTML = `
                    <div class="result-error">
                        <h3>❌ Erro no Processamento</h3>
                        <p>${message}</p>
                        <small>Configure as integrações OAuth em "Configurações"</small>
                    </div>
                `;
                resultDiv.style.display = 'block';
            }

            clearResult() {
                const resultDiv = document.getElementById('bip-result');
                resultDiv.style.display = 'none';
                resultDiv.innerHTML = '';
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            console.log('🚀 Iniciando Sistema de Bipagem com OAuth Real no Railway...');
            new BipagemSystemOAuth();
        });
    </script>
</body>
</html>
"""

SETUP_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configurações OAuth - Sistema de Bipagem</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .domain-info {
            background: linear-gradient(135deg, #d1ecf1, #bee5eb);
            border: 2px solid #17a2b8;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .platform-config {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
        }
        
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #007bff, #0056b3);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,123,255,0.3);
        }
        
        .instructions {
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            border-left: 5px solid #ffc107;
        }
        
        .callback-info {
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            padding: 20px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 4px solid #28a745;
        }
        
        .callback-info code {
            background: white;
            padding: 3px 8px;
            border-radius: 4px;
            color: #155724;
            font-weight: bold;
        }
        
        .navigation {
            text-align: center;
            margin-top: 30px;
        }
        
        .nav-link {
            color: #007bff;
            text-decoration: none;
            padding: 12px 25px;
            border: 2px solid #007bff;
            border-radius: 10px;
            margin: 0 10px;
            transition: all 0.3s;
            font-weight: bold;
        }
        
        .nav-link:hover {
            background: linear-gradient(45deg, #007bff, #0056b3);
            color: white;
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ Configurações OAuth</h1>
            <p>Configure suas integrações reais com as plataformas</p>
        </div>
        
        <div class="domain-info">
            <h3>🌐 Domínio Configurado</h3>
            <p><strong>www.masterhotelaria.com.br</strong></p>
            <small>Todas as URLs de callback estão configuradas para este domínio</small>
        </div>
        
        <div class="instructions">
            <h3>📋 Como Configurar OAuth Real</h3>
            <p>Para cada plataforma, você precisa criar uma aplicação e usar as URLs de callback corretas:</p>
        </div>
        
        <div class="platform-config">
            <h3>🛒 Mercado Livre</h3>
            <div class="callback-info">
                <strong>URL de Callback:</strong><br>
                <code>https://www.masterhotelaria.com.br/oauth/callback/mercadolivre</code>
            </div>
            <p><strong>Passos:</strong></p>
            <ol>
                <li>Acesse <a href="https://developers.mercadolivre.com.br" target="_blank">developers.mercadolivre.com.br</a></li>
                <li>Crie uma aplicação com a URL de callback acima</li>
                <li>Copie o Client ID e Client Secret</li>
                <li>Cole abaixo e clique "Conectar"</li>
            </ol>
            <form id="ml-form">
                <div class="form-group">
                    <label>Client ID:</label>
                    <input type="text" id="ml-client-id" placeholder="Seu Client ID do Mercado Livre">
                </div>
                <div class="form-group">
                    <label>Client Secret:</label>
                    <input type="password" id="ml-client-secret" placeholder="Seu Client Secret do Mercado Livre">
                </div>
                <button type="submit" class="btn btn-primary">Conectar com Mercado Livre</button>
            </form>
        </div>
        
        <div class="platform-config">
            <h3>🏪 Loja Integrada</h3>
            <div class="callback-info">
                <strong>URL de Callback:</strong><br>
                <code>https://www.masterhotelaria.com.br/oauth/callback/loja-integrada</code>
            </div>
            <p><strong>Passos:</strong></p>
            <ol>
                <li>Acesse <a href="https://developers.awsli.com.br" target="_blank">developers.awsli.com.br</a></li>
                <li>Crie uma aplicação com a URL de callback acima</li>
                <li>Copie o Client ID e Client Secret</li>
                <li>Cole abaixo e clique "Conectar"</li>
            </ol>
            <form id="loja-form">
                <div class="form-group">
                    <label>Client ID:</label>
                    <input type="text" id="loja-client-id" placeholder="Seu Client ID da Loja Integrada">
                </div>
                <div class="form-group">
                    <label>Client Secret:</label>
                    <input type="password" id="loja-client-secret" placeholder="Seu Client Secret da Loja Integrada">
                </div>
                <button type="submit" class="btn btn-primary">Conectar com Loja Integrada</button>
            </form>
        </div>
        
        <div class="navigation">
            <a href="/" class="nav-link">🏠 Início</a>
            <a href="/reports" class="nav-link">📊 Relatórios</a>
        </div>
    </div>

    <script>
        // Configuração OAuth das plataformas
        document.getElementById('ml-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const clientId = document.getElementById('ml-client-id').value;
            const clientSecret = document.getElementById('ml-client-secret').value;
            
            if (!clientId || !clientSecret) {
                alert('Preencha todos os campos do Mercado Livre');
                return;
            }
            
            try {
                const response = await fetch('/api/oauth/setup/mercadolivre', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({client_id: clientId, client_secret: clientSecret})
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('Configuração salva! Redirecionando para autorização...');
                    window.location.href = result.auth_url;
                } else {
                    alert('Erro ao salvar configuração: ' + result.message);
                }
            } catch (error) {
                alert('Erro de conexão: ' + error.message);
            }
        });
        
        document.getElementById('loja-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const clientId = document.getElementById('loja-client-id').value;
            const clientSecret = document.getElementById('loja-client-secret').value;
            
            if (!clientId || !clientSecret) {
                alert('Preencha todos os campos da Loja Integrada');
                return;
            }
            
            try {
                const response = await fetch('/api/oauth/setup/loja-integrada', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({client_id: clientId, client_secret: clientSecret})
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('Configuração salva! Redirecionando para autorização...');
                    window.location.href = result.auth_url;
                } else {
                    alert('Erro ao salvar configuração: ' + result.message);
                }
            } catch (error) {
                alert('Erro de conexão: ' + error.message);
            }
        });
    </script>
</body>
</html>
"""

# Rotas Flask
@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/setup')
def setup_page():
    return render_template_string(SETUP_HTML)

@app.route('/reports')
def reports_page():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatórios - Sistema de Bipagem</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                padding: 40px;
                max-width: 1000px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                margin-bottom: 40px;
            }
            .nav-link {
                color: #007bff;
                text-decoration: none;
                padding: 12px 25px;
                border: 2px solid #007bff;
                border-radius: 10px;
                margin: 0 10px;
                transition: all 0.3s;
                font-weight: bold;
            }
            .nav-link:hover {
                background: linear-gradient(45deg, #007bff, #0056b3);
                color: white;
                transform: translateY(-2px);
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                padding: 25px;
                border-radius: 15px;
                text-align: center;
                border-left: 5px solid #007bff;
            }
            .stat-number {
                font-size: 2em;
                font-weight: bold;
                color: #007bff;
            }
            .stat-label {
                color: #666;
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Relatórios OAuth</h1>
                <p>Estatísticas das integrações reais</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-bipagens">0</div>
                    <div class="stat-label">Total de Bipagens</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="bipagens-hoje">0</div>
                    <div class="stat-label">Bipagens Hoje</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="valor-total">R$ 0,00</div>
                    <div class="stat-label">Valor Total</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="plataformas-conectadas">0</div>
                    <div class="stat-label">Plataformas Conectadas</div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <a href="/" class="nav-link">🏠 Voltar ao Sistema</a>
                <a href="/setup" class="nav-link">⚙️ Configurações</a>
            </div>
        </div>
        
        <script>
            // Carregar estatísticas
            fetch('/api/reports')
                .then(response => response.json())
                .then(data => {
                    const total = data.recentes.length;
                    const hoje = data.recentes.filter(b => {
                        const hoje = new Date().toDateString();
                        const bipData = new Date(b.timestamp).toDateString();
                        return hoje === bipData;
                    }).length;
                    
                    const valorTotal = data.recentes.reduce((sum, b) => sum + (b.price || 0), 0);
                    
                    document.getElementById('total-bipagens').textContent = total;
                    document.getElementById('bipagens-hoje').textContent = hoje;
                    document.getElementById('valor-total').textContent = `R$ ${valorTotal.toFixed(2)}`;
                })
                .catch(error => console.error('Erro ao carregar relatórios:', error));
                
            // Verificar plataformas conectadas
            fetch('/api/platform-status')
                .then(response => response.json())
                .then(status => {
                    const conectadas = Object.values(status).filter(Boolean).length;
                    document.getElementById('plataformas-conectadas').textContent = conectadas;
                })
                .catch(error => console.error('Erro ao verificar status:', error));
        </script>
    </body>
    </html>
    """)

@app.route('/api/platform-status')
def platform_status():
    """Verifica status das plataformas"""
    ml_token = get_oauth_token('mercadolivre')
    loja_token = get_oauth_token('loja_integrada')
    
    return jsonify({
        'mercadolivre': bool(ml_token and ml_token['access_token']),
        'loja_integrada': bool(loja_token and loja_token['access_token']),
        'shopee': False  # Em desenvolvimento
    })

@app.route('/api/oauth/setup/mercadolivre', methods=['POST'])
def setup_mercadolivre():
    """Configura OAuth do Mercado Livre"""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        if not client_id or not client_secret:
            return jsonify({'success': False, 'message': 'Dados incompletos'})
        
        # Salvar configuração com domínio público
        redirect_uri = save_platform_config('mercadolivre', client_id, client_secret)
        
        # Gerar URL de autorização
        auth_url = ml_api.get_auth_url(client_id, redirect_uri)
        
        return jsonify({'success': True, 'auth_url': auth_url})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/oauth/setup/loja-integrada', methods=['POST'])
def setup_loja_integrada():
    """Configura OAuth da Loja Integrada"""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        if not client_id or not client_secret:
            return jsonify({'success': False, 'message': 'Dados incompletos'})
        
        # Salvar configuração com domínio público
        redirect_uri = save_platform_config('loja_integrada', client_id, client_secret)
        
        # Gerar URL de autorização
        auth_url = loja_api.get_auth_url(client_id, redirect_uri)
        
        return jsonify({'success': True, 'auth_url': auth_url})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/oauth/callback/mercadolivre')
def oauth_callback_ml():
    """Callback OAuth Mercado Livre"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return f"Erro na autorização: {error}"
    
    if not code:
        return "Erro: Código de autorização não recebido"
    
    try:
        # Buscar configuração
        config = get_platform_config('mercadolivre')
        if not config:
            return "Erro: Configuração não encontrada"
        
        # Trocar código por token
        token_data = ml_api.exchange_code_for_token(
            code, config['client_id'], config['client_secret'], config['redirect_uri']
        )
        
        if token_data and 'access_token' in token_data:
            # Salvar token
            save_oauth_token(
                'mercadolivre',
                token_data['access_token'],
                token_data.get('refresh_token'),
                token_data.get('expires_in'),
                token_data.get('user_id')
            )
            
            # Buscar info do usuário para confirmar
            user_info = ml_api.get_user_info(token_data['access_token'])
            user_name = user_info.get('nickname', 'Usuário') if user_info else 'Usuário'
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mercado Livre Conectado</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: #28a745; font-size: 24px; margin-bottom: 20px; }}
                    .btn {{ background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="success">✅ Mercado Livre Conectado com Sucesso!</div>
                <p>Usuário: <strong>{user_name}</strong></p>
                <p>Agora você pode bipar códigos e buscar produtos reais da sua conta.</p>
                <a href="/" class="btn">Voltar ao Sistema</a>
            </body>
            </html>
            """
        else:
            return "Erro ao obter token de acesso do Mercado Livre"
            
    except Exception as e:
        return f"Erro no callback: {str(e)}"

@app.route('/oauth/callback/loja-integrada')
def oauth_callback_loja():
    """Callback OAuth Loja Integrada"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return f"Erro na autorização: {error}"
    
    if not code:
        return "Erro: Código de autorização não recebido"
    
    try:
        # Buscar configuração
        config = get_platform_config('loja_integrada')
        if not config:
            return "Erro: Configuração não encontrada"
        
        # Trocar código por token
        token_data = loja_api.exchange_code_for_token(
            code, config['client_id'], config['client_secret'], config['redirect_uri']
        )
        
        if token_data and 'access_token' in token_data:
            # Salvar token
            save_oauth_token(
                'loja_integrada',
                token_data['access_token'],
                token_data.get('refresh_token'),
                token_data.get('expires_in')
            )
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Loja Integrada Conectada</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: #28a745; font-size: 24px; margin-bottom: 20px; }}
                    .btn {{ background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="success">✅ Loja Integrada Conectada com Sucesso!</div>
                <p>Agora você pode bipar códigos e buscar produtos reais da sua loja.</p>
                <a href="/" class="btn">Voltar ao Sistema</a>
            </body>
            </html>
            """
        else:
            return "Erro ao obter token de acesso da Loja Integrada"
            
    except Exception as e:
        return f"Erro no callback: {str(e)}"

@app.route('/api/bip', methods=['POST'])
def handle_bip():
    """Processa bipagem com APIs reais"""
    try:
        data = request.get_json()
        barcode = data.get('barcode')
        
        if not barcode:
            return jsonify({"status": "error", "message": "Código não fornecido"}), 400

        result = None
        
        # 1. Tentar Mercado Livre
        ml_token = get_oauth_token('mercadolivre')
        if ml_token and ml_token['access_token']:
            try:
                product = ml_api.search_product_by_barcode(barcode, ml_token['access_token'])
                if product:
                    result = {
                        'platform': 'Mercado Livre',
                        'product_id': product['product_id'],
                        'product_name': product['title'],
                        'price': product['price'],
                        'image_url': product['thumbnail'],
                        'sku': barcode,
                        'buyer_name': None,
                        'order_id': None
                    }
            except Exception as e:
                print(f"Erro ML: {e}")
        
        # 2. Tentar Loja Integrada
        if not result:
            loja_token = get_oauth_token('loja_integrada')
            if loja_token and loja_token['access_token']:
                try:
                    product = loja_api.search_product_by_sku(barcode, loja_token['access_token'])
                    if product:
                        result = {
                            'platform': 'Loja Integrada',
                            'product_id': str(product.get('id')),
                            'product_name': product.get('nome'),
                            'price': float(product.get('preco', 0)),
                            'image_url': product.get('imagem'),
                            'sku': product.get('sku'),
                            'buyer_name': None,
                            'order_id': None
                        }
                except Exception as e:
                    print(f"Erro Loja Integrada: {e}")
        
        # 3. Se não encontrou, retornar erro
        if not result:
            return jsonify({
                "status": "error", 
                "message": "Produto não encontrado nas plataformas conectadas. Configure as integrações OAuth."
            }), 404

        # Salvar no banco
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bipagens (barcode, platform, product_id, product_name, sku, price, buyer_name, order_id, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (barcode, result['platform'], result['product_id'], result['product_name'], 
              result['sku'], result['price'], result['buyer_name'], result['order_id'], result['image_url']))
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "data": result})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reports')
def get_reports():
    """Relatórios de bipagens"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Bipagens recentes
    cursor.execute("SELECT * FROM bipagens ORDER BY timestamp DESC LIMIT 100")
    recentes = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        "recentes": recentes
    })

if __name__ == '__main__':
    print("🚀 Sistema de Bipagem - OAuth Real no Railway")
    print("=" * 60)
    print("🔗 Integração REAL com APIs das plataformas")
    print("🌐 Domínio: www.masterhotelaria.com.br")
    print("🔐 OAuth 2.0 funcionando")
    print("📊 Dados verdadeiros das suas contas")
    print("=" * 60)
    
    # Inicializar banco de dados
    init_db()
    print("✅ Banco de dados inicializado")
    
    print("🌐 Iniciando servidor no Railway...")
    print(f"📊 Porta: {PORT}")
    print("🔗 Callbacks configurados para www.masterhotelaria.com.br")
    print("=" * 60)
    
    # Rodar Flask
    app.run(debug=False, host='0.0.0.0', port=PORT)

