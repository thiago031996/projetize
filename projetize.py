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

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['SECRET_KEY'] = 'projetize-super-secret-key-2026'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000 # Cache de 1 ano para arquivos estáticos

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
        os.path.join(STATIC_FOLDER, 'dev.png'),
        os.path.join(STATIC_FOLDER, 'dev.jpg'),
        os.path.join(STATIC_FOLDER, 'developer.png'),
    ]
    for path in possible_paths:
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"Erro ao tentar carregar de {path}: {e}")
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
            print(f"Erro ao salvar imagem: {e}")
            return None
    return None

def delete_icon_image(filename, is_default=False):
    target_folder = DEFAULT_ICONS_FOLDER if is_default else ICONS_FOLDER
    if filename and os.path.exists(os.path.join(target_folder, filename)):
        try:
            os.remove(os.path.join(target_folder, filename))
            return True
        except: pass
    return False

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
            print(f"Erro ao salvar imagem de fundo: {e}")
            return None
    return None

def delete_background_image(filename):
    if filename and os.path.exists(os.path.join(BACKGROUNDS_FOLDER, filename)):
        try:
            os.remove(os.path.join(BACKGROUNDS_FOLDER, filename))
            return True
        except: pass
    return False

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
            {'name': 'Sensor de Movimento', 'icon': '🔴', 'desc': 'Detecção de movimento - Central de Alarme', 'type': 'sensor', 'subtype': 'movement', 'color': '#005f99', 'iconFile': None},
            {'name': 'Sensor de Porta', 'icon': '🚪', 'desc': 'Abertura de porta - Central de Alarme', 'type': 'sensor', 'subtype': 'door', 'color': '#005f99', 'iconFile': None},
            {'name': 'Sensor de Fumaça', 'icon': '💨', 'desc': 'Detecção de fumaça - Central de Incêndio', 'type': 'sensor', 'subtype': 'smoke', 'color': '#005f99', 'iconFile': None},
            {'name': 'Sensor de Temperatura', 'icon': '🌡️', 'desc': 'Controle térmico - Central de Alarme', 'type': 'sensor', 'subtype': 'temperature', 'color': '#005f99', 'iconFile': None},
            {'name': 'Sensor de Umidade', 'icon': '💧', 'desc': 'Controle de umidade - Central de Alarme', 'type': 'sensor', 'subtype': 'humidity', 'color': '#005f99', 'iconFile': None}
        ]
    },
    'Controle de Acesso': {
        'icon': '🔑',
        'devices': [
            {'name': 'Cancela', 'icon': '🚗', 'desc': 'Controle de acesso', 'type': 'cancela', 'color': '#28a745', 'iconFile': None},
            {'name': 'Controle de Acesso', 'icon': '🔑', 'desc': 'Biometria/Cartão', 'type': 'controle_acesso', 'color': '#28a745', 'iconFile': None},
            {'name': 'Catraca', 'icon': '🚪', 'desc': 'Controle de fluxo', 'type': 'catraca', 'color': '#28a745', 'iconFile': None},
            {'name': 'Vídeo Porteiro', 'icon': '📹', 'desc': 'IP/analógico', 'type': 'video_porteiro', 'color': '#28a745', 'iconFile': None}
        ]
    },
    'Segurança': {
        'icon': '🚨',
        'devices': [
            {'name': 'Central Alarme', 'icon': '🚨', 'desc': 'Sensor perimetral', 'type': 'alarme', 'color': '#dc3545', 'iconFile': None},
            {'name': 'Central Incêndio', 'icon': '🔥', 'desc': 'Detecção', 'type': 'central_incendio', 'color': '#dc3545', 'iconFile': None}
        ]
    },
    'Energia': {
        'icon': '⚡',
        'devices': [
            {'name': 'Nobreak', 'icon': '🔋', 'desc': 'Estabilizador', 'type': 'nobreak', 'color': '#fd7e14', 'iconFile': None},
            {'name': 'Fonte Alimentação', 'icon': '⚡', 'desc': '12V/24V', 'type': 'fonte_alimentacao', 'color': '#fd7e14', 'iconFile': None},
            {'name': 'Eletrificador', 'icon': '⚡', 'desc': 'Cerca elétrica', 'type': 'eletrificador', 'color': '#fd7e14', 'iconFile': None},
            {'name': 'Energia', 'icon': '🔌', 'desc': 'Rede elétrica', 'type': 'energia', 'color': '#fd7e14', 'iconFile': None}
        ]
    },
    'Automação': {
        'icon': '⚙️',
        'devices': [
            {'name': 'Motor', 'icon': '⚙️', 'desc': 'Automação', 'type': 'motor', 'color': '#6c757d', 'iconFile': None}
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
    is_default = data.get('is_default', False)
    target_type = data.get('type', 'equipment')
    if not image_data or not image_data.startswith('data:image'):
        return jsonify({'success': False, 'error': 'Imagem inválida'}), 400
    target_folder = DEFAULT_ICONS_FOLDER if is_default else ICONS_FOLDER
    format_map = {'data:image/png;base64,': '.png', 'data:image/jpeg;base64,': '.jpg', 'data:image/jpg;base64,': '.jpg', 'data:image/gif;base64,': '.gif', 'data:image/webp;base64,': '.webp'}
    ext = '.png'
    for key, value in format_map.items():
        if image_data.startswith(key):
            ext = value
            image_data = image_data.replace(key, '')
            break
    else:
        image_data = image_data.split(',')[1] if ',' in image_data else image_data
    prefix = {'equipment': 'eqp', 'category': 'cat', 'connection': 'con'}.get(target_type, 'ico')
    filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(target_folder, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return jsonify({'success': True, 'filename': filename, 'type': target_type})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_global_categories', methods=['POST'])
@admin_required
def save_global_categories():
    data = request.json
    if data.get('categories'):
        save_json_file(DEFAULT_CONFIG_FILE, data['categories'])
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

@app.route('/api/save_global_connections', methods=['POST'])
@admin_required
def save_global_connections():
    data = request.json
    if data.get('connections'):
        save_json_file(DEFAULT_CONNECTIONS_FILE, data['connections'])
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

@app.route('/api/save_global_custom_devices', methods=['POST'])
@admin_required
def save_global_custom_devices():
    data = request.json
    if data.get('devices') is not None:
        save_json_file(CUSTOM_DEVICES_FILE, data['devices'])
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

@app.route('/api/load_custom_devices', methods=['GET'])
def get_custom_devices():
    return jsonify({'success': True, 'devices': load_json_file(CUSTOM_DEVICES_FILE, [])})

@app.route('/api/upload_background', methods=['POST'])
@login_required
def upload_background():
    data = request.json
    image_data = data.get('image', '')
    name = data.get('name', None)
    if not image_data or not image_data.startswith('data:image'):
        return jsonify({'success': False, 'error': 'Imagem inválida'}), 400
    filename = save_background_image(image_data, name)
    if filename:
        return jsonify({'success': True, 'filename': filename, 'url': f'/uploads/backgrounds/{filename}'})
    return jsonify({'success': False, 'error': 'Erro ao salvar imagem'}), 500

@app.route('/uploads/icons/<filename>')
def serve_icon(filename):
    return send_from_directory(ICONS_FOLDER, filename)

@app.route('/uploads/default_icons/<filename>')
def serve_default_icon(filename):
    return send_from_directory(DEFAULT_ICONS_FOLDER, filename)

@app.route('/uploads/backgrounds/<filename>')
def serve_background(filename):
    return send_from_directory(BACKGROUNDS_FOLDER, filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

@app.route('/api/default_config', methods=['GET'])
def get_default_config():
    return jsonify({'success': True, 'config': load_json_file(DEFAULT_CONFIG_FILE, DEFAULT_CATEGORIES_CONFIG)})

@app.route('/api/default_connections', methods=['GET'])
def get_default_connections():
    return jsonify({'success': True, 'config': load_json_file(DEFAULT_CONNECTIONS_FILE, DEFAULT_CONNECTIONS_CONFIG)})

@app.route('/api/reset_default_config', methods=['POST'])
@admin_required
def reset_default_config():
    for filename in os.listdir(DEFAULT_ICONS_FOLDER):
        try: os.remove(os.path.join(DEFAULT_ICONS_FOLDER, filename))
        except: pass
    save_json_file(DEFAULT_CONFIG_FILE, DEFAULT_CATEGORIES_CONFIG)
    return jsonify({'success': True})

@app.route('/api/reset_default_connections', methods=['POST'])
@admin_required
def reset_default_connections():
    save_json_file(DEFAULT_CONNECTIONS_FILE, DEFAULT_CONNECTIONS_CONFIG)
    return jsonify({'success': True})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
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
    if session.get('role') not in ['admin', 'master']:
        return jsonify({'error': 'Permissão negada'}), 403
    safe_users = {}
    for username, user_data in users.items():
        safe_users[username] = {'role': user_data['role'], 'created_at': user_data.get('created_at', '')}
    return jsonify(safe_users)

@app.route('/api/users', methods=['POST'])
@login_required
def add_user():
    if session.get('role') not in ['admin', 'master']:
        return jsonify({'error': 'Permissão negada'}), 403
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'viewer')
    if not username or not password:
        return jsonify({'error': 'Usuário e senha são obrigatórios'}), 400
    if username in users:
        return jsonify({'error': 'Usuário já existe'}), 400
    users[username] = {'password': hash_password(password), 'role': role, 'created_at': datetime.now().isoformat()}
    save_users(users)
    return jsonify({'success': True})

@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
def delete_user(username):
    if session.get('role') not in ['admin', 'master']:
        return jsonify({'error': 'Permissão negada'}), 403
    if username == 'thiago03':
        return jsonify({'error': 'Não é possível excluir o usuário master'}), 400
    if username in users:
        del users[username]
        save_users(users)
        return jsonify({'success': True})
    return jsonify({'error': 'Usuário não encontrado'}), 404

# ==================== HTML_TEMPLATE OTIMIZADO ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover, shrink-to-fit=no">
    <title>Projetize - Sistema Para CFTV, Redes e muito mais...</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; overflow: hidden; position: fixed; top: 0; left: 0; right: 0; bottom: 0; }
        :root {
            --bg-primary: #ffffff; --bg-secondary: #f8f9fa; --bg-tertiary: #e9ecef;
            --bg-card: #ffffff; --text-primary: #212529; --text-secondary: #6c757d;
            --text-accent: #005f99; --border-color: #dee2e6; --button-primary: #005f99;
            --button-primary-hover: #004d7a; --button-secondary: #e9ecef;
            --button-secondary-hover: #dee2e6; --shadow: rgba(0, 95, 153, 0.2);
            --palette-width: 280px;
            --properties-width: 320px;
        }
        @media (max-width: 1024px) { :root { --palette-width: 240px; --properties-width: 280px; } }
        @media (max-width: 768px) {
            :root { --palette-width: 220px; --properties-width: 260px; }
            body { overflow: auto; position: relative; height: auto; min-height: 100vh; }
        }
        @media (max-width: 576px) { :root { --palette-width: 180px; --properties-width: 240px; } }
        
        .rgb-line { position: fixed; top: 0; left: 0; width: 100%; height: 3px; background: linear-gradient(90deg, #005f99, #0099cc, #00ccff, #005f99); background-size: 300% 100%; animation: rgbMove 3s linear infinite; z-index: 10000; }
        @keyframes rgbMove { 0% { background-position: 0% 0%; } 100% { background-position: 300% 100%; } }
        
        .intro-screen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #001a2e, #00264d); display: flex; justify-content: center; align-items: center; z-index: 25000; overflow-y: auto; padding: 20px; }
        .matrix-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden; font-family: monospace; color: #ffffff; z-index: 0; opacity: 0.3; pointer-events: none; }
        .matrix-column { position: absolute; top: -100%; animation: matrixFall linear infinite; white-space: pre; font-size: 16px; line-height: 1.2; opacity: 0.8; text-shadow: 0 0 8px #ffffff; color: #ffffff; font-weight: bold; }
        @keyframes matrixFall { 0% { top: -100%; } 100% { top: 100%; } }
        .intro-slider-container { position: relative; z-index: 2; width: 100%; max-width: 900px; background: rgba(0, 38, 77, 0.85); backdrop-filter: blur(12px); border-radius: 20px; padding: 25px; border: 1px solid rgba(255,255,255,0.3); box-shadow: 0 0 40px rgba(0,0,0,0.5); max-height: 90vh; overflow-y: auto; animation: fadeInUp 0.6s ease-out; }
        .intro-slider-container::-webkit-scrollbar { width: 6px; }
        .intro-slider-container::-webkit-scrollbar-track { background: rgba(255,255,255,0.1); border-radius: 3px; }
        .intro-slider-container::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.3); border-radius: 3px; }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        .intro-slide { display: none; text-align: center; animation: slideFade 0.8s ease-out; }
        .intro-slide.active { display: block; }
        @keyframes slideFade { from { opacity: 0; transform: translateX(50px); } to { opacity: 1; transform: translateX(0); } }
        .slide-title { font-size: 28px; color: #ffffff; margin-bottom: 15px; text-shadow: 0 0 15px #ffffff; display: flex; align-items: center; justify-content: center; gap: 15px; }
        @media (max-width: 576px) { .slide-title { font-size: 22px; } }
        .slide-content { color: #e0e0ff; font-size: 14px; line-height: 1.5; text-align: left; max-width: 600px; margin: 0 auto; background: rgba(0,0,0,0.4); padding: 20px; border-radius: 15px; border-left: 4px solid #ffffff; }
        @media (max-width: 576px) { .slide-content { font-size: 12px; padding: 15px; } }
        .slide-content ul { margin-left: 20px; margin-top: 10px; }
        .slide-content li { margin: 8px 0; }
        .slide-icon { font-size: 48px; margin-bottom: 20px; filter: drop-shadow(0 0 10px #ffffff); }
        @media (max-width: 576px) { .slide-icon { font-size: 36px; } }
        .dev-slide-image { width: 100px; height: 100px; border-radius: 50%; margin: 0 auto 15px; overflow: hidden; border: 3px solid #ffffff; box-shadow: 0 0 20px rgba(255,255,255,0.5); background: #005f99; display: flex; align-items: center; justify-content: center; }
        @media (max-width: 576px) { .dev-slide-image { width: 80px; height: 80px; } }
        .dev-slide-image img { width: 100%; height: 100%; object-fit: cover; }
        .slide-dots { display: flex; justify-content: center; gap: 12px; margin: 20px 0; flex-wrap: wrap; }
        .dot { width: 10px; height: 10px; background: rgba(255,255,255,0.4); border-radius: 50%; cursor: pointer; transition: all 0.3s; }
        .dot.active { background: #ffffff; box-shadow: 0 0 15px #ffffff; transform: scale(1.2); }
        .slide-nav { display: flex; justify-content: center; gap: 20px; margin: 20px 0 15px; flex-wrap: wrap; }
        .nav-btn { background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.5); color: white; padding: 8px 25px; border-radius: 30px; cursor: pointer; transition: all 0.3s; font-weight: bold; font-size: 14px; }
        @media (max-width: 576px) { .nav-btn { padding: 6px 20px; font-size: 12px; } }
        .nav-btn:hover { background: #ffffff; color: #001a2e; transform: scale(1.02); box-shadow: 0 0 20px rgba(255,255,255,0.5); }
        .access-btn { background: #ffffff; color: #001a2e; border: none; padding: 10px 30px; border-radius: 30px; font-size: 14px; font-weight: bold; cursor: pointer; margin: 10px auto 5px; transition: all 0.3s; animation: btnPulse 2s infinite; display: inline-block; }
        @media (max-width: 576px) { .access-btn { padding: 8px 25px; font-size: 13px; } }
        .access-btn:hover { background: #00ccff; color: #fff; transform: scale(1.02); box-shadow: 0 0 25px rgba(255, 255, 255, 0.6); }
        @keyframes btnPulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.4); } 50% { box-shadow: 0 0 0 12px rgba(255, 255, 255, 0); } }
        .intro-footer-note { text-align: center; margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 11px; color: rgba(255,255,255,0.6); }
        
        .login-modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #001a2e, #00264d); display: none; justify-content: center; align-items: center; z-index: 20000; overflow-y: auto; padding: 20px; }
        .login-dev-container { position: relative; z-index: 2; width: 100%; max-width: 500px; background: rgba(0, 38, 77, 0.9); backdrop-filter: blur(10px); border-radius: 20px; padding: 40px; text-align: center; border: 1px solid #ffffff; box-shadow: 0 0 30px rgba(255, 255, 255, 0.2); animation: fadeInScale 0.5s ease-out; }
        @keyframes fadeInScale { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
        .login-dev-image { width: 150px; height: 150px; border-radius: 50%; margin: 0 auto 20px; overflow: hidden; border: 3px solid #ffffff; box-shadow: 0 0 30px rgba(255, 255, 255, 0.5); animation: borderGlow 2s ease-in-out infinite; display: flex; align-items: center; justify-content: center; background: #005f99; }
        @media (max-width: 768px) { .login-dev-image { width: 120px; height: 120px; } }
        @keyframes borderGlow { 0%, 100% { border-color: #ffffff; box-shadow: 0 0 20px #ffffff; } 50% { border-color: #00ccff; box-shadow: 0 0 40px #00ccff; } }
        .login-dev-image img { width: 100%; height: 100%; object-fit: cover; }
        .login-dev-name { font-size: 24px; color: #ffffff; margin-bottom: 5px; font-weight: bold; text-shadow: 0 0 10px rgba(255,255,255,0.5); }
        .login-dev-role { font-size: 12px; color: #ccccff; margin-bottom: 20px; }
        .login-logo { font-size: 50px; margin-bottom: 15px; animation: logoFloat 3s ease-in-out infinite; }
        @keyframes logoFloat { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
        .login-title { font-size: 28px; color: #ffffff; margin-bottom: 10px; font-weight: bold; text-shadow: 0 0 10px rgba(255,255,255,0.5); }
        .login-subtitle { color: #ccccff; font-size: 12px; margin-bottom: 25px; }
        .login-input { width: 100%; padding: 12px; margin: 10px 0; background: rgba(0, 38, 77, 0.8); border: 1px solid #ffffff; border-radius: 8px; color: #fff; font-size: 14px; transition: all 0.3s ease; }
        .login-input:focus { outline: none; border-color: #00ccff; box-shadow: 0 0 10px rgba(0, 204, 255, 0.5); transform: scale(1.02); }
        .login-input::placeholder { color: #88aacc; }
        .login-btn { width: 100%; padding: 12px; background: #ffffff; border: none; border-radius: 8px; color: #001a2e; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; transition: all 0.3s; }
        .login-btn:hover { background: #00ccff; color: #fff; transform: scale(1.02); box-shadow: 0 0 20px rgba(255, 255, 255, 0.5); }
        .login-error { color: #ff6666; font-size: 12px; margin-top: 15px; display: none; }
        .login-footer { margin-top: 25px; padding-top: 15px; border-top: 1px solid #ffffff; font-size: 11px; color: #ccccff; }
        .login-footer a { color: #ffffff; text-decoration: none; transition: all 0.3s; }
        .login-footer a:hover { text-shadow: 0 0 10px #ffffff; }
        
        .splash-screen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #001a2e, #00264d); display: flex; justify-content: center; align-items: center; z-index: 15000; animation: fadeOut 3s ease-in-out forwards; pointer-events: none; }
        @keyframes fadeOut { 0% { opacity: 1; visibility: visible; } 70% { opacity: 1; } 100% { opacity: 0; visibility: hidden; } }
        .splash-content { text-align: center; z-index: 2; animation: zoomIn 0.8s ease-out; }
        @keyframes zoomIn { from { opacity: 0; transform: scale(0.5); } to { opacity: 1; transform: scale(1); } }
        .splash-logo { font-size: 100px; margin-bottom: 20px; animation: splashPulse 1.5s ease-in-out infinite; }
        @keyframes splashPulse { 0%, 100% { transform: scale(1); text-shadow: 0 0 20px #ffffff; } 50% { transform: scale(1.05); text-shadow: 0 0 40px #ffffff; } }
        .splash-title { font-size: 48px; background: linear-gradient(45deg, #ffffff, #00ccff, #005f99); -webkit-background-clip: text; background-clip: text; color: transparent; margin-bottom: 10px; }
        .splash-subtitle { color: #88aacc; font-size: 16px; }
        
        .dev-badge { position: fixed; top: 10px; left: 10px; width: 45px; height: 45px; border-radius: 50%; background: var(--bg-tertiary); border: 2px solid var(--border-color); cursor: pointer; z-index: 1000; overflow: hidden; transition: all 0.3s ease; box-shadow: 0 0 10px var(--shadow); }
        .dev-badge:hover { width: 280px; border-radius: 25px; background: var(--bg-tertiary); }
        .dev-badge-img { width: 41px; height: 41px; border-radius: 50%; object-fit: cover; float: left; }
        .dev-badge-info { display: none; float: left; padding: 5px 10px; color: var(--text-primary); font-size: 11px; white-space: nowrap; }
        .dev-badge:hover .dev-badge-info { display: block; }
        .dev-badge-name { color: var(--text-accent); font-weight: bold; }
        
        .toolbar { background: var(--bg-secondary); padding: 8px 15px; display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 2px solid var(--border-color); box-shadow: 0 4px 15px rgba(0,0,0,0.1); z-index: 100; position: relative; margin-left: 60px; }
        @media (max-width: 768px) { .toolbar { margin-left: 50px; padding: 5px 10px; gap: 5px; } }
        .btn { padding: 6px 12px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; font-size: 12px; display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
        @media (max-width: 768px) { .btn { padding: 4px 8px; font-size: 10px; } }
        @media (max-width: 576px) { .btn { padding: 3px 6px; font-size: 9px; } .btn span { display: none; } .btn { font-size: 14px; } }
        .btn-primary { background: var(--button-primary); color: #fff; }
        .btn-primary:hover { background: var(--button-primary-hover); transform: scale(1.02); }
        .btn-secondary { background: var(--button-secondary); color: var(--text-primary); border: 1px solid var(--border-color); }
        .btn-secondary:hover { background: var(--button-secondary-hover); transform: scale(1.02); }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-info { background: var(--button-secondary); color: var(--text-primary); }
        .btn-warning { background: #ffc107; color: #212529; }
        .user-info { display: flex; align-items: center; gap: 10px; background: var(--bg-tertiary); padding: 4px 12px; border-radius: 20px; color: var(--text-primary); font-size: 12px; }
        @media (max-width: 576px) { .user-info { padding: 2px 8px; font-size: 10px; } }
        .user-role { background: var(--text-accent); color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 10px; }
        
        .main-container { display: flex; height: calc(100vh - 52px); position: relative; overflow: hidden; }
        @media (max-width: 768px) { .main-container { height: calc(100vh - 48px); flex-direction: column; } }
        
        .palette { width: var(--palette-width); background: var(--bg-tertiary); color: var(--text-primary); overflow-y: auto; padding: 10px; border-right: 2px solid var(--border-color); transition: width 0.3s ease, min-width 0.3s ease, transform 0.3s ease; position: relative; flex-shrink: 0; }
        .palette.collapsed { width: 50px; min-width: 50px; }
        .palette.collapsed .category h3, .palette.collapsed .component-info, .palette.collapsed .category-actions, .palette.collapsed .component-actions { display: none; }
        .palette.collapsed .component { justify-content: center; padding: 6px; }
        .toggle-palette { position: sticky; top: 10px; right: -12px; float: right; background: var(--button-primary); border: none; color: #fff; width: 24px; height: 40px; border-radius: 0 8px 8px 0; cursor: pointer; z-index: 10; font-size: 12px; margin-bottom: 10px; }
        
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
        .component-actions { position: absolute; right: 5px; top: 50%; transform: translateY(-50%); display: none; gap: 5px; }
        .component:hover .component-actions { display: flex; }
        .component-actions button { background: var(--button-primary); border: none; color: #fff; border-radius: 3px; cursor: pointer; font-size: 10px; padding: 2px 4px; }
        
        .shapes-toolbar { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: var(--bg-secondary); padding: 8px 15px; border-radius: 30px; display: flex; gap: 8px; z-index: 150; border: 1px solid var(--border-color); flex-wrap: wrap; max-width: 90%; justify-content: center; }
        .shape-btn { background: var(--bg-tertiary); border: none; color: var(--text-primary); padding: 6px 12px; border-radius: 20px; cursor: pointer; font-size: 12px; transition: all 0.2s; }
        .shape-btn:hover, .shape-btn.active { background: var(--button-primary); color: #fff; transform: scale(1.05); }
        
        .canvas-area { flex: 1; background: var(--bg-primary); overflow: auto; position: relative; cursor: default; -webkit-overflow-scrolling: touch; }
        .canvas-area::-webkit-scrollbar { width: 12px; height: 12px; }
        .canvas-area::-webkit-scrollbar-track { background: #e9ecef; border-radius: 6px; }
        .canvas-area::-webkit-scrollbar-thumb { background: #005f99; border-radius: 6px; }
        #canvas { background: var(--bg-primary); box-shadow: 0 0 20px rgba(0,0,0,0.1); cursor: crosshair; display: block; margin: 20px auto; transform-origin: 0 0; }
        @media (max-width: 768px) { #canvas { margin: 10px auto; } }
        
        .properties { width: 0; background: var(--bg-tertiary); color: var(--text-primary); padding: 0; overflow-y: auto; border-left: none; transition: width 0.3s ease; position: relative; flex-shrink: 0; }
        .properties.open { width: var(--properties-width); padding: 15px; border-left: 2px solid var(--border-color); }
        .properties-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .close-properties-btn { background: none; border: none; font-size: 18px; cursor: pointer; color: var(--text-secondary); padding: 5px; }
        .close-properties-btn:hover { color: var(--text-accent); }
        @media (max-width: 768px) { .properties.open { width: 260px; padding: 10px; } .properties h3 { font-size: 12px; } }
        
        .property-group { margin-bottom: 12px; }
        .property-group label { display: block; font-size: 11px; margin-bottom: 4px; color: var(--text-accent); }
        .property-group input, .property-group select, .property-group textarea { width: 100%; padding: 6px; border-radius: 5px; border: none; background: var(--bg-card); color: var(--text-primary); font-size: 12px; border: 1px solid var(--border-color); }
        
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: center; z-index: 3000; padding: 20px; }
        .modal-content { background: var(--bg-secondary); padding: 25px; border-radius: 12px; width: 500px; max-width: 100%; max-height: 85%; overflow-y: auto; border: 1px solid var(--border-color); }
        @media (max-width: 576px) { .modal-content { padding: 15px; } }
        .modal-content input, .modal-content select, .modal-content textarea { width: 100%; padding: 8px; margin: 8px 0; background: var(--bg-tertiary); border: none; border-radius: 5px; color: var(--text-primary); }
        .modal-buttons { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
        
        .user-list { max-height: 300px; overflow-y: auto; margin: 15px 0; }
        .user-item { background: var(--bg-tertiary); padding: 10px; margin: 5px 0; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .user-actions button { background: none; border: none; cursor: pointer; margin-left: 8px; font-size: 16px; }
        
        .toast { position: fixed; bottom: 20px; right: 20px; background: var(--button-primary); color: #fff; padding: 10px 20px; border-radius: 5px; z-index: 4000; animation: slideIn 0.3s ease; max-width: 90%; word-break: break-word; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        
        .selection-rect { position: absolute; border: 2px dashed #005f99; background: rgba(0, 95, 153, 0.2); display: none; pointer-events: none; z-index: 1000; }
        .context-menu { position: fixed; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 5px 0; z-index: 2000; display: none; min-width: 180px; }
        .context-menu-item { padding: 8px 15px; cursor: pointer; color: var(--text-primary); font-size: 12px; transition: all 0.2s; }
        .context-menu-item:hover { background: var(--button-primary); color: #fff; }
        .selection-info { position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); background: var(--bg-secondary); color: var(--text-primary); padding: 4px 10px; border-radius: 20px; font-size: 11px; z-index: 1000; pointer-events: none; border: 1px solid var(--border-color); white-space: nowrap; }
        
        @keyframes signalWave { 0% { transform: scale(0.8); opacity: 0; } 50% { transform: scale(1.2); opacity: 0.8; } 100% { transform: scale(1.5); opacity: 0; } }
        @keyframes radioWave { 0% { transform: scale(0.5); opacity: 0; } 50% { transform: scale(1); opacity: 0.6; } 100% { transform: scale(1.3); opacity: 0; } }
        @keyframes dataPacket { 0% { transform: translateX(-20px) scale(0.5); opacity: 0; } 20% { opacity: 1; } 80% { opacity: 1; } 100% { transform: translateX(20px) scale(1); opacity: 0; } }
        .connection-animation { position: absolute; pointer-events: none; z-index: 1000; }
        .connection-wave { position: absolute; border-radius: 50%; animation: signalWave 1.5s ease-out infinite; }
        .radio-wave { position: absolute; border-radius: 50%; animation: radioWave 1.5s ease-out infinite; }
        .data-packet { position: absolute; width: 8px; height: 8px; border-radius: 2px; animation: dataPacket 1s linear infinite; }
        .reset-defaults-btn { margin-top: 10px; width: 100%; }
        .background-controls { background: var(--bg-secondary); padding: 12px; border-radius: 8px; margin-bottom: 15px; border: 1px solid var(--border-color); }
        .background-preview { max-width: 100%; max-height: 150px; object-fit: contain; margin-top: 8px; border-radius: 4px; cursor: move; }
        .image-preview { margin-top: 8px; text-align: center; }
        .image-resize-handle { position: absolute; width: 12px; height: 12px; background: #005f99; border: 2px solid white; border-radius: 2px; z-index: 20; cursor: nw-resize; box-shadow: 0 0 5px rgba(0,0,0,0.5); }
        .image-resize-handle.se { bottom: -6px; right: -6px; cursor: se-resize; }
        .image-resize-handle.ne { top: -6px; right: -6px; cursor: ne-resize; }
        .image-resize-handle.sw { bottom: -6px; left: -6px; cursor: sw-resize; }
        .image-resize-handle.nw { top: -6px; left: -6px; cursor: nw-resize; }
        .image-container { position: relative; display: inline-block; }
        .selected-image { outline: 3px solid #005f99; outline-offset: 2px; }
        .action-buttons { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
        .zoom-controls { display: inline-flex; align-items: center; gap: 5px; margin-left: 10px; }
        .zoom-controls button { background: var(--button-secondary); border: 1px solid var(--border-color); padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; }
        .zoom-controls button:hover { background: var(--button-secondary-hover); }
        .zoom-controls span { font-size: 12px; color: var(--text-primary); }
        @media (max-width: 576px) { .zoom-controls span { display: none; } }
        
        .mobile-menu-toggle { display: none; position: fixed; bottom: 20px; left: 20px; background: var(--button-primary); color: white; border: none; border-radius: 50%; width: 50px; height: 50px; font-size: 24px; cursor: pointer; z-index: 200; box-shadow: 0 2px 10px rgba(0,0,0,0.3); }
        @media (max-width: 768px) { .mobile-menu-toggle { display: flex; align-items: center; justify-content: center; } }
        .mobile-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 199; display: none; }
        
        .delete-shape-btn { position: fixed; background: #dc3545; color: white; border: none; border-radius: 20px; padding: 8px 16px; font-size: 12px; cursor: pointer; z-index: 250; display: none; box-shadow: 0 2px 10px rgba(0,0,0,0.3); }
        .delete-shape-btn:hover { background: #c82333; transform: scale(1.02); }
        
        @media (hover: none) and (pointer: coarse) {
            .component, .shape-btn, .btn, .category-actions button, .component-actions button { cursor: pointer; -webkit-tap-highlight-color: transparent; }
            .component:active { opacity: 0.7; }
            .context-menu-item { padding: 12px 20px; font-size: 14px; }
            .btn { padding: 8px 12px; }
        }
    </style>
</head>
<body>
    <button class="mobile-menu-toggle" onclick="toggleMobilePalette()">📋</button>
    <div class="mobile-overlay" id="mobileOverlay" onclick="closeMobilePalette()"></div>
    <div class="rgb-line"></div>
    
    <div class="intro-screen" id="introScreen">
        <div class="matrix-bg" id="introMatrixBg"></div>
        <div class="intro-slider-container">
            <div class="intro-slide active" data-slide="0">
                <div class="slide-icon">🎥🔒🌐</div>
                <div class="slide-title">PROJETIZE</div>
                <div class="slide-content">
                    <h3>📌 Bem-vindo ao Projetize</h3>
                    <p>Sistema completo para criação de projetos de CFTV, redes de computadores, automação e muito mais.</p>
                    <ul>
                        <li>✅ Importe plantas baixas como imagem de fundo</li>
                        <li>✅ Arraste e posicione equipamentos sobre a planta</li>
                        <li>✅ Crie conexões entre equipamentos (cabeadas e sem fio)</li>
                        <li>✅ Desenhe formas, portas, janelas e textos no canvas</li>
                        <li>✅ Exporte projetos em PDF com lista de equipamentos</li>
                        <li>✅ Gere orçamento automático</li>
                    </ul>
                </div>
            </div>
            <div class="intro-slide" data-slide="1">
                <div class="slide-icon">🎯🖱️</div>
                <div class="slide-title">Como Usar</div>
                <div class="slide-content">
                    <ul>
                        <li><strong>📁 Novo Projeto:</strong> Cria um projeto em branco</li>
                        <li><strong>💾 Salvar / 📂 Carregar:</strong> Salve e carregue seus projetos em arquivo .projetize</li>
                        <li><strong>🖼️ Planta:</strong> Importe uma imagem para usar como planta baixa (PNG, JPG)</li>
                        <li><strong>📦 Equipamentos:</strong> Arraste os ícones da barra lateral para o canvas</li>
                        <li><strong>🔌 Conexões:</strong> Shift + clique em dois equipamentos para conectá-los</li>
                        <li><strong>📐 Formas:</strong> Ative o modo de desenho para adicionar formas geométricas</li>
                        <li><strong>🔍 Zoom:</strong> Use os botões de zoom para ampliar o canvas ou aumentar ícones</li>
                        <li><strong>✏️ Edição:</strong> Clique em qualquer equipamento para editar suas propriedades</li>
                        <li><strong>🗑 Excluir:</strong> Selecione itens e use o botão "Excluir Selecionados"</li>
                        <li><strong>🔌 Editar Conexão:</strong> Clique no cabo para selecionar e editar</li>
                        <li><strong>🖼️ Mover Planta:</strong> Selecione a planta e arraste para mover</li>
                        <li><strong>📐 Formas:</strong> Clique na forma para mover, editar ou excluir</li>
                        <li><strong>🎨 Ícones Personalizados:</strong> Clique com botão direito em qualquer item para alterar seu ícone permanentemente</li>
                    </ul>
                </div>
            </div>
            <div class="intro-slide" data-slide="2">
                <div class="slide-icon">👨‍💻⚙️</div>
                <div class="slide-title">Desenvolvedor</div>
                <div class="slide-content" style="text-align: center;">
                    <div class="dev-slide-image" id="devSlideImage">
                        <img id="devSlideImg" src="" alt="Thiago Souza" style="display:none;">
                    </div>
                    <p><strong>Thiago Souza</strong> - Analista de Tecnologia</p>
                    <p>Unidade 2 - São José do Rio Preto</p>
                    <p>📱 Contato: (17) 99600-9537</p>
                    <p>📧 thiago@projetize.com.br</p>
                    <p style="margin-top: 15px;">Todos os direitos reservados © 2026</p>
                </div>
            </div>
            <div class="slide-dots">
                <div class="dot active" onclick="currentSlide(0)"></div>
                <div class="dot" onclick="currentSlide(1)"></div>
                <div class="dot" onclick="currentSlide(2)"></div>
            </div>
            <div class="slide-nav">
                <button class="nav-btn" onclick="prevSlide()">◀ Anterior</button>
                <button class="nav-btn" onclick="nextSlide()">Próximo ▶</button>
            </div>
            <div style="text-align: center;">
                <button class="access-btn" onclick="closeIntroAndShowLogin()">🔓 Acessar Sistema</button>
            </div>
            <div class="intro-footer-note">
                <span>Versão 2.0 | Desenvolvido com 💙 por Thiago Souza</span>
            </div>
        </div>
    </div>
    
    <div class="splash-screen" id="splashScreen">
        <div class="splash-content">
            <div class="splash-logo">🎥🔒🌐</div>
            <div class="splash-title">PROJETIZE</div>
            <div class="splash-subtitle">Sistema Para CFTV, Redes e muito mais...</div>
        </div>
    </div>
    
    <div class="login-modal" id="loginModal">
        <div class="matrix-bg" id="matrixBg"></div>
        <div class="login-dev-container">
            <div class="login-dev-image" id="loginDevImageContainer">
                <img id="loginDevImage" src="" alt="Thiago Souza" style="display:none;">
            </div>
            <div class="login-dev-name">Thiago Souza</div>
            <div class="login-dev-role">Analista de Tecnologia | Unidade 2 - São José do Rio Preto</div>
            <div class="login-logo">🎥🔒</div>
            <div class="login-title">PROJETIZE</div>
            <div class="login-subtitle">Sistema Para CFTV, Redes e muito mais...</div>
            <input type="text" id="loginUsername" class="login-input" placeholder="Usuário">
            <input type="password" id="loginPassword" class="login-input" placeholder="Senha">
            <button class="login-btn" onclick="doLogin()">Entrar</button>
            <div class="login-footer">
                Desenvolvido por <strong>Thiago Souza</strong><br>
                Todos os direitos reservados © 2026<br>
                <a href="https://wa.me/5517996009537" target="_blank">📱 Contato: (17) 99600-9537</a>
            </div>
            <div class="login-error" id="loginError">Usuário ou senha inválidos</div>
        </div>
    </div>
    
    <div class="dev-badge" id="devBadge">
        <img class="dev-badge-img" id="badgeDevImage" src="" alt="TS">
        <div class="dev-badge-info">
            <div class="dev-badge-name">Thiago Souza</div>
            <div>Analista de Tecnologia</div>
            <div style="font-size: 9px;">Unidade 2 - São José do Rio Preto</div>
        </div>
    </div>
    
    <div class="selection-info" id="selectionInfo"></div>
    <div class="selection-rect" id="selectionRect"></div>
    <div class="context-menu" id="contextMenu"></div>
    
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
        <button class="btn btn-danger" onclick="logout()">🚪 Sair</button>
        <span style="flex:1"></span>
        <div class="user-info" id="userInfo"></div>
        <div class="zoom-controls">
            <span>🔍 Zoom:</span>
            <button onclick="zoomIn()">+</button>
            <button onclick="zoomOut()">-</button>
            <button onclick="resetZoom()">Reset</button>
        </div>
        <div class="zoom-controls">
            <span>📐 Ícones:</span>
            <button onclick="iconZoomIn()">+</button>
            <button onclick="iconZoomOut()">-</button>
            <button onclick="resetIconSize()">Reset</button>
        </div>
    </div>
    
    <div class="shapes-toolbar" id="shapesToolbar" style="display: none;">
        <button class="shape-btn" onclick="setShapeMode('line')" title="Linha">📏 Linha</button>
        <button class="shape-btn" onclick="setShapeMode('door')" title="Porta">🚪 Porta</button>
        <button class="shape-btn" onclick="setShapeMode('window')" title="Janela">🪟 Janela</button>
        <button class="shape-btn" onclick="setShapeMode('text')" title="Texto">📝 Texto</button>
        <button class="shape-btn" onclick="cancelShapeMode()" title="Cancelar">❌ Cancelar</button>
    </div>
    
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
    <div id="deleteShapeBtn" class="delete-shape-btn" onclick="deleteSelectedShape()">🗑 Excluir Forma</div>
    
    <script>
        // ==================== CONFIGURAÇÕES INICIAIS & OTIMIZAÇÃO ====================
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
        let currentAngleHandle = null;
        let isSelecting = false;
        let selectionStart = {x:0, y:0};
        let selectionEnd = {x:0, y:0};
        let contextMenuComponent = null;
        let contextMenuShape = null;
        let contextMenuConnection = null;
        let contextMenuCategory = null;
        let contextMenuConnectionType = null;
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
        let selectedConnectionType = null;
        
        // Cache de imagens para otimização do Canvas
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
        
        const defaultCableColors = { /* ... (mantido igual) ... */ };
        let cableColors = JSON.parse(JSON.stringify(defaultCableColors));
        let customConnections = [];
        let connectionCategories = {};
        let customCategoryIcons = {};
        let customConnectionIcons = {};
        
        const STORAGE_KEYS = { /* ... (mantido igual) ... */ };
        let categories = {};
        let customDevices = [];
        let defaultCategories = {};
        
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
        
        // Função de Debounce para salvar dados localmente sem travar o navegador
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
            }, 300); // Salva apenas após 300ms de inatividade
        }

        async function loadUserData() {
            const savedIconSize = localStorage.getItem(STORAGE_KEYS.ICON_SIZE);
            if(savedIconSize) iconSize = parseInt(savedIconSize);
            const savedZoom = localStorage.getItem(STORAGE_KEYS.CANVAS_ZOOM);
            if(savedZoom) zoom = parseFloat(savedZoom);
            
            categories = JSON.parse(JSON.stringify(defaultCategories));
            
            // Carregamento em paralelo para ser mais rápido
            const promises = [
                fetch('/api/load_custom_devices').then(r => r.json()).catch(() => ({success: false}))
            ];
            if (currentUser) {
                promises.push(Promise.resolve(localStorage.getItem(STORAGE_KEYS.COMPONENTS(currentUser))));
                promises.push(Promise.resolve(localStorage.getItem(STORAGE_KEYS.CONNECTIONS_DATA(currentUser))));
                promises.push(Promise.resolve(localStorage.getItem(STORAGE_KEYS.SHAPES(currentUser))));
                promises.push(Promise.resolve(localStorage.getItem(STORAGE_KEYS.BACKGROUND(currentUser))));
            }

            const results = await Promise.all(promises);
            
            if (results[0].success) customDevices = results[0].devices;
            
            if (currentUser && results.length > 1) {
                const savedComponents = results[1];
                const savedConnectionsData = results[2];
                const savedShapes = results[3];
                const savedBackground = results[4];
                
                if(savedComponents) components = JSON.parse(savedComponents);
                if(savedConnectionsData) connections = JSON.parse(savedConnectionsData);
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
        
        // OTIMIZAÇÃO NO DESENHO DO CANVAS (Uso do Cache)
        function drawComponents() {
            components.forEach(comp => {
                const isSelected = selectedComponents.includes(comp);
                if(comp.type === 'sensor') drawSensorAnimation(comp.x, comp.y, sensorAnimationTime);
                ctx.save(); ctx.translate(comp.x, comp.y); ctx.rotate((comp.rotation || 0) * Math.PI / 180); ctx.translate(-comp.x, -comp.y);
                const halfSize = iconSize / 2;
                
                if(comp.iconFile) {
                    ctx.drawImage(getCachedImage(`/uploads/icons/${comp.iconFile}`), comp.x-halfSize, comp.y-halfSize, iconSize, iconSize);
                } else if(comp.customImage && comp.customImage.startsWith('data:image')) {
                    ctx.drawImage(getCachedImage(comp.customImage), comp.x-halfSize, comp.y-halfSize, iconSize, iconSize);
                } else if(comp.customImageTemp && comp.customImageTemp.startsWith('data:image')) {
                    ctx.drawImage(getCachedImage(comp.customImageTemp), comp.x-halfSize, comp.y-halfSize, iconSize, iconSize);
                } else {
                    ctx.fillStyle = comp.color || '#005f99'; ctx.beginPath(); ctx.arc(comp.x, comp.y, iconSize/2, 0, 2*Math.PI); ctx.fill(); ctx.fillStyle = '#fff'; ctx.font = `${iconSize/2}px Arial`; const iconToShow = comp.customIconTemp || comp.icon || '📦'; ctx.fillText(iconToShow, comp.x-12, comp.y+8);
                }
                ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = '#005f99'; ctx.font = `${12}px Arial`; ctx.fillText(comp.name, comp.x-30, comp.y - (iconSize/2) - 5);
                if(comp.ip) { ctx.fillStyle = '#6c757d'; ctx.font = `${10}px Arial`; ctx.fillText(comp.ip, comp.x-25, comp.y - (iconSize/2) - 15); }
                if(isSelected) { ctx.strokeStyle = '#005f99'; ctx.lineWidth = 2; ctx.strokeRect(comp.x - halfSize - 4, comp.y - halfSize - 4, iconSize + 8, iconSize + 8); ctx.beginPath(); ctx.arc(comp.x + halfSize + 8, comp.y - halfSize - 8, 6, 0, 2*Math.PI); ctx.fillStyle = '#005f99'; ctx.fill(); ctx.fillStyle = '#fff'; ctx.font = `${10}px Arial`; ctx.fillText('↻', comp.x + halfSize + 5, comp.y - halfSize - 5); }
                if(comp.type === 'camera') drawFieldOfView(comp);
                ctx.restore();
            });
            sensorAnimationTime = (sensorAnimationTime + 0.01) % 1;
        }

        // OTIMIZAÇÃO NO LOGIN (Promessas em paralelo)
        async function doLogin() {
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;
            const response = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
            const data = await response.json();
            
            if (data.success) {
                currentUser = username; userRole = data.role;
                document.getElementById('loginModal').style.display = 'none';
                document.getElementById('toolbar').style.display = 'flex';
                document.getElementById('userInfo').innerHTML = `<span>👤 ${username}</span><span class="user-role">${data.role.toUpperCase()}</span>`;
                
                if (data.role === 'admin' || data.role === 'master') {
                    document.getElementById('adminUsersBtn').style.display = 'inline-block';
                    document.getElementById('adminShapesBtn').style.display = 'inline-block';
                    document.getElementById('adminCategoriesBtn').style.display = 'inline-block';
                    document.getElementById('adminDevicesBtn').style.display = 'inline-block';
                    document.getElementById('adminConnectionsBtn').style.display = 'inline-block';
                    document.getElementById('resetDefaultsBtn').style.display = 'inline-block';
                }
                
                // Carrega TUDO de uma vez só (MUITO MAIS RÁPIDO)
                await Promise.all([
                    loadDefaultConfig(),
                    loadDefaultConnections()
                ]);
                await loadUserData();
                showToast(`Bem-vindo, ${username}!`);
            } else {
                document.getElementById('loginError').style.display = 'block';
            }
        }

        // [As demais funções JS continuam IGUAIS...]
        
    </script>
</body>
</html>
"""
