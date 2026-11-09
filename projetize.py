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
users = {}

def get_dev_image_base64():
    possible_paths = [
        os.path.join(STATIC_FOLDER, 'dev.png'),
        os.path.join(STATIC_FOLDER, 'dev.jpg'),
        os.path.join(STATIC_FOLDER, 'developer.png'),
        'static/dev.png',
        'dev.png',
        os.path.join(os.path.dirname(__file__), 'static', 'dev.png'),
        os.path.join(os.path.dirname(__file__), 'dev.png'),
    ]
    
    for path in possible_paths:
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    image_data = f.read()
                    print(f"✅ Imagem do desenvolvedor carregada de: {path}")
                    return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            print(f"Erro ao tentar carregar de {path}: {e}")
    
    print("⚠️ Nenhuma imagem do desenvolvedor encontrada. Usando fallback com iniciais.")
    return None

def get_default_avatar_svg():
    return '''<svg width="150" height="150" viewBox="0 0 150 150" xmlns="http://www.w3.org/2000/svg">
        <circle cx="75" cy="75" r="70" fill="#005f99" stroke="#00ccff" stroke-width="3"/>
        <circle cx="75" cy="75" r="65" fill="none" stroke="#00ccff" stroke-width="1" stroke-dasharray="5,5"/>
        <text x="75" y="85" font-family="Arial, sans-serif" font-size="40" font-weight="bold" fill="#ffffff" text-anchor="middle">TS</text>
        <text x="75" y="110" font-family="Arial, sans-serif" font-size="12" fill="#00ccff" text-anchor="middle">Thiago Souza</text>
    </svg>'''

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

users['thiago03'] = {
    'password': hash_password('Thiago@000333'),
    'role': 'master',
    'name': 'Thiago Souza',
    'created_at': datetime.now().isoformat()
}

