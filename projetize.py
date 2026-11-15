# projetize_completo.py - Sistema Para CFTV, Redes e muito mais...
import os
import json
import base64
import hashlib
from flask import Flask, render_template_string, request, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
from functools import wraps
import uuid
from datetime import datetime

app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # Para vídeos
app.config['SECRET_KEY'] = 'projetize-super-secret-key-2026'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ICONS_FOLDER = os.path.join(UPLOAD_FOLDER, 'icons')
BACKGROUNDS_FOLDER = os.path.join(UPLOAD_FOLDER, 'backgrounds')
DYNAMIC_BG_FOLDER = os.path.join(UPLOAD_FOLDER, 'dynamic_bg')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

for folder in [UPLOAD_FOLDER, ICONS_FOLDER, BACKGROUNDS_FOLDER, DYNAMIC_BG_FOLDER, STATIC_FOLDER]:
    os.makedirs(folder, exist_ok=True)

USERS_FILE = os.path.join(UPLOAD_FOLDER, 'users.json')
DYNAMIC_BG_CONFIG = os.path.join(UPLOAD_FOLDER, 'dynamic_bg_config.json')
DEFAULT_CONNECTIONS_FILE = os.path.join(UPLOAD_FOLDER, 'default_connections.json')
DEFAULT_CONFIG_FILE = os.path.join(UPLOAD_FOLDER, 'default_config.json')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    default = {'thiago03': {'password': hash_password('Thiago@000333'), 'role': 'master', 'created_at': datetime.now().isoformat()}}
    save_users(default)
    return default

def save_users(users_dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(users_dict, f, ensure_ascii=False, indent=2)

users = load_users()

def get_dev_image_base64():
    for path in [os.path.join(BASE_DIR, 'dev.png'), os.path.join(BASE_DIR, 'dev.jpg'), os.path.join(STATIC_FOLDER, 'dev.png')]:
        if os.path.exists(path):
            with open(path, 'rb') as f: return base64.b64encode(f.read()).decode('utf-8')
    return ""

dev_image_data = get_dev_image_base64()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'): return jsonify({'error': 'Não autorizado'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'): return jsonify({'error': 'Não autorizado'}), 401
        if session.get('role') not in ['admin', 'master']: return jsonify({'error': 'Permissão negada.'}), 403
        return f(*args, **kwargs)
    return decorated_function

