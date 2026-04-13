# projetize_completo.py - Sistema Para CFTV e Redes e muito mais...
import os
import json
import base64
import hashlib
import shutil
from flask import Flask, render_template_string, request, jsonify, send_file, session, url_for
from werkzeug.utils import secure_filename
from functools import wraps
import uuid
from io import BytesIO
import html
import time
import threading
from datetime import datetime
import mimetypes

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['SECRET_KEY'] = 'projetize-super-secret-key-2024'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

UPLOAD_FOLDER = 'uploads'
ICONS_FOLDER = os.path.join(UPLOAD_FOLDER, 'icons')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ICONS_FOLDER, exist_ok=True)

projects = {}
users = {}

# Caminho da imagem do desenvolvedor
DEV_IMAGE_PATH = '/home/thiago03/Área de trabalho/portifolio/meuportifolio01/dev.png'

def get_dev_image_base64():
    try:
        if os.path.exists(DEV_IMAGE_PATH):
            with open(DEV_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
                return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"Erro ao carregar imagem do desenvolvedor: {e}")
    return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

users['thiago03'] = {
    'password': hash_password('Thiago@000333'),
    'role': 'master',
    'name': 'Thiago Souza',
    'created_at': datetime.now().isoformat()
}

dev_image_data = get_dev_image_base64() or ""

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

# Função para salvar imagem de ícone
def save_icon_image(image_data, old_filename=None):
    if old_filename and os.path.exists(os.path.join(ICONS_FOLDER, old_filename)):
        try:
            os.remove(os.path.join(ICONS_FOLDER, old_filename))
        except:
            pass
    
    if image_data and image_data.startswith('data:image'):
        # Extrair o formato da imagem
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
        filepath = os.path.join(ICONS_FOLDER, filename)
        
        try:
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(image_data))
            return filename
        except Exception as e:
            print(f"Erro ao salvar imagem: {e}")
            return None
    
    return None

# Função para deletar imagem de ícone
def delete_icon_image(filename):
    if filename and os.path.exists(os.path.join(ICONS_FOLDER, filename)):
        try:
            os.remove(os.path.join(ICONS_FOLDER, filename))
            return True
        except:
            pass
    return False

# Função para obter URL da imagem
def get_icon_url(filename):
    if filename and os.path.exists(os.path.join(ICONS_FOLDER, filename)):
        return f'/uploads/icons/{filename}'
    return None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Projetize - Sistema para  CFTV, Redes e muito mais...</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f2f5;
            overflow: hidden;
            transition: all 0.3s ease;
        }

        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-tertiary: #e9ecef;
            --bg-card: #ffffff;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --text-accent: #005f99;
            --border-color: #dee2e6;
            --button-primary: #005f99;
            --button-primary-hover: #004d7a;
            --button-secondary: #e9ecef;
            --button-secondary-hover: #dee2e6;
            --shadow: rgba(0, 95, 153, 0.2);
            --grid-color: #e0e0e0;
            --active-tab: #005f99;
        }

        .rgb-line {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, #005f99, #0099cc, #00ccff, #005f99);
            background-size: 300% 100%;
            animation: rgbMove 3s linear infinite;
            z-index: 10000;
        }

        @keyframes rgbMove {
            0% { background-position: 0% 0%; }
            100% { background-position: 300% 100%; }
        }

        .login-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #001a2e, #00264d);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 20000;
            overflow: hidden;
        }

        .matrix-bg {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: monospace;
            color: #00ccff;
            z-index: 0;
            opacity: 0.4;
        }

        .matrix-column {
            position: absolute;
            top: -100%;
            animation: matrixFall linear infinite;
            white-space: pre;
            font-size: 16px;
            line-height: 1.2;
            opacity: 0.7;
        }

        @keyframes matrixFall {
            0% { top: -100%; }
            100% { top: 100%; }
        }

        .login-dev-container {
            position: relative;
            z-index: 2;
            width: 100%;
            max-width: 500px;
            background: rgba(0, 38, 77, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            border: 1px solid #00ccff;
            box-shadow: 0 0 30px rgba(0, 204, 255, 0.3);
        }

        .login-dev-image {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            margin: 0 auto 20px;
            overflow: hidden;
            border: 3px solid #00ccff;
            box-shadow: 0 0 30px rgba(0, 204, 255, 0.5);
            animation: borderGlow 2s ease-in-out infinite;
        }

        @keyframes borderGlow {
            0%, 100% { border-color: #00ccff; box-shadow: 0 0 20px #00ccff; }
            50% { border-color: #0099cc; box-shadow: 0 0 40px #0099cc; }
        }

        .login-dev-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .login-dev-name {
            font-size: 24px;
            color: #00ccff;
            margin-bottom: 5px;
            font-weight: bold;
        }

        .login-dev-role {
            font-size: 12px;
            color: #88ccff;
            margin-bottom: 20px;
        }

        .login-logo {
            font-size: 50px;
            margin-bottom: 15px;
        }

        .login-title {
            font-size: 28px;
            color: #00ccff;
            margin-bottom: 10px;
            font-weight: bold;
        }

        .login-subtitle {
            color: #88ccff;
            font-size: 12px;
            margin-bottom: 25px;
        }

        .login-input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            background: rgba(0, 38, 77, 0.8);
            border: 1px solid #00ccff;
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
        }

        .login-input:focus {
            outline: none;
            border-color: #00ccff;
            box-shadow: 0 0 10px rgba(0, 204, 255, 0.5);
        }

        .login-input::placeholder {
            color: #88ccff;
        }

        .login-btn {
            width: 100%;
            padding: 12px;
            background: #00ccff;
            border: none;
            border-radius: 8px;
            color: #001a2e;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 20px;
            transition: all 0.3s;
        }

        .login-btn:hover {
            background: #0099cc;
            transform: scale(1.02);
            box-shadow: 0 0 20px rgba(0, 204, 255, 0.5);
        }

        .login-error {
            color: #ff4444;
            font-size: 12px;
            margin-top: 15px;
            display: none;
        }

        .login-footer {
            margin-top: 25px;
            padding-top: 15px;
            border-top: 1px solid #00ccff;
            font-size: 11px;
            color: #88ccff;
        }

        .login-footer a {
            color: #00ccff;
            text-decoration: none;
        }

        .login-footer a:hover {
            text-decoration: underline;
        }

        .splash-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #001a2e, #00264d);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 15000;
            animation: fadeOut 4s ease-in-out forwards;
            overflow: hidden;
        }

        @keyframes fadeOut {
            0% { opacity: 1; visibility: visible; }
            70% { opacity: 1; }
            100% { opacity: 0; visibility: hidden; }
        }

        .splash-content {
            text-align: center;
            z-index: 2;
        }

        .splash-logo {
            font-size: 100px;
            margin-bottom: 20px;
            animation: logoPulse 1.5s ease-in-out infinite;
        }

        @keyframes logoPulse {
            0%, 100% { transform: scale(1); text-shadow: 0 0 20px #00ccff; }
            50% { transform: scale(1.05); text-shadow: 0 0 40px #00ccff; }
        }

        .splash-title {
            font-size: 48px;
            background: linear-gradient(45deg, #00ccff, #0099cc, #005f99);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 10px;
        }

        .splash-subtitle {
            color: #88ccff;
            font-size: 16px;
        }

        .dev-badge {
            position: fixed;
            top: 60px;
            right: 10px;
            width: 45px;
            height: 45px;
            border-radius: 50%;
            background: var(--bg-tertiary);
            border: 2px solid var(--border-color);
            cursor: pointer;
            z-index: 1000;
            overflow: hidden;
            transition: all 0.3s ease;
            box-shadow: 0 0 10px var(--shadow);
        }

        .dev-badge:hover {
            width: 280px;
            border-radius: 25px;
            background: var(--bg-tertiary);
        }

        .dev-badge-img {
            width: 41px;
            height: 41px;
            border-radius: 50%;
            object-fit: cover;
            float: left;
        }

        .dev-badge-info {
            display: none;
            float: left;
            padding: 5px 10px;
            color: var(--text-primary);
            font-size: 11px;
            white-space: nowrap;
        }

        .dev-badge:hover .dev-badge-info {
            display: block;
        }

        .dev-badge-name {
            color: var(--text-accent);
            font-weight: bold;
        }

        .toolbar {
            background: var(--bg-secondary);
            padding: 8px 15px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            border-bottom: 2px solid var(--border-color);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            z-index: 100;
            position: relative;
        }

        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }

        .btn-primary { background: var(--button-primary); color: #fff; }
        .btn-primary:hover { background: var(--button-primary-hover); transform: scale(1.02); }
        .btn-secondary { background: var(--button-secondary); color: var(--text-primary); border: 1px solid var(--border-color); }
        .btn-secondary:hover { background: var(--button-secondary-hover); transform: scale(1.02); }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-info { background: var(--button-secondary); color: var(--text-primary); }

        .user-info {
            display: flex;
            align-items: center;
            gap: 10px;
            background: var(--bg-tertiary);
            padding: 4px 12px;
            border-radius: 20px;
            color: var(--text-primary);
            font-size: 12px;
        }

        .user-role {
            background: var(--text-accent);
            color: #fff;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
        }

        .main-container {
            display: flex;
            height: calc(100vh - 52px);
            position: relative;
        }

        .palette {
            width: 280px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            overflow-y: auto;
            padding: 10px;
            border-right: 2px solid var(--border-color);
            transition: width 0.3s ease;
            position: relative;
        }

        .palette.collapsed {
            width: 50px;
            min-width: 50px;
        }

        .palette::-webkit-scrollbar {
            width: 10px;
        }

        .palette::-webkit-scrollbar-track {
            background: var(--bg-primary);
            border-radius: 5px;
        }

        .palette::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 5px;
        }

        .toggle-palette {
            position: sticky;
            top: 10px;
            right: -12px;
            float: right;
            background: var(--button-primary);
            border: none;
            color: #fff;
            width: 24px;
            height: 40px;
            border-radius: 0 8px 8px 0;
            cursor: pointer;
            z-index: 10;
            font-size: 12px;
            margin-bottom: 10px;
        }

        .category {
            margin-bottom: 15px;
            clear: both;
        }

        .category-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .category h3 {
            font-size: 12px;
            color: var(--text-accent);
            border-left: 3px solid var(--border-color);
            padding-left: 8px;
        }

        .category-actions {
            display: flex;
            gap: 5px;
        }

        .category-actions button {
            background: none;
            border: none;
            color: var(--text-accent);
            cursor: pointer;
            font-size: 12px;
            padding: 2px 5px;
            border-radius: 3px;
        }

        .component {
            background: var(--bg-card);
            border-radius: 8px;
            padding: 6px 10px;
            margin-bottom: 6px;
            cursor: grab;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.2s;
            border: 1px solid var(--border-color);
            position: relative;
        }

        .component:hover {
            background: var(--bg-secondary);
            transform: translateX(3px);
            border-color: var(--text-accent);
        }

        .component-icon { 
            font-size: 20px;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .component-icon img {
            width: 24px;
            height: 24px;
            object-fit: contain;
        }
        
        .component-info { flex: 1; }
        .component-name { font-size: 12px; font-weight: 600; }
        .component-desc { font-size: 9px; opacity: 0.7; }
        
        .component-actions {
            position: absolute;
            right: 5px;
            top: 50%;
            transform: translateY(-50%);
            display: none;
            gap: 5px;
        }
        
        .component:hover .component-actions {
            display: flex;
        }
        
        .component-actions button {
            background: var(--button-primary);
            border: none;
            color: #fff;
            border-radius: 3px;
            cursor: pointer;
            font-size: 10px;
            padding: 2px 4px;
        }

        .shapes-toolbar {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--bg-secondary);
            padding: 8px 15px;
            border-radius: 30px;
            display: flex;
            gap: 8px;
            z-index: 150;
            border: 1px solid var(--border-color);
            flex-wrap: wrap;
            max-width: 90%;
            justify-content: center;
        }

        .shape-btn {
            background: var(--bg-tertiary);
            border: none;
            color: var(--text-primary);
            padding: 6px 12px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }

        .shape-btn:hover, .shape-btn.active {
            background: var(--button-primary);
            color: #fff;
            transform: scale(1.05);
        }

        .canvas-area {
            flex: 1;
            background: var(--bg-primary);
            overflow: auto;
            position: relative;
        }

        .canvas-area::-webkit-scrollbar {
            width: 12px;
            height: 12px;
        }

        .canvas-area::-webkit-scrollbar-track {
            background: #e9ecef;
            border-radius: 6px;
        }

        .canvas-area::-webkit-scrollbar-thumb {
            background: #005f99;
            border-radius: 6px;
        }

        .canvas-area::-webkit-scrollbar-thumb:hover {
            background: #004d7a;
        }

        .canvas-area::-webkit-scrollbar-corner {
            background: #e9ecef;
        }

        #canvas {
            background: var(--bg-primary);
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            cursor: crosshair;
            display: block;
            margin: 20px auto;
        }

        .properties {
            width: 0;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            padding: 0;
            overflow-y: auto;
            border-left: none;
            transition: all 0.3s ease;
            position: relative;
        }

        .properties.open {
            width: 320px;
            padding: 15px;
            border-left: 2px solid var(--border-color);
        }

        .properties::-webkit-scrollbar {
            width: 10px;
        }

        .properties::-webkit-scrollbar-track {
            background: var(--bg-primary);
            border-radius: 5px;
        }

        .properties::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 5px;
        }

        .property-group {
            margin-bottom: 12px;
        }

        .property-group label {
            display: block;
            font-size: 11px;
            margin-bottom: 4px;
            color: var(--text-accent);
        }

        .property-group input, .property-group select, .property-group textarea {
            width: 100%;
            padding: 6px;
            border-radius: 5px;
            border: none;
            background: var(--bg-card);
            color: var(--text-primary);
            font-size: 12px;
            border: 1px solid var(--border-color);
        }

        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 3000;
        }

        .modal-content {
            background: var(--bg-secondary);
            padding: 25px;
            border-radius: 12px;
            width: 500px;
            max-width: 90%;
            max-height: 80%;
            overflow-y: auto;
            border: 1px solid var(--border-color);
        }

        .modal-content input, .modal-content select, .modal-content textarea {
            width: 100%;
            padding: 8px;
            margin: 8px 0;
            background: var(--bg-tertiary);
            border: none;
            border-radius: 5px;
            color: var(--text-primary);
        }

        .modal-buttons {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .user-list {
            max-height: 300px;
            overflow-y: auto;
            margin: 15px 0;
        }

        .user-item {
            background: var(--bg-tertiary);
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .user-actions button {
            background: none;
            border: none;
            cursor: pointer;
            margin-left: 8px;
            font-size: 16px;
        }

        .recording {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(220, 53, 69, 0.9);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            z-index: 1000;
            display: none;
            animation: blink 1s infinite;
        }

        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--button-primary);
            color: #fff;
            padding: 10px 20px;
            border-radius: 5px;
            z-index: 4000;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        .selection-rect {
            position: absolute;
            border: 2px dashed #005f99;
            background: rgba(0, 95, 153, 0.2);
            display: none;
            pointer-events: none;
            z-index: 1000;
        }

        .context-menu {
            position: fixed;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 5px 0;
            z-index: 2000;
            display: none;
            min-width: 180px;
        }

        .context-menu-item {
            padding: 8px 15px;
            cursor: pointer;
            color: var(--text-primary);
            font-size: 12px;
            transition: all 0.2s;
        }

        .context-menu-item:hover {
            background: var(--button-primary);
            color: #fff;
        }

        .selection-info {
            position: fixed;
            bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--bg-secondary);
            color: var(--text-primary);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            z-index: 1000;
            pointer-events: none;
            border: 1px solid var(--border-color);
        }

        @keyframes sensorDetection {
            0% { transform: translate(-50%, -50%) scale(0.5); opacity: 0.8; }
            50% { transform: translate(-50%, -50%) scale(1.2); opacity: 0.5; }
            100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
        }

        @keyframes signalWave {
            0% { transform: scale(0.8); opacity: 0; }
            50% { transform: scale(1.2); opacity: 0.8; }
            100% { transform: scale(1.5); opacity: 0; }
        }
        
        @keyframes radioWave {
            0% { transform: scale(0.5); opacity: 0; box-shadow: 0 0 0 0 currentColor; }
            50% { transform: scale(1); opacity: 0.6; box-shadow: 0 0 0 5px currentColor; }
            100% { transform: scale(1.3); opacity: 0; box-shadow: 0 0 0 10px currentColor; }
        }
        
        @keyframes ookWave {
            0% { transform: scale(0.6); opacity: 0; border-width: 2px; }
            50% { transform: scale(1); opacity: 0.8; border-width: 1px; }
            100% { transform: scale(1.4); opacity: 0; border-width: 0px; }
        }
        
        @keyframes fskWave {
            0% { transform: rotate(0deg) scale(0.5); opacity: 0; }
            50% { transform: rotate(180deg) scale(1); opacity: 0.8; }
            100% { transform: rotate(360deg) scale(1.3); opacity: 0; }
        }
        
        @keyframes amtWave {
            0% { transform: translateY(0) scale(0.5); opacity: 0; }
            25% { transform: translateY(-10px) scale(0.8); opacity: 0.5; }
            50% { transform: translateY(0) scale(1); opacity: 0.8; }
            75% { transform: translateY(10px) scale(0.8); opacity: 0.5; }
            100% { transform: translateY(0) scale(1.2); opacity: 0; }
        }
        
        .connection-animation {
            position: absolute;
            pointer-events: none;
            z-index: 1000;
        }
        
        .connection-wave {
            position: absolute;
            border-radius: 50%;
            animation: signalWave 1.5s ease-out infinite;
        }
        
        .radio-wave {
            position: absolute;
            border-radius: 50%;
            animation: radioWave 1.5s ease-out infinite;
        }
        
        .ook-wave {
            position: absolute;
            border-radius: 50%;
            border-style: solid;
            animation: ookWave 1.5s ease-out infinite;
        }
        
        .fsk-wave {
            position: absolute;
            border-radius: 50%;
            animation: fskWave 1.5s ease-out infinite;
        }
        
        .amt-wave {
            position: absolute;
            border-radius: 50%;
            animation: amtWave 1.5s ease-out infinite;
        }

        @media (max-width: 768px) {
            .palette { width: 220px; }
            .palette.collapsed { width: 45px; }
            .properties.open { width: 260px; }
            .toolbar { gap: 5px; }
            .btn { padding: 4px 8px; font-size: 10px; }
            .login-dev-container { padding: 25px; margin: 20px; }
            .login-dev-image { width: 120px; height: 120px; }
            .login-dev-name { font-size: 20px; }
        }
    </style>