dev_image_data = get_dev_image_base64() or ""
if not dev_image_data:
    dev_image_data = base64.b64encode(get_default_avatar_svg().encode()).decode('utf-8')
    print("✅ Usando avatar SVG como fallback")

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
            try:
                os.remove(old_path)
            except:
                pass
    
    if image_data and image_data.startswith('data:image'):
        format_map = {
            'data:image/png;base64,': '.png',
            'data:image/jpeg;base64,': '.jpg',
            'data:image/jpg;base64,': '.jpg',
            'data:image/gif;base64,': '.gif',
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
        except:
            pass
    return False

def save_background_image(image_data, name=None):
    if image_data and image_data.startswith('data:image'):
        format_map = {
            'data:image/png;base64,': '.png',
            'data:image/jpeg;base64,': '.jpg',
            'data:image/jpg;base64,': '.jpg',
            'data:image/gif;base64,': '.gif',
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
        except:
            pass
    return False

# Configuração padrão de conexões
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

DEFAULT_CONNECTIONS_FILE = os.path.join(UPLOAD_FOLDER, 'default_connections.json')
CUSTOM_DEVICES_FILE = os.path.join(UPLOAD_FOLDER, 'custom_devices.json')

def load_default_connections():
    if os.path.exists(DEFAULT_CONNECTIONS_FILE):
        try:
            with open(DEFAULT_CONNECTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return json.loads(json.dumps(DEFAULT_CONNECTIONS_CONFIG))

def save_default_connections(config):
    try:
        with open(DEFAULT_CONNECTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def load_custom_devices():
    if os.path.exists(CUSTOM_DEVICES_FILE):
        try:
            with open(CUSTOM_DEVICES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return []

def save_custom_devices(devices):
    try:
        with open(CUSTOM_DEVICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(devices, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# Configuração padrão de equipamentos
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

DEFAULT_CONFIG_FILE = os.path.join(UPLOAD_FOLDER, 'default_config.json')

def load_default_config():
    if os.path.exists(DEFAULT_CONFIG_FILE):
        try:
            with open(DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return json.loads(json.dumps(DEFAULT_CATEGORIES_CONFIG))

def save_default_config(config):
    try:
        with open(DEFAULT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

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
    
    format_map = {
        'data:image/png;base64,': '.png',
        'data:image/jpeg;base64,': '.jpg',
        'data:image/jpg;base64,': '.jpg',
        'data:image/gif;base64,': '.gif',
        'data:image/webp;base64,': '.webp'
    }
    
    ext = '.png'
    for key, value in format_map.items():
        if image_data.startswith(key):
            ext = value
            image_data = image_data.replace(key, '')
            break
    else:
        image_data = image_data.split(',')[1] if ',' in image_data else image_data
    
    prefix = {
        'equipment': 'eqp',
        'category': 'cat',
        'connection': 'con'
    }.get(target_type, 'ico')
    
    filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(target_folder, filename)
    
    try:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return jsonify({'success': True, 'filename': filename, 'type': target_type})
    except Exception as e:
        print(f"Erro ao salvar imagem: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_global_categories', methods=['POST'])
@admin_required
def save_global_categories():
    data = request.json
    categories_data = data.get('categories')
    if categories_data:
        save_default_config(categories_data)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

@app.route('/api/save_global_connections', methods=['POST'])
@admin_required
def save_global_connections():
    data = request.json
    connections_data = data.get('connections')
    if connections_data:
        save_default_connections(connections_data)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

@app.route('/api/save_global_custom_devices', methods=['POST'])
@admin_required
def save_global_custom_devices():
    data = request.json
    devices = data.get('devices')
    if devices is not None:
        save_custom_devices(devices)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

@app.route('/api/load_custom_devices', methods=['GET'])
def get_custom_devices():
    return jsonify({'success': True, 'devices': load_custom_devices()})

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

@app.route('/api/backgrounds', methods=['GET'])
@login_required
def get_backgrounds():
    backgrounds_list = []
    for filename in os.listdir(BACKGROUNDS_FOLDER):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            backgrounds_list.append({
                'filename': filename,
                'url': f'/uploads/backgrounds/{filename}'
            })
    return jsonify({'success': True, 'backgrounds': backgrounds_list})

@app.route('/api/delete_background', methods=['POST'])
@login_required
def delete_background():
    data = request.json
    filename = data.get('filename', '')
    
    if delete_background_image(filename):
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Erro ao excluir imagem'}), 500

@app.route('/api/upload_dev_image', methods=['POST'])
@admin_required
def upload_dev_image():
    data = request.json
    image_data = data.get('image', '')
    
    if not image_data or not image_data.startswith('data:image'):
        return jsonify({'success': False, 'error': 'Imagem inválida'}), 400
    
    format_map = {
        'data:image/png;base64,': '.png',
        'data:image/jpeg;base64,': '.jpg',
        'data:image/jpg;base64,': '.jpg',
        'data:image/gif;base64,': '.gif',
        'data:image/webp;base64,': '.webp'
    }
    
    ext = '.png'
    for key, value in format_map.items():
        if image_data.startswith(key):
            ext = value
            image_data = image_data.replace(key, '')
            break
    else:
        image_data = image_data.split(',')[1] if ',' in image_data else image_data
    
    filename = f"dev{ext}"
    filepath = os.path.join(STATIC_FOLDER, filename)
    
    for old_ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        old_path = os.path.join(STATIC_FOLDER, f"dev{old_ext}")
        if os.path.exists(old_path) and old_path != filepath:
            try:
                os.remove(old_path)
            except:
                pass
    
    try:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return jsonify({'success': True, 'url': f'/static/{filename}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/default_config', methods=['GET'])
def get_default_config():
    config = load_default_config()
    return jsonify({'success': True, 'config': config})

@app.route('/api/default_connections', methods=['GET'])
def get_default_connections():
    config = load_default_connections()
    return jsonify({'success': True, 'config': config})

@app.route('/api/reset_default_config', methods=['POST'])
@admin_required
def reset_default_config():
    for filename in os.listdir(DEFAULT_ICONS_FOLDER):
        try:
            os.remove(os.path.join(DEFAULT_ICONS_FOLDER, filename))
        except:
            pass
    
    default_config = json.loads(json.dumps(DEFAULT_CATEGORIES_CONFIG))
    save_default_config(default_config)
    return jsonify({'success': True})

@app.route('/api/reset_default_connections', methods=['POST'])
@admin_required
def reset_default_connections():
    default_connections = json.loads(json.dumps(DEFAULT_CONNECTIONS_CONFIG))
    save_default_connections(default_connections)
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
        safe_users[username] = {
            'role': user_data['role'],
            'created_at': user_data.get('created_at', '')
        }
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
    
    users[username] = {
        'password': hash_password(password),
        'role': role,
        'created_at': datetime.now().isoformat()
    }
    
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
        return jsonify({'success': True})
    
    return jsonify({'error': 'Usuário não encontrado'}), 404

# ==================== HTML_TEMPLATE COMPLETO ====================
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
        @media (max-width: 768px) {
            :root {
                --palette-width: 220px;
                --properties-width: 260px;
            }
        }
        @media (max-width: 576px) {
            :root {
                --palette-width: 180px;
                --properties-width: 240px;
            }
        }
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
        @media (max-width: 768px) { .toolbar { margin-left: 50px; } }
        .btn { padding: 6px 12px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; font-size: 12px; display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
        @media (max-width: 768px) { .btn { padding: 4px 8px; font-size: 10px; } .toolbar { padding: 5px 10px; gap: 5px; } }
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
        @media (max-width: 768px) { .main-container { height: calc(100vh - 48px); } }
        
        .palette { width: var(--palette-width); background: var(--bg-tertiary); color: var(--text-primary); overflow-y: auto; padding: 10px; border-right: 2px solid var(--border-color); transition: width 0.3s ease, min-width 0.3s ease; position: relative; flex-shrink: 0; }
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
            .component, .shape-btn, .btn, .category-actions button, .component-actions button {
                cursor: pointer;
                -webkit-tap-highlight-color: transparent;
            }
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
    
    <!-- Tela de introdução com slides -->
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
    
    <!-- Badge do desenvolvedor -->
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
        
        const devImageBase64 = '""" + dev_image_data + """';
        
        // ==================== CONEXÕES PADRÃO ====================
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
        
        // ==================== VARIÁVEIS DE CONEXÃO PERSONALIZADAS ====================
        let cableColors = JSON.parse(JSON.stringify(defaultCableColors));
        let customConnections = [];
        let connectionCategories = {};
        let customCategoryIcons = {};
        let customConnectionIcons = {};
        
        // ==================== STORAGE KEYS ====================
        const STORAGE_KEYS = {
            ICON_SIZE: 'projetize_icon_size',
            CANVAS_ZOOM: 'projetize_canvas_zoom',
            COMPONENTS: (user) => `projetize_${user}_components`,
            CONNECTIONS_DATA: (user) => `projetize_${user}_connections`,
            SHAPES: (user) => `projetize_${user}_shapes`,
            BACKGROUND: (user) => `projetize_${user}_background`
        };
        
        // ==================== CATEGORIAS E DISPOSITIVOS ====================
        let categories = {};
        let customDevices = [];
        let defaultCategories = {};
        
        // ==================== FUNÇÕES DE CARREGAMENTO ====================
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
                    const config = data.config;
                    connectionCategories = config;
                    for (const [catName, catData] of Object.entries(config)) {
                        for (const conn of catData.connections) {
                            const key = getConnectionKey(conn.name);
                            cableColors[key] = {
                                color: conn.color,
                                name: conn.name,
                                icon: conn.icon,
                                type: conn.type,
                                speed: conn.speed || 'N/A',
                                desc: conn.desc || '',
                                animation: conn.animation || null,
                                iconFile: conn.iconFile || null
                            };
                        }
                    }
                }
            } catch(e) { console.error(e); }
        }
        
        async function loadUserData() {
            const savedIconSize = localStorage.getItem(STORAGE_KEYS.ICON_SIZE);
            if(savedIconSize) iconSize = parseInt(savedIconSize);
            
            const savedZoom = localStorage.getItem(STORAGE_KEYS.CANVAS_ZOOM);
            if(savedZoom) zoom = parseFloat(savedZoom);
            
            // As categorias e conexões agora SEMPRE vêm do servidor.
            // O defaultCategories e connectionCategories já foram preenchidos em doLogin()
            categories = JSON.parse(JSON.stringify(defaultCategories));
            
            // Carregar dispositivos customizados do servidor
            try {
                const devicesRes = await fetch('/api/load_custom_devices');
                const devicesData = await devicesRes.json();
                if (devicesData.success) customDevices = devicesData.devices;
            } catch(e) { console.error("Erro ao carregar custom devices:", e); }
            
            // Não carregar categorias, customDevices e conexões do localStorage
            // para evitar que dados antigos sobrescrevam a configuração global.
            
            if (currentUser) {
                const savedComponents = localStorage.getItem(STORAGE_KEYS.COMPONENTS(currentUser));
                const savedConnectionsData = localStorage.getItem(STORAGE_KEYS.CONNECTIONS_DATA(currentUser));
                const savedShapes = localStorage.getItem(STORAGE_KEYS.SHAPES(currentUser));
                const savedBackground = localStorage.getItem(STORAGE_KEYS.BACKGROUND(currentUser));
                
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
                        backgroundImageObj.onload = function() {
                            if(backgroundWidth === 0) {
                                backgroundWidth = backgroundImageObj.width;
                                backgroundHeight = backgroundImageObj.height;
                                backgroundX = canvas.width/2 - backgroundWidth/2;
                                backgroundY = canvas.height/2 - backgroundHeight/2;
                            }
                        };
                        backgroundImageObj.src = backgroundImage;
                    }
                }
            }
            
            renderPalette();
            renderConnectionsPalette();
            applyZoomToCanvas();
        }
        
        function saveUserData() {
            // O localStorage agora é usado APENAS para dados do projeto do usuário.
            localStorage.setItem(STORAGE_KEYS.ICON_SIZE, iconSize);
            localStorage.setItem(STORAGE_KEYS.CANVAS_ZOOM, zoom);
            
            if (currentUser) {
                localStorage.setItem(STORAGE_KEYS.COMPONENTS(currentUser), JSON.stringify(components));
                localStorage.setItem(STORAGE_KEYS.CONNECTIONS_DATA(currentUser), JSON.stringify(connections));
                localStorage.setItem(STORAGE_KEYS.SHAPES(currentUser), JSON.stringify(shapes));
                localStorage.setItem(STORAGE_KEYS.BACKGROUND(currentUser), JSON.stringify({
                    url: backgroundImage,
                    opacity: backgroundOpacity,
                    width: backgroundWidth,
                    height: backgroundHeight,
                    x: backgroundX,
                    y: backgroundY
                }));
            }
        }
        
        // ==================== FUNÇÃO PARA SALVAR NO SERVIDOR ====================
        async function saveGlobalLibrary() {
            if (userRole !== 'admin' && userRole !== 'master') return;
            try {
                await fetch('/api/save_global_categories', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ categories: categories })
                });
                await fetch('/api/save_global_connections', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ connections: connectionCategories })
                });
                await fetch('/api/save_global_custom_devices', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ devices: customDevices })
                });
                console.log("✅ Biblioteca global salva com sucesso.");
            } catch(e) {
                console.error("Erro ao salvar biblioteca global:", e);
                showToast('❌ Erro ao salvar alterações globais.');
            }
        }
        
        // ==================== FUNÇÕES DE CONEXÃO PERSONALIZADAS ====================
        function getConnectionKey(name) {
            return name.toLowerCase().replace(/[^a-z0-9]/g, '');
        }
        
        function getIconUrl(filename) {
            if (!filename) return null;
            return `/uploads/icons/${filename}`;
        }
        
        function renderConnectionIcon(conn) {
            if (conn.iconFile) {
                return `<img src="/uploads/icons/${conn.iconFile}" style="width:24px;height:24px;object-fit:contain;">`;
            }
            return conn.icon || '🔌';
        }
        
        function addCustomConnection(category, connData) {
            if (!connectionCategories[category]) {
                connectionCategories[category] = { icon: '🔌', connections: [] };
            }
            const key = getConnectionKey(connData.name);
            connectionCategories[category].connections.push(connData);
            
            cableColors[key] = {
                color: connData.color,
                name: connData.name,
                icon: connData.icon,
                type: connData.type || 'cable',
                speed: connData.speed || 'N/A',
                desc: connData.desc || '',
                animation: connData.animation || null,
                iconFile: connData.iconFile || null
            };
            
            saveUserData();
            saveGlobalLibrary(); // Adicionado
            renderConnectionsPalette();
            showToast(`✅ Conexão "${connData.name}" adicionada!`);
        }
        
        function deleteCustomConnection(category, idx) {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem excluir conexões');
                return;
            }
            
            if (confirm('Deseja excluir esta conexão?')) {
                const conn = connectionCategories[category].connections[idx];
                const key = getConnectionKey(conn.name);
                delete cableColors[key];
                connectionCategories[category].connections.splice(idx, 1);
                
                if (connectionCategories[category].connections.length === 0) {
                    delete connectionCategories[category];
                }
                
                saveUserData();
                saveGlobalLibrary(); // Adicionado
                renderConnectionsPalette();
                showToast(`🗑 Conexão removida!`);
            }
        }
        
        function editCustomConnection(category, idx) {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem editar conexões');
                return;
            }
            
            const conn = connectionCategories[category].connections[idx];
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">✏️ Editar Conexão</h3>
                    <input type="text" id="connName" value="${conn.name}" placeholder="Nome da conexão">
                    <input type="text" id="connIcon" value="${conn.icon || '🔌'}" placeholder="Ícone (emoji)">
                    <div class="property-group">
                        <label>OU Imagem personalizada (permanente)</label>
                        <input type="file" id="connIconImage" accept="image/*">
                        <div class="image-preview" id="connIconPreview">
                            ${conn.iconFile ? `<img src="/uploads/icons/${conn.iconFile}" style="max-width:50px;max-height:50px;">` : ''}
                        </div>
                    </div>
                    <input type="color" id="connColor" value="${conn.color || '#005f99'}">
                    <input type="text" id="connSpeed" value="${conn.speed || 'N/A'}" placeholder="Velocidade">
                    <input type="text" id="connDesc" value="${conn.desc || ''}" placeholder="Descrição">
                    <select id="connType">
                        <option value="cable" ${conn.type === 'cable' ? 'selected' : ''}>Cabeado</option>
                        <option value="wireless" ${conn.type === 'wireless' ? 'selected' : ''}>Sem Fio</option>
                    </select>
                    <select id="connAnimation">
                        <option value="">Nenhuma</option>
                        <option value="wave" ${conn.animation === 'wave' ? 'selected' : ''}>Ondas</option>
                        <option value="packet" ${conn.animation === 'packet' ? 'selected' : ''}>Pacotes</option>
                    </select>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="updateCustomConnection('${category.replace(/'/g, "\\'")}', ${idx})">Salvar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            
            // Upload de imagem para ícone da conexão
            const imageInput = document.getElementById('connIconImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('connIconPreview');
                        if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;max-height:50px;">`;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'connection' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempConnectionIconFile = data.filename;
                            showToast('✅ Ícone da conexão enviado com sucesso!');
                        }
                    }
                };
            }
        }
        
        window.updateCustomConnection = async (category, idx) => {
            const name = document.getElementById('connName').value;
            const icon = document.getElementById('connIcon').value;
            const color = document.getElementById('connColor').value;
            const speed = document.getElementById('connSpeed').value;
            const desc = document.getElementById('connDesc').value;
            const type = document.getElementById('connType').value;
            const animation = document.getElementById('connAnimation').value;
            const iconFile = window.tempConnectionIconFile || connectionCategories[category].connections[idx].iconFile;
            
            if (!name) { showToast('Digite um nome para a conexão'); return; }
            
            const oldKey = getConnectionKey(connectionCategories[category].connections[idx].name);
            delete cableColors[oldKey];
            
            const connData = { 
                name, 
                icon: icon || '🔌', 
                color, 
                speed, 
                desc, 
                type, 
                animation: animation || null,
                iconFile: iconFile
            };
            connectionCategories[category].connections[idx] = connData;
            
            const newKey = getConnectionKey(name);
            cableColors[newKey] = {
                color: color,
                name: name,
                icon: icon || '🔌',
                type: type,
                speed: speed || 'N/A',
                desc: desc || '',
                animation: animation || null,
                iconFile: iconFile
            };
            
            window.tempConnectionIconFile = null;
            saveUserData();
            saveGlobalLibrary(); // Adicionado
            closeModal();
            renderConnectionsPalette();
            showToast(`✅ Conexão atualizada!`);
        };
        
        // ==================== FUNÇÕES DE ÍCONES PARA CATEGORIAS ====================
        function openCategoryIconModal(catName) {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem alterar ícones de categorias');
                return;
            }
            
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🎨 Ícone da Categoria: ${catName}</h3>
                    <p>Escolha um novo ícone para a categoria. Isso será visível para todos os usuários.</p>
                    <div class="property-group">
                        <label>Use um emoji</label>
                        <input type="text" id="catEmoji" placeholder="🎥" value="${categories[catName]?.icon || '📁'}" maxlength="2">
                    </div>
                    <div class="property-group">
                        <label>OU faça upload de uma imagem</label>
                        <input type="file" id="catIconImage" accept="image/*">
                        <div class="image-preview" id="catIconPreview">
                            ${categories[catName]?.iconFile ? `<img src="/uploads/icons/${categories[catName].iconFile}" style="max-width:50px;max-height:50px;">` : ''}
                        </div>
                    </div>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="applyCategoryIcon('${catName.replace(/'/g, "\\'")}')">✅ Aplicar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            window.currentCategory = catName;
            
            // Upload de imagem para ícone da categoria
            const imageInput = document.getElementById('catIconImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('catIconPreview');
                        if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;max-height:50px;">`;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'category' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempCategoryIconFile = data.filename;
                            showToast('✅ Ícone da categoria enviado com sucesso!');
                        }
                    }
                };
            }
        }
        
        window.applyCategoryIcon = async (catName) => {
            const emoji = document.getElementById('catEmoji').value;
            const iconFile = window.tempCategoryIconFile || categories[catName]?.iconFile || null;
            
            if (emoji) {
                categories[catName].icon = emoji;
                categories[catName].iconFile = null;
            } else if (iconFile) {
                categories[catName].iconFile = iconFile;
                categories[catName].icon = null;
            }
            
            window.tempCategoryIconFile = null;
            saveUserData();
            await saveGlobalLibrary(); // Adicionado
            closeModal();
            renderPalette();
            showToast(`✅ Ícone da categoria "${catName}" atualizado!`);
        };
        
        // ==================== FUNÇÕES DE ÍCONES PARA CONEXÕES (via menu de contexto) ====================
        function openConnectionIconModal(category, idx) {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem alterar ícones de conexões');
                return;
            }
            
            const conn = connectionCategories[category].connections[idx];
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🎨 Ícone da Conexão: ${conn.name}</h3>
                    <p>Escolha um novo ícone para a conexão. Isso será visível para todos os usuários.</p>
                    <div class="property-group">
                        <label>Use um emoji</label>
                        <input type="text" id="connEmoji" placeholder="🔌" value="${conn.icon || '🔌'}" maxlength="2">
                    </div>
                    <div class="property-group">
                        <label>OU faça upload de uma imagem</label>
                        <input type="file" id="connIconImage" accept="image/*">
                        <div class="image-preview" id="connIconPreview">
                            ${conn.iconFile ? `<img src="/uploads/icons/${conn.iconFile}" style="max-width:50px;max-height:50px;">` : ''}
                        </div>
                    </div>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="applyConnectionIcon('${category.replace(/'/g, "\\'")}', ${idx})">✅ Aplicar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            window.currentConnCategory = category;
            window.currentConnIdx = idx;
            
            // Upload de imagem para ícone da conexão
            const imageInput = document.getElementById('connIconImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('connIconPreview');
                        if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;max-height:50px;">`;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'connection' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempConnectionIconFile = data.filename;
                            showToast('✅ Ícone da conexão enviado com sucesso!');
                        }
                    }
                };
            }
        }
        
        window.applyConnectionIcon = async (category, idx) => {
            const emoji = document.getElementById('connEmoji').value;
            const iconFile = window.tempConnectionIconFile || connectionCategories[category].connections[idx].iconFile || null;
            const conn = connectionCategories[category].connections[idx];
            
            if (emoji) {
                conn.icon = emoji;
                conn.iconFile = null;
            } else if (iconFile) {
                conn.iconFile = iconFile;
                conn.icon = null;
            }
            
            // Atualizar cableColors também
            const key = getConnectionKey(conn.name);
            if (cableColors[key]) {
                cableColors[key].icon = conn.icon || '🔌';
                cableColors[key].iconFile = conn.iconFile;
            }
            
            window.tempConnectionIconFile = null;
            saveUserData();
            await saveGlobalLibrary(); // Adicionado
            closeModal();
            renderConnectionsPalette();
            showToast(`✅ Ícone da conexão "${conn.name}" atualizado!`);
        };
        
        // ==================== FUNÇÕES DE UI ====================
        function renderConnectionsPalette() {
            const container = document.getElementById('connections-container');
            if (!container) return;
            container.innerHTML = '';
            
            const allConnections = { ...connectionCategories };
            
            customConnections.forEach(conn => {
                if (!allConnections['Personalizadas']) {
                    allConnections['Personalizadas'] = { icon: '🔌', connections: [] };
                }
                allConnections['Personalizadas'].connections.push(conn);
            });
            
            for (const [catName, catData] of Object.entries(allConnections)) {
                if (!catData.connections || catData.connections.length === 0) continue;
                
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';
                categoryDiv.innerHTML = `
                    <div class="category-header">
                        <h3>${catData.icon || '🔌'} ${catName}</h3>
                        ${(userRole === 'admin' || userRole === 'master') ? `
                            <div class="category-actions">
                                <button onclick="addConnectionToCategory('${catName.replace(/'/g, "\\'")}')" title="Adicionar">➕</button>
                            </div>
                        ` : ''}
                    </div>
                    <div id="conn-category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>
                `;
                container.appendChild(categoryDiv);
                
                const connContainer = document.getElementById(`conn-category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
                catData.connections.forEach((conn, idx) => {
                    const connEl = document.createElement('div');
                    connEl.className = 'component';
                    connEl.style.cursor = 'pointer';
                    connEl.onclick = () => {
                        selectedConnectionType = getConnectionKey(conn.name);
                        showToast(`✅ Tipo de conexão selecionado: ${conn.name}`);
                    };
                    connEl.innerHTML = `
                        <div class="component-icon">
                            ${renderConnectionIcon(conn)}
                        </div>
                        <div class="component-info">
                            <div class="component-name">${conn.name}</div>
                            <div class="component-desc">${conn.desc || conn.speed || ''}</div>
                        </div>
                        ${(userRole === 'admin' || userRole === 'master') ? `
                            <div class="component-actions">
                                <button onclick="editCustomConnection('${catName.replace(/'/g, "\\'")}', ${idx})" title="Editar">✏️</button>
                                <button onclick="openConnectionIconModal('${catName.replace(/'/g, "\\'")}', ${idx})" title="Alterar Ícone">🎨</button>
                                <button onclick="deleteCustomConnection('${catName.replace(/'/g, "\\'")}', ${idx})" title="Excluir">🗑</button>
                            </div>
                        ` : ''}
                    `;
                    connContainer.appendChild(connEl);
                });
            }
        }
        
        function renderDeviceIcon(device) {
            if(device.iconFile) return `<img src="/uploads/icons/${device.iconFile}" style="width:24px;height:24px;object-fit:contain;">`;
            return device.icon || '📦';
        }
        
        function renderPalette() {
            const container = document.getElementById('categories-container');
            if(!container) return;
            container.innerHTML = '';
            
            for(const [catName, catData] of Object.entries(categories)) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';
                const catIcon = catData.iconFile ? `<img src="/uploads/icons/${catData.iconFile}" style="width:16px;height:16px;">` : (catData.icon || '📁');
                categoryDiv.innerHTML = `
                    <div class="category-header">
                        <h3>${catIcon} ${catName}</h3>
                        ${(userRole === 'admin' || userRole === 'master') ? `
                            <div class="category-actions">
                                <button onclick="editCategory('${catName.replace(/'/g, "\\'")}')" title="Editar">✏️</button>
                                <button onclick="openCategoryIconModal('${catName.replace(/'/g, "\\'")}')" title="Alterar Ícone">🎨</button>
                                <button onclick="deleteCategory('${catName.replace(/'/g, "\\'")}')" title="Excluir">🗑</button>
                                <button onclick="addDeviceToCategory('${catName.replace(/'/g, "\\'")}')" title="Adicionar">➕</button>
                            </div>
                        ` : ''}
                    </div>
                    <div id="category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>
                `;
                container.appendChild(categoryDiv);
                
                const devicesContainer = document.getElementById(`category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
                if (catData.devices) {
                    catData.devices.forEach((device, idx) => {
                        const deviceEl = document.createElement('div');
                        deviceEl.className = 'component';
                        deviceEl.setAttribute('draggable', 'true');
                        deviceEl.setAttribute('data-device-name', device.name);
                        deviceEl.setAttribute('data-device-icon', device.icon);
                        deviceEl.setAttribute('data-device-type', device.type);
                        deviceEl.setAttribute('data-device-subtype', device.subtype || '');
                        deviceEl.setAttribute('data-device-color', device.color);
                        deviceEl.setAttribute('data-device-iconfile', device.iconFile || '');
                        
                        if (!device.id) device.id = Date.now() + idx;
                        
                        deviceEl.innerHTML = `
                            <div class="component-icon">${renderDeviceIcon(device)}</div>
                            <div class="component-info">
                                <div class="component-name">${device.name}</div>
                                <div class="component-desc">${device.desc || ''}</div>
                            </div>
                            ${(userRole === 'admin' || userRole === 'master') ? `
                                <div class="component-actions">
                                    <button onclick="editDevice('${catName.replace(/'/g, "\\'")}', ${idx})" title="Editar">✏️</button>
                                    <button onclick="openDeviceIconModal('${catName.replace(/'/g, "\\'")}', ${idx})" title="Alterar Ícone">🎨</button>
                                    <button onclick="deleteDevice('${catName.replace(/'/g, "\\'")}', ${idx})" title="Excluir">🗑</button>
                                </div>
                            ` : ''}
                        `;
                        deviceEl.addEventListener('dragstart', (e) => {
                            e.dataTransfer.setData('text/plain', JSON.stringify({
                                name: device.name,
                                icon: device.icon,
                                type: device.type,
                                subtype: device.subtype || '',
                                color: device.color,
                                iconFile: device.iconFile || null
                            }));
                        });
                        devicesContainer.appendChild(deviceEl);
                    });
                }
            }
            
            if(customDevices.length > 0) {
                const customDiv = document.createElement('div');
                customDiv.className = 'category';
                customDiv.innerHTML = `
                    <div class="category-header">
                        <h3>🎨 Personalizados</h3>
                        ${(userRole === 'admin' || userRole === 'master') ? `
                            <div class="category-actions">
                                <button onclick="openAddDeviceModal()" title="Adicionar">➕</button>
                            </div>
                        ` : ''}
                    </div>
                    <div id="custom-devices-container"></div>
                `;
                container.appendChild(customDiv);
                
                const customContainer = document.getElementById('custom-devices-container');
                customDevices.forEach((device, idx) => {
                    const deviceEl = document.createElement('div');
                    deviceEl.className = 'component';
                    deviceEl.setAttribute('draggable', 'true');
                    deviceEl.innerHTML = `
                        <div class="component-icon">${renderDeviceIcon(device)}</div>
                        <div class="component-info">
                            <div class="component-name">${device.name}</div>
                            <div class="component-desc">${device.desc || 'Personalizado'}</div>
                        </div>
                        ${(userRole === 'admin' || userRole === 'master') ? `
                            <div class="component-actions">
                                <button onclick="editCustomDevice(${idx})" title="Editar">✏️</button>
                                <button onclick="openCustomDeviceIconModal(${idx})" title="Alterar Ícone">🎨</button>
                                <button onclick="deleteCustomDevice(${idx})" title="Excluir">🗑</button>
                            </div>
                        ` : ''}
                    `;
                    deviceEl.addEventListener('dragstart', (e) => {
                        e.dataTransfer.setData('text/plain', JSON.stringify({
                            name: device.name,
                            icon: device.icon,
                            type: device.type || 'custom',
                            subtype: 'custom',
                            color: device.color || '#005f99',
                            iconFile: device.iconFile || null
                        }));
                    });
                    customContainer.appendChild(deviceEl);
                });
            }
        }
        
        // ==================== FUNÇÕES DE ÍCONES PARA DISPOSITIVOS ====================
        function openDeviceIconModal(catName, idx) {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem alterar ícones de dispositivos');
                return;
            }
            
            const device = categories[catName].devices[idx];
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🎨 Ícone do Dispositivo: ${device.name}</h3>
                    <p>Escolha um novo ícone para o dispositivo. Isso será visível para todos os usuários.</p>
                    <div class="property-group">
                        <label>Use um emoji</label>
                        <input type="text" id="devEmoji" placeholder="📹" value="${device.icon || '📦'}" maxlength="2">
                    </div>
                    <div class="property-group">
                        <label>OU faça upload de uma imagem</label>
                        <input type="file" id="devIconImage" accept="image/*">
                        <div class="image-preview" id="devIconPreview">
                            ${device.iconFile ? `<img src="/uploads/icons/${device.iconFile}" style="max-width:50px;max-height:50px;">` : ''}
                        </div>
                    </div>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="applyDeviceIcon('${catName.replace(/'/g, "\\'")}', ${idx})">✅ Aplicar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            window.currentDeviceCat = catName;
            window.currentDeviceIdx = idx;
            
            const imageInput = document.getElementById('devIconImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devIconPreview');
                        if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;max-height:50px;">`;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'equipment' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempDeviceIconFile = data.filename;
                            showToast('✅ Ícone do dispositivo enviado com sucesso!');
                        }
                    }
                };
            }
        }
        
        window.applyDeviceIcon = async (catName, idx) => {
            const emoji = document.getElementById('devEmoji').value;
            const iconFile = window.tempDeviceIconFile || categories[catName].devices[idx].iconFile || null;
            const device = categories[catName].devices[idx];
            
            if (emoji) {
                device.icon = emoji;
                device.iconFile = null;
            } else if (iconFile) {
                device.iconFile = iconFile;
                device.icon = null;
            }
            
            window.tempDeviceIconFile = null;
            saveUserData();
            await saveGlobalLibrary(); // Adicionado
            closeModal();
            renderPalette();
            showToast(`✅ Ícone do dispositivo "${device.name}" atualizado!`);
        };
        
        function openCustomDeviceIconModal(idx) {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem alterar ícones de dispositivos');
                return;
            }
            
            const device = customDevices[idx];
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🎨 Ícone do Dispositivo: ${device.name}</h3>
                    <p>Escolha um novo ícone para o dispositivo. Isso será visível para todos os usuários.</p>
                    <div class="property-group">
                        <label>Use um emoji</label>
                        <input type="text" id="devEmoji" placeholder="📹" value="${device.icon || '📦'}" maxlength="2">
                    </div>
                    <div class="property-group">
                        <label>OU faça upload de uma imagem</label>
                        <input type="file" id="devIconImage" accept="image/*">
                        <div class="image-preview" id="devIconPreview">
                            ${device.iconFile ? `<img src="/uploads/icons/${device.iconFile}" style="max-width:50px;max-height:50px;">` : ''}
                        </div>
                    </div>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="applyCustomDeviceIcon(${idx})">✅ Aplicar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            window.currentCustomDeviceIdx = idx;
            
            const imageInput = document.getElementById('devIconImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devIconPreview');
                        if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;max-height:50px;">`;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'equipment' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempDeviceIconFile = data.filename;
                            showToast('✅ Ícone do dispositivo enviado com sucesso!');
                        }
                    }
                };
            }
        }
        
        window.applyCustomDeviceIcon = async (idx) => {
            const emoji = document.getElementById('devEmoji').value;
            const iconFile = window.tempDeviceIconFile || customDevices[idx].iconFile || null;
            const device = customDevices[idx];
            
            if (emoji) {
                device.icon = emoji;
                device.iconFile = null;
            } else if (iconFile) {
                device.iconFile = iconFile;
                device.icon = null;
            }
            
            window.tempDeviceIconFile = null;
            saveUserData();
            await saveGlobalLibrary(); // Adicionado
            closeModal();
            renderPalette();
            showToast(`✅ Ícone do dispositivo "${device.name}" atualizado!`);
        };
        
        // ==================== FUNÇÕES DE ZOOM E TOOLBAR ====================
        function applyZoomToCanvas() {
            canvas.style.transform = `scale(${zoom})`;
            canvas.style.transformOrigin = '0 0';
        }
        
        function iconZoomIn() { iconSize = Math.min(iconSize + 4, 80); saveUserData(); showToast(`🔍 Tamanho do ícone: ${iconSize}px`); }
        function iconZoomOut() { iconSize = Math.max(iconSize - 4, 20); saveUserData(); showToast(`🔍 Tamanho do ícone: ${iconSize}px`); }
        function resetIconSize() { iconSize = 36; saveUserData(); showToast(`🔄 Tamanho do ícone restaurado: ${iconSize}px`); }
        
        function zoomIn() { zoom = Math.min(zoom + 0.1, 3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
        function zoomOut() { zoom = Math.max(zoom - 0.1, 0.3); applyZoomToCanvas(); saveUserData(); showToast(`🔍 Zoom: ${Math.round(zoom * 100)}%`); }
        function resetZoom() { zoom = 1; applyZoomToCanvas(); saveUserData(); showToast(`🔄 Zoom restaurado: 100%`); }
        
        // ==================== FUNÇÕES DE TOAST E MODAL ====================
        function showToast(message) {
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = message;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }
        
        function closeModal() {
            if(window.currentModal) {
                document.body.removeChild(window.currentModal);
                window.currentModal = null;
            }
        }
        
        // ==================== FUNÇÕES DE DESENHO ====================
        function drawGrid() {
            if(!showGrid) return;
            const step = 50;
            ctx.save();
            ctx.strokeStyle = '#e0e0e0';
            ctx.lineWidth = 0.5;
            for(let x=0; x<canvas.width; x+=step) {
                ctx.beginPath();
                ctx.moveTo(x,0);
                ctx.lineTo(x,canvas.height);
                ctx.stroke();
            }
            for(let y=0; y<canvas.height; y+=step) {
                ctx.beginPath();
                ctx.moveTo(0,y);
                ctx.lineTo(canvas.width,y);
                ctx.stroke();
            }
            ctx.restore();
        }
        
        function drawBackground() {
            if(backgroundImageObj && backgroundImageObj.complete && backgroundImageObj.src && backgroundWidth > 0 && backgroundHeight > 0) {
                ctx.save();
                ctx.globalAlpha = backgroundOpacity;
                ctx.drawImage(backgroundImageObj, backgroundX, backgroundY, backgroundWidth, backgroundHeight);
                ctx.globalAlpha = 1;
                
                if(isBackgroundSelected) {
                    ctx.strokeStyle = '#005f99';
                    ctx.lineWidth = 3;
                    ctx.setLineDash([8, 6]);
                    ctx.strokeRect(backgroundX, backgroundY, backgroundWidth, backgroundHeight);
                    ctx.setLineDash([]);
                    
                    const handleSize = 10;
                    const handles = [
                        {x: backgroundX, y: backgroundY},
                        {x: backgroundX + backgroundWidth, y: backgroundY},
                        {x: backgroundX, y: backgroundY + backgroundHeight},
                        {x: backgroundX + backgroundWidth, y: backgroundY + backgroundHeight}
                    ];
                    handles.forEach(h => {
                        ctx.fillStyle = '#005f99';
                        ctx.fillRect(h.x - handleSize/2, h.y - handleSize/2, handleSize, handleSize);
                        ctx.fillStyle = 'white';
                        ctx.fillRect(h.x - handleSize/3, h.y - handleSize/3, handleSize/1.5, handleSize/1.5);
                    });
                }
                ctx.restore();
            }
        }
        
        function drawFieldOfView(cam) {
            if(!cam.angle) cam.angle = 0;
            if(!cam.fov) cam.fov = 80;
            const angleRad = cam.angle * Math.PI / 180;
            const fovRad = cam.fov * Math.PI / 180;
            const distance = 100;
            const leftAngle = angleRad - fovRad/2;
            const rightAngle = angleRad + fovRad/2;
            const x1 = cam.x + Math.cos(leftAngle) * distance;
            const y1 = cam.y + Math.sin(leftAngle) * distance;
            const x2 = cam.x + Math.cos(rightAngle) * distance;
            const y2 = cam.y + Math.sin(rightAngle) * distance;
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
            const cx = cam.x + Math.cos(angleRad) * distance;
            const cy = cam.y + Math.sin(angleRad) * distance;
            ctx.beginPath();
            ctx.moveTo(cam.x, cam.y);
            ctx.lineTo(cx, cy);
            ctx.strokeStyle = '#ffaa00';
            ctx.setLineDash([5,5]);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.arc(cx, cy, 6, 0, 2*Math.PI);
            ctx.fillStyle = '#ffaa00';
            ctx.fill();
            ctx.fillStyle = '#000';
            ctx.font = `bold ${10}px Arial`;
            ctx.fillText('↻', cx-3, cy+3);
            ctx.restore();
        }
        
        function drawSensorAnimation(x, y, time) {
            const pulseCount = 3;
            const baseRadius = 25;
            for(let i = 0; i < pulseCount; i++) {
                const delay = i * 0.5;
                const progress = (time + delay) % 1;
                const radius = baseRadius + (progress * 30);
                const opacity = 0.5 * (1 - progress);
                ctx.save();
                ctx.beginPath();
                ctx.arc(x, y, radius, 0, 2 * Math.PI);
                ctx.strokeStyle = `rgba(0, 95, 153, ${opacity})`;
                ctx.lineWidth = 2;
                ctx.stroke();
                ctx.restore();
            }
        }
        
        function drawWirelessAnimationOnLine(x1, y1, x2, y2, type, progress) {
            const cableInfo = cableColors[type];
            if (!cableInfo || cableInfo.type !== 'wireless') return;
            
            const t = progress;
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            
            ctx.save();
            if (cableInfo.animation === 'wave') {
                ctx.beginPath();
                ctx.arc(x, y, 6, 0, 2 * Math.PI);
                ctx.fillStyle = cableInfo.color;
                ctx.shadowBlur = 8;
                ctx.shadowColor = cableInfo.color;
                ctx.fill();
                ctx.beginPath();
                ctx.arc(x, y, 10, 0, 2 * Math.PI);
                ctx.strokeStyle = cableInfo.color;
                ctx.lineWidth = 1.5;
                ctx.stroke();
            } else {
                ctx.fillStyle = cableInfo.color;
                ctx.shadowBlur = 6;
                ctx.shadowColor = cableInfo.color;
                ctx.fillRect(x - 3, y - 3, 6, 6);
            }
            ctx.shadowBlur = 0;
            ctx.restore();
        }
        
        function drawConnections() {
            connections.forEach((conn, idx) => {
                const fromComp = components.find(c => c.id === conn.from);
                const toComp = components.find(c => c.id === conn.to);
                if(!fromComp || !toComp) return;
                
                const cableInfo = cableColors[conn.type] || cableColors['cat6'];
                if (!cableInfo) return;
                
                const isWireless = cableInfo.type === 'wireless';
                const isSelected = (selectedConnectionIndex === idx);
                
                ctx.save();
                if(isWireless) {
                    ctx.setLineDash(cableInfo.dashPattern || [10, 8]);
                    ctx.strokeStyle = cableInfo.color;
                    ctx.lineWidth = isSelected ? 4 : 2;
                    ctx.beginPath();
                    ctx.moveTo(fromComp.x, fromComp.y);
                    ctx.lineTo(toComp.x, toComp.y);
                    ctx.stroke();
                    
                    if (cableInfo.animation === 'wave') {
                        for(let i = 0; i < 2; i++) {
                            const t = (trafficAnimation + i * 0.4) % 1;
                            drawWirelessAnimationOnLine(fromComp.x, fromComp.y, toComp.x, toComp.y, conn.type, t);
                        }
                    } else {
                        for(let i = 0; i < 3; i++) {
                            const t = (trafficAnimation + i * 0.25) % 1;
                            drawWirelessAnimationOnLine(fromComp.x, fromComp.y, toComp.x, toComp.y, conn.type, t);
                        }
                    }
                } else {
                    ctx.setLineDash([]);
                    ctx.beginPath();
                    ctx.moveTo(fromComp.x, fromComp.y);
                    ctx.lineTo(toComp.x, toComp.y);
                    ctx.strokeStyle = cableInfo.color;
                    ctx.lineWidth = isSelected ? 4 : 2;
                    ctx.stroke();
                    
                    const t = trafficAnimation;
                    const x = fromComp.x + (toComp.x - fromComp.x) * t;
                    const y = fromComp.y + (toComp.y - fromComp.y) * t;
                    ctx.beginPath();
                    ctx.arc(x, y, 4, 0, 2*Math.PI);
                    ctx.fillStyle = cableInfo.color;
                    ctx.fill();
                }
                
                ctx.fillStyle = '#6c757d';
                ctx.font = `${9}px Arial`;
                const iconDisplay = cableInfo.iconFile ? '🖼️' : cableInfo.icon;
                ctx.fillText(`${iconDisplay} ${cableInfo.name}`, (fromComp.x+toComp.x)/2 - 20, (fromComp.y+toComp.y)/2 - 5);
                
                if(isSelected) {
                    ctx.strokeStyle = '#005f99';
                    ctx.lineWidth = 2;
                    ctx.setLineDash([5, 5]);
                    ctx.beginPath();
                    ctx.moveTo(fromComp.x, fromComp.y);
                    ctx.lineTo(toComp.x, toComp.y);
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
                if(shape.rotation) {
                    ctx.translate(shape.x + (shape.type === 'door' ? 15 : 30), shape.y + (shape.type === 'door' ? 25 : 20));
                    ctx.rotate(shape.rotation * Math.PI / 180);
                    ctx.translate(-(shape.x + (shape.type === 'door' ? 15 : 30)), -(shape.y + (shape.type === 'door' ? 25 : 20)));
                }
                switch(shape.type) {
                    case 'line': ctx.beginPath(); ctx.moveTo(shape.x1, shape.y1); ctx.lineTo(shape.x2, shape.y2); ctx.stroke(); break;
                    case 'door': ctx.fillStyle = 'rgba(139, 69, 19, 0.3)'; ctx.fillRect(shape.x, shape.y, 30, 50); ctx.strokeStyle = '#8B4513'; ctx.strokeRect(shape.x, shape.y, 30, 50); ctx.beginPath(); ctx.arc(shape.x + 30, shape.y + 25, 20, -Math.PI/2, Math.PI/2); ctx.stroke(); break;
                    case 'window': ctx.fillStyle = 'rgba(135, 206, 235, 0.3)'; ctx.fillRect(shape.x, shape.y, 60, 40); ctx.strokeStyle = '#87CEEB'; ctx.strokeRect(shape.x, shape.y, 60, 40); ctx.beginPath(); ctx.moveTo(shape.x + 30, shape.y); ctx.lineTo(shape.x + 30, shape.y + 40); ctx.moveTo(shape.x, shape.y + 20); ctx.lineTo(shape.x + 60, shape.y + 20); ctx.stroke(); break;
                    case 'text': ctx.font = `${(shape.fontSize || 14)}px Arial`; ctx.fillStyle = shape.textColor || '#212529'; ctx.fillText(shape.text || 'Texto', shape.x, shape.y); break;
                }
                if(shape.rotation) ctx.setTransform(1, 0, 0, 1, 0, 0);
                if(isSelected) {
                    ctx.strokeStyle = '#005f99';
                    ctx.lineWidth = 2;
                    if(shape.type === 'line') {
                        ctx.beginPath(); ctx.moveTo(shape.x1 - 3, shape.y1 - 3); ctx.lineTo(shape.x2 + 3, shape.y2 + 3); ctx.moveTo(shape.x1 + 3, shape.y1 - 3); ctx.lineTo(shape.x2 - 3, shape.y2 + 3); ctx.stroke();
                    } else if(shape.type === 'text') {
                        ctx.strokeRect(shape.x - 5, shape.y - 12, ctx.measureText(shape.text || 'Texto').width + 10, 18);
                    } else {
                        const w = 30; const h = shape.type === 'door' ? 50 : 40;
                        ctx.strokeRect(shape.x - 3, shape.y - 3, w + 6, h + 6);
                    }
                    showShapeDeleteButton(shape);
                } else {
                    document.getElementById('deleteShapeBtn').style.display = 'none';
                }
                ctx.restore();
            });
        }
        
        function drawComponents() {
            components.forEach(comp => {
                const isSelected = selectedComponents.includes(comp);
                if(comp.type === 'sensor') drawSensorAnimation(comp.x, comp.y, sensorAnimationTime);
                
                ctx.save();
                ctx.translate(comp.x, comp.y);
                ctx.rotate((comp.rotation || 0) * Math.PI / 180);
                ctx.translate(-comp.x, -comp.y);
                
                const halfSize = iconSize / 2;
                
                if(comp.iconFile) {
                    const img = new Image();
                    img.src = `/uploads/icons/${comp.iconFile}`;
                    ctx.drawImage(img, comp.x-halfSize, comp.y-halfSize, iconSize, iconSize);
                } else if(comp.customImage && comp.customImage.startsWith('data:image')) {
                    const img = new Image();
                    img.src = comp.customImage;
                    ctx.drawImage(img, comp.x-halfSize, comp.y-halfSize, iconSize, iconSize);
                } else if(comp.customImageTemp && comp.customImageTemp.startsWith('data:image')) {
                    const img = new Image();
                    img.src = comp.customImageTemp;
                    ctx.drawImage(img, comp.x-halfSize, comp.y-halfSize, iconSize, iconSize);
                } else {
                    ctx.fillStyle = comp.color || '#005f99';
                    ctx.beginPath();
                    ctx.arc(comp.x, comp.y, iconSize/2, 0, 2*Math.PI);
                    ctx.fill();
                    ctx.fillStyle = '#fff';
                    ctx.font = `${iconSize/2}px Arial`;
                    const iconToShow = comp.customIconTemp || comp.icon || '📦';
                    ctx.fillText(iconToShow, comp.x-12, comp.y+8);
                }
                
                ctx.setTransform(1, 0, 0, 1, 0, 0);
                ctx.fillStyle = '#005f99';
                ctx.font = `${12}px Arial`;
                ctx.fillText(comp.name, comp.x-30, comp.y - (iconSize/2) - 5);
                if(comp.ip) {
                    ctx.fillStyle = '#6c757d';
                    ctx.font = `${10}px Arial`;
                    ctx.fillText(comp.ip, comp.x-25, comp.y - (iconSize/2) - 15);
                }
                
                if(isSelected) {
                    ctx.strokeStyle = '#005f99';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(comp.x - halfSize - 4, comp.y - halfSize - 4, iconSize + 8, iconSize + 8);
                    ctx.beginPath();
                    ctx.arc(comp.x + halfSize + 8, comp.y - halfSize - 8, 6, 0, 2*Math.PI);
                    ctx.fillStyle = '#005f99';
                    ctx.fill();
                    ctx.fillStyle = '#fff';
                    ctx.font = `${10}px Arial`;
                    ctx.fillText('↻', comp.x + halfSize + 5, comp.y - halfSize - 5);
                }
                if(comp.type === 'camera') drawFieldOfView(comp);
                ctx.restore();
            });
            sensorAnimationTime = (sensorAnimationTime + 0.01) % 1;
        }
        
        function drawShapePreview(start, end, type) {
            if(!start || !end) return;
            ctx.save();
            ctx.setLineDash([5, 5]);
            ctx.strokeStyle = '#005f99';
            ctx.fillStyle = 'rgba(0, 95, 153, 0.2)';
            ctx.lineWidth = 2;
            const x = Math.min(start.x, end.x);
            const y = Math.min(start.y, end.y);
            const width = Math.abs(end.x - start.x);
            switch(type) {
                case 'line': ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke(); break;
                case 'door': ctx.fillRect(end.x, end.y, 30, 50); ctx.strokeRect(end.x, end.y, 30, 50); break;
                case 'window': ctx.fillRect(x, y, width, 40); ctx.strokeRect(x, y, width, 40); break;
            }
            ctx.setLineDash([]);
            ctx.restore();
        }
        
        function drawWithBackground(whiteBg = false, hideGrid = false) {
            if(whiteBg) {
                ctx.fillStyle = '#FFFFFF';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
            } else {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                drawBackground();
            }
            if(!hideGrid && showGrid) drawGrid();
            drawShapes();
            drawConnections();
            drawComponents();
        }
        
        function draw() {
            drawWithBackground(false, false);
            if(drawingPreview && shapeStart) drawShapePreview(shapeStart, lastMousePos || shapeStart, shapeMode);
            requestAnimationFrame(draw);
        }
        draw();
        
        let lastMousePos = null;
        
        // ==================== FUNÇÕES DE MOUSE E TOQUE ====================
        function getMousePos(e) {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            let clientX, clientY;
            if (e.touches) {
                clientX = e.touches[0].clientX;
                clientY = e.touches[0].clientY;
            } else {
                clientX = e.clientX;
                clientY = e.clientY;
            }
            return { x: (clientX - rect.left) * scaleX, y: (clientY - rect.top) * scaleY };
        }
        
        function rotateComponent(comp, angle) {
            comp.rotation = (comp.rotation || 0) + angle;
        }
        
        function accessDevice(comp) {
            if(comp && comp.ip && comp.ip.trim()) {
                let url = comp.ip;
                if(!url.startsWith('http://') && !url.startsWith('https://')) url = 'http://' + url;
                if(comp.port && comp.port !== 80) url += ':' + comp.port;
                window.open(url, '_blank');
                showToast(`🌐 Abrindo ${comp.name} em ${comp.ip}`);
            } else if(comp) {
                showToast(`⚠️ O equipamento "${comp.name}" não possui IP configurado.`);
            }
        }
        
        function endShape(start, end, type) {
            if(!start || !end) return;
            const newShape = {
                id: Date.now(),
                type: type,
                fillColor: '#f8f9fa',
                strokeColor: '#005f99',
                lineWidth: 2,
                rotation: 0
            };
            switch(type) {
                case 'line':
                    newShape.x1 = start.x;
                    newShape.y1 = start.y;
                    newShape.x2 = end.x;
                    newShape.y2 = end.y;
                    break;
                case 'door':
                    newShape.x = end.x;
                    newShape.y = end.y;
                    break;
                case 'window':
                    newShape.x = Math.min(start.x, end.x);
                    newShape.y = Math.min(start.y, end.y);
                    newShape.width = Math.abs(end.x - start.x);
                    newShape.height = 40;
                    break;
                case 'text':
                    const text = prompt('Digite o texto:', 'Texto');
                    if(text) {
                        newShape.text = text;
                        newShape.x = end.x;
                        newShape.y = end.y;
                        newShape.fontSize = 14;
                        newShape.textColor = '#212529';
                    } else return;
                    break;
            }
            shapes.push(newShape);
            showToast(`✅ ${getShapeName(type)} adicionado!`);
            saveUserData();
        }
        
        function getShapeName(mode) {
            const names = { line: 'Linha', door: 'Porta', window: 'Janela', text: 'Texto' };
            return names[mode] || mode;
        }
        
        function showShapeDeleteButton(shape) {
            const btn = document.getElementById('deleteShapeBtn');
            if (btn && shape) {
                const canvasRect = canvas.getBoundingClientRect();
                let x, y;
                if (shape.type === 'line') {
                    x = (shape.x1 + shape.x2) / 2;
                    y = (shape.y1 + shape.y2) / 2;
                } else if (shape.type === 'text') {
                    x = shape.x;
                    y = shape.y;
                } else {
                    x = shape.x + 15;
                    y = shape.y + 25;
                }
                btn.style.left = (canvasRect.left + x * zoom - 60) + 'px';
                btn.style.top = (canvasRect.top + y * zoom - 30) + 'px';
                btn.style.display = 'block';
            }
        }
        
        function pointToLineDistance(px, py, x1, y1, x2, y2) {
            const A = px - x1;
            const B = py - y1;
            const C = x2 - x1;
            const D = y2 - y1;
            const dot = A * C + B * D;
            const len_sq = C * C + D * D;
            let param = -1;
            if (len_sq != 0) param = dot / len_sq;
            let xx, yy;
            if (param < 0) { xx = x1; yy = y1; }
            else if (param > 1) { xx = x2; yy = y2; }
            else { xx = x1 + param * C; yy = y1 + param * D; }
            const dx = px - xx;
            const dy = py - yy;
            return Math.sqrt(dx * dx + dy * dy);
        }
        
        function isPointNearConnection(x, y, fromComp, toComp) {
            const dist = pointToLineDistance(x, y, fromComp.x, fromComp.y, toComp.x, toComp.y);
            return dist < 12;
        }
        
        function isPointOnShape(x, y, shape) {
            if(shape.type === 'line') {
                return pointToLineDistance(x, y, shape.x1, shape.y1, shape.x2, shape.y2) < 8;
            } else if(shape.type === 'text') {
                return x >= shape.x - 5 && x <= shape.x + (shape.text?.length * 7 || 50) && y >= shape.y - 12 && y <= shape.y + 6;
            } else if(shape.type === 'door') {
                return x >= shape.x && x <= shape.x + 30 && y >= shape.y && y <= shape.y + 50;
            } else if(shape.type === 'window') {
                return x >= shape.x && x <= shape.x + 60 && y >= shape.y && y <= shape.y + 40;
            }
            return false;
        }
        
        // ==================== EVENTOS DE MOUSE ====================
        function handleStart(e) {
            e.preventDefault();
            const {x, y} = getMousePos(e);
            lastMousePos = {x, y};
            
            if(shapeMode) {
                shapeStart = {x, y};
                drawingPreview = true;
                return;
            }
            
            // Verificar clique em equipamento
            let clickedComp = null;
            for(let i=components.length-1; i>=0; i--) {
                const comp = components[i];
                if(Math.hypot(x - comp.x, y - comp.y) < iconSize/2) {
                    clickedComp = comp;
                    break;
                }
            }
            
            if(clickedComp) {
                if(e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1)) {
                    if(selectedComponents.includes(clickedComp)) {
                        selectedComponents = selectedComponents.filter(c => c !== clickedComp);
                    } else {
                        selectedComponents.push(clickedComp);
                    }
                    selectedConnectionIndex = null;
                    selectedShapes = [];
                } else {
                    selectedComponents = [clickedComp];
                    dragging = true;
                    dragOffset = {x: clickedComp.x - x, y: clickedComp.y - y};
                    isBackgroundSelected = false;
                    selectedShapes = [];
                    selectedConnectionIndex = null;
                    document.getElementById('deleteShapeBtn').style.display = 'none';
                }
                showProperties(clickedComp);
                openProperties();
                e.preventDefault();
                return;
            }
            
            // Verificar clique em forma
            let clickedShape = null;
            for(let i=shapes.length-1; i>=0; i--) {
                const shape = shapes[i];
                if(isPointOnShape(x, y, shape)) {
                    clickedShape = shape;
                    break;
                }
            }
            
            if(clickedShape) {
                if(e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1)) {
                    if(selectedShapes.includes(clickedShape)) {
                        selectedShapes = selectedShapes.filter(s => s !== clickedShape);
                    } else {
                        selectedShapes.push(clickedShape);
                    }
                    selectedConnectionIndex = null;
                    selectedComponents = [];
                } else {
                    selectedShapes = [clickedShape];
                    dragging = true;
                    if(clickedShape.type === 'line') {
                        dragOffset = {x: clickedShape.x1 - x, y: clickedShape.y1 - y};
                    } else {
                        dragOffset = {x: clickedShape.x - x, y: clickedShape.y - y};
                    }
                    selectedComponents = [];
                    selectedConnectionIndex = null;
                }
                showShapeProperties(clickedShape);
                openProperties();
                e.preventDefault();
                return;
            }
            
            // Verificar clique em conexão
            let clickedConnection = null;
            for(let i = 0; i < connections.length; i++) {
                const conn = connections[i];
                const fromComp = components.find(c => c.id === conn.from);
                const toComp = components.find(c => c.id === conn.to);
                if(fromComp && toComp) {
                    if(isPointNearConnection(x, y, fromComp, toComp)) {
                        clickedConnection = { index: i, conn: conn };
                        break;
                    }
                }
            }
            
            if(clickedConnection) {
                if(e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1)) {
                    if(selectedConnectionIndex === clickedConnection.index) {
                        selectedConnectionIndex = null;
                    } else {
                        selectedConnectionIndex = clickedConnection.index;
                    }
                    selectedComponents = [];
                    selectedShapes = [];
                } else {
                    selectedConnectionIndex = clickedConnection.index;
                    selectedComponents = [];
                    selectedShapes = [];
                }
                if(selectedConnectionIndex !== null) {
                    showConnectionProperties(selectedConnectionIndex);
                    openProperties();
                } else {
                    showProperties(null);
                    closeProperties();
                }
                e.preventDefault();
                return;
            }
            
            // Verificar imagem de fundo
            if(backgroundWidth > 0 && backgroundHeight > 0) {
                const handleSize = 12;
                const isOnNW = (x >= backgroundX - handleSize && x <= backgroundX + handleSize && y >= backgroundY - handleSize && y <= backgroundY + handleSize);
                const isOnNE = (x >= backgroundX + backgroundWidth - handleSize && x <= backgroundX + backgroundWidth + handleSize && y >= backgroundY - handleSize && y <= backgroundY + handleSize);
                const isOnSW = (x >= backgroundX - handleSize && x <= backgroundX + handleSize && y >= backgroundY + backgroundHeight - handleSize && y <= backgroundY + backgroundHeight + handleSize);
                const isOnSE = (x >= backgroundX + backgroundWidth - handleSize && x <= backgroundX + backgroundWidth + handleSize && y >= backgroundY + backgroundHeight - handleSize && y <= backgroundY + backgroundHeight + handleSize);
                
                if(isOnNW || isOnNE || isOnSW || isOnSE) {
                    if(isOnNW) { isResizingBackground = true; resizeHandle = 'nw'; }
                    else if(isOnNE) { isResizingBackground = true; resizeHandle = 'ne'; }
                    else if(isOnSW) { isResizingBackground = true; resizeHandle = 'sw'; }
                    else if(isOnSE) { isResizingBackground = true; resizeHandle = 'se'; }
                    resizeStart = {
                        x: e.clientX || e.touches[0].clientX,
                        y: e.clientY || e.touches[0].clientY,
                        width: backgroundWidth,
                        height: backgroundHeight,
                        bgX: backgroundX,
                        bgY: backgroundY
                    };
                    isBackgroundSelected = true;
                    e.preventDefault();
                    return;
                } else if(x >= backgroundX && x <= backgroundX + backgroundWidth && y >= backgroundY && y <= backgroundY + backgroundHeight) {
                    isBackgroundSelected = true;
                    isDraggingBackgroundImage = true;
                    dragBackgroundStart = {
                        x: (e.clientX || e.touches[0].clientX) - backgroundX,
                        y: (e.clientY || e.touches[0].clientY) - backgroundY
                    };
                    showToast('✅ Imagem selecionada! Arraste para mover ou redimensione pelos cantos.');
                    e.preventDefault();
                    return;
                } else {
                    isBackgroundSelected = false;
                }
            }
            
            // Botão de rotação do equipamento
            for(let comp of components) {
                if(selectedComponents.includes(comp)) {
                    const handleX = comp.x + (iconSize/2) + 8;
                    const handleY = comp.y - (iconSize/2) - 8;
                    if(Math.hypot(x - handleX, y - handleY) < 10) {
                        rotateComponent(comp, 15);
                        saveUserData();
                        return;
                    }
                }
            }
            
            // Handle de ângulo da câmera
            for(let comp of components) {
                if(comp.type === 'camera') {
                    const angleRad = comp.angle * Math.PI / 180;
                    const distance = 100;
                    const handleX = comp.x + Math.cos(angleRad) * distance;
                    const handleY = comp.y + Math.sin(angleRad) * distance;
                    if(Math.hypot(x - handleX, y - handleY) < 10) {
                        currentAngleHandle = comp;
                        return;
                    }
                }
            }
            
            if(e.ctrlKey || e.metaKey || (e.touches && e.touches.length > 1)) {
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
            
            if(e.shiftKey) {
                for(let comp of components) {
                    if(Math.hypot(x - comp.x, y - comp.y) < iconSize/2) {
                        isDrawingConnection = true;
                        connectionStart = comp;
                        return;
                    }
                }
            }
        }
        
        function handleMove(e) {
            let clientX, clientY;
            if (e.touches) {
                clientX = e.touches[0].clientX;
                clientY = e.touches[0].clientY;
            } else {
                clientX = e.clientX;
                clientY = e.clientY;
            }
            const {x, y} = getMousePos(e);
            lastMousePos = {x, y};
            
            if(isResizingBackground && resizeHandle) {
                const dx = (clientX - resizeStart.x);
                const dy = (clientY - resizeStart.y);
                let newWidth = resizeStart.width;
                let newHeight = resizeStart.height;
                let newX = resizeStart.bgX;
                let newY = resizeStart.bgY;
                
                switch(resizeHandle) {
                    case 'se':
                        newWidth = Math.max(50, resizeStart.width + dx);
                        newHeight = Math.max(50, resizeStart.height + dy);
                        break;
                    case 'sw':
                        newWidth = Math.max(50, resizeStart.width - dx);
                        newHeight = Math.max(50, resizeStart.height + dy);
                        newX = resizeStart.bgX + (resizeStart.width - newWidth);
                        break;
                    case 'ne':
                        newWidth = Math.max(50, resizeStart.width + dx);
                        newHeight = Math.max(50, resizeStart.height - dy);
                        newY = resizeStart.bgY + (resizeStart.height - newHeight);
                        break;
                    case 'nw':
                        newWidth = Math.max(50, resizeStart.width - dx);
                        newHeight = Math.max(50, resizeStart.height - dy);
                        newX = resizeStart.bgX + (resizeStart.width - newWidth);
                        newY = resizeStart.bgY + (resizeStart.height - newHeight);
                        break;
                }
                backgroundWidth = newWidth;
                backgroundHeight = newHeight;
                backgroundX = newX;
                backgroundY = newY;
                saveUserData();
                return;
            }
            
            if(isDraggingBackgroundImage) {
                backgroundX = clientX - dragBackgroundStart.x;
                backgroundY = clientY - dragBackgroundStart.y;
                saveUserData();
                return;
            }
            
            if(currentAngleHandle) {
                const angle = Math.atan2(y - currentAngleHandle.y, x - currentAngleHandle.x) * 180 / Math.PI;
                currentAngleHandle.angle = angle;
                saveUserData();
                return;
            }
            
            if(dragging && selectedComponents.length > 0) {
                const dx = (x + dragOffset.x) - selectedComponents[0].x;
                const dy = (y + dragOffset.y) - selectedComponents[0].y;
                selectedComponents.forEach(comp => {
                    comp.x += dx;
                    comp.y += dy;
                });
                dragOffset = {x: selectedComponents[0].x - x, y: selectedComponents[0].y - y};
                saveUserData();
            }
            
            if(dragging && selectedShapes.length > 0) {
                const shape = selectedShapes[0];
                let dx, dy;
                if(shape.type === 'line') {
                    dx = (x + dragOffset.x) - shape.x1;
                    dy = (y + dragOffset.y) - shape.y1;
                    shape.x1 += dx;
                    shape.y1 += dy;
                    shape.x2 += dx;
                    shape.y2 += dy;
                    dragOffset = {x: shape.x1 - x, y: shape.y1 - y};
                } else {
                    dx = (x + dragOffset.x) - shape.x;
                    dy = (y + dragOffset.y) - shape.y;
                    shape.x += dx;
                    shape.y += dy;
                    dragOffset = {x: shape.x - x, y: shape.y - y};
                }
                saveUserData();
            }
            
            if(isSelecting) updateSelection(e);
        }
        
        function handleEnd(e) {
            if(shapeMode && shapeStart) {
                const {x, y} = getMousePos(e);
                endShape(shapeStart, {x, y}, shapeMode);
                shapeStart = null;
                drawingPreview = false;
                return;
            }
            currentAngleHandle = null;
            dragging = false;
            isDraggingBackgroundImage = false;
            isResizingBackground = false;
            resizeHandle = null;
            if(isSelecting) endSelection();
            if(isDrawingConnection && connectionStart) {
                showToast('Clique em um equipamento para conectar');
            }
            isDrawingConnection = false;
            connectionStart = null;
        }
        
        function handleClick(e) {
            const {x, y} = getMousePos(e);
            if(isDrawingConnection && connectionStart) {
                for(let comp of components) {
                    if(Math.hypot(x - comp.x, y - comp.y) < iconSize/2 && comp.id !== connectionStart.id) {
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
            const {x, y} = getMousePos(e);
            
            // Menu para imagem de fundo
            if(isBackgroundSelected && backgroundWidth > 0 && backgroundHeight > 0 && x >= backgroundX && x <= backgroundX + backgroundWidth && y >= backgroundY && y <= backgroundY + backgroundHeight) {
                const menu = document.getElementById('contextMenu');
                menu.innerHTML = `
                    <div class="context-menu-item" onclick="openBackgroundModal()">✏️ Editar Imagem</div>
                    <div class="context-menu-item" onclick="removeBackground()">🗑 Remover Imagem</div>
                    <div class="context-menu-item" onclick="isBackgroundSelected=false; showToast('Imagem desselecionada');">🔲 Desselecionar</div>
                `;
                menu.style.display = 'block';
                menu.style.left = e.pageX + 'px';
                menu.style.top = e.pageY + 'px';
                setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', {once: true}), 100);
                return;
            }
            
            // Menu para equipamentos
            for(let comp of components) {
                if(Math.hypot(x - comp.x, y - comp.y) < iconSize/2) {
                    showContextMenu(e, comp);
                    return;
                }
            }
            
            // Menu para formas
            for(let shape of shapes) {
                if(isPointOnShape(x, y, shape)) {
                    showShapeContextMenu(e, shape);
                    return;
                }
            }
            
            // Menu para conexões
            for(let i = 0; i < connections.length; i++) {
                const conn = connections[i];
                const fromComp = components.find(c => c.id === conn.from);
                const toComp = components.find(c => c.id === conn.to);
                if(fromComp && toComp) {
                    if(isPointNearConnection(x, y, fromComp, toComp)) {
                        showConnectionContextMenu(e, conn, i);
                        return;
                    }
                }
            }
        }
        
        // ==================== MENUS DE CONTEXTO ====================
        function showContextMenu(e, comp) {
            e.preventDefault();
            contextMenuComponent = comp;
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `
                <div class="context-menu-item" onclick="accessDeviceFromMenu()">🌐 Acessar Dispositivo</div>
                <div class="context-menu-item" onclick="copyIpFromMenu()">📋 Copiar IP</div>
                <div class="context-menu-item" onclick="rotateLeftFromMenu()">🔄 Rotacionar Esquerda</div>
                <div class="context-menu-item" onclick="rotateRightFromMenu()">🔄 Rotacionar Direita</div>
                <div class="context-menu-item" onclick="flipComponentFromMenu()">🔁 Inverter Posição</div>
                <div class="context-menu-item" onclick="deleteComponentFromMenu()">🗑 Remover</div>
                <div class="context-menu-item" onclick="duplicateComponentFromMenu()">📋 Duplicar</div>
                <div class="context-menu-item" onclick="openPermanentIconModalFromMenu()">🎨 Alterar Ícone (Permanente)</div>
            `;
            menu.style.display = 'block';
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';
            setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', {once: true}), 100);
        }
        
        window.openPermanentIconModalFromMenu = () => {
            if(contextMenuComponent) openPermanentIconModal(contextMenuComponent);
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.accessDeviceFromMenu = () => {
            if(contextMenuComponent) accessDevice(contextMenuComponent);
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.copyIpFromMenu = () => {
            if(contextMenuComponent && contextMenuComponent.ip) {
                navigator.clipboard.writeText(contextMenuComponent.ip);
                showToast(`📋 IP ${contextMenuComponent.ip} copiado!`);
            } else {
                showToast('Nenhum IP configurado');
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.rotateLeftFromMenu = () => {
            if(contextMenuComponent) rotateComponent(contextMenuComponent, -15);
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.rotateRightFromMenu = () => {
            if(contextMenuComponent) rotateComponent(contextMenuComponent, 15);
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.flipComponentFromMenu = () => {
            if(contextMenuComponent) flipComponent(contextMenuComponent);
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.deleteComponentFromMenu = () => {
            if(contextMenuComponent) {
                connections = connections.filter(c => c.from !== contextMenuComponent.id && c.to !== contextMenuComponent.id);
                components = components.filter(c => c.id !== contextMenuComponent.id);
                selectedComponents = selectedComponents.filter(c => c.id !== contextMenuComponent.id);
                showProperties(null);
                if(selectedComponents.length === 0 && selectedShapes.length === 0 && selectedConnectionIndex === null) closeProperties();
                showToast(`🗑 ${contextMenuComponent.name} removido!`);
                saveUserData();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.duplicateComponentFromMenu = () => {
            if(contextMenuComponent) {
                const newComp = JSON.parse(JSON.stringify(contextMenuComponent));
                newComp.id = Date.now();
                newComp.x += 30;
                newComp.y += 30;
                if(newComp.type === 'camera') {
                    newComp.angle = newComp.angle || 0;
                    newComp.fov = newComp.fov || 80;
                }
                components.push(newComp);
                showToast(`📋 ${contextMenuComponent.name} duplicado!`);
                saveUserData();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        function showShapeContextMenu(e, shape) {
            e.preventDefault();
            contextMenuShape = shape;
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `
                <div class="context-menu-item" onclick="editShapeFromMenu()">✏️ Editar</div>
                <div class="context-menu-item" onclick="rotateShapeLeftFromMenu()">🔄 Girar Esquerda</div>
                <div class="context-menu-item" onclick="rotateShapeRightFromMenu()">🔄 Girar Direita</div>
                <div class="context-menu-item" onclick="flipShapeFromMenu()">🔁 Inverter Posição</div>
                <div class="context-menu-item" onclick="deleteShapeFromMenu()">🗑 Excluir</div>
                <div class="context-menu-item" onclick="duplicateShapeFromMenu()">📋 Duplicar</div>
            `;
            menu.style.display = 'block';
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';
            setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', {once: true}), 100);
        }
        
        window.editShapeFromMenu = () => {
            if(contextMenuShape) {
                showShapeProperties(contextMenuShape);
                openProperties();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.rotateShapeLeftFromMenu = () => {
            if(contextMenuShape && (contextMenuShape.type === 'door' || contextMenuShape.type === 'window')) {
                contextMenuShape.rotation = (contextMenuShape.rotation || 0) - 15;
                saveUserData();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.rotateShapeRightFromMenu = () => {
            if(contextMenuShape && (contextMenuShape.type === 'door' || contextMenuShape.type === 'window')) {
                contextMenuShape.rotation = (contextMenuShape.rotation || 0) + 15;
                saveUserData();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.flipShapeFromMenu = () => {
            if(contextMenuShape) {
                if(contextMenuShape.type === 'line') {
                    const tempX = contextMenuShape.x1;
                    const tempY = contextMenuShape.y1;
                    contextMenuShape.x1 = contextMenuShape.x2;
                    contextMenuShape.y1 = contextMenuShape.y2;
                    contextMenuShape.x2 = tempX;
                    contextMenuShape.y2 = tempY;
                } else {
                    contextMenuShape.rotation = (contextMenuShape.rotation || 0) + 180;
                }
                showToast(`🔄 Forma invertida!`);
                saveUserData();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.deleteShapeFromMenu = () => {
            if(contextMenuShape) {
                shapes = shapes.filter(s => s.id !== contextMenuShape.id);
                selectedShapes = selectedShapes.filter(s => s.id !== contextMenuShape.id);
                showProperties(null);
                if(selectedShapes.length === 0 && selectedComponents.length === 0 && selectedConnectionIndex === null) closeProperties();
                document.getElementById('deleteShapeBtn').style.display = 'none';
                showToast('🗑 Forma removida!');
                saveUserData();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.duplicateShapeFromMenu = () => {
            if(contextMenuShape) {
                const newShape = JSON.parse(JSON.stringify(contextMenuShape));
                newShape.id = Date.now();
                if(newShape.type === 'line') {
                    newShape.x1 += 30;
                    newShape.y1 += 30;
                    newShape.x2 += 30;
                    newShape.y2 += 30;
                } else if(newShape.type === 'text') {
                    newShape.x += 30;
                    newShape.y += 30;
                } else {
                    newShape.x += 30;
                    newShape.y += 30;
                }
                shapes.push(newShape);
                showToast(`📋 Forma duplicada!`);
                saveUserData();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        function showConnectionContextMenu(e, conn, idx) {
            e.preventDefault();
            contextMenuConnection = { conn, idx };
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `
                <div class="context-menu-item" onclick="editConnectionFromMenu()">✏️ Editar Conexão</div>
                <div class="context-menu-item" onclick="deleteConnectionFromMenu()">🗑 Excluir Conexão</div>
            `;
            menu.style.display = 'block';
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';
            setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', {once: true}), 100);
        }
        
        window.editConnectionFromMenu = () => {
            if(contextMenuConnection) {
                selectedConnectionIndex = contextMenuConnection.idx;
                showConnectionProperties(selectedConnectionIndex);
                openProperties();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.deleteConnectionFromMenu = () => {
            if(contextMenuConnection) {
                connections.splice(contextMenuConnection.idx, 1);
                selectedConnectionIndex = null;
                showToast('✅ Conexão removida!');
                saveUserData();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        // ==================== FUNÇÕES DE SELEÇÃO ====================
        function startSelection(e) {
            isSelecting = true;
            const {x, y} = getMousePos(e);
            selectionStart = {x, y};
            selectionEnd = {x, y};
            document.getElementById('selectionRect').style.display = 'block';
        }
        
        function updateSelection(e) {
            if(!isSelecting) return;
            const {x, y} = getMousePos(e);
            selectionEnd = {x, y};
            const left = Math.min(selectionStart.x, selectionEnd.x);
            const top = Math.min(selectionStart.y, selectionEnd.y);
            const width = Math.abs(selectionEnd.x - selectionStart.x);
            const height = Math.abs(selectionEnd.y - selectionStart.y);
            const rect = document.getElementById('selectionRect');
            const canvasRect = canvas.getBoundingClientRect();
            rect.style.left = (canvasRect.left + left) + 'px';
            rect.style.top = (canvasRect.top + top) + 'px';
            rect.style.width = width + 'px';
            rect.style.height = height + 'px';
        }
        
        function endSelection() {
            if(!isSelecting) return;
            isSelecting = false;
            document.getElementById('selectionRect').style.display = 'none';
            
            const minX = Math.min(selectionStart.x, selectionEnd.x);
            const maxX = Math.max(selectionStart.x, selectionEnd.x);
            const minY = Math.min(selectionStart.y, selectionEnd.y);
            const maxY = Math.max(selectionStart.y, selectionEnd.y);
            
            selectedComponents = components.filter(comp => comp.x >= minX && comp.x <= maxX && comp.y >= minY && comp.y <= maxY);
            selectedShapes = shapes.filter(shape => {
                if(shape.type === 'line') {
                    return (shape.x1 >= minX && shape.x1 <= maxX && shape.y1 >= minY && shape.y1 <= maxY) ||
                           (shape.x2 >= minX && shape.x2 <= maxX && shape.y2 >= minY && shape.y2 <= maxY);
                } else if(shape.type === 'text') {
                    return shape.x >= minX && shape.x <= maxX && shape.y >= minY && shape.y <= maxY;
                } else {
                    const w = shape.type === 'door' ? 30 : 60;
                    const h = shape.type === 'door' ? 50 : 40;
                    return shape.x + w >= minX && shape.x <= maxX && shape.y + h >= minY && shape.y <= maxY;
                }
            });
            
            const info = document.getElementById('selectionInfo');
            const total = selectedComponents.length + selectedShapes.length;
            if(total > 0) {
                info.textContent = `${total} item(s) selecionado(s)`;
                info.style.display = 'block';
                setTimeout(() => info.style.display = 'none', 2000);
            }
            
            if(selectedComponents.length === 1 && selectedShapes.length === 0) {
                showProperties(selectedComponents[0]);
                openProperties();
            } else if(selectedShapes.length === 1 && selectedComponents.length === 0) {
                showShapeProperties(selectedShapes[0]);
                openProperties();
            } else if(selectedConnectionIndex !== null) {
                showConnectionProperties(selectedConnectionIndex);
                openProperties();
            } else {
                showProperties(null);
                closeProperties();
            }
        }
        
        // ==================== PROPRIEDADES ====================
        function showProperties(comp) {
            const div = document.getElementById('props-content');
            if(!comp) {
                div.innerHTML = '<p style="color:#6c757d;">Clique em um componente para editar suas propriedades</p>';
                return;
            }
            
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
                ${comp.type === 'camera' ? `
                    <div class="property-group"><label>Ângulo (graus)</label><input type="range" id="prop-angle" min="0" max="360" value="${comp.angle || 0}"><span id="angle-val">${Math.round(comp.angle || 0)}°</span></div>
                    <div class="property-group"><label>Campo Visão (graus)</label><input type="range" id="prop-fov" min="20" max="120" value="${comp.fov || 80}"><span id="fov-val">${Math.round(comp.fov || 80)}°</span></div>
                ` : ''}
                <div class="property-group"><label>🖼️ Ícone Personalizado (Permanente - visível para todos)</label>
                    <input type="file" id="prop-image" accept="image/*">
                    <div class="image-preview" id="prop-image-preview">${comp.iconFile ? `<img src="/uploads/icons/${comp.iconFile}" style="max-width:50px;max-height:50px;">` : ''}</div>
                </div>
                <div class="property-group"><label>🔌 Conectar a</label>
                    <select id="prop-connect"><option value="">-- Selecione --</option>${components.filter(c => c.id !== comp.id).map(c => `<option value="${c.id}">${c.name}</option>`).join('')}</select>
                    <select id="prop-cable-type">
                        ${Object.entries(cableColors).map(([key, value]) => 
                            `<option value="${key}">${value.icon} ${value.name} - ${value.speed}</option>`
                        ).join('')}
                    </select>
                    <button class="btn btn-primary" style="margin-top:5px;" onclick="addConnection(${comp.id})">➕ Conectar</button>
                </div>
                <div class="modal-buttons">
                    <button class="btn btn-info" onclick="accessDeviceById(${comp.id})">🌐 Acessar</button>
                    <button class="btn btn-warning" onclick="rotateLeft(${comp.id})">🔄 Girar Esquerda</button>
                    <button class="btn btn-warning" onclick="rotateRight(${comp.id})">🔄 Girar Direita</button>
                    <button class="btn btn-secondary" onclick="flipComponentById(${comp.id})">🔁 Inverter Posição</button>
                    <button class="btn btn-danger" onclick="deleteComponent(${comp.id})">🗑 Remover</button>
                    <button class="btn btn-secondary" onclick="openPermanentIconModalById(${comp.id})">🎨 Ícone Permanente</button>
                </div>
            `;
            
            const rotationSlider = document.getElementById('prop-rotation');
            if(rotationSlider) {
                rotationSlider.oninput = (e) => {
                    comp.rotation = parseInt(e.target.value);
                    document.getElementById('rotation-val').innerText = comp.rotation + '°';
                    saveUserData();
                };
            }
            
            if(comp.type === 'camera') {
                const angleSlider = document.getElementById('prop-angle');
                const fovSlider = document.getElementById('prop-fov');
                if(angleSlider) {
                    angleSlider.oninput = (e) => {
                        comp.angle = parseInt(e.target.value);
                        document.getElementById('angle-val').innerText = comp.angle + '°';
                        saveUserData();
                    };
                }
                if(fovSlider) {
                    fovSlider.oninput = (e) => {
                        comp.fov = parseInt(e.target.value);
                        document.getElementById('fov-val').innerText = comp.fov + '°';
                        saveUserData();
                    };
                }
            }
            
            document.getElementById('prop-name')?.addEventListener('change', (e) => {
                comp.name = e.target.value;
                saveUserData();
            });
            document.getElementById('prop-x')?.addEventListener('change', (e) => {
                comp.x = parseInt(e.target.value);
                saveUserData();
            });
            document.getElementById('prop-y')?.addEventListener('change', (e) => {
                comp.y = parseInt(e.target.value);
                saveUserData();
            });
            document.getElementById('prop-ip')?.addEventListener('change', (e) => {
                comp.ip = e.target.value;
                saveUserData();
            });
            document.getElementById('prop-port')?.addEventListener('change', (e) => {
                comp.port = parseInt(e.target.value);
                saveUserData();
            });
            document.getElementById('prop-user')?.addEventListener('change', (e) => {
                comp.username = e.target.value;
                saveUserData();
            });
            document.getElementById('prop-pass')?.addEventListener('change', (e) => {
                comp.password = e.target.value;
                saveUserData();
            });
            
            const imageInput = document.getElementById('prop-image');
            if(imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if(file) {
                        const base64 = await readImageAsBase64(file);
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'equipment' })
                        });
                        const data = await response.json();
                        if(data.success) {
                            comp.iconFile = data.filename;
                            comp.customImage = null;
                            const preview = document.getElementById('prop-image-preview');
                            if(preview) preview.innerHTML = `<img src="/uploads/icons/${data.filename}" style="max-width:50px;max-height:50px;">`;
                            showToast(`✅ Ícone permanente aplicado a ${comp.name}`);
                            saveUserData();
                        }
                    }
                };
            }
        }
        
        function showShapeProperties(shape) {
            const div = document.getElementById('props-content');
            if(!shape) {
                div.innerHTML = '<p style="color:#6c757d;">Clique em um componente ou forma</p>';
                return;
            }
            
            div.innerHTML = `
                <div class="property-group"><label>Tipo</label><input type="text" value="${getShapeName(shape.type)}" disabled></div>
                <div class="property-group"><label>Cor da Linha</label><input type="color" id="shape-stroke" value="${shape.strokeColor || '#005f99'}"></div>
                <div class="property-group"><label>Espessura da Linha</label><input type="range" id="shape-linewidth" min="1" max="10" value="${shape.lineWidth || 2}"></div>
                ${shape.type === 'text' ? `
                    <div class="property-group"><label>Texto</label><input type="text" id="shape-text" value="${shape.text || ''}"></div>
                    <div class="property-group"><label>Tamanho da Fonte</label><input type="number" id="shape-fontsize" value="${shape.fontSize || 14}"></div>
                    <div class="property-group"><label>Cor do Texto</label><input type="color" id="shape-textcolor" value="${shape.textColor || '#212529'}"></div>
                ` : `
                    <div class="property-group"><label>🔄 Rotação</label><input type="range" id="shape-rotation" min="0" max="360" value="${shape.rotation || 0}"><span id="rotation-val">${Math.round(shape.rotation || 0)}°</span></div>
                    <div class="property-group"><label>🔁 Inverter Posição</label><button class="btn btn-secondary" onclick="flipShape(${shape.id})" style="width:100%;">🔄 Inverter (180°)</button></div>
                `}
                <div class="property-group"><label>Posição X</label><input type="number" id="shape-x" value="${Math.round(shape.x || shape.x1 || 0)}"></div>
                <div class="property-group"><label>Posição Y</label><input type="number" id="shape-y" value="${Math.round(shape.y || shape.y1 || 0)}"></div>
                <div class="modal-buttons">
                    <button class="btn btn-danger" onclick="deleteShape(${shape.id})">🗑 Excluir Forma</button>
                    <button class="btn btn-secondary" onclick="duplicateShape(${shape.id})">📋 Duplicar Forma</button>
                </div>
            `;
            
            document.getElementById('shape-stroke')?.addEventListener('change', (e) => {
                shape.strokeColor = e.target.value;
                saveUserData();
            });
            document.getElementById('shape-linewidth')?.addEventListener('change', (e) => {
                shape.lineWidth = parseInt(e.target.value);
                saveUserData();
            });
            
            const rotationSlider = document.getElementById('shape-rotation');
            if(rotationSlider) {
                rotationSlider.oninput = (e) => {
                    shape.rotation = parseInt(e.target.value);
                    document.getElementById('rotation-val').innerText = shape.rotation + '°';
                    saveUserData();
                };
            }
            
            document.getElementById('shape-x')?.addEventListener('change', (e) => {
                const val = parseInt(e.target.value);
                if(shape.type === 'line') {
                    shape.x1 = val;
                    shape.x2 = val + (shape.x2 - shape.x1);
                } else {
                    shape.x = val;
                }
                saveUserData();
            });
            document.getElementById('shape-y')?.addEventListener('change', (e) => {
                const val = parseInt(e.target.value);
                if(shape.type === 'line') {
                    shape.y1 = val;
                    shape.y2 = val + (shape.y2 - shape.y1);
                } else {
                    shape.y = val;
                }
                saveUserData();
            });
            
            if(shape.type === 'text') {
                document.getElementById('shape-text')?.addEventListener('change', (e) => {
                    shape.text = e.target.value;
                    saveUserData();
                });
                document.getElementById('shape-fontsize')?.addEventListener('change', (e) => {
                    shape.fontSize = parseInt(e.target.value);
                    saveUserData();
                });
                document.getElementById('shape-textcolor')?.addEventListener('change', (e) => {
                    shape.textColor = e.target.value;
                    saveUserData();
                });
            }
        }
        
        function showConnectionProperties(connIdx) {
            const div = document.getElementById('props-content');
            const conn = connections[connIdx];
            if(!conn) {
                div.innerHTML = '<p style="color:#6c757d;">Clique em uma conexão para editar</p>';
                return;
            }
            const fromComp = components.find(c => c.id === conn.from);
            const toComp = components.find(c => c.id === conn.to);
            if(!fromComp || !toComp) return;
            
            div.innerHTML = `
                <div class="property-group"><label>Conexão</label><input type="text" value="${fromComp.name} → ${toComp.name}" disabled></div>
                <div class="property-group"><label>Tipo de Cabo</label>
                    <select id="conn-cable-type" style="width:100%; padding:8px; background:var(--bg-card); color:var(--text-primary); border:1px solid var(--border-color); border-radius:5px;">
                        ${Object.entries(cableColors).map(([key, value]) => 
                            `<option value="${key}" ${conn.type === key ? 'selected' : ''}>${value.icon} ${value.name} - ${value.speed}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="modal-buttons">
                    <button class="btn btn-primary" onclick="updateSelectedConnection(${connIdx})">✅ Atualizar</button>
                    <button class="btn btn-danger" onclick="deleteSelectedConnection(${connIdx})">🗑 Excluir Conexão</button>
                </div>
            `;
        }
        
        window.updateSelectedConnection = (connIdx) => {
            const cableType = document.getElementById('conn-cable-type').value;
            connections[connIdx].type = cableType;
            selectedConnectionIndex = null;
            showProperties(null);
            closeProperties();
            showToast(`✅ Conexão atualizada para ${cableType.toUpperCase()}!`);
            saveUserData();
        };
        
        window.deleteSelectedConnection = (connIdx) => {
            if(confirm('Deseja excluir esta conexão?')) {
                connections.splice(connIdx, 1);
                selectedConnectionIndex = null;
                showProperties(null);
                closeProperties();
                showToast(`✅ Conexão removida!`);
                saveUserData();
            }
        };
        
        // ==================== FUNÇÕES DE AÇÕES ====================
        window.flipComponentById = (id) => {
            const comp = components.find(c => c.id === id);
            if(comp) {
                flipComponent(comp);
                saveUserData();
            }
        };
        
        window.flipComponent = (comp) => {
            if (!comp) return;
            comp.rotation = (comp.rotation || 0) + 180;
            showToast(`🔄 ${comp.name} invertido!`);
            saveUserData();
        };
        
        window.flipShape = (id) => {
            const shape = shapes.find(s => s.id === id);
            if(shape && (shape.type === 'door' || shape.type === 'window')) {
                shape.rotation = (shape.rotation || 0) + 180;
                showToast(`🔄 Forma invertida!`);
                saveUserData();
            } else if(shape && shape.type === 'line') {
                const tempX = shape.x1;
                const tempY = shape.y1;
                shape.x1 = shape.x2;
                shape.y1 = shape.y2;
                shape.x2 = tempX;
                shape.y2 = tempY;
                showToast(`🔄 Linha invertida!`);
                saveUserData();
            }
        };
        
        window.duplicateShape = (id) => {
            const shape = shapes.find(s => s.id === id);
            if(shape) {
                const newShape = JSON.parse(JSON.stringify(shape));
                newShape.id = Date.now();
                if(newShape.type === 'line') {
                    newShape.x1 += 30;
                    newShape.y1 += 30;
                    newShape.x2 += 30;
                    newShape.y2 += 30;
                } else if(newShape.type === 'text') {
                    newShape.x += 30;
                    newShape.y += 30;
                } else {
                    newShape.x += 30;
                    newShape.y += 30;
                }
                shapes.push(newShape);
                showToast(`📋 Forma duplicada!`);
                saveUserData();
            }
        };
        
        window.deleteShape = (id) => {
            shapes = shapes.filter(s => s.id !== id);
            selectedShapes = selectedShapes.filter(s => s.id !== id);
            showProperties(null);
            if(selectedShapes.length === 0 && selectedComponents.length === 0 && selectedConnectionIndex === null) closeProperties();
            document.getElementById('deleteShapeBtn').style.display = 'none';
            showToast('🗑 Forma removida!');
            saveUserData();
        };
        
        window.deleteSelectedShape = () => {
            if (selectedShapes.length > 0) {
                const shapeId = selectedShapes[0].id;
                shapes = shapes.filter(s => s.id !== shapeId);
                selectedShapes = [];
                showProperties(null);
                closeProperties();
                document.getElementById('deleteShapeBtn').style.display = 'none';
                showToast('🗑 Forma removida!');
                saveUserData();
            }
        };
        
        window.deleteSelectedItems = () => {
            if (selectedComponents.length === 0 && selectedShapes.length === 0 && selectedConnectionIndex === null) {
                showToast('⚠️ Nenhum item selecionado');
                return;
            }
            
            if (confirm(`Deseja excluir ${selectedComponents.length} equipamento(s), ${selectedShapes.length} forma(s) e ${selectedConnectionIndex !== null ? 1 : 0} conexão(ões)?`)) {
                const selectedIds = selectedComponents.map(c => c.id);
                connections = connections.filter(c => !selectedIds.includes(c.from) && !selectedIds.includes(c.to));
                
                if (selectedConnectionIndex !== null) {
                    connections.splice(selectedConnectionIndex, 1);
                    selectedConnectionIndex = null;
                }
                
                components = components.filter(c => !selectedIds.includes(c.id));
                const selectedShapeIds = selectedShapes.map(s => s.id);
                shapes = shapes.filter(s => !selectedShapeIds.includes(s.id));
                
                selectedComponents = [];
                selectedShapes = [];
                showProperties(null);
                closeProperties();
                document.getElementById('deleteShapeBtn').style.display = 'none';
                showToast(`🗑 Itens excluídos com sucesso!`);
                saveUserData();
            }
        };
        
        window.rotateLeft = (id) => {
            const comp = components.find(c => c.id === id);
            if(comp) {
                rotateComponent(comp, -15);
                saveUserData();
            }
        };
        
        window.rotateRight = (id) => {
            const comp = components.find(c => c.id === id);
            if(comp) {
                rotateComponent(comp, 15);
                saveUserData();
            }
        };
        
        window.accessDeviceById = (id) => {
            const comp = components.find(c => c.id === id);
            accessDevice(comp);
        };
        
        window.deleteComponent = (id) => {
            if(confirm('Deseja remover este equipamento?')) {
                connections = connections.filter(c => c.from !== id && c.to !== id);
                components = components.filter(c => c.id !== id);
                selectedComponents = selectedComponents.filter(c => c.id !== id);
                showProperties(null);
                if(selectedComponents.length === 0 && selectedShapes.length === 0 && selectedConnectionIndex === null) closeProperties();
                showToast(`🗑 Equipamento removido!`);
                saveUserData();
            }
        };
        
        window.addConnection = (fromId) => {
            const toId = document.getElementById('prop-connect').value;
            const cableType = document.getElementById('prop-cable-type').value;
            if(toId) {
                connections.push({from: fromId, to: parseInt(toId), type: cableType});
                const cableInfo = cableColors[cableType];
                if(cableInfo && cableInfo.type === 'wireless') {
                    const fromComp = components.find(c => c.id === fromId);
                    const toComp = components.find(c => c.id === parseInt(toId));
                    if(fromComp && toComp) {
                        showWirelessAnimation(fromComp.x, fromComp.y, cableType);
                        setTimeout(() => showWirelessAnimation(toComp.x, toComp.y, cableType), 500);
                    }
                }
                showToast(`✅ Conexão ${cableInfo ? cableInfo.name : cableType.toUpperCase()} adicionada!`);
                saveUserData();
            } else {
                showToast('⚠️ Selecione um equipamento para conectar');
            }
        };
        
        function showWirelessAnimation(x, y, type) {
            const canvasRect = canvas.getBoundingClientRect();
            const container = document.querySelector('.canvas-area');
            const animationDiv = document.createElement('div');
            animationDiv.className = 'connection-animation';
            animationDiv.style.position = 'absolute';
            animationDiv.style.left = (canvasRect.left + x * zoom) + 'px';
            animationDiv.style.top = (canvasRect.top + y * zoom) + 'px';
            animationDiv.style.width = '80px';
            animationDiv.style.height = '80px';
            animationDiv.style.transform = 'translate(-50%, -50%)';
            
            const cableInfo = cableColors[type];
            const color = cableInfo?.color || '#005f99';
            
            if (cableInfo?.animation === 'wave') {
                for(let i = 0; i < 3; i++) {
                    const wave = document.createElement('div');
                    wave.className = 'connection-wave';
                    wave.style.position = 'absolute';
                    wave.style.width = '20px';
                    wave.style.height = '20px';
                    wave.style.left = '40px';
                    wave.style.top = '40px';
                    wave.style.animationDelay = (i * 0.3) + 's';
                    wave.style.border = `2px solid ${color}`;
                    wave.style.borderRadius = '50%';
                    wave.style.boxShadow = `0 0 8px ${color}`;
                    animationDiv.appendChild(wave);
                }
            } else {
                for(let i = 0; i < 4; i++) {
                    const packet = document.createElement('div');
                    packet.className = 'data-packet';
                    packet.style.position = 'absolute';
                    packet.style.width = '8px';
                    packet.style.height = '8px';
                    packet.style.borderRadius = '2px';
                    packet.style.backgroundColor = color;
                    packet.style.boxShadow = `0 0 6px ${color}`;
                    packet.style.top = '36px';
                    packet.style.left = '-20px';
                    packet.style.animation = 'dataPacket 1s linear infinite';
                    packet.style.animationDelay = (i * 0.25) + 's';
                    animationDiv.appendChild(packet);
                }
            }
            
            container.appendChild(animationDiv);
            setTimeout(() => animationDiv.remove(), 1500);
        }
        
        function showCableModal(fromComp, toComp) {
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🔌 Tipo de Conexão</h3>
                    <p>De: ${fromComp.name}</p>
                    <p>Para: ${toComp.name}</p>
                    <select id="cableSelect" style="width:100%; padding:8px; margin:10px 0; background:var(--bg-tertiary); color:var(--text-primary); border:none; border-radius:5px;">
                        ${Object.entries(cableColors).map(([key, value]) => 
                            `<option value="${key}">${value.icon} ${value.name} - ${value.speed}</option>`
                        ).join('')}
                    </select>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="confirmConnection(${fromComp.id}, ${toComp.id})">✅ Conectar</button>
                        <button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
        }
        
        window.confirmConnection = (fromId, toId) => {
            const cableType = document.getElementById('cableSelect').value;
            connections.push({from: fromId, to: toId, type: cableType});
            if(window.currentModal) {
                document.body.removeChild(window.currentModal);
                window.currentModal = null;
            }
            const cableInfo = cableColors[cableType];
            if(cableInfo && cableInfo.type === 'wireless') {
                const fromComp = components.find(c => c.id === fromId);
                const toComp = components.find(c => c.id === toId);
                if(fromComp && toComp) {
                    showWirelessAnimation(fromComp.x, fromComp.y, cableType);
                    setTimeout(() => showWirelessAnimation(toComp.x, toComp.y, cableType), 500);
                }
            }
            showToast(`✅ Conexão ${cableInfo ? cableInfo.name : cableType.toUpperCase()} adicionada!`);
            saveUserData();
        };
        
        // ==================== FUNÇÕES DE ÍCONE PERMANENTE PARA EQUIPAMENTOS ====================
        function openPermanentIconModal(comp) {
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🎨 Alterar Ícone (Permanente)</h3>
                    <p>Equipamento: <strong>${comp.name}</strong></p>
                    <p style="font-size:12px;color:#6c757d;">Este ícone será salvo no servidor e visível para todos os usuários.</p>
                    <div class="property-group"><label>Escolha uma imagem</label><input type="file" id="permIconImage" accept="image/*"><div class="image-preview" id="permIconPreview"></div></div>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="applyPermanentIcon(${comp.id})">✅ Aplicar (Permanente)</button>
                        <button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            window.permIconTargetComp = comp;
            
            const imageInput = document.getElementById('permIconImage');
            if(imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if(file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('permIconPreview');
                        if(preview) preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">';
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'equipment' })
                        });
                        const data = await response.json();
                        if(data.success) {
                            window.permIconFilename = data.filename;
                            showToast('✅ Ícone enviado com sucesso!');
                        }
                    }
                };
            }
        }
        
        window.applyPermanentIcon = (compId) => {
            const comp = components.find(c => c.id === compId);
            if(comp && window.permIconFilename) {
                comp.iconFile = window.permIconFilename;
                comp.customImage = null;
                comp.customImageTemp = null;
                comp.customIconTemp = null;
                showToast(`✅ Ícone permanente aplicado a ${comp.name} (visível para todos)`);
                closeModal();
                saveUserData();
            } else if(comp) {
                showToast('⚠️ Nenhuma imagem selecionada');
            }
            window.permIconFilename = null;
        };
        
        window.openPermanentIconModalById = (id) => {
            const comp = components.find(c => c.id === id);
            if(comp) openPermanentIconModal(comp);
        };
        
        // ==================== FUNÇÕES DE CATEGORIAS E DISPOSITIVOS ====================
        function openAddCategoryModal() {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem adicionar categorias');
                return;
            }
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">📁 Nova Categoria</h3>
                    <input type="text" id="catName" placeholder="Nome da categoria">
                    <input type="text" id="catIcon" placeholder="Ícone (ex: 🌐)" value="📁">
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="addCategory()">Adicionar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
        }
        
        window.addCategory = () => {
            const name = document.getElementById('catName')?.value;
            const icon = document.getElementById('catIcon')?.value;
            if (!name) {
                showToast('Digite um nome para a categoria');
                return;
            }
            if (categories[name]) {
                showToast('Categoria já existe');
                return;
            }
            categories[name] = { icon: icon || '📁', devices: [] };
            saveUserData();
            saveGlobalLibrary(); // Adicionado
            closeModal();
            renderPalette();
            showToast(`✅ Categoria "${name}" adicionada!`);
        };
        
        window.editCategory = (catName) => {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem editar categorias');
                return;
            }
            const catData = categories[catName];
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">✏️ Editar Categoria</h3>
                    <input type="text" id="catName" value="${catName}">
                    <input type="text" id="catIcon" value="${catData.icon}">
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="updateCategory('${catName.replace(/'/g, "\\'")}')">Salvar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
        };
        
        window.updateCategory = (oldName) => {
            const newName = document.getElementById('catName')?.value;
            const icon = document.getElementById('catIcon')?.value;
            if (!newName) return;
            const catData = categories[oldName];
            delete categories[oldName];
            categories[newName] = { ...catData, icon: icon };
            saveUserData();
            saveGlobalLibrary(); // Adicionado
            closeModal();
            renderPalette();
            showToast(`✅ Categoria atualizada!`);
        };
        
        window.deleteCategory = (catName) => {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem excluir categorias');
                return;
            }
            if (confirm(`Deseja excluir a categoria "${catName}" e todos os seus dispositivos?`)) {
                delete categories[catName];
                saveUserData();
                saveGlobalLibrary(); // Adicionado
                renderPalette();
                showToast(`🗑 Categoria "${catName}" removida!`);
            }
        };
        
        window.addDeviceToCategory = (catName) => {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem adicionar dispositivos');
                return;
            }
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">➕ Novo Dispositivo em ${catName}</h3>
                    <input type="text" id="devName" placeholder="Nome">
                    <input type="text" id="devIcon" placeholder="Ícone (emoji)" value="📦">
                    <div class="property-group">
                        <label>OU Imagem do dispositivo (permanente)</label>
                        <input type="file" id="devImage" accept="image/*">
                        <div class="image-preview" id="devImagePreview"></div>
                    </div>
                    <input type="text" id="devDesc" placeholder="Descrição">
                    <input type="color" id="devColor" value="#005f99">
                    <input type="text" id="devType" placeholder="Tipo (ex: camera, switch)">
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="addDevice('${catName.replace(/'/g, "\\'")}')">Adicionar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            
            const imageInput = document.getElementById('devImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devImagePreview');
                        if (preview) preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">';
                        window.tempImageData = base64;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'equipment' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempImageFile = data.filename;
                        }
                    }
                };
            }
        };
        
        window.addDevice = async (catName) => {
            const name = document.getElementById('devName')?.value;
            const icon = document.getElementById('devIcon')?.value;
            const desc = document.getElementById('devDesc')?.value;
            const color = document.getElementById('devColor')?.value;
            const type = document.getElementById('devType')?.value;
            const imageData = window.tempImageData || null;
            const iconFile = window.tempImageFile || null;
            
            if (!name) {
                showToast('Digite um nome para o dispositivo');
                return;
            }
            
            categories[catName].devices.push({
                name,
                icon: icon || '📦',
                desc: desc || '',
                type: type || 'custom',
                color: color || '#005f99',
                imageData: imageData,
                iconFile: iconFile
            });
            
            window.tempImageData = null;
            window.tempImageFile = null;
            saveUserData();
            await saveGlobalLibrary(); // Adicionado
            closeModal();
            renderPalette();
            showToast(`✅ Dispositivo "${name}" adicionado!`);
        };
        
        window.editDevice = (catName, idx) => {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem editar dispositivos');
                return;
            }
            const device = categories[catName].devices[idx];
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">✏️ Editar Dispositivo</h3>
                    <input type="text" id="devName" value="${device.name.replace(/"/g, '&quot;')}">
                    <input type="text" id="devIcon" value="${device.icon || '📦'}">
                    <div class="property-group">
                        <label>OU Imagem do dispositivo</label>
                        <input type="file" id="devImage" accept="image/*">
                        <div class="image-preview" id="devImagePreview">
                            ${device.iconFile ? `<img src="/uploads/icons/${device.iconFile}" style="max-width:50px;max-height:50px;">` : (device.imageData ? `<img src="${device.imageData}" style="max-width:50px;max-height:50px;">` : '')}
                        </div>
                    </div>
                    <input type="text" id="devDesc" value="${device.desc || ''}">
                    <input type="color" id="devColor" value="${device.color || '#005f99'}">
                    <input type="text" id="devType" value="${device.type || 'custom'}">
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="updateDevice('${catName.replace(/'/g, "\\'")}', ${idx})">Salvar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            
            const imageInput = document.getElementById('devImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devImagePreview');
                        if (preview) preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">';
                        window.tempImageData = base64;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'equipment' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempImageFile = data.filename;
                        }
                    }
                };
            }
        };
        
        window.updateDevice = async (catName, idx) => {
            const name = document.getElementById('devName')?.value;
            const icon = document.getElementById('devIcon')?.value;
            const desc = document.getElementById('devDesc')?.value;
            const color = document.getElementById('devColor')?.value;
            const type = document.getElementById('devType')?.value;
            const imageData = window.tempImageData || categories[catName].devices[idx].imageData;
            const iconFile = window.tempImageFile || categories[catName].devices[idx].iconFile;
            
            if (!name) return;
            
            categories[catName].devices[idx] = {
                ...categories[catName].devices[idx],
                name,
                icon: icon || '📦',
                desc: desc || '',
                type: type || 'custom',
                color: color || '#005f99',
                imageData: imageData,
                iconFile: iconFile
            };
            
            window.tempImageData = null;
            window.tempImageFile = null;
            saveUserData();
            await saveGlobalLibrary(); // Adicionado
            closeModal();
            renderPalette();
            showToast(`✅ Dispositivo atualizado!`);
        };
        
        window.deleteDevice = (catName, idx) => {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem excluir dispositivos');
                return;
            }
            if (confirm('Deseja excluir este dispositivo?')) {
                categories[catName].devices.splice(idx, 1);
                saveUserData();
                saveGlobalLibrary(); // Adicionado
                renderPalette();
                showToast(`🗑 Dispositivo removido!`);
            }
        };
        
        function openAddDeviceModal() {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem adicionar equipamentos personalizados');
                return;
            }
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🔧 Novo Equipamento Personalizado</h3>
                    <input type="text" id="devName" placeholder="Nome">
                    <input type="text" id="devIcon" placeholder="Ícone (emoji)" value="📦">
                    <div class="property-group">
                        <label>OU Imagem do equipamento (permanente)</label>
                        <input type="file" id="devImage" accept="image/*">
                        <div class="image-preview" id="devImagePreview"></div>
                    </div>
                    <input type="text" id="devDesc" placeholder="Descrição">
                    <input type="color" id="devColor" value="#005f99">
                    <input type="text" id="devType" placeholder="Tipo (opcional)">
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="addCustomDevice()">Adicionar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            
            const imageInput = document.getElementById('devImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devImagePreview');
                        if (preview) preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">';
                        window.tempImageData = base64;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'equipment' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempImageFile = data.filename;
                        }
                    }
                };
            }
        }
        
        window.addCustomDevice = async () => {
            const name = document.getElementById('devName')?.value;
            const icon = document.getElementById('devIcon')?.value;
            const desc = document.getElementById('devDesc')?.value;
            const color = document.getElementById('devColor')?.value;
            const type = document.getElementById('devType')?.value;
            const imageData = window.tempImageData || null;
            const iconFile = window.tempImageFile || null;
            
            if (!name) {
                showToast('Digite um nome para o equipamento');
                return;
            }
            
            customDevices.push({
                id: Date.now(),
                name,
                icon: icon || '📦',
                desc: desc || '',
                type: type || 'custom',
                color: color || '#005f99',
                imageData: imageData,
                iconFile: iconFile
            });
            
            window.tempImageData = null;
            window.tempImageFile = null;
            saveUserData();
            await saveGlobalLibrary(); // Adicionado
            closeModal();
            renderPalette();
            showToast(`✅ Equipamento "${name}" adicionado!`);
        };
        
        window.editCustomDevice = (idx) => {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem editar equipamentos');
                return;
            }
            const device = customDevices[idx];
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">✏️ Editar Equipamento</h3>
                    <input type="text" id="devName" value="${device.name.replace(/"/g, '&quot;')}">
                    <input type="text" id="devIcon" value="${device.icon || '📦'}">
                    <div class="property-group">
                        <label>OU Imagem do equipamento</label>
                        <input type="file" id="devImage" accept="image/*">
                        <div class="image-preview" id="devImagePreview">
                            ${device.iconFile ? `<img src="/uploads/icons/${device.iconFile}" style="max-width:50px;max-height:50px;">` : (device.imageData ? `<img src="${device.imageData}" style="max-width:50px;max-height:50px;">` : '')}
                        </div>
                    </div>
                    <input type="text" id="devDesc" value="${device.desc || ''}">
                    <input type="color" id="devColor" value="${device.color || '#005f99'}">
                    <input type="text" id="devType" value="${device.type || 'custom'}">
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="updateCustomDevice(${idx})">Salvar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            
            const imageInput = document.getElementById('devImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devImagePreview');
                        if (preview) preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">';
                        window.tempImageData = base64;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'equipment' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempImageFile = data.filename;
                        }
                    }
                };
            }
        };
        
        window.updateCustomDevice = async (idx) => {
            const name = document.getElementById('devName')?.value;
            const icon = document.getElementById('devIcon')?.value;
            const desc = document.getElementById('devDesc')?.value;
            const color = document.getElementById('devColor')?.value;
            const type = document.getElementById('devType')?.value;
            const imageData = window.tempImageData || customDevices[idx].imageData;
            const iconFile = window.tempImageFile || customDevices[idx].iconFile;
            
            if (!name) return;
            
            customDevices[idx] = {
                ...customDevices[idx],
                name,
                icon: icon || '📦',
                desc: desc || '',
                type: type || 'custom',
                color: color || '#005f99',
                imageData: imageData,
                iconFile: iconFile
            };
            
            window.tempImageData = null;
            window.tempImageFile = null;
            saveUserData();
            await saveGlobalLibrary(); // Adicionado
            closeModal();
            renderPalette();
            showToast(`✅ Equipamento atualizado!`);
        };
        
        window.deleteCustomDevice = (idx) => {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem excluir equipamentos');
                return;
            }
            if (confirm('Deseja excluir este equipamento?')) {
                customDevices.splice(idx, 1);
                saveUserData();
                saveGlobalLibrary(); // Adicionado
                renderPalette();
                showToast(`🗑 Equipamento removido!`);
            }
        };
        
        // ==================== FUNÇÕES DE CONEXÃO (NOVA CONEXÃO MODAL) ====================
        function openAddConnectionModal() {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem adicionar conexões');
                return;
            }
            
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🔌 Nova Conexão</h3>
                    <input type="text" id="connName" placeholder="Nome da conexão (ex: Fibra Óptica)">
                    <input type="text" id="connIcon" placeholder="Ícone (ex: 🔷)" value="🔌">
                    <div class="property-group">
                        <label>OU Imagem personalizada (permanente)</label>
                        <input type="file" id="connIconImage" accept="image/*">
                        <div class="image-preview" id="connIconPreview"></div>
                    </div>
                    <input type="color" id="connColor" value="#005f99">
                    <input type="text" id="connSpeed" placeholder="Velocidade (ex: 10 Gbps)" value="N/A">
                    <input type="text" id="connDesc" placeholder="Descrição">
                    <select id="connType">
                        <option value="cable">Cabeado</option>
                        <option value="wireless">Sem Fio</option>
                    </select>
                    <select id="connAnimation">
                        <option value="">Nenhuma</option>
                        <option value="wave">Ondas</option>
                        <option value="packet">Pacotes</option>
                    </select>
                    <select id="connCategory">
                        <option value="Cabeadas">Cabeadas</option>
                        <option value="Sem Fio">Sem Fio</option>
                        <option value="Personalizadas">Personalizadas</option>
                    </select>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="addConnectionFromModal()">Adicionar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            
            // Upload de imagem para ícone da conexão
            const imageInput = document.getElementById('connIconImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('connIconPreview');
                        if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;max-height:50px;">`;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'connection' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempConnIconFile = data.filename;
                            showToast('✅ Ícone da conexão enviado com sucesso!');
                        }
                    }
                };
            }
        }
        
        window.addConnectionFromModal = () => {
            try {
                const name = document.getElementById('connName')?.value;
                const icon = document.getElementById('connIcon')?.value;
                const color = document.getElementById('connColor')?.value;
                const speed = document.getElementById('connSpeed')?.value;
                const desc = document.getElementById('connDesc')?.value;
                const type = document.getElementById('connType')?.value;
                const animation = document.getElementById('connAnimation')?.value;
                const category = document.getElementById('connCategory')?.value;
                const iconFile = window.tempConnIconFile || null;
                
                if (!name) {
                    showToast('Digite um nome para a conexão');
                    return;
                }
                
                const connData = {
                    name,
                    icon: icon || '🔌',
                    color,
                    speed: speed || 'N/A',
                    desc: desc || '',
                    type,
                    animation: animation || null,
                    iconFile: iconFile
                };
                
                addCustomConnection(category, connData);
                window.tempConnIconFile = null;
                closeModal();
                showToast(`✅ Conexão "${name}" adicionada com sucesso!`);
            } catch (error) {
                console.error('Erro ao adicionar conexão:', error);
                showToast('❌ Erro ao adicionar conexão. Verifique o console.');
                closeModal();
            }
        };
        
        window.addConnectionToCategory = (category) => {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem adicionar conexões');
                return;
            }
            
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🔌 Nova Conexão em ${category}</h3>
                    <input type="text" id="connName" placeholder="Nome da conexão">
                    <input type="text" id="connIcon" placeholder="Ícone (ex: 🔷)" value="🔌">
                    <div class="property-group">
                        <label>OU Imagem personalizada (permanente)</label>
                        <input type="file" id="connIconImage" accept="image/*">
                        <div class="image-preview" id="connIconPreview"></div>
                    </div>
                    <input type="color" id="connColor" value="#005f99">
                    <input type="text" id="connSpeed" placeholder="Velocidade" value="N/A">
                    <input type="text" id="connDesc" placeholder="Descrição">
                    <select id="connType">
                        <option value="cable">Cabeado</option>
                        <option value="wireless">Sem Fio</option>
                    </select>
                    <select id="connAnimation">
                        <option value="">Nenhuma</option>
                        <option value="wave">Ondas</option>
                        <option value="packet">Pacotes</option>
                    </select>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="addConnectionToCategoryConfirm('${category.replace(/'/g, "\\'")}')">Adicionar</button>
                        <button class="btn btn-danger" onclick="closeModal()">Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            
            const imageInput = document.getElementById('connIconImage');
            if (imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('connIconPreview');
                        if (preview) preview.innerHTML = `<img src="${base64}" style="max-width:50px;max-height:50px;">`;
                        const response = await fetch('/api/upload_icon', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64, type: 'connection' })
                        });
                        const data = await response.json();
                        if (data.success) {
                            window.tempConnIconFile = data.filename;
                            showToast('✅ Ícone da conexão enviado com sucesso!');
                        }
                    }
                };
            }
        };
        
        window.addConnectionToCategoryConfirm = (category) => {
            try {
                const name = document.getElementById('connName')?.value;
                const icon = document.getElementById('connIcon')?.value;
                const color = document.getElementById('connColor')?.value;
                const speed = document.getElementById('connSpeed')?.value;
                const desc = document.getElementById('connDesc')?.value;
                const type = document.getElementById('connType')?.value;
                const animation = document.getElementById('connAnimation')?.value;
                const iconFile = window.tempConnIconFile || null;
                
                if (!name) {
                    showToast('Digite um nome para a conexão');
                    return;
                }
                
                const connData = {
                    name,
                    icon: icon || '🔌',
                    color,
                    speed: speed || 'N/A',
                    desc: desc || '',
                    type,
                    animation: animation || null,
                    iconFile: iconFile
                };
                
                if (!connectionCategories[category]) {
                    connectionCategories[category] = { icon: '🔌', connections: [] };
                }
                
                const key = getConnectionKey(name);
                connectionCategories[category].connections.push(connData);
                
                cableColors[key] = {
                    color: color,
                    name: name,
                    icon: icon || '🔌',
                    type: type,
                    speed: speed || 'N/A',
                    desc: desc || '',
                    animation: animation || null,
                    iconFile: iconFile
                };
                
                window.tempConnIconFile = null;
                saveUserData();
                saveGlobalLibrary(); // Adicionado
                closeModal();
                renderConnectionsPalette();
                showToast(`✅ Conexão "${name}" adicionada!`);
            } catch (error) {
                console.error('Erro ao adicionar conexão:', error);
                showToast('❌ Erro ao adicionar conexão. Verifique o console.');
                closeModal();
            }
        };
        
        // ==================== FUNÇÕES DE BACKGROUND ====================
        function openBackgroundModal() {
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🖼️ Planta Baixa / Imagem de Fundo</h3>
                    
                    <div class="background-controls">
                        <label><strong>📁 Importar Imagem Local</strong></label>
                        <input type="file" id="bgImageUpload" accept="image/*">
                        <div class="image-preview" id="bgPreview"></div>
                        <button class="btn btn-primary" style="margin-top:8px;" onclick="importLocalImage()">📤 Importar e Adicionar à Tela</button>
                    </div>
                    
                    <div class="background-controls">
                        <label><strong>🎨 Opacidade da Imagem</strong></label>
                        <input type="range" id="bgOpacity" min="0.1" max="1" step="0.01" value="${backgroundOpacity}" onchange="updateBackgroundOpacity(this.value)">
                        <span id="opacityValue">${Math.round(backgroundOpacity * 100)}%</span>
                    </div>
                    
                    ${backgroundImage ? `
                        <div class="background-controls">
                            <label><strong>🖼️ Imagem Atual</strong></label>
                            <div class="action-buttons">
                                <button class="btn btn-secondary" onclick="selectBackgroundImage()">🔍 Selecionar Imagem na Tela</button>
                                <button class="btn btn-danger" onclick="removeBackground()">🗑 Remover Imagem de Fundo</button>
                            </div>
                            <div style="margin-top: 8px; font-size: 12px; color: #005f99;">
                                ✨ Dica: Selecione a imagem e depois arraste para mover ou redimensione pelos cantos!
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="modal-buttons">
                        <button class="btn btn-danger" onclick="closeModal()">❌ Fechar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
        }
        
        window.importLocalImage = async () => {
            const fileInput = document.getElementById('bgImageUpload');
            const file = fileInput.files[0];
            if (file) {
                const base64 = await readImageAsBase64(file);
                await uploadBackgroundImage(base64, file.name);
            } else {
                showToast('Selecione uma imagem primeiro');
            }
        };
        
        window.selectBackgroundImage = () => {
            isBackgroundSelected = true;
            closeModal();
            showToast('✅ Imagem selecionada! Arraste para mover ou redimensione pelos cantos.');
        };
        
        window.updateBackgroundOpacity = (value) => {
            backgroundOpacity = parseFloat(value);
            document.getElementById('opacityValue').innerText = Math.round(backgroundOpacity * 100) + '%';
            saveUserData();
        };
        
        window.removeBackground = () => {
            if (confirm('Deseja remover a imagem de fundo?')) {
                backgroundImage = null;
                backgroundImageObj = null;
                backgroundOpacity = 0.8;
                backgroundWidth = 0;
                backgroundHeight = 0;
                backgroundX = 0;
                backgroundY = 0;
                isBackgroundSelected = false;
                saveUserData();
                showToast('✅ Imagem de fundo removida');
                closeModal();
            }
        };
        
        async function uploadBackgroundImage(base64, name) {
            showToast('📤 Enviando imagem...');
            try {
                const response = await fetch('/api/upload_background', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: base64, name: name })
                });
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
                        showToast('✅ Imagem de fundo adicionada!');
                        closeModal();
                    };
                    backgroundImageObj.src = backgroundImage;
                    saveUserData();
                } else {
                    showToast('Erro ao enviar imagem');
                }
            } catch(e) {
                showToast('Erro ao enviar imagem');
            }
        }
        
        // ==================== FUNÇÕES DE PROJETO ====================
        function newProject() {
            if (confirm('Novo projeto? Todos os dados não salvos serão perdidos.')) {
                components = [];
                connections = [];
                shapes = [];
                selectedComponents = [];
                selectedShapes = [];
                selectedConnectionIndex = null;
                backgroundImage = null;
                backgroundImageObj = null;
                backgroundOpacity = 0.8;
                backgroundWidth = 0;
                backgroundHeight = 0;
                backgroundX = 0;
                backgroundY = 0;
                isBackgroundSelected = false;
                closeProperties();
                saveUserData();
                showToast('📁 Novo projeto criado!');
            }
        }
        
        function saveProjectToFile() {
            const projectData = {
                components: components.map(c => ({
                    ...c,
                    customImage: c.customImage || null,
                    imageData: c.imageData || null,
                    iconFile: c.iconFile || null,
                    customIconTemp: c.customIconTemp || null,
                    customImageTemp: c.customImageTemp || null
                })),
                connections: connections,
                shapes: shapes,
                background: backgroundImage,
                backgroundOpacity: backgroundOpacity,
                backgroundWidth: backgroundWidth,
                backgroundHeight: backgroundHeight,
                backgroundX: backgroundX,
                backgroundY: backgroundY,
                version: '2.0',
                date: new Date().toISOString()
            };
            
            const dataStr = JSON.stringify(projectData, null, 2);
            const blob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `projeto_${Date.now()}.projetize`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('✅ Projeto salvo com sucesso!');
        }
        
        function loadProjectFromFile() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.projetize, .json';
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
                        showToast('✅ Projeto carregado com sucesso!');
                    } catch(err) {
                        showToast('Erro ao carregar projeto: ' + err.message);
                    }
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
                pdfWindow.document.write(`
                    <html><head><title>Projeto CFTV</title></head>
                    <body style="margin:0; padding:20px; display:flex; justify-content:center; background:white;">
                        <img src="${imgData}" style="max-width:100%; height:auto;">
                        <script>window.print();<\\/script>
                    </body></html>
                `);
                setTimeout(() => draw(), 500);
                showToast('📄 PDF gerado! Use Ctrl+P para salvar como PDF.');
            }, 100);
        }
        
        function exportPDFWithList() {
            drawWithBackground(true, true);
            let listHTML = `
                <div style="font-family: Arial, sans-serif; padding: 20px;">
                    <h1 style="color: #005f99; text-align: center;">PROJETIZE - LISTA DE EQUIPAMENTOS</h1>
                    <hr>
                    <p><strong>Data:</strong> ${new Date().toLocaleString()}</p>
                    <p><strong>Projetado por:</strong> Thiago Souza</p>
                    <br>
            `;
            
            const byType = {};
            components.forEach(comp => {
                const type = comp.type;
                if (!byType[type]) byType[type] = [];
                byType[type].push(comp);
            });
            
            for (const [type, comps] of Object.entries(byType)) {
                listHTML += `<h2>📌 ${type.toUpperCase()}</h2>
                    <table style="width:100%;border-collapse:collapse;">
                        <tr style="background:#005f99;color:white;">
                            <th style="padding:8px;text-align:left;">Equipamento</th>
                            <th style="padding:8px;text-align:left;">IP</th>
                            <th style="padding:8px;text-align:left;">Posição</th>
                        </tr>`;
                comps.forEach(comp => {
                    listHTML += `
                        <tr>
                            <td style="padding:8px;">✅ ${comp.name}</td>
                            <td style="padding:8px;">${comp.ip || 'Não configurado'}</td>
                            <td style="padding:8px;">X: ${Math.round(comp.x)}, Y: ${Math.round(comp.y)}</td>
                        </tr>`;
                });
                listHTML += '</table>';
            }
            
            if (connections.length > 0) {
                listHTML += `
                    <h2>🔌 CONEXÕES</h2>
                    <table style="width:100%;border-collapse:collapse;">
                        <tr style="background:#005f99;color:white;">
                            <th style="padding:8px;text-align:left;">Origem</th>
                            <th style="padding:8px;text-align:left;">Destino</th>
                            <th style="padding:8px;text-align:left;">Tipo</th>
                        </tr>`;
                connections.forEach(conn => {
                    const fromComp = components.find(c => c.id === conn.from);
                    const toComp = components.find(c => c.id === conn.to);
                    const cableInfo = cableColors[conn.type] || cableColors['cat6'];
                    if (fromComp && toComp) {
                        listHTML += `
                            <tr>
                                <td style="padding:8px;">${fromComp.name}</td>
                                <td style="padding:8px;">${toComp.name}</td>
                                <td style="padding:8px;">${cableInfo.name}</td>
                            </tr>`;
                    }
                });
                listHTML += '</table>';
            }
            
            listHTML += `
                <br><hr>
                <p><strong>Total de Equipamentos:</strong> ${components.length}</p>
                <p><strong>Total de Conexões:</strong> ${connections.length}</p>
                <p><strong>Total de Formas:</strong> ${shapes.length}</p>
                <br>
                <p style="text-align:center;font-size:11px;color:#888;">
                    Desenvolvido por Thiago Souza - Analista de Tecnologia | Unidade 2 - São José do Rio Preto
                </p>
            </div>`;
            
            const imgData = canvas.toDataURL('image/png');
            const pdfWindow = window.open('', '_blank');
            pdfWindow.document.write(`
                <html>
                    <head>
                        <title>Projeto CFTV - Relatório Completo</title>
                        <style>@media print{.page-break{page-break-before:always;}}</style>
                    </head>
                    <body style="margin:0;padding:20px;">
                        <div style="text-align:center;margin-bottom:20px;">
                            <img src="${imgData}" style="max-width:100%;">
                        </div>
                        <div class="page-break"></div>
                        ${listHTML}
                        <script>window.print();<\\/script>
                    </body>
                </html>
            `);
            setTimeout(() => draw(), 500);
            showToast('📄 PDF com lista de equipamentos gerado!');
        }
        
        function generateBudget() {
            let list = '📋 LISTA DE EQUIPAMENTOS - PROJETO CFTV\\n' + '='.repeat(50) + '\\n\\nData: ' + new Date().toLocaleString() + '\\n\\n';
            
            const byType = {};
            components.forEach(comp => {
                const type = comp.type;
                if (!byType[type]) byType[type] = [];
                byType[type].push(comp);
            });
            
            for (const [type, comps] of Object.entries(byType)) {
                list += `\\n📌 ${type.toUpperCase()}:\\n${'-'.repeat(30)}\\n`;
                comps.forEach(comp => {
                    list += `   ✅ ${comp.name}`;
                    if (comp.ip) list += ` (IP: ${comp.ip})`;
                    list += '\\n';
                });
            }
            
            list += `\\n📡 CONEXÕES:\\n${'-'.repeat(30)}\\n`;
            connections.forEach(conn => {
                const fromComp = components.find(c => c.id === conn.from);
                const toComp = components.find(c => c.id === conn.to);
                const cableInfo = cableColors[conn.type] || cableColors['cat6'];
                if (fromComp && toComp) {
                    list += `   🔗 ${fromComp.name} → ${toComp.name} (${cableInfo.name})\\n`;
                }
            });
            
            list += `\\n${'='.repeat(50)}\\n📊 TOTAL DE EQUIPAMENTOS: ${components.length}\\n🔌 TOTAL DE CONEXÕES: ${connections.length}\\n📐 TOTAL DE FORMAS: ${shapes.length}\\n`;
            
            const blob = new Blob([list], {type: 'text/plain;charset=utf-8'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `orcamento_${Date.now()}.txt`;
            a.click();
            showToast('💰 Orçamento gerado e baixado!');
        }
        
        function toggleGrid() {
            showGrid = !showGrid;
            showToast(showGrid ? '🔲 Grade visível' : '🔳 Grade oculta');
        }
        
        function setShapeMode(mode) {
            shapeMode = mode;
            document.querySelectorAll('.shape-btn').forEach(btn => btn.classList.remove('active'));
            if (event && event.target) event.target.classList.add('active');
            showToast(`Modo: Desenhar ${getShapeName(mode)} - Clique e arraste no canvas`);
        }
        
        function cancelShapeMode() {
            shapeMode = null;
            drawingPreview = null;
            document.querySelectorAll('.shape-btn').forEach(btn => btn.classList.remove('active'));
            showToast('Modo de desenho cancelado');
        }
        
        function toggleShapesToolbar() {
            const toolbar = document.getElementById('shapesToolbar');
            toolbar.style.display = toolbar.style.display === 'none' ? 'flex' : 'none';
        }
        
        function togglePalette() {
            const palette = document.getElementById('palette');
            const toggleBtn = document.querySelector('.toggle-palette');
            palette.classList.toggle('collapsed');
            toggleBtn.innerHTML = palette.classList.contains('collapsed') ? '▶' : '◀';
            if (window.innerWidth <= 768) {
                if (!palette.classList.contains('collapsed')) {
                    document.getElementById('mobileOverlay').style.display = 'block';
                } else {
                    document.getElementById('mobileOverlay').style.display = 'none';
                }
            }
        }
        
        function toggleMobilePalette() {
            const palette = document.getElementById('palette');
            const overlay = document.getElementById('mobileOverlay');
            if (palette.classList.contains('collapsed')) {
                palette.classList.remove('collapsed');
                document.querySelector('.toggle-palette').innerHTML = '◀';
                overlay.style.display = 'block';
            } else {
                palette.classList.add('collapsed');
                document.querySelector('.toggle-palette').innerHTML = '▶';
                overlay.style.display = 'none';
            }
        }
        
        function closeMobilePalette() {
            const palette = document.getElementById('palette');
            if (!palette.classList.contains('collapsed')) {
                palette.classList.add('collapsed');
                document.querySelector('.toggle-palette').innerHTML = '▶';
            }
            document.getElementById('mobileOverlay').style.display = 'none';
        }
        
        function closePropertiesPanel() {
            document.getElementById('propertiesPanel').classList.remove('open');
        }
        
        function openProperties() {
            document.getElementById('propertiesPanel').classList.add('open');
        }
        
        function closeProperties() {
            document.getElementById('propertiesPanel').classList.remove('open');
        }
        
        function readImageAsBase64(file) {
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.readAsDataURL(file);
            });
        }
        
        // ==================== FUNÇÕES DE LOGIN ====================
        async function doLogin() {
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();
            if (data.success) {
                currentUser = username;
                userRole = data.role;
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
                
                await loadDefaultConfig();
                await loadDefaultConnections();
                await loadUserData();
                showToast(`Bem-vindo, ${username}!`);
            } else {
                document.getElementById('loginError').style.display = 'block';
            }
        }
        
        function logout() {
            fetch('/api/logout', { method: 'POST' }).then(() => location.reload());
        }
        
        async function openUserManagement() {
            const response = await fetch('/api/users');
            const users = await response.json();
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">👥 Gerenciar Usuários</h3>
                    <div class="user-list" id="userList"></div>
                    <div style="margin-top:15px;">
                        <input type="text" id="newUsername" placeholder="Novo usuário">
                        <input type="password" id="newPassword" placeholder="Senha">
                        <select id="newRole"><option value="viewer">Visualizador</option><option value="admin">Administrador</option></select>
                        <button class="btn btn-primary" style="margin-top:10px;" onclick="addUser()">➕ Adicionar</button>
                    </div>
                    <div class="modal-buttons"><button class="btn btn-danger" onclick="closeModal()">Fechar</button></div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            renderUserList(users);
        }
        
        function renderUserList(users) {
            const container = document.getElementById('userList');
            if (!container) return;
            container.innerHTML = '';
            for (const [username, userData] of Object.entries(users)) {
                const userDiv = document.createElement('div');
                userDiv.className = 'user-item';
                userDiv.innerHTML = `
                    <div>
                        <strong>${username}</strong><br>
                        <small>${userData.role} | Criado: ${new Date(userData.created_at).toLocaleDateString()}</small>
                    </div>
                    <div class="user-actions">
                        ${userData.role !== 'master' ? `<button onclick="deleteUser('${username}')" title="Excluir">🗑</button>` : '<span style="color:var(--text-accent);">Master</span>'}
                    </div>
                `;
                container.appendChild(userDiv);
            }
        }
        
        async function addUser() {
            const username = document.getElementById('newUsername').value;
            const password = document.getElementById('newPassword').value;
            const role = document.getElementById('newRole').value;
            if (!username || !password) {
                showToast('Preencha todos os campos');
                return;
            }
            const response = await fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, role })
            });
            const data = await response.json();
            if (data.success) {
                showToast('✅ Usuário adicionado!');
                closeModal();
                openUserManagement();
            } else {
                showToast(data.error);
            }
        }
        
        async function deleteUser(username) {
            if (confirm(`Deseja excluir o usuário "${username}"?`)) {
                const response = await fetch(`/api/users/${username}`, { method: 'DELETE' });
                const data = await response.json();
                if (data.success) {
                    showToast('✅ Usuário excluído!');
                    closeModal();
                    openUserManagement();
                } else {
                    showToast(data.error);
                }
            }
        }
        
        async function resetToDefaultConfig() {
            if (userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem restaurar as configurações padrão');
                return;
            }
            if (confirm('⚠️ Isso irá restaurar todas as categorias e dispositivos para a configuração padrão. Continuar?')) {
                try {
                    const response = await fetch('/api/reset_default_config', { method: 'POST' });
                    const data = await response.json();
                    if (data.success) {
                        await loadDefaultConfig();
                        categories = JSON.parse(JSON.stringify(defaultCategories));
                        customDevices = [];
                        saveUserData();
                        saveGlobalLibrary(); // Adicionado
                        renderPalette();
                        showToast('✅ Configurações restauradas para o padrão!');
                    }
                } catch(e) {
                    showToast('Erro ao restaurar configurações');
                }
            }
        }
        
        // ==================== MATRIX ANIMATION ====================
        function createMatrixAnimation(containerId, isLogin = false) {
            const container = document.getElementById(containerId);
            if (!container) return;
            container.innerHTML = '';
            const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
            const columns = Math.floor(window.innerWidth / 20);
            for (let i = 0; i < columns; i++) {
                const column = document.createElement('div');
                column.className = 'matrix-column';
                column.style.left = (i * 20) + 'px';
                column.style.animationDuration = (Math.random() * 5 + 5) + 's';
                column.style.animationDelay = (Math.random() * 5) + 's';
                let text = '';
                for (let j = 0; j < 40; j++) text += chars[Math.floor(Math.random() * chars.length)] + '\\n';
                column.textContent = text;
                container.appendChild(column);
            }
        }
        
        // ==================== SLIDES ====================
        let slideIndex = 0;
        const slides = document.querySelectorAll('.intro-slide');
        const dots = document.querySelectorAll('.dot');
        
        function showSlide(index) {
            if (slides.length === 0) return;
            if (index >= slides.length) index = 0;
            if (index < 0) index = slides.length - 1;
            slides.forEach(slide => slide.classList.remove('active'));
            dots.forEach(dot => dot.classList.remove('active'));
            slides[index].classList.add('active');
            dots[index].classList.add('active');
            slideIndex = index;
        }
        
        window.nextSlide = () => showSlide(slideIndex + 1);
        window.prevSlide = () => showSlide(slideIndex - 1);
        window.currentSlide = (index) => showSlide(index);
        
        function closeIntroAndShowLogin() {
            document.getElementById('introScreen').style.display = 'none';
            document.getElementById('loginModal').style.display = 'flex';
            createMatrixAnimation('matrixBg', true);
        }
        
        // ==================== CARREGAMENTO DE IMAGENS DO DEV ====================
        function loadDevImages() {
            const loginContainer = document.getElementById('loginDevImageContainer');
            const loginImg = document.getElementById('loginDevImage');
            const badgeImg = document.getElementById('badgeDevImage');
            const devSlideImg = document.getElementById('devSlideImg');
            const devSlideContainer = document.getElementById('devSlideImage');
            
            const img = new Image();
            img.onload = function() {
                if (loginImg) { loginImg.src = img.src; loginImg.style.display = 'block'; }
                if (badgeImg) badgeImg.src = img.src;
                if (devSlideImg) { devSlideImg.src = img.src; devSlideImg.style.display = 'block'; }
                if (devSlideContainer) devSlideContainer.style.background = 'transparent';
                if (loginContainer) loginContainer.style.background = 'transparent';
            };
            img.onerror = function() {
                if (devImageBase64) {
                    const dataUrl = 'data:image/png;base64,' + devImageBase64;
                    if (loginImg) { loginImg.src = dataUrl; loginImg.style.display = 'block'; }
                    if (badgeImg) badgeImg.src = dataUrl;
                    if (devSlideImg) { devSlideImg.src = dataUrl; devSlideImg.style.display = 'block'; }
                    if (devSlideContainer) devSlideContainer.style.background = 'transparent';
                    if (loginContainer) loginContainer.style.background = 'transparent';
                } else {
                    if (loginImg) loginImg.style.display = 'none';
                    if (devSlideImg) devSlideImg.style.display = 'none';
                    if (loginContainer) {
                        loginContainer.style.background = '#005f99';
                        loginContainer.innerHTML = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:white;font-size:40px;font-weight:bold;">TS</div>';
                    }
                    if (devSlideContainer) {
                        devSlideContainer.style.background = '#005f99';
                        devSlideContainer.innerHTML = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:white;font-size:40px;font-weight:bold;">TS</div>';
                    }
                    if (badgeImg) {
                        badgeImg.style.display = 'none';
                        badgeImg.parentElement.style.background = '#005f99';
                        badgeImg.parentElement.innerHTML = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:white;font-size:16px;font-weight:bold;">TS</div>';
                    }
                }
            };
            img.src = '/static/dev.png?' + Date.now();
        }
        
        // ==================== INICIALIZAÇÃO ====================
        // Event listeners do canvas
        canvas.addEventListener('dragover', (e) => e.preventDefault());
        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            const {x, y} = getMousePos(e);
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            const component = {
                id: Date.now(),
                type: data.type || 'custom',
                subtype: data.subtype || '',
                name: data.name,
                x: x,
                y: y,
                icon: data.icon || '📦',
                iconFile: data.iconFile || null,
                color: data.color || '#005f99',
                imageData: data.imageData || null,
                angle: 0,
                fov: 80,
                rotation: 0,
                customImage: null,
                customIconTemp: null,
                customImageTemp: null,
                ip: '',
                port: 80,
                username: '',
                password: ''
            };
            components.push(component);
            showToast(`✅ ${component.name} adicionado ao projeto!`);
            saveUserData();
        });
        
        canvas.addEventListener('touchstart', handleStart, { passive: false });
        canvas.addEventListener('touchmove', handleMove, { passive: false });
        canvas.addEventListener('touchend', handleEnd);
        canvas.addEventListener('touchcancel', handleEnd);
        
        canvas.addEventListener('mousedown', handleStart);
        canvas.addEventListener('mousemove', handleMove);
        canvas.addEventListener('mouseup', handleEnd);
        canvas.addEventListener('click', handleClick);
        canvas.addEventListener('contextmenu', handleContextMenu);
        
        // Inicialização
        loadDevImages();
        createMatrixAnimation('introMatrixBg');
        closeProperties();
        
        setTimeout(() => {
            const splash = document.getElementById('splashScreen');
            if (splash) splash.style.display = 'none';
        }, 3000);
        
        // Expor funções globalmente
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
        window.openAddDeviceModal = openAddDeviceModal;
        window.openAddConnectionModal = openAddConnectionModal;
        window.addDeviceToCategory = addDeviceToCategory;
        window.addCategory = addCategory;
        window.addDevice = addDevice;
        window.editCategory = editCategory;
        window.editDevice = editDevice;
        window.deleteCategory = deleteCategory;
        window.deleteDevice = deleteDevice;
        window.updateCategory = updateCategory;
        window.updateDevice = updateDevice;
        window.editCustomDevice = editCustomDevice;
        window.deleteCustomDevice = deleteCustomDevice;
        window.addCustomDevice = addCustomDevice;
        window.doLogin = doLogin;
        window.logout = logout;
        window.openUserManagement = openUserManagement;
        window.addUser = addUser;
        window.deleteUser = deleteUser;
        window.setShapeMode = setShapeMode;
        window.cancelShapeMode = cancelShapeMode;
        window.toggleShapesToolbar = toggleShapesToolbar;
        window.deleteShape = deleteShape;
        window.toggleGrid = toggleGrid;
        window.resetToDefaultConfig = resetToDefaultConfig;
        window.openBackgroundModal = openBackgroundModal;
        window.updateBackgroundOpacity = updateBackgroundOpacity;
        window.removeBackground = removeBackground;
        window.importLocalImage = importLocalImage;
        window.selectBackgroundImage = selectBackgroundImage;
        window.closeIntroAndShowLogin = closeIntroAndShowLogin;
        window.closePropertiesPanel = closePropertiesPanel;
        window.toggleMobilePalette = toggleMobilePalette;
        window.closeMobilePalette = closeMobilePalette;
        window.deleteSelectedShape = deleteSelectedShape;
        window.flipComponent = flipComponent;
        window.flipComponentById = flipComponentById;
        window.nextSlide = nextSlide;
        window.prevSlide = prevSlide;
        window.currentSlide = currentSlide;
        window.deleteSelectedItems = deleteSelectedItems;
        window.updateSelectedConnection = updateSelectedConnection;
        window.deleteSelectedConnection = deleteSelectedConnection;
        window.flipShape = flipShape;
        window.duplicateShape = duplicateShape;
        window.openPermanentIconModal = openPermanentIconModal;
        window.applyPermanentIcon = applyPermanentIcon;
        window.openPermanentIconModalFromMenu = openPermanentIconModalFromMenu;
        window.addCustomConnection = addCustomConnection;
        window.deleteCustomConnection = deleteCustomConnection;
        window.editCustomConnection = editCustomConnection;
        window.addConnectionToCategory = addConnectionToCategory;
        window.addConnectionToCategoryConfirm = addConnectionToCategoryConfirm;
        window.openCategoryIconModal = openCategoryIconModal;
        window.applyCategoryIcon = applyCategoryIcon;
        window.openConnectionIconModal = openConnectionIconModal;
        window.applyConnectionIcon = applyConnectionIcon;
        window.openDeviceIconModal = openDeviceIconModal;
        window.applyDeviceIcon = applyDeviceIcon;
        window.openCustomDeviceIconModal = openCustomDeviceIconModal;
        window.applyCustomDeviceIcon = applyCustomDeviceIcon;
        window.addConnectionFromModal = addConnectionFromModal;
        window.renderConnectionsPalette = renderConnectionsPalette;
        window.renderPalette = renderPalette;
    </script>
</body>
</html>
"""

# O bloco if __name__ == '__main__': app.run() FOI REMOVIDO INTENCIONALMENTE.
# O PythonAnywhere utiliza o próprio servidor WSGI. Deixar o app.run() causa erro 502.
