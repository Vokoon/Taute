import os
import time
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from audiocraft.models import musicgen
import torchaudio
import torch
import random
import warnings
from transformers import file_utils
import sqlite3
from googletrans import Translator

translator = Translator()

def translate_to_english(text):
    try:
        translation = translator.translate(text, src='ru', dest='en')
        return translation.text
    except Exception as e:
        print(f"Ошибка перевода: {e}")
        return text  # В случае ошибки возвращаем оригинальный текст

warnings.filterwarnings("ignore")
os.environ['XFORMERS_FORCE_DISABLE_TRITON'] = '1'
os.environ['XFORMERS_MORE_DETAILS'] = '0'

app = Flask(__name__)
app.secret_key = 'super_secret_key_123!'
app.config['UPLOAD_FOLDER'] = 'static/audio'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['DATABASE'] = 'users.db'
app.config['AVATAR_FOLDER'] = 'static/images/avatars'

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, email, password_hash, avatar=None):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.avatar = avatar

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password_hash, COALESCE(avatar, 'avatar-placeholder.png') FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

def init_db():
    with sqlite3.connect(app.config['DATABASE']) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                avatar TEXT DEFAULT NULL
            )
        ''')
        conn.commit()

if not os.path.exists(app.config['AVATAR_FOLDER']):
    os.makedirs(app.config['AVATAR_FOLDER'])

print("⚙️ Загрузка модели...")
try:
    model = musicgen.MusicGen.get_pretrained('facebook/musicgen-small')
    model.set_generation_params(
        duration=10,
        use_sampling=True,
        top_k=250,
        temperature=1.0,
    )
    print("✅ Модель успешно загружена")
except Exception as e:
    print(f"❌ Ошибка загрузки модели: {str(e)}")
    raise

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

prompts_file = "prompts.txt"
if not os.path.exists(prompts_file):
    with open(prompts_file, "w") as f:
        f.write("dark synthwave beat in the style of Mr Kitty\n")

with open(prompts_file, "r") as f:
    prompts = [line.strip() for line in f if line.strip()]

# В app.py заменим hint_sets на:
hint_sets = {
    'ru': [
        ["меланхоличный джаз", "энергичный рок", "спокойная фортепианная музыка", "космический синтвейв", "грустная гитарная баллада"],
        ["весёлая поп-музыка", "мрачный индастриал", "ретро фанк", "эпическая оркестровая тема", "лёгкий лоу-фай бит"],
        ["техно с ударными", "классическая соната", "дрим-поп атмосфера", "хип-хоп инструментал", "электро свинг"]
    ],
    'en': [
        ["melancholic jazz", "energetic rock", "calm piano music", "space synthwave", "sad guitar ballad"],
        ["happy pop music", "dark industrial", "retro funk", "epic orchestral theme", "light lo-fi beat"],
        ["techno with drums", "classical sonata", "dream-pop atmosphere", "hip-hop instrumental", "electro swing"]
    ]
}

@app.route('/api/check-auth')
def check_auth():
    avatar = 'avatar-placeholder.png'
    if current_user.is_authenticated:
        avatar = current_user.avatar if current_user.avatar else 'avatar-placeholder.png'
    return jsonify({
        'authenticated': current_user.is_authenticated,
        'email': current_user.email if current_user.is_authenticated else None,
        'avatar': url_for('static', filename=f'images/avatars/{avatar}')
    })

@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify(success=False, error="No file uploaded"), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify(success=False, error="No selected file"), 400
    
    filename = f"user_{current_user.id}_{int(time.time())}.png"
    filepath = os.path.join(app.config['AVATAR_FOLDER'], filename)
    file.save(filepath)
    
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar = ? WHERE id = ?", (filename, current_user.id))
    conn.commit()
    conn.close()
    
    return jsonify(success=True, avatarUrl=url_for('static', filename=f'images/avatars/{filename}'))

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password_hash, avatar FROM users WHERE email = ?", (email,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data and check_password_hash(user_data[2], password):
        user = User(user_data[0], user_data[1], user_data[2], user_data[3])
        login_user(user)
        return jsonify(success=True)
    return jsonify(success=False, error="Неверный email или пароль"), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify(success=False, error="Email и пароль обязательны"), 400
    
    password_hash = generate_password_hash(password)
    
    try:
        conn = sqlite3.connect(app.config['DATABASE'])
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, password_hash))
        conn.commit()
        conn.close()
        return jsonify(success=True)
    except sqlite3.IntegrityError:
        return jsonify(success=False, error="Пользователь уже существует"), 400

@app.route('/logout')
def logout():
    logout_user()
    return jsonify(success=True)

@app.route('/')
def index():
    return render_template('index.html', hints=random.choice(hint_sets['ru']))

# В функции generate_music замените строку с промтом:
@app.route('/generate', methods=['POST'])
@login_required
def generate_music():
    prompt = request.form.get('prompt', '').strip()
    duration = int(request.form.get('duration', 15))
    
    if not prompt:
        return jsonify({'error': 'Промт не может быть пустым'}), 400
    
    try:
        # Переводим промт на английский
        english_prompt = translate_to_english(prompt)
        print(f"Оригинальный промт: {prompt}, Переведённый: {english_prompt}")
        
        if prompt not in prompts:
            prompts.append(prompt)
            with open(prompts_file, "a") as f:
                f.write(prompt + "\n")
        
        model.set_generation_params(duration=duration)
        wav = model.generate([english_prompt], progress=True)  # Используем переведённый промт
        
        filename = f"track_{int(time.time())}_{current_user.id}.wav"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        torchaudio.save(filepath, wav[0].cpu(), 32000)
        
        return jsonify({
            'filename': filename,
            'prompt': prompt,  # Возвращаем оригинальный промт для отображения пользователю
            'duration': duration
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/get-hints')
def get_hints():
    lang = request.args.get('lang', 'ru')
    return jsonify({'hints': random.choice(hint_sets[lang])})

@app.route('/get-tracks')
@login_required
def get_tracks():
    tracks = []
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
        if file.endswith('.wav') and file.split('_')[-1].replace('.wav', '') == str(current_user.id):
            tracks.append({
                'filename': file,
                'created': os.path.getctime(os.path.join(app.config['UPLOAD_FOLDER'], file)),
                'prompt': "Сгенерированная музыка"
            })
    return jsonify({'tracks': tracks})

@app.route('/delete-track', methods=['POST'])
@login_required
def delete_track():
    filename = request.form.get('filename')
    if not filename:
        return jsonify({'error': 'Не указан файл'}), 400
    
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'success': True})
        return jsonify({'error': 'Файл не найден'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'favicon'),
                              'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    init_db()
    from waitress import serve
    print("\nСервер запущен. Откройте http://localhost:5000 в браузере")
    serve(app, host="0.0.0.0", port=5000)
