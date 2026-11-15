# projetize_completo.py - Sistema Para CFTV, Redes e muito mais...
import os
import json
import base64
import hashlib
import shutil
from flask import Flask, render_template_string, request, jsonify, send_file, send_from_directory, session, url_for
from werkzeug.utils import secure_filename
from functools import wraps
import uuid
from io import BytesIO
import html
import time
import threading
from datetime import datetime
import mimetypes
import math

app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['SECRET_KEY'] = 'projetize-super-secret-key-2026'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ICONS_FOLDER = os.path.join(UPLOAD_FOLDER, 'icons')
DEFAULT_ICONS_FOLDER = os.path.join(UPLOAD_FOLDER, 'default_icons')
BACKGROUNDS_FOLDER = os.path.join(UPLOAD_FOLDER, 'backgrounds')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ICONS_FOLDER, exist_ok=True)
os.makedirs(DEFAULT_ICONS_FOLDER, exist_ok=True)
os.makedirs(BACKGROUNDS_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

projects = {}
USERS_FILE = os.path.join(UPLOAD_FOLDER, 'users.json')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    default_users = {
        'thiago03': {
            'password': hash_password('Thiago@000333'),
            'role': 'master',
            'name': 'Thiago Souza',
            'created_at': datetime.now().isoformat()
        }
    }
    save_users(default_users)
    return default_users

def save_users(users_dict):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar usuários: {e}")
        return False

users = load_users()

def get_dev_image_base64():
    possible_paths = [
        os.path.join(BASE_DIR, 'dev.png'),
        os.path.join(BASE_DIR, 'dev.jpg'),
        os.path.join(STATIC_FOLDER, 'dev.png'),
        os.path.join(STATIC_FOLDER, 'dev.jpg'),
    ]
    for path in possible_paths:
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            pass
    return None

def get_default_avatar_svg():
    return '''<svg width="150" height="150" viewBox="0 0 150 150" xmlns="http://www.w3.org/2000/svg"><circle cx="75" cy="75" r="70" fill="#005f99" stroke="#00ccff" stroke-width="3"/><circle cx="75" cy="75" r="65" fill="none" stroke="#00ccff" stroke-width="1" stroke-dasharray="5,5"/><text x="75" y="85" font-family="Arial, sans-serif" font-size="40" font-weight="bold" fill="#ffffff" text-anchor="middle">TS</text><text x="75" y="110" font-family="Arial, sans-serif" font-size="12" fill="#00ccff" text-anchor="middle">Thiago Souza</text></svg>'''

dev_image_data = get_dev_image_base64() or ""
if not dev_image_data:
    dev_image_data = base64.b64encode(get_default_avatar_svg().encode()).decode('utf-8')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Não autorizado'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Não autorizado'}), 401
        if session.get('role') not in ['admin', 'master']:
            return jsonify({'error': 'Permissão negada.'}), 403
        return f(*args, **kwargs)
    return decorated_function

def save_icon_image(image_data, old_filename=None, is_default=False):
    target_folder = DEFAULT_ICONS_FOLDER if is_default else ICONS_FOLDER
    if old_filename:
        old_path = os.path.join(target_folder, old_filename)
        if os.path.exists(old_path):
            try: os.remove(old_path)
            except: pass
    if image_data and image_data.startswith('data:image'):
        format_map = {
            'data:image/png;base64,': '.png', 'data:image/jpeg;base64,': '.jpg',
            'data:image/jpg;base64,': '.jpg', 'data:image/gif;base64,': '.gif',
            'data:image/webp;base64,': '.webp'
        }
        ext = '.png'
        for key, value in format_map.items():
            if image_data.startswith(key):
                ext = value
                image_data = image_data.replace(key, '')
                break
        filename = f"icon_{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(target_folder, filename)
        try:
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(image_data))
            return filename
        except Exception as e:
            return None
    return None

def save_background_image(image_data, name=None):
    if image_data and image_data.startswith('data:image'):
        format_map = {
            'data:image/png;base64,': '.png', 'data:image/jpeg;base64,': '.jpg',
            'data:image/jpg;base64,': '.jpg', 'data:image/gif;base64,': '.gif',
            'data:image/webp;base64,': '.webp'
        }
        ext = '.png'
        for key, value in format_map.items():
            if image_data.startswith(key):
                ext = value
                image_data = image_data.replace(key, '')
                break
        if not name:
            name = f"bg_{uuid.uuid4().hex}{ext}"
        elif not name.endswith(ext):
            name = name + ext
        filename = secure_filename(name)
        filepath = os.path.join(BACKGROUNDS_FOLDER, filename)
        try:
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(image_data))
            return filename
        except Exception as e:
            return None
    return None

DEFAULT_CONNECTIONS_CONFIG = {
    'Cabeadas': {
        'icon': '🔌',
        'connections': [
            {'name': 'CAT5', 'color': '#28a745', 'icon': '🟢', 'type': 'cable', 'speed': '100 Mbps', 'desc': 'Cabo de rede categoria 5', 'iconFile': None},
            {'name': 'CAT5e', 'color': '#17a2b8', 'icon': '🔵', 'type': 'cable', 'speed': '1 Gbps', 'desc': 'Cabo de rede categoria 5e', 'iconFile': None},
            {'name': 'CAT6', 'color': '#ffc107', 'icon': '🟡', 'type': 'cable', 'speed': '10 Gbps', 'desc': 'Cabo de rede categoria 6', 'iconFile': None},
            {'name': 'FIBRA', 'color': '#20c997', 'icon': '🔷', 'type': 'cable', 'speed': '10 Gbps', 'desc': 'Cabo de fibra óptica', 'iconFile': None},
            {'name': 'COAXIAL', 'color': '#e83e8c', 'icon': '🟣', 'type': 'cable', 'speed': '1 Gbps', 'desc': 'Cabo coaxial', 'iconFile': None},
            {'name': 'ALARME', 'color': '#dc3545', 'icon': '🔴', 'type': 'cable', 'speed': 'Baixa', 'desc': 'Cabo para alarme', 'iconFile': None},
            {'name': 'CABO CI', 'color': '#6f42c1', 'icon': '🟣', 'type': 'cable', 'speed': 'Média', 'desc': 'Cabo de controle industrial', 'iconFile': None},
            {'name': 'ENERGIA', 'color': '#fd7e14', 'icon': '🔴', 'type': 'cable', 'speed': '-', 'desc': 'Cabo de energia elétrica', 'iconFile': None}
        ]
    },
    'Sem Fio': {
        'icon': '📶',
        'connections': [
            {'name': 'Wi-Fi', 'color': '#00aaff', 'icon': '📶', 'type': 'wireless', 'speed': '1 Gbps', 'desc': 'Conexão Wi-Fi', 'animation': 'wave', 'iconFile': None},
            {'name': 'OOK', 'color': '#ff6600', 'icon': '📻', 'type': 'wireless', 'speed': '100 Kbps', 'desc': 'OOK - Rádio Frequência', 'animation': 'packet', 'iconFile': None},
            {'name': 'FSK', 'color': '#aa44ff', 'icon': '📡', 'type': 'wireless', 'speed': '1 Mbps', 'desc': 'FSK - Modulação por Frequência', 'animation': 'packet', 'iconFile': None},
            {'name': 'AMT 8000', 'color': '#ff44aa', 'icon': '🔊', 'type': 'wireless', 'speed': '8000 bps', 'desc': 'AMT 8000 - Rádio Digital', 'animation': 'wave', 'iconFile': None},
            {'name': 'Bluetooth', 'color': '#0066cc', 'icon': '📱', 'type': 'wireless', 'speed': '24 Mbps', 'desc': 'Bluetooth - Conexão curta distância', 'animation': 'wave', 'iconFile': None},
            {'name': 'ZigBee', 'color': '#00aa66', 'icon': '🔵', 'type': 'wireless', 'speed': '250 Kbps', 'desc': 'ZigBee - IoT/M2M', 'animation': 'packet', 'iconFile': None},
            {'name': 'LoRa', 'color': '#cc8800', 'icon': '📡', 'type': 'wireless', 'speed': '50 Kbps', 'desc': 'LoRa - Longa distância', 'animation': 'packet', 'iconFile': None}
        ]
    }
}

