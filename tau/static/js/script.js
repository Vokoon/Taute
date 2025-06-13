document.addEventListener('DOMContentLoaded', function() {
    const promptInput = document.getElementById('prompt-input');
    const generateBtn = document.getElementById('generate-btn');
    const durationSlider = document.getElementById('duration-slider');
    const durationValue = document.getElementById('duration-value');
    const authButtons = document.getElementById('auth-buttons');
    const userInfo = document.getElementById('user-info');
    const userEmail = document.getElementById('user-email');
    const userAvatar = document.getElementById('user-avatar');
    const loginBtn = document.getElementById('login-btn');
    const registerBtn = document.getElementById('register-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const submitLogin = document.getElementById('submit-login');
    const submitRegister = document.getElementById('submit-register');
    const closeLogin = document.getElementById('close-login');
    const closeRegister = document.getElementById('close-register');
    const authForms = document.getElementById('auth-forms');
    const refreshHintsBtn = document.getElementById('refresh-hints');
    const hintsContainer = document.querySelector('.hints-container');
    const tracksContainer = document.getElementById('tracks-container');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    const generationProgress = document.getElementById('generation-progress');
    const playerContainer = document.getElementById('player-container');
    const nowPlaying = document.getElementById('now-playing');
    const playBtn = document.getElementById('play-btn');
    const progressBar = document.getElementById('progress-bar');
    const currentTime = document.getElementById('current-time');
    const durationDisplay = document.getElementById('duration');
    const volumeControl = document.getElementById('volume-control');

    const audio = new Audio();
    let currentTrack = null;
    let isPlaying = false;
    let currentLang = 'ru';

    durationSlider.addEventListener('input', function() {
        durationValue.textContent = this.value;
    });

    function checkAuth() {
        fetch('/api/check-auth')
            .then(response => response.json())
            .then(data => {
                if (data.authenticated) {
                    authButtons.style.display = 'none';
                    userInfo.style.display = 'flex';
                    userEmail.textContent = data.email;
                    userAvatar.src = data.avatar;
                } else {
                    authButtons.style.display = 'flex';
                    userInfo.style.display = 'none';
                }
            });
    }

    function loadTracks() {
        fetch('/get-tracks')
            .then(response => response.json())
            .then(data => {
                tracksContainer.innerHTML = '';
                data.tracks.forEach(track => {
                    const date = new Date(track.created * 1000);
                    const trackElement = document.createElement('div');
                    trackElement.className = 'track-card';
                    trackElement.innerHTML = `
                        <audio id="audio-${track.filename}" src="/audio/${track.filename}"></audio>
                        <div class="track-info">
                            <div class="track-title">${track.filename.split('_')[1]}</div>
                            <div class="track-prompt">${track.prompt}</div>
                            <div class="track-controls">
                                <button onclick="playTrack('${track.filename}')">▶️ Воспроизвести</button>
                                <a href="/audio/${track.filename}" download="${track.filename}">
                                    <button>💾 Скачать</button>
                                </a>
                                <button onclick="deleteTrack('${track.filename}')">🗑 Удалить</button>
                            </div>
                        </div>
                    `;
                    tracksContainer.appendChild(trackElement);
                });
            });
    }

  function refreshHints() {
    fetch(`/get-hints?lang=${currentLang}`)
        .then(response => response.json())
        .then(data => {
            hintsContainer.innerHTML = '';
            data.hints.forEach(hint => {
                const hintElement = document.createElement('div');
                hintElement.className = 'hint';
                hintElement.textContent = hint;
                hintElement.onclick = () => useHint(hint);
                hintsContainer.appendChild(hintElement);
            });
        });
}

// Добавим обработчик для кнопки переключения языка
document.getElementById('lang-toggle').addEventListener('click', function() {
    currentLang = currentLang === 'ru' ? 'en' : 'ru';
    this.textContent = currentLang === 'ru' ? 'EN' : 'RU';
    refreshHints();
});

    window.useHint = function(hint) {
        promptInput.value = hint;
    }

    generateBtn.addEventListener('click', function() {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert('Пожалуйста, введите промт');
            return;
        }

        loadingOverlay.style.display = 'flex';
        loadingText.textContent = 'Генерация музыки...';
        generateBtn.disabled = true;

        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 5;
            if (progress > 95) progress = 95;
            generationProgress.style.width = `${progress}%`;
        }, 500);

        const formData = new FormData();
        formData.append('prompt', prompt);
        formData.append('duration', durationSlider.value);

        fetch('/generate', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Ошибка: ' + data.error);
            } else {
                loadingText.textContent = 'Готово!';
                generationProgress.style.width = '100%';
                setTimeout(() => {
                    loadingOverlay.style.display = 'none';
                    generateBtn.disabled = false;
                    clearInterval(progressInterval);
                    loadTracks();
                    playTrack(data.filename);
                }, 1000);
            }
        })
        .catch(error => {
            alert('Произошла ошибка: ' + error);
            loadingOverlay.style.display = 'none';
            generateBtn.disabled = false;
            clearInterval(progressInterval);
        });
    });

    loginBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        authForms.style.display = 'block';
    });

    registerBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        registerForm.style.display = 'block';
        loginForm.style.display = 'none';
        authForms.style.display = 'block';
    });

    closeLogin.addEventListener('click', function() {
        authForms.style.display = 'none';
    });

    closeRegister.addEventListener('click', function() {
        authForms.style.display = 'none';
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.auth-form') && !e.target.closest('.auth-sidebar button')) {
            authForms.style.display = 'none';
        }
    });

    submitLogin.addEventListener('click', function() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        
        fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                checkAuth();
                authForms.style.display = 'none';
            } else {
                alert(data.error || 'Ошибка входа');
            }
        });
    });

    submitRegister.addEventListener('click', function() {
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        
        fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Регистрация успешна! Войдите в систему.');
                authForms.style.display = 'none';
            } else {
                alert(data.error || 'Ошибка регистрации');
            }
        });
    });

    logoutBtn.addEventListener('click', function() {
        fetch('/logout')
            .then(() => {
                checkAuth();
                tracksContainer.innerHTML = '';
            });
    });

    refreshHintsBtn.addEventListener('click', refreshHints);

    window.playTrack = function(filename) {
        if (currentTrack === filename && isPlaying) {
            pauseTrack();
            return;
        }
        
        currentTrack = filename;
        audio.src = `/audio/${filename}`;
        audio.play();
        isPlaying = true;
        playBtn.textContent = '⏸';
        nowPlaying.textContent = filename.split('_')[1];
        playerContainer.style.display = 'block';
        
        audio.onended = function() {
            isPlaying = false;
            playBtn.textContent = '▶️';
        };
    };

    function pauseTrack() {
        audio.pause();
        isPlaying = false;
        playBtn.textContent = '▶️';
    }

    playBtn.addEventListener('click', function() {
        if (isPlaying) {
            pauseTrack();
        } else if (currentTrack) {
            audio.play();
            isPlaying = true;
            playBtn.textContent = '⏸';
        }
    });

    audio.addEventListener('timeupdate', function() {
        const current = audio.currentTime;
        const total = audio.duration || 1;
        progressBar.value = (current / total) * 100;
        currentTime.textContent = formatTime(current);
        
        if (!isNaN(total)) {
            durationDisplay.textContent = formatTime(total);
        }
    });

    progressBar.addEventListener('input', function() {
        const seekTime = (progressBar.value / 100) * audio.duration;
        audio.currentTime = seekTime;
    });

    volumeControl.addEventListener('input', function() {
        audio.volume = volumeControl.value / 100;
    });

    window.deleteTrack = function(filename) {
        if (confirm(`Удалить трек ${filename}?`)) {
            fetch('/delete-track', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `filename=${encodeURIComponent(filename)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadTracks();
                    if (currentTrack === filename) {
                        audio.pause();
                        playerContainer.style.display = 'none';
                    }
                } else {
                    alert('Не удалось удалить трек');
                }
            });
        }
    };

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }

    checkAuth();
    loadTracks();
    audio.volume = volumeControl.value / 100;
});