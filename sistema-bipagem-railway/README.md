# Sistema de Bipagem Master Hotelaria v3.0 - Railway Deploy

## 🚀 Deploy no Railway

### Pré-requisitos:
1. Conta no Railway (railway.app)
2. Conta no GitHub (recomendado)

### Passo a Passo:

#### 1. Preparar Repositório GitHub
1. Crie um repositório no GitHub
2. Faça upload de todos os arquivos desta pasta
3. Commit e push

#### 2. Deploy no Railway
1. Acesse railway.app
2. Clique em "Start a New Project"
3. Selecione "Deploy from GitHub repo"
4. Escolha o repositório criado
5. Railway detecta automaticamente Python
6. Deploy automático em ~3 minutos

#### 3. Configurar Domínio Personalizado
1. No painel do Railway, vá em "Settings"
2. Na seção "Domains", clique em "Custom Domain"
3. Adicione: `bipagem.masterhotelaria.com.br`
4. Railway fornecerá um CNAME

#### 4. Configurar DNS no Registro.br
1. Acesse o painel do registro.br
2. Vá em "DNS" → "Zona de DNS"
3. Adicione registro CNAME:
   - **Nome:** bipagem
   - **Tipo:** CNAME
   - **Valor:** [valor fornecido pelo Railway]

#### 5. Configurar Mercado Livre
1. Acesse developers.mercadolivre.com.br
2. Vá em "Minhas Aplicações"
3. Configure redirect_uri:
   ```
   https://bipagem.masterhotelaria.com.br/oauth/callback/mercadolivre
   ```

### URLs Finais:
- **Sistema:** https://bipagem.masterhotelaria.com.br/
- **Configurações:** https://bipagem.masterhotelaria.com.br/config.html
- **Relatórios:** https://bipagem.masterhotelaria.com.br/reports.html

### Estrutura do Projeto:
```
sistema-bipagem-railway/
├── main.py              # Aplicação Flask principal
├── requirements.txt     # Dependências Python
├── Procfile            # Comando de inicialização
├── railway.json        # Configuração Railway
├── README.md           # Este arquivo
└── static/             # Arquivos frontend
    ├── index.html
    ├── config.html
    ├── reports.html
    ├── css/
    └── js/
```

### Logs e Monitoramento:
- Acesse os logs no painel do Railway
- Monitore performance e uso de recursos
- Railway oferece métricas detalhadas

### Suporte:
- Documentação Railway: docs.railway.app
- Suporte Railway: railway.app/help

