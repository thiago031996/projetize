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

def load_login_bg_config():
    if os.path.exists(LOGIN_BG_CONFIG_FILE):
        try:
            with open(LOGIN_BG_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {'type': 'gradient', 'url': '', 'opacity': 0.6}

def save_login_bg_config(config):
    try:
        with open(LOGIN_BG_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except: return False

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

# ============ ROTAS PARA FUNDO DO LOGIN ============
@app.route('/api/login_bg_config', methods=['GET'])
def get_login_bg_config():
    return jsonify({'success': True, 'config': load_login_bg_config()})

@app.route('/api/upload_login_bg', methods=['POST'])
def upload_login_bg():
    data = request.json
    file_type = data.get('type', 'image')
    file_data = data.get('data', '')
    
    if not file_data:
        return jsonify({'success': False, 'error': 'Dados vazios'}), 400
    
    try:
        if file_type == 'video':
            if ',' in file_data:
                file_data = file_data.split(',')[1]
            ext = data.get('ext', '.mp4')
            filename = f"login_bg_{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(BACKGROUNDS_FOLDER, filename)
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(file_data))
        else:
            filename = save_background_image(file_data, f"login_bg_{uuid.uuid4().hex}")
            if not filename:
                return jsonify({'success': False, 'error': 'Erro ao processar imagem'}), 500
        
        url = f'/uploads/backgrounds/{filename}'
        
        config = load_login_bg_config()
        config['url'] = url
        config['type'] = file_type
        save_login_bg_config(config)
        
        return jsonify({'success': True, 'url': url, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_login_bg_config', methods=['POST'])
def save_login_bg_config_route():
    data = request.json
    config = load_login_bg_config()
    if 'opacity' in data:
        config['opacity'] = float(data['opacity'])
    if 'type' in data:
        config['type'] = data['type']
    if 'url' in data:
        config['url'] = data['url']
    save_login_bg_config(config)
    return jsonify({'success': True, 'config': config})

@app.route('/api/reset_login_bg', methods=['POST'])
def reset_login_bg():
    config = {'type': 'gradient', 'url': '', 'opacity': 0.6}
    save_login_bg_config(config)
    return jsonify({'success': True})
# ====================================================

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

# ==================== HTML TEMPLATE ====================
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Projetize - Sistema Para CFTV, Redes e muito mais...</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; overflow: hidden; position: fixed; top: 0; left: 0; right: 0; bottom: 0; }
        :root {
            --bg-primary: #ffffff; --bg-secondary: #f8f9fa; --bg-tertiary: #e9ecef;
            --bg-card: #ffffff; --text-primary: #212529; --text-secondary: #6c757d;
            --text-accent: #005f99; --border-color: #dee2e6; --button-primary: #005f99;
            --button-primary-hover: #004d7a; --button-secondary: #e9ecef;
            --shadow: rgba(0, 95, 153, 0.2);
            --palette-width: 280px; --properties-width: 340px;
            --mobile-nav-height: 65px; --mobile-toolbar-height: 52px;
        }
        
        .rgb-line { position: fixed; top: 0; left: 0; width: 100%; height: 3px; background: linear-gradient(90deg, #005f99, #0099cc, #00ccff, #005f99); background-size: 300% 100%; animation: rgbMove 3s linear infinite; z-index: 99999; }
        @keyframes rgbMove { 0% { background-position: 0% 0%; } 100% { background-position: 300% 100%; } }
        
        /* ============ FUNDO DINÂMICO DO LOGIN ============ */
        .login-bg-dynamic {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            object-fit: cover; z-index: 0; pointer-events: none; display: none;
        }
        .login-bg-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: linear-gradient(135deg, rgba(0,26,46,0.85), rgba(0,38,77,0.85));
            z-index: 1; pointer-events: none;
        }
        
        /* ============ LOGIN ============ */
        .login-modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; z-index: 20000; overflow-y: auto; padding: 20px; background: linear-gradient(135deg, #001a2e, #00264d); }
        .login-dev-container { position: relative; z-index: 2; width: 100%; max-width: 500px; background: rgba(0, 38, 77, 0.92); backdrop-filter: blur(10px); border-radius: 20px; padding: 40px; text-align: center; border: 1px solid #ffffff; box-shadow: 0 0 30px rgba(255, 255, 255, 0.2); }
        .login-dev-image { width: 150px; height: 150px; border-radius: 50%; margin: 0 auto 20px; overflow: hidden; border: 3px solid #ffffff; display: flex; align-items: center; justify-content: center; background: #005f99; }
        .login-dev-image img { width: 100%; height: 100%; object-fit: cover; }
        .login-dev-name { font-size: 24px; color: #ffffff; margin-bottom: 5px; font-weight: bold; }
        .login-dev-role { font-size: 12px; color: #ccccff; margin-bottom: 20px; }
        .login-logo { font-size: 50px; margin-bottom: 15px; }
        .login-title { font-size: 28px; color: #ffffff; margin-bottom: 10px; font-weight: bold; }
        .login-subtitle { color: #ccccff; font-size: 12px; margin-bottom: 25px; }
        .login-input { width: 100%; padding: 12px; margin: 10px 0; background: rgba(0, 38, 77, 0.8); border: 1px solid #ffffff; border-radius: 8px; color: #fff; font-size: 14px; }
        .login-input::placeholder { color: #88aacc; }
        .login-btn { width: 100%; padding: 12px; background: #ffffff; border: none; border-radius: 8px; color: #001a2e; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; }
        .login-error { color: #ff6666; font-size: 12px; margin-top: 15px; display: none; }
        .login-footer { margin-top: 25px; padding-top: 15px; border-top: 1px solid #ffffff; font-size: 11px; color: #ccccff; }
        .login-footer a { color: #ffffff; text-decoration: none; }
        
        /* ============ MODAL CONFIG BG (DENTRO DO SISTEMA) ============ */
        .bg-config-modal {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.95); z-index: 999999; display: none;
            justify-content: center; align-items: center; padding: 20px; overflow-y: auto;
        }
        .bg-config-modal.active { display: flex; }
        .bg-config-content {
            background: linear-gradient(135deg, #00264d, #001a2e);
            border: 2px solid #00ccff; border-radius: 20px; padding: 30px;
            width: 100%; max-width: 550px; color: white; max-height: 90vh;
            overflow-y: auto; box-shadow: 0 0 40px rgba(0, 204, 255, 0.5);
        }
        .bg-config-content h2 { color: #00ccff; margin-bottom: 20px; text-align: center; font-size: 22px; }
        .bg-config-content .form-group { margin-bottom: 18px; }
        .bg-config-content label { display: block; color: #ccccff; font-size: 13px; margin-bottom: 8px; font-weight: 600; }
        .bg-config-content input[type="file"] {
            width: 100%; padding: 12px; background: rgba(0, 0, 0, 0.4);
            border: 1px dashed #00ccff; border-radius: 8px; color: white; font-size: 13px; cursor: pointer;
        }
        .bg-config-content input[type="file"]::file-selector-button {
            background: #00ccff; color: #001a2e; border: none; padding: 8px 15px;
            border-radius: 6px; font-weight: bold; cursor: pointer; margin-right: 10px;
        }
        .bg-config-content input[type="range"] { width: 100%; margin-top: 8px; }
        .bg-config-content .preview-box {
            width: 100%; height: 180px; background: rgba(0, 0, 0, 0.5);
            border: 2px solid #00ccff; border-radius: 10px; overflow: hidden;
            display: flex; align-items: center; justify-content: center; margin-top: 10px;
        }
        .bg-config-content .preview-box img, .bg-config-content .preview-box video { max-width: 100%; max-height: 100%; object-fit: contain; }
        .bg-config-content .preview-box .empty-preview { color: #88aacc; font-size: 13px; text-align: center; padding: 20px; }
        .bg-config-buttons { display: flex; gap: 10px; margin-top: 25px; flex-wrap: wrap; }
        .bg-config-btn { flex: 1; padding: 14px; border: none; border-radius: 10px; font-size: 14px; font-weight: bold; cursor: pointer; min-width: 120px; }
        .bg-config-btn-primary { background: #00ccff; color: #001a2e; }
        .bg-config-btn-danger { background: #dc3545; color: white; }
        .bg-config-btn-secondary { background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.3); }
        .bg-config-tip { background: rgba(0, 204, 255, 0.1); border-left: 3px solid #00ccff; padding: 10px 12px; border-radius: 6px; font-size: 12px; color: #b3e6ff; margin-bottom: 15px; line-height: 1.5; }
        
        /* ============ RESTO DO SISTEMA ============ */
        .dev-badge { position: fixed; top: 10px; left: 10px; width: 45px; height: 45px; border-radius: 50%; background: var(--bg-tertiary); border: 2px solid var(--border-color); cursor: pointer; z-index: 1000; overflow: hidden; }
        .dev-badge-img { width: 41px; height: 41px; border-radius: 50%; object-fit: cover; }
        
        .toolbar { background: var(--bg-secondary); padding: 8px 15px; display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 2px solid var(--border-color); z-index: 100; position: relative; margin-left: 60px; }
        .btn { padding: 6px 12px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
        .btn-primary { background: var(--button-primary); color: #fff; }
        .btn-secondary { background: var(--button-secondary); color: var(--text-primary); border: 1px solid var(--border-color); }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-info { background: var(--button-secondary); color: var(--text-primary); }
        .btn-warning { background: #ffc107; color: #212529; }
        .user-info { display: flex; align-items: center; gap: 10px; background: var(--bg-tertiary); padding: 4px 12px; border-radius: 20px; font-size: 12px; }
        .user-role { background: var(--text-accent); color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 10px; }
        
        .main-container { display: flex; height: calc(100vh - 52px); position: relative; overflow: hidden; }
        
        .palette { width: var(--palette-width); background: var(--bg-tertiary); color: var(--text-primary); overflow-y: auto; padding: 10px; border-right: 2px solid var(--border-color); position: relative; flex-shrink: 0; }
        .palette.collapsed { width: 50px; min-width: 50px; }
        .palette.collapsed .category h3, .palette.collapsed .component-info, .palette.collapsed .category-actions, .palette.collapsed .component-actions { display: none; }
        .toggle-palette { position: sticky; top: 10px; right: -12px; float: right; background: var(--button-primary); border: none; color: #fff; width: 24px; height: 40px; border-radius: 0 8px 8px 0; cursor: pointer; z-index: 10; font-size: 12px; margin-bottom: 10px; }
        
        .category { margin-bottom: 15px; clear: both; }
        .category-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
        .category h3 { font-size: 12px; color: var(--text-accent); border-left: 3px solid var(--border-color); padding-left: 8px; }
        .category-actions { display: flex; gap: 5px; }
        .category-actions button { background: none; border: none; color: var(--text-accent); cursor: pointer; font-size: 12px; padding: 2px 5px; }
        .component { background: var(--bg-card); border-radius: 8px; padding: 6px 10px; margin-bottom: 6px; cursor: grab; display: flex; align-items: center; gap: 10px; border: 1px solid var(--border-color); position: relative; user-select: none; }
        .component-icon { font-size: 20px; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; }
        .component-icon img { width: 24px; height: 24px; object-fit: contain; }
        .component-info { flex: 1; }
        .component-name { font-size: 12px; font-weight: 600; }
        .component-desc { font-size: 9px; opacity: 0.7; }
        .component-actions { position: absolute; right: 5px; top: 50%; transform: translateY(-50%); display: none; gap: 5px; }
        .component:hover .component-actions { display: flex; }
        .component-actions button { background: var(--button-primary); border: none; color: #fff; border-radius: 3px; cursor: pointer; font-size: 10px; padding: 2px 4px; }
        
        .canvas-area { flex: 1; background: var(--bg-primary); overflow: auto; position: relative; -webkit-overflow-scrolling: touch; touch-action: none; }
        .canvas-area::-webkit-scrollbar { width: 12px; height: 12px; }
        .canvas-area::-webkit-scrollbar-track { background: #e9ecef; }
        .canvas-area::-webkit-scrollbar-thumb { background: #005f99; border-radius: 6px; }
        #canvas { background: transparent; cursor: crosshair; display: block; margin: 20px auto; transform-origin: 0 0; touch-action: none; }
        
        .properties { width: 0; background: var(--bg-tertiary); color: var(--text-primary); padding: 0; overflow-y: auto; transition: width 0.3s ease; position: relative; flex-shrink: 0; }
        .properties.open { width: var(--properties-width); padding: 15px; border-left: 2px solid var(--border-color); }
        .properties-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .close-properties-btn { background: none; border: none; font-size: 18px; cursor: pointer; color: var(--text-secondary); padding: 5px; }
        
        .property-group { margin-bottom: 12px; }
        .property-group label { display: block; font-size: 11px; margin-bottom: 4px; color: var(--text-accent); }
        .property-group input, .property-group select, .property-group textarea { width: 100%; padding: 6px; border-radius: 5px; border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-primary); font-size: 12px; }
        
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: center; z-index: 3000; padding: 20px; }
        .modal-content { background: var(--bg-secondary); padding: 25px; border-radius: 12px; width: 500px; max-width: 100%; max-height: 85%; overflow-y: auto; border: 1px solid var(--border-color); }
        .modal-content input, .modal-content select, .modal-content textarea { width: 100%; padding: 8px; margin: 8px 0; background: var(--bg-tertiary); border: none; border-radius: 5px; color: var(--text-primary); }
        .modal-buttons { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
        
        .toast { position: fixed; bottom: 20px; right: 20px; background: var(--button-primary); color: #fff; padding: 10px 20px; border-radius: 5px; z-index: 40000; max-width: 90%; }
        
        .context-menu { position: fixed; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 5px 0; z-index: 40000; display: none; min-width: 200px; }
        .context-menu-item { padding: 12px 18px; cursor: pointer; color: var(--text-primary); font-size: 13px; }
        .context-menu-item:hover { background: var(--button-primary); color: #fff; }
        
        .shapes-toolbar { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: var(--bg-secondary); padding: 8px 15px; border-radius: 30px; display: flex; gap: 8px; z-index: 150; border: 1px solid var(--border-color); flex-wrap: wrap; max-width: 90%; justify-content: center; }
        .shape-btn { background: var(--bg-tertiary); border: none; color: var(--text-primary); padding: 6px 12px; border-radius: 20px; cursor: pointer; font-size: 12px; }
        .shape-btn:hover, .shape-btn.active { background: var(--button-primary); color: #fff; }
        
        .dynamic-background { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; object-fit: cover; pointer-events: none; opacity: 0.3; display: none; }
        .loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 26, 46, 0.95); z-index: 50000; display: none; flex-direction: column; justify-content: center; align-items: center; color: white; }
        .loading-spinner { border: 8px solid #f3f3f3; border-top: 8px solid #00ccff; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; margin-bottom: 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .loading-text { font-size: 18px; font-weight: bold; }
        
        /* ============ MOBILE STYLES ============ */
        body.mobile-mode .dev-badge { display: none; }
        body.mobile-mode .toolbar { position: fixed; top: 0; left: 0; right: 0; margin-left: 0; padding: 8px 10px; background: var(--button-primary); color: white; overflow-x: auto; overflow-y: hidden; flex-wrap: nowrap; height: var(--mobile-toolbar-height); z-index: 500; -webkit-overflow-scrolling: touch; }
        body.mobile-mode .toolbar::-webkit-scrollbar { display: none; }
        body.mobile-mode .toolbar .btn { flex-shrink: 0; background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 12px; font-size: 11px; }
        body.mobile-mode .toolbar .user-info { display: none !important; }
        body.mobile-mode .toolbar .zoom-controls { display: none !important; }
        body.mobile-mode .toolbar span[style*="flex:1"] { display: none !important; }
        body.mobile-mode .main-container { height: calc(100vh - var(--mobile-toolbar-height) - var(--mobile-nav-height)); margin-top: var(--mobile-toolbar-height); margin-bottom: var(--mobile-nav-height); display: block; position: relative; }
        body.mobile-mode .palette { position: fixed; top: var(--mobile-toolbar-height); bottom: var(--mobile-nav-height); left: 0; right: 0; width: 100% !important; max-width: 100% !important; z-index: 400; transform: translateY(100%); transition: transform 0.3s ease; padding: 15px; overflow-y: auto; border: none; background: var(--bg-secondary); }
        body.mobile-mode .palette.mobile-open { transform: translateY(0); }
        body.mobile-mode .palette .toggle-palette { display: none; }
        body.mobile-mode #categories-container, body.mobile-mode #connections-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; }
        body.mobile-mode .category { margin-bottom: 15px; grid-column: 1 / -1; }
        body.mobile-mode .category h3 { font-size: 13px; padding: 8px; background: var(--button-primary); color: white; border-radius: 6px; border-left: none; }
        body.mobile-mode .category-actions { display: flex !important; }
        body.mobile-mode .category-actions button { background: var(--button-primary); color: white; padding: 4px 8px; border-radius: 4px; font-size: 14px; }
        body.mobile-mode .category > div { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; }
        body.mobile-mode .component { flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 12px 6px; min-height: 90px; cursor: pointer; }
        body.mobile-mode .component-icon { font-size: 32px; width: auto; height: auto; margin-bottom: 5px; }
        body.mobile-mode .component-icon img { width: 32px; height: 32px; }
        body.mobile-mode .component-info { flex: none; width: 100%; }
        body.mobile-mode .component-name { font-size: 11px; word-break: break-word; }
        body.mobile-mode .component-actions { display: flex !important; position: static; transform: none; margin-top: 5px; justify-content: center; }
        body.mobile-mode .canvas-area { position: absolute; top: 0; left: 0; right: 0; bottom: 0; }
        body.mobile-mode .properties { position: fixed; top: var(--mobile-toolbar-height); bottom: var(--mobile-nav-height); left: 0; right: 0; width: 100% !important; z-index: 450; transform: translateY(100%); transition: transform 0.3s ease; padding: 15px; overflow-y: auto; border: none; background: var(--bg-secondary); }
        body.mobile-mode .properties.open { transform: translateY(0); width: 100% !important; }
        
        .mobile-nav { display: none; position: fixed; bottom: 0; left: 0; right: 0; height: var(--mobile-nav-height); background: var(--bg-secondary); border-top: 2px solid var(--border-color); z-index: 600; }
        body.mobile-mode .mobile-nav { display: flex; }
        .mobile-nav-btn { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; background: none; border: none; color: var(--text-secondary); font-size: 10px; cursor: pointer; gap: 3px; padding: 5px; }
        .mobile-nav-btn.active { color: var(--button-primary); background: rgba(0, 95, 153, 0.1); }
        .mobile-nav-btn .nav-icon { font-size: 22px; }
        .mobile-nav-btn .nav-label { font-weight: 600; }
        
        .mobile-fab-container { display: none; position: fixed; bottom: calc(var(--mobile-nav-height) + 15px); right: 15px; flex-direction: column; gap: 10px; z-index: 550; }
        body.mobile-mode .mobile-fab-container { display: flex; }
        .mobile-fab { width: 50px; height: 50px; border-radius: 50%; background: var(--button-primary); color: white; border: none; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 10px rgba(0,0,0,0.3); }
        
        .mobile-overlay { display: none; position: fixed; top: var(--mobile-toolbar-height); bottom: var(--mobile-nav-height); left: 0; right: 0; background: rgba(0,0,0,0.3); z-index: 390; }
        .mobile-overlay.active { display: block; }
    </style>
</head>
<body>
    <video id="loginBgVideo" class="login-bg-dynamic" autoplay loop muted playsinline></video>
    <img id="loginBgGif" class="login-bg-dynamic" src="" alt="">
    <div id="loginBgOverlay" class="login-bg-overlay"></div>

    <video id="bgVideo" class="dynamic-background" autoplay loop muted playsinline></video>
    <img id="bgGif" class="dynamic-background" src="" alt="">

    <div id="loadingOverlay" class="loading-overlay">
        <div class="loading-spinner"></div>
        <div class="loading-text">Carregando módulos...</div>
    </div>

    <div class="rgb-line"></div>
    
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
    
    <!-- MODAL DE CONFIGURAÇÃO DO FUNDO DO LOGIN (SÓ ACESSÍVEL PÓS-LOGIN) -->
    <div class="bg-config-modal" id="bgConfigModal">
        <div class="bg-config-content">
            <h2>🎬 Fundo do Login</h2>
            <div class="bg-config-tip">
                💡 <strong>Dica:</strong> Você pode usar uma <strong>imagem</strong>, <strong>GIF animado</strong> ou <strong>vídeo MP4</strong> como fundo da tela de login.
                <br>O arquivo será salvo no servidor e aplicado para todos os usuários.
            </div>
            <div class="form-group">
                <label>📁 Escolha o arquivo (Imagem, GIF ou Vídeo MP4)</label>
                <input type="file" id="loginBgFileInput" accept="image/*,video/mp4,video/webm">
            </div>
            <div class="form-group">
                <label>👁️ Pré-visualização</label>
                <div class="preview-box" id="loginBgPreview">
                    <div class="empty-preview">Nenhum arquivo selecionado</div>
                </div>
            </div>
            <div class="form-group">
                <label>🎨 Opacidade do Fundo: <span id="loginBgOpacityValue">60%</span></label>
                <input type="range" id="loginBgOpacityRange" min="0.1" max="1" step="0.05" value="0.6">
            </div>
            <div class="bg-config-buttons">
                <button class="bg-config-btn bg-config-btn-primary" onclick="applyLoginBg()">✅ Aplicar</button>
                <button class="bg-config-btn bg-config-btn-danger" onclick="resetLoginBg()">🔄 Padrão</button>
                <button class="bg-config-btn bg-config-btn-secondary" onclick="closeLoginBgConfig()">❌ Fechar</button>
            </div>
        </div>
    </div>
    
    <div class="dev-badge" id="devBadge">
        <img class="dev-badge-img" id="badgeDevImage" src="" alt="TS">
    </div>
    
    <div class="context-menu" id="contextMenu"></div>
    <div class="mobile-overlay" id="mobileOverlay" onclick="closeMobilePanels()"></div>

    <div class="toolbar" id="toolbar" style="display: none;">
        <button class="btn btn-primary" onclick="newProject()">📁 <span>Novo</span></button>
        <button class="btn btn-secondary" onclick="saveProjectToFile()">💾 <span>Salvar</span></button>
        <button class="btn btn-secondary" onclick="loadProjectFromFile()">📂 <span>Carregar</span></button>
        <button class="btn btn-primary" onclick="exportPDFWithList()">📄 <span>PDF</span></button>
        <button class="btn btn-primary" onclick="exportPDF()">📄 <span>Mapa</span></button>
        <button class="btn btn-warning" onclick="generateBudget()">💰 <span>Orçamento</span></button>
        <button class="btn btn-danger" onclick="deleteSelectedItems()">🗑 <span>Excluir</span></button>
        <button id="adminUsersBtn" class="btn btn-info" onclick="openUserManagement()" style="display: none;">👥 <span>Usuários</span></button>
        <button id="adminShapesBtn" class="btn btn-info" onclick="toggleShapesToolbar()" style="display: none;">📐 <span>Formas</span></button>
        <button id="adminCategoriesBtn" class="btn btn-info" onclick="openAddCategoryModal()" style="display: none;">📁 <span>+Cat</span></button>
        <button id="adminDevicesBtn" class="btn btn-info" onclick="openAddDeviceModal()" style="display: none;">🔧 <span>+Equip</span></button>
        <button id="adminConnectionsBtn" class="btn btn-info" onclick="openAddConnectionModal()" style="display: none;">🔌 <span>+Conexão</span></button>
        <button id="resetDefaultsBtn" class="btn btn-warning" onclick="resetToDefaultConfig()" style="display: none;">🔄 <span>Padrões</span></button>
        <button class="btn btn-info" onclick="toggleGrid()">🔲 <span>Grade</span></button>
        <button class="btn btn-info" onclick="openBackgroundModal()">🖼️ <span>Planta</span></button>
        <button id="adminDevBtn" class="btn btn-warning" onclick="openDevImageModal()" style="background:#e83e8c; color:white; display: none;">🖼️ <span>Dev</span></button>
        <button id="adminBgBtn" class="btn btn-secondary" onclick="openLoginBgConfig()" style="background:#6f42c1; color:white; display: none;">🎬 <span>Fundo Login</span></button>
        <button class="btn btn-success" onclick="window.open('https://th-tech.souzathiagosantos03.workers.dev', '_blank')" style="background:#fd7e14; color:white; font-weight:bold;">🌐 <span>TH-TEC</span></button>
        <button class="btn btn-danger" onclick="logout()">🚪 <span>Sair</span></button>
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
            <div id="props-content">
                <p style="color:var(--text-secondary);">Clique em um componente ou forma</p>
            </div>
        </div>
    </div>
    <div id="deleteShapeBtn" class="delete-shape-btn" onclick="deleteSelectedShape()">🗑 Excluir Forma</div>
    
    <div class="mobile-nav" id="mobileNav">
        <button class="mobile-nav-btn active" onclick="mobileTab('canvas', this)">
            <span class="nav-icon">🎨</span><span class="nav-label">Projeto</span>
        </button>
        <button class="mobile-nav-btn" onclick="mobileTab('palette', this)">
            <span class="nav-icon">📦</span><span class="nav-label">Equipamentos</span>
        </button>
        <button class="mobile-nav-btn" onclick="mobileTab('properties', this)">
            <span class="nav-icon">📋</span><span class="nav-label">Propriedades</span>
        </button>
        <button class="mobile-nav-btn" onclick="mobileTab('tools', this)">
            <span class="nav-icon">🛠️</span><span class="nav-label">Ferramentas</span>
        </button>
    </div>
    
    <div class="mobile-fab-container">
        <button class="mobile-fab" onclick="zoomIn()">🔍</button>
        <button class="mobile-fab" onclick="zoomOut()">🔎</button>
        <button class="mobile-fab" onclick="openBackgroundModal()">🖼️</button>
    </div>
    
    <script>
        // ==================== DETECÇÃO MOBILE ====================
        function isMobileDevice() {
            return (window.innerWidth <= 1024) || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || (navigator.maxTouchPoints > 0 && window.innerWidth <= 1366);
        }
        let isMobile = isMobileDevice();
        if (isMobile) document.body.classList.add('mobile-mode');
        window.addEventListener('resize', () => {
            const newIsMobile = isMobileDevice();
            if (newIsMobile !== isMobile) {
                isMobile = newIsMobile;
                if (isMobile) document.body.classList.add('mobile-mode');
                else document.body.classList.remove('mobile-mode');
            }
        });
        
        // ==================== SISTEMA DE FUNDO DO LOGIN ====================
        let currentLoginBgConfig = { type: 'gradient', url: '', opacity: 0.6 };
        let selectedLoginBgFile = null;
        let selectedLoginBgType = null;
        
        async function loadLoginBgConfig() {
            try {
                const response = await fetch('/api/login_bg_config');
                const data = await response.json();
                if (data.success) {
                    currentLoginBgConfig = data.config;
                    applyLoginBgToScreen(currentLoginBgConfig);
                }
            } catch(e) { console.error('Erro ao carregar config do fundo:', e); }
        }
        
        function applyLoginBgToScreen(config) {
            const video = document.getElementById('loginBgVideo');
            const gif = document.getElementById('loginBgGif');
            const overlay = document.getElementById('loginBgOverlay');
            
            if (!config.url) {
                video.style.display = 'none';
                gif.style.display = 'none';
                overlay.style.background = 'linear-gradient(135deg, rgba(0,26,46,0.85), rgba(0,38,77,0.85))';
                return;
            }
            
            const opacity = config.opacity || 0.6;
            
            if (config.type === 'video') {
                gif.style.display = 'none';
                video.src = config.url;
                video.style.display = 'block';
                video.style.opacity = opacity;
                video.load();
                video.play().catch(() => {});
                overlay.style.background = 'transparent';
            } else {
                video.style.display = 'none';
                gif.src = config.url;
                gif.style.display = 'block';
                gif.style.opacity = opacity;
                overlay.style.background = 'transparent';
            }
        }
        
        function openLoginBgConfig() {
            const modal = document.getElementById('bgConfigModal');
            modal.classList.add('active');
            
            selectedLoginBgFile = null;
            selectedLoginBgType = null;
            document.getElementById('loginBgFileInput').value = '';
            const preview = document.getElementById('loginBgPreview');
            preview.innerHTML = '<div class="empty-preview">Nenhum arquivo selecionado</div>';
            document.getElementById('loginBgOpacityRange').value = currentLoginBgConfig.opacity || 0.6;
            document.getElementById('loginBgOpacityValue').textContent = Math.round((currentLoginBgConfig.opacity || 0.6) * 100) + '%';
            
            if (currentLoginBgConfig.url) {
                if (currentLoginBgConfig.type === 'video') {
                    preview.innerHTML = `<video src="${currentLoginBgConfig.url}" autoplay loop muted playsinline style="max-width:100%; max-height:100%;"></video>`;
                } else {
                    preview.innerHTML = `<img src="${currentLoginBgConfig.url}" style="max-width:100%; max-height:100%;">`;
                }
            }
        }
        
        function closeLoginBgConfig() {
            document.getElementById('bgConfigModal').classList.remove('active');
        }
        
        function resetLoginBg() {
            if (!confirm('Remover o fundo personalizado e voltar ao padrão?')) return;
            fetch('/api/reset_login_bg', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        currentLoginBgConfig = { type: 'gradient', url: '', opacity: 0.6 };
                        applyLoginBgToScreen(currentLoginBgConfig);
                        closeLoginBgConfig();
                        showToast('✅ Fundo restaurado ao padrão');
                    }
                });
        }
        
        async function applyLoginBg() {
            const opacity = parseFloat(document.getElementById('loginBgOpacityRange').value);
            
            if (!selectedLoginBgFile && currentLoginBgConfig.url) {
                try {
                    const response = await fetch('/api/save_login_bg_config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ opacity: opacity })
                    });
                    const data = await response.json();
                    if (data.success) {
                        currentLoginBgConfig = data.config;
                        applyLoginBgToScreen(currentLoginBgConfig);
                        showToast('✅ Opacidade atualizada!');
                        closeLoginBgConfig();
                    }
                } catch(e) { showToast('❌ Erro ao salvar'); }
                return;
            }
            
            if (!selectedLoginBgFile) {
                showToast('⚠️ Selecione um arquivo primeiro');
                return;
            }
            
            showToast('📤 Enviando arquivo...');
            
            try {
                let fileData, fileType, ext;
                const file = selectedLoginBgFile;
                
                if (file.type.startsWith('video/')) {
                    fileType = 'video';
                    ext = '.' + file.name.split('.').pop();
                    fileData = await new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onload = (e) => resolve(e.target.result.split(',')[1]);
                        reader.onerror = reject;
                        reader.readAsDataURL(file);
                    });
                } else {
                    fileType = 'image';
                    fileData = await new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onload = (e) => resolve(e.target.result);
                        reader.onerror = reject;
                        reader.readAsDataURL(file);
                    });
                }
                
                const response = await fetch('/api/upload_login_bg', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type: fileType, data: fileData, ext: ext || '.mp4' })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    await fetch('/api/save_login_bg_config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ opacity: opacity, type: fileType, url: data.url })
                    });
                    
                    currentLoginBgConfig = { type: fileType, url: data.url, opacity: opacity };
                    applyLoginBgToScreen(currentLoginBgConfig);
                    showToast('✅ Fundo aplicado com sucesso!');
                    closeLoginBgConfig();
                } else {
                    showToast('❌ Erro: ' + (data.error || 'Erro desconhecido'));
                }
            } catch(e) {
                console.error(e);
                showToast('❌ Erro ao enviar arquivo');
            }
        }
        
        // ==================== MOBILE TABS ====================
        function mobileTab(tab, btn) {
            document.querySelectorAll('.mobile-nav-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            const palette = document.getElementById('palette');
            const properties = document.getElementById('propertiesPanel');
            const overlay = document.getElementById('mobileOverlay');
            palette.classList.remove('mobile-open');
            properties.classList.remove('open');
            overlay.classList.remove('active');
            
            if (tab === 'palette') {
                palette.classList.add('mobile-open');
                overlay.classList.add('active');
            } else if (tab === 'properties') {
                if (document.getElementById('props-content').innerHTML.includes('Clique em')) {
                    showToast('👆 Toque em um equipamento primeiro');
                    document.querySelectorAll('.mobile-nav-btn')[0].classList.add('active');
                    if (btn) btn.classList.remove('active');
                    return;
                }
                properties.classList.add('open');
                overlay.classList.add('active');
            } else if (tab === 'tools') {
                showMobileToolsMenu();
                document.querySelectorAll('.mobile-nav-btn')[0].classList.add('active');
                if (btn) btn.classList.remove('active');
            }
        }
        
        function closeMobilePanels() {
            document.getElementById('palette').classList.remove('mobile-open');
            document.getElementById('propertiesPanel').classList.remove('open');
            document.getElementById('mobileOverlay').classList.remove('active');
            document.querySelectorAll('.mobile-nav-btn').forEach((b, i) => b.classList.toggle('active', i === 0));
        }
        
        function showMobileToolsMenu() {
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content" style="max-height: 80vh;">
                    <h3 style="color:var(--text-accent); margin-bottom:15px;">🛠️ Ferramentas</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;">
                        <button class="btn btn-primary" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="newProject(); closeModal();">📁<br>Novo</button>
                        <button class="btn btn-secondary" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="saveProjectToFile(); closeModal();">💾<br>Salvar</button>
                        <button class="btn btn-secondary" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="loadProjectFromFile(); closeModal();">📂<br>Carregar</button>
                        <button class="btn btn-primary" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="exportPDFWithList(); closeModal();">📄<br>PDF Lista</button>
                        <button class="btn btn-primary" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="exportPDF(); closeModal();">🖼️<br>Mapa</button>
                        <button class="btn btn-warning" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="generateBudget(); closeModal();">💰<br>Orçamento</button>
                        <button class="btn btn-info" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="toggleGrid(); closeModal();">🔲<br>Grade</button>
                        <button class="btn btn-info" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="openBackgroundModal(); closeModal();">🖼️<br>Planta</button>
                        <button class="btn btn-info" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="toggleShapesToolbar(); closeModal();">📐<br>Formas</button>
                        <button class="btn btn-danger" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="deleteSelectedItems(); closeModal();">🗑<br>Excluir</button>
                        <button class="btn btn-info" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="openUserManagement(); closeModal();">👥<br>Usuários</button>
                        <button class="btn btn-secondary" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px; background:#6f42c1; color:white;" onclick="openLoginBgConfig(); closeModal();">🎬<br>Fundo Login</button>
                        <button class="btn btn-success" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px; background:#fd7e14;" onclick="window.open('https://th-tech.souzathiagosantos03.workers.dev', '_blank');">🌐<br>TH-TEC</button>
                        <button class="btn btn-danger" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="logout();">🚪<br>Sair</button>
                        <button class="btn btn-info" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="openAddCategoryModal(); closeModal();">📁<br>+Cat</button>
                        <button class="btn btn-info" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="openAddDeviceModal(); closeModal();">🔧<br>+Equip</button>
                        <button class="btn btn-info" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="openAddConnectionModal(); closeModal();">🔌<br>+Conexão</button>
                        <button class="btn btn-warning" style="padding:12px 6px; flex-direction: column; height: 75px; font-size: 10px;" onclick="openDevImageModal(); closeModal();">🖼️<br>Dev</button>
                    </div>
                    <div class="modal-buttons" style="margin-top:15px;">
                        <button class="btn btn-secondary" style="width:100%; padding:12px;" onclick="closeModal()">Fechar</button>
                    </div>
                </div>`;
            document.body.appendChild(modal);
            window.currentModal = modal;
        }
        
        // ==================== ESTADO GLOBAL ====================
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
        let contextMenuComponent = null;
        let contextMenuShape = null;
        
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
            'cat5': { color: '#28a745', name: 'CAT5', icon: '🟢', type: 'cable', speed: '100 Mbps' },
            'cat5e': { color: '#17a2b8', name: 'CAT5e', icon: '🔵', type: 'cable', speed: '1 Gbps' },
            'cat6': { color: '#ffc107', name: 'CAT6', icon: '🟡', type: 'cable', speed: '10 Gbps' },
            'fiber': { color: '#20c997', name: 'FIBRA', icon: '🔷', type: 'cable', speed: '10 Gbps' },
            'coaxial': { color: '#e83e8c', name: 'COAXIAL', icon: '🟣', type: 'cable', speed: '1 Gbps' },
            'alarme': { color: '#dc3545', name: 'ALARME', icon: '🔴', type: 'cable', speed: 'Baixa' },
            'ci': { color: '#6f42c1', name: 'CABO CI', icon: '🟣', type: 'cable', speed: 'Média' },
            'energia': { color: '#fd7e14', name: 'ENERGIA', icon: '🔴', type: 'cable', speed: '-' },
            'wifi': { color: '#00aaff', name: 'Wi-Fi', icon: '📶', type: 'wireless', speed: '1 Gbps', animation: 'wave' },
            'ook': { color: '#ff6600', name: 'OOK', icon: '📻', type: 'wireless', speed: '100 Kbps', animation: 'packet' },
            'fsk': { color: '#aa44ff', name: 'FSK', icon: '📡', type: 'wireless', speed: '1 Mbps', animation: 'packet' },
            'amt8000': { color: '#ff44aa', name: 'AMT 8000', icon: '🔊', type: 'wireless', speed: '8000 bps', animation: 'wave' },
            'bluetooth': { color: '#0066cc', name: 'Bluetooth', icon: '📱', type: 'wireless', speed: '24 Mbps', animation: 'wave' },
            'zigbee': { color: '#00aa66', name: 'ZigBee', icon: '🔵', type: 'wireless', speed: '250 Kbps', animation: 'packet' },
            'lora': { color: '#cc8800', name: 'LoRa', icon: '📡', type: 'wireless', speed: '50 Kbps', animation: 'packet' }
        };
        
        let cableColors = JSON.parse(JSON.stringify(defaultCableColors));
        let connectionCategories = {};
        
        const STORAGE_KEYS = {
            ICON_SIZE: 'projetize_icon_size',
            CANVAS_ZOOM: 'projetize_canvas_zoom',
            COMPONENTS: (user) => `projetize_${user}_components`,
            CONNECTIONS_DATA: (user) => `projetize_${user}_connections`,
            SHAPES: (user) => `projetize_${user}_shapes`,
            BACKGROUND: (user) => `projetize_${user}_background`
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
                }
            }, 300);
        }

        async function loadUserData() {
            const savedIconSize = localStorage.getItem(STORAGE_KEYS.ICON_SIZE);
            if(savedIconSize) iconSize = parseInt(savedIconSize);
            const savedZoom = localStorage.getItem(STORAGE_KEYS.CANVAS_ZOOM);
            if(savedZoom) zoom = parseFloat(savedZoom);
            
            categories = JSON.parse(JSON.stringify(defaultCategories));
            
            const promises = [fetch('/api/load_custom_devices').then(r => r.json()).catch(() => ({success: false}))];
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
                    backgroundX = bgData.x || 0;
                    backgroundY = bgData.y || 0;
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
            } catch(e) { console.error(e); }
        }
        
        function getConnectionKey(name) { return name.toLowerCase().replace(/[^a-z0-9]/g, ''); }
        function renderConnectionIcon(conn) { if (conn.iconFile) { return `<img src="/uploads/icons/${conn.iconFile}" style="width:24px;height:24px;object-fit:contain;">`; } return conn.icon || '🔌'; }
        function renderDeviceIcon(device) { if(device.iconFile) return `<img src="/uploads/icons/${device.iconFile}" style="width:24px;height:24px;object-fit:contain;">`; return device.icon || '📦'; }
        
        function renderPalette() {
            const container = document.getElementById('categories-container'); if(!container) return; container.innerHTML = '';
            for(const [catName, catData] of Object.entries(categories)) {
                const categoryDiv = document.createElement('div'); categoryDiv.className = 'category';
                const catIcon = catData.iconFile ? `<img src="/uploads/icons/${catData.iconFile}" style="width:16px;height:16px;">` : (catData.icon || '📁');
                categoryDiv.innerHTML = `<div class="category-header"><h3>${catIcon} ${catName}</h3>${(userRole === 'admin' || userRole === 'master') ? `<div class="category-actions"><button onclick="editCategory('${catName.replace(/'/g, "\\'")}')">✏️</button><button onclick="openCategoryIconModal('${catName.replace(/'/g, "\\'")}')">🎨</button><button onclick="deleteCategory('${catName.replace(/'/g, "\\'")}')">🗑</button><button onclick="addDeviceToCategory('${catName.replace(/'/g, "\\'")}')">➕</button></div>` : ''}</div><div id="category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>`;
                container.appendChild(categoryDiv);
                const devicesContainer = document.getElementById(`category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
                if (catData.devices) {
                    catData.devices.forEach((device, idx) => {
                        const deviceEl = document.createElement('div'); deviceEl.className = 'component'; deviceEl.setAttribute('draggable', 'true');
                        deviceEl.innerHTML = `<div class="component-icon">${renderDeviceIcon(device)}</div><div class="component-info"><div class="component-name">${device.name}</div><div class="component-desc">${device.desc || ''}</div></div>${(userRole === 'admin' || userRole === 'master') ? `<div class="component-actions"><button onclick="event.stopPropagation(); editDevice('${catName.replace(/'/g, "\\'")}', ${idx})">✏️</button><button onclick="event.stopPropagation(); openDeviceIconModal('${catName.replace(/'/g, "\\'")}', ${idx})">🎨</button><button onclick="event.stopPropagation(); deleteDevice('${catName.replace(/'/g, "\\'")}', ${idx})">🗑</button></div>` : ''}`;
                        deviceEl.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/plain', JSON.stringify({ name: device.name, icon: device.icon, type: device.type, subtype: device.subtype || '', color: device.color, iconFile: device.iconFile || null })); });
                        deviceEl.addEventListener('click', (e) => {
                            if (e.target.tagName === 'BUTTON') return;
                            if (isMobile) { e.preventDefault(); e.stopPropagation(); addDeviceToCanvas(device, catName); }
                        });
                        devicesContainer.appendChild(deviceEl);
                    });
                }
            }
        }
        
        function addDeviceToCanvas(device, catName) {
            const canvasArea = document.getElementById('canvasArea');
            const scrollLeft = canvasArea.scrollLeft;
            const scrollTop = canvasArea.scrollTop;
            const viewWidth = canvasArea.clientWidth;
            const viewHeight = canvasArea.clientHeight;
            const centerX = (scrollLeft + viewWidth/2) / zoom + (Math.random() - 0.5) * 80;
            const centerY = (scrollTop + viewHeight/2) / zoom + (Math.random() - 0.5) * 80;
            const newComp = { id: Date.now() + Math.floor(Math.random()*1000), type: device.type || 'custom', subtype: device.subtype || '', name: device.name, x: centerX, y: centerY, icon: device.icon || '📦', iconFile: device.iconFile || null, color: device.color || '#005f99', angle: 0, fov: 80, rotation: 0, ip: '', port: 80 };
            components.push(newComp);
            showToast(`✅ ${device.name} adicionado!`);
            saveUserData();
            if (isMobile) closeMobilePanels();
        }
        
        function renderConnectionsPalette() {
            const container = document.getElementById('connections-container'); if (!container) return; container.innerHTML = '';
            for (const [catName, catData] of Object.entries(connectionCategories)) {
                if (!catData.connections || catData.connections.length === 0) continue;
                const categoryDiv = document.createElement('div'); categoryDiv.className = 'category';
                categoryDiv.innerHTML = `<div class="category-header"><h3>${catData.icon || '🔌'} ${catName}</h3></div><div id="conn-cat-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>`;
                container.appendChild(categoryDiv);
                const connContainer = document.getElementById(`conn-cat-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
                catData.connections.forEach((conn, idx) => {
                    const connEl = document.createElement('div'); connEl.className = 'component';
                    connEl.innerHTML = `<div class="component-icon">${renderConnectionIcon(conn)}</div><div class="component-info"><div class="component-name">${conn.name}</div><div class="component-desc">${conn.desc || conn.speed || ''}</div></div>`;
                    connContainer.appendChild(connEl);
                });
            }
        }
        
        function applyZoomToCanvas() { canvas.style.transform = `scale(${zoom})`; canvas.style.transformOrigin = '0 0'; }
        function iconZoomIn() { iconSize = Math.min(iconSize + 4, 80); saveUserData(); showToast(`🔍 Ícone: ${iconSize}px`); }
        function iconZoomOut() { iconSize = Math.max(iconSize - 4, 20); saveUserData(); showToast(`🔍 Ícone: ${iconSize}px`); }
        function resetIconSize() { iconSize = 36; saveUserData(); showToast(`🔄 Ícone: 36px`); }
        function zoomIn() { zoom = Math.min(zoom + 0.1, 3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
        function zoomOut() { zoom = Math.max(zoom - 0.1, 0.3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
        function resetZoom() { zoom = 1; applyZoomToCanvas(); saveUserData(); showToast(`🔄 Zoom: 100%`); }
        
        function showToast(message) { const toast = document.createElement('div'); toast.className = 'toast'; toast.textContent = message; document.body.appendChild(toast); setTimeout(() => toast.remove(), 3000); }
        function closeModal() { if(window.currentModal) { document.body.removeChild(window.currentModal); window.currentModal = null; } }
        
        function drawGrid() {
            if(!showGrid) return;
            const step = 50; ctx.save(); ctx.strokeStyle = '#e0e0e0'; ctx.lineWidth = 0.5;
            for(let x=0; x<canvas.width; x+=step) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,canvas.height); ctx.stroke(); }
            for(let y=0; y<canvas.height; y+=step) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(canvas.width,y); ctx.stroke(); }
            ctx.restore();
        }
        
        function drawBackground() {
            if(backgroundImageObj && backgroundImageObj.complete && backgroundImageObj.src && backgroundWidth > 0) {
                ctx.save(); ctx.globalAlpha = backgroundOpacity; ctx.drawImage(backgroundImageObj, backgroundX, backgroundY, backgroundWidth, backgroundHeight); ctx.globalAlpha = 1;
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
            ctx.restore();
        }
        
        function drawSensorAnimation(x, y, time) {
            for(let i = 0; i < 3; i++) {
                const delay = i * 0.5; const progress = (time + delay) % 1; const radius = 25 + (progress * 30); const opacity = 0.5 * (1 - progress);
                ctx.save(); ctx.beginPath(); ctx.arc(x, y, radius, 0, 2 * Math.PI); ctx.strokeStyle = `rgba(0, 95, 153, ${opacity})`; ctx.lineWidth = 2; ctx.stroke(); ctx.restore();
            }
        }
        
        function drawConnections() {
            connections.forEach((conn, idx) => {
                const fromComp = components.find(c => c.id === conn.from); const toComp = components.find(c => c.id === conn.to);
                if(!fromComp || !toComp) return;
                const cableInfo = cableColors[conn.type] || cableColors['cat6']; if (!cableInfo) return;
                const isWireless = cableInfo.type === 'wireless'; const isSelected = (selectedConnectionIndex === idx);
                ctx.save();
                if(isWireless) { ctx.setLineDash([10, 8]); } else { ctx.setLineDash([]); }
                ctx.strokeStyle = cableInfo.color; ctx.lineWidth = isSelected ? 4 : 2;
                ctx.beginPath(); ctx.moveTo(fromComp.x, fromComp.y); ctx.lineTo(toComp.x, toComp.y); ctx.stroke();
                ctx.setLineDash([]);
                ctx.fillStyle = '#6c757d'; ctx.font = `${9}px Arial`; ctx.textAlign = 'center';
                ctx.fillText(`${cableInfo.icon} ${cableInfo.name}`, (fromComp.x+toComp.x)/2, (fromComp.y+toComp.y)/2 - 5);
                ctx.textAlign = 'start';
                ctx.restore();
            });
        }
        
        function drawShapes() {
            shapes.forEach(shape => {
                const isSelected = selectedShapes.includes(shape);
                ctx.save(); ctx.strokeStyle = shape.strokeColor || '#005f99'; ctx.fillStyle = shape.fillColor || 'rgba(0,0,0,0.05)'; ctx.lineWidth = shape.lineWidth || 2;
                if(shape.rotation) { 
                    const cx = shape.type === 'line' ? (shape.x1+shape.x2)/2 : shape.x + (shape.type === 'door' ? 15 : 30);
                    const cy = shape.type === 'line' ? (shape.y1+shape.y2)/2 : shape.y + (shape.type === 'door' ? 25 : 20);
                    ctx.translate(cx, cy); ctx.rotate(shape.rotation * Math.PI / 180); ctx.translate(-cx, -cy); 
                }
                switch(shape.type) {
                    case 'line': ctx.beginPath(); ctx.moveTo(shape.x1, shape.y1); ctx.lineTo(shape.x2, shape.y2); ctx.stroke(); break;
                    case 'door': ctx.fillStyle = 'rgba(139, 69, 19, 0.3)'; ctx.fillRect(shape.x, shape.y, 30, 50); ctx.strokeStyle = '#8B4513'; ctx.strokeRect(shape.x, shape.y, 30, 50); ctx.beginPath(); ctx.arc(shape.x + 30, shape.y + 25, 20, -Math.PI/2, Math.PI/2); ctx.stroke(); break;
                    case 'window': ctx.fillStyle = 'rgba(135, 206, 235, 0.3)'; ctx.fillRect(shape.x, shape.y, 60, 40); ctx.strokeStyle = '#87CEEB'; ctx.strokeRect(shape.x, shape.y, 60, 40); ctx.beginPath(); ctx.moveTo(shape.x + 30, shape.y); ctx.lineTo(shape.x + 30, shape.y + 40); ctx.moveTo(shape.x, shape.y + 20); ctx.lineTo(shape.x + 60, shape.y + 20); ctx.stroke(); break;
                    case 'text': ctx.font = `${(shape.fontSize || 14)}px Arial`; ctx.fillStyle = shape.textColor || '#212529'; ctx.fillText(shape.text || 'Texto', shape.x, shape.y); break;
                }
                ctx.setTransform(1, 0, 0, 1, 0, 0);
                if(isSelected) {
                    ctx.strokeStyle = '#005f99'; ctx.lineWidth = 2;
                    if(shape.type === 'line') { ctx.strokeRect(Math.min(shape.x1, shape.x2)-5, Math.min(shape.y1, shape.y2)-5, Math.abs(shape.x2-shape.x1)+10, Math.abs(shape.y2-shape.y1)+10); }
                    else if(shape.type === 'text') { ctx.strokeRect(shape.x - 5, shape.y - 12, ctx.measureText(shape.text || 'Texto').width + 10, 18); }
                    else { const w = shape.type === 'door' ? 30 : 60; const h = shape.type === 'door' ? 50 : 40; ctx.strokeRect(shape.x - 3, shape.y - 3, w + 6, h + 6); }
                }
                ctx.restore();
            });
        }
        
        function drawComponents() {
            components.forEach(comp => {
                const isSelected = selectedComponents.includes(comp);
                if(comp.type === 'sensor') drawSensorAnimation(comp.x, comp.y, sensorAnimationTime);
                ctx.save(); 
                if (comp.rotation) { ctx.translate(comp.x, comp.y); ctx.rotate((comp.rotation || 0) * Math.PI / 180); ctx.translate(-comp.x, -comp.y); }
                const halfSize = iconSize / 2;
                if(comp.iconFile) {
                    ctx.drawImage(getCachedImage(`/uploads/icons/${comp.iconFile}`), comp.x-halfSize, comp.y-halfSize, iconSize, iconSize);
                } else {
                    ctx.fillStyle = comp.color || '#005f99'; ctx.beginPath(); ctx.arc(comp.x, comp.y, iconSize/2, 0, 2*Math.PI); ctx.fill(); ctx.fillStyle = '#fff'; ctx.font = `${iconSize/2}px Arial`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(comp.icon || '📦', comp.x, comp.y); ctx.textAlign = 'start'; ctx.textBaseline = 'alphabetic';
                }
                ctx.setTransform(1, 0, 0, 1, 0, 0); 
                ctx.fillStyle = '#005f99'; ctx.font = `${12}px Arial`; ctx.textAlign = 'center'; ctx.fillText(comp.name, comp.x, comp.y - (iconSize/2) - 8);
                ctx.textAlign = 'start';
                if(isSelected) { ctx.strokeStyle = '#005f99'; ctx.lineWidth = 2; ctx.strokeRect(comp.x - halfSize - 4, comp.y - halfSize - 4, iconSize + 8, iconSize + 8); }
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
        
        let lastMousePos = null;
        function getMousePos(e) {
            const rect = canvas.getBoundingClientRect(); 
            const scaleX = canvas.width / rect.width; 
            const scaleY = canvas.height / rect.height;
            let clientX, clientY;
            if (e.touches && e.touches.length > 0) { clientX = e.touches[0].clientX; clientY = e.touches[0].clientY; }
            else if (e.changedTouches && e.changedTouches.length > 0) { clientX = e.changedTouches[0].clientX; clientY = e.changedTouches[0].clientY; }
            else { clientX = e.clientX; clientY = e.clientY; }
            return { x: (clientX - rect.left) * scaleX, y: (clientY - rect.top) * scaleY };
        }
        
        function accessDevice(comp) { 
            if(comp && comp.ip && comp.ip.trim()) { 
                let url = comp.ip; 
                if(!url.startsWith('http://') && !url.startsWith('https://')) url = 'http://' + url; 
                if(comp.port && comp.port !== 80) url += ':' + comp.port; 
                window.open(url, '_blank'); 
            } else if(comp) { showToast(`⚠️ "${comp.name}" sem IP`); } 
        }
        
        function endShape(start, end, type) {
            if(!start || !end) return;
            if (type === 'line') {
                const dist = Math.hypot(end.x - start.x, end.y - start.y);
                if (dist < 5) { showToast('⚠️ Linha muito curta'); return; }
            }
            const newShape = { id: Date.now(), type: type, fillColor: '#f8f9fa', strokeColor: '#005f99', lineWidth: 2, rotation: 0 };
            switch(type) {
                case 'line': newShape.x1 = start.x; newShape.y1 = start.y; newShape.x2 = end.x; newShape.y2 = end.y; break;
                case 'door': newShape.x = end.x; newShape.y = end.y; break;
                case 'window': 
                    newShape.x = Math.min(start.x, end.x); 
                    newShape.y = Math.min(start.y, end.y); 
                    newShape.width = Math.abs(end.x - start.x); 
                    newShape.height = 40; 
                    if (newShape.width < 20) { showToast('⚠️ Janela muito pequena'); return; }
                    break;
                case 'text': 
                    const text = prompt('Digite o texto:', 'Texto'); 
                    if(text) { newShape.text = text; newShape.x = end.x; newShape.y = end.y; newShape.fontSize = 14; newShape.textColor = '#212529'; } 
                    else return; 
                    break;
            }
            shapes.push(newShape); 
            showToast(`✅ ${getShapeName(type)} criada!`); 
            saveUserData();
        }
        
        function getShapeName(mode) { const names = { line: 'Linha', door: 'Porta', window: 'Janela', text: 'Texto' }; return names[mode] || mode; }
        
        function pointToLineDistance(px, py, x1, y1, x2, y2) {
            const A = px - x1; const B = py - y1; const C = x2 - x1; const D = y2 - y1; 
            const dot = A * C + B * D; const len_sq = C * C + D * D; let param = -1; 
            if (len_sq != 0) param = dot / len_sq;
            let xx, yy; 
            if (param < 0) { xx = x1; yy = y1; } else if (param > 1) { xx = x2; yy = y2; } else { xx = x1 + param * C; yy = y1 + param * D; }
            const dx = px - xx; const dy = py - yy; return Math.sqrt(dx * dx + dy * dy);
        }
        
        function isPointNearConnection(x, y, fromComp, toComp) { 
            const tolerance = isMobile ? 20 : 12;
            return pointToLineDistance(x, y, fromComp.x, fromComp.y, toComp.x, toComp.y) < tolerance; 
        }
        
        function isPointOnShape(x, y, shape) {
            const tolerance = isMobile ? 15 : 8;
            if(shape.type === 'line') { return pointToLineDistance(x, y, shape.x1, shape.y1, shape.x2, shape.y2) < tolerance; }
            else if(shape.type === 'text') { return x >= shape.x - 5 && x <= shape.x + (shape.text?.length * 7 || 50) && y >= shape.y - 12 && y <= shape.y + 6; }
            else if(shape.type === 'door') { return x >= shape.x && x <= shape.x + 30 && y >= shape.y && y <= shape.y + 50; }
            else if(shape.type === 'window') { return x >= shape.x && x <= shape.x + 60 && y >= shape.y && y <= shape.y + 40; }
            return false;
        }
        
        let longPressTimer = null;
        let touchStartPos = null;
        let touchMoved = false;
        let pinchStartDist = 0;
        let pinchStartZoom = 1;
        
        function handleStart(e) {
            const touch = e.touches ? e.touches[0] : e;
            if (!touch) return;
            const pos = getMousePos(e);
            lastMousePos = pos;
            touchMoved = false;
            touchStartPos = pos;
            
            if (e.touches) {
                clearTimeout(longPressTimer);
                longPressTimer = setTimeout(() => {
                    if (!touchMoved) {
                        for(let comp of components) { 
                            if(Math.hypot(pos.x - comp.x, pos.y - comp.y) < iconSize/2) { 
                                showContextMenu({preventDefault:()=>{}, pageX: touch.clientX, pageY: touch.clientY}, comp); 
                                return; 
                            } 
                        }
                        for(let shape of shapes) { 
                            if(isPointOnShape(pos.x, pos.y, shape)) { 
                                showShapeContextMenu({preventDefault:()=>{}, pageX: touch.clientX, pageY: touch.clientY}, shape); 
                                return; 
                            } 
                        }
                    }
                }, 700);
            }
            
            if(shapeMode) { shapeStart = {x: pos.x, y: pos.y}; drawingPreview = true; if (e.cancelable) e.preventDefault(); return; }
            
            let clickedComp = null;
            for(let i=components.length-1; i>=0; i--) { 
                const comp = components[i]; 
                if(Math.hypot(pos.x - comp.x, pos.y - comp.y) < iconSize/2) { clickedComp = comp; break; } 
            }
            
            if(clickedComp) {
                if(e.ctrlKey || e.metaKey) { 
                    if(selectedComponents.includes(clickedComp)) selectedComponents = selectedComponents.filter(c => c !== clickedComp); 
                    else selectedComponents.push(clickedComp); 
                } else { 
                    selectedComponents = [clickedComp]; 
                    dragging = true; 
                    dragOffset = {x: clickedComp.x - pos.x, y: clickedComp.y - pos.y}; 
                    selectedShapes = []; 
                    selectedConnectionIndex = null; 
                }
                showProperties(clickedComp); 
                openProperties(); 
                if (e.cancelable) e.preventDefault(); 
                return;
            }
            
            let clickedShape = null;
            for(let i=shapes.length-1; i>=0; i--) { 
                const shape = shapes[i]; 
                if(isPointOnShape(pos.x, pos.y, shape)) { clickedShape = shape; break; } 
            }
            if(clickedShape) {
                selectedShapes = [clickedShape]; 
                dragging = true; 
                if(clickedShape.type === 'line') dragOffset = {x: clickedShape.x1 - pos.x, y: clickedShape.y1 - pos.y};
                else dragOffset = {x: clickedShape.x - pos.x, y: clickedShape.y - pos.y};
                selectedComponents = []; 
                selectedConnectionIndex = null;
                showShapeProperties(clickedShape); 
                openProperties(); 
                if (e.cancelable) e.preventDefault(); 
                return;
            }
            
            for(let i = 0; i < connections.length; i++) { 
                const conn = connections[i]; 
                const fromComp = components.find(c => c.id === conn.from); 
                const toComp = components.find(c => c.id === conn.to); 
                if(fromComp && toComp && isPointNearConnection(pos.x, pos.y, fromComp, toComp)) { 
                    selectedConnectionIndex = i; 
                    selectedComponents = []; 
                    selectedShapes = []; 
                    showConnectionProperties(i);
                    openProperties();
                    if (e.cancelable) e.preventDefault();
                    return; 
                } 
            }
            
            if(backgroundWidth > 0 && backgroundHeight > 0) {
                if(pos.x >= backgroundX && pos.x <= backgroundX + backgroundWidth && pos.y >= backgroundY && pos.y <= backgroundY + backgroundHeight) {
                    isBackgroundSelected = true; 
                    isDraggingBackgroundImage = true; 
                    dragBackgroundStart = { x: touch.clientX - backgroundX, y: touch.clientY - backgroundY };
                    if (e.cancelable) e.preventDefault(); 
                    return;
                }
            }
            
            selectedComponents = []; 
            selectedShapes = []; 
            selectedConnectionIndex = null; 
            dragging = false; 
            showProperties(null);
        }
        
        function handleMove(e) {
            if (e.cancelable) e.preventDefault();
            
            if (e.touches && e.touches.length === 2) {
                clearTimeout(longPressTimer);
                const dx = e.touches[0].clientX - e.touches[1].clientX;
                const dy = e.touches[0].clientY - e.touches[1].clientY;
                const dist = Math.sqrt(dx*dx + dy*dy);
                if (pinchStartDist === 0) { pinchStartDist = dist; pinchStartZoom = zoom; }
                else { zoom = Math.min(Math.max(pinchStartZoom * (dist / pinchStartDist), 0.3), 3); applyZoomToCanvas(); }
                return;
            }
            
            const touch = e.touches ? e.touches[0] : e;
            if (!touch) return;
            const pos = getMousePos(e);
            
            if (touchStartPos && Math.hypot(pos.x - touchStartPos.x, pos.y - touchStartPos.y) > 10) {
                touchMoved = true;
                clearTimeout(longPressTimer);
            }
            
            lastMousePos = pos;
            
            if(isDraggingBackgroundImage) { 
                backgroundX = touch.clientX - dragBackgroundStart.x; 
                backgroundY = touch.clientY - dragBackgroundStart.y; 
                saveUserData(); 
                return; 
            }
            
            if(dragging && selectedComponents.length > 0) { 
                const dx = (pos.x + dragOffset.x) - selectedComponents[0].x; 
                const dy = (pos.y + dragOffset.y) - selectedComponents[0].y; 
                selectedComponents.forEach(comp => { comp.x += dx; comp.y += dy; }); 
                dragOffset = {x: selectedComponents[0].x - pos.x, y: selectedComponents[0].y - pos.y}; 
                saveUserData(); 
            }
            
            if(dragging && selectedShapes.length > 0) {
                const shape = selectedShapes[0]; 
                if(shape.type === 'line') { 
                    const dx = (pos.x + dragOffset.x) - shape.x1; 
                    const dy = (pos.y + dragOffset.y) - shape.y1; 
                    shape.x1 += dx; shape.y1 += dy; shape.x2 += dx; shape.y2 += dy; 
                    dragOffset = {x: shape.x1 - pos.x, y: shape.y1 - pos.y}; 
                } else { 
                    const dx = (pos.x + dragOffset.x) - shape.x; 
                    const dy = (pos.y + dragOffset.y) - shape.y; 
                    shape.x += dx; shape.y += dy; 
                    dragOffset = {x: shape.x - pos.x, y: shape.y - pos.y}; 
                }
                saveUserData();
            }
        }
        
        function handleEnd(e) {
            clearTimeout(longPressTimer);
            if (touchStartPos && lastMousePos) {
                const dist = Math.hypot(lastMousePos.x - touchStartPos.x, lastMousePos.y - touchStartPos.y);
                if (dist > 15) touchMoved = true;
            }
            pinchStartDist = 0;
            
            if(shapeMode && shapeStart) { 
                let endPos;
                if (e.changedTouches && e.changedTouches.length > 0) {
                    endPos = getMousePos(e);
                } else {
                    endPos = lastMousePos || shapeStart;
                }
                endShape(shapeStart, endPos, shapeMode); 
                shapeStart = null; 
                drawingPreview = false; 
            }
            
            dragging = false; 
            isDraggingBackgroundImage = false;
            touchStartPos = null;
        }
        
        function showProperties(comp) {
            const div = document.getElementById('props-content');
            if(!comp) { 
                div.innerHTML = '<p style="color:#6c757d; padding:20px; text-align:center;">👆 Toque em um equipamento no canvas</p>'; 
                return; 
            }
            div.innerHTML = `
                <div class="property-group"><label>Nome</label><input type="text" id="prop-name" value="${comp.name.replace(/"/g, '&quot;')}"></div>
                <div class="property-group"><label>Tipo</label><input type="text" value="${comp.type || 'custom'}" disabled></div>
                <div class="property-group"><label>Posição X</label><input type="number" id="prop-x" value="${Math.round(comp.x)}"></div>
                <div class="property-group"><label>Posição Y</label><input type="number" id="prop-y" value="${Math.round(comp.y)}"></div>
                <div class="property-group"><label>🔄 Rotação</label><input type="range" id="prop-rotation" min="0" max="360" value="${comp.rotation || 0}"><span id="rotation-val">${Math.round(comp.rotation || 0)}°</span></div>
                <div class="property-group"><label>🌐 Endereço IP</label><input type="text" id="prop-ip" value="${comp.ip || ''}" placeholder="192.168.1.100"></div>
                <div class="property-group"><label>🔌 Porta</label><input type="number" id="prop-port" value="${comp.port || 80}"></div>
                <div class="property-group"><label>👤 Usuário</label><input type="text" id="prop-user" value="${comp.username || ''}" placeholder="admin"></div>
                <div class="property-group"><label>🔑 Senha</label><input type="password" id="prop-pass" value="${comp.password || ''}"></div>
                ${comp.type === 'camera' ? `<div class="property-group"><label>Ângulo</label><input type="range" id="prop-angle" min="0" max="360" value="${comp.angle || 0}"><span id="angle-val">${Math.round(comp.angle || 0)}°</span></div><div class="property-group"><label>Campo Visão</label><input type="range" id="prop-fov" min="20" max="120" value="${comp.fov || 80}"><span id="fov-val">${Math.round(comp.fov || 80)}°</span></div>` : ''}
                <div class="property-group"><label>🖼️ Ícone Personalizado</label><input type="file" id="prop-image" accept="image/*"><div class="image-preview" id="prop-image-preview">${comp.iconFile ? `<img src="/uploads/icons/${comp.iconFile}" style="max-width:50px;max-height:50px;">` : ''}</div></div>
                <div class="property-group" style="background:#e8f4ff; padding:10px; border-radius:8px; border:1px solid #b3d9ff;">
                    <label>🔌 Conectar a</label>
                    <select id="prop-connect"><option value="">-- Selecione --</option>${components.filter(c => c.id !== comp.id).map(c => `<option value="${c.id}">${c.name}</option>`).join('')}</select>
                    <select id="prop-cable-type">${Object.entries(cableColors).map(([key, value]) => `<option value="${key}">${value.icon} ${value.name} - ${value.speed}</option>`).join('')}</select>
                    <button class="btn btn-primary" style="margin-top:8px; width:100%;" onclick="addConnection(${comp.id})">➕ Conectar</button>
                </div>
                <div class="modal-buttons" style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
                    <button class="btn btn-info" onclick="accessDeviceById(${comp.id})">🌐 Acessar</button>
                    <button class="btn btn-warning" onclick="rotateLeft(${comp.id})">🔄 Girar -</button>
                    <button class="btn btn-warning" onclick="rotateRight(${comp.id})">🔄 Girar +</button>
                    <button class="btn btn-secondary" onclick="flipComponentById(${comp.id})">🔁 Inverter</button>
                    <button class="btn btn-secondary" onclick="openPermanentIconModalById(${comp.id})">🎨 Ícone Perm.</button>
                    <button class="btn btn-secondary" onclick="duplicateComponentById(${comp.id})">📋 Duplicar</button>
                    <button class="btn btn-danger" style="grid-column: span 2;" onclick="deleteComponent(${comp.id})">🗑 Remover</button>
                </div>
            `;
            const rotationSlider = document.getElementById('prop-rotation'); 
            if(rotationSlider) { rotationSlider.oninput = (e) => { comp.rotation = parseInt(e.target.value); document.getElementById('rotation-val').innerText = comp.rotation + '°'; saveUserData(); }; }
            if(comp.type === 'camera') { 
                const angleSlider = document.getElementById('prop-angle'); 
                const fovSlider = document.getElementById('prop-fov'); 
                if(angleSlider) { angleSlider.oninput = (e) => { comp.angle = parseInt(e.target.value); document.getElementById('angle-val').innerText = comp.angle + '°'; saveUserData(); }; } 
                if(fovSlider) { fovSlider.oninput = (e) => { comp.fov = parseInt(e.target.value); document.getElementById('fov-val').innerText = comp.fov + '°'; saveUserData(); }; } 
            }
            document.getElementById('prop-name')?.addEventListener('change', (e) => { comp.name = e.target.value; saveUserData(); });
            document.getElementById('prop-x')?.addEventListener('change', (e) => { comp.x = parseInt(e.target.value); saveUserData(); });
            document.getElementById('prop-y')?.addEventListener('change', (e) => { comp.y = parseInt(e.target.value); saveUserData(); });
            document.getElementById('prop-ip')?.addEventListener('change', (e) => { comp.ip = e.target.value; saveUserData(); });
            document.getElementById('prop-port')?.addEventListener('change', (e) => { comp.port = parseInt(e.target.value); saveUserData(); });
            document.getElementById('prop-user')?.addEventListener('change', (e) => { comp.username = e.target.value; saveUserData(); });
            document.getElementById('prop-pass')?.addEventListener('change', (e) => { comp.password = e.target.value; saveUserData(); });
            const imageInput = document.getElementById('prop-image');
            if(imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if(file) { const base64 = await readImageAsBase64(file); const response = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'equipment' }) }); const data = await response.json(); if(data.success) { comp.iconFile = data.filename; const preview = document.getElementById('prop-image-preview'); if(preview) preview.innerHTML = `<img src="/uploads/icons/${data.filename}" style="max-width:50px;max-height:50px;">`; showToast(`✅ Ícone aplicado`); saveUserData(); } } }; }
        }
        
        function showShapeProperties(shape) {
            const div = document.getElementById('props-content');
            if(!shape) { div.innerHTML = '<p style="color:#6c757d; padding:20px; text-align:center;">👆 Toque em uma forma</p>'; return; }
            div.innerHTML = `
                <div class="property-group"><label>Tipo</label><input type="text" value="${getShapeName(shape.type)}" disabled></div>
                <div class="property-group"><label>Cor</label><input type="color" id="shape-stroke" value="${shape.strokeColor || '#005f99'}"></div>
                <div class="property-group"><label>Espessura</label><input type="range" id="shape-linewidth" min="1" max="10" value="${shape.lineWidth || 2}"></div>
                ${shape.type === 'text' ? `<div class="property-group"><label>Texto</label><input type="text" id="shape-text" value="${shape.text || ''}"></div><div class="property-group"><label>Tamanho Fonte</label><input type="number" id="shape-fontsize" value="${shape.fontSize || 14}"></div><div class="property-group"><label>Cor Texto</label><input type="color" id="shape-textcolor" value="${shape.textColor || '#212529'}"></div>` : `<div class="property-group"><label>🔄 Rotação</label><input type="range" id="shape-rotation" min="0" max="360" value="${shape.rotation || 0}"><span id="rotation-val">${Math.round(shape.rotation || 0)}°</span></div>`}
                <div class="modal-buttons" style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
                    <button class="btn btn-warning" onclick="rotateShapeLeft(${shape.id})">🔄 Girar -</button>
                    <button class="btn btn-warning" onclick="rotateShapeRight(${shape.id})">🔄 Girar +</button>
                    <button class="btn btn-secondary" onclick="duplicateShapeById(${shape.id})">📋 Duplicar</button>
                    <button class="btn btn-danger" onclick="deleteShape(${shape.id})">🗑 Excluir</button>
                </div>
            `;
            document.getElementById('shape-stroke')?.addEventListener('change', (e) => { shape.strokeColor = e.target.value; saveUserData(); });
            document.getElementById('shape-linewidth')?.addEventListener('change', (e) => { shape.lineWidth = parseInt(e.target.value); saveUserData(); });
            const rotSlider = document.getElementById('shape-rotation'); 
            if(rotSlider) { rotSlider.oninput = (e) => { shape.rotation = parseInt(e.target.value); document.getElementById('rotation-val').innerText = shape.rotation + '°'; saveUserData(); }; }
            if(shape.type === 'text') { 
                document.getElementById('shape-text')?.addEventListener('change', (e) => { shape.text = e.target.value; saveUserData(); }); 
                document.getElementById('shape-fontsize')?.addEventListener('change', (e) => { shape.fontSize = parseInt(e.target.value); saveUserData(); }); 
                document.getElementById('shape-textcolor')?.addEventListener('change', (e) => { shape.textColor = e.target.value; saveUserData(); }); 
            }
        }
        
        function showConnectionProperties(idx) {
            const div = document.getElementById('props-content'); 
            const conn = connections[idx];
            if(!conn) { div.innerHTML = '<p style="color:#6c757d;">Conexão não encontrada</p>'; return; }
            const fromComp = components.find(c => c.id === conn.from); 
            const toComp = components.find(c => c.id === conn.to); 
            if(!fromComp || !toComp) return;
            div.innerHTML = `
                <div class="property-group"><label>Conexão</label><input type="text" value="${fromComp.name} → ${toComp.name}" disabled></div>
                <div class="property-group"><label>Tipo de Cabo</label>
                    <select id="conn-cable-type" style="width:100%; padding:8px; background:var(--bg-card); border:1px solid var(--border-color); border-radius:5px;">
                        ${Object.entries(cableColors).map(([key, value]) => `<option value="${key}" ${conn.type === key ? 'selected' : ''}>${value.icon} ${value.name} - ${value.speed}</option>`).join('')}
                    </select>
                </div>
                <div class="modal-buttons">
                    <button class="btn btn-primary" onclick="updateSelectedConnection(${idx})">✅ Atualizar</button>
                    <button class="btn btn-danger" onclick="deleteSelectedConnection(${idx})">🗑 Excluir</button>
                </div>
            `;
        }
        
        window.updateSelectedConnection = (idx) => { 
            const cableType = document.getElementById('conn-cable-type').value; 
            connections[idx].type = cableType; 
            selectedConnectionIndex = null; 
            showProperties(null); 
            closeProperties(); 
            showToast(`✅ Conexão atualizada!`); 
            saveUserData(); 
        };
        window.deleteSelectedConnection = (idx) => { 
            if(confirm('Excluir esta conexão?')) { 
                connections.splice(idx, 1); 
                selectedConnectionIndex = null; 
                showProperties(null); 
                closeProperties(); 
                showToast(`🗑 Conexão removida!`); 
                saveUserData(); 
            } 
        };
        
        window.addConnection = (fromId) => { 
            const toId = document.getElementById('prop-connect').value; 
            const cableType = document.getElementById('prop-cable-type').value; 
            if(toId) { 
                connections.push({from: fromId, to: parseInt(toId), type: cableType}); 
                showToast(`✅ Conexão adicionada!`); 
                saveUserData(); 
            } else { showToast('⚠️ Selecione um equipamento'); } 
        };
        
        window.rotateLeft = (id) => { const comp = components.find(c => c.id === id); if(comp) { comp.rotation = (comp.rotation || 0) - 15; saveUserData(); showToast(`🔄 ${comp.name} girado`); } };
        window.rotateRight = (id) => { const comp = components.find(c => c.id === id); if(comp) { comp.rotation = (comp.rotation || 0) + 15; saveUserData(); showToast(`🔄 ${comp.name} girado`); } };
        window.flipComponentById = (id) => { const comp = components.find(c => c.id === id); if(comp) { comp.rotation = (comp.rotation || 0) + 180; saveUserData(); showToast(`🔁 ${comp.name} invertido`); } };
        window.rotateShapeLeft = (id) => { const s = shapes.find(x => x.id === id); if(s) { s.rotation = (s.rotation || 0) - 15; saveUserData(); } };
        window.rotateShapeRight = (id) => { const s = shapes.find(x => x.id === id); if(s) { s.rotation = (s.rotation || 0) + 15; saveUserData(); } };
        
        window.accessDeviceById = (id) => { const comp = components.find(c => c.id === id); accessDevice(comp); };
        window.deleteComponent = (id) => { 
            if(confirm('Remover este equipamento?')) { 
                connections = connections.filter(c => c.from !== id && c.to !== id); 
                components = components.filter(c => c.id !== id); 
                selectedComponents = selectedComponents.filter(c => c.id !== id); 
                showProperties(null); 
                closeProperties(); 
                showToast(`🗑 Removido!`); 
                saveUserData(); 
            } 
        };
        window.duplicateComponentById = (id) => {
            const comp = components.find(c => c.id === id);
            if (comp) {
                const newComp = JSON.parse(JSON.stringify(comp));
                newComp.id = Date.now();
                newComp.x += 40; newComp.y += 40;
                components.push(newComp);
                showToast(`📋 ${comp.name} duplicado`);
                saveUserData();
            }
        };
        
        window.deleteShape = (id) => { 
            shapes = shapes.filter(s => s.id !== id); 
            selectedShapes = selectedShapes.filter(s => s.id !== id); 
            showProperties(null); 
            closeProperties(); 
            showToast('🗑 Removida!'); 
            saveUserData(); 
        };
        window.duplicateShapeById = (id) => {
            const shape = shapes.find(s => s.id === id);
            if (shape) {
                const newShape = JSON.parse(JSON.stringify(shape));
                newShape.id = Date.now();
                if(newShape.type === 'line') { newShape.x1 += 30; newShape.y1 += 30; newShape.x2 += 30; newShape.y2 += 30; }
                else { newShape.x += 30; newShape.y += 30; }
                shapes.push(newShape);
                showToast(`📋 Forma duplicada`);
                saveUserData();
            }
        };
        
        window.deleteSelectedItems = () => {
            if (selectedComponents.length === 0 && selectedShapes.length === 0 && selectedConnectionIndex === null) { 
                showToast('⚠️ Nenhum item selecionado'); 
                return; 
            }
            if (confirm(`Excluir ${selectedComponents.length} equipamento(s), ${selectedShapes.length} forma(s)?`)) {
                const selectedIds = selectedComponents.map(c => c.id); 
                connections = connections.filter(c => !selectedIds.includes(c.from) && !selectedIds.includes(c.to));
                if (selectedConnectionIndex !== null) { connections.splice(selectedConnectionIndex, 1); selectedConnectionIndex = null; }
                components = components.filter(c => !selectedIds.includes(c.id)); 
                const selectedShapeIds = selectedShapes.map(s => s.id); 
                shapes = shapes.filter(s => !selectedShapeIds.includes(s.id));
                selectedComponents = []; selectedShapes = []; 
                showProperties(null); 
                closeProperties(); 
                showToast(`🗑 Excluído!`); 
                saveUserData();
            }
        };
        
        function showContextMenu(e, comp) {
            if (e.preventDefault) e.preventDefault(); 
            contextMenuComponent = comp;
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `
                <div class="context-menu-item" onclick="accessDeviceFromMenu()">🌐 Acessar</div>
                <div class="context-menu-item" onclick="copyIpFromMenu()">📋 Copiar IP</div>
                <div class="context-menu-item" onclick="rotateLeftFromMenu()">🔄 Girar -</div>
                <div class="context-menu-item" onclick="rotateRightFromMenu()">🔄 Girar +</div>
                <div class="context-menu-item" onclick="duplicateComponentFromMenu()">📋 Duplicar</div>
                <div class="context-menu-item" onclick="openPermanentIconModalFromMenu()">🎨 Alterar Ícone</div>
                <div class="context-menu-item" onclick="deleteComponentFromMenu()" style="color:#dc3545;">🗑 Remover</div>
            `;
            menu.style.display = 'block'; 
            menu.style.left = Math.min(e.pageX, window.innerWidth - 220) + 'px'; 
            menu.style.top = Math.min(e.pageY, window.innerHeight - 350) + 'px';
            setTimeout(() => document.addEventListener('click', closeContextMenu, {once: true}), 100);
        }
        
        function showShapeContextMenu(e, shape) {
            if (e.preventDefault) e.preventDefault(); 
            contextMenuShape = shape;
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `
                <div class="context-menu-item" onclick="editShapeFromMenu()">✏️ Editar</div>
                <div class="context-menu-item" onclick="duplicateShapeFromMenu()">📋 Duplicar</div>
                <div class="context-menu-item" onclick="deleteShapeFromMenu()" style="color:#dc3545;">🗑 Excluir</div>
            `;
            menu.style.display = 'block'; 
            menu.style.left = Math.min(e.pageX, window.innerWidth - 220) + 'px'; 
            menu.style.top = Math.min(e.pageY, window.innerHeight - 200) + 'px';
            setTimeout(() => document.addEventListener('click', closeContextMenu, {once: true}), 100);
        }
        
        function closeContextMenu() { document.getElementById('contextMenu').style.display = 'none'; }
        
        window.accessDeviceFromMenu = () => { if(contextMenuComponent) accessDevice(contextMenuComponent); closeContextMenu(); };
        window.copyIpFromMenu = () => { if(contextMenuComponent && contextMenuComponent.ip) { navigator.clipboard.writeText(contextMenuComponent.ip).catch(()=>{}); showToast(`📋 IP copiado!`); } else { showToast('Sem IP'); } closeContextMenu(); };
        window.rotateLeftFromMenu = () => { if(contextMenuComponent) { contextMenuComponent.rotation = (contextMenuComponent.rotation || 0) - 15; saveUserData(); } closeContextMenu(); };
        window.rotateRightFromMenu = () => { if(contextMenuComponent) { contextMenuComponent.rotation = (contextMenuComponent.rotation || 0) + 15; saveUserData(); } closeContextMenu(); };
        window.duplicateComponentFromMenu = () => { 
            if(contextMenuComponent) { 
                const newComp = JSON.parse(JSON.stringify(contextMenuComponent)); 
                newComp.id = Date.now(); newComp.x += 40; newComp.y += 40; 
                components.push(newComp); 
                showToast(`📋 Duplicado`); 
                saveUserData(); 
            } 
            closeContextMenu(); 
        };
        window.deleteComponentFromMenu = () => { 
            if(contextMenuComponent) { 
                connections = connections.filter(c => c.from !== contextMenuComponent.id && c.to !== contextMenuComponent.id); 
                components = components.filter(c => c.id !== contextMenuComponent.id); 
                selectedComponents = []; 
                showProperties(null); 
                showToast(`🗑 Removido`); 
                saveUserData(); 
            } 
            closeContextMenu(); 
        };
        window.openPermanentIconModalFromMenu = () => { if(contextMenuComponent) openPermanentIconModal(contextMenuComponent); closeContextMenu(); };
        
        window.editShapeFromMenu = () => { if(contextMenuShape) { showShapeProperties(contextMenuShape); openProperties(); } closeContextMenu(); };
        window.duplicateShapeFromMenu = () => { 
            if(contextMenuShape) { 
                const newShape = JSON.parse(JSON.stringify(contextMenuShape)); 
                newShape.id = Date.now(); 
                if(newShape.type === 'line') { newShape.x1 += 30; newShape.y1 += 30; newShape.x2 += 30; newShape.y2 += 30; }
                else { newShape.x += 30; newShape.y += 30; }
                shapes.push(newShape); 
                showToast(`📋 Duplicada`); 
                saveUserData(); 
            } 
            closeContextMenu(); 
        };
        window.deleteShapeFromMenu = () => { 
            if(contextMenuShape) { 
                shapes = shapes.filter(s => s.id !== contextMenuShape.id); 
                selectedShapes = []; 
                showProperties(null); 
                showToast(`🗑 Removida`); 
                saveUserData(); 
            } 
            closeContextMenu(); 
        };
        
        function openPermanentIconModal(comp) {
            const modal = document.createElement('div'); 
            modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🎨 Alterar Ícone</h3><p>Equipamento: <strong>${comp.name}</strong></p><div class="property-group"><label>Escolha uma imagem</label><input type="file" id="permIconImage" accept="image/*"><div class="image-preview" id="permIconPreview"></div></div><div class="modal-buttons"><button class="btn btn-primary" onclick="applyPermanentIcon(${comp.id})">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button></div></div>`;
            document.body.appendChild(modal); 
            window.currentModal = modal;
            const imageInput = document.getElementById('permIconImage');
            if(imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if(file) { const base64 = await readImageAsBase64(file); const preview = document.getElementById('permIconPreview'); if(preview) preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">'; const response = await fetch('/api/upload_icon', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, type: 'equipment' }) }); const data = await response.json(); if(data.success) { window.permIconFilename = data.filename; showToast('✅ Ícone enviado!'); } } }; }
        }
        
        window.applyPermanentIcon = (compId) => {
            const comp = components.find(c => c.id === compId);
            if(comp && window.permIconFilename) { 
                comp.iconFile = window.permIconFilename; 
                showToast(`✅ Ícone aplicado a ${comp.name}`); 
                closeModal(); 
                saveUserData(); 
            }
            else if(comp) showToast('⚠️ Selecione uma imagem');
            window.permIconFilename = null;
        };
        
        window.openPermanentIconModalById = (id) => { const comp = components.find(c => c.id === id); if(comp) openPermanentIconModal(comp); };
        
        function openProperties() { 
            document.getElementById('propertiesPanel').classList.add('open');
            if (isMobile) document.getElementById('mobileOverlay').classList.add('active');
        }
        function closeProperties() { 
            document.getElementById('propertiesPanel').classList.remove('open');
            if (isMobile) document.getElementById('mobileOverlay').classList.remove('active');
        }
        function closePropertiesPanel() { closeProperties(); }
        
        function readImageAsBase64(file) { return new Promise((resolve) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.readAsDataURL(file); }); }
        
        function openBackgroundModal() {
            const modal = document.createElement('div'); 
            modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🖼️ Planta Baixa</h3><div style="background:var(--bg-tertiary); padding:12px; border-radius:8px; margin-bottom:15px;"><label><strong>📁 Importar Imagem</strong></label><input type="file" id="bgImageUpload" accept="image/*" style="margin-top:8px;"><button class="btn btn-primary" style="margin-top:8px; width:100%;" onclick="importLocalImage()">📤 Importar</button></div><div style="background:var(--bg-tertiary); padding:12px; border-radius:8px; margin-bottom:15px;"><label><strong>🎨 Opacidade</strong></label><input type="range" id="bgOpacity" min="0.1" max="1" step="0.01" value="${backgroundOpacity}" onchange="updateBackgroundOpacity(this.value)" style="margin-top:8px;"><span id="opacityValue">${Math.round(backgroundOpacity * 100)}%</span></div>${backgroundImage ? `<div style="margin-bottom:15px;"><button class="btn btn-secondary" style="width:100%; margin-bottom:8px;" onclick="selectBackgroundImage()">🔍 Selecionar</button><button class="btn btn-danger" style="width:100%;" onclick="removeBackground()">🗑 Remover</button></div>` : ''}<div class="modal-buttons"><button class="btn btn-danger" style="width:100%;" onclick="closeModal()">❌ Fechar</button></div></div>`;
            document.body.appendChild(modal); 
            window.currentModal = modal;
        }
        
        window.importLocalImage = async () => { 
            const fileInput = document.getElementById('bgImageUpload'); 
            const file = fileInput.files[0]; 
            if (file) { const base64 = await readImageAsBase64(file); await uploadBackgroundImage(base64, file.name); } 
            else showToast('Selecione uma imagem'); 
        };
        window.selectBackgroundImage = () => { isBackgroundSelected = true; closeModal(); showToast('✅ Imagem selecionada!'); };
        window.updateBackgroundOpacity = (value) => { backgroundOpacity = parseFloat(value); document.getElementById('opacityValue').innerText = Math.round(backgroundOpacity * 100) + '%'; saveUserData(); };
        window.removeBackground = () => { 
            if (confirm('Remover imagem?')) { 
                backgroundImage = null; backgroundImageObj = null; backgroundOpacity = 0.8; backgroundWidth = 0; backgroundHeight = 0; backgroundX = 0; backgroundY = 0; isBackgroundSelected = false; 
                saveUserData(); showToast('✅ Removida'); closeModal(); 
            } 
        };
        
        async function uploadBackgroundImage(base64, name) {
            showToast('📤 Enviando...');
            try {
                const response = await fetch('/api/upload_background', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: base64, name: name }) });
                const data = await response.json();
                if (data.success) { 
                    backgroundImage = data.url; 
                    backgroundImageObj = new Image(); 
                    backgroundImageObj.onload = function() { 
                        backgroundWidth = backgroundImageObj.width; 
                        backgroundHeight = backgroundImageObj.height; 
                        backgroundX = canvas.width/2 - backgroundWidth/2; 
                        backgroundY = canvas.height/2 - backgroundHeight/2; 
                        saveUserData(); 
                        showToast('✅ Imagem adicionada!'); 
                        closeModal(); 
                    }; 
                    backgroundImageObj.src = backgroundImage; 
                    saveUserData(); 
                }
            } catch(e) { showToast('Erro ao enviar'); }
        }
        
        function newProject() { 
            if (confirm('Novo projeto? Dados não salvos serão perdidos.')) { 
                components = []; connections = []; shapes = []; selectedComponents = []; selectedShapes = []; selectedConnectionIndex = null; 
                backgroundImage = null; backgroundImageObj = null; backgroundOpacity = 0.8; backgroundWidth = 0; backgroundHeight = 0; backgroundX = 0; backgroundY = 0; isBackgroundSelected = false; 
                closeProperties(); saveUserData(); showToast('📁 Novo projeto!'); 
            } 
        }
        
        function saveProjectToFile() {
            const projectData = { components, connections, shapes, background: backgroundImage, backgroundOpacity, backgroundWidth, backgroundHeight, backgroundX, backgroundY, version: '2.0', date: new Date().toISOString() };
            const dataStr = JSON.stringify(projectData, null, 2); 
            const blob = new Blob([dataStr], {type: 'application/json'}); 
            const url = URL.createObjectURL(blob); 
            const a = document.createElement('a'); 
            a.href = url; a.download = `projeto_${Date.now()}.projetize`; a.click(); 
            URL.revokeObjectURL(url); 
            showToast('✅ Salvo!');
        }
        
        function loadProjectFromFile() {
            const input = document.createElement('input'); input.type = 'file'; input.accept = '.projetize, .json';
            input.onchange = (e) => {
                const file = e.target.files[0]; if (!file) return;
                const reader = new FileReader();
                reader.onload = (ev) => {
                    try {
                        const data = JSON.parse(ev.target.result); 
                        components = data.components || []; connections = data.connections || []; shapes = data.shapes || [];
                        if (data.background) { 
                            backgroundImage = data.background; backgroundOpacity = data.backgroundOpacity || 0.8; 
                            backgroundWidth = data.backgroundWidth || 0; backgroundHeight = data.backgroundHeight || 0; 
                            backgroundX = data.backgroundX || 0; backgroundY = data.backgroundY || 0; 
                            backgroundImageObj = new Image(); backgroundImageObj.src = backgroundImage; 
                        }
                        saveUserData(); 
                        showToast('✅ Carregado!');
                    } catch(err) { showToast('Erro: ' + err.message); }
                };
                reader.readAsText(file);
            };
            input.click();
        }
        
        function exportPDF() { 
            drawWithBackground(true, true); 
            setTimeout(() => { 
                const imgData = canvas.toDataURL('image/png'); 
                const pdfWindow = window.open('', '_blank'); 
                pdfWindow.document.write(`<html><body style="margin:0;padding:20px;"><img src="${imgData}" style="max-width:100%;"><script>window.print();<\/script></body></html>`); 
                setTimeout(() => draw(), 500); 
                showToast('📄 PDF gerado!'); 
            }, 100); 
        }
        
        function exportPDFWithList() {
            drawWithBackground(true, true);
            let listHTML = `<div style="font-family: Arial; padding: 20px;"><h1 style="color: #005f99; text-align: center;">PROJETIZE</h1><p><strong>Data:</strong> ${new Date().toLocaleString()}</p><p><strong>Por:</strong> Thiago Souza</p><br>`;
            const byType = {}; 
            components.forEach(comp => { const type = comp.type || 'outros'; if (!byType[type]) byType[type] = []; byType[type].push(comp); });
            for (const [type, comps] of Object.entries(byType)) {
                listHTML += `<h2>📌 ${type.toUpperCase()}</h2><table style="width:100%;border-collapse:collapse;"><tr style="background:#005f99;color:white;"><th style="padding:8px;">Equipamento</th><th style="padding:8px;">IP</th></tr>`;
                comps.forEach(comp => { listHTML += `<tr><td style="padding:8px;">${comp.name}</td><td style="padding:8px;">${comp.ip || 'N/A'}</td></tr>`; });
                listHTML += '</table>';
            }
            listHTML += `<br><p><strong>Total:</strong> ${components.length} equipamentos, ${connections.length} conexões</p></div>`;
            const imgData = canvas.toDataURL('image/png'); 
            const pdfWindow = window.open('', '_blank');
            pdfWindow.document.write(`<html><head><title>Projeto</title><style>@media print{.page-break{page-break-before:always;}}</style></head><body style="margin:0;padding:20px;"><img src="${imgData}" style="max-width:100%;"><div class="page-break"></div>${listHTML}<script>window.print();<\/script></body></html>`);
            setTimeout(() => draw(), 500); 
            showToast('📄 PDF gerado!');
        }
        
        function generateBudget() {
            let list = '📋 ORÇAMENTO\n' + '='.repeat(50) + '\n\nData: ' + new Date().toLocaleString() + '\n\n';
            const byType = {}; 
            components.forEach(comp => { const type = comp.type || 'outros'; if (!byType[type]) byType[type] = []; byType[type].push(comp); });
            for (const [type, comps] of Object.entries(byType)) { list += `\n${type.toUpperCase()}:\n`; comps.forEach(comp => { list += `  ✅ ${comp.name}${comp.ip ? ' (' + comp.ip + ')' : ''}\n`; }); }
            list += `\nTotal: ${components.length} equipamentos, ${connections.length} conexões\n`;
            const blob = new Blob([list], {type: 'text/plain;charset=utf-8'}); 
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `orcamento_${Date.now()}.txt`; a.click(); 
            showToast('💰 Baixado!');
        }
        
        function toggleGrid() { showGrid = !showGrid; showToast(showGrid ? '🔲 Grade ON' : '🔳 Grade OFF'); }
        function setShapeMode(mode) { 
            shapeMode = mode; 
            document.querySelectorAll('.shape-btn').forEach(btn => btn.classList.remove('active')); 
            if (event && event.target) event.target.classList.add('active'); 
            showToast(`✏️ Modo: ${getShapeName(mode)}`); 
        }
        function cancelShapeMode() { shapeMode = null; drawingPreview = null; document.querySelectorAll('.shape-btn').forEach(btn => btn.classList.remove('active')); showToast('❌ Cancelado'); }
        function toggleShapesToolbar() { const toolbar = document.getElementById('shapesToolbar'); toolbar.style.display = toolbar.style.display === 'none' ? 'flex' : 'none'; }
        function togglePalette() { const palette = document.getElementById('palette'); palette.classList.toggle('collapsed'); }
        
        // ==================== LOGIN ====================
        async function doLogin() {
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;
            const response = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
            const data = await response.json();
            
            if (data.success) {
                currentUser = username; userRole = data.role;
                document.getElementById('loginModal').style.display = 'none';
                document.getElementById('loginBgVideo').style.display = 'none';
                document.getElementById('loginBgGif').style.display = 'none';
                document.getElementById('loginBgOverlay').style.display = 'none';
                
                document.getElementById('loadingOverlay').style.display = 'flex';
                document.getElementById('toolbar').style.display = 'flex';
                document.getElementById('userInfo').innerHTML = `<span>👤 ${username}</span><span class="user-role">${data.role.toUpperCase()}</span>`;
                
                if (data.role === 'admin' || data.role === 'master') {
                    ['adminUsersBtn','adminShapesBtn','adminCategoriesBtn','adminDevicesBtn','adminConnectionsBtn','resetDefaultsBtn','adminDevBtn','adminBgBtn'].forEach(id => { const el = document.getElementById(id); if(el) el.style.display = 'inline-block'; });
                }
                
                await Promise.all([loadDefaultConfig(), loadDefaultConnections()]);
                await loadUserData();
                document.getElementById('loadingOverlay').style.display = 'none';
                showToast(`Bem-vindo, ${username}!`);
            } else {
                document.getElementById('loginError').style.display = 'block';
            }
        }
        
        function logout() { fetch('/api/logout', { method: 'POST' }).then(() => location.reload()); }
        
        async function openUserManagement() {
            const response = await fetch('/api/users'); 
            const users = await response.json();
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">👥 Usuários</h3><div id="userList" style="margin:15px 0;"></div><div style="margin-top:15px;"><input type="text" id="newUsername" placeholder="Usuário"><input type="password" id="newPassword" placeholder="Senha"><select id="newRole"><option value="viewer">Visualizador</option><option value="admin">Admin</option></select><button class="btn btn-primary" style="margin-top:10px; width:100%;" onclick="addUser()">➕ Adicionar</button></div><div class="modal-buttons"><button class="btn btn-danger" style="width:100%;" onclick="closeModal()">Fechar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal; renderUserList(users);
        }
        
        function renderUserList(users) {
            const container = document.getElementById('userList'); if (!container) return; container.innerHTML = '';
            for (const [username, userData] of Object.entries(users)) { 
                const userDiv = document.createElement('div'); 
                userDiv.style.cssText = 'background:var(--bg-tertiary); padding:10px; margin:5px 0; border-radius:5px; display:flex; justify-content:space-between; align-items:center;';
                userDiv.innerHTML = `<div><strong>${username}</strong><br><small>${userData.role}</small></div><div>${userData.role !== 'master' ? `<button onclick="deleteUser('${username}')" style="background:none;border:none;cursor:pointer;font-size:16px;">🗑</button>` : '<span style="color:var(--text-accent);font-size:11px;">Master</span>'}</div>`; 
                container.appendChild(userDiv); 
            }
        }
        
        async function addUser() {
            const username = document.getElementById('newUsername').value; 
            const password = document.getElementById('newPassword').value; 
            const role = document.getElementById('newRole').value;
            if (!username || !password) { showToast('Preencha tudo'); return; }
            const response = await fetch('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password, role }) });
            const data = await response.json();
            if (data.success) { showToast('✅ Adicionado!'); closeModal(); openUserManagement(); } else { showToast(data.error); }
        }
        
        async function deleteUser(username) {
            if (confirm(`Excluir "${username}"?`)) { 
                const response = await fetch(`/api/users/${username}`, { method: 'DELETE' }); 
                const data = await response.json(); 
                if (data.success) { showToast('✅ Excluído!'); closeModal(); openUserManagement(); } 
                else { showToast(data.error); } 
            }
        }
        
        async function resetToDefaultConfig() {
            if (confirm('⚠️ Restaurar configurações padrão?')) { 
                try { 
                    const response = await fetch('/api/reset_default_config', { method: 'POST' }); 
                    const data = await response.json(); 
                    if (data.success) { 
                        await loadDefaultConfig(); 
                        categories = JSON.parse(JSON.stringify(defaultCategories)); 
                        customDevices = []; 
                        saveUserData(); saveGlobalLibrary(); renderPalette(); 
                        showToast('✅ Restaurado!'); 
                    } 
                } catch(e) { showToast('Erro'); } 
            }
        }
        
        function openDevImageModal() {
            if (userRole !== 'admin' && userRole !== 'master') return;
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content"><h3 style="color:var(--text-accent);">🖼️ Foto do Desenvolvedor</h3><input type="file" id="newDevImage" accept="image/*"><div class="image-preview" id="newDevPreview"></div><div class="modal-buttons"><button class="btn btn-primary" onclick="uploadNewDevImage()">✅ Salvar</button><button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button></div></div>`;
            document.body.appendChild(modal); window.currentModal = modal;
            const imageInput = document.getElementById('newDevImage');
            if (imageInput) { imageInput.onchange = async (e) => { const file = e.target.files[0]; if (file) { const base64 = await readImageAsBase64(file); const preview = document.getElementById('newDevPreview'); if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:100px;max-height:100px;">`; window.tempDevImage = base64; } }; }
        }
        window.uploadNewDevImage = async () => {
            if (!window.tempDevImage) { showToast('Selecione uma imagem'); return; }
            try { 
                const response = await fetch('/api/upload_dev_image', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: window.tempDevImage }) }); 
                const data = await response.json(); 
                if (data.success) { showToast('✅ Foto atualizada!'); setTimeout(() => location.reload(), 1000); } 
                else { showToast('❌ Erro: ' + data.error); } 
            } catch(e) { showToast('❌ Erro'); }
            window.tempDevImage = null; closeModal();
        };
        
        function loadDevImages() {
            const loginContainer = document.getElementById('loginDevImageContainer'); 
            const loginImg = document.getElementById('loginDevImage'); 
            const badgeImg = document.getElementById('badgeDevImage'); 
            const img = new Image();
            img.onload = function() { 
                if (loginImg) { loginImg.src = img.src; loginImg.style.display = 'block'; } 
                if (badgeImg) badgeImg.src = img.src; 
                if (loginContainer) loginContainer.style.background = 'transparent'; 
            };
            img.onerror = function() {
                if (devImageBase64) { 
                    const dataUrl = 'data:image/png;base64,' + devImageBase64; 
                    if (loginImg) { loginImg.src = dataUrl; loginImg.style.display = 'block'; } 
                    if (badgeImg) badgeImg.src = dataUrl; 
                    if (loginContainer) loginContainer.style.background = 'transparent'; 
                }
            };
            img.src = devImageBase64 ? 'data:image/png;base64,' + devImageBase64 : '/static/dev.png?v=2';
        }
        
        // ==================== LISTENERS DE ARQUIVO DE FUNDO ====================
        document.getElementById('loginBgFileInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            selectedLoginBgFile = file;
            const preview = document.getElementById('loginBgPreview');
            
            if (file.type.startsWith('video/')) {
                selectedLoginBgType = 'video';
                const url = URL.createObjectURL(file);
                preview.innerHTML = `<video src="${url}" autoplay loop muted playsinline style="max-width:100%; max-height:100%;"></video>`;
            } else if (file.type.startsWith('image/')) {
                selectedLoginBgType = 'image';
                const url = URL.createObjectURL(file);
                preview.innerHTML = `<img src="${url}" style="max-width:100%; max-height:100%;">`;
            } else {
                showToast('⚠️ Formato não suportado. Use imagem, GIF ou MP4.');
                selectedLoginBgFile = null;
                return;
            }
        });
        
        document.getElementById('loginBgOpacityRange').addEventListener('input', function(e) {
            document.getElementById('loginBgOpacityValue').textContent = Math.round(parseFloat(e.target.value) * 100) + '%';
        });
        
        // ==================== EVENT LISTENERS DO CANVAS ====================
        canvas.addEventListener('dragover', (e) => e.preventDefault());
        canvas.addEventListener('drop', (e) => {
            e.preventDefault(); 
            const pos = getMousePos(e); 
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            const component = { id: Date.now(), type: data.type || 'custom', subtype: data.subtype || '', name: data.name, x: pos.x, y: pos.y, icon: data.icon || '📦', iconFile: data.iconFile || null, color: data.color || '#005f99', angle: 0, fov: 80, rotation: 0, ip: '', port: 80 };
            components.push(component); 
            showToast(`✅ ${component.name} adicionado!`); 
            saveUserData();
        });
        
        canvas.addEventListener('touchstart', (e) => { e.preventDefault(); handleStart(e); }, { passive: false });
        canvas.addEventListener('touchmove', (e) => { e.preventDefault(); handleMove(e); }, { passive: false });
        canvas.addEventListener('touchend', (e) => { handleEnd(e); });
        canvas.addEventListener('touchcancel', (e) => { handleEnd(e); });
        canvas.addEventListener('mousedown', handleStart);
        canvas.addEventListener('mousemove', handleMove);
        canvas.addEventListener('mouseup', handleEnd);
        canvas.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            const pos = getMousePos(e);
            for(let comp of components) { 
                if(Math.hypot(pos.x - comp.x, pos.y - comp.y) < iconSize/2) { 
                    showContextMenu({preventDefault:()=>{}, pageX: e.pageX, pageY: e.pageY}, comp); 
                    return; 
                } 
            }
            for(let shape of shapes) { 
                if(isPointOnShape(pos.x, pos.y, shape)) { 
                    showShapeContextMenu({preventDefault:()=>{}, pageX: e.pageX, pageY: e.pageY}, shape); 
                    return; 
                } 
            }
        });
        
        let lastTap = 0;
        canvas.addEventListener('touchend', (e) => {
            const now = Date.now();
            if (now - lastTap < 300) e.preventDefault();
            lastTap = now;
        }, { passive: false });
        
        // ==================== INIT ====================
        (async function init() {
            await loadLoginBgConfig();
            await loadDefaultConfig();
            await loadDefaultConnections();
            categories = JSON.parse(JSON.stringify(defaultCategories));
            renderPalette();
            renderConnectionsPalette();
        })();

        loadDevImages(); 
        closeProperties();
        setTimeout(() => { const splash = document.getElementById('splashScreen'); if (splash) splash.style.display = 'none'; }, 3000);
        
        window.newProject = newProject; window.saveProjectToFile = saveProjectToFile; window.loadProjectFromFile = loadProjectFromFile; window.exportPDF = exportPDF; window.exportPDFWithList = exportPDFWithList; window.generateBudget = generateBudget;
        window.zoomIn = zoomIn; window.zoomOut = zoomOut; window.resetZoom = resetZoom; window.iconZoomIn = iconZoomIn; window.iconZoomOut = iconZoomOut; window.resetIconSize = resetIconSize;
        window.togglePalette = togglePalette; window.closeModal = closeModal; window.openAddCategoryModal = openAddCategoryModal; window.openAddDeviceModal = openAddDeviceModal; window.openAddConnectionModal = openAddConnectionModal;
        window.doLogin = doLogin; window.logout = logout; window.openUserManagement = openUserManagement; window.addUser = addUser; window.deleteUser = deleteUser;
        window.setShapeMode = setShapeMode; window.cancelShapeMode = cancelShapeMode; window.toggleShapesToolbar = toggleShapesToolbar; window.toggleGrid = toggleGrid; window.resetToDefaultConfig = resetToDefaultConfig;
        window.openBackgroundModal = openBackgroundModal; window.updateBackgroundOpacity = updateBackgroundOpacity; window.removeBackground = removeBackground; window.importLocalImage = importLocalImage; window.selectBackgroundImage = selectBackgroundImage;
        window.closePropertiesPanel = closePropertiesPanel;
        window.deleteSelectedItems = deleteSelectedItems;
        window.openDevImageModal = openDevImageModal; window.uploadNewDevImage = uploadNewDevImage;
        window.openLoginBgConfig = openLoginBgConfig; window.closeLoginBgConfig = closeLoginBgConfig; window.applyLoginBg = applyLoginBg; window.resetLoginBg = resetLoginBg;
        window.mobileTab = mobileTab; window.closeMobilePanels = closeMobilePanels;
        
        window.openAddCategoryModal = openAddCategoryModal;
        window.openAddDeviceModal = openAddDeviceModal;
        window.openAddConnectionModal = openAddConnectionModal;
        
        document.getElementById('bgConfigModal').addEventListener('click', function(e) {
            if (e.target === this) closeLoginBgConfig();
        });
    </script>
</body>
</html>
