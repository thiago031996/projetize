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
LOGIN_BG_FOLDER = os.path.join(UPLOAD_FOLDER, 'login_bg')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ICONS_FOLDER, exist_ok=True)
os.makedirs(DEFAULT_ICONS_FOLDER, exist_ok=True)
os.makedirs(BACKGROUNDS_FOLDER, exist_ok=True)
os.makedirs(LOGIN_BG_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

projects = {}
USERS_FILE = os.path.join(UPLOAD_FOLDER, 'users.json')
LOGIN_BG_CONFIG_FILE = os.path.join(UPLOAD_FOLDER, 'login_bg_config.json')

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

def load_login_bg_config():
    if os.path.exists(LOGIN_BG_CONFIG_FILE):
        try:
            with open(LOGIN_BG_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'type': 'matrix', 'filename': None, 'opacity': 0.35}

def save_login_bg_config(config):
    try:
        with open(LOGIN_BG_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar config do fundo de login: {e}")
        return False

def get_dev_image_base64():
    possible_paths = [
        os.path.join(BASE_DIR, 'dev.png'), os.path.join(BASE_DIR, 'dev.jpg'),
        os.path.join(STATIC_FOLDER, 'dev.png'), os.path.join(STATIC_FOLDER, 'dev.jpg'),
    ]
    for path in possible_paths:
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
        except: pass
    return None

def get_default_avatar_svg():
    return '''<svg width="150" height="150" viewBox="0 0 150 150" xmlns="http://www.w3.org/2000/svg"><circle cx="75" cy="75" r="70" fill="#005f99" stroke="#00ccff" stroke-width="3"/><text x="75" y="85" font-family="Arial, sans-serif" font-size="40" font-weight="bold" fill="#ffffff" text-anchor="middle">TS</text><text x="75" y="110" font-family="Arial, sans-serif" font-size="12" fill="#00ccff" text-anchor="middle">Thiago Souza</text></svg>'''

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
        if not session.get('logged_in'): return jsonify({'error': 'Não autorizado'}), 401
        if session.get('role') not in ['admin', 'master']: return jsonify({'error': 'Permissão negada.'}), 403
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
        format_map = {'data:image/png;base64,': '.png', 'data:image/jpeg;base64,': '.jpg', 'data:image/jpg;base64,': '.jpg', 'data:image/gif;base64,': '.gif', 'data:image/webp;base64,': '.webp'}
        ext = '.png'
        for key, value in format_map.items():
            if image_data.startswith(key):
                ext = value; image_data = image_data.replace(key, ''); break
        filename = f"icon_{uuid.uuid4().hex}{ext}"
        try:
            with open(os.path.join(target_folder, filename), 'wb') as f: f.write(base64.b64decode(image_data))
            return filename
        except: return None
    return None

def save_background_image(image_data, name=None):
    if image_data and image_data.startswith('data:image'):
        format_map = {'data:image/png;base64,': '.png', 'data:image/jpeg;base64,': '.jpg', 'data:image/jpg;base64,': '.jpg', 'data:image/gif;base64,': '.gif', 'data:image/webp;base64,': '.webp'}
        ext = '.png'
        for key, value in format_map.items():
            if image_data.startswith(key):
                ext = value; image_data = image_data.replace(key, ''); break
        if not name: name = f"bg_{uuid.uuid4().hex}{ext}"
        elif not name.endswith(ext): name = name + ext
        filename = secure_filename(name)
        try:
            with open(os.path.join(BACKGROUNDS_FOLDER, filename), 'wb') as f: f.write(base64.b64decode(image_data))
            return filename
        except: return None
    return None

DEFAULT_CONNECTIONS_CONFIG = {
    'Cabeadas': {'icon': '🔌', 'connections': [
        {'name': 'CAT5', 'color': '#28a745', 'icon': '🟢', 'type': 'cable', 'speed': '100 Mbps', 'desc': 'Cabo de rede categoria 5', 'iconFile': None},
        {'name': 'CAT5e', 'color': '#17a2b8', 'icon': '🔵', 'type': 'cable', 'speed': '1 Gbps', 'desc': 'Cabo de rede categoria 5e', 'iconFile': None},
        {'name': 'CAT6', 'color': '#ffc107', 'icon': '🟡', 'type': 'cable', 'speed': '10 Gbps', 'desc': 'Cabo de rede categoria 6', 'iconFile': None},
        {'name': 'FIBRA', 'color': '#20c997', 'icon': '🔷', 'type': 'cable', 'speed': '10 Gbps', 'desc': 'Cabo de fibra óptica', 'iconFile': None},
        {'name': 'COAXIAL', 'color': '#e83e8c', 'icon': '🟣', 'type': 'cable', 'speed': '1 Gbps', 'desc': 'Cabo coaxial', 'iconFile': None},
        {'name': 'ALARME', 'color': '#dc3545', 'icon': '🔴', 'type': 'cable', 'speed': 'Baixa', 'desc': 'Cabo para alarme', 'iconFile': None},
        {'name': 'CABO CI', 'color': '#6f42c1', 'icon': '🟣', 'type': 'cable', 'speed': 'Média', 'desc': 'Cabo de controle industrial', 'iconFile': None},
        {'name': 'ENERGIA', 'color': '#fd7e14', 'icon': '🔴', 'type': 'cable', 'speed': '-', 'desc': 'Cabo de energia elétrica', 'iconFile': None}
    ]},
    'Sem Fio': {'icon': '📶', 'connections': [
        {'name': 'Wi-Fi', 'color': '#00aaff', 'icon': '📶', 'type': 'wireless', 'speed': '1 Gbps', 'desc': 'Conexão Wi-Fi', 'animation': 'wave', 'iconFile': None},
        {'name': 'OOK', 'color': '#ff6600', 'icon': '📻', 'type': 'wireless', 'speed': '100 Kbps', 'desc': 'OOK - Rádio Frequência', 'animation': 'packet', 'iconFile': None},
        {'name': 'FSK', 'color': '#aa44ff', 'icon': '📡', 'type': 'wireless', 'speed': '1 Mbps', 'desc': 'FSK - Modulação por Frequência', 'animation': 'packet', 'iconFile': None},
        {'name': 'Bluetooth', 'color': '#0066cc', 'icon': '📱', 'type': 'wireless', 'speed': '24 Mbps', 'desc': 'Bluetooth - Conexão curta distância', 'animation': 'wave', 'iconFile': None},
        {'name': 'ZigBee', 'color': '#00aa66', 'icon': '🔵', 'type': 'wireless', 'speed': '250 Kbps', 'desc': 'ZigBee - IoT/M2M', 'animation': 'packet', 'iconFile': None},
        {'name': 'LoRa', 'color': '#cc8800', 'icon': '📡', 'type': 'wireless', 'speed': '50 Kbps', 'desc': 'LoRa - Longa distância', 'animation': 'packet', 'iconFile': None}
    ]}
}

DEFAULT_CATEGORIES_CONFIG = {
    'Câmeras': {'icon': '🎥', 'devices': [
        {'name': 'Câmera Dome', 'icon': '📹', 'desc': '360° - 4MP - IVS', 'type': 'camera', 'subtype': 'dome', 'color': '#005f99', 'iconFile': None},
        {'name': 'Câmera Bullet', 'icon': '📹', 'desc': 'Longa distância - 8MP', 'type': 'camera', 'subtype': 'bullet', 'color': '#005f99', 'iconFile': None},
        {'name': 'Câmera S', 'icon': '📹', 'desc': 'Motorizada - Auto tracking', 'type': 'camera', 'subtype': 'ptz', 'color': '#005f99', 'iconFile': None},
        {'name': 'Câmera Térmica', 'icon': '📹', 'desc': 'Detecção de calor', 'type': 'camera', 'subtype': 'thermal', 'color': '#005f99', 'iconFile': None},
        {'name': 'Câmera LPR', 'icon': '📹', 'desc': 'Leitura de placas - 1080P', 'type': 'camera', 'subtype': 'lpr', 'color': '#005f99', 'iconFile': None},
        {'name': 'Câmera PR', 'icon': '📹', 'desc': '1080P Full HD', 'type': 'camera', 'subtype': 'pr', 'color': '#005f99', 'iconFile': None}
    ]},
    'Gravadores': {'icon': '💾', 'devices': [
        {'name': 'NVR', 'icon': '💾', 'desc': '32 canais - 4K', 'type': 'nvr', 'color': '#17a2b8', 'iconFile': None},
        {'name': 'DVR', 'icon': '💾', 'desc': '16 canais - HD', 'type': 'dvr', 'color': '#17a2b8', 'iconFile': None}
    ]},
    'Rede': {'icon': '🌐', 'devices': [
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
    ]},
    'Telefonia': {'icon': '📞', 'devices': [
        {'name': 'PABX', 'icon': '📞', 'desc': 'Central telefônica', 'type': 'pbx', 'color': '#6f42c1', 'iconFile': None},
        {'name': 'Telefone IP', 'icon': '📞', 'desc': 'VoIP', 'type': 'telefone_ip', 'color': '#6f42c1', 'iconFile': None},
        {'name': 'Telefone Analógico', 'icon': '☎️', 'desc': 'Linha convencional', 'type': 'telefone_analogico', 'color': '#6f42c1', 'iconFile': None},
        {'name': 'ATA', 'icon': '🔄', 'desc': 'Adaptador Telefônico', 'type': 'ata', 'color': '#6f42c1', 'iconFile': None}
    ]},
    'Sensores': {'icon': '📡', 'devices': [
        {'name': 'Sensor de Movimento', 'icon': '🔴', 'desc': 'Detecção de movimento', 'type': 'sensor', 'subtype': 'movement', 'color': '#005f99', 'iconFile': None},
        {'name': 'Sensor de Porta', 'icon': '🚪', 'desc': 'Abertura de porta', 'type': 'sensor', 'subtype': 'door', 'color': '#005f99', 'iconFile': None},
        {'name': 'Sensor de Fumaça', 'icon': '💨', 'desc': 'Detecção de fumaça', 'type': 'sensor', 'subtype': 'smoke', 'color': '#005f99', 'iconFile': None},
        {'name': 'Sensor de Temperatura', 'icon': '🌡️', 'desc': 'Controle térmico', 'type': 'sensor', 'subtype': 'temperature', 'color': '#005f99', 'iconFile': None},
        {'name': 'Sensor de Umidade', 'icon': '💧', 'desc': 'Controle de umidade', 'type': 'sensor', 'subtype': 'humidity', 'color': '#005f99', 'iconFile': None}
    ]},
    'Controle de Acesso': {'icon': '🔑', 'devices': [
        {'name': 'Cancela', 'icon': '🚗', 'desc': 'Controle de acesso', 'type': 'cancela', 'color': '#28a745', 'iconFile': None},
        {'name': 'Controle de Acesso', 'icon': '🔑', 'desc': 'Biometria/Cartão', 'type': 'controle_acesso', 'color': '#28a745', 'iconFile': None},
        {'name': 'Catraca', 'icon': '🚪', 'desc': 'Controle de fluxo', 'type': 'catraca', 'color': '#28a745', 'iconFile': None},
        {'name': 'Vídeo Porteiro', 'icon': '📹', 'desc': 'IP/analógico', 'type': 'video_porteiro', 'color': '#28a745', 'iconFile': None}
    ]},
    'Segurança': {'icon': '🚨', 'devices': [
        {'name': 'Central Alarme', 'icon': '🚨', 'desc': 'Sensor perimetral', 'type': 'alarme', 'color': '#dc3545', 'iconFile': None},
        {'name': 'Central Incêndio', 'icon': '🔥', 'desc': 'Detecção', 'type': 'central_incendio', 'color': '#dc3545', 'iconFile': None}
    ]},
    'Energia': {'icon': '⚡', 'devices': [
        {'name': 'Nobreak', 'icon': '🔋', 'desc': 'Estabilizador', 'type': 'nobreak', 'color': '#fd7e14', 'iconFile': None},
        {'name': 'Fonte Alimentação', 'icon': '⚡', 'desc': '12V/24V', 'type': 'fonte_alimentacao', 'color': '#fd7e14', 'iconFile': None},
        {'name': 'Eletrificador', 'icon': '⚡', 'desc': 'Cerca elétrica', 'type': 'eletrificador', 'color': '#fd7e14', 'iconFile': None},
        {'name': 'Energia', 'icon': '🔌', 'desc': 'Rede elétrica', 'type': 'energia', 'color': '#fd7e14', 'iconFile': None}
    ]},
    'Automação': {'icon': '⚙️', 'devices': [
        {'name': 'Motor', 'icon': '⚙️', 'desc': 'Automação', 'type': 'motor', 'color': '#6c757d', 'iconFile': None}
    ]}
}

DEFAULT_CONNECTIONS_FILE = os.path.join(UPLOAD_FOLDER, 'default_connections.json')
DEFAULT_CONFIG_FILE = os.path.join(UPLOAD_FOLDER, 'default_config.json')
CUSTOM_DEVICES_FILE = os.path.join(UPLOAD_FOLDER, 'custom_devices.json')

def load_json_file(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return json.loads(json.dumps(default_value))

def save_json_file(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except: return False

@app.route('/api/upload_icon', methods=['POST'])
@login_required
def upload_icon():
    data = request.json
    image_data = data.get('image', '')
    is_default = data.get('is_default', False)
    target_type = data.get('type', 'equipment')
    if not image_data or not image_data.startswith('data:image'): return jsonify({'success': False, 'error': 'Imagem inválida'}), 400
    target_folder = DEFAULT_ICONS_FOLDER if is_default else ICONS_FOLDER
    format_map = {'data:image/png;base64,': '.png', 'data:image/jpeg;base64,': '.jpg', 'data:image/jpg;base64,': '.jpg', 'data:image/gif;base64,': '.gif', 'data:image/webp;base64,': '.webp'}
    ext = '.png'
    for key, value in format_map.items():
        if image_data.startswith(key): ext = value; image_data = image_data.replace(key, ''); break
    else: image_data = image_data.split(',')[1] if ',' in image_data else image_data
    prefix = {'equipment': 'eqp', 'category': 'cat', 'connection': 'con'}.get(target_type, 'ico')
    filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    try:
        with open(os.path.join(target_folder, filename), 'wb') as f: f.write(base64.b64decode(image_data))
        return jsonify({'success': True, 'filename': filename, 'type': target_type})
    except Exception as e: return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload_dev_image', methods=['POST'])
@admin_required
def upload_dev_image():
    data = request.json
    image_data = data.get('image', '')
    if not image_data or not image_data.startswith('data:image'): return jsonify({'success': False, 'error': 'Imagem inválida'}), 400
    format_map = {'data:image/png;base64,': '.png', 'data:image/jpeg;base64,': '.jpg', 'data:image/jpg;base64,': '.jpg', 'data:image/gif;base64,': '.gif', 'data:image/webp;base64,': '.webp'}
    ext = '.png'
    for key, value in format_map.items():
        if image_data.startswith(key): ext = value; image_data = image_data.replace(key, ''); break
    else: image_data = image_data.split(',')[1] if ',' in image_data else image_data
    filename = f"dev{ext}"
    filepath = os.path.join(BASE_DIR, filename)
    for old_ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        old_path = os.path.join(BASE_DIR, f"dev{old_ext}")
        if os.path.exists(old_path) and old_path != filepath:
            try: os.remove(old_path)
            except: pass
    try:
        with open(filepath, 'wb') as f: f.write(base64.b64decode(image_data))
        return jsonify({'success': True, 'url': f'/static/{filename}'})
    except Exception as e: return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload_login_bg', methods=['POST'])
@admin_required
def upload_login_bg():
    data = request.json
    media_data = data.get('media', '')
    if not media_data: return jsonify({'success': False, 'error': 'Mídia inválida'}), 400
    if media_data.startswith('data:'):
        try:
            header, encoded = media_data.split(',', 1)
            mime = header.split(';')[0].replace('data:', '')
            ext_map = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/jpg': '.jpg', 'image/gif': '.gif', 'image/webp': '.webp', 'image/svg+xml': '.svg', 'video/mp4': '.mp4', 'video/webm': '.webm', 'video/ogg': '.ogv'}
            ext = ext_map.get(mime, '.bin'); file_bytes = base64.b64decode(encoded)
        except Exception as e: return jsonify({'success': False, 'error': f'Falha no decode: {e}'}), 400
    else: return jsonify({'success': False, 'error': 'Formato inválido'}), 400
    old_config = load_login_bg_config()
    if old_config.get('filename'):
        old_path = os.path.join(LOGIN_BG_FOLDER, old_config['filename'])
        if os.path.exists(old_path):
            try: os.remove(old_path)
            except: pass
    filename = f"login_bg_{uuid.uuid4().hex}{ext}"
    try:
        with open(os.path.join(LOGIN_BG_FOLDER, filename), 'wb') as f: f.write(file_bytes)
    except Exception as e: return jsonify({'success': False, 'error': str(e)}), 500
    actual_type = 'video' if mime.startswith('video/') else 'image'
    config = {'type': actual_type, 'filename': filename, 'opacity': data.get('opacity', old_config.get('opacity', 0.35)), 'mime': mime}
    save_login_bg_config(config)
    return jsonify({'success': True, 'filename': filename, 'type': actual_type, 'config': config})

@app.route('/api/login_bg_config', methods=['GET'])
def get_login_bg_config_route(): return jsonify({'success': True, 'config': load_login_bg_config()})

@app.route('/api/login_bg_config', methods=['POST'])
@admin_required
def set_login_bg_config_route():
    data = request.json
    config = load_login_bg_config()
    if 'opacity' in data:
        try: config['opacity'] = max(0.05, min(1.0, float(data['opacity'])))
        except: pass
    if 'type' in data and data['type'] in ['matrix', 'image', 'video']:
        if data['type'] == 'matrix':
            if config.get('filename'):
                old_path = os.path.join(LOGIN_BG_FOLDER, config['filename'])
                if os.path.exists(old_path):
                    try: os.remove(old_path)
                    except: pass
            config['filename'] = None; config['mime'] = None
        config['type'] = data['type']
    save_login_bg_config(config)
    return jsonify({'success': True, 'config': config})

@app.route('/api/reset_login_bg', methods=['POST'])
@admin_required
def reset_login_bg():
    config = load_login_bg_config()
    if config.get('filename'):
        old_path = os.path.join(LOGIN_BG_FOLDER, config['filename'])
        if os.path.exists(old_path):
            try: os.remove(old_path)
            except: pass
    new_config = {'type': 'matrix', 'filename': None, 'opacity': 0.35}
    save_login_bg_config(new_config)
    return jsonify({'success': True, 'config': new_config})

@app.route('/uploads/login_bg/<filename>')
def serve_login_bg(filename): return send_from_directory(LOGIN_BG_FOLDER, filename)

@app.route('/api/save_global_categories', methods=['POST'])
@admin_required
def save_global_categories():
    data = request.json
    if data.get('categories'): save_json_file(DEFAULT_CONFIG_FILE, data['categories']); return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

@app.route('/api/save_global_connections', methods=['POST'])
@admin_required
def save_global_connections():
    data = request.json
    if data.get('connections'): save_json_file(DEFAULT_CONNECTIONS_FILE, data['connections']); return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

@app.route('/api/save_global_custom_devices', methods=['POST'])
@admin_required
def save_global_custom_devices():
    data = request.json
    if data.get('devices') is not None: save_json_file(CUSTOM_DEVICES_FILE, data['devices']); return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

@app.route('/api/load_custom_devices', methods=['GET'])
def get_custom_devices(): return jsonify({'success': True, 'devices': load_json_file(CUSTOM_DEVICES_FILE, [])})

@app.route('/api/upload_background', methods=['POST'])
@login_required
def upload_background():
    data = request.json
    image_data = data.get('image', ''); name = data.get('name', None)
    if not image_data or not image_data.startswith('data:image'): return jsonify({'success': False, 'error': 'Imagem inválida'}), 400
    filename = save_background_image(image_data, name)
    if filename: return jsonify({'success': True, 'filename': filename, 'url': f'/uploads/backgrounds/{filename}'})
    return jsonify({'success': False, 'error': 'Erro'}), 500

@app.route('/uploads/icons/<filename>')
def serve_icon(filename): return send_from_directory(ICONS_FOLDER, filename)

@app.route('/uploads/default_icons/<filename>')
def serve_default_icon(filename): return send_from_directory(DEFAULT_ICONS_FOLDER, filename)

@app.route('/uploads/backgrounds/<filename>')
def serve_background(filename): return send_from_directory(BACKGROUNDS_FOLDER, filename)

@app.route('/dev.png')
def serve_dev_image(): return send_from_directory(BASE_DIR, 'dev.png')

@app.route('/static/<path:filename>')
def serve_static(filename): return send_from_directory(STATIC_FOLDER, filename)

@app.route('/api/default_config', methods=['GET'])
def get_default_config(): return jsonify({'success': True, 'config': load_json_file(DEFAULT_CONFIG_FILE, DEFAULT_CATEGORIES_CONFIG)})

@app.route('/api/default_connections', methods=['GET'])
def get_default_connections(): return jsonify({'success': True, 'config': load_json_file(DEFAULT_CONNECTIONS_FILE, DEFAULT_CONNECTIONS_CONFIG)})

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
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username'); password = data.get('password')
    if username in users and users[username]['password'] == hash_password(password):
        session['logged_in'] = True; session['username'] = username; session['role'] = users[username]['role']
        return jsonify({'success': True, 'role': users[username]['role']})
    return jsonify({'success': False, 'error': 'Credenciais inválidas'}), 401

@app.route('/api/logout', methods=['POST'])
def logout(): session.clear(); return jsonify({'success': True})

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    if session.get('role') not in ['admin', 'master']: return jsonify({'error': 'Permissão negada'}), 403
    safe_users = {}
    for username, user_data in users.items():
        safe_users[username] = {'role': user_data['role'], 'created_at': user_data.get('created_at', '')}
    return jsonify(safe_users)

@app.route('/api/users', methods=['POST'])
@login_required
def add_user():
    if session.get('role') not in ['admin', 'master']: return jsonify({'error': 'Permissão negada'}), 403
    data = request.json
    username = data.get('username'); password = data.get('password'); role = data.get('role', 'viewer')
    if not username or not password: return jsonify({'error': 'Usuário e senha são obrigatórios'}), 400
    if username in users: return jsonify({'error': 'Usuário já existe'}), 400
    users[username] = {'password': hash_password(password), 'role': role, 'created_at': datetime.now().isoformat()}
    save_users(users)
    return jsonify({'success': True})

@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
def delete_user(username):
    if session.get('role') not in ['admin', 'master']: return jsonify({'error': 'Permissão negada'}), 403
    if username == 'thiago03': return jsonify({'error': 'Não é possível excluir master'}), 400
    if username in users: del users[username]; save_users(users); return jsonify({'success': True})
    return jsonify({'error': 'Usuário não encontrado'}), 404

# ==================== HTML_TEMPLATE ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover">
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
            --palette-width: 280px; --properties-width: 340px;
        }
        @media (max-width: 1024px) { :root { --palette-width: 240px; --properties-width: 280px; } }
        @media (max-width: 768px) { :root { --palette-width: 220px; --properties-width: 260px; } body { overflow: auto; position: relative; height: auto; min-height: 100vh; } }
        @media (max-width: 576px) { :root { --palette-width: 180px; --properties-width: 240px; } }
        
        .rgb-line { position: fixed; top: 0; left: 0; width: 100%; height: 3px; background: linear-gradient(90deg, #005f99, #0099cc, #00ccff, #005f99); background-size: 300% 100%; animation: rgbMove 3s linear infinite; z-index: 10000; }
        @keyframes rgbMove { 0% { background-position: 0% 0%; } 100% { background-position: 300% 100%; } }
        
        /* ==================== INTRO SCREEN REDESIGNADO (CORPORATIVO) ==================== */
        .intro-screen { 
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: radial-gradient(ellipse at top, #0a1a2e 0%, #050d1a 60%, #02060d 100%);
            display: flex; justify-content: center; align-items: center; 
            z-index: 25000; overflow-y: auto; padding: 20px;
        }
        .intro-grid-pattern {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-image: 
                linear-gradient(rgba(56, 189, 248, 0.06) 1px, transparent 1px),
                linear-gradient(90deg, rgba(56, 189, 248, 0.06) 1px, transparent 1px);
            background-size: 60px 60px;
            z-index: 0; pointer-events: none;
            mask-image: radial-gradient(ellipse at center, rgba(0,0,0,1), transparent 80%);
            -webkit-mask-image: radial-gradient(ellipse at center, rgba(0,0,0,1), transparent 80%);
        }
        .intro-glow-1, .intro-glow-2 {
            position: fixed; border-radius: 50%; filter: blur(100px);
            z-index: 0; pointer-events: none; opacity: 0.5;
        }
        .intro-glow-1 { width: 500px; height: 500px; background: #06b6d4; top: -150px; left: -100px; animation: glowFloat1 20s ease-in-out infinite; }
        .intro-glow-2 { width: 400px; height: 400px; background: #3b82f6; bottom: -150px; right: -100px; animation: glowFloat2 25s ease-in-out infinite; }
        @keyframes glowFloat1 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(100px, 80px) scale(1.15); } }
        @keyframes glowFloat2 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-80px, -60px) scale(0.9); } }
        
        .intro-container {
            position: relative; z-index: 2; width: 100%; max-width: 1180px;
            background: rgba(10, 20, 36, 0.55);
            backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 24px;
            padding: 40px 40px 30px;
            box-shadow: 0 30px 80px rgba(0,0,0,0.6), 0 0 120px rgba(6,182,212,0.08), inset 0 1px 0 rgba(255,255,255,0.05);
            max-height: 94vh; overflow-y: auto;
            animation: introFadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes introFadeIn { from { opacity: 0; transform: translateY(20px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
        @media (max-width: 768px) { .intro-container { padding: 24px 20px; } }
        
        .intro-brand-header { display: flex; align-items: center; gap: 14px; margin-bottom: 30px; }
        .intro-brand-logo {
            width: 52px; height: 52px; border-radius: 14px;
            background: linear-gradient(135deg, #06b6d4, #3b82f6);
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 8px 24px rgba(6, 182, 212, 0.4);
        }
        .intro-brand-title { font-size: 24px; font-weight: 800; letter-spacing: 2px; color: #ffffff; }
        .intro-brand-title span { color: #38bdf8; }
        .intro-brand-subtitle { font-size: 10px; color: #64748b; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 600; margin-top: 2px; }
        
        .intro-hero { display: grid; grid-template-columns: 1.2fr 1fr; gap: 40px; align-items: center; margin-bottom: 40px; }
        @media (max-width: 860px) { .intro-hero { grid-template-columns: 1fr; gap: 24px; } }
        
        .intro-hero-badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 5px 12px; border-radius: 20px;
            background: rgba(6, 182, 212, 0.1); border: 1px solid rgba(6, 182, 212, 0.3);
            font-size: 10px; font-weight: 700; color: #22d3ee; letter-spacing: 1px; text-transform: uppercase;
            margin-bottom: 16px;
        }
        .intro-hero-badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #22d3ee; box-shadow: 0 0 8px #22d3ee; animation: badgePulse 2s infinite; }
        @keyframes badgePulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
        
        .intro-hero-title {
            font-size: 38px; font-weight: 800; line-height: 1.15; color: #ffffff; margin-bottom: 16px;
            letter-spacing: -0.5px;
        }
        @media (max-width: 768px) { .intro-hero-title { font-size: 28px; } }
        .intro-hero-title .highlight {
            background: linear-gradient(135deg, #22d3ee, #3b82f6);
            -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
        }
        .intro-hero-desc { font-size: 14px; color: #94a3b8; line-height: 1.7; margin-bottom: 28px; max-width: 480px; }
        @media (max-width: 768px) { .intro-hero-desc { font-size: 13px; } }
        
        .intro-cta-group { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
        .intro-cta-primary {
            padding: 14px 32px; border-radius: 12px; border: none;
            background: linear-gradient(135deg, #06b6d4, #3b82f6);
            color: #ffffff; font-size: 14px; font-weight: 700; letter-spacing: 0.5px;
            cursor: pointer; display: inline-flex; align-items: center; gap: 8px;
            box-shadow: 0 10px 30px rgba(6, 182, 212, 0.4);
            transition: all 0.3s;
        }
        .intro-cta-primary:hover { transform: translateY(-2px); box-shadow: 0 14px 40px rgba(6, 182, 212, 0.55); }
        .intro-cta-primary svg { transition: transform 0.3s; }
        .intro-cta-primary:hover svg { transform: translateX(4px); }
        
        .intro-hero-visual { position: relative; }
        .intro-hero-visual svg { width: 100%; height: auto; filter: drop-shadow(0 20px 40px rgba(0,0,0,0.4)); }
        
        .intro-features-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 30px; }
        @media (max-width: 860px) { .intro-features-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 480px) { .intro-features-grid { grid-template-columns: 1fr; } }
        
        .intro-feature-card {
            padding: 18px; border-radius: 14px;
            background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(56, 189, 248, 0.12);
            transition: all 0.3s; cursor: default;
        }
        .intro-feature-card:hover { border-color: rgba(56, 189, 248, 0.4); background: rgba(15, 23, 42, 0.9); transform: translateY(-3px); }
        .intro-feature-icon {
            width: 36px; height: 36px; border-radius: 10px;
            background: linear-gradient(135deg, rgba(6,182,212,0.2), rgba(59,130,246,0.2));
            border: 1px solid rgba(56, 189, 248, 0.25);
            display: flex; align-items: center; justify-content: center;
            color: #38bdf8; margin-bottom: 12px;
        }
        .intro-feature-title { font-size: 12px; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
        .intro-feature-desc { font-size: 10px; color: #64748b; line-height: 1.5; }
        
        .intro-footer-bar {
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
            padding-top: 20px; border-top: 1px solid rgba(56, 189, 248, 0.1);
            font-size: 11px; color: #475569;
        }
        .intro-footer-bar strong { color: #38bdf8; }
        .intro-dev-badge-small {
            display: flex; align-items: center; gap: 10px;
        }
        .intro-dev-avatar-small {
            width: 32px; height: 32px; border-radius: 50%;
            border: 2px solid rgba(56, 189, 248, 0.4);
            overflow: hidden; background: #0f172a;
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0;
        }
        .intro-dev-avatar-small img { width: 100%; height: 100%; object-fit: cover; }
        /* ============================================================================ */
        
        /* ==================== TELA DE LOGIN (PERFEITA - MANTIDA) ==================== */
        .login-modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #060d1a; display: none; justify-content: center; align-items: center; z-index: 20000; overflow: hidden; padding: 20px; }
        #loginBgMedia { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; opacity: 0.35; pointer-events: none; display: none; }
        #loginBgVideo { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; opacity: 0.35; pointer-events: none; display: none; }
        .login-overlay-gradient { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; background: radial-gradient(ellipse at top left, rgba(0,153,204,0.12), transparent 50%), radial-gradient(ellipse at bottom right, rgba(0,95,153,0.18), transparent 50%), linear-gradient(180deg, rgba(6,13,26,0.85), rgba(6,13,26,0.95)); pointer-events: none; }
        .matrix-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden; font-family: monospace; color: #ffffff; z-index: 0; opacity: 0.3; pointer-events: none; }
        .matrix-column { position: absolute; top: -100%; animation: matrixFall linear infinite; white-space: pre; font-size: 16px; line-height: 1.2; opacity: 0.8; text-shadow: 0 0 8px #ffffff; color: #ffffff; font-weight: bold; }
        @keyframes matrixFall { 0% { top: -100%; } 100% { top: 100%; } }
        
        .login-bg-toggle { position: absolute; top: 20px; right: 20px; z-index: 5; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 10px; width: 42px; height: 42px; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.3s; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
        .login-bg-toggle:hover { background: rgba(56, 189, 248, 0.15); transform: translateY(-2px); color: #7dd3fc; box-shadow: 0 12px 32px rgba(56,189,248,0.25); }
        
        .login-split { position: relative; z-index: 2; width: 100%; max-width: 980px; display: grid; grid-template-columns: 1fr 1fr; gap: 0; background: rgba(10, 18, 32, 0.65); backdrop-filter: blur(28px); -webkit-backdrop-filter: blur(28px); border: 1px solid rgba(56, 189, 248, 0.18); border-radius: 20px; overflow: hidden; box-shadow: 0 32px 80px rgba(0,0,0,0.75), 0 0 100px rgba(0,153,204,0.08), inset 0 1px 0 rgba(255,255,255,0.06); animation: loginFadeIn 0.7s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes loginFadeIn { from { opacity: 0; transform: translateY(24px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
        @media (max-width: 820px) { .login-split { grid-template-columns: 1fr; max-width: 420px; } .login-brand-panel { display: none; } }
        
        .login-brand-panel { padding: 48px 40px; display: flex; flex-direction: column; justify-content: center; background: linear-gradient(160deg, rgba(0, 95, 153, 0.20), rgba(0, 40, 80, 0.30)); border-right: 1px solid rgba(56, 189, 248, 0.12); position: relative; overflow: hidden; }
        .login-brand-panel::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(56,189,248,0.10) 0%, transparent 60%); animation: brandGlow 18s linear infinite; }
        @keyframes brandGlow { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .login-brand-logo { width: 84px; height: 84px; margin-bottom: 24px; position: relative; z-index: 1; filter: drop-shadow(0 0 24px rgba(0, 204, 255, 0.5)); }
        .login-brand-name { font-size: 32px; font-weight: 800; letter-spacing: 3px; color: #ffffff; margin-bottom: 8px; position: relative; z-index: 1; }
        .login-brand-tagline { font-size: 12px; color: #7dd3fc; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 600; position: relative; z-index: 1; }
        .login-brand-divider { width: 60px; height: 2px; background: linear-gradient(90deg, #00ccff, transparent); margin: 28px 0; position: relative; z-index: 1; }
        .login-brand-features { display: flex; flex-direction: column; gap: 14px; position: relative; z-index: 1; }
        .feature-item { display: flex; align-items: center; gap: 12px; color: #b8c9dd; font-size: 13px; font-weight: 500; }
        .feature-item svg { color: #38bdf8; flex-shrink: 0; }
        
        .login-form-panel { padding: 48px 44px; display: flex; flex-direction: column; justify-content: center; background: rgba(6, 13, 26, 0.4); }
        .login-form-header { text-align: center; margin-bottom: 32px; }
        .login-avatar { width: 78px; height: 78px; border-radius: 50%; margin: 0 auto 18px; overflow: hidden; border: 2px solid rgba(56, 189, 248, 0.4); box-shadow: 0 0 0 6px rgba(56, 189, 248, 0.06), 0 8px 24px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; background: #0f172a; position: relative; }
        .login-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .login-form-title { font-size: 22px; font-weight: 700; color: #ffffff; margin-bottom: 6px; letter-spacing: 0.3px; }
        .login-form-subtitle { font-size: 12px; color: #64748b; letter-spacing: 0.5px; }
        .login-form-body { display: flex; flex-direction: column; gap: 16px; }
        .login-input-group { display: flex; flex-direction: column; gap: 7px; }
        .login-input-group label { font-size: 11px; color: #7dd3fc; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
        .login-input-wrapper { position: relative; }
        .login-input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #475569; pointer-events: none; transition: color 0.2s; }
        .login-input-field { width: 100%; padding: 13px 14px 13px 44px; background: rgba(15, 23, 42, 0.75); border: 1.5px solid rgba(56, 189, 248, 0.15); border-radius: 10px; color: #f1f5f9; font-size: 14px; font-weight: 500; transition: all 0.25s ease; }
        .login-input-field:focus { outline: none; border-color: #38bdf8; background: rgba(15, 23, 42, 0.95); box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.12), 0 0 24px rgba(56, 189, 248, 0.15); }
        .login-input-wrapper:focus-within .login-input-icon { color: #38bdf8; }
        .login-input-field::placeholder { color: #475569; font-weight: 400; }
        .login-submit-btn { width: 100%; padding: 14px; margin-top: 8px; background: linear-gradient(135deg, #0284c7, #0369a1); border: none; border-radius: 10px; color: #ffffff; font-size: 14px; font-weight: 700; letter-spacing: 0.8px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.25s; box-shadow: 0 8px 24px rgba(2, 132, 199, 0.35); }
        .login-submit-btn:hover { transform: translateY(-2px); box-shadow: 0 12px 32px rgba(2, 132, 199, 0.5); background: linear-gradient(135deg, #0ea5e9, #0284c7); }
        .login-submit-btn:disabled { opacity: 0.55; cursor: not-allowed; transform: none; }
        .login-submit-btn .spinner { width: 15px; height: 15px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .login-error { color: #f87171; font-size: 12px; padding: 10px 14px; background: rgba(248, 113, 113, 0.08); border: 1px solid rgba(248,113,113,0.25); border-radius: 8px; display: none; text-align: center; font-weight: 500; }
        .login-form-footer { margin-top: 28px; padding-top: 20px; border-top: 1px solid rgba(56, 189, 248, 0.08); text-align: center; font-size: 11px; color: #475569; line-height: 1.8; }
        .login-form-footer strong { color: #7dd3fc; font-weight: 700; }
        /* ===================================================================== */
        
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
        #canvas { background: transparent; cursor: crosshair; display: block; margin: 20px auto; transform-origin: 0 0; }
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
        
        .connection-animation { position: absolute; pointer-events: none; z-index: 1000; }
        .connection-wave { position: absolute; border-radius: 50%; animation: signalWave 1.5s ease-out infinite; }
        .data-packet { position: absolute; width: 8px; height: 8px; border-radius: 2px; animation: dataPacket 1s linear infinite; }
        @keyframes signalWave { 0% { transform: scale(0.8); opacity: 0; } 50% { transform: scale(1.2); opacity: 0.8; } 100% { transform: scale(1.5); opacity: 0; } }
        @keyframes dataPacket { 0% { transform: translateX(-20px) scale(0.5); opacity: 0; } 20% { opacity: 1; } 80% { opacity: 1; } 100% { transform: translateX(20px) scale(1); opacity: 0; } }
        
        .zoom-controls { display: inline-flex; align-items: center; gap: 5px; margin-left: 10px; }
        .zoom-controls button { background: var(--button-secondary); border: 1px solid var(--border-color); padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; }
        .zoom-controls button:hover { background: var(--button-secondary-hover); }
        .zoom-controls span { font-size: 12px; color: var(--text-primary); }
        @media (max-width: 576px) { .zoom-controls span { display: none; } }
        
        .mobile-menu-toggle { display: none; position: fixed; bottom: 20px; left: 20px; background: var(--button-primary); color: white; border: none; border-radius: 50%; width: 50px; height: 50px; font-size: 24px; cursor: pointer; z-index: 200; box-shadow: 0 2px 10px rgba(0,0,0,0.3); }
        @media (max-width: 768px) { .mobile-menu-toggle { display: flex; align-items: center; justify-content: center; } }
        .mobile-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 199; display: none; }
        
        .delete-shape-btn { position: fixed; background: #dc3545; color: white; border: none; border-radius: 20px; padding: 8px 16px; font-size: 12px; cursor: pointer; z-index: 250; display: none; box-shadow: 0 2px 10px rgba(0,0,0,0.3); }
        
        .dynamic-background { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; object-fit: cover; pointer-events: none; opacity: 0.3; display: none; }
        
        .loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 26, 46, 0.95); z-index: 30000; display: none; flex-direction: column; justify-content: center; align-items: center; color: white; }
        .loading-spinner { border: 8px solid #f3f3f3; border-top: 8px solid #00ccff; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; margin-bottom: 20px; }
        .loading-text { font-size: 18px; font-weight: bold; animation: pulseText 1.5s infinite; }
        @keyframes pulseText { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
        
        /* ==================== 3D SIMULATOR STYLES ==================== */
        #sim3d-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 15000; background: #080b13; display: none; overflow: hidden; }
        #sim3d-overlay.active { display: block; }
        #sim3d-container { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }
        #sim3d-container canvas { cursor: grab; }
        #sim3d-container canvas:active { cursor: grabbing; }
        
        .sim3d-glass { background: rgba(15, 23, 42, 0.88); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(56, 189, 248, 0.25); box-shadow: 0 20px 50px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.1); }
        .sim3d-header { position: absolute; top: 0; left: 0; width: 100%; padding: 12px 16px; z-index: 20; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; pointer-events: none; }
        .sim3d-header > * { pointer-events: auto; }
        .sim3d-brand { display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-radius: 14px; color: #e2e8f0; }
        .sim3d-brand-icon { width: 38px; height: 38px; border-radius: 10px; background: linear-gradient(135deg, #06b6d4, #3b82f6, #6366f1); display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; box-shadow: 0 6px 20px rgba(6, 182, 212, 0.4); }
        .sim3d-brand h1 { font-size: 14px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; background: linear-gradient(90deg, #67e8f9, #bae6fd, #c7d2fe); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
        .sim3d-brand p { font-size: 10px; color: #94a3b8; display: flex; align-items: center; gap: 5px; }
        .sim3d-brand p::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #34d399; box-shadow: 0 0 8px #34d399; }
        
        .sim3d-btn { padding: 8px 14px; border-radius: 10px; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; border: 1px solid rgba(56, 189, 248, 0.4); color: #67e8f9; background: rgba(15, 23, 42, 0.6); transition: all 0.2s; }
        .sim3d-btn:hover { color: white; background: rgba(6, 182, 212, 0.3); border-color: #22d3ee; }
        .sim3d-btn-primary { background: linear-gradient(90deg, #059669, #0d9488); color: white; border: none; box-shadow: 0 6px 20px rgba(5, 150, 105, 0.4); }
        .sim3d-btn-primary:hover { background: linear-gradient(90deg, #10b981, #14b8a6); }
        .sim3d-btn-close { width: 36px; height: 36px; border-radius: 10px; border: 1px solid rgba(239, 68, 68, 0.4); background: rgba(15, 23, 42, 0.6); color: #f87171; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 16px; transition: all 0.2s; }
        .sim3d-btn-close:hover { background: rgba(239, 68, 68, 0.2); color: #fecaca; }
        
        .sim3d-drawer { position: absolute; left: 16px; top: 80px; bottom: 16px; width: 340px; max-width: calc(100vw - 32px); z-index: 15; border-radius: 16px; padding: 14px; display: flex; flex-direction: column; transition: transform 0.3s ease; }
        .sim3d-drawer.closed { transform: translateX(calc(-100% - 30px)); }
        .sim3d-drawer-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid #1e293b; }
        .sim3d-drawer-header h2 { font-size: 11px; font-weight: 800; color: #67e8f9; text-transform: uppercase; letter-spacing: 1px; }
        .sim3d-drawer-close { width: 26px; height: 26px; border-radius: 7px; border: none; background: #1e293b; color: #cbd5e1; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 12px; }
        .sim3d-drawer-close:hover { background: #334155; color: white; }
        .sim3d-drawer-hint { font-size: 10px; color: #64748b; padding: 8px 0; line-height: 1.5; }
        .sim3d-drawer-hint strong { color: #22d3ee; }
        .sim3d-drawer-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
        .sim3d-drawer-list::-webkit-scrollbar { width: 4px; }
        .sim3d-drawer-list::-webkit-scrollbar-thumb { background: rgba(56, 189, 248, 0.5); border-radius: 4px; }
        
        .sim3d-eq-group { margin-top: 10px; }
        .sim3d-eq-group-title { font-size: 10px; font-weight: 800; color: #22d3ee; text-transform: uppercase; letter-spacing: 1px; padding: 6px 0 4px; }
        
        .sim3d-eq-item { padding: 10px; border-radius: 10px; border: 1px solid #1e293b; background: rgba(15, 23, 42, 0.5); display: flex; justify-content: space-between; align-items: center; gap: 8px; transition: all 0.2s; cursor: grab; user-select: none; }
        .sim3d-eq-item:active { cursor: grabbing; }
        .sim3d-eq-item:hover { border-color: rgba(56, 189, 248, 0.6); background: rgba(30, 41, 59, 0.7); transform: translateX(2px); }
        .sim3d-eq-item.dragging { opacity: 0.4; }
        .sim3d-eq-item.mounted { border-color: rgba(6, 182, 212, 0.6); background: rgba(15, 23, 42, 0.95); box-shadow: 0 4px 15px rgba(6, 182, 212, 0.2); }
        .sim3d-eq-info { flex: 1; min-width: 0; }
        .sim3d-eq-name { font-size: 11px; font-weight: 700; color: #f1f5f9; display: flex; align-items: center; gap: 5px; }
        .sim3d-eq-unit { font-size: 9px; padding: 1px 5px; border-radius: 4px; background: #083344; color: #67e8f9; border: 1px solid #0e7490; font-family: monospace; font-weight: 700; }
        .sim3d-eq-desc { font-size: 9px; color: #64748b; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .sim3d-eq-actions { display: flex; gap: 3px; flex-shrink: 0; }
        .sim3d-eq-btn { padding: 4px 8px; border-radius: 6px; border: none; font-size: 10px; font-weight: 700; cursor: pointer; transition: all 0.2s; background: #06b6d4; color: white; }
        .sim3d-eq-btn:hover { background: #22d3ee; }
        
        /* Painel de propriedades 3D */
        .sim3d-properties { position: absolute; right: 16px; top: 80px; bottom: 16px; width: 340px; max-width: calc(100vw - 32px); z-index: 16; border-radius: 16px; padding: 0; display: flex; flex-direction: column; transform: translateX(calc(100% + 30px)); transition: transform 0.3s ease; overflow: hidden; }
        .sim3d-properties.open { transform: translateX(0); }
        .sim3d-prop-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid #1e293b; background: rgba(2, 6, 23, 0.5); }
        .sim3d-prop-title { font-size: 13px; font-weight: 800; color: #f1f5f9; display: flex; align-items: center; gap: 8px; }
        .sim3d-prop-title::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: #22d3ee; box-shadow: 0 0 8px #22d3ee; }
        .sim3d-prop-close { width: 26px; height: 26px; border-radius: 7px; border: none; background: #1e293b; color: #cbd5e1; cursor: pointer; font-size: 12px; }
        .sim3d-prop-close:hover { background: #ef4444; color: white; }
        .sim3d-prop-body { flex: 1; overflow-y: auto; padding: 14px 16px; }
        .sim3d-prop-body::-webkit-scrollbar { width: 4px; }
        .sim3d-prop-body::-webkit-scrollbar-thumb { background: rgba(56, 189, 248, 0.5); border-radius: 4px; }
        .sim3d-prop-section { margin-bottom: 14px; }
        .sim3d-prop-label { font-size: 10px; font-weight: 800; color: #22d3ee; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; display: flex; align-items: center; justify-content: space-between; }
        .sim3d-prop-input { width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid #334155; background: rgba(2, 6, 23, 0.6); color: #f1f5f9; font-size: 11px; transition: all 0.2s; }
        .sim3d-prop-input:focus { outline: none; border-color: #22d3ee; box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.15); }
        .sim3d-prop-input::placeholder { color: #475569; }
        .sim3d-prop-input:disabled { opacity: 0.5; }
        .sim3d-prop-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }
        .sim3d-prop-actions { display: flex; flex-direction: column; gap: 6px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #1e293b; }
        .sim3d-action-btn { padding: 9px 12px; border-radius: 8px; border: 1px solid #334155; background: rgba(15, 23, 42, 0.7); color: #cbd5e1; font-size: 11px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.2s; text-align: left; }
        .sim3d-action-btn:hover { background: rgba(30, 41, 59, 0.9); border-color: #22d3ee; color: #f1f5f9; transform: translateX(2px); }
        .sim3d-action-btn.primary { background: linear-gradient(90deg, #0891b2, #2563eb); border-color: transparent; color: white; }
        .sim3d-action-btn.primary:hover { background: linear-gradient(90deg, #06b6d4, #3b82f6); }
        .sim3d-action-btn.danger { background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.4); color: #f87171; }
        .sim3d-action-btn.danger:hover { background: rgba(239, 68, 68, 0.3); color: #fecaca; }
        .sim3d-action-icon { width: 16px; height: 16px; flex-shrink: 0; }
        
        /* Drop hint */
        .sim3d-drop-hint { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 40; pointer-events: none; padding: 20px 30px; border-radius: 16px; border: 2px dashed #22d3ee; background: rgba(6, 182, 212, 0.15); backdrop-filter: blur(10px); text-align: center; opacity: 0; transition: opacity 0.2s; }
        .sim3d-drop-hint.active { opacity: 1; }
        .sim3d-drop-hint-icon { font-size: 32px; margin-bottom: 8px; }
        .sim3d-drop-hint-text { font-size: 13px; font-weight: 700; color: #67e8f9; letter-spacing: 0.5px; }
        .sim3d-drop-hint-sub { font-size: 10px; color: #94a3b8; margin-top: 4px; }
        
        .sim3d-connections-panel { position: absolute; left: 16px; bottom: 16px; width: 320px; max-width: calc(100vw - 32px); border-radius: 12px; padding: 12px; max-height: 200px; display: flex; flex-direction: column; z-index: 10; }
        .sim3d-connections-title { font-size: 10px; font-weight: 800; color: #67e8f9; text-transform: uppercase; margin-bottom: 8px; display: flex; justify-content: space-between; }
        .sim3d-connections-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
        .sim3d-connection-row { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 5px 7px; background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; border-radius: 6px; font-size: 9px; color: #cbd5e1; }
        .sim3d-connection-row .tag { font-family: monospace; font-weight: 700; color: #67e8f9; }
        .sim3d-connection-remove { padding: 2px 6px; border-radius: 4px; border: none; background: rgba(239, 68, 68, 0.2); color: #f87171; cursor: pointer; font-size: 9px; font-weight: 700; }
        .sim3d-connection-remove:hover { background: #ef4444; color: white; }
        
        .sim3d-patch-modal { position: fixed; inset: 0; z-index: 60; background: rgba(2, 6, 23, 0.85); backdrop-filter: blur(8px); display: none; align-items: center; justify-content: center; padding: 16px; }
        .sim3d-patch-modal.open { display: flex; }
        .sim3d-patch-content { width: 100%; max-width: 440px; border-radius: 16px; padding: 18px; border: 1px solid rgba(6, 182, 212, 0.4); }
        .sim3d-patch-title { font-size: 13px; font-weight: 800; color: white; }
        .sim3d-patch-sub { font-size: 10px; color: #22d3ee; margin-bottom: 12px; }
        .sim3d-patch-section-label { font-size: 10px; font-weight: 800; color: #cbd5e1; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
        .sim3d-cable-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 12px; }
        .sim3d-cable-btn { padding: 8px; border-radius: 10px; border: 2px solid #334155; background: #0f172a; color: #cbd5e1; font-size: 10px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.2s; }
        .sim3d-cable-btn:hover { border-color: #64748b; }
        .sim3d-cable-btn.active { border-color: #22d3ee; color: white; }
        .sim3d-cable-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
        .sim3d-dest-list { max-height: 140px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; padding: 6px; background: rgba(2, 6, 23, 0.6); border-radius: 10px; border: 1px solid #1e293b; margin-bottom: 12px; }
        .sim3d-dest-item { display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; border-radius: 6px; background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; cursor: pointer; font-size: 10px; color: #cbd5e1; }
        .sim3d-dest-item:hover { background: rgba(30, 41, 59, 0.6); }
        .sim3d-dest-item input { accent-color: #06b6d4; width: 14px; height: 14px; cursor: pointer; }
        .sim3d-patch-confirm { width: 100%; padding: 10px; border-radius: 10px; border: none; background: linear-gradient(90deg, #0891b2, #2563eb); color: white; font-weight: 800; font-size: 11px; cursor: pointer; box-shadow: 0 6px 20px rgba(8, 145, 178, 0.4); }
        .sim3d-patch-confirm:hover { background: linear-gradient(90deg, #06b6d4, #3b82f6); }
        
        .sim3d-terminal { position: fixed; inset: 0; z-index: 60; background: rgba(2, 6, 23, 0.9); backdrop-filter: blur(8px); display: none; align-items: center; justify-content: center; padding: 16px; }
        .sim3d-terminal.open { display: flex; }
        .sim3d-terminal-content { width: 100%; max-width: 560px; border-radius: 16px; padding: 16px; border: 1px solid rgba(16, 185, 129, 0.4); }
        .sim3d-terminal-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid #1e293b; margin-bottom: 10px; }
        .sim3d-terminal-title { font-size: 12px; font-weight: 800; color: white; font-family: monospace; display: flex; align-items: center; gap: 8px; }
        .sim3d-terminal-output { background: #020617; padding: 12px; border-radius: 10px; font-family: monospace; font-size: 11px; color: #34d399; height: 240px; overflow-y: auto; border: 1px solid #0f172a; line-height: 1.6; }
        
        .sim3d-toast { position: fixed; bottom: 24px; right: 24px; z-index: 70; padding: 12px 18px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.5); color: white; font-size: 11px; font-weight: 700; display: flex; align-items: center; gap: 8px; transform: translateY(80px); opacity: 0; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); pointer-events: none; }
        .sim3d-toast.show { transform: translateY(0); opacity: 1; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <video id="bgVideo" class="dynamic-background" autoplay loop muted playsinline></video>
    <img id="bgGif" class="dynamic-background" src="" alt="">

    <div id="loadingOverlay" class="loading-overlay">
        <div class="loading-spinner"></div>
        <div class="loading-text">Carregando módulos...</div>
        <div style="font-size: 12px; margin-top: 10px; opacity: 0.7;" id="loadingDeviceType"></div>
    </div>

    <button class="mobile-menu-toggle" onclick="toggleMobilePalette()">📋</button>
    <div class="mobile-overlay" id="mobileOverlay" onclick="closeMobilePalette()"></div>
    <div class="rgb-line"></div>
    
    <!-- ==================== TELA INICIAL CORPORATIVA ==================== -->
    <div class="intro-screen" id="introScreen">
        <div class="intro-grid-pattern"></div>
        <div class="intro-glow-1"></div>
        <div class="intro-glow-2"></div>
        
        <div class="intro-container">
            <!-- Brand Header -->
            <div class="intro-brand-header">
                <div class="intro-brand-logo">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="2" y="3" width="20" height="6" rx="1"/>
                        <rect x="2" y="15" width="20" height="6" rx="1"/>
                        <line x1="6" y1="6" x2="6.01" y2="6"/>
                        <line x1="6" y1="18" x2="6.01" y2="18"/>
                        <path d="M12 9v6"/>
                    </svg>
                </div>
                <div>
                    <div class="intro-brand-title">PROJ<span>I</span>TIZE</div>
                    <div class="intro-brand-subtitle">Infraestrutura · CFTV · Redes · Datacenter</div>
                </div>
            </div>
            
            <!-- Hero -->
            <div class="intro-hero">
                <div class="intro-hero-text">
                    <div class="intro-hero-badge">Plataforma Profissional</div>
                    <h1 class="intro-hero-title">
                        Sistema Completo para <span class="highlight">CFTV, Redes</span> e Datacenter
                    </h1>
                    <p class="intro-hero-desc">
                        Projete, simule e documente toda sua infraestrutura em 2D e 3D com precisão profissional. 
                        Do rascunho ao orçamento final, tudo em uma única plataforma.
                    </p>
                    <div class="intro-cta-group">
                        <button class="intro-cta-primary" onclick="closeIntroAndShowLogin()">
                            <span>Acessar Sistema</span>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="5" y1="12" x2="19" y2="12"/>
                                <polyline points="12 5 19 12 12 19"/>
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="intro-hero-visual">
                    <svg viewBox="0 0 400 360" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <linearGradient id="rackGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                                <stop offset="0%" stop-color="#1e293b"/>
                                <stop offset="100%" stop-color="#0f172a"/>
                            </linearGradient>
                            <linearGradient id="ledGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stop-color="#22d3ee"/>
                                <stop offset="100%" stop-color="#3b82f6"/>
                            </linearGradient>
                            <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.9"/>
                                <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.3"/>
                            </linearGradient>
                            <filter id="svgGlow">
                                <feGaussianBlur stdDeviation="3" result="blur"/>
                                <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                            </filter>
                        </defs>
                        
                        <!-- Grid floor perspective -->
                        <g opacity="0.25" stroke="#22d3ee" stroke-width="1" fill="none">
                            <line x1="50" y1="300" x2="350" y2="300"/>
                            <line x1="70" y1="310" x2="330" y2="310"/>
                            <line x1="90" y1="320" x2="310" y2="320"/>
                            <line x1="140" y1="300" x2="100" y2="330"/>
                            <line x1="200" y1="300" x2="200" y2="330"/>
                            <line x1="260" y1="300" x2="300" y2="330"/>
                        </g>
                        
                        <!-- Rack -->
                        <g transform="translate(155, 60)" filter="url(#svgGlow)">
                            <rect x="0" y="0" width="90" height="220" rx="6" fill="url(#rackGrad)" stroke="#38bdf8" stroke-width="2"/>
                            <!-- Shelves / equipment -->
                            <rect x="8" y="12" width="74" height="18" rx="2" fill="#0ea5e9" opacity="0.7"/>
                            <circle cx="74" cy="21" r="2" fill="#22c55e"/>
                            <rect x="8" y="36" width="74" height="18" rx="2" fill="#22c55e" opacity="0.7"/>
                            <circle cx="74" cy="45" r="2" fill="#22c55e"/>
                            <rect x="8" y="60" width="74" height="18" rx="2" fill="#f59e0b" opacity="0.7"/>
                            <circle cx="74" cy="69" r="2" fill="#22c55e"/>
                            <rect x="8" y="84" width="74" height="18" rx="2" fill="#06b6d4" opacity="0.7"/>
                            <circle cx="74" cy="93" r="2" fill="#22c55e"/>
                            <rect x="8" y="108" width="74" height="18" rx="2" fill="#8b5cf6" opacity="0.7"/>
                            <circle cx="74" cy="117" r="2" fill="#22c55e"/>
                            <rect x="8" y="132" width="74" height="18" rx="2" fill="#a855f7" opacity="0.7"/>
                            <circle cx="74" cy="141" r="2" fill="#22c55e"/>
                            <rect x="8" y="156" width="74" height="18" rx="2" fill="#6366f1" opacity="0.7"/>
                            <circle cx="74" cy="165" r="2" fill="#22c55e"/>
                            <!-- Base -->
                            <rect x="0" y="190" width="90" height="20" rx="2" fill="#0f172a" stroke="#334155" stroke-width="1"/>
                        </g>
                        
                        <!-- Network nodes -->
                        <g filter="url(#svgGlow)">
                            <circle cx="70" cy="80" r="14" fill="url(#ledGrad)"/>
                            <circle cx="70" cy="80" r="8" fill="#060d1a"/>
                            <circle cx="330" cy="80" r="14" fill="url(#ledGrad)"/>
                            <circle cx="330" cy="80" r="8" fill="#060d1a"/>
                            <circle cx="70" cy="260" r="14" fill="url(#ledGrad)"/>
                            <circle cx="70" cy="260" r="8" fill="#060d1a"/>
                            <circle cx="330" cy="260" r="14" fill="url(#ledGrad)"/>
                            <circle cx="330" cy="260" r="8" fill="#060d1a"/>
                        </g>
                        
                        <!-- Connection paths -->
                        <path d="M 84 80 Q 140 90 155 100" stroke="url(#lineGrad)" stroke-width="2" fill="none" stroke-dasharray="6 4">
                            <animate attributeName="stroke-dashoffset" from="0" to="-20" dur="1.5s" repeatCount="indefinite"/>
                        </path>
                        <path d="M 316 80 Q 260 90 245 100" stroke="url(#lineGrad)" stroke-width="2" fill="none" stroke-dasharray="6 4">
                            <animate attributeName="stroke-dashoffset" from="0" to="-20" dur="1.5s" repeatCount="indefinite"/>
                        </path>
                        <path d="M 84 260 Q 140 250 155 240" stroke="url(#lineGrad)" stroke-width="2" fill="none" stroke-dasharray="6 4">
                            <animate attributeName="stroke-dashoffset" from="0" to="-20" dur="1.5s" repeatCount="indefinite"/>
                        </path>
                        <path d="M 316 260 Q 260 250 245 240" stroke="url(#lineGrad)" stroke-width="2" fill="none" stroke-dasharray="6 4">
                            <animate attributeName="stroke-dashoffset" from="0" to="-20" dur="1.5s" repeatCount="indefinite"/>
                        </path>
                        
                        <!-- Data particles -->
                        <circle cx="84" cy="80" r="3" fill="#22d3ee" filter="url(#svgGlow)">
                            <animateMotion dur="2s" repeatCount="indefinite" path="M 0 0 Q 56 10 71 20"/>
                        </circle>
                        <circle cx="316" cy="80" r="3" fill="#22d3ee" filter="url(#svgGlow)">
                            <animateMotion dur="2s" repeatCount="indefinite" path="M 0 0 Q -56 10 -71 20"/>
                        </circle>
                    </svg>
                </div>
            </div>
            
            <!-- Features -->
            <div class="intro-features-grid">
                <div class="intro-feature-card">
                    <div class="intro-feature-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="3" width="18" height="18" rx="2"/>
                            <path d="M3 9h18M9 21V9"/>
                        </svg>
                    </div>
                    <div class="intro-feature-title">Projetos 2D</div>
                    <div class="intro-feature-desc">Canvas interativo com equipamentos, conexões, formas e plantas baixas.</div>
                </div>
                <div class="intro-feature-card">
                    <div class="intro-feature-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="2" y="3" width="20" height="14" rx="2"/>
                            <line x1="8" y1="21" x2="16" y2="21"/>
                            <line x1="12" y1="17" x2="12" y2="21"/>
                        </svg>
                    </div>
                    <div class="intro-feature-title">Simulador 3D</div>
                    <div class="intro-feature-desc">Monte racks com equipamentos realistas, conexões animadas e diagnósticos.</div>
                </div>
                <div class="intro-feature-card">
                    <div class="intro-feature-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/>
                            <line x1="16" y1="17" x2="8" y2="17"/>
                        </svg>
                    </div>
                    <div class="intro-feature-title">PDF & Relatórios</div>
                    <div class="intro-feature-desc">Exporte mapas, listas de equipamentos e orçamentos completos em PDF.</div>
                </div>
                <div class="intro-feature-card">
                    <div class="intro-feature-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="12" y1="1" x2="12" y2="23"/>
                            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                        </svg>
                    </div>
                    <div class="intro-feature-title">Orçamento</div>
                    <div class="intro-feature-desc">Gere orçamentos automáticos baseados em todos os equipamentos do projeto.</div>
                </div>
            </div>
            
            <!-- Footer -->
            <div class="intro-footer-bar">
                <div class="intro-dev-badge-small">
                    <div class="intro-dev-avatar-small" id="introDevAvatar">
                        <svg viewBox="0 0 32 32" width="32" height="32">
                            <circle cx="16" cy="16" r="16" fill="#0f172a"/>
                            <circle cx="16" cy="13" r="5" fill="#38bdf8" opacity="0.85"/>
                            <path d="M 6 26 Q 6 19 16 19 Q 26 19 26 26" fill="#38bdf8" opacity="0.85"/>
                        </svg>
                    </div>
                    <div>
                        <div style="color:#cbd5e1;font-size:11px;font-weight:600;"><strong style="color:#38bdf8;">Thiago Souza</strong> · Analista de Tecnologia</div>
                        <div style="font-size:10px;">Unidade 2 · São José do Rio Preto · © 2026</div>
                    </div>
                </div>
                <div style="font-size:10px;">v2.4 · Sistema Profissional de Projetos</div>
            </div>
        </div>
    </div>
    
    <!-- ==================== SPLASH ==================== -->
    <div class="splash-screen" id="splashScreen">
        <div class="splash-content">
            <div class="splash-logo">🎥🔒🌐</div>
            <div class="splash-title">PROJETIZE</div>
            <div class="splash-subtitle">Sistema Para CFTV, Redes e muito mais...</div>
        </div>
    </div>
    
    <!-- ==================== TELA DE LOGIN (PERFEITA) ==================== -->
    <div class="login-modal" id="loginModal">
        <img id="loginBgMedia" alt="">
        <video id="loginBgVideo" autoplay loop muted playsinline></video>
        <div class="login-overlay-gradient"></div>
        <div class="matrix-bg" id="matrixBg"></div>
        <button class="login-bg-toggle" id="loginBgToggle" onclick="openLoginBgModal()" title="Trocar fundo da tela de login (Admin)" style="display:none;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
            </svg>
        </button>
        
        <div class="login-split">
            <div class="login-brand-panel">
                <div class="login-brand-logo">
                    <svg viewBox="0 0 64 64" width="84" height="84">
                        <defs>
                            <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#00ccff"/>
                                <stop offset="100%" stop-color="#005f99"/>
                            </linearGradient>
                        </defs>
                        <circle cx="32" cy="32" r="28" fill="none" stroke="url(#logoGrad)" stroke-width="2"/>
                        <circle cx="32" cy="32" r="20" fill="none" stroke="url(#logoGrad)" stroke-width="1" opacity="0.5"/>
                        <path d="M 32 16 L 32 48 M 16 32 L 48 32" stroke="url(#logoGrad)" stroke-width="2"/>
                        <circle cx="32" cy="32" r="4" fill="url(#logoGrad)"/>
                        <circle cx="20" cy="20" r="3" fill="#00ccff"/>
                        <circle cx="44" cy="20" r="3" fill="#00ccff"/>
                        <circle cx="20" cy="44" r="3" fill="#00ccff"/>
                        <circle cx="44" cy="44" r="3" fill="#00ccff"/>
                    </svg>
                </div>
                <h1 class="login-brand-name">PROJETIZE</h1>
                <p class="login-brand-tagline">Infraestrutura · CFTV · Datacenter</p>
                <div class="login-brand-divider"></div>
                <div class="login-brand-features">
                    <div class="feature-item">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                        <span>Projetos 2D completos</span>
                    </div>
                    <div class="feature-item">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                        <span>Simulador 3D de Rack</span>
                    </div>
                    <div class="feature-item">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                        <span>Exportação PDF & Orçamento</span>
                    </div>
                </div>
            </div>
            
            <div class="login-form-panel">
                <div class="login-form-header">
                    <div class="login-avatar">
                        <img id="loginDevImage" src="" alt="Desenvolvedor" style="display:none;">
                        <svg id="loginAvatarFallback" viewBox="0 0 64 64" width="78" height="78">
                            <circle cx="32" cy="32" r="30" fill="#0f172a"/>
                            <circle cx="32" cy="26" r="10" fill="#38bdf8" opacity="0.85"/>
                            <path d="M 14 52 Q 14 38 32 38 Q 50 38 50 52" fill="#38bdf8" opacity="0.85"/>
                        </svg>
                    </div>
                    <h2 class="login-form-title">Bem-vindo de volta</h2>
                    <p class="login-form-subtitle">Faça login para continuar</p>
                </div>
                
                <div class="login-form-body">
                    <div class="login-input-group">
                        <label for="loginUsername">Usuário</label>
                        <div class="login-input-wrapper">
                            <svg class="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                            <input type="text" id="loginUsername" class="login-input-field" placeholder="Digite seu usuário" autocomplete="username" onkeydown="if(event.key==='Enter')doLogin()">
                        </div>
                    </div>
                    <div class="login-input-group">
                        <label for="loginPassword">Senha</label>
                        <div class="login-input-wrapper">
                            <svg class="login-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                            <input type="password" id="loginPassword" class="login-input-field" placeholder="Digite sua senha" autocomplete="current-password" onkeydown="if(event.key==='Enter')doLogin()">
                        </div>
                    </div>
                    <button class="login-submit-btn" id="loginBtn" onclick="doLogin()">
                        <span>Acessar Sistema</span>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                    </button>
                    <div class="login-error" id="loginError"></div>
                </div>
                
                <div class="login-form-footer">
                    <p><strong>Thiago Souza</strong> · Analista de Tecnologia</p>
                    <p>São José do Rio Preto · © 2026 Projetize</p>
                </div>
            </div>
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
        <button id="sim3dBtn" class="btn" onclick="openSim3D()" style="background:linear-gradient(135deg,#06b6d4,#3b82f6);color:white;font-weight:700;">🏢 3D Rack</button>
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
        <button class="btn btn-success" onclick="window.open('https://th-tech.souzathiagosantos03.workers.dev', '_blank')" style="background:#fd7e14; color:white; font-weight:bold;">🌐 TH-TEC</button>
        <button class="btn btn-danger" onclick="logout()">🚪 Sair</button>
        <span style="flex:1"></span>
        <div class="user-info" id="userInfo"></div>
        <div class="zoom-controls"><span>🔍 Zoom:</span><button onclick="zoomIn()">+</button><button onclick="zoomOut()">-</button><button onclick="resetZoom()">Reset</button></div>
        <div class="zoom-controls"><span>📐 Ícones:</span><button onclick="iconZoomIn()">+</button><button onclick="iconZoomOut()">-</button><button onclick="resetIconSize()">Reset</button></div>
    </div>
    
    <div class="shapes-toolbar" id="shapesToolbar" style="display: none;">
        <button class="shape-btn" onclick="setShapeMode('line')">📏 Linha</button>
        <button class="shape-btn" onclick="setShapeMode('door')">🚪 Porta</button>
        <button class="shape-btn" onclick="setShapeMode('window')">🪟 Janela</button>
        <button class="shape-btn" onclick="setShapeMode('text')">📝 Texto</button>
        <button class="shape-btn" onclick="cancelShapeMode()">❌ Cancelar</button>
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
                <button class="close-properties-btn" onclick="closePropertiesPanel()">✕</button>
            </div>
            <div id="props-content"><p style="color:var(--text-secondary);">Clique em um componente ou forma</p></div>
        </div>
    </div>
    <div id="deleteShapeBtn" class="delete-shape-btn" onclick="deleteSelectedShape()">🗑 Excluir Forma</div>
    
    <!-- ==================== SIMULADOR 3D OVERLAY (REDESENHADO) ==================== -->
    <div id="sim3d-overlay">
        <div id="sim3d-container"></div>
        
        <div class="sim3d-header">
            <div class="sim3d-brand sim3d-glass">
                <div class="sim3d-brand-icon">🖥️</div>
                <div>
                    <h1>Simulador 3D</h1>
                    <p>Arraste equipamentos para o cenário</p>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <button id="sim3d-toggle-drawer" class="sim3d-btn">📦 Equipamentos</button>
                <button id="sim3d-run-script" class="sim3d-btn sim3d-btn-primary">⚡ Script</button>
                <button id="sim3d-close-btn" class="sim3d-btn-close" title="Fechar">✕</button>
            </div>
        </div>
        
        <!-- Drawer com equipamentos arrastáveis -->
        <div id="sim3d-equipment-drawer" class="sim3d-drawer sim3d-glass">
            <div class="sim3d-drawer-header">
                <h2>📦 Equipamentos Disponíveis</h2>
                <button id="sim3d-close-drawer" class="sim3d-drawer-close">✕</button>
            </div>
            <p class="sim3d-drawer-hint">Arraste para o cenário 3D ou <strong>clique</strong> para adicionar ao centro.</p>
            <div id="sim3d-equipment-list" class="sim3d-drawer-list"></div>
        </div>
        
        <!-- Painel de propriedades do objeto 3D -->
        <div id="sim3d-properties" class="sim3d-properties sim3d-glass">
            <div class="sim3d-prop-header">
                <div class="sim3d-prop-title" id="sim3d-prop-title">Dispositivo</div>
                <button class="sim3d-prop-close" onclick="sim3dCloseProperties()">✕</button>
            </div>
            <div class="sim3d-prop-body" id="sim3d-prop-body"></div>
        </div>
        
        <!-- Drop hint -->
        <div id="sim3d-drop-hint" class="sim3d-drop-hint">
            <div class="sim3d-drop-hint-icon">⬇️</div>
            <div class="sim3d-drop-hint-text">Solte no cenário</div>
            <div class="sim3d-drop-hint-sub">Posicione livremente dentro ou fora do rack</div>
        </div>
        
        <div id="sim3d-connections-panel" class="sim3d-connections-panel sim3d-glass" style="display:none;">
            <div class="sim3d-connections-title"><span>🔗 Conexões (<span id="sim3d-connections-count">0</span>)</span></div>
            <div id="sim3d-connections-list" class="sim3d-connections-list"></div>
        </div>
        
        <div id="sim3d-patch-modal" class="sim3d-patch-modal">
            <div class="sim3d-patch-content sim3d-glass">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
                    <div>
                        <div id="sim3d-patch-title" class="sim3d-patch-title">Conectar</div>
                        <div class="sim3d-patch-sub">Selecione tipo de cabo e destinos</div>
                    </div>
                    <button id="sim3d-patch-close" class="sim3d-btn-close" style="width:30px;height:30px;font-size:13px;">✕</button>
                </div>
                <div class="sim3d-patch-section-label">Tipo de Cabo</div>
                <div class="sim3d-cable-grid" id="sim3d-cable-grid">
                    <button class="sim3d-cable-btn active" data-cable="cat6"><span class="sim3d-cable-dot" style="background:#22d3ee;"></span> Cat6 UTP</button>
                    <button class="sim3d-cable-btn" data-cable="fiber-sfp"><span class="sim3d-cable-dot" style="background:#f59e0b;"></span> Fibra SFP+</button>
                    <button class="sim3d-cable-btn" data-cable="power-ac"><span class="sim3d-cable-dot" style="background:#ef4444;"></span> Energia AC</button>
                    <button class="sim3d-cable-btn" data-cable="coax-bnc"><span class="sim3d-cable-dot" style="background:#a855f7;"></span> Coaxial BNC</button>
                </div>
                <div class="sim3d-patch-section-label">Destinos</div>
                <div id="sim3d-dest-list" class="sim3d-dest-list"></div>
                <button id="sim3d-confirm-patch" class="sim3d-patch-confirm">✅ Estabelecer Conexão(ões)</button>
            </div>
        </div>
        
        <div id="sim3d-terminal" class="sim3d-terminal">
            <div class="sim3d-terminal-content sim3d-glass">
                <div class="sim3d-terminal-header">
                    <div class="sim3d-terminal-title"><span style="width:8px;height:8px;border-radius:50%;background:#34d399;box-shadow:0 0 8px #34d399;"></span>Network Diagnostics</div>
                    <button id="sim3d-terminal-close" class="sim3d-btn-close" style="width:28px;height:28px;font-size:12px;">✕</button>
                </div>
                <div id="sim3d-terminal-output" class="sim3d-terminal-output"><p style="color:#64748b;">[SYSTEM] Aguardando...</p></div>
            </div>
        </div>
        
        <div id="sim3d-toast" class="sim3d-toast sim3d-glass"><span style="color:#34d399;">✅</span><span id="sim3d-toast-message">Notificação</span></div>
    </div>
    <!-- ============================================================ -->
    
    <script>
        // ==================== PARTE 2 E 3 CONTINUAM AQUI ====================
        // O JavaScript completo será fornecido na PARTE 2 (2D + Login) e PARTE 3 (3D)
        // Cole o conteúdo da PARTE 2 primeiro, depois o da PARTE 3, ambos dentro desta tag <script>
    </script>
</body>
</html>
"""
// ==================== PARTE 2: PROJETIZE 2D + LOGIN + MODAIS ====================
// (Cole este bloco antes da Parte 3)

// ---------- ESTADO GLOBAL 2D ----------
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
let shapeMode = null;
let shapeStart = null;
let drawingPreview = null;
let lastMousePos = null;
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
let loginBgConfig = { type: 'matrix', filename: null, opacity: 0.35, mime: null };

// Detect device
(function() {
    const ua = navigator.userAgent;
    let dev = "Desktop / Notebook";
    if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) dev = "Tablet";
    else if (/Mobile|Android|iP(hone|od)|IEMobile|BlackBerry|Kindle|Silk-Accelerated/i.test(ua)) dev = "Celular";
    const el = document.getElementById('loadingDeviceType');
    if (el) el.innerText = "Dispositivo detectado: " + dev;
})();

// Image cache
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

// Cable defaults
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
    'bluetooth': { color: '#0066cc', name: 'Bluetooth', icon: '📱', type: 'wireless', speed: '24 Mbps', desc: 'Bluetooth', animation: 'wave' },
    'zigbee': { color: '#00aa66', name: 'ZigBee', icon: '🔵', type: 'wireless', speed: '250 Kbps', desc: 'ZigBee - IoT', animation: 'packet' },
    'lora': { color: '#cc8800', name: 'LoRa', icon: '📡', type: 'wireless', speed: '50 Kbps', desc: 'LoRa - Longa distância', animation: 'packet' }
};

let cableColors = JSON.parse(JSON.stringify(defaultCableColors));
let customConnections = [];
let connectionCategories = {};

const STORAGE_KEYS = {
    ICON_SIZE: 'projetize_icon_size',
    CANVAS_ZOOM: 'projetize_canvas_zoom',
    COMPONENTS: (u) => `projetize_${u}_components`,
    CONNECTIONS_DATA: (u) => `projetize_${u}_connections`,
    SHAPES: (u) => `projetize_${u}_shapes`,
    BACKGROUND: (u) => `projetize_${u}_background`,
    SIM3D_MOUNTED: (u) => `projetize_${u}_sim3d_mounted`,
    SIM3D_CONNECTIONS: (u) => `projetize_${u}_sim3d_connections`
};

let categories = {};
let customDevices = [];
let defaultCategories = {};

// ---------- HELPERS ----------
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
function closeModal() {
    if (window.currentModal) {
        document.body.removeChild(window.currentModal);
        window.currentModal = null;
    }
}
function readImageAsBase64(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.readAsDataURL(file);
    });
}
function getConnectionKey(name) { return name.toLowerCase().replace(/[^a-z0-9]/g, ''); }

// ---------- CONFIG LOAD ----------
async function loadDefaultConfig() {
    try {
        const r = await fetch('/api/default_config');
        const d = await r.json();
        if (d.success) defaultCategories = d.config;
    } catch(e) { console.error(e); }
}
async function loadDefaultConnections() {
    try {
        const r = await fetch('/api/default_connections');
        const d = await r.json();
        if (d.success) {
            connectionCategories = d.config;
            for (const catData of Object.values(d.config)) {
                for (const conn of catData.connections) {
                    cableColors[getConnectionKey(conn.name)] = { ...conn };
                }
            }
        }
    } catch(e) { console.error(e); }
}

// ---------- PERSISTENCE ----------
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
            if (typeof window.saveSim3DState === 'function') window.saveSim3DState();
        }
    }, 300);
}

async function loadUserData() {
    const sIS = localStorage.getItem(STORAGE_KEYS.ICON_SIZE);
    if (sIS) iconSize = parseInt(sIS);
    const sZ = localStorage.getItem(STORAGE_KEYS.CANVAS_ZOOM);
    if (sZ) zoom = parseFloat(sZ);

    categories = JSON.parse(JSON.stringify(defaultCategories));

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
        if (results[1]) components = JSON.parse(results[1]);
        if (results[2]) connections = JSON.parse(results[2]);
        if (results[3]) shapes = JSON.parse(results[3]);
        if (results[4]) {
            const bg = JSON.parse(results[4]);
            backgroundImage = bg.url;
            backgroundOpacity = bg.opacity || 0.8;
            backgroundWidth = bg.width || 0;
            backgroundHeight = bg.height || 0;
            backgroundX = bg.x || canvas.width/2 - (bg.width || 0)/2;
            backgroundY = bg.y || canvas.height/2 - (bg.height || 0)/2;
            if (backgroundImage) { backgroundImageObj = new Image(); backgroundImageObj.src = backgroundImage; }
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
        await fetch('/api/save_global_custom_devices', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ devices: customDevices }) });
    } catch(e) { console.error(e); }
}

// ---------- PALETTE RENDERING ----------
function renderDeviceIcon(device) {
    if (device.iconFile) return `<img src="/uploads/icons/${device.iconFile}" style="width:24px;height:24px;object-fit:contain;">`;
    return device.icon || '📦';
}
function renderConnectionIcon(conn) {
    if (conn.iconFile) return `<img src="/uploads/icons/${conn.iconFile}" style="width:24px;height:24px;object-fit:contain;">`;
    return conn.icon || '🔌';
}

function renderPalette() {
    const container = document.getElementById('categories-container');
    if (!container) return;
    container.innerHTML = '';

    for (const [catName, catData] of Object.entries(categories)) {
        const catDiv = document.createElement('div');
        catDiv.className = 'category';
        const catIcon = catData.iconFile ? `<img src="/uploads/icons/${catData.iconFile}" style="width:16px;height:16px;">` : (catData.icon || '📁');
        const isAdmin = userRole === 'admin' || userRole === 'master';
        catDiv.innerHTML = `<div class="category-header"><h3>${catIcon} ${catName}</h3>${isAdmin ? `<div class="category-actions"><button onclick="editCategory('${catName.replace(/'/g, "\\'")}')" title="Editar">✏️</button><button onclick="openCategoryIconModal('${catName.replace(/'/g, "\\'")}')" title="Ícone">🎨</button><button onclick="deleteCategory('${catName.replace(/'/g, "\\'")}')" title="Excluir">🗑</button><button onclick="addDeviceToCategory('${catName.replace(/'/g, "\\'")}')" title="Adicionar">➕</button></div>` : ''}</div><div id="category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>`;
        container.appendChild(catDiv);

        const devContainer = document.getElementById(`category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
        if (catData.devices) {
            catData.devices.forEach((device, idx) => {
                const el = document.createElement('div');
                el.className = 'component';
                el.setAttribute('draggable', 'true');
                el.innerHTML = `<div class="component-icon">${renderDeviceIcon(device)}</div><div class="component-info"><div class="component-name">${device.name}</div><div class="component-desc">${device.desc || ''}</div></div>${isAdmin ? `<div class="component-actions"><button onclick="editDevice('${catName.replace(/'/g, "\\'")}', ${idx})" title="Editar">✏️</button><button onclick="openDeviceIconModal('${catName.replace(/'/g, "\\'")}', ${idx})" title="Ícone">🎨</button><button onclick="deleteDevice('${catName.replace(/'/g, "\\'")}', ${idx})" title="Excluir">🗑</button></div>` : ''}`;
                el.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('text/plain', JSON.stringify({
                        name: device.name, icon: device.icon, type: device.type,
                        subtype: device.subtype || '', color: device.color, iconFile: device.iconFile || null
                    }));
                });
                devContainer.appendChild(el);
            });
        }
    }

    // Custom
    if (customDevices.length > 0) {
        const custDiv = document.createElement('div');
        custDiv.className = 'category';
        const isAdmin = userRole === 'admin' || userRole === 'master';
        custDiv.innerHTML = `<div class="category-header"><h3>🎨 Personalizados</h3>${isAdmin ? `<div class="category-actions"><button onclick="openAddDeviceModal()" title="Adicionar">➕</button></div>` : ''}</div><div id="custom-devices-container"></div>`;
        container.appendChild(custDiv);
        const cc = document.getElementById('custom-devices-container');
        customDevices.forEach((device, idx) => {
            const el = document.createElement('div');
            el.className = 'component';
            el.setAttribute('draggable', 'true');
            el.innerHTML = `<div class="component-icon">${renderDeviceIcon(device)}</div><div class="component-info"><div class="component-name">${device.name}</div><div class="component-desc">${device.desc || 'Personalizado'}</div></div>${isAdmin ? `<div class="component-actions"><button onclick="editCustomDevice(${idx})" title="Editar">✏️</button><button onclick="openCustomDeviceIconModal(${idx})" title="Ícone">🎨</button><button onclick="deleteCustomDevice(${idx})" title="Excluir">🗑</button></div>` : ''}`;
            el.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', JSON.stringify({
                    name: device.name, icon: device.icon, type: device.type || 'custom',
                    subtype: 'custom', color: device.color || '#005f99', iconFile: device.iconFile || null
                }));
            });
            cc.appendChild(el);
        });
    }
}

function renderConnectionsPalette() {
    const container = document.getElementById('connections-container');
    if (!container) return;
    container.innerHTML = '';
    const allConns = { ...connectionCategories };
    customConnections.forEach(conn => {
        if (!allConns['Personalizadas']) allConns['Personalizadas'] = { icon: '🔌', connections: [] };
        allConns['Personalizadas'].connections.push(conn);
    });

    for (const [catName, catData] of Object.entries(allConns)) {
        if (!catData.connections || catData.connections.length === 0) continue;
        const catDiv = document.createElement('div');
        catDiv.className = 'category';
        const isAdmin = userRole === 'admin' || userRole === 'master';
        catDiv.innerHTML = `<div class="category-header"><h3>${catData.icon || '🔌'} ${catName}</h3>${isAdmin ? `<div class="category-actions"><button onclick="addConnectionToCategory('${catName.replace(/'/g, "\\'")}')" title="Adicionar">➕</button></div>` : ''}</div><div id="conn-category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>`;
        container.appendChild(catDiv);
        const c = document.getElementById(`conn-category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
        catData.connections.forEach((conn, idx) => {
            const el = document.createElement('div');
            el.className = 'component';
            el.style.cursor = 'pointer';
            el.onclick = () => { selectedConnectionType = getConnectionKey(conn.name); showToast(`✅ Tipo selecionado: ${conn.name}`); };
            el.innerHTML = `<div class="component-icon">${renderConnectionIcon(conn)}</div><div class="component-info"><div class="component-name">${conn.name}</div><div class="component-desc">${conn.desc || conn.speed || ''}</div></div>${isAdmin ? `<div class="component-actions"><button onclick="editCustomConnection('${catName.replace(/'/g, "\\'")}', ${idx})" title="Editar">✏️</button><button onclick="openConnectionIconModal('${catName.replace(/'/g, "\\'")}', ${idx})" title="Ícone">🎨</button><button onclick="deleteCustomConnection('${catName.replace(/'/g, "\\'")}', ${idx})" title="Excluir">🗑</button></div>` : ''}`;
            c.appendChild(el);
        });
    }
}

// ---------- CANVAS ZOOM ----------
function applyZoomToCanvas() {
    canvas.style.transform = `scale(${zoom})`;
    canvas.style.transformOrigin = '0 0';
}
function zoomIn() { zoom = Math.min(zoom + 0.1, 3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
function zoomOut() { zoom = Math.max(zoom - 0.1, 0.3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
function resetZoom() { zoom = 1; applyZoomToCanvas(); saveUserData(); showToast(`🔄 Zoom: 100%`); }
function iconZoomIn() { iconSize = Math.min(iconSize + 4, 80); saveUserData(); showToast(`📐 Ícone: ${iconSize}px`); }
function iconZoomOut() { iconSize = Math.max(iconSize - 4, 20); saveUserData(); showToast(`📐 Ícone: ${iconSize}px`); }
function resetIconSize() { iconSize = 36; saveUserData(); showToast(`🔄 Ícone: ${iconSize}px`); }

// ---------- CANVAS DRAWING ----------
function drawGrid() {
    if (!showGrid) return;
    const step = 50;
    ctx.save();
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 0.5;
    for (let x = 0; x < canvas.width; x += step) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke(); }
    for (let y = 0; y < canvas.height; y += step) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke(); }
    ctx.restore();
}

function drawBackground() {
    if (backgroundImageObj && backgroundImageObj.complete && backgroundImageObj.src && backgroundWidth > 0 && backgroundHeight > 0) {
        ctx.save();
        ctx.globalAlpha = backgroundOpacity;
        ctx.drawImage(backgroundImageObj, backgroundX, backgroundY, backgroundWidth, backgroundHeight);
        ctx.globalAlpha = 1;
        if (isBackgroundSelected) {
            ctx.strokeStyle = '#005f99';
            ctx.lineWidth = 3;
            ctx.setLineDash([8, 6]);
            ctx.strokeRect(backgroundX, backgroundY, backgroundWidth, backgroundHeight);
            ctx.setLineDash([]);
            const hs = 10;
            const handles = [
                { x: backgroundX, y: backgroundY },
                { x: backgroundX + backgroundWidth, y: backgroundY },
                { x: backgroundX, y: backgroundY + backgroundHeight },
                { x: backgroundX + backgroundWidth, y: backgroundY + backgroundHeight }
            ];
            handles.forEach(h => {
                ctx.fillStyle = '#005f99';
                ctx.fillRect(h.x - hs/2, h.y - hs/2, hs, hs);
                ctx.fillStyle = 'white';
                ctx.fillRect(h.x - hs/3, h.y - hs/3, hs/1.5, hs/1.5);
            });
        }
        ctx.restore();
    }
}

function drawFieldOfView(cam) {
    if (!cam.angle) cam.angle = 0;
    if (!cam.fov) cam.fov = 80;
    const angleRad = cam.angle * Math.PI / 180;
    const fovRad = cam.fov * Math.PI / 180;
    const dist = 100;
    const la = angleRad - fovRad/2;
    const ra = angleRad + fovRad/2;
    const x1 = cam.x + Math.cos(la) * dist;
    const y1 = cam.y + Math.sin(la) * dist;
    const x2 = cam.x + Math.cos(ra) * dist;
    const y2 = cam.y + Math.sin(ra) * dist;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cam.x, cam.y);
    ctx.lineTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.fillStyle = 'rgba(0, 95, 153, 0.2)';
    ctx.fill();
    ctx.strokeStyle = '#005f99';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    const cx = cam.x + Math.cos(angleRad) * dist;
    const cy = cam.y + Math.sin(angleRad) * dist;
    ctx.beginPath();
    ctx.moveTo(cam.x, cam.y);
    ctx.lineTo(cx, cy);
    ctx.strokeStyle = '#ffaa00';
    ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.arc(cx, cy, 6, 0, 2*Math.PI);
    ctx.fillStyle = '#ffaa00';
    ctx.fill();
    ctx.fillStyle = '#000';
    ctx.font = 'bold 10px Arial';
    ctx.fillText('↻', cx-3, cy+3);
    ctx.restore();
}

function drawSensorAnimation(x, y, time) {
    const count = 3;
    const baseR = 25;
    for (let i = 0; i < count; i++) {
        const delay = i * 0.5;
        const prog = (time + delay) % 1;
        const r = baseR + (prog * 30);
        const op = 0.5 * (1 - prog);
        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, r, 0, 2 * Math.PI);
        ctx.strokeStyle = `rgba(0, 95, 153, ${op})`;
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.restore();
    }
}

function drawWirelessAnimationOnLine(x1, y1, x2, y2, type, progress) {
    const info = cableColors[type];
    if (!info || info.type !== 'wireless') return;
    const x = x1 + (x2 - x1) * progress;
    const y = y1 + (y2 - y1) * progress;
    ctx.save();
    if (info.animation === 'wave') {
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, 2 * Math.PI);
        ctx.fillStyle = info.color;
        ctx.shadowBlur = 8;
        ctx.shadowColor = info.color;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(x, y, 10, 0, 2 * Math.PI);
        ctx.strokeStyle = info.color;
        ctx.lineWidth = 1.5;
        ctx.stroke();
    } else {
        ctx.fillStyle = info.color;
        ctx.shadowBlur = 6;
        ctx.shadowColor = info.color;
        ctx.fillRect(x - 3, y - 3, 6, 6);
    }
    ctx.shadowBlur = 0;
    ctx.restore();
}

function drawConnections() {
    connections.forEach((conn, idx) => {
        const from = components.find(c => c.id === conn.from);
        const to = components.find(c => c.id === conn.to);
        if (!from || !to) return;
        const info = cableColors[conn.type] || cableColors['cat6'];
        if (!info) return;
        const isWireless = info.type === 'wireless';
        const isSelected = (selectedConnectionIndex === idx);
        ctx.save();
        if (isWireless) {
            ctx.setLineDash(info.dashPattern || [10, 8]);
            ctx.strokeStyle = info.color;
            ctx.lineWidth = isSelected ? 4 : 2;
            ctx.beginPath();
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(to.x, to.y);
            ctx.stroke();
            if (info.animation === 'wave') {
                for (let i = 0; i < 2; i++) {
                    const t = (trafficAnimation + i * 0.4) % 1;
                    drawWirelessAnimationOnLine(from.x, from.y, to.x, to.y, conn.type, t);
                }
            } else {
                for (let i = 0; i < 3; i++) {
                    const t = (trafficAnimation + i * 0.25) % 1;
                    drawWirelessAnimationOnLine(from.x, from.y, to.x, to.y, conn.type, t);
                }
            }
        } else {
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(to.x, to.y);
            ctx.strokeStyle = info.color;
            ctx.lineWidth = isSelected ? 4 : 2;
            ctx.stroke();
            const t = trafficAnimation;
            const x = from.x + (to.x - from.x) * t;
            const y = from.y + (to.y - from.y) * t;
            ctx.beginPath();
            ctx.arc(x, y, 4, 0, 2*Math.PI);
            ctx.fillStyle = info.color;
            ctx.fill();
        }
        ctx.fillStyle = '#6c757d';
        ctx.font = '9px Arial';
        const icon = info.iconFile ? '🖼️' : info.icon;
        ctx.fillText(`${icon} ${info.name}`, (from.x + to.x)/2 - 20, (from.y + to.y)/2 - 5);
        if (isSelected) {
            ctx.strokeStyle = '#005f99';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(to.x, to.y);
            ctx.stroke();
            ctx.setLineDash([]);
        }
        ctx.restore();
    });
    trafficAnimation = (trafficAnimation + 0.015) % 1;
}

function drawShapes() {
    shapes.forEach(shape => {
        const isSelected = selectedShapes.includes(shape);
        ctx.save();
        ctx.fillStyle = shape.fillColor || 'rgba(0, 0, 0, 0.05)';
        ctx.strokeStyle = shape.strokeColor || '#005f99';
        ctx.lineWidth = shape.lineWidth || 2;
        if (shape.rotation) {
            const cx = shape.x + (shape.type === 'door' ? 15 : 30);
            const cy = shape.y + (shape.type === 'door' ? 25 : 20);
            ctx.translate(cx, cy);
            ctx.rotate(shape.rotation * Math.PI / 180);
            ctx.translate(-cx, -cy);
        }
        switch (shape.type) {
            case 'line':
                ctx.beginPath();
                ctx.moveTo(shape.x1, shape.y1);
                ctx.lineTo(shape.x2, shape.y2);
                ctx.stroke();
                break;
            case 'door':
                ctx.fillStyle = 'rgba(139, 69, 19, 0.3)';
                ctx.fillRect(shape.x, shape.y, 30, 50);
                ctx.strokeStyle = '#8B4513';
                ctx.strokeRect(shape.x, shape.y, 30, 50);
                ctx.beginPath();
                ctx.arc(shape.x + 30, shape.y + 25, 20, -Math.PI/2, Math.PI/2);
                ctx.stroke();
                break;
            case 'window':
                ctx.fillStyle = 'rgba(135, 206, 235, 0.3)';
                ctx.fillRect(shape.x, shape.y, 60, 40);
                ctx.strokeStyle = '#87CEEB';
                ctx.strokeRect(shape.x, shape.y, 60, 40);
                ctx.beginPath();
                ctx.moveTo(shape.x + 30, shape.y);
                ctx.lineTo(shape.x + 30, shape.y + 40);
                ctx.moveTo(shape.x, shape.y + 20);
                ctx.lineTo(shape.x + 60, shape.y + 20);
                ctx.stroke();
                break;
            case 'text':
                ctx.font = `${(shape.fontSize || 14)}px Arial`;
                ctx.fillStyle = shape.textColor || '#212529';
                ctx.fillText(shape.text || 'Texto', shape.x, shape.y);
                break;
        }
        if (shape.rotation) ctx.setTransform(1, 0, 0, 1, 0, 0);
        if (isSelected) {
            ctx.strokeStyle = '#005f99';
            ctx.lineWidth = 2;
            if (shape.type === 'line') {
                ctx.beginPath();
                ctx.moveTo(shape.x1 - 3, shape.y1 - 3);
                ctx.lineTo(shape.x2 + 3, shape.y2 + 3);
                ctx.moveTo(shape.x1 + 3, shape.y1 - 3);
                ctx.lineTo(shape.x2 - 3, shape.y2 + 3);
                ctx.stroke();
            } else if (shape.type === 'text') {
                ctx.strokeRect(shape.x - 5, shape.y - 12, ctx.measureText(shape.text || 'Texto').width + 10, 18);
            } else {
                const w = 30;
                const h = shape.type === 'door' ? 50 : 40;
                ctx.strokeRect(shape.x - 3, shape.y - 3, w + 6, h + 6);
            }
            showShapeDeleteButton(shape);
        } else {
            const btn = document.getElementById('deleteShapeBtn');
            if (btn) btn.style.display = 'none';
        }
        ctx.restore();
    });
}

function drawComponents() {
    components.forEach(comp => {
        const isSelected = selectedComponents.includes(comp);
        if (comp.type === 'sensor') drawSensorAnimation(comp.x, comp.y, sensorAnimationTime);
        ctx.save();
        ctx.translate(comp.x, comp.y);
        ctx.rotate((comp.rotation || 0) * Math.PI / 180);
        ctx.translate(-comp.x, -comp.y);
        const half = iconSize / 2;

        if (comp.iconFile) {
            ctx.drawImage(getCachedImage(`/uploads/icons/${comp.iconFile}`), comp.x - half, comp.y - half, iconSize, iconSize);
        } else if (comp.customImage && comp.customImage.startsWith('data:image')) {
            ctx.drawImage(getCachedImage(comp.customImage), comp.x - half, comp.y - half, iconSize, iconSize);
        } else {
            ctx.fillStyle = comp.color || '#005f99';
            ctx.beginPath();
            ctx.arc(comp.x, comp.y, iconSize/2, 0, 2*Math.PI);
            ctx.fill();
            ctx.fillStyle = '#fff';
            ctx.font = `${iconSize/2}px Arial`;
            ctx.fillText(comp.customIconTemp || comp.icon || '📦', comp.x - 12, comp.y + 8);
        }
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.fillStyle = '#005f99';
        ctx.font = '12px Arial';
        ctx.fillText(comp.name, comp.x - 30, comp.y - (iconSize/2) - 5);
        if (comp.ip) {
            ctx.fillStyle = '#6c757d';
            ctx.font = '10px Arial';
            ctx.fillText(comp.ip, comp.x - 25, comp.y - (iconSize/2) - 15);
        }
        if (isSelected) {
            ctx.strokeStyle = '#005f99';
            ctx.lineWidth = 2;
            ctx.strokeRect(comp.x - half - 4, comp.y - half - 4, iconSize + 8, iconSize + 8);
            ctx.beginPath();
            ctx.arc(comp.x + half + 8, comp.y - half - 8, 6, 0, 2*Math.PI);
            ctx.fillStyle = '#005f99';
            ctx.fill();
            ctx.fillStyle = '#fff';
            ctx.font = '10px Arial';
            ctx.fillText('↻', comp.x + half + 5, comp.y - half - 5);
        }
        if (comp.type === 'camera') drawFieldOfView(comp);
        ctx.restore();
    });
    sensorAnimationTime = (sensorAnimationTime + 0.01) % 1;
}

function drawShapePreview(start, end, type) {
    if (!start || !end) return;
    ctx.save();
    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = '#005f99';
    ctx.fillStyle = 'rgba(0, 95, 153, 0.2)';
    ctx.lineWidth = 2;
    const x = Math.min(start.x, end.x);
    const y = Math.min(start.y, end.y);
    const w = Math.abs(end.x - start.x);
    switch (type) {
        case 'line':
            ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke();
            break;
        case 'door':
            ctx.fillRect(end.x, end.y, 30, 50); ctx.strokeRect(end.x, end.y, 30, 50);
            break;
        case 'window':
            ctx.fillRect(x, y, w, 40); ctx.strokeRect(x, y, w, 40);
            break;
    }
    ctx.setLineDash([]);
    ctx.restore();
}

function drawWithBackground(whiteBg = false, hideGrid = false) {
    if (whiteBg) {
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawBackground();
    }
    if (!hideGrid && showGrid) drawGrid();
    drawShapes();
    drawConnections();
    drawComponents();
}

function draw() {
    drawWithBackground(false, false);
    if (drawingPreview && shapeStart) drawShapePreview(shapeStart, lastMousePos || shapeStart, shapeMode);
    requestAnimationFrame(draw);
}
draw();

// ---------- MOUSE HELPERS ----------
function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    const sx = canvas.width / rect.width;
    const sy = canvas.height / rect.height;
    let cx, cy;
    if (e.touches) { cx = e.touches[0].clientX; cy = e.touches[0].clientY; }
    else { cx = e.clientX; cy = e.clientY; }
    return { x: (cx - rect.left) * sx, y: (cy - rect.top) * sy };
}
function pointToLineDistance(px, py, x1, y1, x2, y2) {
    const A = px - x1, B = py - y1, C = x2 - x1, D = y2 - y1;
    const dot = A * C + B * D;
    const len_sq = C * C + D * D;
    let param = -1;
    if (len_sq !== 0) param = dot / len_sq;
    let xx, yy;
    if (param < 0) { xx = x1; yy = y1; }
    else if (param > 1) { xx = x2; yy = y2; }
    else { xx = x1 + param * C; yy = y1 + param * D; }
    const dx = px - xx, dy = py - yy;
    return Math.sqrt(dx * dx + dy * dy);
}
function isPointOnShape(x, y, shape) {
    if (shape.type === 'line') return pointToLineDistance(x, y, shape.x1, shape.y1, shape.x2, shape.y2) < 8;
    if (shape.type === 'text') return x >= shape.x - 5 && x <= shape.x + (shape.text?.length * 7 || 50) && y >= shape.y - 12 && y <= shape.y + 6;
    if (shape.type === 'door') return x >= shape.x && x <= shape.x + 30 && y >= shape.y && y <= shape.y + 50;
    if (shape.type === 'window') return x >= shape.x && x <= shape.x + 60 && y >= shape.y && y <= shape.y + 40;
    return false;
}
function isPointNearConnection(x, y, from, to) {
    return pointToLineDistance(x, y, from.x, from.y, to.x, to.y) < 12;
}

// ---------- HANDLERS ----------
function handleStart(e) {
    e.preventDefault();
    const { x, y } = getMousePos(e);
    lastMousePos = { x, y };
    if (shapeMode) { shapeStart = { x, y }; drawingPreview = true; return; }

    // Component click
    let clicked = null;
    for (let i = components.length - 1; i >= 0; i--) {
        const c = components[i];
        if (Math.hypot(x - c.x, y - c.y) < iconSize/2) { clicked = c; break; }
    }
    if (clicked) {
        const multi = e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1);
        if (multi) {
            if (selectedComponents.includes(clicked)) selectedComponents = selectedComponents.filter(c => c !== clicked);
            else selectedComponents.push(clicked);
            selectedConnectionIndex = null;
            selectedShapes = [];
        } else {
            selectedComponents = [clicked];
            dragging = true;
            dragOffset = { x: clicked.x - x, y: clicked.y - y };
            isBackgroundSelected = false;
            selectedShapes = [];
            selectedConnectionIndex = null;
        }
        showProperties(clicked);
        openProperties();
        return;
    }

    // Shape click
    let clickedShape = null;
    for (let i = shapes.length - 1; i >= 0; i--) {
        if (isPointOnShape(x, y, shapes[i])) { clickedShape = shapes[i]; break; }
    }
    if (clickedShape) {
        const multi = e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1);
        if (multi) {
            if (selectedShapes.includes(clickedShape)) selectedShapes = selectedShapes.filter(s => s !== clickedShape);
            else selectedShapes.push(clickedShape);
            selectedConnectionIndex = null;
            selectedComponents = [];
        } else {
            selectedShapes = [clickedShape];
            dragging = true;
            if (clickedShape.type === 'line') dragOffset = { x: clickedShape.x1 - x, y: clickedShape.y1 - y };
            else dragOffset = { x: clickedShape.x - x, y: clickedShape.y - y };
            selectedComponents = [];
            selectedConnectionIndex = null;
        }
        showShapeProperties(clickedShape);
        openProperties();
        return;
    }

    // Connection click
    let clickedConn = null;
    for (let i = 0; i < connections.length; i++) {
        const conn = connections[i];
        const from = components.find(c => c.id === conn.from);
        const to = components.find(c => c.id === conn.to);
        if (from && to && isPointNearConnection(x, y, from, to)) { clickedConn = { index: i, conn }; break; }
    }
    if (clickedConn) {
        selectedConnectionIndex = clickedConn.index;
        selectedComponents = [];
        selectedShapes = [];
        showConnectionProperties(selectedConnectionIndex);
        openProperties();
        return;
    }

    // Background click
    if (backgroundWidth > 0 && backgroundHeight > 0) {
        const hs = 12;
        const onNW = x >= backgroundX - hs && x <= backgroundX + hs && y >= backgroundY - hs && y <= backgroundY + hs;
        const onNE = x >= backgroundX + backgroundWidth - hs && x <= backgroundX + backgroundWidth + hs && y >= backgroundY - hs && y <= backgroundY + hs;
        const onSW = x >= backgroundX - hs && x <= backgroundX + hs && y >= backgroundY + backgroundHeight - hs && y <= backgroundY + backgroundHeight + hs;
        const onSE = x >= backgroundX + backgroundWidth - hs && x <= backgroundX + backgroundWidth + hs && y >= backgroundY + backgroundHeight - hs && y <= backgroundY + backgroundHeight + hs;
        if (onNW || onNE || onSW || onSE) {
            isResizingBackground = true;
            resizeHandle = onNW ? 'nw' : onNE ? 'ne' : onSW ? 'sw' : 'se';
            resizeStart = { x: e.clientX || e.touches[0].clientX, y: e.clientY || e.touches[0].clientY, width: backgroundWidth, height: backgroundHeight, bgX: backgroundX, bgY: backgroundY };
            isBackgroundSelected = true;
            return;
        } else if (x >= backgroundX && x <= backgroundX + backgroundWidth && y >= backgroundY && y <= backgroundY + backgroundHeight) {
            isBackgroundSelected = true;
            isDraggingBackgroundImage = true;
            dragBackgroundStart = { x: (e.clientX || e.touches[0].clientX) - backgroundX, y: (e.clientY || e.touches[0].clientY) - backgroundY };
            return;
        } else {
            isBackgroundSelected = false;
        }
    }

    // Rotate handle
    for (const comp of components) {
        if (selectedComponents.includes(comp)) {
            const hx = comp.x + (iconSize/2) + 8;
            const hy = comp.y - (iconSize/2) - 8;
            if (Math.hypot(x - hx, y - hy) < 10) { rotateComponent(comp, 15); saveUserData(); return; }
        }
    }

    // Camera FOV handle
    for (const comp of components) {
        if (comp.type === 'camera') {
            const aRad = (comp.angle || 0) * Math.PI / 180;
            const hx = comp.x + Math.cos(aRad) * 100;
            const hy = comp.y + Math.sin(aRad) * 100;
            if (Math.hypot(x - hx, y - hy) < 10) { currentAngleHandle = comp; return; }
        }
    }

    // Empty selection
    if (e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1)) {
        startSelection(e);
        selectedComponents = [];
        selectedShapes = [];
        selectedConnectionIndex = null;
        showProperties(null);
    } else {
        selectedComponents = [];
        selectedShapes = [];
        selectedConnectionIndex = null;
        dragging = false;
        showProperties(null);
    }

    // Shift-click connection start
    if (e.shiftKey) {
        for (const comp of components) {
            if (Math.hypot(x - comp.x, y - comp.y) < iconSize/2) {
                isDrawingConnection = true;
                connectionStart = comp;
                return;
            }
        }
    }
}

function handleMove(e) {
    let cx, cy;
    if (e.touches) { cx = e.touches[0].clientX; cy = e.touches[0].clientY; }
    else { cx = e.clientX; cy = e.clientY; }
    const { x, y } = getMousePos(e);
    lastMousePos = { x, y };

    if (isResizingBackground && resizeHandle) {
        const dx = cx - resizeStart.x;
        const dy = cy - resizeStart.y;
        let nw = resizeStart.width, nh = resizeStart.height, nx = resizeStart.bgX, ny = resizeStart.bgY;
        switch (resizeHandle) {
            case 'se': nw = Math.max(50, resizeStart.width + dx); nh = Math.max(50, resizeStart.height + dy); break;
            case 'sw': nw = Math.max(50, resizeStart.width - dx); nh = Math.max(50, resizeStart.height + dy); nx = resizeStart.bgX + (resizeStart.width - nw); break;
            case 'ne': nw = Math.max(50, resizeStart.width + dx); nh = Math.max(50, resizeStart.height - dy); ny = resizeStart.bgY + (resizeStart.height - nh); break;
            case 'nw': nw = Math.max(50, resizeStart.width - dx); nh = Math.max(50, resizeStart.height - dy); nx = resizeStart.bgX + (resizeStart.width - nw); ny = resizeStart.bgY + (resizeStart.height - nh); break;
        }
        backgroundWidth = nw; backgroundHeight = nh; backgroundX = nx; backgroundY = ny;
        saveUserData();
        return;
    }
    if (isDraggingBackgroundImage) {
        backgroundX = cx - dragBackgroundStart.x;
        backgroundY = cy - dragBackgroundStart.y;
        saveUserData();
        return;
    }
    if (currentAngleHandle) {
        const angle = Math.atan2(y - currentAngleHandle.y, x - currentAngleHandle.x) * 180 / Math.PI;
        currentAngleHandle.angle = angle;
        saveUserData();
        return;
    }
    if (dragging && selectedComponents.length > 0) {
        const dx = (x + dragOffset.x) - selectedComponents[0].x;
        const dy = (y + dragOffset.y) - selectedComponents[0].y;
        selectedComponents.forEach(c => { c.x += dx; c.y += dy; });
        dragOffset = { x: selectedComponents[0].x - x, y: selectedComponents[0].y - y };
        saveUserData();
    }
    if (dragging && selectedShapes.length > 0) {
        const shape = selectedShapes[0];
        let dx, dy;
        if (shape.type === 'line') {
            dx = (x + dragOffset.x) - shape.x1;
            dy = (y + dragOffset.y) - shape.y1;
            shape.x1 += dx; shape.y1 += dy; shape.x2 += dx; shape.y2 += dy;
            dragOffset = { x: shape.x1 - x, y: shape.y1 - y };
        } else {
            dx = (x + dragOffset.x) - shape.x;
            dy = (y + dragOffset.y) - shape.y;
            shape.x += dx; shape.y += dy;
            dragOffset = { x: shape.x - x, y: shape.y - y };
        }
        saveUserData();
    }
    if (isSelecting) updateSelection(e);
}

function handleEnd(e) {
    if (shapeMode && shapeStart) {
        const { x, y } = getMousePos(e);
        endShape(shapeStart, { x, y }, shapeMode);
        shapeStart = null;
        drawingPreview = false;
        return;
    }
    currentAngleHandle = null;
    dragging = false;
    isDraggingBackgroundImage = false;
    isResizingBackground = false;
    resizeHandle = null;
    if (isSelecting) endSelection();
    isDrawingConnection = false;
    connectionStart = null;
}

function handleClick(e) {
    const { x, y } = getMousePos(e);
    if (isDrawingConnection && connectionStart) {
        for (const comp of components) {
            if (Math.hypot(x - comp.x, y - comp.y) < iconSize/2 && comp.id !== connectionStart.id) {
                showCableModal(connectionStart, comp);
                isDrawingConnection = false;
                connectionStart = null;
                return;
            }
        }
    }
}

function handleContextMenu(e) {
    e.preventDefault();
    const { x, y } = getMousePos(e);

    // Background
    if (isBackgroundSelected && backgroundWidth > 0 && x >= backgroundX && x <= backgroundX + backgroundWidth && y >= backgroundY && y <= backgroundY + backgroundHeight) {
        const menu = document.getElementById('contextMenu');
        menu.innerHTML = `<div class="context-menu-item" onclick="openBackgroundModal()">✏️ Editar Imagem</div><div class="context-menu-item" onclick="removeBackground()">🗑 Remover Imagem</div><div class="context-menu-item" onclick="isBackgroundSelected=false;">🔲 Desselecionar</div>`;
        menu.style.display = 'block';
        menu.style.left = e.pageX + 'px';
        menu.style.top = e.pageY + 'px';
        setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', { once: true }), 100);
        return;
    }
    // Component
    for (const c of components) {
        if (Math.hypot(x - c.x, y - c.y) < iconSize/2) { showContextMenu(e, c); return; }
    }
    // Shape
    for (const s of shapes) {
        if (isPointOnShape(x, y, s)) { showShapeContextMenu(e, s); return; }
    }
    // Connection
    for (let i = 0; i < connections.length; i++) {
        const conn = connections[i];
        const from = components.find(c => c.id === conn.from);
        const to = components.find(c => c.id === conn.to);
        if (from && to && isPointNearConnection(x, y, from, to)) { showConnectionContextMenu(e, conn, i); return; }
    }
}

// ---------- SELECTION ----------
function startSelection(e) {
    isSelecting = true;
    const { x, y } = getMousePos(e);
    selectionStart = { x, y };
    selectionEnd = { x, y };
    document.getElementById('selectionRect').style.display = 'block';
}
function updateSelection(e) {
    if (!isSelecting) return;
    const { x, y } = getMousePos(e);
    selectionEnd = { x, y };
    const left = Math.min(selectionStart.x, selectionEnd.x);
    const top = Math.min(selectionStart.y, selectionEnd.y);
    const w = Math.abs(selectionEnd.x - selectionStart.x);
    const h = Math.abs(selectionEnd.y - selectionStart.y);
    const rect = document.getElementById('selectionRect');
    const cr = canvas.getBoundingClientRect();
    rect.style.left = (cr.left + left) + 'px';
    rect.style.top = (cr.top + top) + 'px';
    rect.style.width = w + 'px';
    rect.style.height = h + 'px';
}
function endSelection() {
    if (!isSelecting) return;
    isSelecting = false;
    document.getElementById('selectionRect').style.display = 'none';
    const minX = Math.min(selectionStart.x, selectionEnd.x);
    const maxX = Math.max(selectionStart.x, selectionEnd.x);
    const minY = Math.min(selectionStart.y, selectionEnd.y);
    const maxY = Math.max(selectionStart.y, selectionEnd.y);
    selectedComponents = components.filter(c => c.x >= minX && c.x <= maxX && c.y >= minY && c.y <= maxY);
    selectedShapes = shapes.filter(s => {
        if (s.type === 'line') return (s.x1 >= minX && s.x1 <= maxX && s.y1 >= minY && s.y1 <= maxY) || (s.x2 >= minX && s.x2 <= maxX && s.y2 >= minY && s.y2 <= maxY);
        if (s.type === 'text') return s.x >= minX && s.x <= maxX && s.y >= minY && s.y <= maxY;
        const w = s.type === 'door' ? 30 : 60;
        const h = s.type === 'door' ? 50 : 40;
        return s.x + w >= minX && s.x <= maxX && s.y + h >= minY && s.y <= maxY;
    });
    const info = document.getElementById('selectionInfo');
    const total = selectedComponents.length + selectedShapes.length;
    if (total > 0) {
        info.textContent = `${total} item(s) selecionado(s)`;
        info.style.display = 'block';
        setTimeout(() => info.style.display = 'none', 2000);
    }
    if (selectedComponents.length === 1 && selectedShapes.length === 0) { showProperties(selectedComponents[0]); openProperties(); }
    else if (selectedShapes.length === 1 && selectedComponents.length === 0) { showShapeProperties(selectedShapes[0]); openProperties(); }
    else { showProperties(null); closeProperties(); }
}

// ---------- PANEL CONTROL ----------
function openProperties() { document.getElementById('propertiesPanel').classList.add('open'); }
function closeProperties() { document.getElementById('propertiesPanel').classList.remove('open'); }
function closePropertiesPanel() { closeProperties(); }
function togglePalette() { const p = document.getElementById('palette'); p.classList.toggle('collapsed'); }
function toggleMobilePalette() {}
function closeMobilePalette() {}

// ---------- PROPERTIES PANEL ----------
function showProperties(comp) {
    const div = document.getElementById('props-content');
    if (!comp) {
        div.innerHTML = '<p style="color:var(--text-secondary);">Clique em um componente ou forma</p>';
        return;
    }
    div.innerHTML = `
        <div class="property-group"><label>Nome</label><input type="text" id="prop-name" value="${(comp.name || '').replace(/"/g, '&quot;')}"></div>
        <div class="property-group"><label>Tipo</label><input type="text" value="${comp.type || ''}" disabled></div>
        <div class="property-group"><label>Posição X</label><input type="number" id="prop-x" value="${Math.round(comp.x)}"></div>
        <div class="property-group"><label>Posição Y</label><input type="number" id="prop-y" value="${Math.round(comp.y)}"></div>
        <div class="property-group"><label>🔄 Rotação</label><input type="range" id="prop-rotation" min="0" max="360" value="${comp.rotation || 0}"><span id="rotation-val">${Math.round(comp.rotation || 0)}°</span></div>
        <div class="property-group"><button class="btn btn-secondary" onclick="flipComponentById(${comp.id})" style="width:100%;">🔁 Inverter (180°)</button></div>
        <div class="property-group"><label>🌐 IP</label><input type="text" id="prop-ip" value="${comp.ip || ''}" placeholder="192.168.1.100"></div>
        <div class="property-group"><label>🔌 Porta</label><input type="number" id="prop-port" value="${comp.port || 80}"></div>
        <div class="property-group"><label>👤 Usuário</label><input type="text" id="prop-user" value="${comp.username || ''}"></div>
        <div class="property-group"><label>🔑 Senha</label><input type="password" id="prop-pass" value="${comp.password || ''}"></div>
        ${comp.type === 'camera' ? `<div class="property-group"><label>Ângulo</label><input type="range" id="prop-angle" min="0" max="360" value="${comp.angle || 0}"><span id="angle-val">${Math.round(comp.angle || 0)}°</span></div><div class="property-group"><label>FOV</label><input type="range" id="prop-fov" min="20" max="120" value="${comp.fov || 80}"><span id="fov-val">${Math.round(comp.fov || 80)}°</span></div>` : ''}
        <div class="property-group"><label>🖼️ Ícone Personalizado</label><input type="file" id="prop-image" accept="image/*"><div class="image-preview" id="prop-image-preview">${comp.iconFile ? `<img src="/uploads/icons/${comp.iconFile}" style="max-width:50px;max-height:50px;">` : ''}</div></div>
        <div class="property-group"><label>🔌 Conectar a</label><select id="prop-connect"><option value="">-- Selecione --</option>${components.filter(c => c.id !== comp.id).map(c => `<option value="${c.id}">${c.name}</option>`).join('')}</select><select id="prop-cable-type">${Object.entries(cableColors).map(([k, v]) => `<option value="${k}">${v.icon} ${v.name} - ${v.speed}</option>`).join('')}</select><button class="btn btn-primary" style="margin-top:5px;" onclick="addConnection(${comp.id})">➕ Conectar</button></div>
        <div class="modal-buttons" style="flex-wrap:wrap;">
            <button class="btn btn-info" onclick="accessDeviceById(${comp.id})">🌐 Acessar</button>
            <button class="btn btn-warning" onclick="rotateLeft(${comp.id})">🔄 Girar Esq.</button>
            <button class="btn btn-warning" onclick="rotateRight(${comp.id})">🔄 Girar Dir.</button>
            <button class="btn btn-danger" onclick="deleteComponent(${comp.id})">🗑 Remover</button>
        </div>
    `;

    const rs = document.getElementById('prop-rotation');
    if (rs) rs.oninput = (e) => { comp.rotation = parseInt(e.target.value); document.getElementById('rotation-val').innerText = comp.rotation + '°'; saveUserData(); };
    if (comp.type === 'camera') {
        const as = document.getElementById('prop-angle');
        const fs = document.getElementById('prop-fov');
        if (as) as.oninput = (e) => { comp.angle = parseInt(e.target.value); document.getElementById('angle-val').innerText = comp.angle + '°'; saveUserData(); };
        if (fs) fs.oninput = (e) => { comp.fov = parseInt(e.target.value); document.getElementById('fov-val').innerText = comp.fov + '°'; saveUserData(); };
    }
    document.getElementById('prop-name')?.addEventListener('change', (e) => { comp.name = e.target.value; saveUserData(); });
    document.getElementById('prop-x')?.addEventListener('change', (e) => { comp.x = parseInt(e.target.value); saveUserData(); });
    document.getElementById('prop-y')?.addEventListener('change', (e) => { comp.y = parseInt(e.target.value); saveUserData(); });
    document.getElementById('prop-ip')?.addEventListener('change', (e) => { comp.ip = e.target.value; saveUserData(); });
    document.getElementById('prop-port')?.addEventListener('change', (e) => { comp.port = parseInt(e.target.value); saveUserData(); });
    document.getElementById('prop-user')?.addEventListener('change', (e) => { comp.username = e.target.value; saveUserData(); });
    document.getElementById('prop-pass')?.addEventListener('change', (e) => { comp.password = e.target.value; saveUserData(); });
    const imgInput = document.getElementById('prop-image');
    if (imgInput) imgInput.onchange = async (e) => {
        const file = e.target.files[0];
        if (file) {
            const base64 = await readImageAsBase64(file);
            const resp = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'equipment' }) });
            const data = await resp.json();
            if (data.success) {
                comp.iconFile = data.filename;
                const prev = document.getElementById('prop-image-preview');
                if (prev) prev.innerHTML = `<img src="/uploads/icons/${data.filename}" style="max-width:50px;max-height:50px;">`;
                showToast(`✅ Ícone aplicado`);
                saveUserData();
            }
        }
    };
}

function showShapeProperties(shape) {
    const div = document.getElementById('props-content');
    if (!shape) return;
    div.innerHTML = `
        <div class="property-group"><label>Tipo</label><input type="text" value="${getShapeName(shape.type)}" disabled></div>
        <div class="property-group"><label>Cor da Linha</label><input type="color" id="shape-stroke" value="${shape.strokeColor || '#005f99'}"></div>
        <div class="property-group"><label>Espessura</label><input type="range" id="shape-linewidth" min="1" max="10" value="${shape.lineWidth || 2}"></div>
        ${shape.type === 'text' ? `<div class="property-group"><label>Texto</label><input type="text" id="shape-text" value="${(shape.text || '').replace(/"/g, '&quot;')}"></div><div class="property-group"><label>Fonte</label><input type="number" id="shape-fontsize" value="${shape.fontSize || 14}"></div><div class="property-group"><label>Cor Texto</label><input type="color" id="shape-textcolor" value="${shape.textColor || '#212529'}"></div>` : `<div class="property-group"><label>🔄 Rotação</label><input type="range" id="shape-rotation" min="0" max="360" value="${shape.rotation || 0}"></div>`}
        <div class="property-group"><label>Pos X</label><input type="number" id="shape-x" value="${Math.round(shape.x || shape.x1 || 0)}"></div>
        <div class="property-group"><label>Pos Y</label><input type="number" id="shape-y" value="${Math.round(shape.y || shape.y1 || 0)}"></div>
        <div class="modal-buttons"><button class="btn btn-danger" onclick="deleteShape(${shape.id})">🗑 Excluir</button><button class="btn btn-secondary" onclick="duplicateShape(${shape.id})">📋 Duplicar</button></div>
    `;
    document.getElementById('shape-stroke')?.addEventListener('change', (e) => { shape.strokeColor = e.target.value; saveUserData(); });
    document.getElementById('shape-linewidth')?.addEventListener('change', (e) => { shape.lineWidth = parseInt(e.target.value); saveUserData(); });
    const rr = document.getElementById('shape-rotation');
    if (rr) rr.oninput = (e) => { shape.rotation = parseInt(e.target.value); saveUserData(); };
    document.getElementById('shape-x')?.addEventListener('change', (e) => {
        const v = parseInt(e.target.value);
        if (shape.type === 'line') { shape.x1 = v; shape.x2 = v + (shape.x2 - shape.x1); } else { shape.x = v; }
        saveUserData();
    });
    document.getElementById('shape-y')?.addEventListener('change', (e) => {
        const v = parseInt(e.target.value);
        if (shape.type === 'line') { shape.y1 = v; shape.y2 = v + (shape.y2 - shape.y1); } else { shape.y = v; }
        saveUserData();
    });
    if (shape.type === 'text') {
        document.getElementById('shape-text')?.addEventListener('change', (e) => { shape.text = e.target.value; saveUserData(); });
        document.getElementById('shape-fontsize')?.addEventListener('change', (e) => { shape.fontSize = parseInt(e.target.value); saveUserData(); });
        document.getElementById('shape-textcolor')?.addEventListener('change', (e) => { shape.textColor = e.target.value; saveUserData(); });
    }
}

function showConnectionProperties(idx) {
    const div = document.getElementById('props-content');
    const conn = connections[idx];
    if (!conn) return;
    const from = components.find(c => c.id === conn.from);
    const to = components.find(c => c.id === conn.to);
    if (!from || !to) return;
    div.innerHTML = `
        <div class="property-group"><label>Conexão</label><input type="text" value="${from.name} → ${to.name}" disabled></div>
        <div class="property-group"><label>Tipo de Cabo</label><select id="conn-cable-type" style="width:100%;padding:8px;background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border-color);border-radius:5px;">${Object.entries(cableColors).map(([k, v]) => `<option value="${k}" ${conn.type === k ? 'selected' : ''}>${v.icon} ${v.name} - ${v.speed}</option>`).join('')}</select></div>
        <div class="modal-buttons"><button class="btn btn-primary" onclick="updateSelectedConnection(${idx})">✅ Atualizar</button><button class="btn btn-danger" onclick="deleteSelectedConnection(${idx})">🗑 Excluir</button></div>
    `;
}

// ---------- SHAPES ----------
function setShapeMode(mode) {
    shapeMode = mode;
    document.querySelectorAll('.shape-btn').forEach(b => b.classList.remove('active'));
    if (event && event.target) event.target.classList.add('active');
    showToast(`Modo: ${getShapeName(mode)}`);
}
function cancelShapeMode() {
    shapeMode = null;
    drawingPreview = null;
    document.querySelectorAll('.shape-btn').forEach(b => b.classList.remove('active'));
    showToast('Modo cancelado');
}
function toggleShapesToolbar() {
    const t = document.getElementById('shapesToolbar');
    t.style.display = t.style.display === 'none' ? 'flex' : 'none';
}
function endShape(start, end, type) {
    if (!start || !end) return;
    const s = { id: Date.now(), type, fillColor: '#f8f9fa', strokeColor: '#005f99', lineWidth: 2, rotation: 0 };
    switch (type) {
        case 'line': s.x1 = start.x; s.y1 = start.y; s.x2 = end.x; s.y2 = end.y; break;
        case 'door': s.x = end.x; s.y = end.y; break;
        case 'window': s.x = Math.min(start.x, end.x); s.y = Math.min(start.y, end.y); s.width = Math.abs(end.x - start.x); s.height = 40; break;
        case 'text':
            const txt = prompt('Digite o texto:', 'Texto');
            if (txt) { s.text = txt; s.x = end.x; s.y = end.y; s.fontSize = 14; s.textColor = '#212529'; }
            else return;
            break;
    }
    shapes.push(s);
    showToast(`✅ ${getShapeName(type)} adicionado!`);
    saveUserData();
}
function getShapeName(m) { return { line: 'Linha', door: 'Porta', window: 'Janela', text: 'Texto' }[m] || m; }
function showShapeDeleteButton(shape) {
    const btn = document.getElementById('deleteShapeBtn');
    if (!btn || !shape) return;
    const cr = canvas.getBoundingClientRect();
    let x, y;
    if (shape.type === 'line') { x = (shape.x1 + shape.x2) / 2; y = (shape.y1 + shape.y2) / 2; }
    else if (shape.type === 'text') { x = shape.x; y = shape.y; }
    else { x = shape.x + 15; y = shape.y + 25; }
    btn.style.left = (cr.left + x * zoom - 60) + 'px';
    btn.style.top = (cr.top + y * zoom - 30) + 'px';
    btn.style.display = 'block';
}

// ---------- CONTEXT MENUS ----------
function showContextMenu(e, comp) {
    contextMenuComponent = comp;
    const menu = document.getElementById('contextMenu');
    menu.innerHTML = `<div class="context-menu-item" onclick="accessDeviceFromMenu()">🌐 Acessar</div><div class="context-menu-item" onclick="copyIpFromMenu()">📋 Copiar IP</div><div class="context-menu-item" onclick="rotateLeftFromMenu()">🔄 Girar Esq.</div><div class="context-menu-item" onclick="rotateRightFromMenu()">🔄 Girar Dir.</div><div class="context-menu-item" onclick="flipComponentFromMenu()">🔁 Inverter</div><div class="context-menu-item" onclick="deleteComponentFromMenu()">🗑 Remover</div><div class="context-menu-item" onclick="duplicateComponentFromMenu()">📋 Duplicar</div>`;
    menu.style.display = 'block';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';
    setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', { once: true }), 100);
}
function showShapeContextMenu(e, shape) {
    contextMenuShape = shape;
    const menu = document.getElementById('contextMenu');
    menu.innerHTML = `<div class="context-menu-item" onclick="editShapeFromMenu()">✏️ Editar</div><div class="context-menu-item" onclick="rotateShapeLeftFromMenu()">🔄 Girar Esq.</div><div class="context-menu-item" onclick="rotateShapeRightFromMenu()">🔄 Girar Dir.</div><div class="context-menu-item" onclick="flipShapeFromMenu()">🔁 Inverter</div><div class="context-menu-item" onclick="deleteShapeFromMenu()">🗑 Excluir</div><div class="context-menu-item" onclick="duplicateShapeFromMenu()">📋 Duplicar</div>`;
    menu.style.display = 'block';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';
    setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', { once: true }), 100);
}
function showConnectionContextMenu(e, conn, idx) {
    contextMenuConnection = { conn, idx };
    const menu = document.getElementById('contextMenu');
    menu.innerHTML = `<div class="context-menu-item" onclick="editConnectionFromMenu()">✏️ Editar</div><div class="context-menu-item" onclick="deleteConnectionFromMenu()">🗑 Excluir</div>`;
    menu.style.display = 'block';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';
    setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', { once: true }), 100);
}

// ---------- CONTEXT MENU ACTIONS ----------
window.accessDeviceFromMenu = () => { if (contextMenuComponent) accessDevice(contextMenuComponent); document.getElementById('contextMenu').style.display = 'none'; };
window.copyIpFromMenu = () => {
    if (contextMenuComponent && contextMenuComponent.ip) {
        navigator.clipboard.writeText(contextMenuComponent.ip);
        showToast(`📋 IP copiado: ${contextMenuComponent.ip}`);
    } else showToast('Nenhum IP configurado');
    document.getElementById('contextMenu').style.display = 'none';
};
window.rotateLeftFromMenu = () => { if (contextMenuComponent) rotateComponent(contextMenuComponent, -15); document.getElementById('contextMenu').style.display = 'none'; };
window.rotateRightFromMenu = () => { if (contextMenuComponent) rotateComponent(contextMenuComponent, 15); document.getElementById('contextMenu').style.display = 'none'; };
window.flipComponentFromMenu = () => { if (contextMenuComponent) flipComponent(contextMenuComponent); document.getElementById('contextMenu').style.display = 'none'; };
window.deleteComponentFromMenu = () => {
    if (contextMenuComponent) {
        connections = connections.filter(c => c.from !== contextMenuComponent.id && c.to !== contextMenuComponent.id);
        components = components.filter(c => c.id !== contextMenuComponent.id);
        selectedComponents = selectedComponents.filter(c => c.id !== contextMenuComponent.id);
        showProperties(null);
        showToast(`🗑 Removido`);
        saveUserData();
    }
    document.getElementById('contextMenu').style.display = 'none';
};
window.duplicateComponentFromMenu = () => {
    if (contextMenuComponent) {
        const n = JSON.parse(JSON.stringify(contextMenuComponent));
        n.id = Date.now();
        n.x += 30; n.y += 30;
        components.push(n);
        showToast(`📋 Duplicado`);
        saveUserData();
    }
    document.getElementById('contextMenu').style.display = 'none';
};
window.editShapeFromMenu = () => { if (contextMenuShape) { showShapeProperties(contextMenuShape); openProperties(); } document.getElementById('contextMenu').style.display = 'none'; };
window.rotateShapeLeftFromMenu = () => { if (contextMenuShape && (contextMenuShape.type === 'door' || contextMenuShape.type === 'window')) { contextMenuShape.rotation = (contextMenuShape.rotation || 0) - 15; saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
window.rotateShapeRightFromMenu = () => { if (contextMenuShape && (contextMenuShape.type === 'door' || contextMenuShape.type === 'window')) { contextMenuShape.rotation = (contextMenuShape.rotation || 0) + 15; saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
window.flipShapeFromMenu = () => {
    if (contextMenuShape) {
        if (contextMenuShape.type === 'line') {
            const tx = contextMenuShape.x1, ty = contextMenuShape.y1;
            contextMenuShape.x1 = contextMenuShape.x2; contextMenuShape.y1 = contextMenuShape.y2;
            contextMenuShape.x2 = tx; contextMenuShape.y2 = ty;
        } else {
            contextMenuShape.rotation = (contextMenuShape.rotation || 0) + 180;
        }
        saveUserData();
    }
    document.getElementById('contextMenu').style.display = 'none';
};
window.deleteShapeFromMenu = () => {
    if (contextMenuShape) {
        shapes = shapes.filter(s => s.id !== contextMenuShape.id);
        selectedShapes = selectedShapes.filter(s => s.id !== contextMenuShape.id);
        showProperties(null);
        document.getElementById('deleteShapeBtn').style.display = 'none';
        showToast('🗑 Removida');
        saveUserData();
    }
    document.getElementById('contextMenu').style.display = 'none';
};
window.duplicateShapeFromMenu = () => {
    if (contextMenuShape) {
        const n = JSON.parse(JSON.stringify(contextMenuShape));
        n.id = Date.now();
        if (n.type === 'line') { n.x1 += 30; n.y1 += 30; n.x2 += 30; n.y2 += 30; }
        else { n.x += 30; n.y += 30; }
        shapes.push(n);
        saveUserData();
    }
    document.getElementById('contextMenu').style.display = 'none';
};
window.editConnectionFromMenu = () => { if (contextMenuConnection) { selectedConnectionIndex = contextMenuConnection.idx; showConnectionProperties(selectedConnectionIndex); openProperties(); } document.getElementById('contextMenu').style.display = 'none'; };
window.deleteConnectionFromMenu = () => { if (contextMenuConnection) { connections.splice(contextMenuConnection.idx, 1); selectedConnectionIndex = null; showToast('Conexão removida'); saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };

// ---------- PUBLIC ACTIONS ----------
function rotateComponent(comp, angle) { comp.rotation = (comp.rotation || 0) + angle; }
window.rotateLeft = (id) => { const c = components.find(x => x.id === id); if (c) { rotateComponent(c, -15); saveUserData(); } };
window.rotateRight = (id) => { const c = components.find(x => x.id === id); if (c) { rotateComponent(c, 15); saveUserData(); } };
window.flipComponent = (comp) => { if (comp) { comp.rotation = (comp.rotation || 0) + 180; saveUserData(); } };
window.flipComponentById = (id) => { const c = components.find(x => x.id === id); if (c) flipComponent(c); };
window.flipShape = (id) => {
    const s = shapes.find(x => x.id === id);
    if (!s) return;
    if (s.type === 'door' || s.type === 'window') s.rotation = (s.rotation || 0) + 180;
    else if (s.type === 'line') {
        const tx = s.x1, ty = s.y1;
        s.x1 = s.x2; s.y1 = s.y2; s.x2 = tx; s.y2 = ty;
    }
    saveUserData();
};
window.duplicateShape = (id) => {
    const s = shapes.find(x => x.id === id);
    if (!s) return;
    const n = JSON.parse(JSON.stringify(s));
    n.id = Date.now();
    if (n.type === 'line') { n.x1 += 30; n.y1 += 30; n.x2 += 30; n.y2 += 30; }
    else { n.x += 30; n.y += 30; }
    shapes.push(n);
    saveUserData();
};
window.deleteShape = (id) => {
    shapes = shapes.filter(s => s.id !== id);
    selectedShapes = selectedShapes.filter(s => s.id !== id);
    showProperties(null);
    document.getElementById('deleteShapeBtn').style.display = 'none';
    saveUserData();
};
window.deleteSelectedShape = () => {
    if (selectedShapes.length > 0) {
        const id = selectedShapes[0].id;
        shapes = shapes.filter(s => s.id !== id);
        selectedShapes = [];
        showProperties(null);
        closeProperties();
        document.getElementById('deleteShapeBtn').style.display = 'none';
        saveUserData();
    }
};
window.deleteComponent = (id) => {
    if (confirm('Remover este equipamento?')) {
        connections = connections.filter(c => c.from !== id && c.to !== id);
        components = components.filter(c => c.id !== id);
        selectedComponents = selectedComponents.filter(c => c.id !== id);
        showProperties(null);
        closeProperties();
        saveUserData();
    }
};
window.deleteSelectedItems = () => {
    if (selectedComponents.length === 0 && selectedShapes.length === 0 && selectedConnectionIndex === null) {
        showToast('⚠️ Nenhum item selecionado');
        return;
    }
    if (confirm('Excluir itens selecionados?')) {
        const ids = selectedComponents.map(c => c.id);
        connections = connections.filter(c => !ids.includes(c.from) && !ids.includes(c.to));
        if (selectedConnectionIndex !== null) { connections.splice(selectedConnectionIndex, 1); selectedConnectionIndex = null; }
        components = components.filter(c => !ids.includes(c.id));
        const sids = selectedShapes.map(s => s.id);
        shapes = shapes.filter(s => !sids.includes(s.id));
        selectedComponents = [];
        selectedShapes = [];
        showProperties(null);
        closeProperties();
        document.getElementById('deleteShapeBtn').style.display = 'none';
        saveUserData();
    }
};
function accessDevice(comp) {
    if (comp && comp.ip && comp.ip.trim()) {
        let url = comp.ip;
        if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'http://' + url;
        if (comp.port && comp.port !== 80) url += ':' + comp.port;
        window.open(url, '_blank');
        showToast(`🌐 Abrindo ${comp.name}`);
    } else if (comp) {
        showToast(`⚠️ "${comp.name}" sem IP configurado`);
    }
}
window.accessDeviceById = (id) => { const c = components.find(x => x.id === id); if (c) accessDevice(c); };
window.updateSelectedConnection = (idx) => {
    const t = document.getElementById('conn-cable-type').value;
    connections[idx].type = t;
    selectedConnectionIndex = null;
    showProperties(null);
    closeProperties();
    showToast(`✅ Conexão atualizada`);
    saveUserData();
};
window.deleteSelectedConnection = (idx) => {
    if (confirm('Excluir esta conexão?')) {
        connections.splice(idx, 1);
        selectedConnectionIndex = null;
        showProperties(null);
        closeProperties();
        saveUserData();
    }
};
window.addConnection = (fromId) => {
    const toId = document.getElementById('prop-connect').value;
    const cableType = document.getElementById('prop-cable-type').value;
    if (toId) {
        connections.push({ from: fromId, to: parseInt(toId), type: cableType });
        const info = cableColors[cableType];
        showToast(`✅ Conexão ${info ? info.name : cableType.toUpperCase()} adicionada!`);
        saveUserData();
    } else showToast('⚠️ Selecione um equipamento');
};

// ---------- CABLE MODAL ----------
function showCableModal(from, to) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🔌 Tipo de Conexão</h3><p>De: ${from.name}</p><p>Para: ${to.name}</p><select id="cableSelect" style="width:100%;padding:8px;margin:10px 0;background:var(--bg-tertiary);color:var(--text-primary);border:none;border-radius:5px;">${Object.entries(cableColors).map(([k, v]) => `<option value="${k}">${v.icon} ${v.name} - ${v.speed}</option>`).join('')}</select><div class="modal-buttons"><button class="btn btn-primary" onclick="confirmConnection(${from.id}, ${to.id})">✅ Conectar</button><button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
}
window.confirmConnection = (fromId, toId) => {
    const t = document.getElementById('cableSelect').value;
    connections.push({ from: fromId, to: toId, type: t });
    if (window.currentModal) { document.body.removeChild(window.currentModal); window.currentModal = null; }
    const info = cableColors[t];
    showToast(`✅ Conexão ${info ? info.name : t} adicionada!`);
    saveUserData();
};

// ---------- DRAG FROM PALETTE ----------
canvas.addEventListener('dragover', (e) => e.preventDefault());
canvas.addEventListener('drop', (e) => {
    e.preventDefault();
    const { x, y } = getMousePos(e);
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    const comp = { id: Date.now(), type: data.type || 'custom', subtype: data.subtype || '', name: data.name, x, y, icon: data.icon || '📦', iconFile: data.iconFile || null, color: data.color || '#005f99', angle: 0, fov: 80, rotation: 0, ip: '', port: 80, username: '', password: '' };
    components.push(comp);
    showToast(`✅ ${comp.name} adicionado!`);
    saveUserData();
});

// Mouse / touch bindings
canvas.addEventListener('touchstart', handleStart, { passive: false });
canvas.addEventListener('touchmove', handleMove, { passive: false });
canvas.addEventListener('touchend', handleEnd);
canvas.addEventListener('touchcancel', handleEnd);
canvas.addEventListener('mousedown', handleStart);
canvas.addEventListener('mousemove', handleMove);
canvas.addEventListener('mouseup', handleEnd);
canvas.addEventListener('click', handleClick);
canvas.addEventListener('contextmenu', handleContextMenu);

// ---------- PROJECT / FILE ----------
function newProject() {
    if (confirm('Novo projeto? Dados não salvos serão perdidos.')) {
        components = []; connections = []; shapes = [];
        selectedComponents = []; selectedShapes = []; selectedConnectionIndex = null;
        backgroundImage = null; backgroundImageObj = null;
        backgroundOpacity = 0.8; backgroundWidth = 0; backgroundHeight = 0;
        backgroundX = 0; backgroundY = 0; isBackgroundSelected = false;
        closeProperties();
        saveUserData();
        showToast('📁 Novo projeto criado!');
    }
}
function saveProjectToFile() {
    const p = {
        components, connections, shapes,
        background: backgroundImage, backgroundOpacity, backgroundWidth, backgroundHeight, backgroundX, backgroundY,
        version: '2.4', date: new Date().toISOString()
    };
    const blob = new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `projeto_${Date.now()}.projetize`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('✅ Projeto salvo!');
}
function loadProjectFromFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.projetize,.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const data = JSON.parse(ev.target.result);
                components = data.components || [];
                connections = data.connections || [];
                shapes = data.shapes || [];
                if (data.background) {
                    backgroundImage = data.background;
                    backgroundOpacity = data.backgroundOpacity || 0.8;
                    backgroundWidth = data.backgroundWidth || 0;
                    backgroundHeight = data.backgroundHeight || 0;
                    backgroundX = data.backgroundX || 0;
                    backgroundY = data.backgroundY || 0;
                    backgroundImageObj = new Image();
                    backgroundImageObj.src = backgroundImage;
                }
                selectedComponents = [];
                selectedShapes = [];
                selectedConnectionIndex = null;
                closeProperties();
                saveUserData();
                showToast('✅ Projeto carregado!');
            } catch (err) {
                showToast('Erro: ' + err.message);
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

// ---------- EXPORTS ----------
function exportPDF() {
    drawWithBackground(true, true);
    setTimeout(() => {
        const imgData = canvas.toDataURL('image/png');
        const w = window.open('', '_blank');
        w.document.write(`<html><head><title>Projeto CFTV</title></head><body style="margin:0;padding:20px;display:flex;justify-content:center;background:white;"><img src="${imgData}" style="max-width:100%;height:auto;"><script>window.print();<\\/script></body></html>`);
        setTimeout(() => draw(), 500);
        showToast('📄 PDF gerado!');
    }, 100);
}
function exportPDFWithList() {
    drawWithBackground(true, true);
    let list = `<div style="font-family:Arial;padding:20px;"><h1 style="color:#005f99;text-align:center;">PROJETIZE - EQUIPAMENTOS</h1><hr><p><strong>Data:</strong> ${new Date().toLocaleString()}</p><br>`;
    const byType = {};
    components.forEach(c => { const t = c.type || 'custom'; if (!byType[t]) byType[t] = []; byType[t].push(c); });
    for (const [t, list2] of Object.entries(byType)) {
        list += `<h2>📌 ${t.toUpperCase()}</h2><table style="width:100%;border-collapse:collapse;"><tr style="background:#005f99;color:white;"><th style="padding:8px;text-align:left;">Equipamento</th><th style="padding:8px;text-align:left;">IP</th><th style="padding:8px;text-align:left;">Posição</th></tr>`;
        list2.forEach(c => { list += `<tr><td style="padding:8px;">✅ ${c.name}</td><td style="padding:8px;">${c.ip || '-'}</td><td style="padding:8px;">X: ${Math.round(c.x)}, Y: ${Math.round(c.y)}</td></tr>`; });
        list += '</table>';
    }
    if (connections.length > 0) {
        list += `<h2>🔌 CONEXÕES</h2><table style="width:100%;border-collapse:collapse;"><tr style="background:#005f99;color:white;"><th style="padding:8px;">Origem</th><th style="padding:8px;">Destino</th><th style="padding:8px;">Tipo</th></tr>`;
        connections.forEach(conn => {
            const from = components.find(c => c.id === conn.from);
            const to = components.find(c => c.id === conn.to);
            const info = cableColors[conn.type] || cableColors['cat6'];
            if (from && to) list += `<tr><td style="padding:8px;">${from.name}</td><td style="padding:8px;">${to.name}</td><td style="padding:8px;">${info.name}</td></tr>`;
        });
        list += '</table>';
    }
    list += `<br><hr><p><strong>Total:</strong> ${components.length} equipamentos · ${connections.length} conexões · ${shapes.length} formas</p><p style="text-align:center;font-size:11px;color:#888;">Desenvolvido por Thiago Souza</p></div>`;
    const img = canvas.toDataURL('image/png');
    const w = window.open('', '_blank');
    w.document.write(`<html><head><title>Projeto Completo</title><style>@media print{.page-break{page-break-before:always;}}</style></head><body style="margin:0;padding:20px;"><div style="text-align:center;"><img src="${img}" style="max-width:100%;"></div><div class="page-break"></div>${list}<script>window.print();<\\/script></body></html>`);
    setTimeout(() => draw(), 500);
    showToast('📄 PDF completo!');
}
function generateBudget() {
    let t = '📋 LISTA DE EQUIPAMENTOS\n' + '='.repeat(50) + '\n\nData: ' + new Date().toLocaleString() + '\n\n';
    const byType = {};
    components.forEach(c => { const ty = c.type || 'custom'; if (!byType[ty]) byType[ty] = []; byType[ty].push(c); });
    for (const [ty, arr] of Object.entries(byType)) {
        t += `\n📌 ${ty.toUpperCase()}:\n${'-'.repeat(30)}\n`;
        arr.forEach(c => { t += `   ✅ ${c.name}`; if (c.ip) t += ` (IP: ${c.ip})`; t += '\n'; });
    }
    t += `\n📡 CONEXÕES:\n${'-'.repeat(30)}\n`;
    connections.forEach(conn => {
        const from = components.find(c => c.id === conn.from);
        const to = components.find(c => c.id === conn.to);
        const info = cableColors[conn.type] || cableColors['cat6'];
        if (from && to) t += `   🔗 ${from.name} → ${to.name} (${info.name})\n`;
    });
    t += `\n${'='.repeat(50)}\n📊 TOTAL: ${components.length} equip · ${connections.length} conex · ${shapes.length} formas\n`;
    const blob = new Blob([t], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `orcamento_${Date.now()}.txt`;
    a.click();
    showToast('💰 Orçamento gerado!');
}

// ---------- LOGIN ----------
async function loadLoginBgConfig() {
    try {
        const r = await fetch('/api/login_bg_config');
        const d = await r.json();
        if (d.success) { loginBgConfig = d.config; applyLoginBg(); }
    } catch(e) { console.error(e); }
}

function applyLoginBg() {
    const imgEl = document.getElementById('loginBgMedia');
    const vidEl = document.getElementById('loginBgVideo');
    const mtxEl = document.getElementById('matrixBg');
    imgEl.style.display = 'none'; vidEl.style.display = 'none';
    imgEl.src = ''; vidEl.src = '';
    mtxEl.style.display = 'block';

    if (loginBgConfig.type === 'image' && loginBgConfig.filename) {
        imgEl.src = `/uploads/login_bg/${loginBgConfig.filename}?t=${Date.now()}`;
        imgEl.style.display = 'block';
        imgEl.style.opacity = loginBgConfig.opacity || 0.35;
        mtxEl.style.display = 'none';
    } else if (loginBgConfig.type === 'video' && loginBgConfig.filename) {
        vidEl.src = `/uploads/login_bg/${loginBgConfig.filename}?t=${Date.now()}`;
        vidEl.style.display = 'block';
        vidEl.style.opacity = loginBgConfig.opacity || 0.35;
        vidEl.play().catch(() => {});
        mtxEl.style.display = 'none';
    } else {
        createMatrixAnimation('matrixBg', true);
        mtxEl.style.display = 'block';
    }
}

function createMatrixAnimation(containerId, isLogin = false) {
    const c = document.getElementById(containerId);
    if (!c) return;
    c.innerHTML = '';
    const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
    const cols = Math.floor(window.innerWidth / 20);
    for (let i = 0; i < cols; i++) {
        const col = document.createElement('div');
        col.className = 'matrix-column';
        col.style.left = (i * 20) + 'px';
        col.style.animationDuration = (Math.random() * 5 + 5) + 's';
        col.style.animationDelay = (Math.random() * 5) + 's';
        let txt = '';
        for (let j = 0; j < 40; j++) txt += chars[Math.floor(Math.random() * chars.length)] + '\n';
        col.textContent = txt;
        c.appendChild(col);
    }
}

function openLoginBgModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content" style="max-width:560px;">
            <h3 style="color:var(--text-accent);">🎬 Fundo da Tela de Login</h3>
            <p style="font-size:12px;color:#6c757d;margin-bottom:15px;">Personalize com imagem, GIF ou vídeo.</p>
            <div class="background-controls">
                <label><strong>📁 Escolher mídia</strong></label>
                <input type="file" id="loginBgFileInput" accept="image/*,video/mp4,video/webm,video/ogg">
                <div class="image-preview" id="loginBgPreview"></div>
            </div>
            <div class="background-controls">
                <label><strong>🎨 Opacidade</strong></label>
                <input type="range" id="loginBgOpacityRange" min="0.05" max="1" step="0.05" value="${loginBgConfig.opacity || 0.35}" oninput="document.getElementById('loginBgOpacityVal').innerText=Math.round(this.value*100)+'%'">
                <span id="loginBgOpacityVal">${Math.round((loginBgConfig.opacity || 0.35)*100)}%</span>
            </div>
            <div class="background-controls">
                <label><strong>🔢 Voltar para Matrix</strong></label>
                <button class="btn btn-secondary" onclick="setLoginBgMatrix()" style="width:100%;">🔢 Restaurar Matrix</button>
            </div>
            <div class="modal-buttons">
                <button class="btn btn-primary" onclick="uploadLoginBgMedia()">✅ Aplicar</button>
                <button class="btn btn-danger" onclick="closeModal()">❌ Fechar</button>
            </div>
        </div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;

    const input = document.getElementById('loginBgFileInput');
    if (input) input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const prev = document.getElementById('loginBgPreview');
        const url = URL.createObjectURL(file);
        if (file.type.startsWith('video/')) prev.innerHTML = `<video src="${url}" style="max-width:100%;max-height:150px;border-radius:6px;" autoplay loop muted playsinline></video>`;
        else prev.innerHTML = `<img src="${url}" style="max-width:100%;max-height:150px;border-radius:6px;">`;
        window.tempLoginBgFile = file;
    };
}

window.setLoginBgMatrix = async () => {
    try {
        const r = await fetch('/api/login_bg_config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'matrix' }) });
        const d = await r.json();
        if (d.success) { loginBgConfig = d.config; applyLoginBg(); showToast('✅ Matrix restaurado!'); closeModal(); }
    } catch(e) { showToast('❌ Erro'); }
};

window.uploadLoginBgMedia = async () => {
    if (!window.tempLoginBgFile) { showToast('⚠️ Selecione uma mídia'); return; }
    const file = window.tempLoginBgFile;
    if (file.size > 40 * 1024 * 1024) { showToast('⚠️ Máximo 40MB'); return; }
    showToast('📤 Enviando...');
    try {
        const base64 = await readImageAsBase64(file);
        const type = file.type.startsWith('video/') ? 'video' : 'image';
        const opacity = parseFloat(document.getElementById('loginBgOpacityRange').value) || 0.35;
        const r = await fetch('/api/upload_login_bg', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ media: base64, type, opacity }) });
        const d = await r.json();
        if (d.success) { loginBgConfig = d.config; applyLoginBg(); showToast('✅ Fundo atualizado!'); closeModal(); }
        else showToast('❌ ' + (d.error || 'Erro'));
    } catch(e) { showToast('❌ ' + e.message); }
    window.tempLoginBgFile = null;
};

async function doLogin() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const btn = document.getElementById('loginBtn');
    const err = document.getElementById('loginError');
    err.style.display = 'none';
    if (!username || !password) { err.textContent = 'Preencha usuário e senha'; err.style.display = 'block'; return; }

    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Entrando...';

    try {
        const r = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
        const d = await r.json();
        if (d.success) {
            currentUser = username;
            userRole = d.role;
            if (d.role === 'admin' || d.role === 'master') document.getElementById('loginBgToggle').style.display = 'flex';
            document.getElementById('loginModal').style.display = 'none';
            document.getElementById('loadingOverlay').style.display = 'flex';
            document.getElementById('toolbar').style.display = 'flex';
            document.getElementById('userInfo').innerHTML = `<span>👤 ${username}</span><span class="user-role">${d.role.toUpperCase()}</span>`;

            if (d.role === 'admin' || d.role === 'master') {
                ['adminUsersBtn','adminShapesBtn','adminCategoriesBtn','adminDevicesBtn','adminConnectionsBtn','resetDefaultsBtn','adminDevBtn','adminBgBtn'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.style.display = 'inline-block';
                });
            }

            await Promise.all([loadDefaultConfig(), loadDefaultConnections()]);
            await loadUserData();

            document.getElementById('loadingOverlay').style.display = 'none';
            showToast(`Bem-vindo, ${username}!`);
        } else {
            err.textContent = d.error || 'Credenciais inválidas';
            err.style.display = 'block';
            btn.disabled = false;
            btn.innerHTML = orig;
        }
    } catch(e) {
        err.textContent = 'Erro de conexão';
        err.style.display = 'block';
        btn.disabled = false;
        btn.innerHTML = orig;
    }
}

function logout() { fetch('/api/logout', { method: 'POST' }).then(() => location.reload()); }

// ---------- USER MANAGEMENT ----------
async function openUserManagement() {
    const r = await fetch('/api/users');
    const users = await r.json();
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">👥 Usuários</h3><div class="user-list" id="userList"></div><div style="margin-top:15px;"><input type="text" id="newUsername" placeholder="Usuário"><input type="password" id="newPassword" placeholder="Senha"><select id="newRole"><option value="viewer">Visualizador</option><option value="admin">Administrador</option></select><button class="btn btn-primary" style="margin-top:10px;" onclick="addUser()">➕ Adicionar</button></div><div class="modal-buttons"><button class="btn btn-danger" onclick="closeModal()">Fechar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
    const list = document.getElementById('userList');
    for (const [u, ud] of Object.entries(users)) {
        const div = document.createElement('div');
        div.className = 'user-item';
        div.innerHTML = `<div><strong>${u}</strong><br><small>${ud.role} | ${new Date(ud.created_at).toLocaleDateString()}</small></div><div class="user-actions">${ud.role !== 'master' ? `<button onclick="deleteUser('${u}')" title="Excluir">🗑</button>` : '<span style="color:var(--text-accent);">Master</span>'}</div>`;
        list.appendChild(div);
    }
}
window.addUser = async () => {
    const username = document.getElementById('newUsername').value;
    const password = document.getElementById('newPassword').value;
    const role = document.getElementById('newRole').value;
    if (!username || !password) { showToast('Preencha todos os campos'); return; }
    const r = await fetch('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password, role }) });
    const d = await r.json();
    if (d.success) { showToast('✅ Usuário adicionado'); closeModal(); openUserManagement(); }
    else showToast(d.error);
};
window.deleteUser = async (u) => {
    if (!confirm(`Excluir usuário "${u}"?`)) return;
    const r = await fetch(`/api/users/${u}`, { method: 'DELETE' });
    const d = await r.json();
    if (d.success) { showToast('✅ Excluído'); closeModal(); openUserManagement(); }
    else showToast(d.error);
};

// ---------- CATEGORY/DEVICE/CONNECTION ADMIN MODALS ----------
function openAddCategoryModal() {
    if (userRole !== 'admin' && userRole !== 'master') return;
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">📁 Nova Categoria</h3><input type="text" id="catName" placeholder="Nome"><input type="text" id="catIcon" placeholder="Ícone" value="📁"><div class="modal-buttons"><button class="btn btn-primary" onclick="addCategory()">Adicionar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
}
window.addCategory = () => {
    const name = document.getElementById('catName')?.value;
    const icon = document.getElementById('catIcon')?.value;
    if (!name) { showToast('Digite um nome'); return; }
    if (categories[name]) { showToast('Já existe'); return; }
    categories[name] = { icon: icon || '📁', devices: [] };
    saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    showToast(`✅ "${name}" adicionada!`);
};
window.editCategory = (catName) => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    const cd = categories[catName];
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">✏️ Editar Categoria</h3><input type="text" id="catName" value="${catName}"><input type="text" id="catIcon" value="${cd.icon || '📁'}"><div class="modal-buttons"><button class="btn btn-primary" onclick="updateCategory('${catName.replace(/'/g, "\\'")}')">Salvar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
};
window.updateCategory = (oldName) => {
    const newName = document.getElementById('catName')?.value;
    const icon = document.getElementById('catIcon')?.value;
    if (!newName) return;
    const data = categories[oldName];
    delete categories[oldName];
    categories[newName] = { ...data, icon };
    saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    showToast('✅ Atualizada');
};
window.deleteCategory = (catName) => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    if (!confirm(`Excluir "${catName}"?`)) return;
    delete categories[catName];
    saveUserData(); saveGlobalLibrary(); renderPalette();
    showToast('🗑 Removida');
};
window.addDeviceToCategory = (catName) => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">➕ Novo em ${catName}</h3><input type="text" id="devName" placeholder="Nome"><input type="text" id="devIcon" placeholder="Ícone" value="📦"><input type="text" id="devDesc" placeholder="Descrição"><input type="color" id="devColor" value="#005f99"><input type="text" id="devType" placeholder="Tipo (ex: switch, camera)"><div class="modal-buttons"><button class="btn btn-primary" onclick="addDevice('${catName.replace(/'/g, "\\'")}')">Adicionar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
};
window.addDevice = (catName) => {
    const name = document.getElementById('devName')?.value;
    const icon = document.getElementById('devIcon')?.value;
    const desc = document.getElementById('devDesc')?.value;
    const color = document.getElementById('devColor')?.value;
    const type = document.getElementById('devType')?.value;
    if (!name) { showToast('Digite um nome'); return; }
    categories[catName].devices.push({ name, icon: icon || '📦', desc: desc || '', type: type || 'custom', color: color || '#005f99', iconFile: null });
    saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    showToast(`✅ "${name}" adicionado!`);
};
window.editDevice = (catName, idx) => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    const d = categories[catName].devices[idx];
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">✏️ Editar</h3><input type="text" id="devName" value="${(d.name || '').replace(/"/g, '&quot;')}"><input type="text" id="devIcon" value="${d.icon || '📦'}"><input type="text" id="devDesc" value="${d.desc || ''}"><input type="color" id="devColor" value="${d.color || '#005f99'}"><input type="text" id="devType" value="${d.type || 'custom'}"><div class="modal-buttons"><button class="btn btn-primary" onclick="updateDevice('${catName.replace(/'/g, "\\'")}', ${idx})">Salvar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
};
window.updateDevice = (catName, idx) => {
    const name = document.getElementById('devName')?.value;
    const icon = document.getElementById('devIcon')?.value;
    const desc = document.getElementById('devDesc')?.value;
    const color = document.getElementById('devColor')?.value;
    const type = document.getElementById('devType')?.value;
    if (!name) return;
    categories[catName].devices[idx] = { ...categories[catName].devices[idx], name, icon: icon || '📦', desc: desc || '', color, type };
    saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    showToast('✅ Atualizado');
};
window.deleteDevice = (catName, idx) => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    if (!confirm('Excluir este dispositivo?')) return;
    categories[catName].devices.splice(idx, 1);
    saveUserData(); saveGlobalLibrary(); renderPalette();
    showToast('🗑 Removido');
};
window.openAddDeviceModal = () => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🔧 Novo Equipamento</h3><input type="text" id="devName" placeholder="Nome"><input type="text" id="devIcon" placeholder="Ícone" value="📦"><input type="text" id="devDesc" placeholder="Descrição"><input type="color" id="devColor" value="#005f99"><input type="text" id="devType" placeholder="Tipo"><div class="modal-buttons"><button class="btn btn-primary" onclick="addCustomDevice()">Adicionar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
};
window.addCustomDevice = () => {
    const name = document.getElementById('devName')?.value;
    const icon = document.getElementById('devIcon')?.value;
    const desc = document.getElementById('devDesc')?.value;
    const color = document.getElementById('devColor')?.value;
    const type = document.getElementById('devType')?.value;
    if (!name) return;
    customDevices.push({ id: Date.now(), name, icon: icon || '📦', desc: desc || '', color: color || '#005f99', type: type || 'custom', iconFile: null });
    saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    showToast(`✅ "${name}" adicionado!`);
};
window.editCustomDevice = (idx) => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    const d = customDevices[idx];
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">✏️ Editar</h3><input type="text" id="devName" value="${(d.name || '').replace(/"/g, '&quot;')}"><input type="text" id="devIcon" value="${d.icon || '📦'}"><input type="text" id="devDesc" value="${d.desc || ''}"><input type="color" id="devColor" value="${d.color || '#005f99'}"><input type="text" id="devType" value="${d.type || 'custom'}"><div class="modal-buttons"><button class="btn btn-primary" onclick="updateCustomDevice(${idx})">Salvar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
};
window.updateCustomDevice = (idx) => {
    const name = document.getElementById('devName')?.value;
    const icon = document.getElementById('devIcon')?.value;
    const desc = document.getElementById('devDesc')?.value;
    const color = document.getElementById('devColor')?.value;
    const type = document.getElementById('devType')?.value;
    if (!name) return;
    customDevices[idx] = { ...customDevices[idx], name, icon, desc, color, type };
    saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    showToast('✅ Atualizado');
};
window.deleteCustomDevice = (idx) => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    if (!confirm('Excluir?')) return;
    customDevices.splice(idx, 1);
    saveUserData(); saveGlobalLibrary(); renderPalette();
    showToast('🗑 Removido');
};
window.openAddConnectionModal = () => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🔌 Nova Conexão</h3><input type="text" id="connName" placeholder="Nome"><input type="text" id="connIcon" placeholder="Ícone" value="🔌"><input type="color" id="connColor" value="#005f99"><input type="text" id="connSpeed" placeholder="Velocidade" value="N/A"><input type="text" id="connDesc" placeholder="Descrição"><select id="connType"><option value="cable">Cabeado</option><option value="wireless">Sem Fio</option></select><select id="connCategory"><option value="Cabeadas">Cabeadas</option><option value="Sem Fio">Sem Fio</option><option value="Personalizadas">Personalizadas</option></select><div class="modal-buttons"><button class="btn btn-primary" onclick="addConnectionFromModal()">Adicionar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
};
window.addConnectionFromModal = () => {
    const name = document.getElementById('connName')?.value;
    const icon = document.getElementById('connIcon')?.value;
    const color = document.getElementById('connColor')?.value;
    const speed = document.getElementById('connSpeed')?.value;
    const desc = document.getElementById('connDesc')?.value;
    const type = document.getElementById('connType')?.value;
    const cat = document.getElementById('connCategory')?.value;
    if (!name) { showToast('Digite um nome'); return; }
    if (!connectionCategories[cat]) connectionCategories[cat] = { icon: '🔌', connections: [] };
    const connData = { name, icon: icon || '🔌', color, speed: speed || 'N/A', desc: desc || '', type, animation: null, iconFile: null };
    connectionCategories[cat].connections.push(connData);
    cableColors[getConnectionKey(name)] = { ...connData };
    saveUserData(); saveGlobalLibrary(); closeModal(); renderConnectionsPalette();
    showToast(`✅ "${name}" adicionada!`);
};
window.addConnectionToCategory = (cat) => openAddConnectionModal();
window.editCustomConnection = (cat, idx) => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    const c = connectionCategories[cat].connections[idx];
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">✏️ Editar Conexão</h3><input type="text" id="connName" value="${(c.name || '').replace(/"/g, '&quot;')}"><input type="text" id="connIcon" value="${c.icon || '🔌'}"><input type="color" id="connColor" value="${c.color || '#005f99'}"><input type="text" id="connSpeed" value="${c.speed || 'N/A'}"><input type="text" id="connDesc" value="${c.desc || ''}"><select id="connType"><option value="cable" ${c.type === 'cable' ? 'selected' : ''}>Cabeado</option><option value="wireless" ${c.type === 'wireless' ? 'selected' : ''}>Sem Fio</option></select><div class="modal-buttons"><button class="btn btn-primary" onclick="updateCustomConnection('${cat.replace(/'/g, "\\'")}', ${idx})">Salvar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
};
window.updateCustomConnection = (cat, idx) => {
    const name = document.getElementById('connName')?.value;
    const icon = document.getElementById('connIcon')?.value;
    const color = document.getElementById('connColor')?.value;
    const speed = document.getElementById('connSpeed')?.value;
    const desc = document.getElementById('connDesc')?.value;
    const type = document.getElementById('connType')?.value;
    if (!name) return;
    const oldKey = getConnectionKey(connectionCategories[cat].connections[idx].name);
    delete cableColors[oldKey];
    const data = { name, icon, color, speed, desc, type, animation: null, iconFile: connectionCategories[cat].connections[idx].iconFile };
    connectionCategories[cat].connections[idx] = data;
    cableColors[getConnectionKey(name)] = { ...data };
    saveUserData(); saveGlobalLibrary(); closeModal(); renderConnectionsPalette();
    showToast('✅ Atualizada');
};
window.deleteCustomConnection = (cat, idx) => {
    if (userRole !== 'admin' && userRole !== 'master') return;
    if (!confirm('Excluir?')) return;
    const key = getConnectionKey(connectionCategories[cat].connections[idx].name);
    delete cableColors[key];
    connectionCategories[cat].connections.splice(idx, 1);
    if (connectionCategories[cat].connections.length === 0) delete connectionCategories[cat];
    saveUserData(); saveGlobalLibrary(); renderConnectionsPalette();
    showToast('🗑 Removida');
};

// Icon modals
function openCategoryIconModal(catName) {
    if (userRole !== 'admin' && userRole !== 'master') return;
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🎨 Ícone: ${catName}</h3><input type="text" id="catEmoji" value="${categories[catName]?.icon || '📁'}" maxlength="2"><div class="modal-buttons"><button class="btn btn-primary" onclick="applyCategoryIcon('${catName.replace(/'/g, "\\'")}')">✅</button><button class="btn btn-danger" onclick="closeModal()">❌</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
}
window.applyCategoryIcon = (catName) => {
    const emoji = document.getElementById('catEmoji')?.value;
    if (emoji) categories[catName].icon = emoji;
    saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    showToast('✅');
};
window.openCategoryIconModal = openCategoryIconModal;
window.openConnectionIconModal = () => {};
window.applyConnectionIcon = () => {};
window.openDeviceIconModal = () => {};
window.applyDeviceIcon = () => {};
window.openCustomDeviceIconModal = () => {};
window.applyCustomDeviceIcon = () => {};

// ---------- BACKGROUND / PLANTA ----------
function openBackgroundModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🖼️ Planta Baixa</h3><div class="background-controls"><label><strong>📁 Importar Imagem</strong></label><input type="file" id="bgImageUpload" accept="image/*"><div class="image-preview" id="bgPreview"></div><button class="btn btn-primary" style="margin-top:8px;" onclick="importLocalImage()">📤 Importar</button></div><div class="background-controls"><label><strong>🎨 Opacidade</strong></label><input type="range" id="bgOpacity" min="0.1" max="1" step="0.01" value="${backgroundOpacity}" onchange="updateBackgroundOpacity(this.value)"><span id="opacityValue">${Math.round(backgroundOpacity * 100)}%</span></div>${backgroundImage ? `<div class="background-controls"><label><strong>🖼️ Imagem Atual</strong></label><div class="action-buttons"><button class="btn btn-secondary" onclick="selectBackgroundImage()">🔍 Selecionar</button><button class="btn btn-danger" onclick="removeBackground()">🗑 Remover</button></div></div>` : ''}<div class="modal-buttons"><button class="btn btn-danger" onclick="closeModal()">❌ Fechar</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
}
window.importLocalImage = async () => {
    const input = document.getElementById('bgImageUpload');
    const file = input.files[0];
    if (!file) { showToast('Selecione uma imagem'); return; }
    const base64 = await readImageAsBase64(file);
    showToast('📤 Enviando...');
    try {
        const r = await fetch('/api/upload_background', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, name: file.name }) });
        const d = await r.json();
        if (d.success) {
            backgroundImage = d.url;
            backgroundImageObj = new Image();
            backgroundImageObj.onload = function() {
                backgroundWidth = backgroundImageObj.width;
                backgroundHeight = backgroundImageObj.height;
                backgroundX = canvas.width/2 - backgroundWidth/2;
                backgroundY = canvas.height/2 - backgroundHeight/2;
                saveUserData();
                showToast('✅ Planta adicionada!');
                closeModal();
            };
            backgroundImageObj.src = backgroundImage;
        }
    } catch(e) { showToast('Erro'); }
};
window.selectBackgroundImage = () => { isBackgroundSelected = true; closeModal(); showToast('✅ Arraste para mover'); };
window.updateBackgroundOpacity = (v) => { backgroundOpacity = parseFloat(v); document.getElementById('opacityValue').innerText = Math.round(backgroundOpacity * 100) + '%'; saveUserData(); };
window.removeBackground = () => {
    if (confirm('Remover imagem?')) {
        backgroundImage = null; backgroundImageObj = null;
        backgroundOpacity = 0.8; backgroundWidth = 0; backgroundHeight = 0;
        backgroundX = 0; backgroundY = 0; isBackgroundSelected = false;
        saveUserData(); closeModal();
    }
};
window.openBackgroundModal = openBackgroundModal;

// ---------- DEV IMAGE / DYNAMIC BG ----------
function openDevImageModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3>🖼️ Foto do Dev</h3><input type="file" id="newDevImage" accept="image/*"><div class="image-preview" id="newDevPreview"></div><div class="modal-buttons"><button class="btn btn-primary" onclick="uploadNewDevImage()">✅ Salvar</button><button class="btn btn-danger" onclick="closeModal()">❌</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
    const inp = document.getElementById('newDevImage');
    if (inp) inp.onchange = async (e) => {
        const f = e.target.files[0];
        if (f) { const b = await readImageAsBase64(f); document.getElementById('newDevPreview').innerHTML = `<img src="${b}" style="max-width:100px;">`; window.tempDevImage = b; }
    };
}
window.uploadNewDevImage = async () => {
    if (!window.tempDevImage) { showToast('Selecione'); return; }
    try {
        const r = await fetch('/api/upload_dev_image', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: window.tempDevImage }) });
        const d = await r.json();
        if (d.success) { showToast('✅ Atualizada!'); setTimeout(() => location.reload(), 1000); }
    } catch(e) { showToast('Erro'); }
    window.tempDevImage = null;
    closeModal();
};
function openDynamicBgModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content"><h3>🎬 Fundo Dinâmico</h3><input type="file" id="newBgFile" accept="image/gif,video/mp4"><div class="image-preview" id="newBgPreview"></div><div class="modal-buttons"><button class="btn btn-primary" onclick="applyDynamicBg()">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">❌</button></div></div>`;
    document.body.appendChild(modal);
    window.currentModal = modal;
    const inp = document.getElementById('newBgFile');
    if (inp) inp.onchange = (e) => {
        const f = e.target.files[0];
        if (f) {
            const url = URL.createObjectURL(f);
            const prev = document.getElementById('newBgPreview');
            prev.innerHTML = f.type.startsWith('image') ? `<img src="${url}" style="max-width:100px;">` : `<video src="${url}" style="max-width:100px;" autoplay loop muted></video>`;
            window.tempBgFile = f;
        }
    };
}
window.applyDynamicBg = () => {
    if (!window.tempBgFile) { showToast('Selecione um arquivo'); return; }
    const url = URL.createObjectURL(window.tempBgFile);
    if (window.tempBgFile.type.startsWith('image')) {
        document.getElementById('bgVideo').style.display = 'none';
        document.getElementById('bgGif').src = url;
        document.getElementById('bgGif').style.display = 'block';
    } else {
        document.getElementById('bgGif').style.display = 'none';
        document.getElementById('bgVideo').src = url;
        document.getElementById('bgVideo').style.display = 'block';
    }
    showToast('✅ Fundo aplicado!');
    closeModal();
};
window.openDevImageModal = openDevImageModal;
window.openDynamicBgModal = openDynamicBgModal;

// ---------- MISC ----------
function toggleGrid() { showGrid = !showGrid; showToast(showGrid ? '🔲 Grade on' : '🔳 Grade off'); }
async function resetToDefaultConfig() {
    if (!confirm('Restaurar configurações padrão?')) return;
    try {
        const r = await fetch('/api/reset_default_config', { method: 'POST' });
        if ((await r.json()).success) {
            await loadDefaultConfig();
            categories = JSON.parse(JSON.stringify(defaultCategories));
            customDevices = [];
            saveUserData(); saveGlobalLibrary(); renderPalette();
            showToast('✅ Restaurado');
        }
    } catch(e) { showToast('Erro'); }
}

// ---------- INTRO / SLIDER ----------
window.closeIntroAndShowLogin = function() {
    document.getElementById('introScreen').style.display = 'none';
    document.getElementById('loginModal').style.display = 'flex';
    loadLoginBgConfig();
};

function loadDevImages() {
    const loginImg = document.getElementById('loginDevImage');
    const badgeImg = document.getElementById('badgeDevImage');
    const introAvatar = document.getElementById('introDevAvatar');
    const img = new Image();
    img.onload = function() {
        if (loginImg) { loginImg.src = img.src; loginImg.style.display = 'block'; const fb = document.getElementById('loginAvatarFallback'); if (fb) fb.style.display = 'none'; }
        if (badgeImg) badgeImg.src = img.src;
        if (introAvatar) introAvatar.innerHTML = `<img src="${img.src}" style="width:100%;height:100%;object-fit:cover;">`;
    };
    img.src = devImageBase64 ? 'data:image/png;base64,' + devImageBase64 : '/static/dev.png?v=2';
}

// ---------- INIT ----------
(async function init() {
    await loadDefaultConfig();
    await loadDefaultConnections();
    categories = JSON.parse(JSON.stringify(defaultCategories));
    renderPalette();
    renderConnectionsPalette();
})();

loadDevImages();
createMatrixAnimation('matrixBg', true);
closeProperties();
loadLoginBgConfig();
setTimeout(() => { const s = document.getElementById('splashScreen'); if (s) s.style.display = 'none'; }, 3000);

// ---------- EXPORTS 2D ----------
window.newProject = newProject;
window.saveProjectToFile = saveProjectToFile;
window.loadProjectFromFile = loadProjectFromFile;
window.exportPDF = exportPDF;
window.exportPDFWithList = exportPDFWithList;
window.generateBudget = generateBudget;
window.zoomIn = zoomIn;
window.zoomOut = zoomOut;
window.resetZoom = resetZoom;
window.iconZoomIn = iconZoomIn;
window.iconZoomOut = iconZoomOut;
window.resetIconSize = resetIconSize;
window.togglePalette = togglePalette;
window.closeModal = closeModal;
window.openAddCategoryModal = openAddCategoryModal;
window.doLogin = doLogin;
window.logout = logout;
window.openUserManagement = openUserManagement;
window.setShapeMode = setShapeMode;
window.cancelShapeMode = cancelShapeMode;
window.toggleShapesToolbar = toggleShapesToolbar;
window.toggleGrid = toggleGrid;
window.resetToDefaultConfig = resetToDefaultConfig;
window.closePropertiesPanel = closePropertiesPanel;
window.toggleMobilePalette = toggleMobilePalette;
window.closeMobilePalette = closeMobilePalette;
window.openLoginBgModal = openLoginBgModal;
window.loadLoginBgConfig = loadLoginBgConfig;
window.applyLoginBg = applyLoginBg;
window.renderPalette = renderPalette;
window.renderConnectionsPalette = renderConnectionsPalette;

// ==================== FIM DA PARTE 2 ====================
// (A PARTE 3 deve ser colada logo abaixo, dentro da mesma tag <script>)
// ==================== PARTE 3: SIMULADOR 3D COMPLETO ====================
(function() {
    'use strict';

    // ===== CATÁLOGO DE EQUIPAMENTOS 3D =====
    // Cada tipo tem tamanho/formato realista + builder específico
    const DEVICE_CATALOG = {
        // RACK (grandes)
        'router':       { w: 3.2, h: 0.35, d: 2.4, layout: 'rack',     label: 'Router',       builder: 'router' },
        'switch_l2':    { w: 3.2, h: 0.35, d: 2.4, layout: 'rack',     label: 'Switch L2',    builder: 'switch' },
        'switch_l3':    { w: 3.2, h: 0.35, d: 2.4, layout: 'rack',     label: 'Switch L3',    builder: 'switch' },
        'switch_l2_poe':{ w: 3.2, h: 0.35, d: 2.4, layout: 'rack',     label: 'Switch PoE',   builder: 'switch' },
        'switch_l3_poe':{ w: 3.2, h: 0.35, d: 2.4, layout: 'rack',     label: 'Switch PoE',   builder: 'switch' },
        'olt':          { w: 3.2, h: 0.7,  d: 2.4, layout: 'rack',     label: 'OLT GPON',     builder: 'olt' },
        'patch':        { w: 3.2, h: 0.25, d: 0.3, layout: 'rack',     label: 'Patch Panel',  builder: 'patch' },
        'nvr':          { w: 3.2, h: 0.35, d: 2.4, layout: 'rack',     label: 'NVR',          builder: 'nvr' },
        'dvr':          { w: 3.2, h: 0.35, d: 2.4, layout: 'rack',     label: 'DVR',          builder: 'nvr' },
        'pbx':          { w: 3.2, h: 0.7,  d: 2.4, layout: 'rack',     label: 'PABX IP',      builder: 'pbx' },
        'nobreak':      { w: 3.2, h: 1.0,  d: 2.4, layout: 'rack',     label: 'Nobreak',      builder: 'ups' },
        'server':       { w: 3.2, h: 0.7,  d: 2.4, layout: 'rack',     label: 'Servidor',     builder: 'server' },
        'nas':          { w: 3.2, h: 1.0,  d: 2.4, layout: 'rack',     label: 'NAS',          builder: 'nas' },
        // DESKTOP (pequenos)
        'onu':          { w: 1.0, h: 0.2,  d: 0.7, layout: 'desktop',  label: 'ONU',          builder: 'onu' },
        'ont':          { w: 1.0, h: 0.2,  d: 0.7, layout: 'desktop',  label: 'ONT',          builder: 'onu' },
        // WALL (parede - caixas)
        'cto':          { w: 0.7, h: 0.7,  d: 0.2, layout: 'wall',     label: 'CTO',          builder: 'cto' },
        // MINI (muito pequenos)
        'converter':    { w: 0.5, h: 0.12, d: 0.35,layout: 'mini',     label: 'Conversor',    builder: 'converter' },
        // OUTROS
        'camera':       { w: 0.35,h: 0.35, d: 0.35,layout: 'generic',  label: 'Câmera',       builder: 'camera' },
        'sensor':       { w: 0.2, h: 0.2,  d: 0.2, layout: 'generic',  label: 'Sensor',       builder: 'sensor' },
        'telefone_ip':  { w: 0.35,h: 0.25, d: 0.15,layout: 'generic',  label: 'Tel. IP',      builder: 'phone' },
        'telefone_analogico': { w: 0.35, h: 0.25, d: 0.15, layout: 'generic', label: 'Tel. Analógico', builder: 'phone' },
        'ata':          { w: 0.4, h: 0.15, d: 0.25,layout: 'mini',     label: 'ATA',          builder: 'converter' },
        'controle_acesso': { w: 0.4, h: 0.5, d: 0.15, layout: 'generic', label: 'Control. Acesso', builder: 'generic' },
        'fonte_alimentacao': { w: 0.6, h: 0.3, d: 0.35, layout: 'generic', label: 'Fonte',    builder: 'ups' }
    };

    function getCatalog(type) {
        return DEVICE_CATALOG[type] || { w: 0.5, h: 0.35, d: 0.4, layout: 'generic', label: type || 'Dispositivo', builder: 'generic' };
    }

    // ===== HELPERS 3D =====
    function makeLED(color, powered, size) {
        size = size || 0.025;
        return new THREE.Mesh(
            new THREE.SphereGeometry(size, 8, 8),
            new THREE.MeshStandardMaterial({
                color: powered ? color : 0x334155,
                emissive: powered ? color : 0x000000,
                emissiveIntensity: powered ? 1.2 : 0
            })
        );
    }
    function makeChassis(w, h, d, color) {
        color = color || 0x1e293b;
        const m = new THREE.Mesh(
            new THREE.BoxGeometry(w, h, d),
            new THREE.MeshStandardMaterial({ color, metalness: 0.7, roughness: 0.35 })
        );
        m.castShadow = true;
        m.receiveShadow = true;
        return m;
    }

    // ===== TEXTURA FRONTAL (canvas) =====
    function createDeviceTexture(type, label, powered) {
        const cv = document.createElement('canvas');
        cv.width = 512; cv.height = 128;
        const c = cv.getContext('2d');
        c.fillStyle = '#0f172a'; c.fillRect(0, 0, 512, 128);
        c.strokeStyle = '#334155'; c.lineWidth = 2; c.strokeRect(1, 1, 510, 126);
        // Barra superior
        c.fillStyle = '#1e293b'; c.fillRect(0, 0, 512, 22);
        c.fillStyle = '#38bdf8'; c.font = 'bold 11px monospace';
        c.fillText(label.toUpperCase().substring(0, 30), 8, 15);
        // LED power
        c.fillStyle = powered ? '#22c55e' : '#475569';
        c.beginPath(); c.arc(500, 11, 4, 0, Math.PI * 2); c.fill();

        const bc = 'switch_l2';
        switch (type) {
            case 'router':
            case 'switch_l2': case 'switch_l3': case 'switch_l2_poe': case 'switch_l3_poe':
                // 24 portas em 2 fileiras
                for (let row = 0; row < 2; row++) {
                    for (let i = 0; i < 12; i++) {
                        const x = 12 + i * 35, y = 32 + row * 44;
                        c.fillStyle = '#020617'; c.fillRect(x, y, 28, 32);
                        c.strokeStyle = '#334155'; c.strokeRect(x, y, 28, 32);
                        c.fillStyle = powered && Math.random() > 0.4 ? '#22c55e' : '#475569';
                        c.fillRect(x + 10, y + 3, 6, 4);
                    }
                }
                // SFP
                for (let i = 0; i < 2; i++) {
                    c.fillStyle = '#020617'; c.fillRect(438 + i * 36, 40, 30, 30);
                    c.strokeStyle = powered ? '#f59e0b' : '#334155'; c.strokeRect(438 + i * 36, 40, 30, 30);
                }
                break;
            case 'olt':
                for (let i = 0; i < 2; i++) { c.fillStyle = powered ? '#22c55e' : '#475569'; c.beginPath(); c.arc(20 + i * 15, 40, 5, 0, Math.PI * 2); c.fill(); }
                for (let i = 0; i < 16; i++) {
                    c.fillStyle = '#020617'; c.fillRect(70 + i * 26, 40, 20, 22);
                    c.strokeStyle = powered ? '#14b8a6' : '#334155'; c.strokeRect(70 + i * 26, 40, 20, 22);
                    c.fillStyle = powered && Math.random() > 0.3 ? '#22c55e' : '#334155';
                    c.fillRect(76 + i * 26, 45, 5, 3);
                }
                c.fillStyle = '#020617'; c.fillRect(70, 80, 60, 20);
                c.strokeStyle = powered ? '#f59e0b' : '#334155'; c.strokeRect(70, 80, 60, 20);
                c.fillStyle = '#020617'; c.fillRect(400, 32, 100, 62);
                c.strokeStyle = '#1e293b'; c.strokeRect(400, 32, 100, 62);
                c.fillStyle = powered ? '#22c55e' : '#ef4444'; c.font = 'bold 12px monospace';
                c.fillText(powered ? 'ONLINE' : 'OFFLINE', 415, 60);
                c.font = '10px monospace'; c.fillStyle = '#94a3b8'; c.fillText('64 ONU', 415, 78);
                break;
            case 'patch':
                for (let i = 0; i < 24; i++) {
                    c.fillStyle = '#020617'; c.fillRect(12 + i * 20, 45, 16, 32);
                    c.strokeStyle = '#475569'; c.lineWidth = 1;
                    c.strokeRect(12 + i * 20, 45, 16, 32);
                    c.fillStyle = '#94a3b8'; c.font = 'bold 8px monospace';
                    c.fillText((i + 1).toString(), 16 + i * 20, 90);
                }
                break;
            case 'nvr':
                for (let i = 0; i < 4; i++) {
                    const x = 20 + i * 60;
                    c.fillStyle = '#020617'; c.fillRect(x, 35, 50, 62);
                    c.strokeStyle = '#475569'; c.lineWidth = 1.5; c.strokeRect(x, 35, 50, 62);
                    c.fillStyle = '#94a3b8'; c.font = 'bold 9px monospace'; c.fillText('HDD ' + (i+1), x + 12, 55);
                    c.fillStyle = powered && Math.random() > 0.3 ? '#8b5cf6' : '#475569';
                    c.beginPath(); c.arc(x + 25, 80, 4, 0, Math.PI * 2); c.fill();
                }
                c.fillStyle = '#020617'; c.fillRect(280, 35, 180, 62);
                c.strokeStyle = '#1e293b'; c.strokeRect(280, 35, 180, 62);
                c.fillStyle = powered ? '#22c55e' : '#ef4444'; c.font = 'bold 12px monospace';
                c.fillText(powered ? 'REC 16CH' : 'STANDBY', 300, 58);
                c.font = '10px monospace'; c.fillStyle = '#94a3b8'; c.fillText('4K H.265 · 30fps', 300, 78);
                break;
            case 'pbx':
                c.fillStyle = '#a855f7'; c.font = 'bold 9px monospace'; c.fillText('FXS', 20, 32);
                for (let i = 0; i < 8; i++) {
                    c.fillStyle = '#020617'; c.fillRect(20 + i * 22, 38, 18, 28);
                    c.strokeStyle = powered ? '#a855f7' : '#334155'; c.strokeRect(20 + i * 22, 38, 18, 28);
                }
                c.fillStyle = '#eab308'; c.fillText('FXO', 210, 32);
                for (let i = 0; i < 4; i++) {
                    c.fillStyle = '#020617'; c.fillRect(210 + i * 22, 38, 18, 28);
                    c.strokeStyle = powered ? '#eab308' : '#334155'; c.strokeRect(210 + i * 22, 38, 18, 28);
                }
                c.fillStyle = powered ? '#22c55e' : '#475569'; c.font = 'bold 11px monospace';
                c.fillText('SIP', 340, 55); c.fillText('PSTN', 400, 55);
                break;
            case 'ups':
                c.fillStyle = '#020617'; c.fillRect(20, 30, 300, 72);
                c.strokeStyle = powered ? '#22c55e' : '#ef4444'; c.lineWidth = 2; c.strokeRect(20, 30, 300, 72);
                c.fillStyle = powered ? '#22c55e' : '#ef4444'; c.font = 'bold 20px monospace';
                c.fillText(powered ? '220V · 87%' : '--- OFF ---', 40, 70);
                c.font = '10px monospace'; c.fillStyle = '#94a3b8'; c.fillText('IN 220V · OUT 220V', 40, 90);
                for (let i = 0; i < 4; i++) {
                    c.fillStyle = '#334155'; c.fillRect(350 + i * 35, 50, 28, 22);
                    c.fillStyle = '#94a3b8'; c.font = 'bold 8px monospace'; c.fillText('BTN', 358 + i * 35, 64);
                }
                break;
            case 'server':
                for (let i = 0; i < 8; i++) {
                    const x = 15 + i * 55;
                    c.fillStyle = '#020617'; c.fillRect(x, 35, 48, 62);
                    c.strokeStyle = '#475569'; c.lineWidth = 1.5; c.strokeRect(x, 35, 48, 62);
                    c.fillStyle = '#334155'; c.fillRect(x + 8, 50, 32, 6);
                    c.fillStyle = powered && Math.random() > 0.5 ? '#22c55e' : '#475569';
                    c.beginPath(); c.arc(x + 24, 78, 4, 0, Math.PI * 2); c.fill();
                    c.fillStyle = '#94a3b8'; c.font = 'bold 8px monospace'; c.fillText('B' + (i+1), x + 20, 45);
                }
                break;
            case 'nas':
                for (let row = 0; row < 2; row++) for (let i = 0; i < 6; i++) {
                    const x = 15 + i * 55, y = 30 + row * 36;
                    c.fillStyle = '#020617'; c.fillRect(x, y, 48, 32);
                    c.strokeStyle = '#475569'; c.lineWidth = 1; c.strokeRect(x, y, 48, 32);
                    c.fillStyle = powered && Math.random() > 0.2 ? '#22c55e' : '#334155';
                    c.beginPath(); c.arc(x + 24, y + 16, 3, 0, Math.PI * 2); c.fill();
                }
                c.fillStyle = powered ? '#22c55e' : '#ef4444'; c.font = 'bold 10px monospace';
                c.fillText(powered ? 'RAID 5 OK' : 'ERROR', 380, 64);
                break;
            case 'onu':
                c.fillStyle = '#22c55e'; c.font = 'bold 9px monospace'; c.fillText('PON', 15, 30);
                c.fillStyle = '#020617'; c.fillRect(15, 38, 28, 24);
                c.strokeStyle = powered ? '#22c55e' : '#334155'; c.strokeRect(15, 38, 28, 24);
                for (let i = 0; i < 4; i++) {
                    c.fillStyle = '#020617'; c.fillRect(70 + i * 30, 38, 24, 24);
                    c.strokeStyle = '#334155'; c.strokeRect(70 + i * 30, 38, 24, 24);
                    c.fillStyle = powered ? '#22c55e' : '#334155'; c.fillRect(80 + i * 30, 42, 5, 4);
                }
                c.fillStyle = '#94a3b8'; c.font = '9px monospace'; c.fillText('LAN', 70, 32);
                break;
            case 'cto':
                c.fillStyle = '#1e293b'; c.fillRect(10, 10, 492, 108);
                c.strokeStyle = '#475569'; c.lineWidth = 2; c.strokeRect(10, 10, 492, 108);
                c.fillStyle = '#475569'; c.fillRect(240, 60, 32, 8);
                for (let i = 0; i < 3; i++) {
                    c.fillStyle = '#64748b'; c.beginPath(); c.arc(20, 25 + i * 30, 4, 0, Math.PI * 2); c.fill();
                }
                c.fillStyle = '#94a3b8'; c.font = 'bold 11px monospace'; c.fillText('CTO OPTICAL BOX', 200, 115);
                break;
            case 'converter':
                c.fillStyle = '#10b981'; c.font = 'bold 9px monospace'; c.fillText('FX', 60, 55);
                c.fillStyle = '#020617'; c.fillRect(90, 45, 40, 35);
                c.strokeStyle = powered ? '#10b981' : '#334155'; c.strokeRect(90, 45, 40, 35);
                c.fillStyle = '#94a3b8'; c.font = 'bold 9px monospace'; c.fillText('TX', 200, 55);
                c.fillStyle = '#020617'; c.fillRect(230, 45, 40, 35);
                c.strokeStyle = '#334155'; c.strokeRect(230, 45, 40, 35);
                break;
            case 'camera':
                c.fillStyle = '#1e293b'; c.beginPath(); c.arc(256, 64, 40, 0, Math.PI * 2); c.fill();
                c.fillStyle = '#020617'; c.beginPath(); c.arc(256, 64, 22, 0, Math.PI * 2); c.fill();
                c.fillStyle = powered ? '#3b82f6' : '#334155'; c.beginPath(); c.arc(256, 64, 14, 0, Math.PI * 2); c.fill();
                break;
            case 'sensor':
                c.fillStyle = '#475569'; c.beginPath(); c.arc(256, 64, 30, 0, Math.PI * 2); c.fill();
                c.fillStyle = powered ? '#dc3545' : '#475569';
                c.beginPath(); c.arc(256, 64, 10, 0, Math.PI * 2); c.fill();
                break;
            case 'phone':
                c.fillStyle = '#1e293b'; c.fillRect(200, 30, 112, 68);
                c.fillStyle = '#020617'; c.fillRect(215, 40, 82, 30);
                for (let i = 0; i < 12; i++) {
                    c.fillStyle = '#475569';
                    c.fillRect(215 + (i % 3) * 28, 75 + Math.floor(i / 3) * 12, 20, 8);
                }
                break;
            default:
                c.fillStyle = '#020617'; c.fillRect(20, 30, 472, 68);
                c.strokeStyle = '#475569'; c.strokeRect(20, 30, 472, 68);
                c.fillStyle = powered ? '#22c55e' : '#ef4444'; c.font = 'bold 14px monospace';
                c.fillText(powered ? '● ONLINE' : '○ OFF', 40, 68);
        }
        return new THREE.CanvasTexture(cv);
    }

    // ===== MODELO 3D =====
    function buildDeviceModel(type, name, powered) {
        const cat = getCatalog(type);
        const group = new THREE.Group();
        const chassis = makeChassis(cat.w, cat.h, cat.d, 0x1e293b);
        group.add(chassis);
        // Painel frontal texturizado
        const tex = createDeviceTexture(cat.builder, cat.label, powered);
        const front = new THREE.Mesh(
            new THREE.PlaneGeometry(cat.w * 0.98, cat.h * 0.85),
            new THREE.MeshStandardMaterial({ map: tex, roughness: 0.6, metalness: 0.2 })
        );
        front.position.z = cat.d/2 + 0.005;
        group.add(front);
        // Detalhes 3D específicos
        if (cat.builder === 'router') {
            for (let i = 0; i < 3; i++) {
                const ant = new THREE.Mesh(
                    new THREE.CylinderGeometry(0.02, 0.03, 0.6, 6),
                    new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.6 })
                );
                ant.position.set(-0.8 + i * 0.8, cat.h/2 + 0.3, -cat.d/2 + 0.3);
                group.add(ant);
            }
        }
        if (cat.builder === 'onu') {
            const ant = new THREE.Mesh(
                new THREE.CylinderGeometry(0.015, 0.02, 0.4, 6),
                new THREE.MeshStandardMaterial({ color: 0x334155 })
            );
            ant.position.set(0, cat.h/2 + 0.2, -cat.d/2 + 0.15);
            group.add(ant);
        }
        if (cat.builder === 'cto') {
            const handle = new THREE.Mesh(
                new THREE.BoxGeometry(0.15, 0.03, 0.02),
                new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.8 })
            );
            handle.position.set(0, 0, cat.d/2 + 0.01);
            group.add(handle);
        }
        // LED power universal
        const pwrLed = makeLED(0x22c55e, powered, Math.min(0.025, cat.h * 0.15));
        pwrLed.position.set(cat.w/2 - 0.1, cat.h/2 - 0.06, cat.d/2 + 0.02);
        group.add(pwrLed);

        group.userData.baseSize = { w: cat.w, h: cat.h, d: cat.d };
        return group;
    }

    // ===== ESTADO =====
    const state = {
        scene: null, camera: null, renderer: null, controls: null,
        raycaster: new THREE.Raycaster(),
        mouse: new THREE.Vector2(),
        floorPlane: new THREE.Plane(new THREE.Vector3(0, 1, 0), 2.5),
        devicesGroup: null, cablesGroup: null, particlesGroup: null,
        instances: [], // { id, type, name, group, w, h, d, ip, port, username, password }
        connections: [], // { id, from, to, cableType }
        selected: null,
        dragging: null, isDragging: false, dragStart: null, dragMoved: false,
        pointerDownPos: null,
        cableAnims: [], textureUpdates: [],
        animFrame: null, isOpen: false,
        cableType: 'cat6', patchSource: null, patchDests: new Set()
    };

    const FLOOR_Y = -2.5;
    const RACK_BOTTOM = -2.35;
    const RACK_TOP = 7.5;
    const RACK_FP = 1.8;

    // ===== SCENE INIT =====
    function initScene() {
        const container = document.getElementById('sim3d-container');
        container.innerHTML = '';
        state.scene = new THREE.Scene();
        state.scene.background = new THREE.Color(0x080b13);
        state.scene.fog = new THREE.FogExp2(0x080b13, 0.012);

        state.camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 200);
        state.camera.position.set(16, 8, 20);

        state.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
        state.renderer.setSize(window.innerWidth, window.innerHeight);
        state.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        state.renderer.shadowMap.enabled = true;
        state.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        state.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        state.renderer.toneMappingExposure = 1.3;
        container.appendChild(state.renderer.domElement);

        state.controls = new THREE.OrbitControls(state.camera, state.renderer.domElement);
        state.controls.enableDamping = true;
        state.controls.dampingFactor = 0.06;
        state.controls.target.set(0, 2.5, 0);
        state.controls.maxPolarAngle = Math.PI / 2 + 0.05;
        state.controls.minDistance = 4;
        state.controls.maxDistance = 50;

        // Lights
        state.scene.add(new THREE.AmbientLight(0xffffff, 1.5));
        const spot = new THREE.SpotLight(0x38bdf8, 3);
        spot.position.set(12, 20, 14);
        spot.angle = Math.PI / 4;
        spot.castShadow = true;
        spot.shadow.mapSize.set(2048, 2048);
        state.scene.add(spot);
        const fill = new THREE.PointLight(0x0284c7, 2, 40);
        fill.position.set(-14, 10, -8);
        state.scene.add(fill);

        // Floor
        const floor = new THREE.Mesh(
            new THREE.PlaneGeometry(80, 80),
            new THREE.MeshStandardMaterial({ color: 0x0a0e17, roughness: 0.5, metalness: 0.7 })
        );
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = FLOOR_Y;
        floor.receiveShadow = true;
        state.scene.add(floor);
        const grid = new THREE.GridHelper(80, 80, 0x38bdf8, 0x1e293b);
        grid.position.y = FLOOR_Y + 0.01;
        grid.material.opacity = 0.35;
        grid.material.transparent = true;
        state.scene.add(grid);

        buildRack();

        state.devicesGroup = new THREE.Group();
        state.cablesGroup = new THREE.Group();
        state.particlesGroup = new THREE.Group();
        state.scene.add(state.devicesGroup);
        state.scene.add(state.cablesGroup);
        state.scene.add(state.particlesGroup);

        // Event listeners
        const dom = state.renderer.domElement;
        dom.addEventListener('pointerdown', onPointerDown);
        dom.addEventListener('pointermove', onPointerMove);
        dom.addEventListener('pointerup', onPointerUp);
        dom.addEventListener('pointerleave', onPointerUp);
        dom.addEventListener('dragover', onDragOver);
        dom.addEventListener('drop', onDrop);
        window.addEventListener('resize', onResize);
    }

    function buildRack() {
        const rack = new THREE.Group();
        const metal = new THREE.MeshStandardMaterial({ color: 0x111622, metalness: 0.9, roughness: 0.4 });
        const pillarGeo = new THREE.BoxGeometry(0.25, 10, 0.25);
        [[-2, 2.7, -2], [2, 2.7, -2], [-2, 2.7, 2], [2, 2.7, 2]].forEach(p => {
            const mesh = new THREE.Mesh(pillarGeo, metal);
            mesh.position.set(...p);
            mesh.castShadow = true;
            rack.add(mesh);
        });
        const top = new THREE.Mesh(new THREE.BoxGeometry(4.5, 0.3, 4.5), metal);
        top.position.set(0, 7.85, 0);
        top.castShadow = true;
        rack.add(top);
        const bot = new THREE.Mesh(new THREE.BoxGeometry(4.5, 0.3, 4.5), metal);
        bot.position.set(0, -2.55, 0);
        bot.castShadow = true;
        rack.add(bot);
        // U-slots markers (linhas horizontais nas colunas)
        for (let i = 0; i < 20; i++) {
            const line = new THREE.Mesh(
                new THREE.BoxGeometry(4.2, 0.02, 0.05),
                new THREE.MeshBasicMaterial({ color: 0x1e293b })
            );
            line.position.set(0, RACK_BOTTOM + i * 0.48, -2.15);
            rack.add(line);
        }
        // Etiqueta do rack
        const cv = document.createElement('canvas');
        cv.width = 512; cv.height = 64;
        const c = cv.getContext('2d');
        c.fillStyle = 'transparent'; c.fillRect(0, 0, 512, 64);
        c.fillStyle = '#38bdf8'; c.font = 'bold 32px monospace';
        c.fillText('RACK PRINCIPAL', 100, 42);
        const tex = new THREE.CanvasTexture(cv);
        const labelMesh = new THREE.Mesh(
            new THREE.PlaneGeometry(3, 0.4),
            new THREE.MeshBasicMaterial({ map: tex, transparent: true })
        );
        labelMesh.position.set(0, 8.3, 2.3);
        rack.add(labelMesh);
        state.scene.add(rack);
    }

    // ===== RAYCAST =====
    function rayToFloor(clientX, clientY) {
        const rect = state.renderer.domElement.getBoundingClientRect();
        state.mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
        state.mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
        state.raycaster.setFromCamera(state.mouse, state.camera);
        const pt = new THREE.Vector3();
        state.raycaster.ray.intersectPlane(state.floorPlane, pt);
        return pt;
    }

    function rayDevices(clientX, clientY) {
        const rect = state.renderer.domElement.getBoundingClientRect();
        state.mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
        state.mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
        state.raycaster.setFromCamera(state.mouse, state.camera);
        const hits = state.raycaster.intersectObjects(state.devicesGroup.children, true);
        if (!hits.length) return null;
        let obj = hits[0].object;
        while (obj.parent && obj.parent !== state.devicesGroup) obj = obj.parent;
        if (!obj.userData.instanceId) return null;
        return state.instances.find(i => i.id === obj.userData.instanceId) || null;
    }

    // ===== AUTO-Y PARA RACK =====
    function computeY(x, z, h) {
        const inRack = Math.abs(x) < RACK_FP && Math.abs(z) < RACK_FP;
        if (!inRack) return FLOOR_Y + h/2 + 0.01;
        // Empilha dentro do rack
        const inRackDevs = state.instances.filter(d => {
            const p = d.group.position;
            return Math.abs(p.x) < RACK_FP && Math.abs(p.z) < RACK_FP && p.y > FLOOR_Y - 0.5 && p.y < RACK_TOP;
        });
        if (inRackDevs.length === 0) return RACK_BOTTOM + h/2 + 0.05;
        let maxTop = RACK_BOTTOM;
        inRackDevs.forEach(d => {
            const t = d.group.position.y + d.h/2;
            if (t > maxTop) maxTop = t;
        });
        const newY = maxTop + h/2 + 0.06;
        return newY > RACK_TOP ? FLOOR_Y + h/2 + 0.01 : newY;
    }

    // ===== ADD / REMOVE DEVICE =====
    function addDevice(type, name, x, y, z, opts) {
        opts = opts || {};
        const cat = getCatalog(type);
        const powered = true;
        const group = buildDeviceModel(type, name, powered);
        const finalY = (y === undefined || y === null) ? computeY(x, z, cat.h) : y;
        group.position.set(x, finalY, z);
        if (opts.rotation) group.rotation.y = opts.rotation;
        group.userData.instanceId = opts.restoreId || ('dev_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6));

        state.devicesGroup.add(group);
        const instance = {
            id: group.userData.instanceId,
            type, name,
            group,
            w: cat.w, h: cat.h, d: cat.d,
            ip: opts.ip || '',
            port: opts.port || 80,
            username: opts.username || '',
            password: opts.password || ''
        };
        state.instances.push(instance);
        rebuildAllCables();
        saveState();
        return instance;
    }

    function removeDevice(id) {
        const inst = state.instances.find(i => i.id === id);
        if (!inst) return;
        state.devicesGroup.remove(inst.group);
        // Dispose
        inst.group.traverse(o => {
            if (o.geometry) o.geometry.dispose();
            if (o.material) {
                if (o.material.map) o.material.map.dispose();
                o.material.dispose();
            }
        });
        state.instances = state.instances.filter(i => i.id !== id);
        state.connections = state.connections.filter(c => c.from !== id && c.to !== id);
        if (state.selected && state.selected.id === id) {
            state.selected = null;
            hideProperties();
        }
        rebuildAllCables();
        renderConnectionsPanel();
        saveState();
    }

    // ===== CABLES =====
    function rebuildAllCables() {
        while (state.cablesGroup.children.length) {
            const c = state.cablesGroup.children[0];
            state.cablesGroup.remove(c);
            if (c.geometry) c.geometry.dispose();
            if (c.material) c.material.dispose();
        }
        while (state.particlesGroup.children.length) {
            const c = state.particlesGroup.children[0];
            state.particlesGroup.remove(c);
            if (c.geometry) c.geometry.dispose();
            if (c.material) c.material.dispose();
        }
        state.cableAnims = [];

        state.connections.forEach(conn => {
            const from = state.instances.find(i => i.id === conn.from);
            const to = state.instances.find(i => i.id === conn.to);
            if (!from || !to) return;
            const isPower = conn.cableType === 'power-ac';
            const zOff1 = isPower ? -from.d/2 - 0.1 : from.d/2 + 0.1;
            const zOff2 = isPower ? -to.d/2 - 0.1 : to.d/2 + 0.1;
            const p1 = new THREE.Vector3(from.group.position.x, from.group.position.y, from.group.position.z + zOff1);
            const p2 = new THREE.Vector3(to.group.position.x, to.group.position.y, to.group.position.z + zOff2);
            const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
            mid.y -= 0.3;
            mid.x += (isPower ? -1 : 1);
            const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);

            let color = 0x38bdf8, particleColor = 0x22c55e;
            if (conn.cableType === 'fiber-sfp') { color = 0xf59e0b; particleColor = 0xffffff; }
            else if (conn.cableType === 'power-ac') { color = 0xef4444; particleColor = 0xfacc15; }
            else if (conn.cableType === 'coax-bnc') { color = 0xa855f7; particleColor = 0x38bdf8; }

            const tube = new THREE.Mesh(
                new THREE.TubeGeometry(curve, 40, 0.04, 8, false),
                new THREE.MeshStandardMaterial({ color, roughness: 0.3, metalness: 0.2 })
            );
            state.cablesGroup.add(tube);

            const particleGeo = new THREE.BufferGeometry();
            const count = 12;
            const positions = new Float32Array(count * 3);
            const progresses = [];
            for (let i = 0; i < count; i++) {
                const t = i / count;
                progresses.push(t);
                const pt = curve.getPoint(t);
                positions[i*3] = pt.x;
                positions[i*3+1] = pt.y;
                positions[i*3+2] = pt.z;
            }
            particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            const pMesh = new THREE.Points(
                particleGeo,
                new THREE.PointsMaterial({ color: particleColor, size: 0.12, transparent: true, opacity: 0.9 })
            );
            state.particlesGroup.add(pMesh);
            state.cableAnims.push({ mesh: pMesh, curve, progress: progresses });
        });
    }

    function renderConnectionsPanel() {
        const panel = document.getElementById('sim3d-connections-panel');
        const list = document.getElementById('sim3d-connections-list');
        const cnt = document.getElementById('sim3d-connections-count');
        if (!list) return;
        list.innerHTML = '';
        cnt.innerText = state.connections.length;
        panel.style.display = state.connections.length > 0 ? 'flex' : 'none';
        state.connections.forEach((c, i) => {
            const from = state.instances.find(x => x.id === c.from);
            const to = state.instances.find(x => x.id === c.to);
            const div = document.createElement('div');
            div.className = 'sim3d-connection-row';
            div.innerHTML = `<div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"><span class="tag">[${c.cableType.toUpperCase()}]</span> ${(from?.name || '?').substring(0, 12)} ↔ ${(to?.name || '?').substring(0, 12)}</div><button class="sim3d-connection-remove" onclick="sim3DRemoveConnection('${c.id}')">✕</button>`;
            list.appendChild(div);
        });
    }
    window.sim3DRemoveConnection = (id) => {
        state.connections = state.connections.filter(c => c.id !== id);
        rebuildAllCables();
        renderConnectionsPanel();
        saveState();
        toast('🗑 Conexão removida');
    };

    // ===== DRAWER (equipamentos) =====
    function renderDrawer() {
        const list = document.getElementById('sim3d-equipment-list');
        if (!list) return;
        list.innerHTML = '';
        const grouped = {};
        Object.entries(categories || {}).forEach(([cat, data]) => {
            if (!data.devices) return;
            data.devices.forEach(d => {
                if (!grouped[cat]) grouped[cat] = [];
                grouped[cat].push(d);
            });
        });
        (customDevices || []).forEach(d => {
            if (!grouped['Personalizados']) grouped['Personalizados'] = [];
            grouped['Personalizados'].push(d);
        });

        Object.entries(grouped).forEach(([catName, devices]) => {
            const grp = document.createElement('div');
            grp.className = 'sim3d-eq-group';
            grp.innerHTML = `<div class="sim3d-eq-group-title">${catName}</div>`;
            devices.forEach(dev => {
                const cat = getCatalog(dev.type);
                const layoutLabel = { rack: 'Rack', desktop: 'Desktop', wall: 'Parede', mini: 'Mini', generic: 'Compacto' }[cat.layout] || 'Custom';
                const item = document.createElement('div');
                item.className = 'sim3d-eq-item';
                item.draggable = true;
                item.innerHTML = `<div class="sim3d-eq-info"><div class="sim3d-eq-name"><span class="sim3d-eq-unit">${layoutLabel}</span>${dev.name}</div><div class="sim3d-eq-desc">${dev.desc || dev.type || ''}</div></div>`;
                item.addEventListener('dragstart', e => {
                    e.dataTransfer.setData('application/json', JSON.stringify({ type: dev.type, name: dev.name }));
                    e.dataTransfer.effectAllowed = 'copy';
                    item.classList.add('dragging');
                });
                item.addEventListener('dragend', () => item.classList.remove('dragging'));
                item.addEventListener('click', () => {
                    // Clique = adiciona em frente ao rack
                    addDevice(dev.type, dev.name, -3, undefined, 4);
                    toast(`✅ ${dev.name} adicionado`);
                });
                grp.appendChild(item);
            });
            list.appendChild(grp);
        });
    }

    // ===== DRAG & DROP =====
    function onDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        const hint = document.getElementById('sim3d-drop-hint');
        if (hint) hint.classList.add('active');
    }
    function onDrop(e) {
        e.preventDefault();
        const hint = document.getElementById('sim3d-drop-hint');
        if (hint) hint.classList.remove('active');
        try {
            const data = JSON.parse(e.dataTransfer.getData('application/json'));
            if (!data) return;
            const pt = rayToFloor(e.clientX, e.clientY);
            addDevice(data.type, data.name, pt.x, undefined, pt.z);
            toast(`✅ ${data.name} posicionado`);
        } catch(err) { console.error(err); }
    }

    // ===== POINTER INTERACTION =====
    function onPointerDown(e) {
        if (e.button !== 0) return;
        state.pointerDownPos = { x: e.clientX, y: e.clientY };
        state.dragMoved = false;
        const hit = rayDevices(e.clientX, e.clientY);
        if (hit) {
            state.selected = hit;
            state.dragging = hit;
            state.dragStart = rayToFloor(e.clientX, e.clientY);
            // Não desabilita controls ainda - só quando começar movimento real
        } else {
            // Clique em espaço vazio
            if (state.selected) {
                state.selected = null;
                hideProperties();
            }
        }
    }

    function onPointerMove(e) {
        if (state.pointerDownPos) {
            const dx = e.clientX - state.pointerDownPos.x;
            const dy = e.clientY - state.pointerDownPos.y;
            if (Math.hypot(dx, dy) > 5 && state.dragging && !state.dragMoved) {
                state.dragMoved = true;
                state.controls.enabled = false;
                state.renderer.domElement.style.cursor = 'grabbing';
            }
        }
        if (state.dragging && state.dragMoved) {
            const cur = rayToFloor(e.clientX, e.clientY);
            const curDx = cur.x - state.dragStart.x;
            const curDz = cur.z - state.dragStart.z;
            const inst = state.dragging;
            inst.group.position.x += curDx;
            inst.group.position.z += curDz;
            state.dragStart = cur;
            // Atualiza Y se estiver no rack
            const newY = computeY(inst.group.position.x, inst.group.position.z, inst.h);
            inst.group.position.y = newY;
            rebuildAllCables();
        } else {
            // Hover cursor
            const hit = rayDevices(e.clientX, e.clientY);
            state.renderer.domElement.style.cursor = hit ? 'grab' : 'default';
        }
    }

    function onPointerUp(e) {
        if (state.pointerDownPos) {
            const dx = e.clientX - state.pointerDownPos.x;
            const dy = e.clientY - state.pointerDownPos.y;
            const wasClick = Math.hypot(dx, dy) < 5;
            if (state.selected && wasClick) {
                showProperties(state.selected);
            } else if (state.selected) {
                saveState();
            }
        }
        state.dragging = null;
        state.isDragging = false;
        state.dragMoved = false;
        state.pointerDownPos = null;
        state.controls.enabled = true;
        state.renderer.domElement.style.cursor = 'default';
    }

    function onResize() {
        if (!state.camera || !state.renderer) return;
        state.camera.aspect = window.innerWidth / window.innerHeight;
        state.camera.updateProjectionMatrix();
        state.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    // ===== PROPERTIES PANEL =====
    function showProperties(inst) {
        const panel = document.getElementById('sim3d-properties');
        const title = document.getElementById('sim3d-prop-title');
        const body = document.getElementById('sim3d-prop-body');
        if (!panel || !body) return;
        title.textContent = inst.name;
        const pos = inst.group.position;
        body.innerHTML = `
            <div class="sim3d-prop-section">
                <div class="sim3d-prop-label">Nome</div>
                <input class="sim3d-prop-input" id="s3d-name" value="${(inst.name || '').replace(/"/g, '&quot;')}">
            </div>
            <div class="sim3d-prop-section">
                <div class="sim3d-prop-label">Tipo</div>
                <input class="sim3d-prop-input" value="${inst.type}" disabled>
            </div>
            <div class="sim3d-prop-section">
                <div class="sim3d-prop-label">Posição</div>
                <div class="sim3d-prop-row">
                    <input class="sim3d-prop-input" id="s3d-x" type="number" step="0.1" value="${pos.x.toFixed(2)}" placeholder="X">
                    <input class="sim3d-prop-input" id="s3d-y" type="number" step="0.1" value="${pos.y.toFixed(2)}" placeholder="Y">
                </div>
                <input class="sim3d-prop-input" id="s3d-z" type="number" step="0.1" value="${pos.z.toFixed(2)}" placeholder="Z">
            </div>
            <div class="sim3d-prop-section">
                <div class="sim3d-prop-label">Rotação (graus)</div>
                <input class="sim3d-prop-input" id="s3d-rot" type="range" min="0" max="360" value="${(inst.group.rotation.y * 180 / Math.PI).toFixed(0)}" oninput="document.getElementById('s3d-rot-val').innerText=this.value+'°'">
                <div id="s3d-rot-val" style="font-size:10px;color:#94a3b8;text-align:right;">${(inst.group.rotation.y * 180 / Math.PI).toFixed(0)}°</div>
            </div>
            <div class="sim3d-prop-section">
                <div class="sim3d-prop-label">🌐 Endereço IP</div>
                <input class="sim3d-prop-input" id="s3d-ip" value="${inst.ip || ''}" placeholder="192.168.1.100">
            </div>
            <div class="sim3d-prop-section">
                <div class="sim3d-prop-label">🔌 Porta</div>
                <input class="sim3d-prop-input" id="s3d-port" type="number" value="${inst.port || 80}">
            </div>
            <div class="sim3d-prop-row">
                <div class="sim3d-prop-section">
                    <div class="sim3d-prop-label">👤 Usuário</div>
                    <input class="sim3d-prop-input" id="s3d-user" value="${inst.username || ''}">
                </div>
                <div class="sim3d-prop-section">
                    <div class="sim3d-prop-label">🔑 Senha</div>
                    <input class="sim3d-prop-input" id="s3d-pass" type="password" value="${inst.password || ''}">
                </div>
            </div>
            <div class="sim3d-prop-actions">
                <button class="sim3d-action-btn primary" onclick="sim3DAccessDevice('${inst.id}')">🌐 Acessar Dispositivo</button>
                <button class="sim3d-action-btn" onclick="sim3DOpenPatchModal('${inst.id}')">🔗 Conectar a...</button>
                <button class="sim3d-action-btn" onclick="sim3DRotate90('${inst.id}')">🔄 Girar 90°</button>
                <button class="sim3d-action-btn" onclick="sim3DDuplicate('${inst.id}')">📋 Duplicar</button>
                <button class="sim3d-action-btn danger" onclick="sim3DDelete('${inst.id}')">🗑 Excluir</button>
            </div>
        `;
        // Bindings
        const b = (id, event, handler) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener(event, handler);
        };
        b('s3d-name', 'input', e => { inst.name = e.target.value; title.textContent = inst.name; saveState(); renderDrawer(); });
        b('s3d-x', 'change', e => { inst.group.position.x = parseFloat(e.target.value) || 0; rebuildAllCables(); saveState(); });
        b('s3d-y', 'change', e => { inst.group.position.y = parseFloat(e.target.value) || 0; rebuildAllCables(); saveState(); });
        b('s3d-z', 'change', e => { inst.group.position.z = parseFloat(e.target.value) || 0; rebuildAllCables(); saveState(); });
        b('s3d-rot', 'input', e => { inst.group.rotation.y = (parseFloat(e.target.value) || 0) * Math.PI / 180; rebuildAllCables(); saveState(); });
        b('s3d-ip', 'input', e => { inst.ip = e.target.value; saveState(); });
        b('s3d-port', 'input', e => { inst.port = parseInt(e.target.value) || 80; saveState(); });
        b('s3d-user', 'input', e => { inst.username = e.target.value; saveState(); });
        b('s3d-pass', 'input', e => { inst.password = e.target.value; saveState(); });

        panel.classList.add('open');
    }

    function hideProperties() {
        document.getElementById('sim3d-properties').classList.remove('open');
    }
    window.sim3DCloseProperties = hideProperties;

    window.sim3DAccessDevice = (id) => {
        const inst = state.instances.find(i => i.id === id);
        if (!inst) return;
        if (!inst.ip || !inst.ip.trim()) { toast('⚠️ Configure o IP primeiro'); return; }
        let url = inst.ip.trim();
        if (!/^https?:\/\//i.test(url)) url = 'http://' + url;
        if (inst.port && inst.port !== 80 && inst.port !== 443) url += ':' + inst.port;
        window.open(url, '_blank');
        toast(`🌐 Abrindo ${inst.name} → ${inst.ip}`);
    };
    window.sim3DRotate90 = (id) => {
        const inst = state.instances.find(i => i.id === id);
        if (!inst) return;
        inst.group.rotation.y += Math.PI / 2;
        rebuildAllCables();
        saveState();
        toast('🔄 Rotacionado 90°');
    };
    window.sim3DDuplicate = (id) => {
        const inst = state.instances.find(i => i.id === id);
        if (!inst) return;
        const p = inst.group.position;
        addDevice(inst.type, inst.name + ' (cópia)', p.x + 0.5, p.y, p.z + 0.5, { ip: inst.ip, port: inst.port, username: inst.username, password: inst.password, rotation: inst.group.rotation.y });
        toast('📋 Duplicado');
    };
    window.sim3DDelete = (id) => {
        if (!confirm('Excluir este dispositivo?')) return;
        removeDevice(id);
        toast('🗑 Removido');
    };

    // ===== CONNECTIONS MODAL =====
    window.sim3DOpenPatchModal = (fromId) => {
        state.patchSource = fromId;
        state.patchDests.clear();
        const from = state.instances.find(i => i.id === fromId);
        if (!from) return;
        document.getElementById('sim3d-patch-title').textContent = `Conectar: ${from.name}`;
        const destList = document.getElementById('sim3d-dest-list');
        destList.innerHTML = '';
        state.instances.forEach(inst => {
            if (inst.id === fromId) return;
            const lbl = document.createElement('label');
            lbl.className = 'sim3d-dest-item';
            lbl.innerHTML = `<span>${inst.name}</span><input type="checkbox" value="${inst.id}" onchange="window.sim3DToggleDest('${inst.id}')">`;
            destList.appendChild(lbl);
        });
        document.getElementById('sim3d-patch-modal').classList.add('open');
    };
    window.sim3DToggleDest = (id) => {
        if (state.patchDests.has(id)) state.patchDests.delete(id);
        else state.patchDests.add(id);
    };

    function setupPatchUI() {
        document.querySelectorAll('.sim3d-cable-btn').forEach(btn => {
            if (btn.dataset.bound) return;
            btn.dataset.bound = '1';
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.sim3d-cable-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                state.cableType = e.currentTarget.getAttribute('data-cable');
            });
        });
        const confirmBtn = document.getElementById('sim3d-confirm-patch');
        if (confirmBtn && !confirmBtn.dataset.bound) {
            confirmBtn.dataset.bound = '1';
            confirmBtn.addEventListener('click', () => {
                if (state.patchDests.size === 0) { toast('⚠️ Selecione pelo menos um destino'); return; }
                let count = 0;
                state.patchDests.forEach(destId => {
                    const exists = state.connections.some(c =>
                        (c.from === state.patchSource && c.to === destId) ||
                        (c.from === destId && c.to === state.patchSource)
                    );
                    if (!exists) {
                        state.connections.push({
                            id: 'conn_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6),
                            from: state.patchSource,
                            to: destId,
                            cableType: state.cableType
                        });
                        count++;
                    }
                });
                document.getElementById('sim3d-patch-modal').classList.remove('open');
                rebuildAllCables();
                renderConnectionsPanel();
                saveState();
                toast(`✅ ${count} conexão(ões) criada(s)`);
            });
        }
        const closePatch = document.getElementById('sim3d-patch-close');
        if (closePatch && !closePatch.dataset.bound) {
            closePatch.dataset.bound = '1';
            closePatch.addEventListener('click', () => document.getElementById('sim3d-patch-modal').classList.remove('open'));
        }
    }

    // ===== SAVE / LOAD =====
    function saveState() {
        if (!currentUser) return;
        const devices = state.instances.map(d => ({
            id: d.id, type: d.type, name: d.name,
            x: d.group.position.x, y: d.group.position.y, z: d.group.position.z,
            rotation: d.group.rotation.y,
            ip: d.ip, port: d.port, username: d.username, password: d.password
        }));
        try {
            localStorage.setItem(STORAGE_KEYS.SIM3D_MOUNTED(currentUser), JSON.stringify(devices));
            localStorage.setItem(STORAGE_KEYS.SIM3D_CONNECTIONS(currentUser), JSON.stringify(state.connections));
        } catch(e) { console.error(e); }
    }
    window.saveSim3DState = saveState;

    function loadState() {
        if (!currentUser) return;
        try {
            const devRaw = localStorage.getItem(STORAGE_KEYS.SIM3D_MOUNTED(currentUser));
            if (devRaw) {
                const devs = JSON.parse(devRaw);
                devs.forEach(d => {
                    addDevice(d.type, d.name, d.x, d.y, d.z, {
                        restoreId: d.id, rotation: d.rotation,
                        ip: d.ip, port: d.port, username: d.username, password: d.password
                    });
                });
            }
            const connRaw = localStorage.getItem(STORAGE_KEYS.SIM3D_CONNECTIONS(currentUser));
            if (connRaw) {
                state.connections = JSON.parse(connRaw);
                rebuildAllCables();
                renderConnectionsPanel();
            }
        } catch(e) { console.error(e); }
    }
    window.loadSim3DState = loadState;

    // ===== PUBLIC API =====
    window.openSim3D = function() {
        document.getElementById('sim3d-overlay').classList.add('active');
        state.isOpen = true;
        // Reset state
        state.instances = [];
        state.connections = [];
        state.selected = null;
        state.dragging = null;
        state.cableAnims = [];
        // Init scene
        setTimeout(() => {
            initScene();
            setupPatchUI();
            setupSim3DListeners();
            loadState();
            renderDrawer();
        }, 30);
    };
    window.closeSim3D = function() {
        document.getElementById('sim3d-overlay').classList.remove('active');
        state.isOpen = false;
        saveState();
        if (state.animFrame) { cancelAnimationFrame(state.animFrame); state.animFrame = null; }
        if (state.renderer) {
            state.renderer.dispose();
            if (state.renderer.domElement && state.renderer.domElement.parentNode) {
                state.renderer.domElement.parentNode.removeChild(state.renderer.domElement);
            }
        }
        if (state.scene) {
            state.scene.traverse(o => {
                if (o.geometry) o.geometry.dispose();
                if (o.material) {
                    if (o.material.map) o.material.map.dispose();
                    o.material.dispose();
                }
            });
            state.scene = null;
        }
        state.camera = null;
        state.renderer = null;
        state.controls = null;
        state.devicesGroup = null;
        state.cablesGroup = null;
        state.particlesGroup = null;
    };

    // ===== SETUP LISTENERS =====
    function setupSim3DListeners() {
        const bind = (id, evt, fn) => {
            const el = document.getElementById(id);
            if (el && !el.dataset.bound) { el.dataset.bound = '1'; el.addEventListener(evt, fn); }
        };
        bind('sim3d-close-btn', 'click', () => window.closeSim3D());
        bind('sim3d-toggle-drawer', 'click', () => {
            document.getElementById('sim3d-equipment-drawer').classList.toggle('closed');
        });
        bind('sim3d-close-drawer', 'click', () => {
            document.getElementById('sim3d-equipment-drawer').classList.add('closed');
        });
        bind('sim3d-run-script', 'click', runScript);
        bind('sim3d-terminal-close', 'click', () => {
            document.getElementById('sim3d-terminal').classList.remove('open');
        });
    }

    // ===== SCRIPT / TERMINAL =====
    function runScript() {
        const modal = document.getElementById('sim3d-terminal');
        const out = document.getElementById('sim3d-terminal-output');
        modal.classList.add('open');
        out.innerHTML = '<p style="color:#64748b;">[SYSTEM] Executando diagnóstico de infraestrutura...</p>';
        setTimeout(() => {
            const logs = [];
            logs.push(`<span style="color:#34d399;">[OK] ${state.instances.length} dispositivos no cenário.</span>`);
            logs.push(`<span style="color:#34d399;">[OK] ${state.connections.length} conexões estabelecidas.</span>`);
            if (state.instances.length === 0) {
                logs.push('<span style="color:#fbbf24;">[ALERTA] Nenhum dispositivo montado.</span>');
            } else {
                const hasRouter = state.instances.some(i => i.type === 'router');
                const hasSwitch = state.instances.some(i => i.type && i.type.startsWith('switch'));
                const hasOLT = state.instances.some(i => i.type === 'olt');
                const hasONU = state.instances.some(i => i.type === 'onu' || i.type === 'ont');
                const hasCTO = state.instances.some(i => i.type === 'cto');
                if (hasRouter) logs.push('<span style="color:#34d399;">[OK] Router de borda detectado.</span>');
                if (hasSwitch) logs.push('<span style="color:#34d399;">[OK] Switch(es) detectado(s).</span>');
                if (hasOLT) logs.push('<span style="color:#34d399;">[OK] OLT GPON detectada.</span>');
                if (hasOLT && !hasONU) logs.push('<span style="color:#fbbf24;">[ALERTA] OLT sem ONU/ONT para terminar fibra.</span>');
                if (hasONU && !hasOLT) logs.push('<span style="color:#fbbf24;">[ALERTA] ONU sem OLT para conexão PON.</span>');
                if (hasCTO && !hasOLT) logs.push('<span style="color:#fbbf24;">[INFO] CTO presente — necessita OLT para distribuição.</span>');
                const powerConns = state.connections.filter(c => c.cableType === 'power-ac');
                if (powerConns.length === 0 && state.instances.length > 0) {
                    logs.push('<span style="color:#fbbf24;">[ALERTA] Nenhuma conexão de energia AC.</span>');
                } else if (powerConns.length > 0) {
                    logs.push(`<span style="color:#34d399;">[OK] ${powerConns.length} conexões de energia AC.</span>`);
                }
            }
            logs.push('<br><span style="color:#67e8f9;font-weight:bold;">>>> DIAGNÓSTICO CONCLUÍDO <<<</span>');
            out.innerHTML += logs.join('<br>');
            out.scrollTop = out.scrollHeight;
            toast('⚡ Diagnóstico concluído!');
        }, 800);
    }

    // ===== TOAST 3D =====
    function toast(msg) {
        const t = document.getElementById('sim3d-toast');
        const m = document.getElementById('sim3d-toast-message');
        if (!t || !m) return;
        m.innerText = msg;
        t.classList.add('show');
        clearTimeout(t._timeout);
        t._timeout = setTimeout(() => t.classList.remove('show'), 2800);
    }

    // ===== ANIMATION LOOP =====
    function animate() {
        state.animFrame = requestAnimationFrame(animate);
        // Partículas dos cabos
        state.cableAnims.forEach(anim => {
            const arr = anim.mesh.geometry.attributes.position.array;
            for (let i = 0; i < anim.progress.length; i++) {
                anim.progress[i] += 0.008;
                if (anim.progress[i] > 1) anim.progress[i] = 0;
                const pt = anim.curve.getPoint(anim.progress[i]);
                arr[i*3] = pt.x;
                arr[i*3+1] = pt.y;
                arr[i*3+2] = pt.z;
            }
            anim.mesh.geometry.attributes.position.needsUpdate = true;
        });
        if (state.controls) state.controls.update();
        if (state.renderer && state.scene && state.camera) {
            state.renderer.render(state.scene, state.camera);
        }
    }

    // Start animation once
    const origOpen = window.openSim3D;
    window.openSim3D = function() {
        origOpen();
        // Reset animation frame
        if (state.animFrame) cancelAnimationFrame(state.animFrame);
        setTimeout(() => {
            if (state.scene) animate();
        }, 100);
    };

    console.log('[SIM3D] Módulo 3D carregado — modelos realistas por tipo');
})();
// ==================== FIM DO SISTEMA ====================