DEFAULT_CATEGORIES_CONFIG = {
    'Câmeras': {
        'icon': '🎥',
        'devices': [
            {'name': 'Câmera Dome', 'icon': '📹', 'desc': '360° - 4MP - IVS', 'type': 'camera', 'subtype': 'dome', 'color': '#005f99', 'iconFile': None},
            {'name': 'Câmera Bullet', 'icon': '📹', 'desc': 'Longa distância - 8MP', 'type': 'camera', 'subtype': 'bullet', 'color': '#005f99', 'iconFile': None},
            {'name': 'Câmera S', 'icon': '📹', 'desc': 'Motorizada - Auto tracking', 'type': 'camera', 'subtype': 'ptz', 'color': '#005f99', 'iconFile': None},
            {'name': 'Câmera Térmica', 'icon': '📹', 'desc': 'Detecção de calor', 'type': 'camera', 'subtype': 'thermal', 'color': '#005f99', 'iconFile': None},
            {'name': 'Câmera LPR', 'icon': '📹', 'desc': 'Leitura de placas - 1080P', 'type': 'camera', 'subtype': 'lpr', 'color': '#005f99', 'iconFile': None},
            {'name': 'Câmera PR', 'icon': '📹', 'desc': '1080P Full HD', 'type': 'camera', 'subtype': 'pr', 'color': '#005f99', 'iconFile': None}
        ]
    },
    'Gravadores': {
        'icon': '💾',
        'devices': [
            {'name': 'NVR', 'icon': '💾', 'desc': '32 canais - 4K', 'type': 'nvr', 'color': '#17a2b8', 'iconFile': None},
            {'name': 'DVR', 'icon': '💾', 'desc': '16 canais - HD', 'type': 'dvr', 'color': '#17a2b8', 'iconFile': None}
        ]
    },
    'Rede': {
        'icon': '🌐',
        'devices': [
            {'name': 'Router', 'icon': '📡', 'desc': 'Gigabit', 'type': 'router', 'color': '#20c997', 'iconFile': None},
            {'name': 'Switch L2 PoE', 'icon': '🔌', 'desc': '24 portas PoE', 'type': 'switch_l2_poe', 'color': '#20c997', 'iconFile': None},
            {'name': 'Switch L2', 'icon': '🔌', 'desc': '24 portas', 'type': 'switch_l2', 'color': '#20c997', 'iconFile': None},
            {'name': 'Switch L3 PoE', 'icon': '🔌', 'desc': 'Layer 3 com PoE', 'type': 'switch_l3_poe', 'color': '#20c997', 'iconFile': None},
            {'name': 'Switch L3', 'icon': '🔌', 'desc': 'Layer 3', 'type': 'switch_l3', 'color': '#20c997', 'iconFile': None},
            {'name': 'OLT GPON', 'icon': '🔷', 'desc': 'Fibra óptica', 'type': 'olt', 'color': '#20c997', 'iconFile': None},
            {'name': 'ONU', 'icon': '🔷', 'desc': 'Optical Network Unit', 'type': 'onu', 'color': '#20c997', 'iconFile': None},
            {'name': 'ONT', 'icon': '🔷', 'desc': 'Optical Terminal', 'type': 'ont', 'color': '#20c997', 'iconFile': None},
            {'name': 'CTO', 'icon': '📦', 'desc': 'Caixa Terminal Óptica', 'type': 'cto', 'color': '#20c997', 'iconFile': None},
            {'name': 'Conversor Mídia', 'icon': '🔄', 'desc': 'Fibra/RJ45', 'type': 'converter', 'color': '#20c997', 'iconFile': None}
        ]
    },
    'Telefonia': {
        'icon': '📞',
        'devices': [
            {'name': 'PABX', 'icon': '📞', 'desc': 'Central telefônica', 'type': 'pbx', 'color': '#6f42c1', 'iconFile': None},
            {'name': 'Telefone IP', 'icon': '📞', 'desc': 'VoIP', 'type': 'telefone_ip', 'color': '#6f42c1', 'iconFile': None},
            {'name': 'Telefone Analógico', 'icon': '☎️', 'desc': 'Linha convencional', 'type': 'telefone_analogico', 'color': '#6f42c1', 'iconFile': None},
            {'name': 'ATA', 'icon': '🔄', 'desc': 'Adaptador Telefônico', 'type': 'ata', 'color': '#6f42c1', 'iconFile': None}
        ]
    },
    'Sensores': {
        'icon': '📡',
        'devices': [
            {'name': 'Sensor de Movimento', 'icon': '🔴', 'desc': 'Detecção de movimento', 'type': 'sensor', 'subtype': 'movement', 'color': '#005f99', 'iconFile': None},
            {'name': 'Sensor de Porta', 'icon': '🚪', 'desc': 'Abertura de porta', 'type': 'sensor', 'subtype': 'door', 'color': '#005f99', 'iconFile': None},
            {'name': 'Sensor de Fumaça', 'icon': '💨', 'desc': 'Detecção de fumaça', 'type': 'sensor', 'subtype': 'smoke', 'color': '#005f99', 'iconFile': None}
        ]
    },
    'Controle de Acesso': {
        'icon': '🔑',
        'devices': [
            {'name': 'Cancela', 'icon': '🚗', 'desc': 'Controle de acesso', 'type': 'cancela', 'color': '#28a745', 'iconFile': None},
            {'name': 'Controle de Acesso', 'icon': '🔑', 'desc': 'Biometria/Cartão', 'type': 'controle_acesso', 'color': '#28a745', 'iconFile': None},
            {'name': 'Catraca', 'icon': '🚪', 'desc': 'Controle de fluxo', 'type': 'catraca', 'color': '#28a745', 'iconFile': None}
        ]
    }
}

DEFAULT_CONNECTIONS_FILE = os.path.join(UPLOAD_FOLDER, 'default_connections.json')
DEFAULT_CONFIG_FILE = os.path.join(UPLOAD_FOLDER, 'default_config.json')
CUSTOM_DEVICES_FILE = os.path.join(UPLOAD_FOLDER, 'custom_devices.json')

