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

@app.route('/api/upload_dev_image', methods=['POST'])
@admin_required
def upload_dev_image():
    data = request.json
    image_data = data.get('image', '')
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
    
    filename = f"dev{ext}"
    filepath = os.path.join(BASE_DIR, filename)
    
    for old_ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        old_path = os.path.join(BASE_DIR, f"dev{old_ext}")
        if os.path.exists(old_path) and old_path != filepath:
            try: os.remove(old_path)
            except: pass
    
    try:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return jsonify({'success': True, 'url': f'/static/{filename}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload_login_bg', methods=['POST'])
@admin_required
def upload_login_bg():
    data = request.json
    media_data = data.get('media', '')
    media_type = data.get('type', 'image')
    
    if not media_data:
        return jsonify({'success': False, 'error': 'Mídia inválida'}), 400
    
    if media_data.startswith('data:'):
        try:
            header, encoded = media_data.split(',', 1)
            mime = header.split(';')[0].replace('data:', '')
            ext_map = {
                'image/png': '.png', 'image/jpeg': '.jpg', 'image/jpg': '.jpg',
                'image/gif': '.gif', 'image/webp': '.webp', 'image/svg+xml': '.svg',
                'video/mp4': '.mp4', 'video/webm': '.webm', 'video/ogg': '.ogv'
            }
            ext = ext_map.get(mime, '.bin')
            file_bytes = base64.b64decode(encoded)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Falha no decode: {e}'}), 400
    else:
        return jsonify({'success': False, 'error': 'Formato de mídia inválido'}), 400
    
    old_config = load_login_bg_config()
    if old_config.get('filename'):
        old_path = os.path.join(LOGIN_BG_FOLDER, old_config['filename'])
        if os.path.exists(old_path):
            try: os.remove(old_path)
            except: pass
    
    filename = f"login_bg_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(LOGIN_BG_FOLDER, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(file_bytes)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
    actual_type = 'video' if mime.startswith('video/') else 'image'
    config = {
        'type': actual_type,
        'filename': filename,
        'opacity': data.get('opacity', old_config.get('opacity', 0.35)),
        'mime': mime
    }
    save_login_bg_config(config)
    return jsonify({'success': True, 'filename': filename, 'type': actual_type, 'config': config})

@app.route('/api/login_bg_config', methods=['GET'])
def get_login_bg_config_route():
    return jsonify({'success': True, 'config': load_login_bg_config()})

@app.route('/api/login_bg_config', methods=['POST'])
@admin_required
def set_login_bg_config_route():
    data = request.json
    config = load_login_bg_config()
    if 'opacity' in data:
        try:
            config['opacity'] = max(0.05, min(1.0, float(data['opacity'])))
        except: pass
    if 'type' in data and data['type'] in ['matrix', 'image', 'video']:
        if data['type'] == 'matrix':
            if config.get('filename'):
                old_path = os.path.join(LOGIN_BG_FOLDER, config['filename'])
                if os.path.exists(old_path):
                    try: os.remove(old_path)
                    except: pass
            config['filename'] = None
            config['mime'] = None
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
def serve_login_bg(filename):
    return send_from_directory(LOGIN_BG_FOLDER, filename)

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

@app.route('/dev.png')
def serve_dev_image():
    return send_from_directory(BASE_DIR, 'dev.png')

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

# ==================== HTML_TEMPLATE ====================
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
        
        /* ==================== LOGIN MODERNO ==================== */
        .login-modal { 
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: #060d1a;
            display: none; justify-content: center; align-items: center; 
            z-index: 20000; overflow: hidden; padding: 20px; 
        }
        #loginBgMedia { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; opacity: 0.35; pointer-events: none; display: none; }
        #loginBgVideo { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; opacity: 0.35; pointer-events: none; display: none; }
        .login-overlay-gradient { 
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; 
            background: radial-gradient(ellipse at top left, rgba(0,153,204,0.12), transparent 50%), radial-gradient(ellipse at bottom right, rgba(0,95,153,0.18), transparent 50%), linear-gradient(180deg, rgba(6,13,26,0.85), rgba(6,13,26,0.95));
            pointer-events: none;
        }
        
        .login-bg-toggle {
            position: absolute; top: 20px; right: 20px; z-index: 5;
            background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px);
            color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); 
            border-radius: 10px; width: 42px; height: 42px; font-size: 18px;
            cursor: pointer; display: flex; align-items: center; justify-content: center;
            transition: all 0.3s; box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        .login-bg-toggle:hover { background: rgba(56, 189, 248, 0.15); transform: translateY(-2px); color: #7dd3fc; }
        
        .login-split {
            position: relative; z-index: 2; width: 100%; max-width: 980px;
            display: grid; grid-template-columns: 1fr 1fr; gap: 0;
            background: rgba(10, 18, 32, 0.65); backdrop-filter: blur(28px); -webkit-backdrop-filter: blur(28px);
            border: 1px solid rgba(56, 189, 248, 0.18); border-radius: 20px; overflow: hidden;
            box-shadow: 0 32px 80px rgba(0,0,0,0.75), 0 0 100px rgba(0,153,204,0.08), inset 0 1px 0 rgba(255,255,255,0.06);
            animation: loginFadeIn 0.7s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes loginFadeIn { from { opacity: 0; transform: translateY(24px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
        @media (max-width: 820px) { .login-split { grid-template-columns: 1fr; max-width: 420px; } .login-brand-panel { display: none; } }
        
        .login-brand-panel {
            padding: 48px 40px; display: flex; flex-direction: column; justify-content: center;
            background: linear-gradient(160deg, rgba(0, 95, 153, 0.20), rgba(0, 40, 80, 0.30));
            border-right: 1px solid rgba(56, 189, 248, 0.12); position: relative; overflow: hidden;
        }
        .login-brand-logo { width: 84px; height: 84px; margin-bottom: 24px; position: relative; z-index: 1; filter: drop-shadow(0 0 24px rgba(0, 204, 255, 0.5)); }
        .login-brand-name { font-size: 32px; font-weight: 800; letter-spacing: 3px; color: #ffffff; margin-bottom: 8px; position: relative; z-index: 1; }
        .login-brand-tagline { font-size: 12px; color: #7dd3fc; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 600; position: relative; z-index: 1; }
        .login-brand-divider { width: 60px; height: 2px; background: linear-gradient(90deg, #00ccff, transparent); margin: 28px 0; position: relative; z-index: 1; }
        .login-brand-features { display: flex; flex-direction: column; gap: 14px; position: relative; z-index: 1; }
        .feature-item { display: flex; align-items: center; gap: 12px; color: #b8c9dd; font-size: 13px; font-weight: 500; }
        .feature-item svg { color: #38bdf8; flex-shrink: 0; }
        
        .login-form-panel {
            padding: 48px 44px; display: flex; flex-direction: column; justify-content: center;
            background: rgba(6, 13, 26, 0.4);
        }
        .login-form-header { text-align: center; margin-bottom: 32px; }
        .login-avatar {
            width: 78px; height: 78px; border-radius: 50%; margin: 0 auto 18px;
            overflow: hidden; border: 2px solid rgba(56, 189, 248, 0.4);
            box-shadow: 0 0 0 6px rgba(56, 189, 248, 0.06), 0 8px 24px rgba(0,0,0,0.4);
            display: flex; align-items: center; justify-content: center;
            background: #0f172a; position: relative;
        }
        .login-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .login-avatar svg { width: 78px; height: 78px; }
        .login-form-title { font-size: 22px; font-weight: 700; color: #ffffff; margin-bottom: 6px; }
        .login-form-subtitle { font-size: 12px; color: #64748b; letter-spacing: 0.5px; }
        
        .login-form-body { display: flex; flex-direction: column; gap: 16px; }
        .login-input-group { display: flex; flex-direction: column; gap: 7px; }
        .login-input-group label { font-size: 11px; color: #7dd3fc; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
        .login-input-wrapper { position: relative; }
        .login-input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #475569; pointer-events: none; transition: color 0.2s; }
        .login-input-field {
            width: 100%; padding: 13px 14px 13px 44px;
            background: rgba(15, 23, 42, 0.75);
            border: 1.5px solid rgba(56, 189, 248, 0.15);
            border-radius: 10px; color: #f1f5f9; font-size: 14px; font-weight: 500;
            transition: all 0.25s ease;
        }
        .login-input-field:focus {
            outline: none; border-color: #38bdf8; background: rgba(15, 23, 42, 0.95);
            box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.12), 0 0 24px rgba(56, 189, 248, 0.15);
        }
        .login-input-wrapper:focus-within .login-input-icon { color: #38bdf8; }
        .login-input-field::placeholder { color: #475569; font-weight: 400; }
        
        .login-submit-btn {
            width: 100%; padding: 14px; margin-top: 8px;
            background: linear-gradient(135deg, #0284c7, #0369a1);
            border: none; border-radius: 10px; color: #ffffff;
            font-size: 14px; font-weight: 700; letter-spacing: 0.8px; cursor: pointer;
            display: flex; align-items: center; justify-content: center; gap: 8px;
            transition: all 0.25s; box-shadow: 0 8px 24px rgba(2, 132, 199, 0.35);
        }
        .login-submit-btn:hover { transform: translateY(-2px); box-shadow: 0 12px 32px rgba(2, 132, 199, 0.5); background: linear-gradient(135deg, #0ea5e9, #0284c7); }
        .login-submit-btn:disabled { opacity: 0.55; cursor: not-allowed; transform: none; }
        .login-submit-btn .spinner { width: 15px; height: 15px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .login-error { color: #f87171; font-size: 12px; padding: 10px 14px; background: rgba(248, 113, 113, 0.08); border: 1px solid rgba(248,113,113,0.25); border-radius: 8px; display: none; text-align: center; font-weight: 500; }
        .login-form-footer { margin-top: 28px; padding-top: 20px; border-top: 1px solid rgba(56, 189, 248, 0.08); text-align: center; font-size: 11px; color: #475569; line-height: 1.8; }
        .login-form-footer strong { color: #7dd3fc; font-weight: 700; }
        
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

        .dynamic-background { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; object-fit: cover; pointer-events: none; opacity: 0.3; display: none; }

        .loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 26, 46, 0.95); z-index: 30000; display: none; flex-direction: column; justify-content: center; align-items: center; color: white; }
        .loading-spinner { border: 8px solid #f3f3f3; border-top: 8px solid #00ccff; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; margin-bottom: 20px; }
        .loading-text { font-size: 18px; font-weight: bold; animation: pulseText 1.5s infinite; }
        @keyframes pulseText { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
        
        /* ==================== 3D SIMULATOR STYLES ==================== */
        #sim3d-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 15000; background: #080b13; display: none; overflow: hidden; }
        #sim3d-overlay.active { display: block; }
        #sim3d-container { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }
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
        
        .sim3d-drawer { position: absolute; left: 16px; top: 80px; bottom: 16px; width: 320px; max-width: calc(100vw - 32px); z-index: 15; border-radius: 16px; padding: 14px; display: flex; flex-direction: column; transition: transform 0.3s ease; }
        .sim3d-drawer.closed { transform: translateX(calc(-100% - 30px)); }
        .sim3d-drawer-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid #1e293b; }
        .sim3d-drawer-header h2 { font-size: 11px; font-weight: 800; color: #67e8f9; text-transform: uppercase; letter-spacing: 1px; }
        .sim3d-drawer-close { width: 26px; height: 26px; border-radius: 7px; border: none; background: #1e293b; color: #cbd5e1; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 12px; }
        .sim3d-drawer-close:hover { background: #334155; color: white; }
        .sim3d-drawer-list { flex: 1; overflow-y: auto; padding-top: 10px; display: flex; flex-direction: column; gap: 8px; }
        .sim3d-drawer-hint { font-size: 10px; color: #64748b; padding: 4px 0 8px; }
        .sim3d-drawer-list::-webkit-scrollbar { width: 4px; }
        .sim3d-drawer-list::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.5); }
        .sim3d-drawer-list::-webkit-scrollbar-thumb { background: rgba(56, 189, 248, 0.5); border-radius: 4px; }
        
        .sim3d-eq-item { padding: 10px; border-radius: 10px; border: 1px solid #1e293b; background: rgba(15, 23, 42, 0.5); display: flex; justify-content: space-between; align-items: center; gap: 8px; transition: all 0.2s; }
        .sim3d-eq-item.mounted { border-color: rgba(6, 182, 212, 0.5); background: rgba(15, 23, 42, 0.9); box-shadow: 0 4px 15px rgba(6, 182, 212, 0.15); }
        .sim3d-eq-item:hover { border-color: rgba(56, 189, 248, 0.5); }
        .sim3d-eq-info { flex: 1; min-width: 0; cursor: pointer; }
        .sim3d-eq-name { font-size: 11px; font-weight: 700; color: #f1f5f9; display: flex; align-items: center; gap: 5px; }
        .sim3d-eq-unit { font-size: 9px; padding: 1px 5px; border-radius: 4px; background: #083344; color: #67e8f9; border: 1px solid #0e7490; font-family: monospace; font-weight: 700; }
        .sim3d-eq-desc { font-size: 9px; color: #64748b; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .sim3d-eq-actions { display: flex; gap: 4px; flex-shrink: 0; }
        .sim3d-eq-btn { padding: 4px 8px; border-radius: 6px; border: none; font-size: 10px; font-weight: 700; cursor: pointer; transition: all 0.2s; background: #06b6d4; color: white; }
        .sim3d-eq-btn:hover { background: #22d3ee; }
        .sim3d-eq-btn-small { width: 22px; height: 22px; padding: 0; display: flex; align-items: center; justify-content: center; background: #1e293b; color: #cbd5e1; font-size: 10px; }
        .sim3d-eq-btn-small:hover { background: #334155; }
        .sim3d-eq-btn-remove { width: 22px; height: 22px; padding: 0; display: flex; align-items: center; justify-content: center; background: rgba(239, 68, 68, 0.2); color: #f87171; font-size: 11px; }
        .sim3d-eq-btn-remove:hover { background: #ef4444; color: white; }
        
        .sim3d-connections-panel { position: absolute; left: 16px; bottom: 16px; width: 320px; max-width: calc(100vw - 32px); border-radius: 12px; padding: 12px; max-height: 200px; display: flex; flex-direction: column; z-index: 10; }
        .sim3d-connections-title { font-size: 10px; font-weight: 800; color: #67e8f9; text-transform: uppercase; margin-bottom: 8px; display: flex; justify-content: space-between; }
        .sim3d-connections-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
        .sim3d-connections-list::-webkit-scrollbar { width: 3px; }
        .sim3d-connections-list::-webkit-scrollbar-thumb { background: rgba(56, 189, 248, 0.5); border-radius: 3px; }
        .sim3d-connection-row { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 5px 7px; background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; border-radius: 6px; font-size: 9px; color: #cbd5e1; }
        .sim3d-connection-row .tag { font-family: monospace; font-weight: 700; color: #67e8f9; }
        .sim3d-connection-remove { padding: 2px 6px; border-radius: 4px; border: none; background: rgba(239, 68, 68, 0.2); color: #f87171; cursor: pointer; font-size: 9px; font-weight: 700; }
        .sim3d-connection-remove:hover { background: #ef4444; color: white; }
        
        .sim3d-patch-modal { position: fixed; inset: 0; z-index: 60; background: rgba(2, 6, 23, 0.85); backdrop-filter: blur(8px); display: none; align-items: center; justify-content: center; padding: 16px; }
        .sim3d-patch-modal.open { display: flex; }
        .sim3d-patch-content { width: 100%; max-width: 440px; border-radius: 16px; padding: 18px; border: 1px solid rgba(6, 182, 212, 0.4); position: relative; }
        .sim3d-patch-title { font-size: 13px; font-weight: 800; color: white; }
        .sim3d-patch-sub { font-size: 10px; color: #22d3ee; margin-bottom: 12px; }
        .sim3d-patch-section-label { font-size: 10px; font-weight: 800; color: #cbd5e1; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
        .sim3d-cable-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 12px; }
        .sim3d-cable-btn { padding: 8px; border-radius: 10px; border: 2px solid #334155; background: #0f172a; color: #cbd5e1; font-size: 10px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.2s; }
        .sim3d-cable-btn:hover { border-color: #64748b; }
        .sim3d-cable-btn.active { border-color: #22d3ee; color: white; }
        .sim3d-cable-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
        .sim3d-dest-list { max-height: 140px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; padding: 6px; background: rgba(2, 6, 23, 0.6); border-radius: 10px; border: 1px solid #1e293b; margin-bottom: 12px; }
        .sim3d-dest-list::-webkit-scrollbar { width: 3px; }
        .sim3d-dest-list::-webkit-scrollbar-thumb { background: rgba(56, 189, 248, 0.5); border-radius: 3px; }
        .sim3d-dest-item { display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; border-radius: 6px; background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; cursor: pointer; font-size: 10px; color: #cbd5e1; }
        .sim3d-dest-item:hover { background: rgba(30, 41, 59, 0.6); }
        .sim3d-dest-item input { accent-color: #06b6d4; width: 14px; height: 14px; cursor: pointer; }
        .sim3d-patch-confirm { width: 100%; padding: 10px; border-radius: 10px; border: none; background: linear-gradient(90deg, #0891b2, #2563eb); color: white; font-weight: 800; font-size: 11px; cursor: pointer; box-shadow: 0 6px 20px rgba(8, 145, 178, 0.4); transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 6px; }
        .sim3d-patch-confirm:hover { background: linear-gradient(90deg, #06b6d4, #3b82f6); }
        
        .sim3d-terminal { position: fixed; inset: 0; z-index: 60; background: rgba(2, 6, 23, 0.9); backdrop-filter: blur(8px); display: none; align-items: center; justify-content: center; padding: 16px; }
        .sim3d-terminal.open { display: flex; }
        .sim3d-terminal-content { width: 100%; max-width: 560px; border-radius: 16px; padding: 16px; border: 1px solid rgba(16, 185, 129, 0.4); }
        .sim3d-terminal-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid #1e293b; margin-bottom: 10px; }
        .sim3d-terminal-title { font-size: 12px; font-weight: 800; color: white; font-family: monospace; display: flex; align-items: center; gap: 8px; }
        .sim3d-terminal-output { background: #020617; padding: 12px; border-radius: 10px; font-family: monospace; font-size: 11px; color: #34d399; height: 240px; overflow-y: auto; border: 1px solid #0f172a; line-height: 1.6; }
        .sim3d-terminal-output::-webkit-scrollbar { width: 4px; }
        .sim3d-terminal-output::-webkit-scrollbar-thumb { background: rgba(16, 185, 129, 0.5); border-radius: 4px; }
        
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
                        <li>✅ <strong>NOVO:</strong> Simulador 3D de Rack (categoria Rede)</li>
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
                        <li><strong>🏢 3D Rack:</strong> Abra o simulador 3D para montar o rack de rede</li>
                        <li><strong>📐 Formas:</strong> Ative o modo de desenho para adicionar formas geométricas</li>
                        <li><strong>🔍 Zoom:</strong> Use os botões de zoom para ampliar o canvas ou aumentar ícones</li>
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
                <span>Versão 2.4 | Desenvolvido com 💙 por Thiago Souza</span>
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
    
    <!-- ==================== TELA DE LOGIN MODERNA ==================== -->
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
    <!-- ============================================================ -->
    
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
    
    <!-- ==================== SIMULADOR 3D OVERLAY ==================== -->
    <div id="sim3d-overlay">
        <div id="sim3d-container"></div>
        
        <div class="sim3d-header">
            <div class="sim3d-brand sim3d-glass">
                <div class="sim3d-brand-icon">🖥️</div>
                <div>
                    <h1>Rack 3D · Rede</h1>
                    <p>Dispositivos de rede com modelos realistas</p>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <button id="sim3d-toggle-drawer" class="sim3d-btn">
                    📦 Gerenciar Rack (<span id="sim3d-mounted-count">0</span>)
                </button>
                <button id="sim3d-run-script" class="sim3d-btn sim3d-btn-primary">
                    ⚡ Executar Script
                </button>
                <button id="sim3d-close-btn" class="sim3d-btn-close" title="Fechar Simulador 3D">✕</button>
            </div>
        </div>
        
        <div id="sim3d-equipment-drawer" class="sim3d-drawer sim3d-glass closed">
            <div class="sim3d-drawer-header">
                <h2>🌐 Dispositivos de Rede</h2>
                <button id="sim3d-close-drawer" class="sim3d-drawer-close">✕</button>
            </div>
            <p class="sim3d-drawer-hint">Somente equipamentos da categoria <strong>Rede</strong>. Cada tipo tem modelo 3D realista.</p>
            <div id="sim3d-equipment-list" class="sim3d-drawer-list"></div>
            <div style="padding-top:10px;border-top:1px solid #1e293b;margin-top:10px;text-align:center;">
                <button id="sim3d-reset-btn" class="sim3d-btn" style="font-size:10px;background:none;border:none;color:#94a3b8;">
                    🔄 Resetar Rack
                </button>
            </div>
        </div>
        
        <div id="sim3d-connections-panel" class="sim3d-connections-panel sim3d-glass" style="display:none;">
            <div class="sim3d-connections-title">
                <span>🔗 Conexões Ativas (<span id="sim3d-connections-count">0</span>)</span>
            </div>
            <div id="sim3d-connections-list" class="sim3d-connections-list"></div>
        </div>
        
        <div id="sim3d-patch-modal" class="sim3d-patch-modal">
            <div class="sim3d-patch-content sim3d-glass">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
                    <div>
                        <div id="sim3d-patch-title" class="sim3d-patch-title">Conectar Equipamento</div>
                        <div class="sim3d-patch-sub">Selecione tipo de cabo e destinos</div>
                    </div>
                    <button id="sim3d-patch-close" class="sim3d-btn-close" style="width:30px;height:30px;font-size:13px;">✕</button>
                </div>
                <div class="sim3d-patch-section-label">Tipo de Cabo</div>
                <div class="sim3d-cable-grid" id="sim3d-cable-grid">
                    <button class="sim3d-cable-btn active" data-cable="cat6">
                        <span class="sim3d-cable-dot" style="background:#22d3ee;"></span> Cat6 UTP
                    </button>
                    <button class="sim3d-cable-btn" data-cable="fiber-sfp">
                        <span class="sim3d-cable-dot" style="background:#f59e0b;"></span> Fibra SFP+
                    </button>
                    <button class="sim3d-cable-btn" data-cable="power-ac">
                        <span class="sim3d-cable-dot" style="background:#ef4444;"></span> Energia AC
                    </button>
                    <button class="sim3d-cable-btn" data-cable="coax-bnc">
                        <span class="sim3d-cable-dot" style="background:#a855f7;"></span> Coaxial BNC
                    </button>
                </div>
                <div class="sim3d-patch-section-label">Conectar a (múltiplos destinos)</div>
                <div id="sim3d-dest-list" class="sim3d-dest-list"></div>
                <button id="sim3d-confirm-patch" class="sim3d-patch-confirm">
                    ✅ Estabelecer Conexão(ões)
                </button>
            </div>
        </div>
        
        <div id="sim3d-terminal" class="sim3d-terminal">
            <div class="sim3d-terminal-content sim3d-glass">
                <div class="sim3d-terminal-header">
                    <div class="sim3d-terminal-title">
                        <span style="width:8px;height:8px;border-radius:50%;background:#34d399;box-shadow:0 0 8px #34d399;"></span>
                        CLI Terminal // Network Automation
                    </div>
                    <button id="sim3d-terminal-close" class="sim3d-btn-close" style="width:28px;height:28px;font-size:12px;">✕</button>
                </div>
                <div id="sim3d-terminal-output" class="sim3d-terminal-output">
                    <p style="color:#64748b;">[SYSTEM] Inicializando diagnóstico...</p>
                </div>
            </div>
        </div>
        
        <div id="sim3d-toast" class="sim3d-toast sim3d-glass">
            <span style="color:#34d399;">✅</span>
            <span id="sim3d-toast-message">Notificação</span>
        </div>
    </div>
    <!-- ============================================================ -->
    
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
        let lastMousePos = null;
        
        function getDeviceType() {
            const ua = navigator.userAgent;
            if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) return "Tablet";
            if (/Mobile|Android|iP(hone|od)|IEMobile|BlackBerry|Kindle|Silk-Accelerated/i.test(ua)) return "Celular";
            return "Desktop / Notebook";
        }
        document.getElementById('loadingDeviceType').innerText = "Dispositivo detectado: " + getDeviceType();

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
        let customConnections = [];
        let connectionCategories = {};
        
        const STORAGE_KEYS = {
            ICON_SIZE: 'projetize_icon_size',
            CANVAS_ZOOM: 'projetize_canvas_zoom',
            COMPONENTS: (user) => `projetize_${user}_components`,
            CONNECTIONS_DATA: (user) => `projetize_${user}_connections`,
            SHAPES: (user) => `projetize_${user}_shapes`,
            BACKGROUND: (user) => `projetize_${user}_background`,
            SIM3D_MOUNTED: (user) => `projetize_${user}_sim3d_mounted`,
            SIM3D_CONNECTIONS: (user) => `projetize_${user}_sim3d_connections`
        };
        
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
            const savedIconSize = localStorage.getItem(STORAGE_KEYS.ICON_SIZE);
            if(savedIconSize) iconSize = parseInt(savedIconSize);
            const savedZoom = localStorage.getItem(STORAGE_KEYS.CANVAS_ZOOM);
            if(savedZoom) zoom = parseFloat(savedZoom);
            
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
                if(results[1]) components = JSON.parse(results[1]);
                if(results[2]) connections = JSON.parse(results[2]);
                if(results[3]) shapes = JSON.parse(results[3]);
                if(results[4]) {
                    const bgData = JSON.parse(results[4]);
                    backgroundImage = bgData.url;
                    backgroundOpacity = bgData.opacity || 0.8;
                    backgroundWidth = bgData.width || 0;
                    backgroundHeight = bgData.height || 0;
                    backgroundX = bgData.x || canvas.width/2 - (bgData.width || 0)/2;
                    backgroundY = bgData.y || canvas.height/2 - (bgData.height || 0)/2;
                    if(backgroundImage) { backgroundImageObj = new Image(); backgroundImageObj.src = backgroundImage; }
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
            } catch(e) { console.error("Erro ao salvar biblioteca global:", e); }
        }
        
        function getConnectionKey(name) { return name.toLowerCase().replace(/[^a-z0-9]/g, ''); }
        function getIconUrl(filename) { if (!filename) return null; return `/uploads/icons/${filename}`; }
        function renderConnectionIcon(conn) { if (conn.iconFile) { return `<img src="/uploads/icons/${conn.iconFile}" style="width:24px;height:24px;object-fit:contain;">`; } return conn.icon || '🔌'; }
        function renderDeviceIcon(device) { if(device.iconFile) return `<img src="/uploads/icons/${device.iconFile}" style="width:24px;height:24px;object-fit:contain;">`; return device.icon || '📦'; }
                function addCustomConnection(category, connData) {
            if (!connectionCategories[category]) connectionCategories[category] = { icon: '🔌', connections: [] };
            const key = getConnectionKey(connData.name);
            connectionCategories[category].connections.push(connData);
            cableColors[key] = { color: connData.color, name: connData.name, icon: connData.icon, type: connData.type || 'cable', speed: connData.speed || 'N/A', desc: connData.desc || '', animation: connData.animation || null, iconFile: connData.iconFile || null };
            saveUserData(); saveGlobalLibrary(); renderConnectionsPalette();
            showToast(`✅ Conexão "${connData.name}" adicionada!`);
        }
        
        function deleteCustomConnection(category, idx) {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores podem excluir conexões'); return; }
            if (confirm('Deseja excluir esta conexão?')) {
                const conn = connectionCategories[category].connections[idx];
                const key = getConnectionKey(conn.name);
                delete cableColors[key];
                connectionCategories[category].connections.splice(idx, 1);
                if (connectionCategories[category].connections.length === 0) delete connectionCategories[category];
                saveUserData(); saveGlobalLibrary(); renderConnectionsPalette(); showToast(`🗑 Conexão removida!`);
            }
        }
        
        function editCustomConnection(category, idx) {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores podem editar conexões'); return; }
            const conn = connectionCategories[category].connections[idx];
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">✏️ Editar Conexão</h3>
                    <input type="text" id="connName" value="${conn.name}" placeholder="Nome da conexão">
                    <input type="text" id="connIcon" value="${conn.icon || '🔌'}" placeholder="Ícone (emoji)">
                    <div class="property-group"><label>OU Imagem personalizada (permanente)</label><input type="file" id="connIconImage" accept="image/*"><div class="image-preview" id="connIconPreview">${conn.iconFile ? `<img src="/uploads/icons/${conn.iconFile}" style="max-width:50px;max-height:50px;">` : ''}</div></div>
                    <input type="color" id="connColor" value="${conn.color || '#005f99'}">
                    <input type="text" id="connSpeed" value="${conn.speed || 'N/A'}" placeholder="Velocidade">
                    <input type="text" id="connDesc" value="${conn.desc || ''}" placeholder="Descrição">
                    <select id="connType"><option value="cable" ${conn.type === 'cable' ? 'selected' : ''}>Cabeado</option><option value="wireless" ${conn.type === 'wireless' ? 'selected' : ''}>Sem Fio</option></select>
                    <select id="connAnimation"><option value="">Nenhuma</option><option value="wave" ${conn.animation === 'wave' ? 'selected' : ''}>Ondas</option><option value="packet" ${conn.animation === 'packet' ? 'selected' : ''}>Pacotes</option></select>
                    <div class="modal-buttons"><button class="btn btn-primary" onclick="updateCustomConnection('${category.replace(/'/g, "\\'")}', ${idx})">Salvar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div>
                </div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const imageInput = document.getElementById('connIconImage');
            if (imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if (file) { const base64 = await readImageAsBase64(file); const preview = document.getElementById('connIconPreview'); if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;max-height:50px;">`; const response = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'connection' }) }); const data = await response.json(); if (data.success) { window.tempConnectionIconFile = data.filename; showToast('✅ Ícone da conexão enviado!'); } } }; }
        }
        
        window.updateCustomConnection = async (category, idx) => {
            const name = document.getElementById('connName').value; const icon = document.getElementById('connIcon').value; const color = document.getElementById('connColor').value; const speed = document.getElementById('connSpeed').value; const desc = document.getElementById('connDesc').value; const type = document.getElementById('connType').value; const animation = document.getElementById('connAnimation').value; const iconFile = window.tempConnectionIconFile || connectionCategories[category].connections[idx].iconFile;
            if (!name) { showToast('Digite um nome para a conexão'); return; }
            const oldKey = getConnectionKey(connectionCategories[category].connections[idx].name); delete cableColors[oldKey];
            const connData = { name, icon: icon || '🔌', color, speed, desc, type, animation: animation || null, iconFile: iconFile };
            connectionCategories[category].connections[idx] = connData;
            const newKey = getConnectionKey(name);
            cableColors[newKey] = { color: color, name: name, icon: icon || '🔌', type: type, speed: speed || 'N/A', desc: desc || '', animation: animation || null, iconFile: iconFile };
            window.tempConnectionIconFile = null; saveUserData(); saveGlobalLibrary(); closeModal(); renderConnectionsPalette(); showToast(`✅ Conexão atualizada!`);
        };
        
        function openCategoryIconModal(catName) {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores podem alterar ícones de categorias'); return; }
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🎨 Ícone da Categoria: ${catName}</h3><div class="property-group"><label>Use um emoji</label><input type="text" id="catEmoji" placeholder="🎥" value="${categories[catName]?.icon || '📁'}" maxlength="2"></div><div class="property-group"><label>OU faça upload de uma imagem</label><input type="file" id="catIconImage" accept="image/*"><div class="image-preview" id="catIconPreview">${categories[catName]?.iconFile ? `<img src="/uploads/icons/${categories[catName].iconFile}" style="max-width:50px;max-height:50px;">` : ''}</div></div><div class="modal-buttons"><button class="btn btn-primary" onclick="applyCategoryIcon('${catName.replace(/'/g, "\\'")}')">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const imageInput = document.getElementById('catIconImage');
            if (imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if (file) { const base64 = await readImageAsBase64(file); const preview = document.getElementById('catIconPreview'); if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;max-height:50px;">`; const response = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'category' }) }); const data = await response.json(); if (data.success) { window.tempCategoryIconFile = data.filename; showToast('✅ Ícone enviado!'); } } }; }
        }
        
        window.applyCategoryIcon = async (catName) => {
            const emoji = document.getElementById('catEmoji').value; const iconFile = window.tempCategoryIconFile || categories[catName]?.iconFile || null;
            if (emoji) { categories[catName].icon = emoji; categories[catName].iconFile = null; } else if (iconFile) { categories[catName].iconFile = iconFile; categories[catName].icon = null; }
            window.tempCategoryIconFile = null; saveUserData(); await saveGlobalLibrary(); closeModal(); renderPalette(); showToast(`✅ Ícone atualizado!`);
        };
        
        function openConnectionIconModal(category, idx) {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const conn = connectionCategories[category].connections[idx];
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🎨 Ícone: ${conn.name}</h3><div class="property-group"><label>Emoji</label><input type="text" id="connEmoji" value="${conn.icon || '🔌'}" maxlength="2"></div><div class="property-group"><label>OU Imagem</label><input type="file" id="connIconImage" accept="image/*"><div class="image-preview" id="connIconPreview">${conn.iconFile ? `<img src="/uploads/icons/${conn.iconFile}" style="max-width:50px;">` : ''}</div></div><div class="modal-buttons"><button class="btn btn-primary" onclick="applyConnectionIcon('${category.replace(/'/g, "\\'")}', ${idx})">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const imageInput = document.getElementById('connIconImage');
            if (imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if (file) { const base64 = await readImageAsBase64(file); const preview = document.getElementById('connIconPreview'); if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;">`; const response = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'connection' }) }); const data = await response.json(); if (data.success) { window.tempConnectionIconFile = data.filename; } } }; }
        }
        
        window.applyConnectionIcon = async (category, idx) => {
            const emoji = document.getElementById('connEmoji').value; const iconFile = window.tempConnectionIconFile || connectionCategories[category].connections[idx].iconFile || null; const conn = connectionCategories[category].connections[idx];
            if (emoji) { conn.icon = emoji; conn.iconFile = null; } else if (iconFile) { conn.iconFile = iconFile; conn.icon = null; }
            const key = getConnectionKey(conn.name); if (cableColors[key]) { cableColors[key].icon = conn.icon || '🔌'; cableColors[key].iconFile = conn.iconFile; }
            window.tempConnectionIconFile = null; saveUserData(); await saveGlobalLibrary(); closeModal(); renderConnectionsPalette(); showToast(`✅ Ícone atualizado!`);
        };
        
        function renderConnectionsPalette() {
            const container = document.getElementById('connections-container'); if (!container) return; container.innerHTML = '';
            const allConnections = { ...connectionCategories };
            customConnections.forEach(conn => { if (!allConnections['Personalizadas']) allConnections['Personalizadas'] = { icon: '🔌', connections: [] }; allConnections['Personalizadas'].connections.push(conn); });
            for (const [catName, catData] of Object.entries(allConnections)) {
                if (!catData.connections || catData.connections.length === 0) continue;
                const categoryDiv = document.createElement('div'); categoryDiv.className = 'category';
                categoryDiv.innerHTML = `<div class="category-header"><h3>${catData.icon || '🔌'} ${catName}</h3>${(userRole === 'admin' || userRole === 'master') ? `<div class="category-actions"><button onclick="addConnectionToCategory('${catName.replace(/'/g, "\\'")}')" title="Adicionar">➕</button></div>` : ''}</div><div id="conn-category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>`;
                container.appendChild(categoryDiv);
                const connContainer = document.getElementById(`conn-category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
                catData.connections.forEach((conn, idx) => {
                    const connEl = document.createElement('div'); connEl.className = 'component'; connEl.style.cursor = 'pointer';
                    connEl.onclick = () => { selectedConnectionType = getConnectionKey(conn.name); showToast(`✅ Tipo de conexão: ${conn.name}`); };
                    connEl.innerHTML = `<div class="component-icon">${renderConnectionIcon(conn)}</div><div class="component-info"><div class="component-name">${conn.name}</div><div class="component-desc">${conn.desc || conn.speed || ''}</div></div>${(userRole === 'admin' || userRole === 'master') ? `<div class="component-actions"><button onclick="editCustomConnection('${catName.replace(/'/g, "\\'")}', ${idx})" title="Editar">✏️</button><button onclick="openConnectionIconModal('${catName.replace(/'/g, "\\'")}', ${idx})" title="Ícone">🎨</button><button onclick="deleteCustomConnection('${catName.replace(/'/g, "\\'")}', ${idx})" title="Excluir">🗑</button></div>` : ''}`;
                    connContainer.appendChild(connEl);
                });
            }
        }
        
        function renderPalette() {
            const container = document.getElementById('categories-container'); if(!container) return; container.innerHTML = '';
            for(const [catName, catData] of Object.entries(categories)) {
                const categoryDiv = document.createElement('div'); categoryDiv.className = 'category';
                const catIcon = catData.iconFile ? `<img src="/uploads/icons/${catData.iconFile}" style="width:16px;height:16px;">` : (catData.icon || '📁');
                categoryDiv.innerHTML = `<div class="category-header"><h3>${catIcon} ${catName}</h3>${(userRole === 'admin' || userRole === 'master') ? `<div class="category-actions"><button onclick="editCategory('${catName.replace(/'/g, "\\'")}')" title="Editar">✏️</button><button onclick="openCategoryIconModal('${catName.replace(/'/g, "\\'")}')" title="Ícone">🎨</button><button onclick="deleteCategory('${catName.replace(/'/g, "\\'")}')" title="Excluir">🗑</button><button onclick="addDeviceToCategory('${catName.replace(/'/g, "\\'")}')" title="Adicionar">➕</button></div>` : ''}</div><div id="category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>`;
                container.appendChild(categoryDiv);
                const devicesContainer = document.getElementById(`category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
                if (catData.devices) {
                    catData.devices.forEach((device, idx) => {
                        const deviceEl = document.createElement('div'); deviceEl.className = 'component'; deviceEl.setAttribute('draggable', 'true');
                        if (!device.id) device.id = Date.now() + idx;
                        deviceEl.innerHTML = `<div class="component-icon">${renderDeviceIcon(device)}</div><div class="component-info"><div class="component-name">${device.name}</div><div class="component-desc">${device.desc || ''}</div></div>${(userRole === 'admin' || userRole === 'master') ? `<div class="component-actions"><button onclick="editDevice('${catName.replace(/'/g, "\\'")}', ${idx})" title="Editar">✏️</button><button onclick="openDeviceIconModal('${catName.replace(/'/g, "\\'")}', ${idx})" title="Ícone">🎨</button><button onclick="deleteDevice('${catName.replace(/'/g, "\\'")}', ${idx})" title="Excluir">🗑</button></div>` : ''}`;
                        deviceEl.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/plain', JSON.stringify({ name: device.name, icon: device.icon, type: device.type, subtype: device.subtype || '', color: device.color, iconFile: device.iconFile || null })); });
                        devicesContainer.appendChild(deviceEl);
                    });
                }
            }
            if(customDevices.length > 0) {
                const customDiv = document.createElement('div'); customDiv.className = 'category';
                customDiv.innerHTML = `<div class="category-header"><h3>🎨 Personalizados</h3>${(userRole === 'admin' || userRole === 'master') ? `<div class="category-actions"><button onclick="openAddDeviceModal()" title="Adicionar">➕</button></div>` : ''}</div><div id="custom-devices-container"></div>`;
                container.appendChild(customDiv);
                const customContainer = document.getElementById('custom-devices-container');
                customDevices.forEach((device, idx) => {
                    const deviceEl = document.createElement('div'); deviceEl.className = 'component'; deviceEl.setAttribute('draggable', 'true');
                    deviceEl.innerHTML = `<div class="component-icon">${renderDeviceIcon(device)}</div><div class="component-info"><div class="component-name">${device.name}</div><div class="component-desc">${device.desc || 'Personalizado'}</div></div>${(userRole === 'admin' || userRole === 'master') ? `<div class="component-actions"><button onclick="editCustomDevice(${idx})" title="Editar">✏️</button><button onclick="openCustomDeviceIconModal(${idx})" title="Ícone">🎨</button><button onclick="deleteCustomDevice(${idx})" title="Excluir">🗑</button></div>` : ''}`;
                    deviceEl.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/plain', JSON.stringify({ name: device.name, icon: device.icon, type: device.type || 'custom', subtype: 'custom', color: device.color || '#005f99', iconFile: device.iconFile || null })); });
                    customContainer.appendChild(deviceEl);
                });
            }
        }
        
        function openDeviceIconModal(catName, idx) {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const device = categories[catName].devices[idx];
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🎨 Ícone: ${device.name}</h3><div class="property-group"><label>Emoji</label><input type="text" id="devEmoji" value="${device.icon || '📦'}" maxlength="2"></div><div class="property-group"><label>OU Imagem</label><input type="file" id="devIconImage" accept="image/*"><div class="image-preview" id="devIconPreview">${device.iconFile ? `<img src="/uploads/icons/${device.iconFile}" style="max-width:50px;">` : ''}</div></div><div class="modal-buttons"><button class="btn btn-primary" onclick="applyDeviceIcon('${catName.replace(/'/g, "\\'")}', ${idx})">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const imageInput = document.getElementById('devIconImage');
            if (imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if (file) { const base64 = await readImageAsBase64(file); const preview = document.getElementById('devIconPreview'); if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;">`; const response = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'equipment' }) }); const data = await response.json(); if (data.success) { window.tempDeviceIconFile = data.filename; } } }; }
        }
        
        window.applyDeviceIcon = async (catName, idx) => {
            const emoji = document.getElementById('devEmoji').value; const iconFile = window.tempDeviceIconFile || categories[catName].devices[idx].iconFile || null; const device = categories[catName].devices[idx];
            if (emoji) { device.icon = emoji; device.iconFile = null; } else if (iconFile) { device.iconFile = iconFile; device.icon = null; }
            window.tempDeviceIconFile = null; saveUserData(); await saveGlobalLibrary(); closeModal(); renderPalette(); showToast(`✅ Ícone atualizado!`);
        };
        
        function openCustomDeviceIconModal(idx) {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const device = customDevices[idx];
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🎨 Ícone: ${device.name}</h3><div class="property-group"><label>Emoji</label><input type="text" id="devEmoji" value="${device.icon || '📦'}" maxlength="2"></div><div class="property-group"><label>OU Imagem</label><input type="file" id="devIconImage" accept="image/*"><div class="image-preview" id="devIconPreview">${device.iconFile ? `<img src="/uploads/icons/${device.iconFile}" style="max-width:50px;">` : ''}</div></div><div class="modal-buttons"><button class="btn btn-primary" onclick="applyCustomDeviceIcon(${idx})">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const imageInput = document.getElementById('devIconImage');
            if (imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if (file) { const base64 = await readImageAsBase64(file); const preview = document.getElementById('devIconPreview'); if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;">`; const response = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'equipment' }) }); const data = await response.json(); if (data.success) { window.tempDeviceIconFile = data.filename; } } }; }
        }
        
        window.applyCustomDeviceIcon = async (idx) => {
            const emoji = document.getElementById('devEmoji').value; const iconFile = window.tempDeviceIconFile || customDevices[idx].iconFile || null; const device = customDevices[idx];
            if (emoji) { device.icon = emoji; device.iconFile = null; } else if (iconFile) { device.iconFile = iconFile; device.icon = null; }
            window.tempDeviceIconFile = null; saveUserData(); await saveGlobalLibrary(); closeModal(); renderPalette(); showToast(`✅ Ícone atualizado!`);
        };
        
        function applyZoomToCanvas() { canvas.style.transform = `scale(${zoom})`; canvas.style.transformOrigin = '0 0'; }
        function iconZoomIn() { iconSize = Math.min(iconSize + 4, 80); saveUserData(); showToast(`🔍 Ícone: ${iconSize}px`); }
        function iconZoomOut() { iconSize = Math.max(iconSize - 4, 20); saveUserData(); showToast(`🔍 Ícone: ${iconSize}px`); }
        function resetIconSize() { iconSize = 36; saveUserData(); showToast(`🔄 Ícone: ${iconSize}px`); }
        function zoomIn() { zoom = Math.min(zoom + 0.1, 3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
        function zoomOut() { zoom = Math.max(zoom - 0.1, 0.3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
        function resetZoom() { zoom = 1; applyZoomToCanvas(); saveUserData(); showToast(`🔄 Zoom: 100%`); }
        
        function showToast(message) { const toast = document.createElement('div'); toast.className = 'toast'; toast.textContent = message; document.body.appendChild(toast); setTimeout(() => toast.remove(), 3000); }
        function closeModal() { if(window.currentModal) { document.body.removeChild(window.currentModal); window.currentModal = null; } }
        function readImageAsBase64(file) { return new Promise((resolve) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.readAsDataURL(file); }); }
        
        // ==================== CANVAS DRAW ====================
        function drawGrid() {
            if(!showGrid) return;
            const step = 50; ctx.save(); ctx.strokeStyle = '#e0e0e0'; ctx.lineWidth = 0.5;
            for(let x=0; x<canvas.width; x+=step) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,canvas.height); ctx.stroke(); }
            for(let y=0; y<canvas.height; y+=step) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(canvas.width,y); ctx.stroke(); }
            ctx.restore();
        }
        
        function drawBackground() {
            if(backgroundImageObj && backgroundImageObj.complete && backgroundImageObj.src && backgroundWidth > 0 && backgroundHeight > 0) {
                ctx.save(); ctx.globalAlpha = backgroundOpacity; ctx.drawImage(backgroundImageObj, backgroundX, backgroundY, backgroundWidth, backgroundHeight); ctx.globalAlpha = 1;
                if(isBackgroundSelected) {
                    ctx.strokeStyle = '#005f99'; ctx.lineWidth = 3; ctx.setLineDash([8, 6]); ctx.strokeRect(backgroundX, backgroundY, backgroundWidth, backgroundHeight); ctx.setLineDash([]);
                    const hs = 10; const handles = [{x: backgroundX, y: backgroundY},{x: backgroundX + backgroundWidth, y: backgroundY},{x: backgroundX, y: backgroundY + backgroundHeight},{x: backgroundX + backgroundWidth, y: backgroundY + backgroundHeight}];
                    handles.forEach(h => { ctx.fillStyle = '#005f99'; ctx.fillRect(h.x - hs/2, h.y - hs/2, hs, hs); ctx.fillStyle = 'white'; ctx.fillRect(h.x - hs/3, h.y - hs/3, hs/1.5, hs/1.5); });
                }
                ctx.restore();
            }
        }
        
        function drawFieldOfView(cam) {
            if(!cam.angle) cam.angle = 0; if(!cam.fov) cam.fov = 80;
            const angleRad = cam.angle * Math.PI / 180; const fovRad = cam.fov * Math.PI / 180; const distance = 100;
            const leftAngle = angleRad - fovRad/2; const rightAngle = angleRad + fovRad/2;
            const x1 = cam.x + Math.cos(leftAngle) * distance; const y1 = cam.y + Math.sin(leftAngle) * distance;
            const x2 = cam.x + Math.cos(rightAngle) * distance; const y2 = cam.y + Math.sin(rightAngle) * distance;
            ctx.save(); ctx.beginPath(); ctx.moveTo(cam.x, cam.y); ctx.lineTo(x1, y1); ctx.lineTo(x2, y2); ctx.fillStyle = 'rgba(0, 95, 153, 0.2)'; ctx.fill(); ctx.strokeStyle = '#005f99'; ctx.lineWidth = 1.5; ctx.stroke();
            const cx = cam.x + Math.cos(angleRad) * distance; const cy = cam.y + Math.sin(angleRad) * distance;
            ctx.beginPath(); ctx.moveTo(cam.x, cam.y); ctx.lineTo(cx, cy); ctx.strokeStyle = '#ffaa00'; ctx.setLineDash([5,5]); ctx.stroke(); ctx.setLineDash([]);
            ctx.beginPath(); ctx.arc(cx, cy, 6, 0, 2*Math.PI); ctx.fillStyle = '#ffaa00'; ctx.fill(); ctx.fillStyle = '#000'; ctx.font = `bold ${10}px Arial`; ctx.fillText('↻', cx-3, cy+3);
            ctx.restore();
        }
        
        function drawSensorAnimation(x, y, time) {
            const pulseCount = 3; const baseRadius = 25;
            for(let i = 0; i < pulseCount; i++) {
                const delay = i * 0.5; const progress = (time + delay) % 1; const radius = baseRadius + (progress * 30); const opacity = 0.5 * (1 - progress);
                ctx.save(); ctx.beginPath(); ctx.arc(x, y, radius, 0, 2 * Math.PI); ctx.strokeStyle = `rgba(0, 95, 153, ${opacity})`; ctx.lineWidth = 2; ctx.stroke(); ctx.restore();
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
        
        function drawConnections() {
            connections.forEach((conn, idx) => {
                const fromComp = components.find(c => c.id === conn.from); const toComp = components.find(c => c.id === conn.to);
                if(!fromComp || !toComp) return;
                const cableInfo = cableColors[conn.type] || cableColors['cat6']; if (!cableInfo) return;
                const isWireless = cableInfo.type === 'wireless'; const isSelected = (selectedConnectionIndex === idx);
                ctx.save();
                if(isWireless) {
                    ctx.setLineDash(cableInfo.dashPattern || [10, 8]); ctx.strokeStyle = cableInfo.color; ctx.lineWidth = isSelected ? 4 : 2;
                    ctx.beginPath(); ctx.moveTo(fromComp.x, fromComp.y); ctx.lineTo(toComp.x, toComp.y); ctx.stroke();
                    if (cableInfo.animation === 'wave') { for(let i = 0; i < 2; i++) { const t = (trafficAnimation + i * 0.4) % 1; drawWirelessAnimationOnLine(fromComp.x, fromComp.y, toComp.x, toComp.y, conn.type, t); } }
                    else { for(let i = 0; i < 3; i++) { const t = (trafficAnimation + i * 0.25) % 1; drawWirelessAnimationOnLine(fromComp.x, fromComp.y, toComp.x, toComp.y, conn.type, t); } }
                } else {
                    ctx.setLineDash([]); ctx.beginPath(); ctx.moveTo(fromComp.x, fromComp.y); ctx.lineTo(toComp.x, toComp.y); ctx.strokeStyle = cableInfo.color; ctx.lineWidth = isSelected ? 4 : 2; ctx.stroke();
                    const t = trafficAnimation; const x = fromComp.x + (toComp.x - fromComp.x) * t; const y = fromComp.y + (toComp.y - fromComp.y) * t;
                    ctx.beginPath(); ctx.arc(x, y, 4, 0, 2*Math.PI); ctx.fillStyle = cableInfo.color; ctx.fill();
                }
                ctx.fillStyle = '#6c757d'; ctx.font = `${9}px Arial`; const iconDisplay = cableInfo.iconFile ? '🖼️' : cableInfo.icon;
                ctx.fillText(`${iconDisplay} ${cableInfo.name}`, (fromComp.x+toComp.x)/2 - 20, (fromComp.y+toComp.y)/2 - 5);
                if(isSelected) { ctx.strokeStyle = '#005f99'; ctx.lineWidth = 2; ctx.setLineDash([5, 5]); ctx.beginPath(); ctx.moveTo(fromComp.x, fromComp.y); ctx.lineTo(toComp.x, toComp.y); ctx.stroke(); ctx.setLineDash([]); }
                ctx.restore();
            });
            trafficAnimation = (trafficAnimation + 0.015) % 1;
        }
        
        function drawShapes() {
            shapes.forEach(shape => {
                const isSelected = selectedShapes.includes(shape);
                ctx.save(); ctx.fillStyle = shape.fillColor || 'rgba(0, 0, 0, 0.05)'; ctx.strokeStyle = shape.strokeColor || '#005f99'; ctx.lineWidth = shape.lineWidth || 2;
                if(shape.rotation) { ctx.translate(shape.x + (shape.type === 'door' ? 15 : 30), shape.y + (shape.type === 'door' ? 25 : 20)); ctx.rotate(shape.rotation * Math.PI / 180); ctx.translate(-(shape.x + (shape.type === 'door' ? 15 : 30)), -(shape.y + (shape.type === 'door' ? 25 : 20))); }
                switch(shape.type) {
                    case 'line': ctx.beginPath(); ctx.moveTo(shape.x1, shape.y1); ctx.lineTo(shape.x2, shape.y2); ctx.stroke(); break;
                    case 'door': ctx.fillStyle = 'rgba(139, 69, 19, 0.3)'; ctx.fillRect(shape.x, shape.y, 30, 50); ctx.strokeStyle = '#8B4513'; ctx.strokeRect(shape.x, shape.y, 30, 50); ctx.beginPath(); ctx.arc(shape.x + 30, shape.y + 25, 20, -Math.PI/2, Math.PI/2); ctx.stroke(); break;
                    case 'window': ctx.fillStyle = 'rgba(135, 206, 235, 0.3)'; ctx.fillRect(shape.x, shape.y, 60, 40); ctx.strokeStyle = '#87CEEB'; ctx.strokeRect(shape.x, shape.y, 60, 40); ctx.beginPath(); ctx.moveTo(shape.x + 30, shape.y); ctx.lineTo(shape.x + 30, shape.y + 40); ctx.moveTo(shape.x, shape.y + 20); ctx.lineTo(shape.x + 60, shape.y + 20); ctx.stroke(); break;
                    case 'text': ctx.font = `${(shape.fontSize || 14)}px Arial`; ctx.fillStyle = shape.textColor || '#212529'; ctx.fillText(shape.text || 'Texto', shape.x, shape.y); break;
                }
                if(shape.rotation) ctx.setTransform(1, 0, 0, 1, 0, 0);
                if(isSelected) {
                    ctx.strokeStyle = '#005f99'; ctx.lineWidth = 2;
                    if(shape.type === 'line') { ctx.beginPath(); ctx.moveTo(shape.x1 - 3, shape.y1 - 3); ctx.lineTo(shape.x2 + 3, shape.y2 + 3); ctx.moveTo(shape.x1 + 3, shape.y1 - 3); ctx.lineTo(shape.x2 - 3, shape.y2 + 3); ctx.stroke(); }
                    else if(shape.type === 'text') { ctx.strokeRect(shape.x - 5, shape.y - 12, ctx.measureText(shape.text || 'Texto').width + 10, 18); }
                    else { const w = 30; const h = shape.type === 'door' ? 50 : 40; ctx.strokeRect(shape.x - 3, shape.y - 3, w + 6, h + 6); }
                    showShapeDeleteButton(shape);
                } else { document.getElementById('deleteShapeBtn').style.display = 'none'; }
                ctx.restore();
            });
        }
        
        function drawComponents() {
            components.forEach(comp => {
                const isSelected = selectedComponents.includes(comp);
                if(comp.type === 'sensor') drawSensorAnimation(comp.x, comp.y, sensorAnimationTime);
                ctx.save(); ctx.translate(comp.x, comp.y); ctx.rotate((comp.rotation || 0) * Math.PI / 180); ctx.translate(-comp.x, -comp.y);
                const halfSize = iconSize / 2;
                if(comp.iconFile) { ctx.drawImage(getCachedImage(`/uploads/icons/${comp.iconFile}`), comp.x-halfSize, comp.y-halfSize, iconSize, iconSize); }
                else if(comp.customImage && comp.customImage.startsWith('data:image')) { ctx.drawImage(getCachedImage(comp.customImage), comp.x-halfSize, comp.y-halfSize, iconSize, iconSize); }
                else if(comp.customImageTemp && comp.customImageTemp.startsWith('data:image')) { ctx.drawImage(getCachedImage(comp.customImageTemp), comp.x-halfSize, comp.y-halfSize, iconSize, iconSize); }
                else {
                    ctx.fillStyle = comp.color || '#005f99'; ctx.beginPath(); ctx.arc(comp.x, comp.y, iconSize/2, 0, 2*Math.PI); ctx.fill();
                    ctx.fillStyle = '#fff'; ctx.font = `${iconSize/2}px Arial`; const iconToShow = comp.customIconTemp || comp.icon || '📦'; ctx.fillText(iconToShow, comp.x-12, comp.y+8);
                }
                ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = '#005f99'; ctx.font = `${12}px Arial`; ctx.fillText(comp.name, comp.x-30, comp.y - (iconSize/2) - 5);
                if(comp.ip) { ctx.fillStyle = '#6c757d'; ctx.font = `${10}px Arial`; ctx.fillText(comp.ip, comp.x-25, comp.y - (iconSize/2) - 15); }
                if(isSelected) { ctx.strokeStyle = '#005f99'; ctx.lineWidth = 2; ctx.strokeRect(comp.x - halfSize - 4, comp.y - halfSize - 4, iconSize + 8, iconSize + 8); ctx.beginPath(); ctx.arc(comp.x + halfSize + 8, comp.y - halfSize - 8, 6, 0, 2*Math.PI); ctx.fillStyle = '#005f99'; ctx.fill(); ctx.fillStyle = '#fff'; ctx.font = `${10}px Arial`; ctx.fillText('↻', comp.x + halfSize + 5, comp.y - halfSize - 5); }
                if(comp.type === 'camera') drawFieldOfView(comp);
                ctx.restore();
            });
            sensorAnimationTime = (sensorAnimationTime + 0.01) % 1;
        }
        
        function drawShapePreview(start, end, type) {
            if(!start || !end) return;
            ctx.save(); ctx.setLineDash([5, 5]); ctx.strokeStyle = '#005f99'; ctx.fillStyle = 'rgba(0, 95, 153, 0.2)'; ctx.lineWidth = 2;
            const x = Math.min(start.x, end.x); const y = Math.min(start.y, end.y); const width = Math.abs(end.x - start.x);
            switch(type) {
                case 'line': ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke(); break;
                case 'door': ctx.fillRect(end.x, end.y, 30, 50); ctx.strokeRect(end.x, end.y, 30, 50); break;
                case 'window': ctx.fillRect(x, y, width, 40); ctx.strokeRect(x, y, width, 40); break;
            }
            ctx.setLineDash([]); ctx.restore();
        }
        
        function drawWithBackground(whiteBg = false, hideGrid = false) {
            if(whiteBg) { ctx.fillStyle = '#FFFFFF'; ctx.fillRect(0, 0, canvas.width, canvas.height); }
            else { ctx.clearRect(0, 0, canvas.width, canvas.height); drawBackground(); }
            if(!hideGrid && showGrid) drawGrid();
            drawShapes(); drawConnections(); drawComponents();
        }
        
        function draw() {
            drawWithBackground(false, false);
            if(drawingPreview && shapeStart) drawShapePreview(shapeStart, lastMousePos || shapeStart, shapeMode);
            requestAnimationFrame(draw);
        }
        draw();
        
        function getMousePos(e) {
            const rect = canvas.getBoundingClientRect(); const scaleX = canvas.width / rect.width; const scaleY = canvas.height / rect.height;
            let clientX, clientY;
            if (e.touches) { clientX = e.touches[0].clientX; clientY = e.touches[0].clientY; }
            else { clientX = e.clientX; clientY = e.clientY; }
            return { x: (clientX - rect.left) * scaleX, y: (clientY - rect.top) * scaleY };
        }
        
        function rotateComponent(comp, angle) { comp.rotation = (comp.rotation || 0) + angle; }
        function accessDevice(comp) { if(comp && comp.ip && comp.ip.trim()) { let url = comp.ip; if(!url.startsWith('http://') && !url.startsWith('https://')) url = 'http://' + url; if(comp.port && comp.port !== 80) url += ':' + comp.port; window.open(url, '_blank'); showToast(`🌐 Abrindo ${comp.name}`); } else if(comp) { showToast(`⚠️ "${comp.name}" sem IP.`); } }
        
        function endShape(start, end, type) {
            if(!start || !end) return;
            const newShape = { id: Date.now(), type: type, fillColor: '#f8f9fa', strokeColor: '#005f99', lineWidth: 2, rotation: 0 };
            switch(type) {
                case 'line': newShape.x1 = start.x; newShape.y1 = start.y; newShape.x2 = end.x; newShape.y2 = end.y; break;
                case 'door': newShape.x = end.x; newShape.y = end.y; break;
                case 'window': newShape.x = Math.min(start.x, end.x); newShape.y = Math.min(start.y, end.y); newShape.width = Math.abs(end.x - start.x); newShape.height = 40; break;
                case 'text': const text = prompt('Digite o texto:', 'Texto'); if(text) { newShape.text = text; newShape.x = end.x; newShape.y = end.y; newShape.fontSize = 14; newShape.textColor = '#212529'; } else return; break;
            }
            shapes.push(newShape); showToast(`✅ ${getShapeName(type)} adicionado!`); saveUserData();
        }
        
        function getShapeName(mode) { const names = { line: 'Linha', door: 'Porta', window: 'Janela', text: 'Texto' }; return names[mode] || mode; }
        
        function showShapeDeleteButton(shape) {
            const btn = document.getElementById('deleteShapeBtn');
            if (btn && shape) {
                const canvasRect = canvas.getBoundingClientRect(); let x, y;
                if (shape.type === 'line') { x = (shape.x1 + shape.x2) / 2; y = (shape.y1 + shape.y2) / 2; }
                else if (shape.type === 'text') { x = shape.x; y = shape.y; }
                else { x = shape.x + 15; y = shape.y + 25; }
                btn.style.left = (canvasRect.left + x * zoom - 60) + 'px'; btn.style.top = (canvasRect.top + y * zoom - 30) + 'px'; btn.style.display = 'block';
            }
        }
        
        function pointToLineDistance(px, py, x1, y1, x2, y2) {
            const A = px - x1; const B = py - y1; const C = x2 - x1; const D = y2 - y1; const dot = A * C + B * D; const len_sq = C * C + D * D; let param = -1; if (len_sq != 0) param = dot / len_sq;
            let xx, yy; if (param < 0) { xx = x1; yy = y1; } else if (param > 1) { xx = x2; yy = y2; } else { xx = x1 + param * C; yy = y1 + param * D; }
            const dx = px - xx; const dy = py - yy; return Math.sqrt(dx * dx + dy * dy);
        }
        
        function isPointNearConnection(x, y, fromComp, toComp) { return pointToLineDistance(x, y, fromComp.x, fromComp.y, toComp.x, toComp.y) < 12; }
        
        function isPointOnShape(x, y, shape) {
            if(shape.type === 'line') { return pointToLineDistance(x, y, shape.x1, shape.y1, shape.x2, shape.y2) < 8; }
            else if(shape.type === 'text') { return x >= shape.x - 5 && x <= shape.x + (shape.text?.length * 7 || 50) && y >= shape.y - 12 && y <= shape.y + 6; }
            else if(shape.type === 'door') { return x >= shape.x && x <= shape.x + 30 && y >= shape.y && y <= shape.y + 50; }
            else if(shape.type === 'window') { return x >= shape.x && x <= shape.x + 60 && y >= shape.y && y <= shape.y + 40; }
            return false;
        }
        
        function handleStart(e) {
            e.preventDefault(); const {x, y} = getMousePos(e); lastMousePos = {x, y};
            if(shapeMode) { shapeStart = {x, y}; drawingPreview = true; return; }
            let clickedComp = null;
            for(let i=components.length-1; i>=0; i--) { const comp = components[i]; if(Math.hypot(x - comp.x, y - comp.y) < iconSize/2) { clickedComp = comp; break; } }
            if(clickedComp) {
                if(e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1)) { if(selectedComponents.includes(clickedComp)) { selectedComponents = selectedComponents.filter(c => c !== clickedComp); } else { selectedComponents.push(clickedComp); } selectedConnectionIndex = null; selectedShapes = []; }
                else { selectedComponents = [clickedComp]; dragging = true; dragOffset = {x: clickedComp.x - x, y: clickedComp.y - y}; isBackgroundSelected = false; selectedShapes = []; selectedConnectionIndex = null; document.getElementById('deleteShapeBtn').style.display = 'none'; }
                showProperties(clickedComp); openProperties(); e.preventDefault(); return;
            }
            let clickedShape = null;
            for(let i=shapes.length-1; i>=0; i--) { const shape = shapes[i]; if(isPointOnShape(x, y, shape)) { clickedShape = shape; break; } }
            if(clickedShape) {
                if(e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1)) { if(selectedShapes.includes(clickedShape)) { selectedShapes = selectedShapes.filter(s => s !== clickedShape); } else { selectedShapes.push(clickedShape); } selectedConnectionIndex = null; selectedComponents = []; }
                else { selectedShapes = [clickedShape]; dragging = true; if(clickedShape.type === 'line') { dragOffset = {x: clickedShape.x1 - x, y: clickedShape.y1 - y}; } else { dragOffset = {x: clickedShape.x - x, y: clickedShape.y - y}; } selectedComponents = []; selectedConnectionIndex = null; }
                showShapeProperties(clickedShape); openProperties(); e.preventDefault(); return;
            }
            let clickedConnection = null;
            for(let i = 0; i < connections.length; i++) { const conn = connections[i]; const fromComp = components.find(c => c.id === conn.from); const toComp = components.find(c => c.id === conn.to); if(fromComp && toComp) { if(isPointNearConnection(x, y, fromComp, toComp)) { clickedConnection = { index: i, conn: conn }; break; } } }
            if(clickedConnection) {
                selectedConnectionIndex = clickedConnection.index; selectedComponents = []; selectedShapes = [];
                showConnectionProperties(selectedConnectionIndex); openProperties(); e.preventDefault(); return;
            }
            if(backgroundWidth > 0 && backgroundHeight > 0) {
                const hs = 12;
                const isOnNW = (x >= backgroundX - hs && x <= backgroundX + hs && y >= backgroundY - hs && y <= backgroundY + hs);
                const isOnNE = (x >= backgroundX + backgroundWidth - hs && x <= backgroundX + backgroundWidth + hs && y >= backgroundY - hs && y <= backgroundY + hs);
                const isOnSW = (x >= backgroundX - hs && x <= backgroundX + hs && y >= backgroundY + backgroundHeight - hs && y <= backgroundY + backgroundHeight + hs);
                const isOnSE = (x >= backgroundX + backgroundWidth - hs && x <= backgroundX + backgroundWidth + hs && y >= backgroundY + backgroundHeight - hs && y <= backgroundY + backgroundHeight + hs);
                if(isOnNW || isOnNE || isOnSW || isOnSE) {
                    if(isOnNW) { isResizingBackground = true; resizeHandle = 'nw'; } else if(isOnNE) { isResizingBackground = true; resizeHandle = 'ne'; } else if(isOnSW) { isResizingBackground = true; resizeHandle = 'sw'; } else if(isOnSE) { isResizingBackground = true; resizeHandle = 'se'; }
                    resizeStart = { x: e.clientX || e.touches[0].clientX, y: e.clientY || e.touches[0].clientY, width: backgroundWidth, height: backgroundHeight, bgX: backgroundX, bgY: backgroundY };
                    isBackgroundSelected = true; e.preventDefault(); return;
                } else if(x >= backgroundX && x <= backgroundX + backgroundWidth && y >= backgroundY && y <= backgroundY + backgroundHeight) {
                    isBackgroundSelected = true; isDraggingBackgroundImage = true; dragBackgroundStart = { x: (e.clientX || e.touches[0].clientX) - backgroundX, y: (e.clientY || e.touches[0].clientY) - backgroundY };
                    showToast('✅ Imagem selecionada!'); e.preventDefault(); return;
                } else { isBackgroundSelected = false; }
            }
            for(let comp of components) { if(selectedComponents.includes(comp)) { const handleX = comp.x + (iconSize/2) + 8; const handleY = comp.y - (iconSize/2) - 8; if(Math.hypot(x - handleX, y - handleY) < 10) { rotateComponent(comp, 15); saveUserData(); return; } } }
            for(let comp of components) { if(comp.type === 'camera') { const angleRad = (comp.angle || 0) * Math.PI / 180; const distance = 100; const handleX = comp.x + Math.cos(angleRad) * distance; const handleY = comp.y + Math.sin(angleRad) * distance; if(Math.hypot(x - handleX, y - handleY) < 10) { currentAngleHandle = comp; return; } } }
            if(e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1)) { startSelection(e); selectedComponents = []; selectedShapes = []; selectedConnectionIndex = null; showProperties(null); }
            else { selectedComponents = []; selectedShapes = []; selectedConnectionIndex = null; dragging = false; showProperties(null); }
            if(e.shiftKey) { for(let comp of components) { if(Math.hypot(x - comp.x, y - comp.y) < iconSize/2) { isDrawingConnection = true; connectionStart = comp; return; } } }
        }
        
        function handleMove(e) {
            let clientX, clientY;
            if (e.touches) { clientX = e.touches[0].clientX; clientY = e.touches[0].clientY; } else { clientX = e.clientX; clientY = e.clientY; }
            const {x, y} = getMousePos(e); lastMousePos = {x, y};
            if(isResizingBackground && resizeHandle) {
                const dx = (clientX - resizeStart.x); const dy = (clientY - resizeStart.y);
                let newWidth = resizeStart.width; let newHeight = resizeStart.height; let newX = resizeStart.bgX; let newY = resizeStart.bgY;
                switch(resizeHandle) {
                    case 'se': newWidth = Math.max(50, resizeStart.width + dx); newHeight = Math.max(50, resizeStart.height + dy); break;
                    case 'sw': newWidth = Math.max(50, resizeStart.width - dx); newHeight = Math.max(50, resizeStart.height + dy); newX = resizeStart.bgX + (resizeStart.width - newWidth); break;
                    case 'ne': newWidth = Math.max(50, resizeStart.width + dx); newHeight = Math.max(50, resizeStart.height - dy); newY = resizeStart.bgY + (resizeStart.height - newHeight); break;
                    case 'nw': newWidth = Math.max(50, resizeStart.width - dx); newHeight = Math.max(50, resizeStart.height - dy); newX = resizeStart.bgX + (resizeStart.width - newWidth); newY = resizeStart.bgY + (resizeStart.height - newHeight); break;
                }
                backgroundWidth = newWidth; backgroundHeight = newHeight; backgroundX = newX; backgroundY = newY; saveUserData(); return;
            }
            if(isDraggingBackgroundImage) { backgroundX = clientX - dragBackgroundStart.x; backgroundY = clientY - dragBackgroundStart.y; saveUserData(); return; }
            if(currentAngleHandle) { const angle = Math.atan2(y - currentAngleHandle.y, x - currentAngleHandle.x) * 180 / Math.PI; currentAngleHandle.angle = angle; saveUserData(); return; }
            if(dragging && selectedComponents.length > 0) { const dx = (x + dragOffset.x) - selectedComponents[0].x; const dy = (y + dragOffset.y) - selectedComponents[0].y; selectedComponents.forEach(comp => { comp.x += dx; comp.y += dy; }); dragOffset = {x: selectedComponents[0].x - x, y: selectedComponents[0].y - y}; saveUserData(); }
            if(dragging && selectedShapes.length > 0) {
                const shape = selectedShapes[0]; let dx, dy;
                if(shape.type === 'line') { dx = (x + dragOffset.x) - shape.x1; dy = (y + dragOffset.y) - shape.y1; shape.x1 += dx; shape.y1 += dy; shape.x2 += dx; shape.y2 += dy; dragOffset = {x: shape.x1 - x, y: shape.y1 - y}; }
                else { dx = (x + dragOffset.x) - shape.x; dy = (y + dragOffset.y) - shape.y; shape.x += dx; shape.y += dy; dragOffset = {x: shape.x - x, y: shape.y - y}; }
                saveUserData();
            }
            if(isSelecting) updateSelection(e);
        }
        
        function handleEnd(e) {
            if(shapeMode && shapeStart) { const {x, y} = getMousePos(e); endShape(shapeStart, {x, y}, shapeMode); shapeStart = null; drawingPreview = false; return; }
            currentAngleHandle = null; dragging = false; isDraggingBackgroundImage = false; isResizingBackground = false; resizeHandle = null;
            if(isSelecting) endSelection();
            if(isDrawingConnection && connectionStart) { showToast('Clique em outro equipamento para conectar'); }
            isDrawingConnection = false; connectionStart = null;
        }
        
        function handleClick(e) {
            const {x, y} = getMousePos(e);
            if(isDrawingConnection && connectionStart) { for(let comp of components) { if(Math.hypot(x - comp.x, y - comp.y) < iconSize/2 && comp.id !== connectionStart.id) { showCableModal(connectionStart, comp); isDrawingConnection = false; connectionStart = null; return; } } }
        }
        
        function handleContextMenu(e) {
            e.preventDefault(); const {x, y} = getMousePos(e);
            if(isBackgroundSelected && backgroundWidth > 0 && backgroundHeight > 0 && x >= backgroundX && x <= backgroundX + backgroundWidth && y >= backgroundY && y <= backgroundY + backgroundHeight) {
                const menu = document.getElementById('contextMenu');
                menu.innerHTML = `<div class="context-menu-item" onclick="openBackgroundModal()">✏️ Editar Imagem</div><div class="context-menu-item" onclick="removeBackground()">🗑 Remover Imagem</div><div class="context-menu-item" onclick="isBackgroundSelected=false; showToast('Desselecionada');">🔲 Desselecionar</div>`;
                menu.style.display = 'block'; menu.style.left = e.pageX + 'px'; menu.style.top = e.pageY + 'px';
                setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', {once: true}), 100); return;
            }
            for(let comp of components) { if(Math.hypot(x - comp.x, y - comp.y) < iconSize/2) { showContextMenu(e, comp); return; } }
            for(let shape of shapes) { if(isPointOnShape(x, y, shape)) { showShapeContextMenu(e, shape); return; } }
            for(let i = 0; i < connections.length; i++) { const conn = connections[i]; const fromComp = components.find(c => c.id === conn.from); const toComp = components.find(c => c.id === conn.to); if(fromComp && toComp) { if(isPointNearConnection(x, y, fromComp, toComp)) { showConnectionContextMenu(e, conn, i); return; } } }
        }
        
        function showContextMenu(e, comp) {
            e.preventDefault(); contextMenuComponent = comp;
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `<div class="context-menu-item" onclick="accessDeviceFromMenu()">🌐 Acessar Dispositivo</div><div class="context-menu-item" onclick="copyIpFromMenu()">📋 Copiar IP</div><div class="context-menu-item" onclick="rotateLeftFromMenu()">🔄 Rotacionar Esquerda</div><div class="context-menu-item" onclick="rotateRightFromMenu()">🔄 Rotacionar Direita</div><div class="context-menu-item" onclick="flipComponentFromMenu()">🔁 Inverter Posição</div><div class="context-menu-item" onclick="deleteComponentFromMenu()">🗑 Remover</div><div class="context-menu-item" onclick="duplicateComponentFromMenu()">📋 Duplicar</div><div class="context-menu-item" onclick="openPermanentIconModalFromMenu()">🎨 Alterar Ícone (Permanente)</div>`;
            menu.style.display = 'block'; menu.style.left = e.pageX + 'px'; menu.style.top = e.pageY + 'px';
            setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', {once: true}), 100);
        }
        
        window.openPermanentIconModalFromMenu = () => { if(contextMenuComponent) openPermanentIconModal(contextMenuComponent); document.getElementById('contextMenu').style.display = 'none'; };
        window.accessDeviceFromMenu = () => { if(contextMenuComponent) accessDevice(contextMenuComponent); document.getElementById('contextMenu').style.display = 'none'; };
        window.copyIpFromMenu = () => { if(contextMenuComponent && contextMenuComponent.ip) { navigator.clipboard.writeText(contextMenuComponent.ip); showToast(`📋 IP copiado!`); } else { showToast('Nenhum IP'); } document.getElementById('contextMenu').style.display = 'none'; };
        window.rotateLeftFromMenu = () => { if(contextMenuComponent) rotateComponent(contextMenuComponent, -15); document.getElementById('contextMenu').style.display = 'none'; };
        window.rotateRightFromMenu = () => { if(contextMenuComponent) rotateComponent(contextMenuComponent, 15); document.getElementById('contextMenu').style.display = 'none'; };
        window.flipComponentFromMenu = () => { if(contextMenuComponent) flipComponent(contextMenuComponent); document.getElementById('contextMenu').style.display = 'none'; };
        window.deleteComponentFromMenu = () => { if(contextMenuComponent) { connections = connections.filter(c => c.from !== contextMenuComponent.id && c.to !== contextMenuComponent.id); components = components.filter(c => c.id !== contextMenuComponent.id); selectedComponents = selectedComponents.filter(c => c.id !== contextMenuComponent.id); showProperties(null); if(selectedComponents.length === 0 && selectedShapes.length === 0 && selectedConnectionIndex === null) closeProperties(); showToast(`🗑 Removido!`); saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
        window.duplicateComponentFromMenu = () => { if(contextMenuComponent) { const newComp = JSON.parse(JSON.stringify(contextMenuComponent)); newComp.id = Date.now(); newComp.x += 30; newComp.y += 30; components.push(newComp); showToast(`📋 Duplicado!`); saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
        
        function showShapeContextMenu(e, shape) {
            e.preventDefault(); contextMenuShape = shape;
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `<div class="context-menu-item" onclick="editShapeFromMenu()">✏️ Editar</div><div class="context-menu-item" onclick="rotateShapeLeftFromMenu()">🔄 Girar Esquerda</div><div class="context-menu-item" onclick="rotateShapeRightFromMenu()">🔄 Girar Direita</div><div class="context-menu-item" onclick="flipShapeFromMenu()">🔁 Inverter</div><div class="context-menu-item" onclick="deleteShapeFromMenu()">🗑 Excluir</div><div class="context-menu-item" onclick="duplicateShapeFromMenu()">📋 Duplicar</div>`;
            menu.style.display = 'block'; menu.style.left = e.pageX + 'px'; menu.style.top = e.pageY + 'px';
            setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', {once: true}), 100);
        }
        
        window.editShapeFromMenu = () => { if(contextMenuShape) { showShapeProperties(contextMenuShape); openProperties(); } document.getElementById('contextMenu').style.display = 'none'; };
        window.rotateShapeLeftFromMenu = () => { if(contextMenuShape && (contextMenuShape.type === 'door' || contextMenuShape.type === 'window')) { contextMenuShape.rotation = (contextMenuShape.rotation || 0) - 15; saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
        window.rotateShapeRightFromMenu = () => { if(contextMenuShape && (contextMenuShape.type === 'door' || contextMenuShape.type === 'window')) { contextMenuShape.rotation = (contextMenuShape.rotation || 0) + 15; saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
        window.flipShapeFromMenu = () => { if(contextMenuShape) { if(contextMenuShape.type === 'line') { const tX = contextMenuShape.x1; const tY = contextMenuShape.y1; contextMenuShape.x1 = contextMenuShape.x2; contextMenuShape.y1 = contextMenuShape.y2; contextMenuShape.x2 = tX; contextMenuShape.y2 = tY; } else { contextMenuShape.rotation = (contextMenuShape.rotation || 0) + 180; } showToast(`🔄 Invertida!`); saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
        window.deleteShapeFromMenu = () => { if(contextMenuShape) { shapes = shapes.filter(s => s.id !== contextMenuShape.id); selectedShapes = selectedShapes.filter(s => s.id !== contextMenuShape.id); showProperties(null); if(selectedShapes.length === 0 && selectedComponents.length === 0 && selectedConnectionIndex === null) closeProperties(); document.getElementById('deleteShapeBtn').style.display = 'none'; showToast('🗑 Removida!'); saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
        window.duplicateShapeFromMenu = () => { if(contextMenuShape) { const newShape = JSON.parse(JSON.stringify(contextMenuShape)); newShape.id = Date.now(); if(newShape.type === 'line') { newShape.x1 += 30; newShape.y1 += 30; newShape.x2 += 30; newShape.y2 += 30; } else { newShape.x += 30; newShape.y += 30; } shapes.push(newShape); showToast(`📋 Duplicada!`); saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
        
        function showConnectionContextMenu(e, conn, idx) {
            e.preventDefault(); contextMenuConnection = { conn, idx };
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `<div class="context-menu-item" onclick="editConnectionFromMenu()">✏️ Editar Conexão</div><div class="context-menu-item" onclick="deleteConnectionFromMenu()">🗑 Excluir Conexão</div>`;
            menu.style.display = 'block'; menu.style.left = e.pageX + 'px'; menu.style.top = e.pageY + 'px';
            setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', {once: true}), 100);
        }
        
        window.editConnectionFromMenu = () => { if(contextMenuConnection) { selectedConnectionIndex = contextMenuConnection.idx; showConnectionProperties(selectedConnectionIndex); openProperties(); } document.getElementById('contextMenu').style.display = 'none'; };
        window.deleteConnectionFromMenu = () => { if(contextMenuConnection) { connections.splice(contextMenuConnection.idx, 1); selectedConnectionIndex = null; showToast('✅ Conexão removida!'); saveUserData(); } document.getElementById('contextMenu').style.display = 'none'; };
        
        function startSelection(e) { isSelecting = true; const {x, y} = getMousePos(e); selectionStart = {x, y}; selectionEnd = {x, y}; document.getElementById('selectionRect').style.display = 'block'; }
        function updateSelection(e) { if(!isSelecting) return; const {x, y} = getMousePos(e); selectionEnd = {x, y}; const left = Math.min(selectionStart.x, selectionEnd.x); const top = Math.min(selectionStart.y, selectionEnd.y); const width = Math.abs(selectionEnd.x - selectionStart.x); const height = Math.abs(selectionEnd.y - selectionStart.y); const rect = document.getElementById('selectionRect'); const canvasRect = canvas.getBoundingClientRect(); rect.style.left = (canvasRect.left + left) + 'px'; rect.style.top = (canvasRect.top + top) + 'px'; rect.style.width = width + 'px'; rect.style.height = height + 'px'; }
        
        function endSelection() {
            if(!isSelecting) return; isSelecting = false; document.getElementById('selectionRect').style.display = 'none';
            const minX = Math.min(selectionStart.x, selectionEnd.x); const maxX = Math.max(selectionStart.x, selectionEnd.x); const minY = Math.min(selectionStart.y, selectionEnd.y); const maxY = Math.max(selectionStart.y, selectionEnd.y);
            selectedComponents = components.filter(comp => comp.x >= minX && comp.x <= maxX && comp.y >= minY && comp.y <= maxY);
            selectedShapes = shapes.filter(shape => {
                if(shape.type === 'line') { return (shape.x1 >= minX && shape.x1 <= maxX && shape.y1 >= minY && shape.y1 <= maxY) || (shape.x2 >= minX && shape.x2 <= maxX && shape.y2 >= minY && shape.y2 <= maxY); }
                else if(shape.type === 'text') { return shape.x >= minX && shape.x <= maxX && shape.y >= minY && shape.y <= maxY; }
                else { const w = shape.type === 'door' ? 30 : 60; const h = shape.type === 'door' ? 50 : 40; return shape.x + w >= minX && shape.x <= maxX && shape.y + h >= minY && shape.y <= maxY; }
            });
            const info = document.getElementById('selectionInfo'); const total = selectedComponents.length + selectedShapes.length;
            if(total > 0) { info.textContent = `${total} item(s) selecionado(s)`; info.style.display = 'block'; setTimeout(() => info.style.display = 'none', 2000); }
            if(selectedComponents.length === 1 && selectedShapes.length === 0) { showProperties(selectedComponents[0]); openProperties(); }
            else if(selectedShapes.length === 1 && selectedComponents.length === 0) { showShapeProperties(selectedShapes[0]); openProperties(); }
            else if(selectedConnectionIndex !== null) { showConnectionProperties(selectedConnectionIndex); openProperties(); }
            else { showProperties(null); closeProperties(); }
        }
        
        function showProperties(comp) {
            const div = document.getElementById('props-content');
            if(!comp) { div.innerHTML = '<p style="color:#6c757d;">Clique em um componente para editar suas propriedades</p>'; return; }
            div.innerHTML = `
                <div class="property-group"><label>Nome</label><input type="text" id="prop-name" value="${comp.name.replace(/"/g, '&quot;')}"></div>
                <div class="property-group"><label>Tipo</label><input type="text" value="${comp.type}" disabled></div>
                <div class="property-group"><label>Posição X</label><input type="number" id="prop-x" value="${Math.round(comp.x)}"></div>
                <div class="property-group"><label>Posição Y</label><input type="number" id="prop-y" value="${Math.round(comp.y)}"></div>
                <div class="property-group"><label>🔄 Rotação</label><input type="range" id="prop-rotation" min="0" max="360" value="${comp.rotation || 0}"><span id="rotation-val">${Math.round(comp.rotation || 0)}°</span></div>
                <div class="property-group"><label>🔁 Inverter Posição</label><button class="btn btn-secondary" onclick="flipComponentById(${comp.id})" style="width:100%;">🔄 Inverter (180°)</button></div>
                <div class="property-group"><label>🌐 Endereço IP</label><input type="text" id="prop-ip" value="${comp.ip || ''}" placeholder="192.168.1.100"></div>
                <div class="property-group"><label>🔌 Porta</label><input type="number" id="prop-port" value="${comp.port || 80}" placeholder="80"></div>
                <div class="property-group"><label>👤 Usuário</label><input type="text" id="prop-user" value="${comp.username || ''}" placeholder="admin"></div>
                <div class="property-group"><label>🔑 Senha</label><input type="password" id="prop-pass" value="${comp.password || ''}"></div>
                ${comp.type === 'camera' ? `<div class="property-group"><label>Ângulo (graus)</label><input type="range" id="prop-angle" min="0" max="360" value="${comp.angle || 0}"><span id="angle-val">${Math.round(comp.angle || 0)}°</span></div><div class="property-group"><label>Campo Visão (graus)</label><input type="range" id="prop-fov" min="20" max="120" value="${comp.fov || 80}"><span id="fov-val">${Math.round(comp.fov || 80)}°</span></div>` : ''}
                <div class="property-group"><label>🖼️ Ícone Personalizado (Permanente)</label><input type="file" id="prop-image" accept="image/*"><div class="image-preview" id="prop-image-preview">${comp.iconFile ? `<img src="/uploads/icons/${comp.iconFile}" style="max-width:50px;max-height:50px;">` : ''}</div></div>
                <div class="property-group"><label>🔌 Conectar a</label><select id="prop-connect"><option value="">-- Selecione --</option>${components.filter(c => c.id !== comp.id).map(c => `<option value="${c.id}">${c.name}</option>`).join('')}</select><select id="prop-cable-type">${Object.entries(cableColors).map(([key, value]) => `<option value="${key}">${value.icon} ${value.name} - ${value.speed}</option>`).join('')}</select><button class="btn btn-primary" style="margin-top:5px;" onclick="addConnection(${comp.id})">➕ Conectar</button></div>
                <div class="modal-buttons"><button class="btn btn-info" onclick="accessDeviceById(${comp.id})">🌐 Acessar</button><button class="btn btn-warning" onclick="rotateLeft(${comp.id})">🔄 Girar Esq</button><button class="btn btn-warning" onclick="rotateRight(${comp.id})">🔄 Girar Dir</button><button class="btn btn-danger" onclick="deleteComponent(${comp.id})">🗑 Remover</button><button class="btn btn-secondary" onclick="openPermanentIconModalById(${comp.id})">🎨 Ícone Permanente</button></div>
            `;
            const rotationSlider = document.getElementById('prop-rotation'); if(rotationSlider) { rotationSlider.oninput = (e) => { comp.rotation = parseInt(e.target.value); document.getElementById('rotation-val').innerText = comp.rotation + '°'; saveUserData(); }; }
            if(comp.type === 'camera') { const angleSlider = document.getElementById('prop-angle'); const fovSlider = document.getElementById('prop-fov'); if(angleSlider) { angleSlider.oninput = (e) => { comp.angle = parseInt(e.target.value); document.getElementById('angle-val').innerText = comp.angle + '°'; saveUserData(); }; } if(fovSlider) { fovSlider.oninput = (e) => { comp.fov = parseInt(e.target.value); document.getElementById('fov-val').innerText = comp.fov + '°'; saveUserData(); }; } }
            document.getElementById('prop-name')?.addEventListener('change', (e) => { comp.name = e.target.value; saveUserData(); });
            document.getElementById('prop-x')?.addEventListener('change', (e) => { comp.x = parseInt(e.target.value); saveUserData(); });
            document.getElementById('prop-y')?.addEventListener('change', (e) => { comp.y = parseInt(e.target.value); saveUserData(); });
            document.getElementById('prop-ip')?.addEventListener('change', (e) => { comp.ip = e.target.value; saveUserData(); });
            document.getElementById('prop-port')?.addEventListener('change', (e) => { comp.port = parseInt(e.target.value); saveUserData(); });
            document.getElementById('prop-user')?.addEventListener('change', (e) => { comp.username = e.target.value; saveUserData(); });
            document.getElementById('prop-pass')?.addEventListener('change', (e) => { comp.password = e.target.value; saveUserData(); });
            const imageInput = document.getElementById('prop-image');
            if(imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if(file) { const base64 = await readImageAsBase64(file); const response = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'equipment' }) }); const data = await response.json(); if(data.success) { comp.iconFile = data.filename; const preview = document.getElementById('prop-image-preview'); if(preview) preview.innerHTML = `<img src="/uploads/icons/${data.filename}" style="max-width:50px;max-height:50px;">`; showToast(`✅ Aplicado a ${comp.name}`); saveUserData(); } } }; }
        }
        
        function showShapeProperties(shape) {
            const div = document.getElementById('props-content');
            if(!shape) { div.innerHTML = '<p style="color:#6c757d;">Clique em um componente ou forma</p>'; return; }
            div.innerHTML = `
                <div class="property-group"><label>Tipo</label><input type="text" value="${getShapeName(shape.type)}" disabled></div>
                <div class="property-group"><label>Cor da Linha</label><input type="color" id="shape-stroke" value="${shape.strokeColor || '#005f99'}"></div>
                <div class="property-group"><label>Espessura</label><input type="range" id="shape-linewidth" min="1" max="10" value="${shape.lineWidth || 2}"></div>
                ${shape.type === 'text' ? `<div class="property-group"><label>Texto</label><input type="text" id="shape-text" value="${shape.text || ''}"></div><div class="property-group"><label>Fonte</label><input type="number" id="shape-fontsize" value="${shape.fontSize || 14}"></div><div class="property-group"><label>Cor Texto</label><input type="color" id="shape-textcolor" value="${shape.textColor || '#212529'}"></div>` : `<div class="property-group"><label>🔄 Rotação</label><input type="range" id="shape-rotation" min="0" max="360" value="${shape.rotation || 0}"><span id="rotation-val">${Math.round(shape.rotation || 0)}°</span></div><div class="property-group"><label>🔁 Inverter</label><button class="btn btn-secondary" onclick="flipShape(${shape.id})" style="width:100%;">🔄 Inverter (180°)</button></div>`}
                <div class="property-group"><label>Posição X</label><input type="number" id="shape-x" value="${Math.round(shape.x || shape.x1 || 0)}"></div>
                <div class="property-group"><label>Posição Y</label><input type="number" id="shape-y" value="${Math.round(shape.y || shape.y1 || 0)}"></div>
                <div class="modal-buttons"><button class="btn btn-danger" onclick="deleteShape(${shape.id})">🗑 Excluir</button><button class="btn btn-secondary" onclick="duplicateShape(${shape.id})">📋 Duplicar</button></div>
            `;
            document.getElementById('shape-stroke')?.addEventListener('change', (e) => { shape.strokeColor = e.target.value; saveUserData(); });
            document.getElementById('shape-linewidth')?.addEventListener('change', (e) => { shape.lineWidth = parseInt(e.target.value); saveUserData(); });
            const rotationSlider = document.getElementById('shape-rotation'); if(rotationSlider) { rotationSlider.oninput = (e) => { shape.rotation = parseInt(e.target.value); document.getElementById('rotation-val').innerText = shape.rotation + '°'; saveUserData(); }; }
            document.getElementById('shape-x')?.addEventListener('change', (e) => { const val = parseInt(e.target.value); if(shape.type === 'line') { shape.x1 = val; shape.x2 = val + (shape.x2 - shape.x1); } else { shape.x = val; } saveUserData(); });
            document.getElementById('shape-y')?.addEventListener('change', (e) => { const val = parseInt(e.target.value); if(shape.type === 'line') { shape.y1 = val; shape.y2 = val + (shape.y2 - shape.y1); } else { shape.y = val; } saveUserData(); });
            if(shape.type === 'text') { document.getElementById('shape-text')?.addEventListener('change', (e) => { shape.text = e.target.value; saveUserData(); }); document.getElementById('shape-fontsize')?.addEventListener('change', (e) => { shape.fontSize = parseInt(e.target.value); saveUserData(); }); document.getElementById('shape-textcolor')?.addEventListener('change', (e) => { shape.textColor = e.target.value; saveUserData(); }); }
        }
        
        function showConnectionProperties(connIdx) {
            const div = document.getElementById('props-content'); const conn = connections[connIdx];
            if(!conn) { div.innerHTML = '<p style="color:#6c757d;">Clique em uma conexão</p>'; return; }
            const fromComp = components.find(c => c.id === conn.from); const toComp = components.find(c => c.id === conn.to); if(!fromComp || !toComp) return;
            div.innerHTML = `<div class="property-group"><label>Conexão</label><input type="text" value="${fromComp.name} → ${toComp.name}" disabled></div><div class="property-group"><label>Tipo de Cabo</label><select id="conn-cable-type">${Object.entries(cableColors).map(([key, value]) => `<option value="${key}" ${conn.type === key ? 'selected' : ''}>${value.icon} ${value.name} - ${value.speed}</option>`).join('')}</select></div><div class="modal-buttons"><button class="btn btn-primary" onclick="updateSelectedConnection(${connIdx})">✅ Atualizar</button><button class="btn btn-danger" onclick="deleteSelectedConnection(${connIdx})">🗑 Excluir</button></div>`;
        }
        
        window.updateSelectedConnection = (connIdx) => { const cableType = document.getElementById('conn-cable-type').value; connections[connIdx].type = cableType; selectedConnectionIndex = null; showProperties(null); closeProperties(); showToast(`✅ Atualizada!`); saveUserData(); };
        window.deleteSelectedConnection = (connIdx) => { if(confirm('Excluir conexão?')) { connections.splice(connIdx, 1); selectedConnectionIndex = null; showProperties(null); closeProperties(); showToast(`✅ Removida!`); saveUserData(); } };
        window.flipComponentById = (id) => { const comp = components.find(c => c.id === id); if(comp) { flipComponent(comp); saveUserData(); } };
        window.flipComponent = (comp) => { if (!comp) return; comp.rotation = (comp.rotation || 0) + 180; showToast(`🔄 ${comp.name} invertido!`); saveUserData(); };
        window.flipShape = (id) => { const shape = shapes.find(s => s.id === id); if(shape && (shape.type === 'door' || shape.type === 'window')) { shape.rotation = (shape.rotation || 0) + 180; showToast(`🔄 Invertida!`); saveUserData(); } else if(shape && shape.type === 'line') { const tX = shape.x1; const tY = shape.y1; shape.x1 = shape.x2; shape.y1 = shape.y2; shape.x2 = tX; shape.y2 = tY; showToast(`🔄 Invertida!`); saveUserData(); } };
        window.duplicateShape = (id) => { const shape = shapes.find(s => s.id === id); if(shape) { const newShape = JSON.parse(JSON.stringify(shape)); newShape.id = Date.now(); if(newShape.type === 'line') { newShape.x1 += 30; newShape.y1 += 30; newShape.x2 += 30; newShape.y2 += 30; } else { newShape.x += 30; newShape.y += 30; } shapes.push(newShape); showToast(`📋 Duplicada!`); saveUserData(); } };
        window.deleteShape = (id) => { shapes = shapes.filter(s => s.id !== id); selectedShapes = selectedShapes.filter(s => s.id !== id); showProperties(null); if(selectedShapes.length === 0 && selectedComponents.length === 0 && selectedConnectionIndex === null) closeProperties(); document.getElementById('deleteShapeBtn').style.display = 'none'; showToast('🗑 Removida!'); saveUserData(); };
        window.deleteSelectedShape = () => { if (selectedShapes.length > 0) { const shapeId = selectedShapes[0].id; shapes = shapes.filter(s => s.id !== shapeId); selectedShapes = []; showProperties(null); closeProperties(); document.getElementById('deleteShapeBtn').style.display = 'none'; showToast('🗑 Removida!'); saveUserData(); } };
        window.deleteSelectedItems = () => {
            if (selectedComponents.length === 0 && selectedShapes.length === 0 && selectedConnectionIndex === null) { showToast('⚠️ Nenhum item selecionado'); return; }
            if (confirm(`Deseja excluir ${selectedComponents.length} equipamento(s), ${selectedShapes.length} forma(s) e ${selectedConnectionIndex !== null ? 1 : 0} conexão(ões)?`)) {
                const selectedIds = selectedComponents.map(c => c.id); connections = connections.filter(c => !selectedIds.includes(c.from) && !selectedIds.includes(c.to));
                if (selectedConnectionIndex !== null) { connections.splice(selectedConnectionIndex, 1); selectedConnectionIndex = null; }
                components = components.filter(c => !selectedIds.includes(c.id)); const selectedShapeIds = selectedShapes.map(s => s.id); shapes = shapes.filter(s => !selectedShapeIds.includes(s.id));
                selectedComponents = []; selectedShapes = []; showProperties(null); closeProperties(); document.getElementById('deleteShapeBtn').style.display = 'none'; showToast(`🗑 Excluídos!`); saveUserData();
            }
        };
        window.rotateLeft = (id) => { const comp = components.find(c => c.id === id); if(comp) { rotateComponent(comp, -15); saveUserData(); } };
        window.rotateRight = (id) => { const comp = components.find(c => c.id === id); if(comp) { rotateComponent(comp, 15); saveUserData(); } };
        window.accessDeviceById = (id) => { const comp = components.find(c => c.id === id); accessDevice(comp); };
        window.deleteComponent = (id) => { if(confirm('Remover equipamento?')) { connections = connections.filter(c => c.from !== id && c.to !== id); components = components.filter(c => c.id !== id); selectedComponents = selectedComponents.filter(c => c.id !== id); showProperties(null); if(selectedComponents.length === 0 && selectedShapes.length === 0 && selectedConnectionIndex === null) closeProperties(); showToast(`🗑 Removido!`); saveUserData(); } };
        window.addConnection = (fromId) => { const toId = document.getElementById('prop-connect').value; const cableType = document.getElementById('prop-cable-type').value; if(toId) { connections.push({from: fromId, to: parseInt(toId), type: cableType}); const cableInfo = cableColors[cableType]; showToast(`✅ Conexão ${cableInfo ? cableInfo.name : cableType.toUpperCase()}!`); saveUserData(); } else { showToast('⚠️ Selecione um equipamento'); } };
        
        function showCableModal(fromComp, toComp) {
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🔌 Tipo de Conexão</h3><p>De: ${fromComp.name}</p><p>Para: ${toComp.name}</p><select id="cableSelect">${Object.entries(cableColors).map(([key, value]) => `<option value="${key}">${value.icon} ${value.name} - ${value.speed}</option>`).join('')}</select><div class="modal-buttons"><button class="btn btn-primary" onclick="confirmConnection(${fromComp.id}, ${toComp.id})">✅ Conectar</button><button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        }
        
        window.confirmConnection = (fromId, toId) => {
            const cableType = document.getElementById('cableSelect').value; connections.push({from: fromId, to: toId, type: cableType});
            if(window.currentModal) { document.body.removeChild(window.currentModal); window.currentModal = null; }
            const cableInfo = cableColors[cableType]; showToast(`✅ Conexão ${cableInfo ? cableInfo.name : cableType.toUpperCase()}!`); saveUserData();
        };
        
        function openPermanentIconModal(comp) {
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🎨 Ícone Permanente</h3><p>${comp.name}</p><input type="file" id="permIconImage" accept="image/*"><div class="image-preview" id="permIconPreview"></div><div class="modal-buttons"><button class="btn btn-primary" onclick="applyPermanentIcon(${comp.id})">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const imageInput = document.getElementById('permIconImage');
            if(imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if(file) { const base64 = await readImageAsBase64(file); document.getElementById('permIconPreview').innerHTML = `<img src="${base64}" style="max-width:50px;">`; const response = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'equipment' }) }); const data = await response.json(); if(data.success) window.permIconFilename = data.filename; } }; }
        }
        
        window.applyPermanentIcon = (compId) => { const comp = components.find(c => c.id === compId); if(comp && window.permIconFilename) { comp.iconFile = window.permIconFilename; showToast(`✅ Aplicado a ${comp.name}`); closeModal(); saveUserData(); } else { showToast('⚠️ Selecione uma imagem'); } window.permIconFilename = null; };
        window.openPermanentIconModalById = (id) => { const comp = components.find(c => c.id === id); if(comp) openPermanentIconModal(comp); };
        
        function openAddCategoryModal() {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">📁 Nova Categoria</h3><input type="text" id="catName" placeholder="Nome"><input type="text" id="catIcon" placeholder="Ícone" value="📁"><div class="modal-buttons"><button class="btn btn-primary" onclick="addCategory()">Adicionar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        }
        
        window.addCategory = () => { const name = document.getElementById('catName')?.value; const icon = document.getElementById('catIcon')?.value; if (!name) { showToast('Digite um nome'); return; } if (categories[name]) { showToast('Categoria já existe'); return; } categories[name] = { icon: icon || '📁', devices: [] }; saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette(); showToast(`✅ "${name}"!`); };
        
        window.editCategory = (catName) => {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const catData = categories[catName]; const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>✏️ Editar Categoria</h3><input type="text" id="catName" value="${catName}"><input type="text" id="catIcon" value="${catData.icon}"><div class="modal-buttons"><button class="btn btn-primary" onclick="updateCategory('${catName.replace(/'/g, "\\'")}')">Salvar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        };
        
        window.updateCategory = (oldName) => { const newName = document.getElementById('catName')?.value; const icon = document.getElementById('catIcon')?.value; if (!newName) return; const catData = categories[oldName]; delete categories[oldName]; categories[newName] = { ...catData, icon: icon }; saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette(); showToast(`✅ Atualizada!`); };
        
        window.deleteCategory = (catName) => { if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; } if (confirm(`Excluir "${catName}"?`)) { delete categories[catName]; saveUserData(); saveGlobalLibrary(); renderPalette(); showToast(`🗑 Removida!`); } };
        
        window.addDeviceToCategory = (catName) => {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>➕ Novo Dispositivo em ${catName}</h3><input type="text" id="devName" placeholder="Nome"><input type="text" id="devIcon" placeholder="Ícone" value="📦"><input type="text" id="devDesc" placeholder="Descrição"><input type="color" id="devColor" value="#005f99"><input type="text" id="devType" placeholder="Tipo (camera, switch...)"><div class="modal-buttons"><button class="btn btn-primary" onclick="addDevice('${catName.replace(/'/g, "\\'")}')">Adicionar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        };
        
        window.addDevice = async (catName) => {
            const name = document.getElementById('devName')?.value; const icon = document.getElementById('devIcon')?.value; const desc = document.getElementById('devDesc')?.value; const color = document.getElementById('devColor')?.value; const type = document.getElementById('devType')?.value;
            if (!name) { showToast('Digite um nome'); return; }
            categories[catName].devices.push({ name, icon: icon || '📦', desc: desc || '', type: type || 'custom', color: color || '#005f99', iconFile: null });
            saveUserData(); await saveGlobalLibrary(); closeModal(); renderPalette(); showToast(`✅ "${name}"!`);
        };
        
        window.editDevice = (catName, idx) => {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const device = categories[catName].devices[idx]; const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>✏️ Editar</h3><input type="text" id="devName" value="${device.name.replace(/"/g, '&quot;')}"><input type="text" id="devIcon" value="${device.icon || '📦'}"><input type="text" id="devDesc" value="${device.desc || ''}"><input type="color" id="devColor" value="${device.color || '#005f99'}"><input type="text" id="devType" value="${device.type || 'custom'}"><div class="modal-buttons"><button class="btn btn-primary" onclick="updateDevice('${catName.replace(/'/g, "\\'")}', ${idx})">Salvar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        };
        
        window.updateDevice = async (catName, idx) => {
            const name = document.getElementById('devName')?.value; const icon = document.getElementById('devIcon')?.value; const desc = document.getElementById('devDesc')?.value; const color = document.getElementById('devColor')?.value; const type = document.getElementById('devType')?.value;
            if (!name) return;
            categories[catName].devices[idx] = { ...categories[catName].devices[idx], name, icon: icon || '📦', desc: desc || '', type: type || 'custom', color: color || '#005f99' };
            saveUserData(); await saveGlobalLibrary(); closeModal(); renderPalette(); showToast(`✅ Atualizado!`);
        };
        
        window.deleteDevice = (catName, idx) => { if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; } if (confirm('Excluir?')) { categories[catName].devices.splice(idx, 1); saveUserData(); saveGlobalLibrary(); renderPalette(); showToast(`🗑 Removido!`); } };
        
        function openAddDeviceModal() {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>🔧 Novo Equipamento Personalizado</h3><input type="text" id="devName" placeholder="Nome"><input type="text" id="devIcon" placeholder="Ícone" value="📦"><input type="text" id="devDesc" placeholder="Descrição"><input type="color" id="devColor" value="#005f99"><input type="text" id="devType" placeholder="Tipo"><div class="modal-buttons"><button class="btn btn-primary" onclick="addCustomDevice()">Adicionar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        }
        
        window.addCustomDevice = async () => {
            const name = document.getElementById('devName')?.value; const icon = document.getElementById('devIcon')?.value; const desc = document.getElementById('devDesc')?.value; const color = document.getElementById('devColor')?.value; const type = document.getElementById('devType')?.value;
            if (!name) { showToast('Digite um nome'); return; }
            customDevices.push({ id: Date.now(), name, icon: icon || '📦', desc: desc || '', type: type || 'custom', color: color || '#005f99', iconFile: null });
            saveUserData(); await saveGlobalLibrary(); closeModal(); renderPalette(); showToast(`✅ "${name}"!`);
        };
        
        window.editCustomDevice = (idx) => {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const device = customDevices[idx]; const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>✏️ Editar</h3><input type="text" id="devName" value="${device.name.replace(/"/g, '&quot;')}"><input type="text" id="devIcon" value="${device.icon || '📦'}"><input type="text" id="devDesc" value="${device.desc || ''}"><input type="color" id="devColor" value="${device.color || '#005f99'}"><input type="text" id="devType" value="${device.type || 'custom'}"><div class="modal-buttons"><button class="btn btn-primary" onclick="updateCustomDevice(${idx})">Salvar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        };
        
        window.updateCustomDevice = async (idx) => {
            const name = document.getElementById('devName')?.value; const icon = document.getElementById('devIcon')?.value; const desc = document.getElementById('devDesc')?.value; const color = document.getElementById('devColor')?.value; const type = document.getElementById('devType')?.value;
            if (!name) return;
            customDevices[idx] = { ...customDevices[idx], name, icon: icon || '📦', desc: desc || '', type: type || 'custom', color: color || '#005f99' };
            saveUserData(); await saveGlobalLibrary(); closeModal(); renderPalette(); showToast(`✅ Atualizado!`);
        };
        
        window.deleteCustomDevice = (idx) => { if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; } if (confirm('Excluir?')) { customDevices.splice(idx, 1); saveUserData(); saveGlobalLibrary(); renderPalette(); showToast(`🗑 Removido!`); } };
        
        function openAddConnectionModal() {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>🔌 Nova Conexão</h3><input type="text" id="connName" placeholder="Nome"><input type="text" id="connIcon" placeholder="Ícone" value="🔌"><input type="color" id="connColor" value="#005f99"><input type="text" id="connSpeed" placeholder="Velocidade"><input type="text" id="connDesc" placeholder="Descrição"><select id="connType"><option value="cable">Cabeado</option><option value="wireless">Sem Fio</option></select><select id="connAnimation"><option value="">Nenhuma</option><option value="wave">Ondas</option><option value="packet">Pacotes</option></select><select id="connCategory"><option value="Cabeadas">Cabeadas</option><option value="Sem Fio">Sem Fio</option></select><div class="modal-buttons"><button class="btn btn-primary" onclick="addConnectionFromModal()">Adicionar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        }
        
        window.addConnectionFromModal = () => {
            const name = document.getElementById('connName')?.value; const icon = document.getElementById('connIcon')?.value; const color = document.getElementById('connColor')?.value; const speed = document.getElementById('connSpeed')?.value; const desc = document.getElementById('connDesc')?.value; const type = document.getElementById('connType')?.value; const animation = document.getElementById('connAnimation')?.value; const category = document.getElementById('connCategory')?.value;
            if (!name) { showToast('Digite um nome'); return; }
            addCustomConnection(category, { name, icon: icon || '🔌', color, speed: speed || 'N/A', desc: desc || '', type, animation: animation || null, iconFile: null });
            closeModal();
        };
        
        window.addConnectionToCategory = (category) => {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>🔌 Nova Conexão em ${category}</h3><input type="text" id="connName" placeholder="Nome"><input type="text" id="connIcon" placeholder="Ícone" value="🔌"><input type="color" id="connColor" value="#005f99"><input type="text" id="connSpeed" placeholder="Velocidade"><input type="text" id="connDesc" placeholder="Descrição"><select id="connType"><option value="cable">Cabeado</option><option value="wireless">Sem Fio</option></select><select id="connAnimation"><option value="">Nenhuma</option><option value="wave">Ondas</option><option value="packet">Pacotes</option></select><div class="modal-buttons"><button class="btn btn-primary" onclick="addConnectionToCategoryConfirm('${category.replace(/'/g, "\\'")}')">Adicionar</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        };
        
        window.addConnectionToCategoryConfirm = (category) => {
            const name = document.getElementById('connName')?.value; const icon = document.getElementById('connIcon')?.value; const color = document.getElementById('connColor')?.value; const speed = document.getElementById('connSpeed')?.value; const desc = document.getElementById('connDesc')?.value; const type = document.getElementById('connType')?.value; const animation = document.getElementById('connAnimation')?.value;
            if (!name) { showToast('Digite um nome'); return; }
            if (!connectionCategories[category]) connectionCategories[category] = { icon: '🔌', connections: [] };
            const key = getConnectionKey(name);
            connectionCategories[category].connections.push({ name, icon: icon || '🔌', color, speed: speed || 'N/A', desc: desc || '', type, animation: animation || null, iconFile: null });
            cableColors[key] = { color, name, icon: icon || '🔌', type, speed: speed || 'N/A', desc: desc || '', animation: animation || null, iconFile: null };
            saveUserData(); saveGlobalLibrary(); closeModal(); renderConnectionsPalette(); showToast(`✅ "${name}"!`);
        };
        
        function openBackgroundModal() {
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>🖼️ Planta Baixa / Fundo</h3><div class="background-controls"><label><strong>📁 Importar Imagem</strong></label><input type="file" id="bgImageUpload" accept="image/*"><div class="image-preview" id="bgPreview"></div><button class="btn btn-primary" style="margin-top:8px;" onclick="importLocalImage()">📤 Importar</button></div><div class="background-controls"><label><strong>🎨 Opacidade</strong></label><input type="range" id="bgOpacity" min="0.1" max="1" step="0.01" value="${backgroundOpacity}" onchange="updateBackgroundOpacity(this.value)"><span id="opacityValue">${Math.round(backgroundOpacity * 100)}%</span></div>${backgroundImage ? `<div class="background-controls"><div class="action-buttons"><button class="btn btn-secondary" onclick="selectBackgroundImage()">🔍 Selecionar</button><button class="btn btn-danger" onclick="removeBackground()">🗑 Remover</button></div></div>` : ''}<div class="modal-buttons"><button class="btn btn-danger" onclick="closeModal()">❌ Fechar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
        }
        
        window.importLocalImage = async () => { const fileInput = document.getElementById('bgImageUpload'); const file = fileInput.files[0]; if (file) { const base64 = await readImageAsBase64(file); await uploadBackgroundImage(base64, file.name); } else { showToast('Selecione uma imagem'); } };
        window.selectBackgroundImage = () => { isBackgroundSelected = true; closeModal(); showToast('✅ Imagem selecionada!'); };
        window.updateBackgroundOpacity = (value) => { backgroundOpacity = parseFloat(value); document.getElementById('opacityValue').innerText = Math.round(backgroundOpacity * 100) + '%'; saveUserData(); };
        window.removeBackground = () => { if (confirm('Remover imagem?')) { backgroundImage = null; backgroundImageObj = null; backgroundOpacity = 0.8; backgroundWidth = 0; backgroundHeight = 0; backgroundX = 0; backgroundY = 0; isBackgroundSelected = false; saveUserData(); showToast('✅ Removida'); closeModal(); } };
        
        async function uploadBackgroundImage(base64, name) {
            showToast('📤 Enviando...');
            try {
                const response = await fetch('/api/upload_background', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, name: name }) });
                const data = await response.json();
                if (data.success) { backgroundImage = data.url; backgroundImageObj = new Image(); backgroundImageObj.onload = function() { backgroundWidth = backgroundImageObj.width; backgroundHeight = backgroundImageObj.height; backgroundX = canvas.width/2 - backgroundWidth/2; backgroundY = canvas.height/2 - backgroundHeight/2; saveUserData(); showToast('✅ Adicionada!'); closeModal(); }; backgroundImageObj.src = backgroundImage; saveUserData(); }
                else { showToast('Erro ao enviar'); }
            } catch(e) { showToast('Erro'); }
        }
        
        function newProject() { if (confirm('Novo projeto? Todos os dados não salvos serão perdidos.')) { components = []; connections = []; shapes = []; selectedComponents = []; selectedShapes = []; selectedConnectionIndex = null; backgroundImage = null; backgroundImageObj = null; backgroundOpacity = 0.8; backgroundWidth = 0; backgroundHeight = 0; backgroundX = 0; backgroundY = 0; isBackgroundSelected = false; closeProperties(); saveUserData(); showToast('📁 Novo projeto!'); } }
        
        function saveProjectToFile() {
            const projectData = { components, connections, shapes, background: backgroundImage, backgroundOpacity, backgroundWidth, backgroundHeight, backgroundX, backgroundY, version: '2.4', date: new Date().toISOString() };
            const dataStr = JSON.stringify(projectData, null, 2); const blob = new Blob([dataStr], {type: 'application/json'}); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `projeto_${Date.now()}.projetize`; a.click(); URL.revokeObjectURL(url); showToast('✅ Salvo!');
        }
        
        function loadProjectFromFile() {
            const input = document.createElement('input'); input.type = 'file'; input.accept = '.projetize, .json';
            input.onchange = (e) => {
                const file = e.target.files[0]; if (!file) return;
                const reader = new FileReader();
                reader.onload = (ev) => {
                    try {
                        const data = JSON.parse(ev.target.result); components = data.components || []; connections = data.connections || []; shapes = data.shapes || [];
                        if (data.background) { backgroundImage = data.background; backgroundOpacity = data.backgroundOpacity || 0.8; backgroundWidth = data.backgroundWidth || 0; backgroundHeight = data.backgroundHeight || 0; backgroundX = data.backgroundX || 0; backgroundY = data.backgroundY || 0; backgroundImageObj = new Image(); backgroundImageObj.src = backgroundImage; }
                        selectedComponents = []; selectedShapes = []; selectedConnectionIndex = null; closeProperties(); saveUserData(); showToast('✅ Carregado!');
                    } catch(err) { showToast('Erro: ' + err.message); }
                };
                reader.readAsText(file);
            };
            input.click();
        }
        
        function exportPDF() { drawWithBackground(true, true); setTimeout(() => { const imgData = canvas.toDataURL('image/png'); const pdfWindow = window.open('', '_blank'); pdfWindow.document.write(`<html><head><title>Projeto CFTV</title></head><body style="margin:0;padding:20px;display:flex;justify-content:center;background:white;"><img src="${imgData}" style="max-width:100%;height:auto;"><script>window.print();<\\/script></body></html>`); setTimeout(() => draw(), 500); showToast('📄 PDF gerado!'); }, 100); }
        
        function exportPDFWithList() {
            drawWithBackground(true, true);
            let listHTML = `<div style="font-family:Arial,sans-serif;padding:20px;"><h1 style="color:#005f99;text-align:center;">PROJETIZE - LISTA DE EQUIPAMENTOS</h1><hr><p><strong>Data:</strong> ${new Date().toLocaleString()}</p><p><strong>Projetado por:</strong> Thiago Souza</p><br>`;
            const byType = {}; components.forEach(comp => { const type = comp.type; if (!byType[type]) byType[type] = []; byType[type].push(comp); });
            for (const [type, comps] of Object.entries(byType)) {
                listHTML += `<h2>📌 ${type.toUpperCase()}</h2><table style="width:100%;border-collapse:collapse;"><tr style="background:#005f99;color:white;"><th style="padding:8px;text-align:left;">Equipamento</th><th style="padding:8px;text-align:left;">IP</th><th style="padding:8px;text-align:left;">Posição</th></tr>`;
                comps.forEach(comp => { listHTML += `<tr><td style="padding:8px;">✅ ${comp.name}</td><td style="padding:8px;">${comp.ip || 'Não configurado'}</td><td style="padding:8px;">X: ${Math.round(comp.x)}, Y: ${Math.round(comp.y)}</td></tr>`; });
                listHTML += '</table>';
            }
            if (connections.length > 0) {
                listHTML += `<h2>🔌 CONEXÕES</h2><table style="width:100%;border-collapse:collapse;"><tr style="background:#005f99;color:white;"><th style="padding:8px;text-align:left;">Origem</th><th style="padding:8px;text-align:left;">Destino</th><th style="padding:8px;text-align:left;">Tipo</th></tr>`;
                connections.forEach(conn => { const fromComp = components.find(c => c.id === conn.from); const toComp = components.find(c => c.id === conn.to); const cableInfo = cableColors[conn.type] || cableColors['cat6']; if (fromComp && toComp) { listHTML += `<tr><td style="padding:8px;">${fromComp.name}</td><td style="padding:8px;">${toComp.name}</td><td style="padding:8px;">${cableInfo.name}</td></tr>`; } });
                listHTML += '</table>';
            }
            listHTML += `<br><hr><p><strong>Total de Equipamentos:</strong> ${components.length}</p><p><strong>Total de Conexões:</strong> ${connections.length}</p><p><strong>Total de Formas:</strong> ${shapes.length}</p><br><p style="text-align:center;font-size:11px;color:#888;">Desenvolvido por Thiago Souza - Analista de Tecnologia | Unidade 2 - São José do Rio Preto</p></div>`;
            const imgData = canvas.toDataURL('image/png'); const pdfWindow = window.open('', '_blank');
            pdfWindow.document.write(`<html><head><title>Projeto CFTV - Relatório</title><style>@media print{.page-break{page-break-before:always;}}</style></head><body style="margin:0;padding:20px;"><div style="text-align:center;margin-bottom:20px;"><img src="${imgData}" style="max-width:100%;"></div><div class="page-break"></div>${listHTML}<script>window.print();<\\/script></body></html>`);
            setTimeout(() => draw(), 500); showToast('📄 PDF completo gerado!');
        }
        
        function generateBudget() {
            let list = '📋 LISTA DE EQUIPAMENTOS - PROJETO CFTV\\n' + '='.repeat(50) + '\\n\\nData: ' + new Date().toLocaleString() + '\\n\\n';
            const byType = {}; components.forEach(comp => { const type = comp.type; if (!byType[type]) byType[type] = []; byType[type].push(comp); });
            for (const [type, comps] of Object.entries(byType)) { list += `\\n📌 ${type.toUpperCase()}:\\n${'-'.repeat(30)}\\n`; comps.forEach(comp => { list += `   ✅ ${comp.name}`; if (comp.ip) list += ` (IP: ${comp.ip})`; list += '\\n'; }); }
            list += `\\n📡 CONEXÕES:\\n${'-'.repeat(30)}\\n`;
            connections.forEach(conn => { const fromComp = components.find(c => c.id === conn.from); const toComp = components.find(c => c.id === conn.to); const cableInfo = cableColors[conn.type] || cableColors['cat6']; if (fromComp && toComp) { list += `   🔗 ${fromComp.name} → ${toComp.name} (${cableInfo.name})\\n`; } });
            list += `\\n${'='.repeat(50)}\\n📊 TOTAL: ${components.length} equipamentos, ${connections.length} conexões, ${shapes.length} formas\\n`;
            const blob = new Blob([list], {type: 'text/plain;charset=utf-8'}); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `orcamento_${Date.now()}.txt`; a.click(); showToast('💰 Orçamento baixado!');
        }
        
        function toggleGrid() { showGrid = !showGrid; showToast(showGrid ? '🔲 Grade ON' : '🔳 Grade OFF'); }
        function setShapeMode(mode) { shapeMode = mode; document.querySelectorAll('.shape-btn').forEach(btn => btn.classList.remove('active')); if (event && event.target) event.target.classList.add('active'); showToast(`Desenhar: ${getShapeName(mode)}`); }
        function cancelShapeMode() { shapeMode = null; drawingPreview = null; document.querySelectorAll('.shape-btn').forEach(btn => btn.classList.remove('active')); showToast('Cancelado'); }
        function toggleShapesToolbar() { const toolbar = document.getElementById('shapesToolbar'); toolbar.style.display = toolbar.style.display === 'none' ? 'flex' : 'none'; }
        function togglePalette() { const palette = document.getElementById('palette'); const toggleBtn = document.querySelector('.toggle-palette'); palette.classList.toggle('collapsed'); toggleBtn.innerHTML = palette.classList.contains('collapsed') ? '▶' : '◀'; }
        function toggleMobilePalette() { const palette = document.getElementById('palette'); const overlay = document.getElementById('mobileOverlay'); if (palette.classList.contains('collapsed')) { palette.classList.remove('collapsed'); overlay.style.display = 'block'; } else { palette.classList.add('collapsed'); overlay.style.display = 'none'; } }
        function closeMobilePalette() { const palette = document.getElementById('palette'); if (!palette.classList.contains('collapsed')) palette.classList.add('collapsed'); document.getElementById('mobileOverlay').style.display = 'none'; }
        function closePropertiesPanel() { document.getElementById('propertiesPanel').classList.remove('open'); }
        function openProperties() { document.getElementById('propertiesPanel').classList.add('open'); }
        function closeProperties() { document.getElementById('propertiesPanel').classList.remove('open'); }
        
        async function openUserManagement() {
            const response = await fetch('/api/users'); const users = await response.json();
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>👥 Gerenciar Usuários</h3><div class="user-list" id="userList"></div><div style="margin-top:15px;"><input type="text" id="newUsername" placeholder="Novo usuário"><input type="password" id="newPassword" placeholder="Senha"><select id="newRole"><option value="viewer">Visualizador</option><option value="admin">Administrador</option></select><button class="btn btn-primary" style="margin-top:10px;" onclick="addUser()">➕ Adicionar</button></div><div class="modal-buttons"><button class="btn btn-danger" onclick="closeModal()">Fechar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal; renderUserList(users);
        }
        
        function renderUserList(users) {
            const container = document.getElementById('userList'); if (!container) return; container.innerHTML = '';
            for (const [username, userData] of Object.entries(users)) { const userDiv = document.createElement('div'); userDiv.className = 'user-item'; userDiv.innerHTML = `<div><strong>${username}</strong><br><small>${userData.role} | ${new Date(userData.created_at).toLocaleDateString()}</small></div><div class="user-actions">${userData.role !== 'master' ? `<button onclick="deleteUser('${username}')">🗑</button>` : '<span style="color:var(--text-accent);">Master</span>'}</div>`; container.appendChild(userDiv); }
        }
        
        async function addUser() {
            const username = document.getElementById('newUsername').value; const password = document.getElementById('newPassword').value; const role = document.getElementById('newRole').value;
            if (!username || !password) { showToast('Preencha todos os campos'); return; }
            const response = await fetch('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password, role }) });
            const data = await response.json();
            if (data.success) { showToast('✅ Adicionado!'); closeModal(); openUserManagement(); } else { showToast(data.error); }
        }
        
        async function deleteUser(username) {
            if (confirm(`Excluir "${username}"?`)) { const response = await fetch(`/api/users/${username}`, { method: 'DELETE' }); const data = await response.json(); if (data.success) { showToast('✅ Excluído!'); closeModal(); openUserManagement(); } else { showToast(data.error); } }
        }
        
        async function resetToDefaultConfig() {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            if (confirm('⚠️ Restaurar todas as categorias e dispositivos para o padrão?')) { try { const response = await fetch('/api/reset_default_config', { method: 'POST' }); const data = await response.json(); if (data.success) { await loadDefaultConfig(); categories = JSON.parse(JSON.stringify(defaultCategories)); customDevices = []; saveUserData(); saveGlobalLibrary(); renderPalette(); showToast('✅ Restaurado!'); } } catch(e) { showToast('Erro'); } }
        }
        
        function createMatrixAnimation(containerId, isLogin = false) {
            const container = document.getElementById(containerId); if (!container) return; container.innerHTML = '';
            const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン'; const columns = Math.floor(window.innerWidth / 20);
            for (let i = 0; i < columns; i++) { const column = document.createElement('div'); column.className = 'matrix-column'; column.style.left = (i * 20) + 'px'; column.style.animationDuration = (Math.random() * 5 + 5) + 's'; column.style.animationDelay = (Math.random() * 5) + 's'; let text = ''; for (let j = 0; j < 40; j++) text += chars[Math.floor(Math.random() * chars.length)] + '\\n'; column.textContent = text; container.appendChild(column); }
        }
        
        let slideIndex = 0;
        const slides = document.querySelectorAll('.intro-slide'); const dots = document.querySelectorAll('.dot');
        function showSlide(index) { if (slides.length === 0) return; if (index >= slides.length) index = 0; if (index < 0) index = slides.length - 1; slides.forEach(slide => slide.classList.remove('active')); dots.forEach(dot => dot.classList.remove('active')); slides[index].classList.add('active'); dots[index].classList.add('active'); slideIndex = index; }
        
        window.nextSlide = () => showSlide(slideIndex + 1); window.prevSlide = () => showSlide(slideIndex - 1); window.currentSlide = (index) => showSlide(index);
        function closeIntroAndShowLogin() { document.getElementById('introScreen').style.display = 'none'; document.getElementById('loginModal').style.display = 'flex'; loadLoginBgConfig(); }
        
        function loadDevImages() {
            const loginContainer = document.getElementById('loginDevImageContainer'); const loginImg = document.getElementById('loginDevImage'); const badgeImg = document.getElementById('badgeDevImage'); const devSlideImg = document.getElementById('devSlideImg'); const devSlideContainer = document.getElementById('devSlideImage');
            const img = new Image();
            img.onload = function() { if (loginImg) { loginImg.src = img.src; loginImg.style.display = 'block'; const fallback = document.getElementById('loginAvatarFallback'); if (fallback) fallback.style.display = 'none'; } if (badgeImg) badgeImg.src = img.src; if (devSlideImg) { devSlideImg.src = img.src; devSlideImg.style.display = 'block'; } };
            img.src = devImageBase64 ? 'data:image/png;base64,' + devImageBase64 : '/static/dev.png?v=2';
        }
        
        // ================ LOGIN BG ================
        async function loadLoginBgConfig() {
            try {
                const response = await fetch('/api/login_bg_config');
                const data = await response.json();
                if (data.success) { loginBgConfig = data.config; applyLoginBg(); }
            } catch(e) { console.error(e); }
        }

        function applyLoginBg() {
            const imgEl = document.getElementById('loginBgMedia'); const videoEl = document.getElementById('loginBgVideo'); const matrixEl = document.getElementById('matrixBg');
            imgEl.style.display = 'none'; videoEl.style.display = 'none'; imgEl.src = ''; videoEl.src = ''; matrixEl.style.display = 'block';
            if (loginBgConfig.type === 'image' && loginBgConfig.filename) { imgEl.src = `/uploads/login_bg/${loginBgConfig.filename}?t=${Date.now()}`; imgEl.style.display = 'block'; imgEl.style.opacity = loginBgConfig.opacity || 0.35; matrixEl.style.display = 'none'; }
            else if (loginBgConfig.type === 'video' && loginBgConfig.filename) { videoEl.src = `/uploads/login_bg/${loginBgConfig.filename}?t=${Date.now()}`; videoEl.style.display = 'block'; videoEl.style.opacity = loginBgConfig.opacity || 0.35; videoEl.play().catch(() => {}); matrixEl.style.display = 'none'; }
            else { createMatrixAnimation('matrixBg', true); matrixEl.style.display = 'block'; }
        }

        function openLoginBgModal() {
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content" style="max-width:560px;"><h3 style="color:var(--text-accent);">🎬 Fundo da Tela de Login</h3><p style="font-size:12px;color:#6c757d;margin-bottom:15px;">Personalize com imagem, GIF ou vídeo.</p><div class="background-controls"><label><strong>📁 Escolher mídia</strong></label><input type="file" id="loginBgFileInput" accept="image/*,video/mp4,video/webm,video/ogg"><div class="image-preview" id="loginBgPreview"></div></div><div class="background-controls"><label><strong>🎨 Opacidade</strong></label><input type="range" id="loginBgOpacityRange" min="0.05" max="1" step="0.05" value="${loginBgConfig.opacity || 0.35}" oninput="document.getElementById('loginBgOpacityVal').innerText=Math.round(this.value*100)+'%'"><span id="loginBgOpacityVal">${Math.round((loginBgConfig.opacity || 0.35)*100)}%</span></div><div class="background-controls"><label><strong>🔢 Matrix</strong></label><button class="btn btn-secondary" onclick="setLoginBgMatrix()" style="width:100%;">Restaurar Matrix</button></div><div class="modal-buttons"><button class="btn btn-primary" onclick="uploadLoginBgMedia()">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">❌ Fechar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const fileInput = document.getElementById('loginBgFileInput');
            if (fileInput) { fileInput.onchange = async (e) => { const file = e.target.files[0]; if (!file) return; const preview = document.getElementById('loginBgPreview'); const url = URL.createObjectURL(file); if (file.type.startsWith('video/')) { preview.innerHTML = `<video src="${url}" style="max-width:100%;max-height:150px;border-radius:6px;" autoplay loop muted playsinline></video>`; } else { preview.innerHTML = `<img src="${url}" style="max-width:100%;max-height:150px;border-radius:6px;">`; } window.tempLoginBgFile = file; }; }
        }

        window.setLoginBgMatrix = async () => {
            try { const response = await fetch('/api/login_bg_config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'matrix' }) }); const data = await response.json(); if (data.success) { loginBgConfig = data.config; applyLoginBg(); showToast('✅ Matrix restaurado!'); closeModal(); } } catch(e) { showToast('❌ Erro'); }
        };

        window.uploadLoginBgMedia = async () => {
            if (!window.tempLoginBgFile) { showToast('⚠️ Selecione uma mídia'); return; }
            const file = window.tempLoginBgFile;
            if (file.size > 40 * 1024 * 1024) { showToast('⚠️ Máximo 40MB'); return; }
            showToast('📤 Enviando...');
            try {
                const base64 = await readImageAsBase64(file);
                const mediaType = file.type.startsWith('video/') ? 'video' : 'image';
                const opacity = parseFloat(document.getElementById('loginBgOpacityRange').value) || 0.35;
                const response = await fetch('/api/upload_login_bg', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ media: base64, type: mediaType, opacity: opacity }) });
                const data = await response.json();
                if (data.success) { loginBgConfig = data.config; applyLoginBg(); showToast('✅ Atualizado!'); closeModal(); }
                else { showToast('❌ ' + (data.error || 'Erro')); }
            } catch(e) { showToast('❌ Erro: ' + e.message); }
            window.tempLoginBgFile = null;
        };

        function openDevImageModal() {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>🖼️ Alterar Foto do Desenvolvedor</h3><input type="file" id="newDevImage" accept="image/*"><div class="image-preview" id="newDevPreview"></div><div class="modal-buttons"><button class="btn btn-primary" onclick="uploadNewDevImage()">✅ Salvar</button><button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const imageInput = document.getElementById('newDevImage');
            if (imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if (file) { const base64 = await readImageAsBase64(file); document.getElementById('newDevPreview').innerHTML = `<img src="${base64}" style="max-width:100px;">`; window.tempDevImage = base64; } }; }
        }

        window.uploadNewDevImage = async () => {
            if (!window.tempDevImage) { showToast('Selecione uma imagem'); return; }
            try { const response = await fetch('/api/upload_dev_image', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: window.tempDevImage }) }); const data = await response.json(); if (data.success) { showToast('✅ Atualizada!'); setTimeout(() => location.reload(), 1000); } } catch(e) { showToast('❌ Erro'); }
            window.tempDevImage = null; closeModal();
        };

        function openDynamicBgModal() {
            if (userRole !== 'admin' && userRole !== 'master') { showToast('Apenas administradores'); return; }
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3>🎬 Fundo Dinâmico</h3><p>GIF ou MP4</p><input type="file" id="newBgFile" accept="image/gif, video/mp4"><div class="image-preview" id="newBgPreview"></div><div class="modal-buttons"><button class="btn btn-primary" onclick="applyDynamicBg()">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const fileInput = document.getElementById('newBgFile');
            if (fileInput) { fileInput.onchange = (e) => { const file = e.target.files[0]; if (file) { const preview = document.getElementById('newBgPreview'); const url = URL.createObjectURL(file); preview.innerHTML = file.type.startsWith('image') ? `<img src="${url}" style="max-width:100px;">` : `<video src="${url}" style="max-width:100px;" autoplay loop muted></video>`; window.tempBgFile = file; } }; }
        }

        window.applyDynamicBg = () => {
            if (!window.tempBgFile) { showToast('Selecione um arquivo'); return; }
            const url = URL.createObjectURL(window.tempBgFile);
            if (window.tempBgFile.type.startsWith('image')) { document.getElementById('bgVideo').style.display = 'none'; document.getElementById('bgGif').src = url; document.getElementById('bgGif').style.display = 'block'; }
            else { document.getElementById('bgGif').style.display = 'none'; document.getElementById('bgVideo').src = url; document.getElementById('bgVideo').style.display = 'block'; }
            showToast('✅ Aplicado!'); closeModal();
        };

        async function doLogin() {
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;
            const btn = document.getElementById('loginBtn');
            const errEl = document.getElementById('loginError');
            errEl.style.display = 'none';
            if (!username || !password) { errEl.textContent = 'Preencha usuário e senha'; errEl.style.display = 'block'; return; }
            btn.disabled = true;
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span class="spinner"></span> Entrando...';
            try {
                const response = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
                const data = await response.json();
                if (data.success) {
                    currentUser = username; userRole = data.role;
                    if (data.role === 'admin' || data.role === 'master') { document.getElementById('loginBgToggle').style.display = 'flex'; }
                    document.getElementById('loginModal').style.display = 'none';
                    document.getElementById('loadingOverlay').style.display = 'flex';
                    document.getElementById('toolbar').style.display = 'flex';
                    document.getElementById('userInfo').innerHTML = `<span>👤 ${username}</span><span class="user-role">${data.role.toUpperCase()}</span>`;
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
                    showToast(`Bem-vindo, ${username}!`);
                } else {
                    errEl.textContent = data.error || 'Credenciais inválidas';
                    errEl.style.display = 'block';
                    btn.disabled = false; btn.innerHTML = originalText;
                }
            } catch(e) {
                errEl.textContent = 'Erro de conexão';
                errEl.style.display = 'block';
                btn.disabled = false; btn.innerHTML = originalText;
            }
        }
        
        function logout() { fetch('/api/logout', { method: 'POST' }).then(() => location.reload()); }
        
        canvas.addEventListener('dragover', (e) => e.preventDefault());
        canvas.addEventListener('drop', (e) => {
            e.preventDefault(); const {x, y} = getMousePos(e); const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            const component = { id: Date.now(), type: data.type || 'custom', subtype: data.subtype || '', name: data.name, x: x, y: y, icon: data.icon || '📦', iconFile: data.iconFile || null, color: data.color || '#005f99', angle: 0, fov: 80, rotation: 0, customImage: null, customIconTemp: null, customImageTemp: null, ip: '', port: 80, username: '', password: '' };
            components.push(component); showToast(`✅ ${component.name} adicionado!`); saveUserData();
        });
        
        canvas.addEventListener('touchstart', handleStart, { passive: false }); canvas.addEventListener('touchmove', handleMove, { passive: false }); canvas.addEventListener('touchend', handleEnd); canvas.addEventListener('touchcancel', handleEnd);
        canvas.addEventListener('mousedown', handleStart); canvas.addEventListener('mousemove', handleMove); canvas.addEventListener('mouseup', handleEnd); canvas.addEventListener('click', handleClick); canvas.addEventListener('contextmenu', handleContextMenu);
        
        (async function init() {
            await loadDefaultConfig();
            await loadDefaultConnections();
            categories = JSON.parse(JSON.stringify(defaultCategories));
            renderPalette();
            renderConnectionsPalette();
        })();

        loadDevImages(); createMatrixAnimation('introMatrixBg'); closeProperties();
        loadLoginBgConfig();
        setTimeout(() => { const splash = document.getElementById('splashScreen'); if (splash) splash.style.display = 'none'; }, 3000);
        
        window.newProject = newProject; window.saveProjectToFile = saveProjectToFile; window.loadProjectFromFile = loadProjectFromFile; window.exportPDF = exportPDF; window.exportPDFWithList = exportPDFWithList; window.generateBudget = generateBudget;
        window.zoomIn = zoomIn; window.zoomOut = zoomOut; window.resetZoom = resetZoom; window.iconZoomIn = iconZoomIn; window.iconZoomOut = iconZoomOut; window.resetIconSize = resetIconSize;
        window.togglePalette = togglePalette; window.closeModal = closeModal; window.openAddCategoryModal = openAddCategoryModal; window.openAddDeviceModal = openAddDeviceModal; window.openAddConnectionModal = openAddConnectionModal;
        window.doLogin = doLogin; window.logout = logout; window.openUserManagement = openUserManagement; window.addUser = addUser; window.deleteUser = deleteUser;
        window.setShapeMode = setShapeMode; window.cancelShapeMode = cancelShapeMode; window.toggleShapesToolbar = toggleShapesToolbar; window.toggleGrid = toggleGrid; window.resetToDefaultConfig = resetToDefaultConfig;
        window.openBackgroundModal = openBackgroundModal;
        window.closeIntroAndShowLogin = closeIntroAndShowLogin; window.closePropertiesPanel = closePropertiesPanel; window.toggleMobilePalette = toggleMobilePalette; window.closeMobilePalette = closeMobilePalette;
        window.nextSlide = nextSlide; window.prevSlide = prevSlide; window.currentSlide = currentSlide; window.deleteSelectedItems = deleteSelectedItems;
        window.loadLoginBgConfig = loadLoginBgConfig; window.applyLoginBg = applyLoginBg; window.openLoginBgModal = openLoginBgModal; window.uploadLoginBgMedia = uploadLoginBgMedia; window.setLoginBgMatrix = setLoginBgMatrix;
        window.openDevImageModal = openDevImageModal; window.uploadNewDevImage = uploadNewDevImage; window.openDynamicBgModal = openDynamicBgModal; window.applyDynamicBg = applyDynamicBg;
        
        // ==================== SIMULADOR 3D — APENAS DISPOSITIVOS DE REDE ====================
        (function() {
            const NETWORK_3D_CATALOG = {
                'router':        { unit: '1U', height: 0.4, label: 'Router',        visualType: 'router' },
                'switch_l2':     { unit: '1U', height: 0.4, label: 'Switch L2',     visualType: 'switch' },
                'switch_l3':     { unit: '1U', height: 0.4, label: 'Switch L3',     visualType: 'switch' },
                'switch_l2_poe': { unit: '1U', height: 0.4, label: 'Switch L2 PoE', visualType: 'switch' },
                'switch_l3_poe': { unit: '1U', height: 0.4, label: 'Switch L3 PoE', visualType: 'switch' },
                'olt':           { unit: '2U', height: 0.8, label: 'OLT GPON',      visualType: 'olt' },
                'onu':           { unit: '1U', height: 0.4, label: 'ONU',           visualType: 'onu' },
                'ont':           { unit: '1U', height: 0.4, label: 'ONT',           visualType: 'onu' },
                'converter':     { unit: '1U', height: 0.4, label: 'Conversor',     visualType: 'converter' },
                'patch':         { unit: '1U', height: 0.4, label: 'Patch Panel',   visualType: 'patch' },
                'nvr':           { unit: '1U', height: 0.4, label: 'NVR',           visualType: 'nvr' },
                'dvr':           { unit: '1U', height: 0.4, label: 'DVR',           visualType: 'nvr' },
                'pbx':           { unit: '2U', height: 0.8, label: 'PABX',          visualType: 'pbx' },
                'server':        { unit: '2U', height: 0.8, label: 'Servidor',      visualType: 'server' },
                'nas':           { unit: '3U', height: 1.2, label: 'NAS/SAN',       visualType: 'nas' },
                'nobreak':       { unit: '3U', height: 1.2, label: 'Nobreak',       visualType: 'ups' },
                'ups':           { unit: '3U', height: 1.2, label: 'UPS',           visualType: 'ups' },
                'pdu':           { unit: '1U', height: 0.3, label: 'PDU',           visualType: 'pdu' }
            };
            
            const NETWORK_TYPES_FILTER = ['router', 'switch_l2', 'switch_l3', 'switch_l2_poe', 'switch_l3_poe', 'olt', 'onu', 'ont', 'converter', 'cto', 'patch', 'nvr', 'dvr', 'pbx', 'nobreak', 'ups', 'pdu'];
            const NETWORK_CATEGORY_NAMES = ['rede', 'redes', 'network', 'networking'];
            
            let mountedInstances = [];
            let sim3dConnections = [];
            let activeSourceId = null;
            let selectedCable = 'cat6';
            let selectedDestinations = new Set();
            
            let scene3d, camera3d, renderer3d, controls3d;
            let rackMeshes = [];
            let cableGroup, particleGroup;
            let textureUpdates = [];
            let animFrame3d = null;
            let activeCableAnims = [];
            
            const raycaster3d = new THREE.Raycaster();
            const mouse3d = new THREE.Vector2();
            
            function isNetworkCategory(catName) { const lower = catName.toLowerCase(); return NETWORK_CATEGORY_NAMES.some(n => lower.includes(n)); }
            function isNetworkDevice(dev) { return NETWORK_TYPES_FILTER.includes(dev.type); }
            
            function getAvailableNetworkDevices() {
                const list = []; const seen = new Set();
                for (const [catName, catData] of Object.entries(categories || {})) {
                    if (!catData.devices) continue;
                    if (!isNetworkCategory(catName)) continue;
                    for (const dev of catData.devices) {
                        const key = dev.name + '|' + dev.type;
                        if (seen.has(key)) continue;
                        seen.add(key);
                        list.push({ ...dev, _category: catName });
                    }
                }
                for (const dev of (customDevices || [])) {
                    if (!isNetworkDevice(dev)) continue;
                    const key = dev.name + '|' + dev.type;
                    if (seen.has(key)) continue;
                    seen.add(key);
                    list.push({ ...dev, _category: 'Personalizados' });
                }
                return list;
            }
            
            function makeInstanceId(dev) { return dev.type + '::' + dev.name; }
            function findCatalogEntry(dev) { return NETWORK_3D_CATALOG[dev.type] || { unit: '1U', height: 0.4, label: dev.name, visualType: 'generic' }; }
            
            function init3DScene() {
                const container = document.getElementById('sim3d-container');
                container.innerHTML = '';
                scene3d = new THREE.Scene();
                scene3d.background = new THREE.Color(0x080b13);
                scene3d.fog = new THREE.FogExp2(0x080b13, 0.015);
                camera3d = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 100);
                camera3d.position.set(14, 6.5, 17);
                renderer3d = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
                renderer3d.setSize(window.innerWidth, window.innerHeight);
                renderer3d.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                renderer3d.shadowMap.enabled = true;
                renderer3d.shadowMap.type = THREE.PCFSoftShadowMap;
                renderer3d.toneMapping = THREE.ACESFilmicToneMapping;
                renderer3d.toneMappingExposure = 1.3;
                container.appendChild(renderer3d.domElement);
                controls3d = new THREE.OrbitControls(camera3d, renderer3d.domElement);
                controls3d.enableDamping = true; controls3d.dampingFactor = 0.05;
                controls3d.target.set(0, 3, 0); controls3d.maxPolarAngle = Math.PI / 2 + 0.05;
                controls3d.minDistance = 4; controls3d.maxDistance = 30;
                scene3d.add(new THREE.AmbientLight(0xffffff, 1.6));
                const spot = new THREE.SpotLight(0x38bdf8, 3.2); spot.position.set(10, 18, 12); spot.angle = Math.PI / 4; spot.castShadow = true; scene3d.add(spot);
                const fill = new THREE.PointLight(0x0284c7, 2.0, 30); fill.position.set(-12, 8, -5); scene3d.add(fill);
                cableGroup = new THREE.Group(); particleGroup = new THREE.Group();
                scene3d.add(cableGroup); scene3d.add(particleGroup);
                buildEnvironment3D(); buildRackCabinet3D();
                rebuildRack3D(); renderSim3DTrayUI();
                window.addEventListener('resize', onSim3DResize);
                renderer3d.domElement.addEventListener('click', onSim3DClick);
                animate3D();
            }
            
            function buildEnvironment3D() {
                const grid = new THREE.GridHelper(50, 50, 0x38bdf8, 0x1e293b);
                grid.position.y = -2.51; grid.material.opacity = 0.35; grid.material.transparent = true;
                scene3d.add(grid);
                const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshStandardMaterial({ color: 0x0a0e17, roughness: 0.4, metalness: 0.7 }));
                floor.rotation.x = -Math.PI / 2; floor.position.y = -2.52; floor.receiveShadow = true; scene3d.add(floor);
            }
            
            function buildRackCabinet3D() {
                const rackGroup = new THREE.Group();
                const metal = new THREE.MeshStandardMaterial({ color: 0x111622, roughness: 0.5, metalness: 0.85 });
                const pillarGeo = new THREE.BoxGeometry(0.3, 11, 0.3);
                [[-2.1, 2.7, -2.1], [2.1, 2.7, -2.1], [-2.1, 2.7, 2.1], [2.1, 2.7, 2.1]].forEach(pos => { const p = new THREE.Mesh(pillarGeo, metal); p.position.set(...pos); rackGroup.add(p); });
                const top = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.4, 4.6), metal); top.position.set(0, 8.2, 0); rackGroup.add(top);
                const bot = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.4, 4.6), metal); bot.position.set(0, -2.6, 0); rackGroup.add(bot);
                const doorGlass = new THREE.Mesh(new THREE.BoxGeometry(4.0, 10.2, 0.06), new THREE.MeshPhysicalMaterial({ color: 0x0284c7, transparent: true, opacity: 0.15, transmission: 0.85, roughness: 0.1 }));
                doorGlass.position.set(0, 2.7, 2.25); rackGroup.add(doorGlass);
                scene3d.add(rackGroup);
            }
            
            function createFrontTexture(visualType, name, isPowered) {
                const canvas = document.createElement('canvas');
                canvas.width = 1024; canvas.height = 256;
                const ctx = canvas.getContext('2d');
                
                function draw() {
                    ctx.fillStyle = '#0f172a'; ctx.fillRect(0, 0, 1024, 256);
                    ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 4; ctx.strokeRect(2, 2, 1020, 252);
                    ctx.fillStyle = '#1e293b'; ctx.fillRect(0, 0, 1024, 32);
                    ctx.fillStyle = '#e2e8f0'; ctx.font = 'bold 16px "JetBrains Mono", monospace';
                    ctx.fillText(name.toUpperCase().substring(0, 40), 16, 22);
                    ctx.fillStyle = isPowered ? '#22c55e' : '#475569';
                    ctx.beginPath(); ctx.arc(1000, 16, 6, 0, Math.PI * 2); ctx.fill();
                    
                    switch(visualType) {
                        case 'router':
                            ctx.fillStyle = '#475569'; ctx.font = '11px monospace'; ctx.fillText('WAN', 20, 60);
                            for (let i = 0; i < 4; i++) {
                                const x = 20 + i * 44;
                                ctx.fillStyle = '#020617'; ctx.fillRect(x, 70, 36, 30);
                                ctx.strokeStyle = '#0ea5e9'; ctx.strokeRect(x, 70, 36, 30);
                                ctx.fillStyle = isPowered && Math.random() > 0.2 ? '#22c55e' : '#1e293b';
                                ctx.fillRect(x + 14, 76, 8, 8);
                            }
                            ctx.fillStyle = '#020617'; ctx.fillRect(220, 70, 50, 30); ctx.strokeStyle = '#f59e0b'; ctx.strokeRect(220, 70, 50, 30);
                            ctx.fillStyle = isPowered ? '#f59e0b' : '#1e293b'; ctx.fillRect(240, 82, 10, 8);
                            ctx.fillStyle = '#020617'; ctx.fillRect(700, 65, 180, 55); ctx.strokeStyle = '#0ea5e9'; ctx.strokeRect(700, 65, 180, 55);
                            ctx.fillStyle = isPowered ? '#22c55e' : '#ef4444'; ctx.font = 'bold 14px monospace';
                            ctx.fillText(isPowered ? 'WAN: UP' : 'WAN: DOWN', 720, 90);
                            ctx.font = '10px monospace'; ctx.fillStyle = '#94a3b8'; ctx.fillText('CPU 12% | RAM 43%', 720, 108);
                            for (let i = 0; i < 12; i++) { ctx.fillStyle = isPowered && (Math.random() > 0.5) ? '#22c55e' : '#334155'; ctx.fillRect(20 + i * 70, 200, 40, 8); }
                            break;
                        case 'switch':
                            ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.fillText('24x RJ45 Gigabit + 2x SFP+', 20, 55);
                            for (let i = 0; i < 24; i++) {
                                const x = 20 + (i % 12) * 60; const y = 70 + Math.floor(i / 12) * 70;
                                ctx.fillStyle = '#020617'; ctx.fillRect(x, y, 50, 34);
                                ctx.strokeStyle = '#334155'; ctx.strokeRect(x, y, 50, 34);
                                ctx.fillStyle = isPowered && (Math.random() > 0.4) ? '#22c55e' : '#475569';
                                ctx.fillRect(x + 20, y + 4, 8, 5);
                            }
                            for (let i = 0; i < 2; i++) { ctx.fillStyle = '#020617'; ctx.fillRect(760 + i * 60, 70, 50, 34); ctx.strokeStyle = '#f59e0b'; ctx.strokeRect(760 + i * 60, 70, 50, 34); ctx.fillStyle = isPowered ? '#f59e0b' : '#334155'; ctx.fillRect(778 + i * 60, 80, 14, 10); }
                            break;
                        case 'olt':
                            ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.fillText('GPON OLT · 16 PON', 20, 55);
                            for (let i = 0; i < 2; i++) { ctx.fillStyle = isPowered ? '#22c55e' : '#475569'; ctx.beginPath(); ctx.arc(30 + i * 24, 85, 8, 0, Math.PI * 2); ctx.fill(); }
                            for (let i = 0; i < 16; i++) { const x = 140 + i * 50; ctx.fillStyle = '#020617'; ctx.fillRect(x, 80, 42, 26); ctx.strokeStyle = '#14b8a6'; ctx.strokeRect(x, 80, 42, 26); ctx.fillStyle = isPowered && Math.random() > 0.3 ? '#22c55e' : '#334155'; ctx.fillRect(x + 5, 86, 5, 5); }
                            ctx.fillStyle = '#020617'; ctx.fillRect(140, 140, 80, 30); ctx.strokeStyle = '#f59e0b'; ctx.strokeRect(140, 140, 80, 30);
                            ctx.fillStyle = '#f59e0b'; ctx.font = 'bold 12px monospace'; ctx.fillText('SFP+ UPLINK', 150, 160);
                            ctx.fillStyle = '#020617'; ctx.fillRect(700, 140, 220, 40); ctx.fillStyle = isPowered ? '#22c55e' : '#ef4444'; ctx.font = 'bold 14px monospace';
                            ctx.fillText(isPowered ? 'ONLINE · 47/64 ONU' : 'OFFLINE', 720, 168);
                            break;
                        case 'onu':
                            ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.fillText('GPON ONU · 4x LAN + WiFi', 20, 55);
                            ctx.fillStyle = '#020617'; ctx.fillRect(20, 80, 46, 30); ctx.strokeStyle = '#22c55e'; ctx.strokeRect(20, 80, 46, 30);
                            ctx.fillStyle = isPowered ? '#22c55e' : '#334155'; ctx.fillRect(32, 88, 10, 6);
                            for (let i = 0; i < 4; i++) { ctx.fillStyle = '#020617'; ctx.fillRect(110 + i * 55, 80, 46, 30); ctx.strokeStyle = '#334155'; ctx.strokeRect(110 + i * 55, 80, 46, 30); ctx.fillStyle = isPowered ? '#22c55e' : '#334155'; ctx.fillRect(124 + i * 55, 86, 6, 6); }
                            break;
                        case 'converter':
                            ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.fillText('MEDIA CONVERTER · Fiber ↔ RJ45', 20, 55);
                            ctx.fillStyle = '#020617'; ctx.fillRect(40, 80, 55, 40); ctx.strokeStyle = '#f59e0b'; ctx.strokeRect(40, 80, 55, 40);
                            ctx.fillStyle = isPowered ? '#f59e0b' : '#334155'; ctx.fillRect(60, 92, 14, 14);
                            ctx.fillStyle = '#020617'; ctx.fillRect(160, 80, 55, 40); ctx.strokeStyle = '#10b981'; ctx.strokeRect(160, 80, 55, 40);
                            ctx.fillStyle = '#10b981'; ctx.fillRect(178, 94, 18, 12);
                            ctx.fillStyle = isPowered ? '#22c55e' : '#475569'; ctx.font = 'bold 14px monospace'; ctx.fillText('PWR', 280, 110);
                            break;
                        case 'nvr':
                            ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.fillText('NVR/DVR · 16CH 4K', 20, 55);
                            for (let i = 0; i < 4; i++) { ctx.fillStyle = '#020617'; ctx.fillRect(20 + i * 70, 80, 60, 50); ctx.strokeStyle = '#8b5cf6'; ctx.strokeRect(20 + i * 70, 80, 60, 50); ctx.fillStyle = isPowered && Math.random() > 0.3 ? '#8b5cf6' : '#334155'; ctx.beginPath(); ctx.arc(50 + i * 70, 90, 4, 0, Math.PI * 2); ctx.fill(); }
                            ctx.fillStyle = '#020617'; ctx.fillRect(400, 80, 280, 50); ctx.strokeStyle = '#8b5cf6'; ctx.strokeRect(400, 80, 280, 50);
                            ctx.fillStyle = '#22c55e'; ctx.font = 'bold 14px monospace'; ctx.fillText(isPowered ? 'REC · CH01-CH16' : 'STANDBY', 420, 105);
                            break;
                        case 'pbx':
                            ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.fillText('PABX IP · 16x FXS + 4x FXO', 20, 55);
                            for (let bloco = 0; bloco < 2; bloco++) { for (let i = 0; i < 8; i++) { const x = 20 + bloco * 200 + i * 22; ctx.fillStyle = '#020617'; ctx.fillRect(x, 80, 18, 24); ctx.strokeStyle = bloco === 0 ? '#a855f7' : '#eab308'; ctx.strokeRect(x, 80, 18, 24); } }
                            break;
                        case 'server':
                            ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.fillText('RACK SERVER · 2U', 20, 55);
                            for (let i = 0; i < 8; i++) { const x = 20 + i * 80; ctx.fillStyle = '#020617'; ctx.fillRect(x, 80, 70, 60); ctx.strokeStyle = '#6366f1'; ctx.strokeRect(x, 80, 70, 60); ctx.fillStyle = isPowered ? '#6366f1' : '#334155'; ctx.fillRect(x + 8, 100, 54, 8); }
                            break;
                        case 'nas':
                            ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.fillText('NAS STORAGE · 12 BAYS', 20, 55);
                            for (let row = 0; row < 2; row++) { for (let i = 0; i < 12; i++) { const x = 20 + i * 55; const y = 80 + row * 55; ctx.fillStyle = '#020617'; ctx.fillRect(x, y, 48, 45); ctx.strokeStyle = '#6366f1'; ctx.strokeRect(x, y, 48, 45); ctx.fillStyle = isPowered && Math.random() > 0.2 ? '#22c55e' : '#334155'; ctx.beginPath(); ctx.arc(x + 24, y + 22, 4, 0, Math.PI * 2); ctx.fill(); } }
                            break;
                        case 'ups':
                        case 'pdu':
                            ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.fillText('UPS ONLINE · 3000VA', 20, 55);
                            ctx.fillStyle = '#020617'; ctx.fillRect(40, 80, 400, 100); ctx.strokeStyle = '#ef4444'; ctx.strokeRect(40, 80, 400, 100);
                            ctx.fillStyle = isPowered ? '#22c55e' : '#ef4444'; ctx.font = 'bold 32px monospace';
                            ctx.fillText(isPowered ? '220V · 87%' : '--- OFF ---', 60, 130);
                            break;
                        case 'patch':
                            for (let i = 0; i < 24; i++) { const x = 30 + i * 40; ctx.fillStyle = '#020617'; ctx.fillRect(x, 90, 30, 40); ctx.strokeStyle = '#64748b'; ctx.strokeRect(x, 90, 30, 40); ctx.fillStyle = '#eab308'; ctx.fillRect(x + 5, 98, 20, 4); }
                            break;
                        default:
                            ctx.fillStyle = '#020617'; ctx.fillRect(20, 80, 980, 130); ctx.strokeStyle = '#475569'; ctx.strokeRect(20, 80, 980, 130);
                            ctx.fillStyle = isPowered ? '#22c55e' : '#ef4444'; ctx.font = 'bold 20px monospace';
                            ctx.fillText(isPowered ? 'STATUS: ONLINE' : 'STATUS: OFF', 60, 150);
                    }
                }
                draw();
                const tex = new THREE.CanvasTexture(canvas);
                textureUpdates.push({ texture: tex, redraw: draw });
                return tex;
            }
            
            function rebuildRack3D() {
                rackMeshes.forEach(m => scene3d.remove(m));
                rackMeshes = [];
                let currentY = 7.0;
                mountedInstances.forEach((inst) => {
                    const catEntry = NETWORK_3D_CATALOG[inst.type] || { unit: '1U', height: 0.4, label: inst.name, visualType: 'generic' };
                    const group = new THREE.Group();
                    const width = 3.65; const height = catEntry.height; const depth = 3.4;
                    const isPowered = sim3dConnections.some(c => (c.to === inst.id || c.from === inst.id) && c.cable === 'power-ac');
                    const frontTexture = createFrontTexture(catEntry.visualType, inst.name, isPowered);
                    const materials = [
                        new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.3 }),
                        new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.3 }),
                        new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.7, roughness: 0.4 }),
                        new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.7, roughness: 0.4 }),
                        new THREE.MeshStandardMaterial({ map: frontTexture, roughness: 0.2, metalness: 0.5 }),
                        new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.9, roughness: 0.2 })
                    ];
                    const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), materials);
                    mesh.castShadow = true;
                    group.add(mesh);
                    addFrontDetails(group, catEntry.visualType, width, height, isPowered);
                    group.position.set(0, currentY - height / 2, 0);
                    group.userData = { instanceId: inst.id, type: inst.type, name: inst.name };
                    rackMeshes.push(group);
                    scene3d.add(group);
                    currentY -= (height + 0.1);
                });
                renderSim3DConnectionsUI();
            }
            
            function addFrontDetails(group, visualType, width, height, isPowered) {
                const detailY = height / 2 - 0.05; const detailZ = 1.72;
                if (visualType === 'switch') { for (let i = 0; i < 2; i++) { const sfp = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.06, 0.03), new THREE.MeshStandardMaterial({ color: isPowered ? 0xf59e0b : 0x334155, emissive: isPowered ? 0xf59e0b : 0x000000, emissiveIntensity: 0.5, metalness: 0.9, roughness: 0.2 })); sfp.position.set(1.3 - i * 0.25, detailY - 0.02, detailZ); group.add(sfp); } }
                else if (visualType === 'router') { for (let i = 0; i < 3; i++) { const antenna = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.5, 8), new THREE.MeshStandardMaterial({ color: 0x0ea5e9, metalness: 0.8, roughness: 0.3 })); antenna.position.set(-1.2 + i * 0.4, height / 2 + 0.2, detailZ - 0.1); antenna.rotation.z = 0.2; group.add(antenna); } }
                const powerLed = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 8), new THREE.MeshStandardMaterial({ color: isPowered ? 0x22c55e : 0x475569, emissive: isPowered ? 0x22c55e : 0x000000, emissiveIntensity: isPowered ? 1 : 0 }));
                powerLed.position.set(width / 2 - 0.15, detailY - 0.03, detailZ);
                group.add(powerLed);
            }
            
            function rebuildCables3D() {
                while (cableGroup.children.length > 0) cableGroup.remove(cableGroup.children[0]);
                while (particleGroup.children.length > 0) particleGroup.remove(particleGroup.children[0]);
                activeCableAnims = [];
                sim3dConnections.forEach(conn => {
                    const srcMesh = rackMeshes.find(m => m.userData.instanceId === conn.from);
                    const dstMesh = rackMeshes.find(m => m.userData.instanceId === conn.to);
                    if (!srcMesh || !dstMesh) return;
                    const zOffset = (conn.cable === 'power-ac') ? -1.7 : 1.7;
                    const p1 = new THREE.Vector3(srcMesh.position.x, srcMesh.position.y, srcMesh.position.z + zOffset);
                    const p2 = new THREE.Vector3(dstMesh.position.x, dstMesh.position.y, dstMesh.position.z + zOffset);
                    const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
                    mid.x += (conn.cable === 'power-ac') ? -2.2 : 2.2;
                    const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
                    const tubeGeo = new THREE.TubeGeometry(curve, 32, 0.035, 8, false);
                    let cableColor = 0x38bdf8; let particleColor = 0x22c55e;
                    if (conn.cable === 'fiber-sfp') { cableColor = 0xf59e0b; particleColor = 0xffffff; }
                    else if (conn.cable === 'power-ac') { cableColor = 0xef4444; particleColor = 0xfacc15; }
                    else if (conn.cable === 'coax-bnc') { cableColor = 0xa855f7; particleColor = 0x38bdf8; }
                    const cableMat = new THREE.MeshStandardMaterial({ color: cableColor, roughness: 0.3, metalness: 0.2 });
                    cableGroup.add(new THREE.Mesh(tubeGeo, cableMat));
                    const particleGeo = new THREE.BufferGeometry();
                    const count = 12;
                    const positions = new Float32Array(count * 3);
                    const progresses = [];
                    for (let i = 0; i < count; i++) { const t = i / count; progresses.push(t); const pt = curve.getPoint(t); positions[i * 3] = pt.x; positions[i * 3 + 1] = pt.y; positions[i * 3 + 2] = pt.z; }
                    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
                    const particleMat = new THREE.PointsMaterial({ color: particleColor, size: 0.1, transparent: true, opacity: 0.9 });
                    const pMesh = new THREE.Points(particleGeo, particleMat);
                    particleGroup.add(pMesh);
                    activeCableAnims.push({ mesh: pMesh, curve: curve, progress: progresses });
                });
                rebuildRack3D();
            }
            
            function renderSim3DTrayUI() {
                const tray = document.getElementById('sim3d-equipment-list');
                if (!tray) return;
                tray.innerHTML = '';
                const countEl = document.getElementById('sim3d-mounted-count');
                if (countEl) countEl.innerText = mountedInstances.length;
                const available = getAvailableNetworkDevices();
                if (available.length === 0) {
                    tray.innerHTML = '<p style="color:#64748b;font-size:11px;text-align:center;padding:20px;">Nenhum dispositivo na categoria <strong>Rede</strong>. Adicione equipamentos de rede no Projetize.</p>';
                    return;
                }
                available.forEach((dev) => {
                    const instanceId = makeInstanceId(dev);
                    const isMounted = mountedInstances.some(m => m.id === instanceId);
                    const catEntry = NETWORK_3D_CATALOG[dev.type] || { unit: '1U', label: dev.name };
                    const div = document.createElement('div');
                    div.className = `sim3d-eq-item ${isMounted ? 'mounted' : ''}`;
                    div.innerHTML = `
                        <div class="sim3d-eq-info" onclick="window.sim3dToggleMount('${instanceId.replace(/'/g, "\\'")}', '${dev.name.replace(/'/g, "\\'")}', '${dev.type}')">
                            <div class="sim3d-eq-name"><span class="sim3d-eq-unit">${catEntry.unit}</span>${dev.name}</div>
                            <div class="sim3d-eq-desc">${dev.desc || catEntry.label}</div>
                        </div>
                        <div class="sim3d-eq-actions">
                            ${isMounted ? `
                                <button onclick="event.stopPropagation();window.sim3dMoveUp('${instanceId.replace(/'/g, "\\'")}')" title="Subir" class="sim3d-eq-btn sim3d-eq-btn-small">▲</button>
                                <button onclick="event.stopPropagation();window.sim3dMoveDown('${instanceId.replace(/'/g, "\\'")}')" title="Descer" class="sim3d-eq-btn sim3d-eq-btn-small">▼</button>
                                <button onclick="event.stopPropagation();window.sim3dToggleMount('${instanceId.replace(/'/g, "\\'")}', '${dev.name.replace(/'/g, "\\'")}', '${dev.type}')" title="Remover" class="sim3d-eq-btn sim3d-eq-btn-remove">✕</button>
                            ` : `
                                <button onclick="event.stopPropagation();window.sim3dToggleMount('${instanceId.replace(/'/g, "\\'")}', '${dev.name.replace(/'/g, "\\'")}', '${dev.type}')" class="sim3d-eq-btn">Adicionar</button>
                            `}
                        </div>`;
                    tray.appendChild(div);
                });
            }
            
            window.sim3dToggleMount = function(instanceId, displayName, type) {
                const idx = mountedInstances.findIndex(m => m.id === instanceId);
                if (idx >= 0) { mountedInstances.splice(idx, 1); sim3dConnections = sim3dConnections.filter(c => c.from !== instanceId && c.to !== instanceId); sim3dShowToast('Removido do Rack.'); }
                else { mountedInstances.push({ id: instanceId, type: type, name: displayName }); sim3dShowToast(`"${displayName}" montado!`); }
                rebuildRack3D(); renderSim3DTrayUI(); rebuildCables3D();
                if (typeof window.saveSim3DState === 'function') window.saveSim3DState();
            };
            
            window.sim3dMoveUp = function(instanceId) { const idx = mountedInstances.findIndex(m => m.id === instanceId); if (idx <= 0) return; [mountedInstances[idx - 1], mountedInstances[idx]] = [mountedInstances[idx], mountedInstances[idx - 1]]; rebuildRack3D(); renderSim3DTrayUI(); rebuildCables3D(); if (typeof window.saveSim3DState === 'function') window.saveSim3DState(); };
            window.sim3dMoveDown = function(instanceId) { const idx = mountedInstances.findIndex(m => m.id === instanceId); if (idx < 0 || idx >= mountedInstances.length - 1) return; [mountedInstances[idx + 1], mountedInstances[idx]] = [mountedInstances[idx], mountedInstances[idx + 1]]; rebuildRack3D(); renderSim3DTrayUI(); rebuildCables3D(); if (typeof window.saveSim3DState === 'function') window.saveSim3DState(); };
            
            function onSim3DClick(event) {
                if (event.target.closest('#sim3d-patch-modal') || event.target.closest('#sim3d-terminal')) return;
                if (event.target.closest('.sim3d-drawer') || event.target.closest('.sim3d-header')) return;
                mouse3d.x = (event.clientX / window.innerWidth) * 2 - 1;
                mouse3d.y = -(event.clientY / window.innerHeight) * 2 + 1;
                raycaster3d.setFromCamera(mouse3d, camera3d);
                const intersects = raycaster3d.intersectObjects(rackMeshes, true);
                if (intersects.length > 0) {
                    let top = intersects[0].object;
                    while (top.parent && top.parent.type === 'Group' && top.parent !== scene3d) top = top.parent;
                    if (top.userData && top.userData.instanceId) openSim3DPatchModal(top.userData.instanceId, top.userData.name);
                }
            }
            
            function openSim3DPatchModal(instanceId, name) {
                activeSourceId = instanceId; selectedDestinations.clear();
                const titleEl = document.getElementById('sim3d-patch-title');
                if (titleEl) titleEl.innerText = `Conectar: ${name}`;
                const listContainer = document.getElementById('sim3d-dest-list');
                if (!listContainer) return;
                listContainer.innerHTML = '';
                mountedInstances.forEach(target => {
                    if (target.id === instanceId) return;
                    const label = document.createElement('label');
                    label.className = 'sim3d-dest-item';
                    label.innerHTML = `<span>${target.name}</span><input type="checkbox" value="${target.id}" onchange="window.sim3dToggleDest('${target.id.replace(/'/g, "\\'")}')">`;
                    listContainer.appendChild(label);
                });
                document.getElementById('sim3d-patch-modal').classList.add('open');
            }
            
            window.sim3dToggleDest = function(id) { if (selectedDestinations.has(id)) selectedDestinations.delete(id); else selectedDestinations.add(id); };
            
            function renderSim3DConnectionsUI() {
                const container = document.getElementById('sim3d-connections-list');
                const panel = document.getElementById('sim3d-connections-panel');
                const countEl = document.getElementById('sim3d-connections-count');
                if (!container) return;
                container.innerHTML = '';
                if (countEl) countEl.innerText = sim3dConnections.length;
                if (panel) panel.style.display = sim3dConnections.length > 0 ? 'flex' : 'none';
                sim3dConnections.forEach((c, idx) => {
                    const e1 = mountedInstances.find(m => m.id === c.from);
                    const e2 = mountedInstances.find(m => m.id === c.to);
                    const div = document.createElement('div');
                    div.className = 'sim3d-connection-row';
                    div.innerHTML = `<div style="truncate"><span class="tag">[${c.cable.toUpperCase()}]</span> ${(e1?.name || '?').substring(0, 14)} ↔ ${(e2?.name || '?').substring(0, 14)}</div><button onclick="window.sim3dRemoveConnection(${idx})" class="sim3d-connection-remove">✕</button>`;
                    container.appendChild(div);
                });
            }
            
            window.sim3dRemoveConnection = function(idx) { sim3dConnections.splice(idx, 1); rebuildCables3D(); sim3dShowToast('Conexão removida!'); if (typeof window.saveSim3DState === 'function') window.saveSim3DState(); };
            
            function runSim3DScript() {
                const modal = document.getElementById('sim3d-terminal');
                const output = document.getElementById('sim3d-terminal-output');
                if (!modal || !output) return;
                modal.classList.add('open');
                output.innerHTML = '<p style="color:#64748b;">[SYSTEM] Executando diagnóstico de rede...</p>';
                setTimeout(() => {
                    let logs = [];
                    if (mountedInstances.length === 0) logs.push('<span style="color:#fbbf24;">[ALERTA] Nenhum dispositivo montado.</span>');
                    else logs.push(`<span style="color:#34d399;">[OK] ${mountedInstances.length} dispositivos no rack.</span>`);
                    const hasRouter = mountedInstances.some(m => m.type === 'router');
                    const hasSwitch = mountedInstances.some(m => m.type.startsWith('switch'));
                    const hasOLT = mountedInstances.some(m => m.type === 'olt');
                    if (!hasRouter && !hasOLT && mountedInstances.length > 0) logs.push('<span style="color:#fbbf24;">[ALERTA] Sem router de borda ou OLT.</span>');
                    else if (hasRouter) logs.push('<span style="color:#34d399;">[OK] Router de borda detectado.</span>');
                    else if (hasOLT) logs.push('<span style="color:#34d399;">[OK] OLT GPON detectada.</span>');
                    if (hasSwitch) logs.push('<span style="color:#34d399;">[OK] Switch(es) detectado(s).</span>');
                    const dataConns = sim3dConnections.filter(c => c.cable === 'cat6' || c.cable === 'fiber-sfp');
                    if (dataConns.length > 0) logs.push(`<span style="color:#34d399;">[OK] ${dataConns.length} conexões de dados.</span>`);
                    logs.push('<br><span style="color:#67e8f9;font-weight:bold;">>>> DIAGNÓSTICO CONCLUÍDO <<<</span>');
                    sim3dShowToast('Diagnóstico completo!');
                    output.innerHTML += logs.join('<br>');
                    output.scrollTop = output.scrollHeight;
                }, 800);
            }
            
            function sim3dShowToast(msg) {
                const toast = document.getElementById('sim3d-toast');
                const msgEl = document.getElementById('sim3d-toast-message');
                if (!toast || !msgEl) return;
                msgEl.innerText = msg;
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 3000);
            }
            
            function onSim3DResize() { if (!camera3d || !renderer3d) return; camera3d.aspect = window.innerWidth / window.innerHeight; camera3d.updateProjectionMatrix(); renderer3d.setSize(window.innerWidth, window.innerHeight); }
            
            let lastBlink3d = 0;
            function animate3D(timestamp) {
                animFrame3d = requestAnimationFrame(animate3D);
                if (!lastBlink3d || timestamp - lastBlink3d > 250) { lastBlink3d = timestamp; textureUpdates.forEach(item => { item.redraw(); item.texture.needsUpdate = true; }); }
                activeCableAnims.forEach(anim => {
                    const positions = anim.mesh.geometry.attributes.position.array;
                    for (let i = 0; i < anim.progress.length; i++) { anim.progress[i] += 0.007; if (anim.progress[i] > 1) anim.progress[i] = 0; const pt = anim.curve.getPoint(anim.progress[i]); positions[i * 3] = pt.x; positions[i * 3 + 1] = pt.y; positions[i * 3 + 2] = pt.z; }
                    anim.mesh.geometry.attributes.position.needsUpdate = true;
                });
                if (controls3d) controls3d.update();
                if (renderer3d) renderer3d.render(scene3d, camera3d);
            }
            
            window.saveSim3DState = function() {
                if (!currentUser) return;
                localStorage.setItem(STORAGE_KEYS.SIM3D_MOUNTED(currentUser), JSON.stringify(mountedInstances));
                localStorage.setItem(STORAGE_KEYS.SIM3D_CONNECTIONS(currentUser), JSON.stringify(sim3dConnections));
            };
            
            window.loadSim3DState = function() {
                if (!currentUser) return;
                try {
                    const saved = localStorage.getItem(STORAGE_KEYS.SIM3D_MOUNTED(currentUser));
                    if (saved) mountedInstances = JSON.parse(saved);
                    const savedConn = localStorage.getItem(STORAGE_KEYS.SIM3D_CONNECTIONS(currentUser));
                    if (savedConn) sim3dConnections = JSON.parse(savedConn);
                } catch(e) { console.error(e); }
            };
            
            window.openSim3D = function() {
                const overlay = document.getElementById('sim3d-overlay');
                if (!overlay) return;
                overlay.classList.add('active');
                loadSim3DState();
                setTimeout(() => { init3DScene(); setupSim3DEventListeners(); }, 50);
            };
            
            function setupSim3DEventListeners() {
                const bind = (id, handler) => { const el = document.getElementById(id); if (el && !el.dataset.bound) { el.dataset.bound = '1'; el.addEventListener('click', handler); } };
                bind('sim3d-close-btn', () => {
                    document.getElementById('sim3d-overlay').classList.remove('active');
                    if (animFrame3d) cancelAnimationFrame(animFrame3d);
                    if (renderer3d && renderer3d.domElement && renderer3d.domElement.parentNode) renderer3d.domElement.parentNode.removeChild(renderer3d.domElement);
                    if (scene3d) { while (scene3d.children.length > 0) scene3d.remove(scene3d.children[0]); }
                    rackMeshes = []; textureUpdates = []; activeCableAnims = [];
                });
                bind('sim3d-toggle-drawer', () => { document.getElementById('sim3d-equipment-drawer').classList.toggle('closed'); });
                bind('sim3d-close-drawer', () => { document.getElementById('sim3d-equipment-drawer').classList.add('closed'); });
                bind('sim3d-run-script', runSim3DScript);
                bind('sim3d-terminal-close', () => { document.getElementById('sim3d-terminal').classList.remove('open'); });
                bind('sim3d-patch-close', () => { document.getElementById('sim3d-patch-modal').classList.remove('open'); });
                bind('sim3d-confirm-patch', () => {
                    if (selectedDestinations.size === 0) { sim3dShowToast('⚠️ Selecione pelo menos um destino!'); return; }
                    selectedDestinations.forEach(destId => {
                        const exists = sim3dConnections.some(c => (c.from === activeSourceId && c.to === destId) || (c.from === destId && c.to === activeSourceId));
                        if (!exists) sim3dConnections.push({ from: activeSourceId, to: destId, cable: selectedCable });
                    });
                    rebuildCables3D();
                    document.getElementById('sim3d-patch-modal').classList.remove('open');
                    sim3dShowToast('Conexão(ões) estabelecida(s)!');
                    if (typeof window.saveSim3DState === 'function') window.saveSim3DState();
                });
                bind('sim3d-reset-btn', () => {
                    if (confirm('Resetar rack 3D?')) {
                        mountedInstances = []; sim3dConnections = [];
                        rebuildRack3D(); renderSim3DTrayUI(); rebuildCables3D();
                        sim3dShowToast('Rack resetado!');
                        if (typeof window.saveSim3DState === 'function') window.saveSim3DState();
                    }
                });
                document.querySelectorAll('.sim3d-cable-btn').forEach(btn => {
                    if (btn.dataset.bound) return;
                    btn.dataset.bound = '1';
                    btn.addEventListener('click', (e) => {
                        document.querySelectorAll('.sim3d-cable-btn').forEach(b => b.classList.remove('active'));
                        e.currentTarget.classList.add('active');
                        selectedCable = e.currentTarget.getAttribute('data-cable');
                    });
                });
            }
        })();
        // ===================================================================
    </script>
</body>
</html>
"""