</head>
<body>
    <div class="rgb-line"></div>

    <div class="login-modal" id="loginModal">
        <div class="matrix-bg" id="matrixBg"></div>
        <div class="login-dev-container">
            <div class="login-dev-image">
                <img id="loginDevImage" src="" alt="Thiago Souza">
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
                Todos os direitos reservados © 2024<br>
                <a href="https://wa.me/5517996009537" target="_blank">📱 Contato: (17) 99600-9537</a>
            </div>
            <div class="login-error" id="loginError">Usuário ou senha inválidos</div>
        </div>
    </div>

    <div class="splash-screen" id="splashScreen">
        <div class="splash-content">
            <div class="splash-logo">🎥🔒🌐</div>
            <div class="splash-title">PROJETIZE</div>
            <div class="splash-subtitle">Sistema Para CFTV, Redes e muito mais...</div>
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

    <div class="recording" id="recordingIndicator">🔴 GRAVANDO...</div>
    <div class="selection-info" id="selectionInfo"></div>
    <div class="selection-rect" id="selectionRect"></div>
    <div class="context-menu" id="contextMenu"></div>

    <div class="toolbar" id="toolbar" style="display: none;">
        <button class="btn btn-primary" onclick="newProject()">📁 Novo Projeto</button>
        <button class="btn btn-secondary" onclick="saveProjectToFile()">💾 Salvar</button>
        <button class="btn btn-secondary" onclick="loadProjectFromFile()">📂 Carregar</button>
        <button class="btn btn-primary" onclick="exportPDFWithList()">📄 PDF com Lista</button>
        <button class="btn btn-primary" onclick="exportPDF()">📄 PDF (Apenas Mapa)</button>
        <button class="btn btn-warning" onclick="startRecordingWithSelection()">🎬 Gravar</button>
        <button class="btn btn-warning" onclick="stopRecording()">⏹️ Parar</button>
        <button class="btn btn-warning" onclick="generateBudget()">💰 Orçamento</button>
        <button id="adminUsersBtn" class="btn btn-info" onclick="openUserManagement()" style="display: none;">👥 Usuários</button>
        <button id="adminShapesBtn" class="btn btn-info" onclick="toggleShapesToolbar()" style="display: none;">📐 Formas</button>
        <button id="adminCategoriesBtn" class="btn btn-info" onclick="openAddCategoryModal()" style="display: none;">📁 + Categoria</button>
        <button id="adminDevicesBtn" class="btn btn-info" onclick="openAddDeviceModal()" style="display: none;">🔧 + Equipamento</button>
        <button class="btn btn-info" onclick="toggleGrid()">🔲 Grade</button>
        <button class="btn btn-danger" onclick="logout()">🚪 Sair</button>
        <span style="flex:1"></span>
        <div class="user-info" id="userInfo"></div>
        <span style="color: var(--text-primary);">Zoom: 
            <button class="btn btn-secondary" onclick="zoomIn()">+</button>
            <button class="btn btn-secondary" onclick="zoomOut()">-</button>
            <button class="btn btn-secondary" onclick="resetZoom()">Reset</button>
        </span>
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
        </div>

        <div class="canvas-area">
            <canvas id="canvas" width="3000" height="2500" style="width:3000px;height:2500px"></canvas>
        </div>

        <div class="properties" id="propertiesPanel">
            <h3 style="margin-bottom:15px;color:var(--text-accent);">📋 Propriedades</h3>
            <div id="props-content">
                <p style="color:var(--text-secondary);">Clique em um componente ou forma</p>
            </div>
        </div>
    </div>

    <script>
        // Configuração inicial
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        let components = [];
        let connections = [];
        let shapes = [];
        let selectedComponents = [];
        let selectedShapes = [];
        let dragging = false;
        let dragStart = {x:0, y:0};
        let dragOffset = {x:0, y:0};
        let zoom = 1;
        let isDrawingConnection = false;
        let connectionStart = null;
        let currentAngleHandle = null;
        let currentFovHandle = null;
        let mediaRecorder = null;
        let recordedChunks = [];
        let recordingStream = null;
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
        
        let currentUser = null;
        let userRole = null;
        
        const devImageBase64 = '""" + dev_image_data + """';
        
        const cableColors = {
            'cat5': { color: '#28a745', name: 'CAT5', icon: '🟢', type: 'cable', dashPattern: [] },
            'cat5e': { color: '#17a2b8', name: 'CAT5e', icon: '🔵', type: 'cable', dashPattern: [] },
            'cat6': { color: '#ffc107', name: 'CAT6', icon: '🟡', type: 'cable', dashPattern: [] },
            'fiber': { color: '#20c997', name: 'FIBRA', icon: '🔷', type: 'cable', dashPattern: [] },
            'coaxial': { color: '#e83e8c', name: 'COAXIAL', icon: '🟣', type: 'cable', dashPattern: [] },
            'alarme': { color: '#dc3545', name: 'ALARME', icon: '🔴', type: 'cable', dashPattern: [] },
            'ci': { color: '#6f42c1', name: 'CABO CI', icon: '🟣', type: 'cable', dashPattern: [] },
            'energia': { color: '#fd7e14', name: 'ENERGIA', icon: '🔴', type: 'cable', dashPattern: [] },
            'wifi': { color: '#005f99', name: 'Wi-Fi', icon: '📶', type: 'wireless', dashPattern: [10, 8], animation: 'wifi' },
            'ook': { color: '#fd7e14', name: 'OOK', icon: '📻', type: 'wireless', dashPattern: [8, 6, 2, 6], animation: 'ook' },
            'fsk': { color: '#e83e8c', name: 'FSK', icon: '📡', type: 'wireless', dashPattern: [5, 5, 10, 5], animation: 'fsk' },
            'amt8000': { color: '#20c997', name: 'AMT 8000', icon: '🔊', type: 'wireless', dashPattern: [12, 4, 8, 4], animation: 'amt' }
        };
        
        // ========== GERENCIAMENTO DE PERSISTÊNCIA ==========
        const STORAGE_KEYS = {
            CATEGORIES: 'projetize_categories',
            CUSTOM_DEVICES: 'projetize_custom_devices',
            COMPONENTS: (user) => `projetize_${user}_components`,
            CONNECTIONS: (user) => `projetize_${user}_connections`,
            SHAPES: (user) => `projetize_${user}_shapes`
        };
        
        const DEFAULT_CATEGORIES = {
            'Câmeras': {
                icon: '🎥',
                devices: [
                    { name: 'Câmera Dome', icon: '📹', desc: '360° - 4MP - IVS', type: 'camera', subtype: 'dome', color: '#005f99', iconFile: null },
                    { name: 'Câmera Bullet', icon: '📹', desc: 'Longa distância - 8MP', type: 'camera', subtype: 'bullet', color: '#005f99', iconFile: null },
                    { name: 'PTZ', icon: '📹', desc: 'Motorizada - Auto tracking', type: 'camera', subtype: 'ptz', color: '#005f99', iconFile: null },
                    { name: 'Câmera Térmica', icon: '📹', desc: 'Detecção de calor', type: 'camera', subtype: 'thermal', color: '#005f99', iconFile: null },
                    { name: 'Câmera LPR', icon: '📹', desc: 'Leitura de placas - 1080P', type: 'camera', subtype: 'lpr', color: '#005f99', iconFile: null },
                    { name: 'Câmera PR', icon: '📹', desc: '1080P Full HD', type: 'camera', subtype: 'pr', color: '#005f99', iconFile: null }
                ]
            },
            'Gravadores': {
                icon: '💾',
                devices: [
                    { name: 'NVR', icon: '💾', desc: '32 canais - 4K', type: 'nvr', color: '#17a2b8', iconFile: null },
                    { name: 'DVR', icon: '💾', desc: '16 canais - HD', type: 'dvr', color: '#17a2b8', iconFile: null }
                ]
            },
            'Rede': {
                icon: '🌐',
                devices: [
                    { name: 'Router', icon: '📡', desc: 'Gigabit', type: 'router', color: '#20c997', iconFile: null },
                    { name: 'Switch L2 PoE', icon: '🔌', desc: '24 portas PoE', type: 'switch_l2_poe', color: '#20c997', iconFile: null },
                    { name: 'Switch L2', icon: '🔌', desc: '24 portas', type: 'switch_l2', color: '#20c997', iconFile: null },
                    { name: 'Switch L3 PoE', icon: '🔌', desc: 'Layer 3 com PoE', type: 'switch_l3_poe', color: '#20c997', iconFile: null },
                    { name: 'Switch L3', icon: '🔌', desc: 'Layer 3', type: 'switch_l3', color: '#20c997', iconFile: null },
                    { name: 'OLT GPON', icon: '🔷', desc: 'Fibra óptica', type: 'olt', color: '#20c997', iconFile: null },
                    { name: 'ONU', icon: '🔷', desc: 'Optical Network Unit', type: 'onu', color: '#20c997', iconFile: null },
                    { name: 'ONT', icon: '🔷', desc: 'Optical Terminal', type: 'ont', color: '#20c997', iconFile: null },
                    { name: 'CTO', icon: '📦', desc: 'Caixa Terminal Óptica', type: 'cto', color: '#20c997', iconFile: null },
                    { name: 'Conversor Mídia', icon: '🔄', desc: 'Fibra/RJ45', type: 'converter', color: '#20c997', iconFile: null }
                ]
            },
            'Telefonia': {
                icon: '📞',
                devices: [
                    { name: 'PABX', icon: '📞', desc: 'Central telefônica', type: 'pbx', color: '#6f42c1', iconFile: null },
                    { name: 'Telefone IP', icon: '📞', desc: 'VoIP', type: 'telefone_ip', color: '#6f42c1', iconFile: null },
                    { name: 'Telefone Analógico', icon: '☎️', desc: 'Linha convencional', type: 'telefone_analogico', color: '#6f42c1', iconFile: null },
                    { name: 'ATA', icon: '🔄', desc: 'Adaptador Telefônico', type: 'ata', color: '#6f42c1', iconFile: null }
                ]
            },
            'Sensores': {
                icon: '📡',
                devices: [
                    { name: 'Sensor de Movimento', icon: '🔴', desc: 'Detecção de movimento - Central de Alarme', type: 'sensor', subtype: 'movement', color: '#005f99', iconFile: null },
                    { name: 'Sensor de Porta', icon: '🚪', desc: 'Abertura de porta - Central de Alarme', type: 'sensor', subtype: 'door', color: '#005f99', iconFile: null },
                    { name: 'Sensor de Fumaça', icon: '💨', desc: 'Detecção de fumaça - Central de Incêndio', type: 'sensor', subtype: 'smoke', color: '#005f99', iconFile: null },
                    { name: 'Sensor de Temperatura', icon: '🌡️', desc: 'Controle térmico - Central de Alarme', type: 'sensor', subtype: 'temperature', color: '#005f99', iconFile: null },
                    { name: 'Sensor de Umidade', icon: '💧', desc: 'Controle de umidade - Central de Alarme', type: 'sensor', subtype: 'humidity', color: '#005f99', iconFile: null }
                ]
            },
            'Controle de Acesso': {
                icon: '🔑',
                devices: [
                    { name: 'Cancela', icon: '🚗', desc: 'Controle de acesso', type: 'cancela', color: '#28a745', iconFile: null },
                    { name: 'Controle de Acesso', icon: '🔑', desc: 'Biometria/Cartão', type: 'controle_acesso', color: '#28a745', iconFile: null },
                    { name: 'Catraca', icon: '🚪', desc: 'Controle de fluxo', type: 'catraca', color: '#28a745', iconFile: null },
                    { name: 'Vídeo Porteiro', icon: '📹', desc: 'IP/analógico', type: 'video_porteiro', color: '#28a745', iconFile: null }
                ]
            },
            'Segurança': {
                icon: '🚨',
                devices: [
                    { name: 'Central Alarme', icon: '🚨', desc: 'Sensor perimetral', type: 'alarme', color: '#dc3545', iconFile: null },
                    { name: 'Central Incêndio', icon: '🔥', desc: 'Detecção', type: 'central_incendio', color: '#dc3545', iconFile: null }
                ]
            },
            'Energia': {
                icon: '⚡',
                devices: [
                    { name: 'Nobreak', icon: '🔋', desc: 'Estabilizador', type: 'nobreak', color: '#fd7e14', iconFile: null },
                    { name: 'Fonte Alimentação', icon: '⚡', desc: '12V/24V', type: 'fonte_alimentacao', color: '#fd7e14', iconFile: null },
                    { name: 'Eletrificador', icon: '⚡', desc: 'Cerca elétrica', type: 'eletrificador', color: '#fd7e14', iconFile: null },
                    { name: 'Energia', icon: '🔌', desc: 'Rede elétrica', type: 'energia', color: '#fd7e14', iconFile: null }
                ]
            },
            'Automação': {
                icon: '⚙️',
                devices: [
                    { name: 'Motor', icon: '⚙️', desc: 'Automação', type: 'motor', color: '#6c757d', iconFile: null }
                ]
            }
        };
        
        let categories = JSON.parse(JSON.stringify(DEFAULT_CATEGORIES));
        let customDevices = [];
        
        // Carregar dados salvos
        function loadAllData() {
            const savedCategories = localStorage.getItem(STORAGE_KEYS.CATEGORIES);
            if (savedCategories) {
                try {
                    categories = JSON.parse(savedCategories);
                } catch(e) {}
            }
            
            const savedCustom = localStorage.getItem(STORAGE_KEYS.CUSTOM_DEVICES);
            if (savedCustom) {
                try {
                    customDevices = JSON.parse(savedCustom);
                } catch(e) {}
            }
        }
        
        function saveAllData() {
            localStorage.setItem(STORAGE_KEYS.CATEGORIES, JSON.stringify(categories));
            localStorage.setItem(STORAGE_KEYS.CUSTOM_DEVICES, JSON.stringify(customDevices));
            if (currentUser) {
                localStorage.setItem(STORAGE_KEYS.COMPONENTS(currentUser), JSON.stringify(components));
                localStorage.setItem(STORAGE_KEYS.CONNECTIONS(currentUser), JSON.stringify(connections));
                localStorage.setItem(STORAGE_KEYS.SHAPES(currentUser), JSON.stringify(shapes));
            }
        }
        
        // Upload de imagem para o servidor
        async function uploadIcon(imageData) {
            if (!imageData || !imageData.startsWith('data:image')) return null;
            
            try {
                const response = await fetch('/api/upload_icon', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: imageData })
                });
                const data = await response.json();
                if (data.success) {
                    return data.filename;
                }
            } catch(e) {
                console.error('Erro ao fazer upload:', e);
            }
            return null;
        }
        
        function getIconUrl(filename) {
            if (filename) {
                return `/uploads/icons/${filename}`;
            }
            return null;
        }
        
        function toggleGrid() {
            showGrid = !showGrid;
            showToast(showGrid ? '🔲 Grade visível' : '🔳 Grade oculta');
        }
        
        function openProperties() {
            document.getElementById('propertiesPanel').classList.add('open');
        }
        
        function closeProperties() {
            document.getElementById('propertiesPanel').classList.remove('open');
        }
        
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
            
            let waveClass = '';
            let numWaves = 3;
            
            switch(type) {
                case 'wifi': waveClass = 'connection-wave'; break;
                case 'ook': waveClass = 'ook-wave'; break;
                case 'fsk': waveClass = 'fsk-wave'; numWaves = 2; break;
                case 'amt8000': waveClass = 'amt-wave'; numWaves = 4; break;
                default: waveClass = 'radio-wave';
            }
            
            const color = cableColors[type]?.color || '#005f99';
            
            for(let i = 0; i < numWaves; i++) {
                const wave = document.createElement('div');
                wave.className = waveClass;
                wave.style.position = 'absolute';
                wave.style.width = '20px';
                wave.style.height = '20px';
                wave.style.left = '40px';
                wave.style.top = '40px';
                wave.style.animationDelay = (i * 0.3) + 's';
                wave.style.animationDuration = '1.5s';
                wave.style.borderColor = color;
                wave.style.backgroundColor = 'transparent';
                wave.style.boxShadow = `0 0 10px ${color}`;
                if(type === 'ook') wave.style.borderWidth = '2px';
                if(type === 'fsk') wave.style.border = `2px solid ${color}`;
                animationDiv.appendChild(wave);
            }
            
            container.appendChild(animationDiv);
            setTimeout(() => { animationDiv.remove(); }, 1500);
        }
        
        async function doLogin() {
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;
            
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            if(data.success) {
                currentUser = username;
                userRole = data.role;
                document.getElementById('loginModal').style.display = 'none';
                document.getElementById('toolbar').style.display = 'flex';
                document.getElementById('userInfo').innerHTML = `<span>👤 ${username}</span><span class="user-role">${data.role.toUpperCase()}</span>`;
                
                if(data.role === 'admin' || data.role === 'master') {
                    document.getElementById('adminUsersBtn').style.display = 'inline-block';
                    document.getElementById('adminShapesBtn').style.display = 'inline-block';
                    document.getElementById('adminCategoriesBtn').style.display = 'inline-block';
                    document.getElementById('adminDevicesBtn').style.display = 'inline-block';
                }
                
                loadUserData();
                showToast(`Bem-vindo, ${username}!`);
            } else {
                document.getElementById('loginError').style.display = 'block';
            }
        }
        
        function logout() {
            fetch('/api/logout', { method: 'POST' })
                .then(() => { location.reload(); });
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
                    <div style="margin-top: 15px;">
                        <input type="text" id="newUsername" placeholder="Novo usuário">
                        <input type="password" id="newPassword" placeholder="Senha">
                        <select id="newRole">
                            <option value="viewer">Visualizador</option>
                            <option value="admin">Administrador</option>
                        </select>
                        <button class="btn btn-primary" style="margin-top: 10px;" onclick="addUser()">➕ Adicionar</button>
                    </div>
                    <div class="modal-buttons" style="margin-top: 15px;">
                        <button class="btn btn-danger" onclick="closeModal()">Fechar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
            renderUserList(users);
        }
        
        function renderUserList(users) {
            const container = document.getElementById('userList');
            if(!container) return;
            container.innerHTML = '';
            for(const [username, userData] of Object.entries(users)) {
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
            
            if(!username || !password) {
                showToast('Preencha todos os campos');
                return;
            }
            
            const response = await fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, role })
            });
            
            const data = await response.json();
            if(data.success) {
                showToast('✅ Usuário adicionado!');
                closeModal();
                openUserManagement();
            } else {
                showToast(data.error);
            }
        }
        
        async function deleteUser(username) {
            if(confirm(`Deseja excluir o usuário "${username}"?`)) {
                const response = await fetch(`/api/users/${username}`, { method: 'DELETE' });
                const data = await response.json();
                if(data.success) {
                    showToast('✅ Usuário excluído!');
                    closeModal();
                    openUserManagement();
                } else {
                    showToast(data.error);
                }
            }
        }
        
        function setShapeMode(mode) {
            shapeMode = mode;
            document.querySelectorAll('.shape-btn').forEach(btn => btn.classList.remove('active'));
            if(event.target) event.target.classList.add('active');
            showToast(`Modo: Desenhar ${getShapeName(mode)} - Clique e arraste no canvas`);
        }
        
        function getShapeName(mode) {
            const names = { line: 'Linha', door: 'Porta', window: 'Janela', text: 'Texto' };
            return names[mode] || mode;
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
        
        function drawGrid() {
            if(!showGrid) return;
            const step = 50;
            ctx.save();
            ctx.scale(zoom, zoom);
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
            ctx.scale(zoom, zoom);
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
            ctx.font = `bold ${10/zoom}px Arial`;
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
                ctx.scale(zoom, zoom);
                ctx.beginPath();
                ctx.arc(x, y, radius, 0, 2 * Math.PI);
                ctx.strokeStyle = `rgba(0, 95, 153, ${opacity})`;
                ctx.lineWidth = 2;
                ctx.stroke();
                ctx.restore();
            }
        }
        
        let trafficAnimation = 0;
        let wirelessAnimationOffset = 0;
        
        function drawConnections() {
            connections.forEach((conn, idx) => {
                const fromComp = components.find(c => c.id === conn.from);
                const toComp = components.find(c => c.id === conn.to);
                if(!fromComp || !toComp) return;
                
                const cableInfo = cableColors[conn.type] || cableColors['cat6'];
                const isWireless = cableInfo.type === 'wireless';
                
                ctx.save();
                ctx.scale(zoom, zoom);
                
                if(isWireless) {
                    ctx.setLineDash(cableInfo.dashPattern || [10, 8]);
                    ctx.strokeStyle = cableInfo.color;
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(fromComp.x, fromComp.y);
                    ctx.lineTo(toComp.x, toComp.y);
                    ctx.stroke();
                    
                    wirelessAnimationOffset = (wirelessAnimationOffset + 0.05) % (Math.PI * 2);
                    const numParticles = cableInfo.animation === 'amt8000' ? 4 : 3;
                    
                    for(let i = 1; i <= numParticles; i++) {
                        const t = (trafficAnimation + i * 0.2) % 1;
                        const x = fromComp.x + (toComp.x - fromComp.x) * t;
                        const y = fromComp.y + (toComp.y - fromComp.y) * t;
                        
                        ctx.setLineDash([]);
                        
                        switch(conn.type) {
                            case 'wifi':
                                ctx.beginPath();
                                ctx.arc(x, y, 6 + Math.sin(wirelessAnimationOffset + i) * 2, 0, 2 * Math.PI);
                                ctx.fillStyle = cableInfo.color;
                                ctx.fill();
                                ctx.fillStyle = '#fff';
                                ctx.font = `${10/zoom}px Arial`;
                                ctx.fillText('📶', x-5, y+3);
                                break;
                            case 'ook':
                                ctx.beginPath();
                                ctx.rect(x-5, y-5, 10, 10);
                                ctx.fillStyle = cableInfo.color;
                                ctx.fill();
                                ctx.fillStyle = '#fff';
                                ctx.font = `${8/zoom}px Arial`;
                                ctx.fillText('◻', x-3, y+3);
                                break;
                            case 'fsk':
                                ctx.beginPath();
                                ctx.ellipse(x, y, 6, 4, wirelessAnimationOffset + i, 0, 2 * Math.PI);
                                ctx.fillStyle = cableInfo.color;
                                ctx.fill();
                                ctx.fillStyle = '#fff';
                                ctx.font = `${9/zoom}px Arial`;
                                ctx.fillText('↻', x-3, y+3);
                                break;
                            case 'amt8000':
                                const angle = wirelessAnimationOffset + i * Math.PI * 2 / 3;
                                const radius = 8;
                                const px = x + Math.cos(angle) * radius;
                                const py = y + Math.sin(angle) * radius;
                                ctx.beginPath();
                                ctx.arc(px, py, 3, 0, 2 * Math.PI);
                                ctx.fillStyle = cableInfo.color;
                                ctx.fill();
                                break;
                            default:
                                ctx.beginPath();
                                ctx.arc(x, y, 4, 0, 2 * Math.PI);
                                ctx.fillStyle = cableInfo.color;
                                ctx.fill();
                        }
                    }
                } else {
                    ctx.setLineDash([]);
                    ctx.beginPath();
                    ctx.moveTo(fromComp.x, fromComp.y);
                    ctx.lineTo(toComp.x, toComp.y);
                    ctx.strokeStyle = cableInfo.color;
                    ctx.lineWidth = 2;
                    ctx.stroke();
                    
                    trafficAnimation = (trafficAnimation + 0.02) % 1;
                    const t = trafficAnimation;
                    const x = fromComp.x + (toComp.x - fromComp.x) * t;
                    const y = fromComp.y + (toComp.y - fromComp.y) * t;
                    ctx.beginPath();
                    ctx.arc(x, y, 4, 0, 2*Math.PI);
                    ctx.fillStyle = cableInfo.color;
                    ctx.fill();
                }
                
                ctx.fillStyle = '#6c757d';
                ctx.font = `${9/zoom}px Arial`;
                ctx.fillText(`${cableInfo.icon} ${cableInfo.name}`, (fromComp.x+toComp.x)/2, (fromComp.y+toComp.y)/2-5);
                ctx.restore();
            });
        }
        
        function drawShapes() {
            shapes.forEach(shape => {
                const isSelected = selectedShapes.includes(shape);
                
                ctx.save();
                ctx.scale(zoom, zoom);
                
                ctx.fillStyle = shape.fillColor || 'rgba(0, 0, 0, 0.05)';
                ctx.strokeStyle = shape.strokeColor || '#005f99';
                ctx.lineWidth = (shape.lineWidth || 2) / zoom;
                
                if(shape.rotation) {
                    ctx.translate(shape.x + (shape.type === 'door' ? 15 : 30), shape.y + (shape.type === 'door' ? 25 : 20));
                    ctx.rotate(shape.rotation * Math.PI / 180);
                    ctx.translate(-(shape.x + (shape.type === 'door' ? 15 : 30)), -(shape.y + (shape.type === 'door' ? 25 : 20)));
                }
                
                switch(shape.type) {
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
                        ctx.font = `${(shape.fontSize || 14) / zoom}px Arial`;
                        ctx.fillStyle = shape.textColor || '#212529';
                        ctx.fillText(shape.text || 'Texto', shape.x, shape.y);
                        break;
                }
                
                if(shape.rotation) {
                    ctx.setTransform(1, 0, 0, 1, 0, 0);
                }
                
                if(isSelected) {
                    ctx.strokeStyle = '#005f99';
                    ctx.lineWidth = 2 / zoom;
                    if(shape.type === 'line') {
                        ctx.beginPath();
                        ctx.moveTo(shape.x1 - 3, shape.y1 - 3);
                        ctx.lineTo(shape.x2 + 3, shape.y2 + 3);
                        ctx.moveTo(shape.x1 + 3, shape.y1 - 3);
                        ctx.lineTo(shape.x2 - 3, shape.y2 + 3);
                        ctx.stroke();
                    } else if(shape.type === 'text') {
                        ctx.strokeRect(shape.x - 5, shape.y - 12, ctx.measureText(shape.text || 'Texto').width + 10, 18);
                    } else {
                        const w = 30;
                        const h = shape.type === 'door' ? 50 : 40;
                        ctx.strokeRect(shape.x - 3, shape.y - 3, w + 6, h + 6);
                    }
                }
                
                ctx.restore();
            });
        }
        
        function drawComponents() {
            components.forEach(comp => {
                const isSelected = selectedComponents.includes(comp);
                
                if(comp.type === 'sensor') {
                    drawSensorAnimation(comp.x, comp.y, sensorAnimationTime);
                }
                
                ctx.save();
                ctx.scale(zoom, zoom);
                ctx.translate(comp.x, comp.y);
                ctx.rotate((comp.rotation || 0) * Math.PI / 180);
                ctx.translate(-comp.x, -comp.y);
                
                if(comp.customImage && comp.customImage.startsWith('data:image')) {
                    const img = new Image();
                    img.src = comp.customImage;
                    ctx.drawImage(img, comp.x-18, comp.y-18, 36, 36);
                } else if(comp.iconUrl) {
                    const img = new Image();
                    img.src = comp.iconUrl;
                    ctx.drawImage(img, comp.x-18, comp.y-18, 36, 36);
                } else if(comp.iconFile) {
                    const img = new Image();
                    img.src = `/uploads/icons/${comp.iconFile}`;
                    ctx.drawImage(img, comp.x-18, comp.y-18, 36, 36);
                } else {
                    ctx.fillStyle = comp.color || '#005f99';
                    ctx.beginPath();
                    ctx.arc(comp.x, comp.y, 18, 0, 2*Math.PI);
                    ctx.fill();
                    ctx.fillStyle = '#fff';
                    ctx.font = `${18/zoom}px Arial`;
                    ctx.fillText(comp.icon || '📦', comp.x-10, comp.y+7);
                }
                
                ctx.setTransform(1, 0, 0, 1, 0, 0);
                
                ctx.fillStyle = '#005f99';
                ctx.font = `${10/zoom}px Arial`;
                ctx.fillText(comp.name, comp.x-25, comp.y-22);
                
                if(comp.ip) {
                    ctx.fillStyle = '#6c757d';
                    ctx.font = `${8/zoom}px Arial`;
                    ctx.fillText(comp.ip, comp.x-20, comp.y-12);
                }
                
                if(isSelected) {
                    ctx.strokeStyle = '#005f99';
                    ctx.lineWidth = 2 / zoom;
                    ctx.strokeRect(comp.x-22, comp.y-22, 44, 44);
                    
                    ctx.beginPath();
                    ctx.arc(comp.x + 25, comp.y - 25, 6, 0, 2*Math.PI);
                    ctx.fillStyle = '#005f99';
                    ctx.fill();
                    ctx.fillStyle = '#fff';
                    ctx.font = `${10/zoom}px Arial`;
                    ctx.fillText('↻', comp.x + 22, comp.y - 22);
                }
                
                if(comp.type === 'camera') {
                    drawFieldOfView(comp);
                }
                
                ctx.restore();
            });
        }
        
        function drawWithBackground(whiteBg = false, hideGrid = false) {
            if(whiteBg) {
                ctx.fillStyle = '#FFFFFF';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
            } else {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
            }
            if(!hideGrid && showGrid) drawGrid();
            drawShapes();
            drawConnections();
            drawComponents();
        }
        
        function drawShapePreview(start, end, type) {
            if(!start || !end) return;
            
            ctx.save();
            ctx.scale(zoom, zoom);
            ctx.setLineDash([5, 5]);
            ctx.strokeStyle = '#005f99';
            ctx.fillStyle = 'rgba(0, 95, 153, 0.2)';
            ctx.lineWidth = 2;
            
            const x = Math.min(start.x, end.x);
            const y = Math.min(start.y, end.y);
            const width = Math.abs(end.x - start.x);
            
            switch(type) {
                case 'line':
                    ctx.beginPath();
                    ctx.moveTo(start.x, start.y);
                    ctx.lineTo(end.x, end.y);
                    ctx.stroke();
                    break;
                case 'door':
                    ctx.fillRect(end.x, end.y, 30, 50);
                    ctx.strokeRect(end.x, end.y, 30, 50);
                    break;
                case 'window':
                    ctx.fillRect(x, y, width, 40);
                    ctx.strokeRect(x, y, width, 40);
                    break;
            }
            
            ctx.setLineDash([]);
            ctx.restore();
        }
        
        function draw() {
            sensorAnimationTime = (sensorAnimationTime + 0.01) % 1;
            drawWithBackground(false, false);
            if(drawingPreview && shapeStart) {
                const {x, y} = lastMousePos || {x: shapeStart.x, y: shapeStart.y};
                drawShapePreview(shapeStart, {x, y}, shapeMode);
            }
            requestAnimationFrame(draw);
        }
        
        let lastMousePos = null;
        draw();
        
        function getMousePos(e) {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const mouseX = (e.clientX - rect.left) * scaleX / zoom;
            const mouseY = (e.clientY - rect.top) * scaleY / zoom;
            return {x: mouseX, y: mouseY};
        }
        
        function rotateComponent(comp, angle) {
            comp.rotation = (comp.rotation || 0) + angle;
        }
        
        function rotateShape(shape, angle) {
            if(shape.type === 'door' || shape.type === 'window') {
                shape.rotation = (shape.rotation || 0) + angle;
            }
        }
        
        function accessDevice(comp) {
            if(comp && comp.ip && comp.ip.trim()) {
                let url = comp.ip;
                if(!url.startsWith('http://') && !url.startsWith('https://')) {
                    url = 'http://' + url;
                }
                if(comp.port && comp.port !== 80) {
                    url += ':' + comp.port;
                }
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
                    } else {
                        return;
                    }
                    break;
            }
            
            shapes.push(newShape);
            showToast(`✅ ${getShapeName(type)} adicionado!`);
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
                `}
                <div class="modal-buttons" style="margin-top:10px;">
                    <button class="btn btn-danger" onclick="deleteShape(${shape.id})">🗑 Excluir Forma</button>
                </div>
            `;
            
            document.getElementById('shape-stroke')?.addEventListener('change', (e) => { shape.strokeColor = e.target.value; });
            document.getElementById('shape-linewidth')?.addEventListener('change', (e) => { shape.lineWidth = parseInt(e.target.value); });
            
            const rotationSlider = document.getElementById('shape-rotation');
            if(rotationSlider) {
                rotationSlider.oninput = (e) => { 
                    shape.rotation = parseInt(e.target.value); 
                    document.getElementById('rotation-val').innerText = shape.rotation + '°';
                };
            }
            
            if(shape.type === 'text') {
                document.getElementById('shape-text')?.addEventListener('change', (e) => { shape.text = e.target.value; });
                document.getElementById('shape-fontsize')?.addEventListener('change', (e) => { shape.fontSize = parseInt(e.target.value); });
                document.getElementById('shape-textcolor')?.addEventListener('change', (e) => { shape.textColor = e.target.value; });
            }
        }
        
        window.deleteShape = (id) => {
            shapes = shapes.filter(s => s.id !== id);
            selectedShapes = selectedShapes.filter(s => s.id !== id);
            showProperties(null);
            showToast('🗑 Forma removida!');
        };
        
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
        
        canvas.addEventListener('mousedown', (e) => {
            const {x, y} = getMousePos(e);
            lastMousePos = {x, y};
            
            if(shapeMode) {
                shapeStart = {x, y};
                drawingPreview = true;
                e.preventDefault();
                return;
            }
            
            for(let comp of components) {
                if(selectedComponents.includes(comp)) {
                    const handleX = comp.x + 25;
                    const handleY = comp.y - 25;
                    if(Math.hypot(x - handleX, y - handleY) < 10) {
                        rotateComponent(comp, 15);
                        return;
                    }
                }
            }
            
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
            
            let clickedShape = null;
            for(let i=shapes.length-1; i>=0; i--) {
                const shape = shapes[i];
                let hit = false;
                if(shape.type === 'line') {
                    const dist = pointToLineDistance(x, y, shape.x1, shape.y1, shape.x2, shape.y2);
                    hit = dist < 5;
                } else if(shape.type === 'text') {
                    hit = x >= shape.x - 5 && x <= shape.x + (shape.text?.length * 7 || 50) && y >= shape.y - 12 && y <= shape.y + 6;
                } else {
                    const w = 30;
                    const h = shape.type === 'door' ? 50 : 40;
                    hit = x >= shape.x && x <= shape.x + w && y >= shape.y && y <= shape.y + h;
                }
                if(hit) {
                    clickedShape = shape;
                    break;
                }
            }
            
            let clickedComp = null;
            for(let i=components.length-1; i>=0; i--) {
                const comp = components[i];
                if(Math.hypot(x - comp.x, y - comp.y) < 20) {
                    clickedComp = comp;
                    break;
                }
            }
            
            if(clickedComp) {
                if(e.ctrlKey || e.metaKey) {
                    if(selectedComponents.includes(clickedComp)) {
                        selectedComponents = selectedComponents.filter(c => c !== clickedComp);
                    } else {
                        selectedComponents.push(clickedComp);
                    }
                } else {
                    selectedComponents = [clickedComp];
                    dragging = true;
                    dragOffset = {x: clickedComp.x - x, y: clickedComp.y - y};
                }
                showProperties(clickedComp);
                openProperties();
                return;
            } else if(clickedShape) {
                if(e.ctrlKey || e.metaKey) {
                    if(selectedShapes.includes(clickedShape)) {
                        selectedShapes = selectedShapes.filter(s => s !== clickedShape);
                    } else {
                        selectedShapes.push(clickedShape);
                    }
                } else {
                    selectedShapes = [clickedShape];
                    dragging = true;
                    if(clickedShape.type === 'line') {
                        dragOffset = {x: clickedShape.x1 - x, y: clickedShape.y1 - y};
                    } else {
                        dragOffset = {x: clickedShape.x - x, y: clickedShape.y - y};
                    }
                }
                showShapeProperties(clickedShape);
                openProperties();
                return;
            } else if(e.ctrlKey || e.metaKey) {
                startSelection(e);
                selectedComponents = [];
                selectedShapes = [];
                showProperties(null);
            } else {
                selectedComponents = [];
                selectedShapes = [];
                dragging = false;
                showProperties(null);
            }
            
            if(e.shiftKey) {
                for(let comp of components) {
                    if(Math.hypot(x - comp.x, y - comp.y) < 20) {
                        isDrawingConnection = true;
                        connectionStart = comp;
                        return;
                    }
                }
            }
        });
        
        canvas.addEventListener('mousemove', (e) => {
            const {x, y} = getMousePos(e);
            lastMousePos = {x, y};
            
            if(currentAngleHandle) {
                const angle = Math.atan2(y - currentAngleHandle.y, x - currentAngleHandle.x) * 180 / Math.PI;
                currentAngleHandle.angle = angle;
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
            }
            
            if(dragging && selectedShapes.length > 0) {
                const dx = (x + dragOffset.x) - (selectedShapes[0].type === 'line' ? selectedShapes[0].x1 : selectedShapes[0].x);
                const dy = (y + dragOffset.y) - (selectedShapes[0].type === 'line' ? selectedShapes[0].y1 : selectedShapes[0].y);
                selectedShapes.forEach(shape => {
                    if(shape.type === 'line') {
                        shape.x1 += dx;
                        shape.y1 += dy;
                        shape.x2 += dx;
                        shape.y2 += dy;
                    } else {
                        shape.x += dx;
                        shape.y += dy;
                    }
                });
                dragOffset = {x: (selectedShapes[0].type === 'line' ? selectedShapes[0].x1 : selectedShapes[0].x) - x, 
                              y: (selectedShapes[0].type === 'line' ? selectedShapes[0].y1 : selectedShapes[0].y) - y};
            }
            
            if(isSelecting) {
                updateSelection(e);
            }
        });
        
        canvas.addEventListener('mouseup', (e) => {
            if(shapeMode && shapeStart) {
                const {x, y} = getMousePos(e);
                endShape(shapeStart, {x, y}, shapeMode);
                shapeStart = null;
                drawingPreview = false;
                return;
            }
            
            currentAngleHandle = null;
            dragging = false;
            if(isSelecting) {
                endSelection();
            }
            if(isDrawingConnection && connectionStart) {
                showToast('Clique em um equipamento para conectar');
            }
            isDrawingConnection = false;
            connectionStart = null;
        });
        
        canvas.addEventListener('click', (e) => {
            const {x, y} = getMousePos(e);
            if(isDrawingConnection && connectionStart) {
                for(let comp of components) {
                    if(Math.hypot(x - comp.x, y - comp.y) < 20 && comp.id !== connectionStart.id) {
                        showCableModal(connectionStart, comp);
                        isDrawingConnection = false;
                        connectionStart = null;
                        return;
                    }
                }
            }
        });
        
        canvas.addEventListener('contextmenu', (e) => {
            const {x, y} = getMousePos(e);
            for(let comp of components) {
                if(Math.hypot(x - comp.x, y - comp.y) < 20) {
                    showContextMenu(e, comp);
                    return;
                }
            }
            for(let shape of shapes) {
                let hit = false;
                if(shape.type === 'line') {
                    hit = pointToLineDistance(x, y, shape.x1, shape.y1, shape.x2, shape.y2) < 5;
                } else if(shape.type === 'text') {
                    hit = x >= shape.x - 5 && x <= shape.x + (shape.text?.length * 7 || 50) && y >= shape.y - 12 && y <= shape.y + 6;
                } else {
                    const w = 30;
                    const h = shape.type === 'door' ? 50 : 40;
                    hit = x >= shape.x && x <= shape.x + w && y >= shape.y && y <= shape.y + h;
                }
                if(hit) {
                    showShapeContextMenu(e, shape);
                    return;
                }
            }
            for(let i = 0; i < connections.length; i++) {
                const conn = connections[i];
                const fromComp = components.find(c => c.id === conn.from);
                const toComp = components.find(c => c.id === conn.to);
                if(fromComp && toComp) {
                    const dist = pointToLineDistance(x, y, fromComp.x, fromComp.y, toComp.x, toComp.y);
                    if(dist < 8) {
                        showConnectionContextMenu(e, conn, i);
                        return;
                    }
                }
            }
        });
        
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
            
            setTimeout(() => {
                document.addEventListener('click', () => { menu.style.display = 'none'; }, {once: true});
            }, 100);
        }
        
        window.editConnectionFromMenu = () => {
            if(contextMenuConnection) {
                const conn = contextMenuConnection.conn;
                const fromComp = components.find(c => c.id === conn.from);
                const toComp = components.find(c => c.id === conn.to);
                if(fromComp && toComp) {
                    showEditCableModal(fromComp, toComp, contextMenuConnection.idx);
                }
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.deleteConnectionFromMenu = () => {
            if(contextMenuConnection) {
                connections.splice(contextMenuConnection.idx, 1);
                showToast('✅ Conexão removida!');
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        function showEditCableModal(fromComp, toComp, connIdx) {
            const currentConn = connections[connIdx];
            const currentType = currentConn.type;
            
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">✏️ Editar Conexão</h3>
                    <p>De: ${fromComp.name}</p>
                    <p>Para: ${toComp.name}</p>
                    <select id="cableSelect" style="width:100%; padding:8px; margin:10px 0; background:var(--bg-tertiary); color:var(--text-primary); border:none; border-radius:5px;">
                        <optgroup label="📡 Conexões com Fio">
                            <option value="cat5" ${currentType === 'cat5' ? 'selected' : ''}>🟢 CAT5 - 100Mbps</option>
                            <option value="cat5e" ${currentType === 'cat5e' ? 'selected' : ''}>🔵 CAT5e - 1Gbps</option>
                            <option value="cat6" ${currentType === 'cat6' ? 'selected' : ''}>🟡 CAT6 - 10Gbps</option>
                            <option value="fiber" ${currentType === 'fiber' ? 'selected' : ''}>🔷 Fibra Óptica - 10Gbps</option>
                            <option value="coaxial" ${currentType === 'coaxial' ? 'selected' : ''}>🟣 Cabo Coaxial</option>
                            <option value="alarme" ${currentType === 'alarme' ? 'selected' : ''}>🔴 Cabo Alarme</option>
                            <option value="ci" ${currentType === 'ci' ? 'selected' : ''}>🟣 Cabo CI</option>
                            <option value="energia" ${currentType === 'energia' ? 'selected' : ''}>🔴 ENERGIA (Rede Elétrica)</option>
                        </optgroup>
                        <optgroup label="📶 Conexões Sem Fio">
                            <option value="wifi" ${currentType === 'wifi' ? 'selected' : ''}>📶 Wi-Fi - 2.4/5GHz</option>
                            <option value="ook" ${currentType === 'ook' ? 'selected' : ''}>📻 OOK - Rádio Frequência</option>
                            <option value="fsk" ${currentType === 'fsk' ? 'selected' : ''}>📡 FSK - Modulação por Frequência</option>
                            <option value="amt8000" ${currentType === 'amt8000' ? 'selected' : ''}>🔊 AMT 8000 - Rádio Digital</option>
                        </optgroup>
                    </select>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" onclick="updateConnection(${connIdx})">✅ Atualizar</button>
                        <button class="btn btn-danger" onclick="closeModal()">❌ Cancelar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            window.currentModal = modal;
        }
        
        window.updateConnection = (connIdx) => {
            const cableType = document.getElementById('cableSelect').value;
            connections[connIdx].type = cableType;
            if(window.currentModal) {
                document.body.removeChild(window.currentModal);
                window.currentModal = null;
            }
            showToast(`✅ Conexão atualizada para ${cableType.toUpperCase()}!`);
        };
        
        function showShapeContextMenu(e, shape) {
            e.preventDefault();
            contextMenuShape = shape;
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `
                <div class="context-menu-item" onclick="editShapeFromMenu()">✏️ Editar</div>
                <div class="context-menu-item" onclick="rotateShapeLeftFromMenu()">🔄 Girar Esquerda</div>
                <div class="context-menu-item" onclick="rotateShapeRightFromMenu()">🔄 Girar Direita</div>
                <div class="context-menu-item" onclick="deleteShapeFromMenu()">🗑 Excluir</div>
                <div class="context-menu-item" onclick="duplicateShapeFromMenu()">📋 Duplicar</div>
            `;
            menu.style.display = 'block';
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';
            
            setTimeout(() => {
                document.addEventListener('click', () => { menu.style.display = 'none'; }, {once: true});
            }, 100);
        }
        
        window.rotateShapeLeftFromMenu = () => {
            if(contextMenuShape && (contextMenuShape.type === 'door' || contextMenuShape.type === 'window')) {
                contextMenuShape.rotation = (contextMenuShape.rotation || 0) - 15;
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.rotateShapeRightFromMenu = () => {
            if(contextMenuShape && (contextMenuShape.type === 'door' || contextMenuShape.type === 'window')) {
                contextMenuShape.rotation = (contextMenuShape.rotation || 0) + 15;
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.editShapeFromMenu = () => {
            if(contextMenuShape) {
                showShapeProperties(contextMenuShape);
                openProperties();
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.deleteShapeFromMenu = () => {
            if(contextMenuShape) {
                shapes = shapes.filter(s => s.id !== contextMenuShape.id);
                selectedShapes = selectedShapes.filter(s => s.id !== contextMenuShape.id);
                showProperties(null);
                if(selectedShapes.length === 0 && selectedComponents.length === 0) closeProperties();
                showToast('🗑 Forma removida!');
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.duplicateShapeFromMenu = () => {
            if(contextMenuShape) {
                const newShape = JSON.parse(JSON.stringify(contextMenuShape));
                newShape.id = Date.now();
                if(newShape.type === 'line') {
                    newShape.x1 += 20;
                    newShape.y1 += 20;
                    newShape.x2 += 20;
                    newShape.y2 += 20;
                } else {
                    newShape.x += 20;
                    newShape.y += 20;
                }
                shapes.push(newShape);
                showToast(`📋 Forma duplicada!`);
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        function startSelection(e) {
            isSelecting = true;
            const {x, y} = getMousePos(e);
            selectionStart = {x, y};
            selectionEnd = {x, y};
            const rect = document.getElementById('selectionRect');
            rect.style.display = 'block';
        }
        
        function updateSelection(e) {
            if(!isSelecting) return;
            const {x, y} = getMousePos(e);
            selectionEnd = {x, y};
            
            const left = Math.min(selectionStart.x, selectionEnd.x) * zoom;
            const top = Math.min(selectionStart.y, selectionEnd.y) * zoom;
            const width = Math.abs(selectionEnd.x - selectionStart.x) * zoom;
            const height = Math.abs(selectionEnd.y - selectionStart.y) * zoom;
            
            const rect = document.getElementById('selectionRect');
            const canvasRect = canvas.getBoundingClientRect();
            rect.style.left = canvasRect.left + left + 'px';
            rect.style.top = canvasRect.top + top + 'px';
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
            
            selectedComponents = components.filter(comp => {
                return comp.x >= minX && comp.x <= maxX && comp.y >= minY && comp.y <= maxY;
            });
            
            selectedShapes = shapes.filter(shape => {
                if(shape.type === 'line') {
                    return (shape.x1 >= minX && shape.x1 <= maxX && shape.y1 >= minY && shape.y1 <= maxY) ||
                           (shape.x2 >= minX && shape.x2 <= maxX && shape.y2 >= minY && shape.y2 <= maxY);
                } else if(shape.type === 'text') {
                    return shape.x >= minX && shape.x <= maxX && shape.y >= minY && shape.y <= maxY;
                } else {
                    const w = 30;
                    const h = shape.type === 'door' ? 50 : 40;
                    return shape.x + w >= minX && shape.x <= maxX && shape.y + h >= minY && shape.y <= maxY;
                }
            });
            
            const info = document.getElementById('selectionInfo');
            const total = selectedComponents.length + selectedShapes.length;
            if(total > 0) {
                info.textContent = `${total} item(s) selecionado(s)`;
                info.style.display = 'block';
                setTimeout(() => { info.style.display = 'none'; }, 2000);
            }
            
            if(selectedComponents.length === 1 && selectedShapes.length === 0) {
                showProperties(selectedComponents[0]);
                openProperties();
            } else if(selectedShapes.length === 1 && selectedComponents.length === 0) {
                showShapeProperties(selectedShapes[0]);
                openProperties();
            } else {
                showProperties(null);
                closeProperties();
            }
        }
        
        function showContextMenu(e, comp) {
            e.preventDefault();
            contextMenuComponent = comp;
            const menu = document.getElementById('contextMenu');
            menu.innerHTML = `
                <div class="context-menu-item" onclick="accessDeviceFromMenu()">🌐 Acessar Dispositivo</div>
                <div class="context-menu-item" onclick="copyIpFromMenu()">📋 Copiar IP</div>
                <div class="context-menu-item" onclick="rotateLeftFromMenu()">🔄 Rotacionar Esquerda</div>
                <div class="context-menu-item" onclick="rotateRightFromMenu()">🔄 Rotacionar Direita</div>
                <div class="context-menu-item" onclick="deleteComponentFromMenu()">🗑 Remover</div>
                <div class="context-menu-item" onclick="duplicateComponentFromMenu()">📋 Duplicar</div>
            `;
            menu.style.display = 'block';
            menu.style.left = e.pageX + 'px';
            menu.style.top = e.pageY + 'px';
            
            setTimeout(() => {
                document.addEventListener('click', () => { menu.style.display = 'none'; }, {once: true});
            }, 100);
        }
        
        window.rotateLeftFromMenu = () => {
            if(contextMenuComponent) rotateComponent(contextMenuComponent, -15);
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        window.rotateRightFromMenu = () => {
            if(contextMenuComponent) rotateComponent(contextMenuComponent, 15);
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
        
        window.deleteComponentFromMenu = () => {
            if(contextMenuComponent) {
                connections = connections.filter(c => c.from !== contextMenuComponent.id && c.to !== contextMenuComponent.id);
                components = components.filter(c => c.id !== contextMenuComponent.id);
                selectedComponents = selectedComponents.filter(c => c.id !== contextMenuComponent.id);
                showProperties(null);
                if(selectedComponents.length === 0 && selectedShapes.length === 0) closeProperties();
                showToast(`🗑 ${contextMenuComponent.name} removido!`);
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
            }
            document.getElementById('contextMenu').style.display = 'none';
        };
        
        function showCableModal(fromComp, toComp) {
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <h3 style="color:var(--text-accent);">🔌 Tipo de Conexão</h3>
                    <p>De: ${fromComp.name}</p>
                    <p>Para: ${toComp.name}</p>
                    <select id="cableSelect" style="width:100%; padding:8px; margin:10px 0; background:var(--bg-tertiary); color:var(--text-primary); border:none; border-radius:5px;">
                        <optgroup label="📡 Conexões com Fio">
                            <option value="cat5">🟢 CAT5 - 100Mbps</option>
                            <option value="cat5e">🔵 CAT5e - 1Gbps</option>
                            <option value="cat6">🟡 CAT6 - 10Gbps</option>
                            <option value="fiber">🔷 Fibra Óptica - 10Gbps</option>
                            <option value="coaxial">🟣 Cabo Coaxial</option>
                            <option value="alarme">🔴 Cabo Alarme</option>
                            <option value="ci">🟣 Cabo CI</option>
                            <option value="energia">🔴 ENERGIA (Rede Elétrica)</option>
                        </optgroup>
                        <optgroup label="📶 Conexões Sem Fio">
                            <option value="wifi">📶 Wi-Fi - 2.4/5GHz</option>
                            <option value="ook">📻 OOK - Rádio Frequência</option>
                            <option value="fsk">📡 FSK - Modulação por Frequência</option>
                            <option value="amt8000">🔊 AMT 8000 - Rádio Digital</option>
                        </optgroup>
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
                    setTimeout(() => {
                        showWirelessAnimation(toComp.x, toComp.y, cableType);
                    }, 500);
                }
            }
            
            showToast(`✅ Conexão ${cableInfo ? cableInfo.name : cableType.toUpperCase()} adicionada!`);
        };
        
        canvas.addEventListener('dragover', (e) => e.preventDefault());
        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            const {x, y} = getMousePos(e);
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            
            let compType = data.type || 'custom';
            let isCamera = compType === 'camera' || data.name?.toLowerCase().includes('câmera') || data.name?.toLowerCase().includes('camera');
            let isSensor = compType === 'sensor' || data.name?.toLowerCase().includes('sensor');
            
            const component = {
                id: Date.now(),
                type: compType,
                subtype: data.subtype || '',
                name: data.name,
                x: x, y: y,
                icon: data.icon || '📦',
                iconFile: data.iconFile || null,
                color: data.color || '#005f99',
                imageData: data.imageData || null,
                angle: 0,
                fov: 80,
                rotation: 0,
                customImage: null,
                ip: '',
                port: 80,
                username: '',
                password: ''
            };
            components.push(component);
            showToast(`✅ ${component.name} adicionado ao projeto!`);
        });
        
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
                <div class="property-group"><label>🌐 Endereço IP</label><input type="text" id="prop-ip" value="${comp.ip || ''}" placeholder="192.168.1.100"></div>
                <div class="property-group"><label>🔌 Porta</label><input type="number" id="prop-port" value="${comp.port || 80}" placeholder="80"></div>
                <div class="property-group"><label>👤 Usuário</label><input type="text" id="prop-user" value="${comp.username || ''}" placeholder="admin"></div>
                <div class="property-group"><label>🔑 Senha</label><input type="password" id="prop-pass" value="${comp.password || ''}"></div>
                ${comp.type === 'camera' ? `
                <div class="property-group"><label>Ângulo (graus)</label><input type="range" id="prop-angle" min="0" max="360" value="${comp.angle || 0}"><span id="angle-val">${Math.round(comp.angle || 0)}°</span></div>
                <div class="property-group"><label>Campo Visão (graus)</label><input type="range" id="prop-fov" min="20" max="120" value="${comp.fov || 80}"><span id="fov-val">${Math.round(comp.fov || 80)}°</span></div>
                ` : ''}
                <div class="property-group"><label>🖼️ Ícone Personalizado</label><input type="file" id="prop-image" accept="image/*"></div>
                ${comp.iconFile ? `<div class="image-preview"><img src="/uploads/icons/${comp.iconFile}" style="max-width:50px;max-height:50px;"></div>` : ''}
                ${comp.imageData ? `<div class="image-preview"><img src="${comp.imageData}" style="max-width:50px;max-height:50px;"></div>` : ''}
                <div class="property-group"><label>🔌 Conectar a</label>
                    <select id="prop-connect">
                        <option value="">-- Selecione --</option>
                        ${components.filter(c => c.id !== comp.id).map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
                    </select>
                    <select id="prop-cable-type">
                        <optgroup label="📡 Conexões com Fio">
                            <option value="cat5">🟢 CAT5</option>
                            <option value="cat5e">🔵 CAT5e</option>
                            <option value="cat6">🟡 CAT6</option>
                            <option value="fiber">🔷 Fibra</option>
                            <option value="coaxial">🟣 Coaxial</option>
                            <option value="alarme">🔴 Alarme</option>
                            <option value="ci">🟣 Cabo CI</option>
                            <option value="energia">🔴 ENERGIA</option>
                        </optgroup>
                        <optgroup label="📶 Conexões Sem Fio">
                            <option value="wifi">📶 Wi-Fi</option>
                            <option value="ook">📻 OOK - Rádio Frequência</option>
                            <option value="fsk">📡 FSK - Modulação por Frequência</option>
                            <option value="amt8000">🔊 AMT 8000 - Rádio Digital</option>
                        </optgroup>
                    </select>
                    <button class="btn btn-primary" style="margin-top:5px;" onclick="addConnection(${comp.id})">➕ Conectar</button>
                </div>
                <div class="modal-buttons" style="margin-top:10px;">
                    <button class="btn btn-info" onclick="accessDeviceById(${comp.id})">🌐 Acessar</button>
                    <button class="btn btn-warning" onclick="rotateLeft(${comp.id})">🔄 Girar Esquerda</button>
                    <button class="btn btn-warning" onclick="rotateRight(${comp.id})">🔄 Girar Direita</button>
                    <button class="btn btn-danger" onclick="deleteComponent(${comp.id})">🗑 Remover</button>
                </div>
            `;
            
            const rotationSlider = document.getElementById('prop-rotation');
            if(rotationSlider) {
                rotationSlider.oninput = (e) => { comp.rotation = parseInt(e.target.value); document.getElementById('rotation-val').innerText = comp.rotation + '°'; };
            }
            
            if(comp.type === 'camera') {
                const angleSlider = document.getElementById('prop-angle');
                const fovSlider = document.getElementById('prop-fov');
                if(angleSlider) angleSlider.oninput = (e) => { comp.angle = parseInt(e.target.value); document.getElementById('angle-val').innerText = comp.angle + '°'; };
                if(fovSlider) fovSlider.oninput = (e) => { comp.fov = parseInt(e.target.value); document.getElementById('fov-val').innerText = comp.fov + '°'; };
            }
            
            document.getElementById('prop-name')?.addEventListener('change', (e) => comp.name = e.target.value);
            document.getElementById('prop-x')?.addEventListener('change', (e) => comp.x = parseInt(e.target.value));
            document.getElementById('prop-y')?.addEventListener('change', (e) => comp.y = parseInt(e.target.value));
            document.getElementById('prop-ip')?.addEventListener('change', (e) => comp.ip = e.target.value);
            document.getElementById('prop-port')?.addEventListener('change', (e) => comp.port = parseInt(e.target.value));
            document.getElementById('prop-user')?.addEventListener('change', (e) => comp.username = e.target.value);
            document.getElementById('prop-pass')?.addEventListener('change', (e) => comp.password = e.target.value);
            
            const imageInput = document.getElementById('prop-image');
            if(imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if(file) {
                        const base64 = await readImageAsBase64(file);
                        // Upload da imagem para o servidor
                        const filename = await uploadIcon(base64);
                        if (filename) {
                            comp.iconFile = filename;
                            comp.customImage = null;
                            comp.imageData = null;
                            showToast(`✅ Ícone adicionado a ${comp.name}`);
                        } else {
                            comp.customImage = base64;
                            comp.imageData = base64;
                            showToast(`✅ Imagem adicionada a ${comp.name} (modo local)`);
                        }
                    }
                };
            }
        }
        
        window.rotateLeft = (id) => {
            const comp = components.find(c => c.id === id);
            if(comp) rotateComponent(comp, -15);
        };
        
        window.rotateRight = (id) => {
            const comp = components.find(c => c.id === id);
            if(comp) rotateComponent(comp, 15);
        };
        
        function readImageAsBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        }
        
        window.accessDeviceById = (id) => {
            const comp = components.find(c => c.id === id);
            accessDevice(comp);
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
                        setTimeout(() => {
                            showWirelessAnimation(toComp.x, toComp.y, cableType);
                        }, 500);
                    }
                }
                
                showToast(`✅ Conexão ${cableInfo ? cableInfo.name : cableType.toUpperCase()} adicionada!`);
            } else {
                showToast('⚠️ Selecione um equipamento para conectar');
            }
        };
        
        window.deleteComponent = (id) => {
            if(confirm('Deseja remover este equipamento?')) {
                connections = connections.filter(c => c.from !== id && c.to !== id);
                components = components.filter(c => c.id !== id);
                selectedComponents = selectedComponents.filter(c => c.id !== id);
                showProperties(null);
                if(selectedComponents.length === 0 && selectedShapes.length === 0) closeProperties();
                showToast(`🗑 Equipamento removido!`);
            }
        };
        
        function newProject() { 
            if(confirm('Novo projeto? Todos os dados não salvos serão perdidos.')) { 
                components = []; 
                connections = []; 
                shapes = [];
                selectedComponents = []; 
                selectedShapes = [];
                closeProperties();
                showToast('📁 Novo projeto criado!');
            } 
        }
        
        function saveProjectToFile() {
            const projectData = {
                components: components.map(c => ({
                    ...c,
                    customImage: c.customImage || null,
                    imageData: c.imageData || null,
                    iconFile: c.iconFile || null
                })),
                connections: connections,
                shapes: shapes,
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
                if(!file) return;
                const reader = new FileReader();
                reader.onload = (ev) => {
                    try {
                        const data = JSON.parse(ev.target.result);
                        components = data.components || [];
                        connections = data.connections || [];
                        shapes = data.shapes || [];
                        selectedComponents = [];
                        selectedShapes = [];
                        closeProperties();
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
                    <html>
                        <head><title>Projeto CFTV</title></head>
                        <body style="margin:0; padding:20px; display:flex; justify-content:center; background:white;">
                            <img src="${imgData}" style="max-width:100%; height:auto; box-shadow:0 0 10px rgba(0,0,0,0.1);">
                            <script>
                                window.print();
                            <\\/script>
                        </body>
                    </html>
                `);
                setTimeout(() => { draw(); }, 500);
                showToast('📄 PDF gerado! Use Ctrl+P para salvar como PDF.');
            }, 100);
        }
        
        function exportPDFWithList() {
            drawWithBackground(true, true);
            
            let listHTML = '<div style="font-family: Arial, sans-serif; padding: 20px;">';
            listHTML += '<h1 style="color: #005f99; text-align: center;">PROJETIZE- LISTA DE EQUIPAMENTOS</h1>';
            listHTML += '<hr style="border-color: #005f99;">';
            listHTML += `<p><strong>Data:</strong> ${new Date().toLocaleString()}</p>`;
            listHTML += `<p><strong>Projetado por:</strong> Thiago Souza</p>`;
            listHTML += '<br>';
            
            const byType = {};
            components.forEach(comp => {
                const type = comp.type;
                if(!byType[type]) byType[type] = [];
                byType[type].push(comp);
            });
            
            for(const [type, comps] of Object.entries(byType)) {
                listHTML += `<h2 style="color: #005f99; margin-top: 20px;">📌 ${type.toUpperCase()}</h2>`;
                listHTML += '<table style="width: 100%; border-collapse: collapse;">';
                listHTML += '<tr style="background: #005f99; color: white;"><th style="padding: 8px; text-align: left;">Equipamento</th><th style="padding: 8px; text-align: left;">IP</th><th style="padding: 8px; text-align: left;">Posição</th></tr>';
                comps.forEach(comp => {
                    listHTML += `<tr style="border-bottom: 1px solid #ddd;">`;
                    listHTML += `<td style="padding: 8px;">✅ ${comp.name}</td>`;
                    listHTML += `<td style="padding: 8px;">${comp.ip || 'Não configurado'}</td>`;
                    listHTML += `<td style="padding: 8px;">X: ${Math.round(comp.x)}, Y: ${Math.round(comp.y)}</td>`;
                    listHTML += `</tr>`;
                });
                listHTML += '</table>';
            }
            
            if(connections.length > 0) {
                listHTML += '<h2 style="color: #005f99; margin-top: 20px;">🔌 CONEXÕES</h2>';
                listHTML += '<table style="width: 100%; border-collapse: collapse;">';
                listHTML += '<tr style="background: #005f99; color: white;"><th style="padding: 8px; text-align: left;">Origem</th><th style="padding: 8px; text-align: left;">Destino</th><th style="padding: 8px; text-align: left;">Tipo</th></tr>';
                connections.forEach(conn => {
                    const fromComp = components.find(c => c.id === conn.from);
                    const toComp = components.find(c => c.id === conn.to);
                    const cableInfo = cableColors[conn.type] || cableColors['cat6'];
                    if(fromComp && toComp) {
                        listHTML += `<tr style="border-bottom: 1px solid #ddd;">`;
                        listHTML += `<td style="padding: 8px;">${fromComp.name}</td>`;
                        listHTML += `<td style="padding: 8px;">${toComp.name}</td>`;
                        listHTML += `<td style="padding: 8px;">${cableInfo.name}</td>`;
                        listHTML += `<tr>`;
                    }
                });
                listHTML += '</table>';
            }
            
            listHTML += '<br><hr>';
            listHTML += `<p><strong>Total de Equipamentos:</strong> ${components.length}</p>`;
            listHTML += `<p><strong>Total de Conexões:</strong> ${connections.length}</p>`;
            listHTML += `<p><strong>Total de Formas:</strong> ${shapes.length}</p>`;
            listHTML += '<br>';
            listHTML += '<p style="text-align: center; font-size: 11px; color: #888;">Desenvolvido por Thiago Souza - Analista de Tecnologia | Unidade 2 - São José do Rio Preto</p>';
            listHTML += '</div>';
            
            const imgData = canvas.toDataURL('image/png');
            
            const pdfWindow = window.open('', '_blank');
            pdfWindow.document.write(`
                <html>
                    <head>
                        <title>Projeto CFTV - Relatório Completo</title>
                        <style>
                            @media print {
                                .page-break { page-break-before: always; }
                                body { margin: 0; padding: 0; }
                            }
                        </style>
                    </head>
                    <body style="margin:0; padding:20px; font-family: Arial, sans-serif;">
                        <div style="text-align: center; margin-bottom: 20px;">
                            <img src="${imgData}" style="max-width: 100%; height: auto; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
                        </div>
                        <div class="page-break"></div>
                        ${listHTML}
                        <script>
                            window.print();
                        <\\/script>
                    </body>
                </html>
            `);
            setTimeout(() => { draw(); }, 500);
            showToast('📄 PDF com lista de equipamentos gerado!');
        }
        
        async function startRecordingWithSelection() {
            try {
                const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
                recordingStream = stream;
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
                recordedChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) recordedChunks.push(event.data);
                };
                
                mediaRecorder.onstop = () => {
                    const blob = new Blob(recordedChunks, { type: 'video/webm' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `projeto_animado_${Date.now()}.webm`;
                    a.click();
                    URL.revokeObjectURL(url);
                    document.getElementById('recordingIndicator').style.display = 'none';
                    showToast('🎬 Vídeo salvo!');
                };
                
                mediaRecorder.start(100);
                document.getElementById('recordingIndicator').style.display = 'block';
                showToast('🔴 Selecione a área que deseja gravar!');
            } catch (err) {
                showToast('Erro ao iniciar gravação: ' + err.message);
            }
        }
        
        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                if (recordingStream) {
                    recordingStream.getTracks().forEach(track => track.stop());
                }
                document.getElementById('recordingIndicator').style.display = 'none';
            }
        }
        
        function generateBudget() { 
            let list = '📋 LISTA DE EQUIPAMENTOS - PROJETO CFTV\\n';
            list += '='.repeat(50) + '\\n\\n';
            list += `Data: ${new Date().toLocaleString()}\\n\\n`;
            
            const byType = {};
            components.forEach(comp => {
                const type = comp.type;
                if(!byType[type]) byType[type] = [];
                byType[type].push(comp);
            });
            
            for(const [type, comps] of Object.entries(byType)) {
                list += `\\n📌 ${type.toUpperCase()}:\\n`;
                list += '-'.repeat(30) + '\\n';
                comps.forEach(comp => {
                    list += `   ✅ ${comp.name}`;
                    if(comp.ip) list += ` (IP: ${comp.ip})`;
                    list += '\\n';
                });
            }
            
            list += `\\n📡 CONEXÕES:\\n`;
            list += '-'.repeat(30) + '\\n';
            connections.forEach(conn => {
                const fromComp = components.find(c => c.id === conn.from);
                const toComp = components.find(c => c.id === conn.to);
                const cableInfo = cableColors[conn.type] || cableColors['cat6'];
                if(fromComp && toComp) {
                    list += `   🔗 ${fromComp.name} → ${toComp.name} (${cableInfo.name})\\n`;
                }
            });
            
            list += `\\n${'='.repeat(50)}\\n`;
            list += `📊 TOTAL DE EQUIPAMENTOS: ${components.length}\\n`;
            list += `🔌 TOTAL DE CONEXÕES: ${connections.length}\\n`;
            list += `📐 TOTAL DE FORMAS: ${shapes.length}\\n`;
            
            const blob = new Blob([list], {type: 'text/plain;charset=utf-8'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `orcamento_${Date.now()}.txt`;
            a.click();
            showToast('💰 Orçamento gerado e baixado!');
        }
        
        function zoomIn() { 
            zoom = Math.min(zoom+0.1, 2.5); 
        }
        function zoomOut() { 
            zoom = Math.max(zoom-0.1, 0.5); 
        }
        function resetZoom() { 
            zoom = 1; 
        }
        function clearCanvas() { 
            if(confirm('Limpar tudo?')) { 
                components = []; 
                connections = []; 
                shapes = []; 
                selectedComponents = []; 
                selectedShapes = [];
                closeProperties();
                showToast('🗑 Tela limpa!'); 
            } 
        }
        
        function togglePalette() {
            const palette = document.getElementById('palette');
            const toggleBtn = document.querySelector('.toggle-palette');
            palette.classList.toggle('collapsed');
            toggleBtn.innerHTML = palette.classList.contains('collapsed') ? '▶' : '◀';
        }
        
        function closeModal() {
            if(window.currentModal) {
                document.body.removeChild(window.currentModal);
                window.currentModal = null;
            }
        }
        
        function showToast(message) {
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = message;
            document.body.appendChild(toast);
            setTimeout(() => { toast.remove(); }, 3000);
        }
        
        function renderDeviceIcon(device) {
            if(device.iconFile) {
                return `<img src="/uploads/icons/${device.iconFile}" alt="${device.name}" style="width:24px;height:24px;object-fit:contain;">`;
            }
            return device.icon || '📦';
        }
        
        function renderPalette() {
            const container = document.getElementById('categories-container');
            if(!container) return;
            container.innerHTML = '';
            
            for(const [catName, catData] of Object.entries(categories)) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';
                categoryDiv.innerHTML = `
                    <div class="category-header">
                        <h3>${catData.icon} ${catName}</h3>
                        ${(userRole === 'admin' || userRole === 'master') ? `
                        <div class="category-actions">
                            <button onclick="editCategory('${catName.replace(/'/g, "\\'")}')" title="Editar">✏️</button>
                            <button onclick="deleteCategory('${catName.replace(/'/g, "\\'")}')" title="Excluir">🗑</button>
                            <button onclick="addDeviceToCategory('${catName.replace(/'/g, "\\'")}')" title="Adicionar">➕</button>
                        </div>
                        ` : ''}
                    </div>
                    <div id="category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}"></div>
                `;
                container.appendChild(categoryDiv);
                
                const devicesContainer = document.getElementById(`category-${catName.replace(/[^a-zA-Z0-9]/g, '_')}`);
                
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
                    deviceEl.innerHTML = `
                        <div class="component-icon">${renderDeviceIcon(device)}</div>
                        <div class="component-info">
                            <div class="component-name">${device.name}</div>
                            <div class="component-desc">${device.desc || ''}</div>
                        </div>
                        ${(userRole === 'admin' || userRole === 'master') ? `
                        <div class="component-actions">
                            <button onclick="editDevice('${catName.replace(/'/g, "\\'")}', ${idx})" title="Editar">✏️</button>
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
        
        function loadDevImages() {
            if(devImageBase64) {
                const loginImg = document.getElementById('loginDevImage');
                const badgeImg = document.getElementById('badgeDevImage');
                if(loginImg) loginImg.src = 'data:image/png;base64,' + devImageBase64;
                if(badgeImg) badgeImg.src = 'data:image/png;base64,' + devImageBase64;
            }
        }
        
        function loadUserData() {
            const savedComponents = localStorage.getItem(STORAGE_KEYS.COMPONENTS(currentUser));
            const savedConnections = localStorage.getItem(STORAGE_KEYS.CONNECTIONS(currentUser));
            const savedShapes = localStorage.getItem(STORAGE_KEYS.SHAPES(currentUser));
            
            if(savedComponents) components = JSON.parse(savedComponents);
            if(savedConnections) connections = JSON.parse(savedConnections);
            if(savedShapes) shapes = JSON.parse(savedShapes);
            
            renderPalette();
        }
        
        function saveUserData() {
            localStorage.setItem(STORAGE_KEYS.COMPONENTS(currentUser), JSON.stringify(components));
            localStorage.setItem(STORAGE_KEYS.CONNECTIONS(currentUser), JSON.stringify(connections));
            localStorage.setItem(STORAGE_KEYS.SHAPES(currentUser), JSON.stringify(shapes));
        }
        
        function openAddCategoryModal() {
            if(userRole !== 'admin' && userRole !== 'master') {
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
            if(!name) {
                showToast('Digite um nome para a categoria');
                return;
            }
            if(categories[name]) {
                showToast('Categoria já existe');
                return;
            }
            categories[name] = { icon: icon || '📁', devices: [] };
            saveAllData();
            closeModal();
            renderPalette();
            showToast(`✅ Categoria "${name}" adicionada!`);
        };
        
        window.editCategory = (catName) => {
            if(userRole !== 'admin' && userRole !== 'master') {
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
            if(!newName) return;
            const catData = categories[oldName];
            delete categories[oldName];
            categories[newName] = { ...catData, icon: icon };
            saveAllData();
            closeModal();
            renderPalette();
            showToast(`✅ Categoria atualizada!`);
        };
        
        window.deleteCategory = (catName) => {
            if(userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem excluir categorias');
                return;
            }
            if(confirm(`Deseja excluir a categoria "${catName}" e todos os seus dispositivos?`)) {
                delete categories[catName];
                saveAllData();
                renderPalette();
                showToast(`🗑 Categoria "${catName}" removida!`);
            }
        };
        
        window.addDeviceToCategory = (catName) => {
            if(userRole !== 'admin' && userRole !== 'master') {
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
                        <label>OU Imagem do dispositivo</label>
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
            if(imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if(file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devImagePreview');
                        if(preview) {
                            preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">';
                        }
                        window.tempImageData = base64;
                        window.tempImageFile = await uploadIcon(base64);
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
            
            if(!name) {
                showToast('Digite um nome para o dispositivo');
                return;
            }
            
            categories[catName].devices.push({
                name, icon: icon || '📦', desc: desc || '', 
                type: type || 'custom', color: color || '#005f99',
                imageData: imageData,
                iconFile: iconFile
            });
            window.tempImageData = null;
            window.tempImageFile = null;
            saveAllData();
            closeModal();
            renderPalette();
            showToast(`✅ Dispositivo "${name}" adicionado!`);
        };
        
        window.editDevice = (catName, idx) => {
            if(userRole !== 'admin' && userRole !== 'master') {
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
                        <div class="image-preview" id="devImagePreview">${device.iconFile ? `<img src="/uploads/icons/${device.iconFile}" style="max-width:50px;max-height:50px;">` : (device.imageData ? `<img src="${device.imageData}" style="max-width:50px;max-height:50px;">` : '')}</div>
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
            if(imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if(file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devImagePreview');
                        if(preview) {
                            preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">';
                        }
                        window.tempImageData = base64;
                        window.tempImageFile = await uploadIcon(base64);
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
            
            if(!name) return;
            categories[catName].devices[idx] = {
                ...categories[catName].devices[idx],
                name, icon: icon || '📦', desc: desc || '',
                type: type || 'custom', color: color || '#005f99',
                imageData: imageData,
                iconFile: iconFile
            };
            window.tempImageData = null;
            window.tempImageFile = null;
            saveAllData();
            closeModal();
            renderPalette();
            showToast(`✅ Dispositivo atualizado!`);
        };
        
        window.deleteDevice = (catName, idx) => {
            if(userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem excluir dispositivos');
                return;
            }
            if(confirm('Deseja excluir este dispositivo?')) {
                categories[catName].devices.splice(idx, 1);
                saveAllData();
                renderPalette();
                showToast(`🗑 Dispositivo removido!`);
            }
        };
        
        function openAddDeviceModal() {
            if(userRole !== 'admin' && userRole !== 'master') {
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
                        <label>OU Imagem do equipamento</label>
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
            if(imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if(file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devImagePreview');
                        if(preview) {
                            preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">';
                        }
                        window.tempImageData = base64;
                        window.tempImageFile = await uploadIcon(base64);
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
            
            if(!name) {
                showToast('Digite um nome para o equipamento');
                return;
            }
            
            customDevices.push({
                id: Date.now(),
                name, icon: icon || '📦', desc: desc || '',
                type: type || 'custom', color: color || '#005f99',
                imageData: imageData,
                iconFile: iconFile
            });
            window.tempImageData = null;
            window.tempImageFile = null;
            saveAllData();
            closeModal();
            renderPalette();
            showToast(`✅ Equipamento "${name}" adicionado!`);
        };
        
        window.editCustomDevice = (idx) => {
            if(userRole !== 'admin' && userRole !== 'master') {
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
                        <div class="image-preview" id="devImagePreview">${device.iconFile ? `<img src="/uploads/icons/${device.iconFile}" style="max-width:50px;max-height:50px;">` : (device.imageData ? `<img src="${device.imageData}" style="max-width:50px;max-height:50px;">` : '')}</div>
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
            if(imageInput) {
                imageInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if(file) {
                        const base64 = await readImageAsBase64(file);
                        const preview = document.getElementById('devImagePreview');
                        if(preview) {
                            preview.innerHTML = '<img src="' + base64 + '" style="max-width:50px;max-height:50px;">';
                        }
                        window.tempImageData = base64;
                        window.tempImageFile = await uploadIcon(base64);
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
            
            if(!name) return;
            customDevices[idx] = {
                ...customDevices[idx],
                name, icon: icon || '📦', desc: desc || '',
                type: type || 'custom', color: color || '#005f99',
                imageData: imageData,
                iconFile: iconFile
            };
            window.tempImageData = null;
            window.tempImageFile = null;
            saveAllData();
            closeModal();
            renderPalette();
            showToast(`✅ Equipamento atualizado!`);
        };
        
        window.deleteCustomDevice = (idx) => {
            if(userRole !== 'admin' && userRole !== 'master') {
                showToast('Apenas administradores podem excluir equipamentos');
                return;
            }
            if(confirm('Deseja excluir este equipamento?')) {
                customDevices.splice(idx, 1);
                saveAllData();
                renderPalette();
                showToast(`🗑 Equipamento removido!`);
            }
        };
        
        function createMatrixAnimation() {
            const container = document.getElementById('matrixBg');
            if(!container) return;
            
            const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
            const columns = Math.floor(window.innerWidth / 20);
            
            for(let i = 0; i < columns; i++) {
                const column = document.createElement('div');
                column.className = 'matrix-column';
                column.style.left = (i * 20) + 'px';
                column.style.animationDuration = (Math.random() * 5 + 5) + 's';
                column.style.animationDelay = (Math.random() * 5) + 's';
                
                let text = '';
                for(let j = 0; j < 30; j++) {
                    text += chars[Math.floor(Math.random() * chars.length)] + '\\n';
                }
                column.textContent = text;
                container.appendChild(column);
            }
        }
        
        loadAllData();
        loadDevImages();
        renderPalette();
        createMatrixAnimation();
        closeProperties();
        
        setTimeout(() => {
            const splash = document.getElementById('splashScreen');
            if(splash) splash.style.display = 'none';
        }, 4000);
        
        window.newProject = newProject;
        window.saveProjectToFile = saveProjectToFile;
        window.loadProjectFromFile = loadProjectFromFile;
        window.exportPDF = exportPDF;
        window.exportPDFWithList = exportPDFWithList;
        window.startRecordingWithSelection = startRecordingWithSelection;
        window.stopRecording = stopRecording;
        window.generateBudget = generateBudget;
        window.zoomIn = zoomIn;
        window.zoomOut = zoomOut;
        window.resetZoom = resetZoom;
        window.clearCanvas = clearCanvas;
        window.togglePalette = togglePalette;
        window.closeModal = closeModal;
        window.openAddCategoryModal = openAddCategoryModal;
        window.openAddDeviceModal = openAddDeviceModal;
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
    </script>
</body>
</html>
"""

@app.route('/api/upload_icon', methods=['POST'])
@login_required
def upload_icon():
    data = request.json
    image_data = data.get('image', '')
    
    if not image_data or not image_data.startswith('data:image'):
        return jsonify({'success': False, 'error': 'Imagem inválida'}), 400
    
    # Extrair o formato da imagem
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
    
    filename = f"icon_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(ICONS_FOLDER, filename)
    
    try:
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        print(f"Erro ao salvar imagem: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/uploads/icons/<filename>')
def serve_icon(filename):
    return send_file(os.path.join(ICONS_FOLDER, filename))

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

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════════════════════════════════╗
    ║                                                                                          ║
    ║                    🎥 PROJETIZE - Sistema Para CFTV, Redes e muito mais...              ║
    ║                                                                                          ║
    ║     🌐 Servidor: http://localhost:5000                                                   ║
    ║                                                                                          ║
    ║     ✅ PERSISTÊNCIA DE ÍCONES IMPLEMENTADA:                                             ║
    ║     • As imagens dos ícones são salvas fisicamente na pasta uploads/icons/              ║
    ║     • Os ícones personalizados persistem mesmo após reiniciar o servidor               ║
    ║     • Exclusão de dispositivos também remove as imagens associadas                      ║
    ║     • Upload de imagens via API para o servidor                                         ║
    ║                                                                                          ║
    ║     📌 CONTROLES:                                                                       ║
    ║     • Usuário master: thiago03 / Senha: Thiago@000333                                   ║
    ║                                                                                          ║
    ║     Desenvolvido por Thiago Souza                                                       ║
    ║     Analista da Unidade 2 - São José do Rio Preto                                       ║
    ║     Todos os direitos reservados © 2024                                                 ║
    ║                                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)