def load_json_file(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return json.loads(json.dumps(default_value))

def save_json_file(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except: return False

@app.route('/api/upload_icon', methods=['POST'])
@login_required
def upload_icon():
    data = request.json
    image_data = data.get('image', '')
    target_type = data.get('type', 'equipment')
    if not image_data or not image_data.startswith('data:image'):
        return jsonify({'success': False, 'error': 'Imagem inválida'}), 400
    
    format_map = {'data:image/png;base64,': '.png', 'data:image/jpeg;base64,': '.jpg', 'data:image/jpg;base64,': '.jpg', 'data:image/gif;base64,': '.gif', 'data:image/webp;base64,': '.webp'}
    ext = '.png'
    for key, value in format_map.items():
        if image_data.startswith(key):
            ext = value
            image_data = image_data.replace(key, '')
            break
    else:
        image_data = image_data.split(',')[1] if ',' in image_data else image_data
    
    filename = f"{target_type}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(ICONS_FOLDER, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload_dev_image', methods=['POST'])
@admin_required
def upload_dev_image():
    data = request.json
    image_data = data.get('image', '')
    if not image_data: return jsonify({'success': False, 'error': 'Imagem inválida'}), 400
    if ',' in image_data: image_data = image_data.split(',')[1]
    
    filename = "dev.png"
    filepath = os.path.join(BASE_DIR, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload_background', methods=['POST'])
@login_required
def upload_background():
    data = request.json
    image_data = data.get('image', '')
    name = data.get('name', None)
    if not image_data: return jsonify({'success': False}), 400
    filename = save_background_image(image_data, name)
    if filename:
        return jsonify({'success': True, 'url': f'/uploads/backgrounds/{filename}'})
    return jsonify({'success': False}), 500

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

@app.route('/static/<path:filename>')
def serve_static(filename): return send_from_directory(STATIC_FOLDER, filename)

@app.route('/api/default_config', methods=['GET'])
def get_default_config(): return jsonify({'success': True, 'config': load_json_file(DEFAULT_CONFIG_FILE, DEFAULT_CATEGORIES_CONFIG)})

@app.route('/api/default_connections', methods=['GET'])
def get_default_connections(): return jsonify({'success': True, 'config': load_json_file(DEFAULT_CONNECTIONS_FILE, DEFAULT_CONNECTIONS_CONFIG)})

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username, password = data.get('username'), data.get('password')
    if username in users and users[username]['password'] == hash_password(password):
        session['logged_in'] = True
        session['username'] = username
        session['role'] = users[username]['role']
        return jsonify({'success': True, 'role': users[username]['role']})
    return jsonify({'success': False, 'error': 'Credenciais inválidas'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    if session.get('role') not in ['admin', 'master']: return jsonify({'error': 'Permissão negada'}), 403
    return jsonify({u: {'role': d['role'], 'created_at': d.get('created_at','')} for u, d in users.items()})

@app.route('/api/users', methods=['POST'])
@login_required
def add_user():
    if session.get('role') not in ['admin', 'master']: return jsonify({'error': 'Permissão negada'}), 403
    data = request.json
    if data['username'] in users: return jsonify({'error': 'Usuário já existe'}), 400
    users[data['username']] = {'password': hash_password(data['password']), 'role': data.get('role', 'viewer'), 'created_at': datetime.now().isoformat()}
    save_users(users)
    return jsonify({'success': True})

@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
def delete_user(username):
    if session.get('role') not in ['admin', 'master']: return jsonify({'error': 'Permissão negada'}), 403
    if username == 'thiago03': return jsonify({'error': 'Master não pode ser excluído'}), 400
    if username in users:
        del users[username]
        save_users(users)
        return jsonify({'success': True})
    return jsonify({'error': 'Não encontrado'}), 404

# ==================== HTML TEMPLATE (INTERFACE ORIGINAL MANTIDA) ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Projetize - Sistema CFTV</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0f18; overflow: hidden; position: fixed; top: 0; left: 0; right: 0; bottom: 0; color: #e2e8f0; }
        :root {
            --bg-primary: #0f172a; --bg-secondary: #1e293b; --bg-tertiary: #334155;
            --bg-card: #1e293b; --text-primary: #e2e8f0; --text-secondary: #94a3b8;
            --text-accent: #00e5ff; --border-color: #334155; --button-primary: #00e5ff;
            --button-primary-hover: #00b8cc; --button-secondary: #1e293b;
            --button-secondary-hover: #334155; --shadow: rgba(0, 229, 255, 0.2);
            --palette-width: 280px;
            --properties-width: 320px;
        }
        
        /* ==================== LOGIN CORPORATIVO ==================== */
        .login-screen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #050a14; display: flex; justify-content: center; align-items: center; z-index: 25000; overflow: hidden; }
        .login-grid-bg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background-image: linear-gradient(rgba(0, 229, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 229, 255, 0.05) 1px, transparent 1px); background-size: 40px 40px; animation: gridMove 20s linear infinite; z-index: 1; }
        @keyframes gridMove { 0% { transform: translateY(0); } 100% { transform: translateY(40px); } }
        .login-container { position: relative; z-index: 2; width: 100%; max-width: 440px; padding: 20px; animation: fadeUp 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        .login-card { background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(20px); border-radius: 20px; padding: 40px; border: 1px solid rgba(0, 229, 255, 0.15); box-shadow: 0 0 50px rgba(0, 0, 0, 0.5), 0 0 20px rgba(0, 229, 255, 0.05); position: relative; }
        .login-card::before { content: ''; position: absolute; top: 0; left: 10%; right: 10%; height: 1px; background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.8), transparent); }
        .brand-logo { display: flex; align-items: center; gap: 15px; margin-bottom: 30px; }
        .brand-icon { width: 50px; height: 50px; background: linear-gradient(135deg, rgba(0,229,255,0.2), rgba(0,150,255,0.1)); border-radius: 12px; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(0, 229, 255, 0.3); box-shadow: 0 0 15px rgba(0, 229, 255, 0.1); font-size: 24px; }
        .brand-text h1 { font-size: 24px; font-weight: 800; color: #fff; letter-spacing: 2px; margin-bottom: 2px; }
        .brand-text p { font-size: 11px; color: var(--text-accent); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
        .login-form-group { margin-bottom: 20px; }
        .login-form-group label { display: block; font-size: 12px; color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .login-input { width: 100%; padding: 14px 16px; background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; color: #fff; font-size: 14px; transition: all 0.3s; outline: none; }
        .login-input:focus { border-color: var(--text-accent); box-shadow: 0 0 0 3px rgba(0, 229, 255, 0.1); background: rgba(0, 0, 0, 0.5); }
        .login-btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #00e5ff, #0077ff); border: none; border-radius: 10px; color: #050a14; font-size: 15px; font-weight: 800; cursor: pointer; margin-top: 10px; transition: all 0.3s; letter-spacing: 1px; box-shadow: 0 4px 15px rgba(0, 229, 255, 0.3); }
        .login-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 229, 255, 0.5); }
        .login-footer { margin-top: 30px; text-align: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 20px; }
        .login-footer-avatar { width: 40px; height: 40px; border-radius: 50%; border: 2px solid rgba(0, 229, 255, 0.3); margin: 0 auto 10px; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #1e293b; }
        .login-footer-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .login-footer-text { font-size: 11px; color: var(--text-secondary); line-height: 1.6; }
        .login-footer-text strong { color: var(--text-accent); }

        /* ==================== TOOLBAR E MAIN LAYOUT (ORIGINAL) ==================== */
        .toolbar { background: var(--bg-secondary); padding: 8px 15px; display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 2px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.1); z-index: 100; position: relative; margin-left: 60px; }
        .btn { padding: 6px 12px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; font-size: 12px; display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
        .btn-primary { background: var(--button-primary); color: #0f172a; }
        .btn-primary:hover { background: var(--button-primary-hover); transform: scale(1.02); }
        .btn-secondary { background: var(--button-secondary); color: var(--text-primary); border: 1px solid var(--border-color); }
        .btn-secondary:hover { background: var(--button-secondary-hover); transform: scale(1.02); }
        .btn-danger { background: #dc3545; color: white; }
        .btn-info { background: var(--button-secondary); color: var(--text-primary); }
        .btn-warning { background: #ffc107; color: #212529; }
        
        .main-container { display: flex; height: calc(100vh - 52px); position: relative; overflow: hidden; }
        .palette { width: var(--palette-width); background: var(--bg-tertiary); color: var(--text-primary); overflow-y: auto; padding: 10px; border-right: 2px solid var(--border-color); transition: width 0.3s ease; position: relative; flex-shrink: 0; }
        .palette.collapsed { width: 50px; min-width: 50px; }
        .palette.collapsed .category h3, .palette.collapsed .component-info, .palette.collapsed .category-actions, .palette.collapsed .component-actions { display: none; }
        .palette.collapsed .component { justify-content: center; padding: 6px; }
        .toggle-palette { position: sticky; top: 10px; right: -12px; float: right; background: var(--button-primary); border: none; color: #0f172a; width: 24px; height: 40px; border-radius: 0 8px 8px 0; cursor: pointer; z-index: 10; font-size: 12px; margin-bottom: 10px; }
        
        .category { margin-bottom: 15px; clear: both; }
        .category-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
        .category h3 { font-size: 12px; color: var(--text-accent); border-left: 3px solid var(--border-color); padding-left: 8px; }
        .category-actions { display: flex; gap: 5px; }
        .category-actions button { background: none; border: none; color: var(--text-accent); cursor: pointer; font-size: 12px; padding: 2px 5px; border-radius: 3px; }
        .component { background: var(--bg-card); border-radius: 8px; padding: 6px 10px; margin-bottom: 6px; cursor: grab; display: flex; align-items: center; gap: 10px; transition: all 0.2s; border: 1px solid var(--border-color); position: relative; }
        .component:active { cursor: grabbing; }
        .component:hover { background: var(--bg-secondary); transform: translateX(3px); border-color: var(--text-accent); }
        .component-icon { font-size: 20px; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; }
        .component-icon img { width: 24px; height: 24px; object-fit: contain; }
        .component-info { flex: 1; }
        .component-name { font-size: 12px; font-weight: 600; }
        .component-desc { font-size: 9px; opacity: 0.7; }
        
        .canvas-area { flex: 1; background: #000; overflow: auto; position: relative; cursor: default; }
        #canvas { background: transparent; cursor: crosshair; display: block; margin: 0 auto; transform-origin: 0 0; }
        
        .properties { width: 0; background: var(--bg-tertiary); color: var(--text-primary); padding: 0; overflow-y: auto; border-left: none; transition: width 0.3s ease; position: relative; flex-shrink: 0; }
        .properties.open { width: var(--properties-width); padding: 15px; border-left: 2px solid var(--border-color); }
        .properties-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .close-properties-btn { background: none; border: none; font-size: 18px; cursor: pointer; color: var(--text-secondary); padding: 5px; }
        .close-properties-btn:hover { color: var(--text-accent); }
        
        .property-group { margin-bottom: 12px; }
        .property-group label { display: block; font-size: 11px; margin-bottom: 4px; color: var(--text-accent); }
        .property-group input, .property-group select, .property-group textarea { width: 100%; padding: 6px; border-radius: 5px; border: none; background: var(--bg-card); color: var(--text-primary); font-size: 12px; border: 1px solid var(--border-color); }
        
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: center; z-index: 3000; padding: 20px; }
        .modal-content { background: var(--bg-secondary); padding: 25px; border-radius: 12px; width: 500px; max-width: 100%; max-height: 85%; overflow-y: auto; border: 1px solid var(--border-color); }
        .modal-content input, .modal-content select, .modal-content textarea { width: 100%; padding: 8px; margin: 8px 0; background: var(--bg-tertiary); border: none; border-radius: 5px; color: var(--text-primary); }
        .modal-buttons { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
        
        .toast { position: fixed; bottom: 20px; right: 20px; background: var(--button-primary); color: #0f172a; padding: 10px 20px; border-radius: 5px; z-index: 4000; animation: slideIn 0.3s ease; max-width: 90%; word-break: break-word; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        
        .context-menu { position: fixed; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 5px 0; z-index: 2000; display: none; min-width: 180px; }
        .context-menu-item { padding: 8px 15px; cursor: pointer; color: var(--text-primary); font-size: 12px; transition: all 0.2s; }
        .context-menu-item:hover { background: var(--button-primary); color: #0f172a; }
        
        .loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.95); z-index: 30000; display: none; flex-direction: column; justify-content: center; align-items: center; color: white; }
        .loading-spinner { border: 8px solid rgba(0, 229, 255, 0.1); border-top: 8px solid #00e5ff; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; margin-bottom: 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .loading-text { font-size: 18px; font-weight: bold; animation: pulseText 1.5s infinite; }
        @keyframes pulseText { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
    </style>
</head>
<body>
    <!-- Loading -->
    <div id="loadingOverlay" class="loading-overlay">
        <div class="loading-spinner"></div>
        <div class="loading-text">Carregando módulos...</div>
        <div style="font-size: 12px; margin-top: 10px; opacity: 0.7;" id="loadingDeviceType"></div>
    </div>

    <!-- LOGIN CORPORATIVO -->
    <div class="login-screen" id="loginScreen">
        <div class="login-grid-bg"></div>
        <div class="login-container">
            <div class="login-card">
                <div class="brand-logo">
                    <div class="brand-icon">🛡️</div>
                    <div class="brand-text">
                        <h1>PROJETIZE</h1>
                        <p>Infraestrutura & Redes</p>
                    </div>
                </div>
                <div class="login-form-group">
                    <label>Usuário</label>
                    <input type="text" id="loginUsername" class="login-input" placeholder="Digite seu usuário" autocomplete="username">
                </div>
                <div class="login-form-group">
                    <label>Senha</label>
                    <input type="password" id="loginPassword" class="login-input" placeholder="Digite sua senha" autocomplete="current-password">
                </div>
                <button class="login-btn" onclick="doLogin()">Acessar Painel</button>
                <div class="login-footer">
                    <div class="login-footer-avatar" id="loginAvatar">
                        <img id="loginDevImage" src="" style="display:none;">
                        <span id="loginAvatarFallback" style="color: var(--text-accent); font-weight: bold;">TS</span>
                    </div>
                    <div class="login-footer-text">
                        Desenvolvido por <strong>Thiago Souza</strong><br>
                        Analista de Tecnologia | Unidade 2 - São José do Rio Preto<br>
                        Todos os direitos reservados © 2026
                    </div>
                </div>
                <div class="login-error" id="loginError" style="color: #ff5577; font-size: 12px; margin-top: 14px; display: none; text-align: center;">Usuário ou senha inválidos</div>
            </div>
        </div>
    </div>

    <!-- TOOLBAR ORIGINAL -->
    <div class="toolbar" id="toolbar" style="display: none;">
        <button class="btn btn-primary" onclick="newProject()">📁 Novo</button>
        <button class="btn btn-secondary" onclick="saveProjectToFile()">💾 Salvar</button>
        <button class="btn btn-secondary" onclick="loadProjectFromFile()">📂 Carregar</button>
        <button class="btn btn-primary" onclick="exportPDFWithList()">📄 PDF</button>
        <button class="btn btn-primary" onclick="exportPDF()">📄 Mapa</button>
        <button class="btn btn-warning" onclick="generateBudget()">💰 Orçamento</button>
        <button class="btn btn-danger" onclick="deleteSelectedItems()">🗑 Excluir Selecionados</button>
        <button id="adminUsersBtn" class="btn btn-info" onclick="openUserManagement()" style="display: none;">👥 Usuários</button>
        <button id="adminShapesBtn" class="btn btn-info" onclick="toggleShapesToolbar()" style="display: none;">📐 Formas</button>
        <button id="adminCategoriesBtn" class="btn btn-info" onclick="openAddCategoryModal()" style="display: none;">📁 + Cat</button>
        <button id="adminDevicesBtn" class="btn btn-info" onclick="openAddDeviceModal()" style="display: none;">🔧 + Equip</button>
        <button id="adminConnectionsBtn" class="btn btn-info" onclick="openAddConnectionModal()" style="display: none;">🔌 + Conexão</button>
        <button id="resetDefaultsBtn" class="btn btn-warning" onclick="resetToDefaultConfig()" style="display: none;">🔄 Padrões</button>
        <button class="btn btn-info" onclick="toggleGrid()">🔲 Grade</button>
        <button class="btn btn-info" onclick="openBackgroundModal()">🖼️ Planta</button>
        <button id="adminDevBtn" class="btn btn-warning" onclick="openDevImageModal()" style="background:#e83e8c; color:white; display: none;">🖼️ Dev</button>
        <button id="adminBgBtn" class="btn btn-secondary" onclick="openDynamicBgModal()" style="background:#6f42c1; color:white; display: none;">🎬 Fundo</button>
        
        <button class="btn btn-danger" onclick="logout()">🚪 Sair</button>
        <span style="flex:1"></span>
        <div class="user-info" id="userInfo" style="display: flex; align-items: center; gap: 10px; background: var(--bg-tertiary); padding: 4px 12px; border-radius: 20px; color: var(--text-primary); font-size: 12px;"></div>
    </div>

    <!-- MAIN CONTAINER ORIGINAL -->
    <div class="main-container">
        <div class="palette" id="palette">
            <button class="toggle-palette" onclick="togglePalette()">◀</button>
            <div id="categories-container"></div>
            <hr style="margin: 15px 0; border-color: var(--border-color);">
            <h4 style="color: var(--text-accent); font-size: 12px; margin-bottom: 10px;">🔌 Tipos de Conexão</h4>
            <div id="connections-container"></div>
        </div>
        <div class="canvas-area" id="canvasArea">
            <canvas id="canvas" width="5000" height="4000" style="width:5000px;height:4000px"></canvas>
        </div>
        <div class="properties" id="propertiesPanel">
            <div class="properties-header">
                <h3>📋 Propriedades</h3>
                <button class="close-properties-btn" onclick="closePropertiesPanel()" title="Fechar">✕</button>
            </div>
            <div id="props-content">
                <p style="color:var(--text-secondary);">Clique em um componente ou forma</p>
            </div>
        </div>
    </div>
    <div class="context-menu" id="contextMenu"></div>

    <script>
        // ==================== CONFIGURAÇÕES INICIAIS ====================
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        let components = [];
        let connections = [];
        let shapes = [];
        let selectedComponents = [];
        let selectedShapes = [];
        let selectedConnectionIndex = null;
        let dragging = false;
        let dragOffset = {x:0, y:0};
        let zoom = 1;
        let iconSize = 36;
        let isDrawingConnection = false;
        let connectionStart = null;
        let isSelecting = false;
        let selectionStart = {x:0, y:0};
        let selectionEnd = {x:0, y:0};
        let contextMenuComponent = null;
        let contextMenuShape = null;
        let contextMenuConnection = null;
        let shapeMode = null;
        let shapeStart = null;
        let drawingPreview = null;
        let showGrid = true;
        let sensorAnimationTime = 0;
        let trafficAnimation = 0;
        let currentUser = null;
        let userRole = null;
        let backgroundImage = null;
        let backgroundImageObj = null;
        let backgroundOpacity = 0.8;
        let backgroundWidth = 0;
        let backgroundHeight = 0;
        let backgroundX = 0;
        let backgroundY = 0;
        let isBackgroundSelected = false;
        let isDraggingBackgroundImage = false;
        let dragBackgroundStart = {x:0, y:0};
        let isResizingBackground = false;
        let resizeHandle = null;
        let resizeStart = {x:0, y:0, width:0, height:0, x:0, y:0};
        
        // Waypoints para curvar cabos
        let draggingWaypoint = false;
        let waypointConnIdx = null;
        let waypointIdx = null;

        // Cache de imagens
        const imageCache = {};
        function getCachedImage(src) {
            if (!imageCache[src]) {
                const img = new Image();
                img.src = src;
                imageCache[src] = img;
            }
            return imageCache[src];
        }

        const devImageBase64 = '""" + dev_image_data + """';
        
        const defaultCableColors = {
            'cat5': { color: '#28a745', name: 'CAT5', icon: '🟢', type: 'cable', speed: '100 Mbps', desc: 'Cabo de rede categoria 5' },
            'cat5e': { color: '#17a2b8', name: 'CAT5e', icon: '🔵', type: 'cable', speed: '1 Gbps', desc: 'Cabo de rede categoria 5e' },
            'cat6': { color: '#ffc107', name: 'CAT6', icon: '🟡', type: 'cable', speed: '10 Gbps', desc: 'Cabo de rede categoria 6' },
            'fiber': { color: '#20c997', name: 'FIBRA', icon: '🔷', type: 'cable', speed: '10 Gbps', desc: 'Cabo de fibra óptica' },
            'coaxial': { color: '#e83e8c', name: 'COAXIAL', icon: '🟣', type: 'cable', speed: '1 Gbps', desc: 'Cabo coaxial' },
            'alarme': { color: '#dc3545', name: 'ALARME', icon: '🔴', type: 'cable', speed: 'Baixa', desc: 'Cabo para alarme' },
            'ci': { color: '#6f42c1', name: 'CABO CI', icon: '🟣', type: 'cable', speed: 'Média', desc: 'Cabo de controle industrial' },
            'energia': { color: '#fd7e14', name: 'ENERGIA', icon: '🔴', type: 'cable', speed: '-', desc: 'Cabo de energia elétrica' },
            'wifi': { color: '#00aaff', name: 'Wi-Fi', icon: '📶', type: 'wireless', speed: '1 Gbps', desc: 'Conexão Wi-Fi', animation: 'wave' },
            'ook': { color: '#ff6600', name: 'OOK', icon: '📻', type: 'wireless', speed: '100 Kbps', desc: 'OOK - Rádio Frequência', animation: 'packet' },
            'fsk': { color: '#aa44ff', name: 'FSK', icon: '📡', type: 'wireless', speed: '1 Mbps', desc: 'FSK - Modulação por Frequência', animation: 'packet' },
            'amt8000': { color: '#ff44aa', name: 'AMT 8000', icon: '🔊', type: 'wireless', speed: '8000 bps', desc: 'AMT 8000 - Rádio Digital', animation: 'wave' },
            'bluetooth': { color: '#0066cc', name: 'Bluetooth', icon: '📱', type: 'wireless', speed: '24 Mbps', desc: 'Bluetooth - Conexão curta distância', animation: 'wave' },
            'zigbee': { color: '#00aa66', name: 'ZigBee', icon: '🔵', type: 'wireless', speed: '250 Kbps', desc: 'ZigBee - IoT/M2M', animation: 'packet' },
            'lora': { color: '#cc8800', name: 'LoRa', icon: '📡', type: 'wireless', speed: '50 Kbps', desc: 'LoRa - Longa distância', animation: 'packet' }
        };
        
        let cableColors = JSON.parse(JSON.stringify(defaultCableColors));
        let connectionCategories = {};
        let categories = {};
        let defaultCategories = {};
        
        const STORAGE_KEYS = {
            ICON_SIZE: 'projetize_icon_size',
            CANVAS_ZOOM: 'projetize_canvas_zoom',
            COMPONENTS: (user) => `projetize_${user}_components`,
            CONNECTIONS_DATA: (user) => `projetize_${user}_connections`,
            SHAPES: (user) => `projetize_${user}_shapes`,
            BACKGROUND: (user) => `projetize_${user}_background`
        };
        
        async function loadDefaultConfig() {
            try {
                const response = await fetch('/api/default_config');
                const data = await response.json();
                if (data.success) defaultCategories = data.config;
            } catch(e) { console.error(e); }
        }
        
        async function loadDefaultConnections() {
            try {
                const response = await fetch('/api/default_connections');
                const data = await response.json();
                if (data.success) {
                    connectionCategories = data.config;
                    for (const [catName, catData] of Object.entries(data.config)) {
                        for (const conn of catData.connections) {
                            const key = getConnectionKey(conn.name);
                            cableColors[key] = { ...conn };
                        }
                    }
                }
            } catch(e) { console.error(e); }
        }
        
        let saveTimeout;
        function saveUserData() {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => {
                localStorage.setItem(STORAGE_KEYS.ICON_SIZE, iconSize);
                localStorage.setItem(STORAGE_KEYS.CANVAS_ZOOM, zoom);
                if (currentUser) {
                    localStorage.setItem(STORAGE_KEYS.COMPONENTS(currentUser), JSON.stringify(components));
                    localStorage.setItem(STORAGE_KEYS.CONNECTIONS_DATA(currentUser), JSON.stringify(connections));
                    localStorage.setItem(STORAGE_KEYS.SHAPES(currentUser), JSON.stringify(shapes));
                    localStorage.setItem(STORAGE_KEYS.BACKGROUND(currentUser), JSON.stringify({
                        url: backgroundImage, opacity: backgroundOpacity, width: backgroundWidth,
                        height: backgroundHeight, x: backgroundX, y: backgroundY
                    }));
                }
            }, 300);
        }

        async function loadUserData() {
            const savedIconSize = localStorage.getItem(STORAGE_KEYS.ICON_SIZE);
            if(savedIconSize) iconSize = parseInt(savedIconSize);
            const savedZoom = localStorage.getItem(STORAGE_KEYS.CANVAS_ZOOM);
            if(savedZoom) zoom = parseFloat(savedZoom);
            
            categories = JSON.parse(JSON.stringify(defaultCategories));
            
            if (currentUser) {
                const savedComponents = localStorage.getItem(STORAGE_KEYS.COMPONENTS(currentUser));
                const savedConnectionsData = localStorage.getItem(STORAGE_KEYS.CONNECTIONS_DATA(currentUser));
                const savedShapes = localStorage.getItem(STORAGE_KEYS.SHAPES(currentUser));
                const savedBackground = localStorage.getItem(STORAGE_KEYS.BACKGROUND(currentUser));
                
                if(savedComponents) components = JSON.parse(savedComponents);
                if(savedConnectionsData) {
                    connections = JSON.parse(savedConnectionsData);
                    // Garante que conexões antigas tenham waypoints
                    connections.forEach(c => { if (!c.waypoints) c.waypoints = []; });
                }
                if(savedShapes) shapes = JSON.parse(savedShapes);
                if(savedBackground) {
                    const bgData = JSON.parse(savedBackground);
                    backgroundImage = bgData.url;
                    backgroundOpacity = bgData.opacity || 0.8;
                    backgroundWidth = bgData.width || 0;
                    backgroundHeight = bgData.height || 0;
                    backgroundX = bgData.x || canvas.width/2 - (bgData.width || 0)/2;
                    backgroundY = bgData.y || canvas.height/2 - (bgData.height || 0)/2;
                    if(backgroundImage) {
                        backgroundImageObj = new Image();
                        backgroundImageObj.src = backgroundImage;
                    }
                }
            }
            
            renderPalette();
            renderConnectionsPalette();
            applyZoomToCanvas();
        }
        
        async function saveGlobalLibrary() {
            if (userRole !== 'admin' && userRole !== 'master') return;
            try {
                await fetch('/api/save_global_categories', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ categories: categories }) });
                await fetch('/api/save_global_connections', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ connections: connectionCategories }) });
            } catch(e) { console.error("Erro ao salvar biblioteca global:", e); }
        }
        
        function getConnectionKey(name) { return name.toLowerCase().replace(/[^a-z0-9]/g, ''); }
        function renderConnectionIcon(conn) { if (conn.iconFile) { return `<img src="/uploads/icons/${conn.iconFile}" style="width:24px;height:24px;object-fit:contain;">`; } return conn.icon || '🔌'; }
        
        function renderConnectionsPalette() {
            const container = document.getElementById('connections-container'); if (!container) return; container.innerHTML = '';
            for (const [catName, catData] of Object.entries(connectionCategories)) {
                if (!catData.connections || catData.connections.length === 0) continue;
                const categoryDiv = document.createElement('div'); categoryDiv.className = 'category';
                categoryDiv.innerHTML = `<div class="category-header"><h3>${catData.icon || '🔌'} ${catName}</h3></div><div id="conn-category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>`;
                container.appendChild(categoryDiv);
                const connContainer = document.getElementById(`conn-category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
                catData.connections.forEach((conn, idx) => {
                    const connEl = document.createElement('div'); connEl.className = 'component'; connEl.style.cursor = 'pointer';
                    connEl.onclick = () => { showToast(`✅ Tipo de conexão selecionado: ${conn.name}`); };
                    connEl.innerHTML = `<div class="component-icon">${renderConnectionIcon(conn)}</div><div class="component-info"><div class="component-name">${conn.name}</div><div class="component-desc">${conn.desc || conn.speed || ''}</div></div>`;
                    connContainer.appendChild(connEl);
                });
            }
        }
        
        function renderDeviceIcon(device) { if(device.iconFile) return `<img src="/uploads/icons/${device.iconFile}" style="width:24px;height:24px;object-fit:contain;">`; return device.icon || '📦'; }
        
        function renderPalette() {
            const container = document.getElementById('categories-container'); if(!container) return; container.innerHTML = '';
            for(const [catName, catData] of Object.entries(categories)) {
                const categoryDiv = document.createElement('div'); categoryDiv.className = 'category';
                const catIcon = catData.iconFile ? `<img src="/uploads/icons/${catData.iconFile}" style="width:16px;height:16px;">` : (catData.icon || '📁');
                categoryDiv.innerHTML = `<div class="category-header"><h3>${catIcon} ${catName}</h3></div><div id="category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>`;
                container.appendChild(categoryDiv);
                const devicesContainer = document.getElementById(`category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
                if (catData.devices) {
                    catData.devices.forEach((device, idx) => {
                        const deviceEl = document.createElement('div'); deviceEl.className = 'component'; deviceEl.setAttribute('draggable', 'true');
                        deviceEl.innerHTML = `<div class="component-icon">${renderDeviceIcon(device)}</div><div class="component-info"><div class="component-name">${device.name}</div><div class="component-desc">${device.desc || ''}</div></div>`;
                        deviceEl.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/plain', JSON.stringify({ name: device.name, icon: device.icon, type: device.type, subtype: device.subtype || '', color: device.color, iconFile: device.iconFile || null })); });
                        devicesContainer.appendChild(deviceEl);
                    });
                }
            }
        }
        
        function applyZoomToCanvas() { canvas.style.transform = `scale(${zoom})`; canvas.style.transformOrigin = '0 0'; }
        function zoomIn() { zoom = Math.min(zoom + 0.1, 3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
        function zoomOut() { zoom = Math.max(zoom - 0.1, 0.3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
        function resetZoom() { zoom = 1; applyZoomToCanvas(); saveUserData(); showToast(`🔄 Zoom restaurado: 100%`); }
        
        function showToast(message) { const toast = document.createElement('div'); toast.className = 'toast'; toast.textContent = message; document.body.appendChild(toast); setTimeout(() => toast.remove(), 3000); }
        function closeModal() { if(window.currentModal) { document.body.removeChild(window.currentModal); window.currentModal = null; } }
        
        function drawGrid() {
            if(!showGrid) return;
            const step = 50; ctx.save(); ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 0.5;
            for(let x=0; x<canvas.width; x+=step) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,canvas.height); ctx.stroke(); }
            for(let y=0; y<canvas.height; y+=step) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(canvas.width,y); ctx.stroke(); }
            ctx.restore();
        }
        
        function drawBackground() {
            if(backgroundImageObj && backgroundImageObj.complete && backgroundImageObj.src && backgroundWidth > 0 && backgroundHeight > 0) {
                ctx.save(); ctx.globalAlpha = backgroundOpacity; ctx.drawImage(backgroundImageObj, backgroundX, backgroundY, backgroundWidth, backgroundHeight); ctx.globalAlpha = 1;
                ctx.restore();
            }
        }
        
        function drawSensorAnimation(x, y, time) {
            const pulseCount = 3; const baseRadius = 25;
            for(let i = 0; i < pulseCount; i++) {
                const delay = i * 0.5; const progress = (time + delay) % 1; const radius = baseRadius + (progress * 30); const opacity = 0.5 * (1 - progress);
                ctx.save(); ctx.beginPath(); ctx.arc(x, y, radius, 0, 2 * Math.PI); ctx.strokeStyle = `rgba(0, 229, 255, ${opacity})`; ctx.lineWidth = 2; ctx.stroke(); ctx.restore();
            }
        }
        
        function drawWirelessAnimationOnLine(x1, y1, x2, y2, type, progress) {
            const cableInfo = cableColors[type]; if (!cableInfo || cableInfo.type !== 'wireless') return;
            const t = progress; const x = x1 + (x2 - x1) * t; const y = y1 + (y2 - y1) * t;
            ctx.save();
            if (cableInfo.animation === 'wave') {
                ctx.beginPath(); ctx.arc(x, y, 6, 0, 2 * Math.PI); ctx.fillStyle = cableInfo.color; ctx.shadowBlur = 8; ctx.shadowColor = cableInfo.color; ctx.fill();
                ctx.beginPath(); ctx.arc(x, y, 10, 0, 2 * Math.PI); ctx.strokeStyle = cableInfo.color; ctx.lineWidth = 1.5; ctx.stroke();
            } else {
                ctx.fillStyle = cableInfo.color; ctx.shadowBlur = 6; ctx.shadowColor = cableInfo.color; ctx.fillRect(x - 3, y - 3, 6, 6);
            }
            ctx.shadowBlur = 0; ctx.restore();
        }
        
        // ==================== CONEXÕES COM CURVAS ====================
        function getConnectionPath(conn) {
            const fromComp = components.find(c => c.id === conn.from);
            const toComp = components.find(c => c.id === conn.to);
            if(!fromComp || !toComp) return null;
            
            const points = [{x: fromComp.x, y: fromComp.y}];
            if (conn.waypoints && conn.waypoints.length > 0) {
                conn.waypoints.forEach(wp => points.push({x: wp.x, y: wp.y}));
            }
            points.push({x: toComp.x, y: toComp.y});
            return points;
        }
        
        function getPointOnPath(points, t) {
            if (points.length === 2) {
                return { x: points[0].x + (points[1].x - points[0].x) * t, y: points[0].y + (points[1].y - points[0].y) * t };
            }
            let totalLength = 0;
            const segments = [];
            for (let i = 0; i < points.length - 1; i++) {
                const dx = points[i+1].x - points[i].x;
                const dy = points[i+1].y - points[i].y;
                const len = Math.sqrt(dx*dx + dy*dy);
                segments.push({len, start: totalLength});
                totalLength += len;
            }
            const targetLen = t * totalLength;
            for (let i = 0; i < segments.length; i++) {
                if (targetLen <= segments[i].start + segments[i].len) {
                    const localT = (targetLen - segments[i].start) / segments[i].len;
                    return { x: points[i].x + (points[i+1].x - points[i].x) * localT, y: points[i].y + (points[i+1].y - points[i].y) * localT };
                }
            }
            return points[points.length - 1];
        }
        
        function drawSmoothPath(points, color, lineWidth, dashPattern) {
            ctx.save();
            if (dashPattern) ctx.setLineDash(dashPattern);
            ctx.strokeStyle = color; ctx.lineWidth = lineWidth; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
            
            if (points.length === 2) {
                ctx.beginPath(); ctx.moveTo(points[0].x, points[0].y); ctx.lineTo(points[1].x, points[1].y); ctx.stroke();
            } else {
                ctx.beginPath(); ctx.moveTo(points[0].x, points[0].y);
                for (let i = 0; i < points.length - 1; i++) {
                    const p0 = points[i === 0 ? 0 : i - 1];
                    const p1 = points[i];
                    const p2 = points[i + 1];
                    const p3 = points[i + 2 >= points.length ? points.length - 1 : i + 2];
                    const cp1x = p1.x + (p2.x - p0.x) / 6;
                    const cp1y = p1.y + (p2.y - p0.y) / 6;
                    const cp2x = p2.x - (p3.x - p1.x) / 6;
                    const cp2y = p2.y - (p3.y - p1.y) / 6;
                    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
                }
                ctx.stroke();
            }
            ctx.restore();
        }
        
        function drawWaypointHandles(connIdx) {
            const conn = connections[connIdx];
            if (!conn || !conn.waypoints) return;
            conn.waypoints.forEach((wp, wpIdx) => {
                ctx.save();
                ctx.beginPath();
                ctx.arc(wp.x, wp.y, 7, 0, 2 * Math.PI);
                ctx.fillStyle = (waypointIdx === wpIdx) ? '#00e5ff' : '#ffaa00';
                ctx.fill();
                ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 2; ctx.stroke();
                ctx.restore();
            });
        }
        
        function drawConnections() {
            connections.forEach((conn, idx) => {
                const fromComp = components.find(c => c.id === conn.from); const toComp = components.find(c => c.id === conn.to);
                if(!fromComp || !toComp) return;
                const cableInfo = cableColors[conn.type] || cableColors['cat6']; if (!cableInfo) return;
                const isWireless = cableInfo.type === 'wireless'; const isSelected = (selectedConnectionIndex === idx);
                
                const pathPoints = getConnectionPath(conn);
                if (!pathPoints) return;
                
                ctx.save();
                
                if(isWireless) {
                    ctx.setLineDash([10, 8]); ctx.strokeStyle = cableInfo.color; ctx.lineWidth = isSelected ? 4 : 2;
                    ctx.beginPath(); ctx.moveTo(fromComp.x, fromComp.y); ctx.lineTo(toComp.x, toComp.y); ctx.stroke();
                    if (cableInfo.animation === 'wave') {
                        for(let i = 0; i < 2; i++) { const t = (trafficAnimation + i * 0.4) % 1; drawWirelessAnimationOnLine(fromComp.x, fromComp.y, toComp.x, toComp.y, conn.type, t); }
                    } else {
                        for(let i = 0; i < 3; i++) { const t = (trafficAnimation + i * 0.25) % 1; drawWirelessAnimationOnLine(fromComp.x, fromComp.y, toComp.x, toComp.y, conn.type, t); }
                    }
                } else {
                    const hasWaypoints = conn.waypoints && conn.waypoints.length > 0;
                    if (hasWaypoints) {
                        drawSmoothPath(pathPoints, cableInfo.color, isSelected ? 4 : 3, null);
                    } else {
                        ctx.setLineDash([]); ctx.beginPath(); ctx.moveTo(fromComp.x, fromComp.y); ctx.lineTo(toComp.x, toComp.y); ctx.strokeStyle = cableInfo.color; ctx.lineWidth = isSelected ? 4 : 2; ctx.stroke();
                    }
                    
                    const t = trafficAnimation; const point = getPointOnPath(pathPoints, t);
                    ctx.beginPath(); ctx.arc(point.x, point.y, 4, 0, 2*Math.PI); ctx.fillStyle = cableInfo.color; ctx.shadowBlur = 6; ctx.shadowColor = cableInfo.color; ctx.fill(); ctx.shadowBlur = 0;
                    
                    if (isSelected && hasWaypoints) drawWaypointHandles(idx);
                }
                
                ctx.fillStyle = '#94a3b8'; ctx.font = `${9}px Arial`; 
                const iconDisplay = cableInfo.iconFile ? '🖼️' : cableInfo.icon;
                const labelPoint = (conn.waypoints && conn.waypoints.length > 0) ? getPointOnPath(pathPoints, 0.5) : {x: (fromComp.x+toComp.x)/2, y: (fromComp.y+toComp.y)/2};
                ctx.fillText(`${iconDisplay} ${cableInfo.name}`, labelPoint.x - 20, labelPoint.y - 8);
                
                ctx.restore();
            });
            trafficAnimation = (trafficAnimation + 0.015) % 1;
        }
        
        function drawShapes() {
            shapes.forEach(shape => {
                const isSelected = selectedShapes.includes(shape);
                ctx.save(); ctx.fillStyle = shape.fillColor || 'rgba(0, 0, 0, 0.05)'; ctx.strokeStyle = shape.strokeColor || '#00e5ff'; ctx.lineWidth = shape.lineWidth || 2;
                if(shape.rotation) { ctx.translate(shape.x + (shape.type === 'door' ? 15 : 30), shape.y + (shape.type === 'door' ? 25 : 20)); ctx.rotate(shape.rotation * Math.PI / 180); ctx.translate(-(shape.x + (shape.type === 'door' ? 15 : 30)), -(shape.y + (shape.type === 'door' ? 25 : 20))); }
                switch(shape.type) {
                    case 'line': ctx.beginPath(); ctx.moveTo(shape.x1, shape.y1); ctx.lineTo(shape.x2, shape.y2); ctx.stroke(); break;
                    case 'door': ctx.fillStyle = 'rgba(139, 69, 19, 0.3)'; ctx.fillRect(shape.x, shape.y, 30, 50); ctx.strokeStyle = '#8B4513'; ctx.strokeRect(shape.x, shape.y, 30, 50); ctx.beginPath(); ctx.arc(shape.x + 30, shape.y + 25, 20, -Math.PI/2, Math.PI/2); ctx.stroke(); break;
                    case 'window': ctx.fillStyle = 'rgba(135, 206, 235, 0.3)'; ctx.fillRect(shape.x, shape.y, 60, 40); ctx.strokeStyle = '#87CEEB'; ctx.strokeRect(shape.x, shape.y, 60, 40); ctx.beginPath(); ctx.moveTo(shape.x + 30, shape.y); ctx.lineTo(shape.x + 30, shape.y + 40); ctx.moveTo(shape.x, shape.y + 20); ctx.lineTo(shape.x + 60, shape.y + 20); ctx.stroke(); break;
                    case 'text': ctx.font = `${(shape.fontSize || 14)}px Arial`; ctx.fillStyle = shape.textColor || '#e2e8f0'; ctx.fillText(shape.text || 'Texto', shape.x, shape.y); break;
                }
                if(shape.rotation) ctx.setTransform(1, 0, 0, 1, 0, 0);
                if(isSelected) { ctx.strokeStyle = '#00e5ff'; ctx.lineWidth = 2; if(shape.type === 'line') { ctx.beginPath(); ctx.moveTo(shape.x1 - 3, shape.y1 - 3); ctx.lineTo(shape.x2 + 3, shape.y2 + 3); ctx.moveTo(shape.x1 + 3, shape.y1 - 3); ctx.lineTo(shape.x2 - 3, shape.y2 + 3); ctx.stroke(); } else if(shape.type === 'text') { ctx.strokeRect(shape.x - 5, shape.y - 12, ctx.measureText(shape.text || 'Texto').width + 10, 18); } else { const w = 30; const h = shape.type === 'door' ? 50 : 40; ctx.strokeRect(shape.x - 3, shape.y - 3, w + 6, h + 6); } }
                ctx.restore();
            });
        }
        
        function drawComponents() {
            components.forEach(comp => {
                const isSelected = selectedComponents.includes(comp);
                if(comp.type === 'sensor') drawSensorAnimation(comp.x, comp.y, sensorAnimationTime);
                ctx.save(); ctx.translate(comp.x, comp.y); ctx.rotate((comp.rotation || 0) * Math.PI / 180); ctx.translate(-comp.x, -comp.y);
                const halfSize = iconSize / 2;
                
                if(comp.iconFile) {
                    ctx.drawImage(getCachedImage(`/uploads/icons/${comp.iconFile}`), comp.x-halfSize, comp.y-halfSize, iconSize, iconSize);
                } else {
                    ctx.fillStyle = comp.color || '#1e293b'; ctx.beginPath(); ctx.arc(comp.x, comp.y, iconSize/2, 0, 2*Math.PI); ctx.fill(); ctx.fillStyle = '#fff'; ctx.font = `${iconSize/2}px Arial`; const iconToShow = comp.icon || '📦'; ctx.fillText(iconToShow, comp.x-12, comp.y+8);
                }
                ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = '#00e5ff'; ctx.font = `${12}px Arial`; ctx.fillText(comp.name, comp.x-30, comp.y - (iconSize/2) - 5);
                if(isSelected) { ctx.strokeStyle = '#00e5ff'; ctx.lineWidth = 2; ctx.strokeRect(comp.x - halfSize - 4, comp.y - halfSize - 4, iconSize + 8, iconSize + 8); }
                ctx.restore();
            });
            sensorAnimationTime = (sensorAnimationTime + 0.01) % 1;
        }
        
        function drawWithBackground(whiteBg = false, hideGrid = false) {
            if(whiteBg) { ctx.fillStyle = '#FFFFFF'; ctx.fillRect(0, 0, canvas.width, canvas.height); }
            else { ctx.clearRect(0, 0, canvas.width, canvas.height); drawBackground(); }
            if(!hideGrid && showGrid) drawGrid();
            drawShapes(); drawConnections(); drawComponents();
        }
        
        function draw() {
            drawWithBackground(false, false);
            if(drawingPreview && shapeStart) { /* preview não implementado para simplificar */ }
            requestAnimationFrame(draw);
        }
        
        let lastMousePos = null;
        function getMousePos(e) {
            const rect = canvas.getBoundingClientRect(); const scaleX = canvas.width / rect.width; const scaleY = canvas.height / rect.height;
            let clientX, clientY;
            if (e.touches) { clientX = e.touches[0].clientX; clientY = e.touches[0].clientY; }
            else { clientX = e.clientX; clientY = e.clientY; }
            return { x: (clientX - rect.left) * scaleX, y: (clientY - rect.top) * scaleY };
        }
        
        function pointToLineDistance(px, py, x1, y1, x2, y2) {
            const A = px - x1; const B = py - y1; const C = x2 - x1; const D = y2 - y1; const dot = A * C + B * D; const len_sq = C * C + D * D; let param = -1; if (len_sq != 0) param = dot / len_sq;
            let xx, yy; if (param < 0) { xx = x1; yy = y1; } else if (param > 1) { xx = x2; yy = y2; } else { xx = x1 + param * C; yy = y1 + param * D; }
            const dx = px - xx; const dy = py - yy; return Math.sqrt(dx * dx + dy * dy);
        }
        
        function isPointNearConnection(x, y, conn) {
            const pathPoints = getConnectionPath(conn);
            if (!pathPoints) return false;
            for (let i = 0; i < pathPoints.length - 1; i++) {
                if (pointToLineDistance(x, y, pathPoints[i].x, pathPoints[i].y, pathPoints[i+1].x, pathPoints[i+1].y) < 12) return true;
            }
            return false;
        }
        
        function findWaypointAtPosition(x, y, connIdx) {
            const conn = connections[connIdx];
            if (!conn || !conn.waypoints) return -1;
            for (let i = 0; i < conn.waypoints.length; i++) {
                if (Math.hypot(x - conn.waypoints[i].x, y - conn.waypoints[i].y) < 12) return i;
            }
            return -1;
        }
        
        function handleStart(e) {
            e.preventDefault(); const {x, y} = getMousePos(e); lastMousePos = {x, y};
            
            // 1. Verifica waypoints de conexão selecionada
            if (selectedConnectionIndex !== null) {
                const wpIdx = findWaypointAtPosition(x, y, selectedConnectionIndex);
                if (wpIdx !== -1) {
                    draggingWaypoint = true;
                    waypointConnIdx = selectedConnectionIndex;
                    waypointIdx = wpIdx;
                    return;
                }
                // Clique no meio do cabo para adicionar waypoint
                const conn = connections[selectedConnectionIndex];
                if (conn && isPointNearConnection(x, y, conn)) {
                    if (!conn.waypoints) conn.waypoints = [];
                    conn.waypoints.push({x, y});
                    saveUserData();
                    showToast('✅ Ponto de curva adicionado! Arraste para curvar.');
                    return;
                }
            }
            
            // 2. Verifica componentes
            let clickedComp = null;
            for(let i=components.length-1; i>=0; i--) { const comp = components[i]; if(Math.hypot(x - comp.x, y - comp.y) < iconSize/2) { clickedComp = comp; break; } }
            if(clickedComp) {
                selectedComponents = [clickedComp]; dragging = true; dragOffset = {x: clickedComp.x - x, y: clickedComp.y - y};
                selectedShapes = []; selectedConnectionIndex = null;
                showProperties(clickedComp); openProperties(); return;
            }
            
            // 3. Verifica conexões
            let clickedConn = null;
            for(let i = 0; i < connections.length; i++) {
                if (isPointNearConnection(x, y, connections[i])) { clickedConn = i; break; }
            }
            if(clickedConn !== null) {
                selectedConnectionIndex = clickedConn;
                selectedComponents = []; selectedShapes = [];
                showConnectionProperties(clickedConn); openProperties();
                return;
            }
            
            selectedComponents = []; selectedShapes = []; selectedConnectionIndex = null;
            showProperties(null); closeProperties();
        }
        
        function handleMove(e) {
            const {x, y} = getMousePos(e); lastMousePos = {x, y};
            
            if (draggingWaypoint && waypointConnIdx !== null && waypointIdx !== null) {
                connections[waypointConnIdx].waypoints[waypointIdx] = {x, y};
                saveUserData();
                return;
            }
            
            if(dragging && selectedComponents.length > 0) {
                const dx = (x + dragOffset.x) - selectedComponents[0].x;
                const dy = (y + dragOffset.y) - selectedComponents[0].y;
                selectedComponents.forEach(comp => { comp.x += dx; comp.y += dy; });
                dragOffset = {x: selectedComponents[0].x - x, y: selectedComponents[0].y - y};
                saveUserData();
            }
        }
        
        function handleEnd(e) {
            dragging = false;
            draggingWaypoint = false;
            waypointConnIdx = null;
            waypointIdx = null;
        }
        
        function handleContextMenu(e) {
            e.preventDefault(); const {x, y} = getMousePos(e);
            for(let i = 0; i < connections.length; i++) {
                if (isPointNearConnection(x, y, connections[i])) {
                    contextMenuConnection = { conn: connections[i], idx: i };
                    const menu = document.getElementById('contextMenu');
                    menu.innerHTML = `<div class="context-menu-item" onclick="resetConnectionCurve(${i})">📏 Endireitar Cabo</div><div class="context-menu-item" onclick="deleteConnection(${i})">🗑 Excluir Conexão</div>`;
                    menu.style.display = 'block'; menu.style.left = e.pageX + 'px'; menu.style.top = e.pageY + 'px';
                    setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', {once: true}), 100);
                    return;
                }
            }
        }
        
        window.resetConnectionCurve = (idx) => {
            connections[idx].waypoints = [];
            saveUserData();
            showToast('📏 Cabo endireitado!');
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.deleteConnection = (idx) => {
            connections.splice(idx, 1);
            selectedConnectionIndex = null;
            saveUserData();
            showToast('🗑 Conexão removida!');
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        function showProperties(comp) {
            const div = document.getElementById('props-content');
            if(!comp) { div.innerHTML = '<p style="color:#94a3b8;">Clique em um componente para editar</p>'; return; }
            div.innerHTML = `
                <div class="property-group"><label>Nome</label><input type="text" id="prop-name" value="${comp.name.replace(/"/g, '&quot;')}"></div>
                <div class="property-group"><label>Posição X</label><input type="number" id="prop-x" value="${Math.round(comp.x)}"></div>
                <div class="property-group"><label>Posição Y</label><input type="number" id="prop-y" value="${Math.round(comp.y)}"></div>
                <div class="property-group"><label>IP</label><input type="text" id="prop-ip" value="${comp.ip || ''}"></div>
            `;
            document.getElementById('prop-name')?.addEventListener('change', (e) => { comp.name = e.target.value; saveUserData(); });
            document.getElementById('prop-x')?.addEventListener('change', (e) => { comp.x = parseInt(e.target.value); saveUserData(); });
            document.getElementById('prop-y')?.addEventListener('change', (e) => { comp.y = parseInt(e.target.value); saveUserData(); });
            document.getElementById('prop-ip')?.addEventListener('change', (e) => { comp.ip = e.target.value; saveUserData(); });
        }
        
        function showConnectionProperties(idx) {
            const div = document.getElementById('props-content');
            const conn = connections[idx];
            if(!conn) return;
            const fromComp = components.find(c => c.id === conn.from);
            const toComp = components.find(c => c.id === conn.to);
            div.innerHTML = `
                <div class="property-group"><label>Conexão</label><input type="text" value="${fromComp?.name} → ${toComp?.name}" disabled></div>
                <div class="property-group"><label>Tipo</label><input type="text" value="${conn.type}" disabled></div>
                <div class="property-group"><label>Curvas</label><p style="font-size:11px; color:#94a3b8;">${conn.waypoints?.length || 0} ponto(s)</p></div>
                <button class="btn btn-secondary" style="width:100%;" onclick="resetConnectionCurve(${idx})">📏 Endireitar Cabo</button>
            `;
        }
        
        function openProperties() { document.getElementById('propertiesPanel').classList.add('open'); }
        function closeProperties() { document.getElementById('propertiesPanel').classList.remove('open'); }
        function closePropertiesPanel() { document.getElementById('propertiesPanel').classList.remove('open'); }
        
        function readImageAsBase64(file) { return new Promise((resolve) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.readAsDataURL(file); }); }
        
        // ==================== LOGIN ====================
        async function doLogin() {
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;
            const response = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
            const data = await response.json();
            
            if (data.success) {
                currentUser = username; userRole = data.role;
                document.getElementById('loginScreen').style.display = 'none';
                document.getElementById('loadingOverlay').style.display = 'flex';
                document.getElementById('toolbar').style.display = 'flex';
                document.getElementById('userInfo').innerHTML = `<span>👤 ${username}</span><span class="user-role" style="background: var(--text-accent); color: #0f172a; padding: 2px 8px; border-radius: 12px; font-size: 10px;">${data.role.toUpperCase()}</span>`;
                
                if (data.role === 'admin' || data.role === 'master') {
                    document.getElementById('adminUsersBtn').style.display = 'inline-block';
                    document.getElementById('adminShapesBtn').style.display = 'inline-block';
                    document.getElementById('adminCategoriesBtn').style.display = 'inline-block';
                    document.getElementById('adminDevicesBtn').style.display = 'inline-block';
                    document.getElementById('adminConnectionsBtn').style.display = 'inline-block';
                    document.getElementById('resetDefaultsBtn').style.display = 'inline-block';
                    document.getElementById('adminDevBtn').style.display = 'inline-block';
                    document.getElementById('adminBgBtn').style.display = 'inline-block';
                }
                
                await Promise.all([loadDefaultConfig(), loadDefaultConnections()]);
                await loadUserData();
                
                document.getElementById('loadingOverlay').style.display = 'none';
                draw(); // Inicia o loop de renderização APÓS tudo carregado
                showToast(`Bem-vindo, ${username}!`);
            } else {
                document.getElementById('loginError').style.display = 'block';
            }
        }
        
        function logout() { fetch('/api/logout', { method: 'POST' }).then(() => location.reload()); }
        
        function loadDevImages() {
            const loginImg = document.getElementById('loginDevImage');
            const fallback = document.getElementById('loginAvatarFallback');
            const img = new Image();
            img.onload = () => { loginImg.src = img.src; loginImg.style.display = 'block'; fallback.style.display = 'none'; };
            img.onerror = () => { fallback.style.display = 'block'; };
            img.src = devImageBase64 ? 'data:image/png;base64,' + devImageBase64 : '/static/dev.png';
        }
        
        // ==================== PLACEHOLDERS PARA FUNÇÕES NÃO IMPLEMENTADAS ====================
        window.newProject = () => { if(confirm('Novo projeto?')) { components=[]; connections=[]; shapes=[]; saveUserData(); showToast('Novo projeto'); } };
        window.saveProjectToFile = () => { const data = {components, connections, shapes, background: backgroundImage, backgroundOpacity, backgroundWidth, backgroundHeight, backgroundX, backgroundY}; const blob = new Blob([JSON.stringify(data)], {type:'application/json'}); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'projeto.projetize'; a.click(); showToast('Projeto salvo'); };
        window.loadProjectFromFile = () => { const input = document.createElement('input'); input.type = 'file'; input.accept = '.projetize,.json'; input.onchange = (e) => { const reader = new FileReader(); reader.onload = (ev) => { const data = JSON.parse(ev.target.result); components = data.components || []; connections = data.connections || []; shapes = data.shapes || []; connections.forEach(c => { if (!c.waypoints) c.waypoints = []; }); saveUserData(); showToast('Projeto carregado'); }; reader.readAsText(e.target.files[0]); }; input.click(); };
        window.exportPDF = () => { drawWithBackground(true, true); setTimeout(() => { const imgData = canvas.toDataURL('image/png'); const w = window.open(''); w.document.write(`<img src="${imgData}" style="max-width:100%;" onload="window.print()">`); setTimeout(() => draw(), 500); }, 100); };
        window.exportPDFWithList = () => { window.exportPDF(); };
        window.generateBudget = () => { showToast('Orçamento gerado (placeholder)'); };
        window.deleteSelectedItems = () => { if(selectedComponents.length > 0) { components = components.filter(c => !selectedComponents.includes(c)); selectedComponents = []; saveUserData(); showToast('Itens excluídos'); } };
        window.openUserManagement = () => { showToast('Gerenciamento de usuários (placeholder)'); };
        window.toggleShapesToolbar = () => { showToast('Ferramenta de formas (placeholder)'); };
        window.openAddCategoryModal = () => { showToast('Adicionar categoria (placeholder)'); };
        window.openAddDeviceModal = () => { showToast('Adicionar equipamento (placeholder)'); };
        window.openAddConnectionModal = () => { showToast('Adicionar conexão (placeholder)'); };
        window.resetToDefaultConfig = () => { showToast('Restaurar padrões (placeholder)'); };
        window.toggleGrid = () => { showGrid = !showGrid; showToast(showGrid ? 'Grade visível' : 'Grade oculta'); };
        window.openBackgroundModal = () => { const input = document.createElement('input'); input.type = 'file'; input.accept = 'image/*'; input.onchange = async (e) => { const base64 = await readImageAsBase64(e.target.files[0]); const res = await fetch('/api/upload_background', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({image: base64}) }); const data = await res.json(); if(data.success) { backgroundImage = data.url; backgroundImageObj = new Image(); backgroundImageObj.onload = () => { backgroundWidth = backgroundImageObj.width; backgroundHeight = backgroundImageObj.height; backgroundX = canvas.width/2 - backgroundWidth/2; backgroundY = canvas.height/2 - backgroundHeight/2; saveUserData(); showToast('Planta adicionada'); }; backgroundImageObj.src = data.url; } }; input.click(); };
        window.openDevImageModal = () => { const input = document.createElement('input'); input.type = 'file'; input.accept = 'image/*'; input.onchange = async (e) => { const base64 = await readImageAsBase64(e.target.files[0]); const res = await fetch('/api/upload_dev_image', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({image: base64}) }); if(res.ok) { showToast('Foto atualizada'); setTimeout(() => location.reload(), 1000); } }; input.click(); };
        window.openDynamicBgModal = () => { showToast('Fundo dinâmico (placeholder)'); };
        window.togglePalette = () => { document.getElementById('palette').classList.toggle('collapsed'); };
        
        // Eventos do canvas
        canvas.addEventListener('touchstart', handleStart, { passive: false });
        canvas.addEventListener('touchmove', handleMove, { passive: false });
        canvas.addEventListener('touchend', handleEnd);
        canvas.addEventListener('mousedown', handleStart);
        canvas.addEventListener('mousemove', handleMove);
        canvas.addEventListener('mouseup', handleEnd);
        canvas.addEventListener('contextmenu', handleContextMenu);
        
        canvas.addEventListener('dragover', (e) => e.preventDefault());
        canvas.addEventListener('drop', (e) => {
            e.preventDefault(); const {x, y} = getMousePos(e); const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            components.push({ id: Date.now(), name: data.name, icon: data.icon, type: data.type, color: data.color, x, y, iconFile: null, ip: '' });
            showToast(`✅ ${data.name} adicionado`); saveUserData();
        });
        
        // Init
        (async function init() {
            await loadDefaultConfig();
            await loadDefaultConnections();
            categories = JSON.parse(JSON.stringify(defaultCategories));
            renderPalette();
            renderConnectionsPalette();
        })();
        loadDevImages();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