def load_json_file(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return default_value

def save_json_file(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

DEFAULT_CONNECTIONS_CONFIG = {
    'Cabeadas': {
        'icon': '🔌',
        'connections': [
            {'name': 'CAT6', 'color': '#ffc107', 'icon': '🟡', 'type': 'cable', 'speed': '10 Gbps'},
            {'name': 'FIBRA', 'color': '#20c997', 'icon': '🔷', 'type': 'cable', 'speed': '10 Gbps'}
        ]
    },
    'Sem Fio': {
        'icon': '📶',
        'connections': [
            {'name': 'Wi-Fi', 'color': '#00aaff', 'icon': '📶', 'type': 'wireless', 'speed': '1 Gbps'}
        ]
    }
}

DEFAULT_CATEGORIES_CONFIG = {
    'Câmeras': {
        'icon': '🎥',
        'devices': [
            {'name': 'Câmera Dome', 'icon': '📹', 'type': 'camera', 'color': '#005f99'},
            {'name': 'Câmera Bullet', 'icon': '📹', 'type': 'camera', 'color': '#005f99'}
        ]
    },
    'Gravadores': {
        'icon': '💾',
        'devices': [
            {'name': 'NVR', 'icon': '💾', 'type': 'nvr', 'color': '#17a2b8'},
            {'name': 'DVR', 'icon': '💾', 'type': 'dvr', 'color': '#17a2b8'}
        ]
    },
    'Rede': {
        'icon': '🌐',
        'devices': [
            {'name': 'Router', 'icon': '📡', 'type': 'router', 'color': '#20c997'},
            {'name': 'Switch', 'icon': '🔌', 'type': 'switch', 'color': '#20c997'}
        ]
    }
}

# ==================== ROTAS ====================
@app.route('/api/upload_dynamic_bg', methods=['POST'])
@admin_required
def upload_dynamic_bg():
    data = request.json
    file_data = data.get('file', '')
    file_type = data.get('type', '')
    opacity = data.get('opacity', 0.3)
    
    if not file_data: return jsonify({'success': False}), 400
    
    try:
        if ',' in file_data: file_data = file_data.split(',', 1)[1]
        ext = '.mp4' if file_type == 'video' else ('.gif' if 'gif' in data.get('mimeType', '') else '.png')
        
        for old_file in os.listdir(DYNAMIC_BG_FOLDER):
            try: os.remove(os.path.join(DYNAMIC_BG_FOLDER, old_file))
            except: pass
        
        filename = f"dynamic_bg_{uuid.uuid4().hex}{ext}"
        with open(os.path.join(DYNAMIC_BG_FOLDER, filename), 'wb') as f:
            f.write(base64.b64decode(file_data))
        
        save_json_file(DYNAMIC_BG_CONFIG, {'filename': filename, 'type': file_type, 'opacity': float(opacity)})
        return jsonify({'success': True, 'url': f'/uploads/dynamic_bg/{filename}', 'type': file_type, 'opacity': opacity})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_dynamic_bg', methods=['GET'])
def get_dynamic_bg():
    config = load_json_file(DYNAMIC_BG_CONFIG, None)
    if config and os.path.exists(os.path.join(DYNAMIC_BG_FOLDER, config['filename'])):
        return jsonify({'success': True, 'url': f'/uploads/dynamic_bg/{config["filename"]}', 'type': config.get('type', 'image'), 'opacity': config.get('opacity', 0.3)})
    return jsonify({'success': False})

@app.route('/api/upload_icon', methods=['POST'])
@login_required
def upload_icon():
    data = request.json
    image_data = data.get('image', '')
    target_type = data.get('type', 'equipment')
    if not image_data: return jsonify({'success': False}), 400
    
    if ',' in image_data: image_data = image_data.split(',')[1]
    filename = f"{target_type}_{uuid.uuid4().hex}.png"
    with open(os.path.join(ICONS_FOLDER, filename), 'wb') as f:
        f.write(base64.b64decode(image_data))
    return jsonify({'success': True, 'filename': filename})

@app.route('/api/upload_dev_image', methods=['POST'])
@admin_required
def upload_dev_image():
    data = request.json
    image_data = data.get('image', '')
    if ',' in image_data: image_data = image_data.split(',')[1]
    with open(os.path.join(BASE_DIR, 'dev.png'), 'wb') as f:
        f.write(base64.b64decode(image_data))
    return jsonify({'success': True})

@app.route('/api/upload_background', methods=['POST'])
@login_required
def upload_background():
    data = request.json
    image_data = data.get('image', '')
    if ',' in image_data: image_data = image_data.split(',')[1]
    filename = f"bg_{uuid.uuid4().hex}.png"
    with open(os.path.join(BACKGROUNDS_FOLDER, filename), 'wb') as f:
        f.write(base64.b64decode(image_data))
    return jsonify({'success': True, 'url': f'/uploads/backgrounds/{filename}'})

@app.route('/api/save_global_categories', methods=['POST'])
@admin_required
def save_global_categories():
    save_json_file(DEFAULT_CONFIG_FILE, request.json.get('categories', {}))
    return jsonify({'success': True})

@app.route('/api/save_global_connections', methods=['POST'])
@admin_required
def save_global_connections():
    save_json_file(DEFAULT_CONNECTIONS_FILE, request.json.get('connections', {}))
    return jsonify({'success': True})

@app.route('/uploads/icons/<filename>')
def serve_icon(filename): return send_from_directory(ICONS_FOLDER, filename)

@app.route('/uploads/backgrounds/<filename>')
def serve_background(filename): return send_from_directory(BACKGROUNDS_FOLDER, filename)

@app.route('/uploads/dynamic_bg/<filename>')
def serve_dynamic_bg(filename): return send_from_directory(DYNAMIC_BG_FOLDER, filename)

@app.route('/api/default_config', methods=['GET'])
def get_default_config(): return jsonify({'success': True, 'config': load_json_file(DEFAULT_CONFIG_FILE, DEFAULT_CATEGORIES_CONFIG)})

@app.route('/api/default_connections', methods=['GET'])
def get_default_connections(): return jsonify({'success': True, 'config': load_json_file(DEFAULT_CONNECTIONS_FILE, DEFAULT_CONNECTIONS_CONFIG)})

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') in users and users[data['username']]['password'] == hash_password(data.get('password', '')):
        session['logged_in'] = True
        session['username'] = data['username']
        session['role'] = users[data['username']]['role']
        return jsonify({'success': True, 'role': users[data['username']]['role']})
    return jsonify({'success': False}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

# ==================== HTML TEMPLATE (CORRIGIDO E COMPLETO) ====================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Projetize - Sistema CFTV</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #0a0f18; overflow: hidden; height: 100vh; color: #e2e8f0; }
        :root { --accent: #00e5ff; --bg-dark: #0f172a; --bg-light: #1e293b; --border: #334155; }
        
        /* FUNDO DINÂMICO */
        #dynamicBgContainer { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; overflow: hidden; display: none; }
        #dynamicBgContainer.active { display: block; }
        #dynamicBgContainer video, #dynamicBgContainer img { position: absolute; top: 50%; left: 50%; min-width: 100%; min-height: 100%; transform: translate(-50%, -50%); object-fit: cover; opacity: 0.25; }
        .bg-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, rgba(10,15,24,0.95), rgba(15,23,42,0.9)); }

        /* LOGIN CORPORATIVO */
        #loginScreen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #050a14; display: flex; justify-content: center; align-items: center; z-index: 25000; }
        .grid-bg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background-image: linear-gradient(rgba(0,229,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.05) 1px, transparent 1px); background-size: 40px 40px; animation: gridMove 20s linear infinite; }
        @keyframes gridMove { 0% { transform: translateY(0); } 100% { transform: translateY(40px); } }
        .login-box { position: relative; z-index: 2; width: 100%; max-width: 420px; padding: 20px; animation: fadeUp 0.8s ease; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        .login-card { background: rgba(15,23,42,0.7); backdrop-filter: blur(20px); border-radius: 20px; padding: 40px; border: 1px solid rgba(0,229,255,0.15); box-shadow: 0 0 50px rgba(0,0,0,0.5); position: relative; }
        .login-card::before { content: ''; position: absolute; top: 0; left: 10%; right: 10%; height: 1px; background: linear-gradient(90deg, transparent, rgba(0,229,255,0.8), transparent); }
        .brand { display: flex; align-items: center; gap: 15px; margin-bottom: 30px; }
        .brand-icon { width: 50px; height: 50px; background: linear-gradient(135deg, rgba(0,229,255,0.2), rgba(0,150,255,0.1)); border-radius: 12px; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(0,229,255,0.3); font-size: 24px; }
        .brand h1 { font-size: 24px; font-weight: 800; color: #fff; letter-spacing: 2px; }
        .brand p { font-size: 11px; color: var(--accent); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; font-size: 12px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .form-input { width: 100%; padding: 14px 16px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: #fff; font-size: 14px; outline: none; transition: all 0.3s; }
        .form-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0,229,255,0.1); }
        .btn-login { width: 100%; padding: 14px; background: linear-gradient(135deg, #00e5ff, #0077ff); border: none; border-radius: 10px; color: #050a14; font-size: 15px; font-weight: 800; cursor: pointer; margin-top: 10px; transition: all 0.3s; letter-spacing: 1px; box-shadow: 0 4px 15px rgba(0,229,255,0.3); }
        .btn-login:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,229,255,0.5); }
        .footer-avatar { width: 40px; height: 40px; border-radius: 50%; border: 2px solid rgba(0,229,255,0.3); margin: 20px auto 10px; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #1e293b; }
        .footer-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .footer-text { font-size: 11px; color: #64748b; text-align: center; line-height: 1.6; }
        .footer-text strong { color: var(--accent); }

        /* UI PRINCIPAL */
        #appScreen { display: none; height: 100vh; flex-direction: column; position: relative; z-index: 1; }
        .toolbar { background: #1e293b; padding: 10px 20px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; border-bottom: 1px solid #334155; }
        .btn { padding: 8px 14px; border: 1px solid #334155; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; background: #0f172a; color: #e2e8f0; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        .btn:hover { background: #334155; border-color: var(--accent); }
        .btn-primary { background: rgba(0,229,255,0.1); border-color: rgba(0,229,255,0.3); color: var(--accent); }
        .main-layout { display: flex; flex: 1; overflow: hidden; }
        
        .sidebar { width: 260px; background: #0f172a; border-right: 1px solid #334155; overflow-y: auto; padding: 15px; flex-shrink: 0; }
        .sidebar h3 { font-size: 12px; color: var(--accent); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; border-bottom: 1px solid #334155; padding-bottom: 5px; }
        .device-item { background: #1e293b; border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; cursor: grab; display: flex; align-items: center; gap: 8px; border: 1px solid transparent; }
        .device-item:hover { border-color: var(--accent); }
        .device-item span { font-size: 18px; }
        .device-item div { font-size: 12px; font-weight: 600; }
        
        .canvas-area { flex: 1; background: #000; overflow: auto; position: relative; }
        #canvas { display: block; background: transparent; cursor: crosshair; transform-origin: 0 0; }
        
        .properties-panel { width: 0; background: #0f172a; border-left: 1px solid #334155; overflow-y: auto; transition: width 0.3s; flex-shrink: 0; }
        .properties-panel.open { width: 280px; padding: 15px; }
        .property-group { margin-bottom: 15px; }
        .property-group label { display: block; font-size: 11px; color: var(--accent); margin-bottom: 5px; text-transform: uppercase; }
        .property-group input { width: 100%; padding: 8px; background: #1e293b; border: 1px solid #334155; border-radius: 6px; color: #fff; font-size: 12px; }
        
        .toast { position: fixed; bottom: 20px; right: 20px; background: #1e293b; color: #fff; padding: 12px 20px; border-radius: 8px; border-left: 4px solid var(--accent); z-index: 4000; animation: slideIn 0.3s; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        
        .loading { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #050a14; z-index: 30000; display: none; flex-direction: column; justify-content: center; align-items: center; }
        .spinner { width: 40px; height: 40px; border: 3px solid rgba(0,229,255,0.1); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <!-- Fundo Dinâmico -->
    <div id="dynamicBgContainer">
        <video id="bgVideo" autoplay loop muted playsinline style="display:none;"></video>
        <img id="bgImage" src="" style="display:none;">
        <div class="bg-overlay"></div>
    </div>

    <!-- Loading -->
    <div class="loading" id="loadingOverlay">
        <div class="spinner"></div>
        <div style="margin-top: 20px; color: var(--accent); font-weight: bold; letter-spacing: 2px;">INICIALIZANDO</div>
    </div>

    <!-- TELA DE LOGIN CORPORATIVA -->
    <div id="loginScreen">
        <div class="grid-bg"></div>
        <div class="login-box">
            <div class="login-card">
                <div class="brand">
                    <div class="brand-icon">🛡️</div>
                    <div>
                        <h1>PROJETIZE</h1>
                        <p>Infraestrutura & Redes</p>
                    </div>
                </div>
                <div class="form-group">
                    <label>Usuário</label>
                    <input type="text" id="loginUser" class="form-input" placeholder="Digite seu usuário">
                </div>
                <div class="form-group">
                    <label>Senha</label>
                    <input type="password" id="loginPass" class="form-input" placeholder="Digite sua senha">
                </div>
                <button class="btn-login" onclick="fazerLogin()">Acessar Painel</button>
                <div class="footer-avatar" id="devAvatar">
                    <span style="color:var(--accent); font-weight:bold;">TS</span>
                </div>
                <div class="footer-text">
                    Desenvolvido por <strong>Thiago Souza</strong><br>
                    Analista de Tecnologia | Unidade 2 - São José do Rio Preto<br>
                    Todos os direitos reservados © 2026
                </div>
            </div>
        </div>
    </div>

    <!-- TELA PRINCIPAL DO SISTEMA -->
    <div id="appScreen">
        <div class="toolbar">
            <button class="btn btn-primary" onclick="novoProjeto()">📁 Novo</button>
            <button class="btn btn-primary" onclick="salvarProjeto()">💾 Salvar</button>
            <button class="btn btn-primary" onclick="carregarProjeto()">📂 Carregar</button>
            <button class="btn btn-primary" onclick="carregarPlanta()">🖼️ Planta</button>
            <button class="btn btn-primary" id="btnFundo" onclick="configurarFundo()" style="display:none;">🎬 Fundo</button>
            <button class="btn btn-primary" id="btnDev" onclick="configurarDev()" style="display:none;">📸 Dev</button>
            <span style="flex:1"></span>
            <span style="font-size:11px; color:#64748b;">Zoom</span>
            <button class="btn" onclick="zoomIn()">+</button>
            <button class="btn" onclick="zoomOut()">-</button>
            <button class="btn" style="border-color:#ef4444; color:#ef4444;" onclick="sair()">Sair</button>
        </div>
        <div class="main-layout">
            <div class="sidebar" id="sidebar">
                <div id="listaDispositivos"></div>
                <hr style="border-color:#334155; margin:20px 0;">
                <div id="listaConexoes"></div>
            </div>
            <div class="canvas-area">
                <canvas id="canvas" width="4000" height="3000"></canvas>
            </div>
            <div class="properties-panel" id="propertiesPanel">
                <h3 style="color:var(--accent); font-size:14px; margin-bottom:15px;">Propriedades</h3>
                <div id="propsContent"><p style="color:#64748b; font-size:12px;">Selecione um item.</p></div>
            </div>
        </div>
    </div>

    <script>
        // ==================== ESTADO GLOBAL ====================
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        let dispositivos = [];
        let conexoes = [];
        let categorias = {};
        let conexoesCategorias = {};
        let coresCabos = {};
        let dispositivoSelecionado = null;
        let conexaoSelecionada = null;
        let arrastando = false;
        let arrastandoWaypoint = false;
        let waypointConnIdx = null;
        let waypointIdx = null;
        let dragOffset = {x:0, y:0};
        let zoom = 1;
        let usuarioAtual = null;
        let perfilUsuario = null;
        let plantaImg = null;
        let plantaX = 0, plantaY = 0, plantaW = 0, plantaH = 0;
        
        const cacheImagens = {};
        function getImgCached(src) {
            if (!cacheImagens[src]) {
                const img = new Image();
                img.src = src;
                cacheImagens[src] = img;
            }
            return cacheImagens[src];
        }

        const devBase64 = '""" + dev_image_data + """';

        // ==================== LOGIN ====================
        async function fazerLogin() {
            const u = document.getElementById('loginUser').value;
            const p = document.getElementById('loginPass').value;
            const res = await fetch('/api/login', {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({username: u, password: p})
            });
            const data = await res.json();
            if (data.success) {
                usuarioAtual = u; perfilUsuario = data.role;
                document.getElementById('loginScreen').style.display = 'none';
                document.getElementById('appScreen').style.display = 'flex';
                document.getElementById('loadingOverlay').style.display = 'flex';
                
                if (data.role === 'admin' || data.role === 'master') {
                    document.getElementById('btnFundo').style.display = 'inline-block';
                    document.getElementById('btnDev').style.display = 'inline-block';
                }
                
                await carregarConfiguracoes();
                carregarDadosLocais();
                document.getElementById('loadingOverlay').style.display = 'none';
                iniciarRenderizacao(); // INICIA O LOOP AQUI
                mostrarToast('Bem-vindo, ' + u);
            } else {
                alert('Credenciais inválidas');
            }
        }
        
        function sair() { fetch('/api/logout', {method:'POST'}).then(()=>location.reload()); }

        // ==================== CARREGAR DADOS ====================
        async function carregarConfiguracoes() {
            try {
                const r1 = await fetch('/api/default_config');
                const d1 = await r1.json();
                if (d1.success) categorias = d1.config;
                
                const r2 = await fetch('/api/default_connections');
                const d2 = await r2.json();
                if (d2.success) {
                    conexoesCategorias = d2.config;
                    for (let cat of Object.values(d2.config)) {
                        for (let c of cat.connections) {
                            coresCabos[c.name.toLowerCase().replace(/[^a-z0-9]/g, '')] = c;
                        }
                    }
                }
                renderizarSidebar();
            } catch(e) { console.error(e); }
        }
        
        function carregarDadosLocais() {
            if (!usuarioAtual) return;
            const disp = localStorage.getItem('projetize_' + usuarioAtual + '_dispositivos');
            if (disp) dispositivos = JSON.parse(disp);
            const con = localStorage.getItem('projetize_' + usuarioAtual + '_conexoes');
            if (con) conexoes = JSON.parse(con);
            const pl = localStorage.getItem('projetize_' + usuarioAtual + '_planta');
            if (pl) {
                const p = JSON.parse(pl);
                if (p.url) {
                    plantaImg = new Image();
                    plantaImg.src = p.url;
                    plantaImg.onload = () => { plantaW = p.w; plantaH = p.h; plantaX = p.x; plantaY = p.y; };
                }
            }
        }
        
        function salvarDadosLocais() {
            if (!usuarioAtual) return;
            localStorage.setItem('projetize_' + usuarioAtual + '_dispositivos', JSON.stringify(dispositivos));
            localStorage.setItem('projetize_' + usuarioAtual + '_conexoes', JSON.stringify(conexoes));
            if (plantaImg) {
                localStorage.setItem('projetize_' + usuarioAtual + '_planta', JSON.stringify({url: plantaImg.src, w: plantaW, h: plantaH, x: plantaX, y: plantaY}));
            }
        }

        // ==================== SIDEBAR ====================
        function renderizarSidebar() {
            const divDisp = document.getElementById('listaDispositivos');
            divDisp.innerHTML = '<h3>Equipamentos</h3>';
            for (let [catNome, catData] of Object.entries(categorias)) {
                const catDiv = document.createElement('div');
                catDiv.innerHTML = `<h3 style="margin-top:15px;">${catData.icon} ${catNome}</h3>`;
                catData.devices.forEach(dev => {
                    const el = document.createElement('div');
                    el.className = 'device-item';
                    el.draggable = true;
                    el.innerHTML = `<span>${dev.icon}</span><div>${dev.name}</div>`;
                    el.addEventListener('dragstart', (e) => {
                        e.dataTransfer.setData('text/plain', JSON.stringify(dev));
                    });
                    catDiv.appendChild(el);
                });
                divDisp.appendChild(catDiv);
            }
            
            const divCon = document.getElementById('listaConexoes');
            divCon.innerHTML = '<h3>Conexões</h3>';
            for (let [catNome, catData] of Object.entries(conexoesCategorias)) {
                const catDiv = document.createElement('div');
                catDiv.innerHTML = `<h3 style="margin-top:15px;">${catData.icon} ${catNome}</h3>`;
                catData.connections.forEach(con => {
                    const el = document.createElement('div');
                    el.className = 'device-item';
                    el.innerHTML = `<span style="color:${con.color}">${con.icon}</span><div>${con.name}</div>`;
                    catDiv.appendChild(el);
                });
                divCon.appendChild(catDiv);
            }
        }

        // ==================== RENDERIZAÇÃO DO CANVAS ====================
        function iniciarRenderizacao() {
            requestAnimationFrame(loopRender);
        }
        
        function loopRender() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Desenha Planta
            if (plantaImg && plantaImg.complete && plantaW > 0) {
                ctx.globalAlpha = 0.8;
                ctx.drawImage(plantaImg, plantaX, plantaY, plantaW, plantaH);
                ctx.globalAlpha = 1;
            }
            
            // Desenha Conexões
            conexoes.forEach((conn, idx) => {
                const de = dispositivos.find(d => d.id === conn.de);
                const para = dispositivos.find(d => d.id === conn.para);
                if (!de || !para) return;
                
                const infoCabo = coresCabos[conn.tipo.toLowerCase().replace(/[^a-z0-9]/g, '')] || {color: '#00e5ff'};
                const selecionada = (conexaoSelecionada === idx);
                
                ctx.beginPath();
                ctx.strokeStyle = infoCabo.color;
                ctx.lineWidth = selecionada ? 4 : 2;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                
                if (conn.waypoints && conn.waypoints.length > 0) {
                    ctx.moveTo(de.x, de.y);
                    conn.waypoints.forEach(wp => ctx.lineTo(wp.x, wp.y));
                    ctx.lineTo(para.x, para.y);
                } else {
                    ctx.moveTo(de.x, de.y);
                    ctx.lineTo(para.x, para.y);
                }
                ctx.stroke();
                
                // Desenha handles dos waypoints se selecionado
                if (selecionada && conn.waypoints) {
                    conn.waypoints.forEach((wp, wIdx) => {
                        ctx.beginPath();
                        ctx.arc(wp.x, wp.y, 8, 0, Math.PI * 2);
                        ctx.fillStyle = (arrastandoWaypoint && waypointIdx === wIdx) ? '#fff' : '#ffaa00';
                        ctx.fill();
                        ctx.strokeStyle = '#000';
                        ctx.lineWidth = 2;
                        ctx.stroke();
                    });
                }
            });
            
            // Desenha Dispositivos
            dispositivos.forEach(disp => {
                if (disp.iconFile) {
                    const img = getImgCached('/uploads/icons/' + disp.iconFile);
                    if (img.complete) {
                        ctx.drawImage(img, disp.x - 20, disp.y - 20, 40, 40);
                    }
                } else {
                    ctx.fillStyle = disp.color || '#1e293b';
                    ctx.beginPath();
                    ctx.arc(disp.x, disp.y, 20, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.fillStyle = '#fff';
                    ctx.font = '20px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(disp.icon || '📦', disp.x, disp.y);
                }
                
                ctx.fillStyle = '#e2e8f0';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(disp.name, disp.x, disp.y - 30);
                
                if (dispositivoSelecionado === disp) {
                    ctx.strokeStyle = '#00e5ff';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(disp.x - 24, disp.y - 24, 48, 48);
                }
            });
            
            requestAnimationFrame(loopRender);
        }

        // ==================== INTERAÇÃO (CURVAR CABO) ====================
        function getMousePos(e) {
            const rect = canvas.getBoundingClientRect();
            const cx = e.touches ? e.touches[0].clientX : e.clientX;
            const cy = e.touches ? e.touches[0].clientY : e.clientY;
            return {
                x: (cx - rect.left) / zoom,
                y: (cy - rect.top) / zoom
            };
        }

        function iniciarClique(e) {
            const {x, y} = getMousePos(e);
            
            // 1. Verifica se clicou em um waypoint de conexão selecionada
            if (conexaoSelecionada !== null) {
                const conn = conexoes[conexaoSelecionada];
                if (conn.waypoints) {
                    for (let i = 0; i < conn.waypoints.length; i++) {
                        if (Math.hypot(x - conn.waypoints[i].x, y - conn.waypoints[i].y) < 15) {
                            arrastandoWaypoint = true;
                            waypointConnIdx = conexaoSelecionada;
                            waypointIdx = i;
                            return;
                        }
                    }
                }
            }
            
            // 2. Verifica se clicou em um dispositivo
            for (let i = dispositivos.length - 1; i >= 0; i--) {
                const d = dispositivos[i];
                if (Math.hypot(x - d.x, y - d.y) < 25) {
                    dispositivoSelecionado = d;
                    conexaoSelecionada = null;
                    arrastando = true;
                    dragOffset = {x: d.x - x, y: d.y - y};
                    mostrarPropriedades(d);
                    return;
                }
            }
            
            // 3. Verifica se clicou em uma conexão (para curvar)
            for (let i = 0; i < conexoes.length; i++) {
                const conn = conexoes[i];
                const de = dispositivos.find(d => d.id === conn.de);
                const para = dispositivos.find(d => d.id === conn.para);
                if (!de || !para) continue;
                
                const dist = distanciaPontoLinha(x, y, de.x, de.y, para.x, para.y);
                if (dist < 15) {
                    conexaoSelecionada = i;
                    dispositivoSelecionado = null;
                    // Adiciona waypoint automaticamente no local do clique
                    if (!conn.waypoints) conn.waypoints = [];
                    conn.waypoints.push({x: x, y: y});
                    arrastandoWaypoint = true;
                    waypointConnIdx = i;
                    waypointIdx = conn.waypoints.length - 1;
                    mostrarPropriedadesConexao(i);
                    return;
                }
            }
            
            dispositivoSelecionado = null;
            conexaoSelecionada = null;
            fecharPropriedades();
        }

        function moverMouse(e) {
            const {x, y} = getMousePos(e);
            
            if (arrastandoWaypoint && waypointConnIdx !== null && waypointIdx !== null) {
                conexoes[waypointConnIdx].waypoints[waypointIdx] = {x, y};
                salvarDadosLocais();
            } else if (arrastando && dispositivoSelecionado) {
                dispositivoSelecionado.x = x + dragOffset.x;
                dispositivoSelecionado.y = y + dragOffset.y;
                salvarDadosLocais();
            }
        }

        function finalizarClique() {
            arrastando = false;
            arrastandoWaypoint = false;
            waypointConnIdx = null;
            waypointIdx = null;
        }

        function distanciaPontoLinha(px, py, x1, y1, x2, y2) {
            const A = px - x1, B = py - y1, C = x2 - x1, D = y2 - y1;
            const dot = A * C + B * D;
            const len_sq = C * C + D * D;
            let param = -1;
            if (len_sq != 0) param = dot / len_sq;
            let xx, yy;
            if (param < 0) { xx = x1; yy = y1; }
            else if (param > 1) { xx = x2; yy = y2; }
            else { xx = x1 + param * C; yy = y1 + param * D; }
            return Math.hypot(px - xx, py - yy);
        }

        // ==================== EVENTOS ====================
        canvas.addEventListener('mousedown', iniciarClique);
        canvas.addEventListener('mousemove', moverMouse);
        canvas.addEventListener('mouseup', finalizarClique);
        canvas.addEventListener('touchstart', (e) => { e.preventDefault(); iniciarClique(e); }, {passive:false});
        canvas.addEventListener('touchmove', (e) => { e.preventDefault(); moverMouse(e); }, {passive:false});
        canvas.addEventListener('touchend', finalizarClique);

        canvas.addEventListener('dragover', (e) => e.preventDefault());
        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            const {x, y} = getMousePos(e);
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            dispositivos.push({
                id: Date.now(),
                name: data.name,
                icon: data.icon,
                color: data.color,
                x: x,
                y: y,
                iconFile: null
            });
            salvarDadosLocais();
            mostrarToast('✅ ' + data.name + ' adicionado');
        });

        // ==================== UI (PROPRIEDADES) ====================
        function mostrarPropriedades(disp) {
            const div = document.getElementById('propsContent');
            div.innerHTML = `
                <div class="property-group"><label>Nome</label><input type="text" value="${disp.name}" onchange="atualizarNome(${disp.id}, this.value)"></div>
                <div class="property-group"><label>Posição X</label><input type="number" value="${Math.round(disp.x)}" onchange="atualizarX(${disp.id}, this.value)"></div>
                <div class="property-group"><label>Posição Y</label><input type="number" value="${Math.round(disp.y)}" onchange="atualizarY(${disp.id}, this.value)"></div>
            `;
            document.getElementById('propertiesPanel').classList.add('open');
        }

        function mostrarPropriedadesConexao(idx) {
            const div = document.getElementById('propsContent');
            div.innerHTML = `
                <p style="font-size:12px; color:#94a3b8;">Cabo selecionado.</p>
                <button class="btn" style="width:100%; margin-top:10px;" onclick="endireitarCabo(${idx})">📏 Endireitar Cabo</button>
                <p style="font-size:11px; color:#64748b; margin-top:10px;">Dica: Clique no cabo para adicionar pontos e arraste para curvar.</p>
            `;
            document.getElementById('propertiesPanel').classList.add('open');
        }

        function fecharPropriedades() { document.getElementById('propertiesPanel').classList.remove('open'); }
        
        window.endireitarCabo = (idx) => {
            conexoes[idx].waypoints = [];
            salvarDadosLocais();
            mostrarToast('Cabo endireitado');
        };
        
        window.atualizarNome = (id, v) => { dispositivos.find(d => d.id === id).name = v; salvarDadosLocais(); };
        window.atualizarX = (id, v) => { dispositivos.find(d => d.id === id).x = parseFloat(v); salvarDadosLocais(); };
        window.atualizarY = (id, v) => { dispositivos.find(d => d.id === id).y = parseFloat(v); salvarDadosLocais(); };

        // ==================== FUNÇÕES DE PROJETO ====================
        window.novoProjeto = () => {
            if (confirm('Criar novo projeto? Dados atuais serão perdidos.')) {
                dispositivos = []; conexoes = []; plantaImg = null;
                salvarDadosLocais(); mostrarToast('Novo projeto');
            }
        };

        window.salvarProjeto = () => {
            const data = {dispositivos, conexoes, planta: plantaImg ? {url: plantaImg.src, w: plantaW, h: plantaH, x: plantaX, y: plantaY} : null};
            const blob = new Blob([JSON.stringify(data)], {type:'application/json'});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'projeto.projetize'; a.click();
            mostrarToast('Projeto exportado');
        };

        window.carregarProjeto = () => {
            const input = document.createElement('input'); input.type = 'file'; input.accept = '.projetize,.json';
            input.onchange = (e) => {
                const reader = new FileReader();
                reader.onload = (ev) => {
                    const data = JSON.parse(ev.target.result);
                    dispositivos = data.dispositivos || [];
                    conexoes = data.conexoes || [];
                    if (data.planta) {
                        plantaImg = new Image(); plantaImg.src = data.planta.url;
                        plantaW = data.planta.w; plantaH = data.planta.h;
                        plantaX = data.planta.x; plantaY = data.planta.y;
                    }
                    salvarDadosLocais(); mostrarToast('Projeto carregado');
                };
                reader.readAsText(e.target.files[0]);
            };
            input.click();
        };

        window.carregarPlanta = () => {
            const input = document.createElement('input'); input.type = 'file'; input.accept = 'image/*';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                const reader = new FileReader();
                reader.onload = async (ev) => {
                    const res = await fetch('/api/upload_background', {
                        method:'POST', headers:{'Content-Type':'application/json'},
                        body: JSON.stringify({image: ev.target.result})
                    });
                    const data = await res.json();
                    if (data.success) {
                        plantaImg = new Image(); plantaImg.src = data.url;
                        plantaImg.onload = () => {
                            plantaW = plantaImg.width; plantaH = plantaImg.height;
                            plantaX = (canvas.width - plantaW) / 2; plantaY = (canvas.height - plantaH) / 2;
                            salvarDadosLocais(); mostrarToast('Planta carregada');
                        };
                    }
                };
                reader.readAsDataURL(file);
            };
            input.click();
        };

        window.configurarFundo = () => {
            const input = document.createElement('input'); input.type = 'file'; input.accept = 'image/gif, video/mp4, image/*';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                const reader = new FileReader();
                reader.onload = async (ev) => {
                    const isVideo = file.type.startsWith('video');
                    const res = await fetch('/api/upload_dynamic_bg', {
                        method:'POST', headers:{'Content-Type':'application/json'},
                        body: JSON.stringify({file: ev.target.result, type: isVideo ? 'video':'image', opacity: 0.25, mimeType: file.type})
                    });
                    const data = await res.json();
                    if (data.success) {
                        carregarFundoDinamico();
                        mostrarToast('Fundo atualizado');
                    }
                };
                reader.readAsDataURL(file);
            };
            input.click();
        };

        async function carregarFundoDinamico() {
            const res = await fetch('/api/get_dynamic_bg');
            const data = await res.json();
            if (data.success) {
                const container = document.getElementById('dynamicBgContainer');
                container.classList.add('active');
                if (data.type === 'video') {
                    const v = document.getElementById('bgVideo');
                    v.src = data.url; v.style.display = 'block'; v.style.opacity = data.opacity; v.play();
                    document.getElementById('bgImage').style.display = 'none';
                } else {
                    const img = document.getElementById('bgImage');
                    img.src = data.url; img.style.display = 'block'; img.style.opacity = data.opacity;
                    document.getElementById('bgVideo').style.display = 'none';
                }
            }
        }

        window.configurarDev = () => {
            const input = document.createElement('input'); input.type = 'file'; input.accept = 'image/*';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                const reader = new FileReader();
                reader.onload = async (ev) => {
                    const res = await fetch('/api/upload_dev_image', {
                        method:'POST', headers:{'Content-Type':'application/json'},
                        body: JSON.stringify({image: ev.target.result})
                    });
                    if (res.ok) { mostrarToast('Foto atualizada!'); setTimeout(()=>location.reload(), 1000); }
                };
                reader.readAsDataURL(file);
            };
            input.click();
        };

        window.zoomIn = () => { zoom += 0.1; canvas.style.transform = `scale(${zoom})`; };
        window.zoomOut = () => { zoom = Math.max(0.2, zoom - 0.1); canvas.style.transform = `scale(${zoom})`; };
        
        function mostrarToast(msg) {
            const t = document.createElement('div');
            t.className = 'toast'; t.innerText = msg;
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 3000);
        }

        // ==================== BOOT ====================
        if (devBase64) {
            const img = document.getElementById('devAvatar');
            img.innerHTML = `<img src="data:image/png;base64,${devBase64}" style="width:100%;height:100%;object-fit:cover;">`;
        }
        carregarFundoDinamico();
    </script>
</body>
</html>
"""
