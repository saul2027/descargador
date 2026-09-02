# YT Downloader 🎵🎬
### Creado por Saúl Code

Descargador de YouTube con diseño premium. Soporta MP3 (320 kbps) y MP4 (mejor calidad disponible).

---

## 📦 Instalación

### 1. Requisitos previos
- Python 3.8 o superior
- FFmpeg instalado y en el PATH del sistema

### 2. Instalar FFmpeg (necesario para MP3)
**Windows:**
1. Descarga desde https://ffmpeg.org/download.html
2. Extrae y agrega la carpeta `bin` al PATH del sistema.
   O más fácil: `winget install ffmpeg`

### 3. Instalar dependencias de Python
Abre una terminal en esta carpeta y ejecuta:
```bash
pip install -r requirements.txt
```

---

## 🚀 Cómo usar

### Paso 1: Iniciar el servidor
```bash
python app.py
```
Verás: `Servidor corriendo en http://localhost:5000`

### Paso 2: Abrir la web
- Abre tu navegador y ve a: **http://localhost:5000**
- O simplemente abre el archivo `index.html` directamente en el navegador
  (asegúrate de que el servidor `app.py` esté corriendo)

### Paso 3: Descargar
1. Selecciona el formato (MP3 o MP4)
2. Pega el link de YouTube
3. Haz clic en "Descargar"
4. El archivo se guardará en tu carpeta de Descargas del navegador

---

## 📁 Estructura del proyecto
```
yt-downloader/
├── app.py           ← Backend Python (Flask)
├── index.html       ← Frontend web (HTML/CSS/JS)
├── requirements.txt ← Dependencias
├── downloads/       ← Carpeta temporal (se crea automáticamente)
└── README.md
```

---

## ⚠️ Notas
- Las descargas temporales se eliminan automáticamente después de servirse.
- Solo para uso personal.
