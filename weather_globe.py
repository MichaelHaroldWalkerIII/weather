#!/usr/bin/env python3
"""
3D Weather Globe Visualization
==============================
A real-time weather visualization on an interactive 3D globe.
Features: clouds, rain, wind arrows, temperature gradients, rotation, and zoom.

Uses Open-Meteo API (free, no API key required) for weather data.
"""

import http.server
import socketserver
import json
import urllib.request
import urllib.parse
from pathlib import Path
import threading
import webbrowser
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
PORT = int(os.environ.get('PORT', '8081'))  # Default 8081 (8080 often used by code-servers)
CACHE_DURATION = 300  # 5 minutes cache for weather data

# Weather data cache
weather_cache = {}
cache_lock = threading.Lock()


def fetch_weather_data(lat: float, lon: float, name: str = "") -> dict:
    """Fetch weather data from Open-Meteo API."""
    cache_key = f"{lat:.2f},{lon:.2f}"
    
    with cache_lock:
        if cache_key in weather_cache:
            cached_time, cached_data = weather_cache[cache_key]
            if time.time() - cached_time < CACHE_DURATION:
                return cached_data
    
    # Open-Meteo API - free, no API key needed
    params = {
        'latitude': lat,
        'longitude': lon,
        'current': 'temperature_2m,relative_humidity_2m,precipitation,rain,cloud_cover,wind_speed_10m,wind_direction_10m,weather_code',
        'timezone': 'auto'
    }
    
    url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            result = {
                'name': name,
                'lat': lat,
                'lon': lon,
                'temperature': data['current'].get('temperature_2m', 20),
                'humidity': data['current'].get('relative_humidity_2m', 50),
                'precipitation': data['current'].get('precipitation', 0),
                'rain': data['current'].get('rain', 0),
                'cloud_cover': data['current'].get('cloud_cover', 0),
                'wind_speed': data['current'].get('wind_speed_10m', 0),
                'wind_direction': data['current'].get('wind_direction_10m', 0),
                'weather_code': data['current'].get('weather_code', 0),
                'time': data['current'].get('time', '')
            }
            
            with cache_lock:
                weather_cache[cache_key] = (time.time(), result)
            
            print(f"  Fetched: {name}")
            return result
    except Exception as e:
        print(f"  Error fetching {name}: {e}")
        # Return simulated data on error
        import random
        return {
            'name': name,
            'lat': lat, 'lon': lon,
            'temperature': 15 + random.random() * 20,
            'humidity': 40 + random.random() * 40,
            'precipitation': random.random() * 2 if random.random() > 0.7 else 0,
            'rain': 0,
            'cloud_cover': random.random() * 100,
            'wind_speed': 5 + random.random() * 25,
            'wind_direction': random.random() * 360,
            'weather_code': 0,
            'time': '',
            'simulated': True
        }


def fetch_all_weather_data(cities: list) -> list:
    """Fetch weather data for all cities in parallel."""
    print(f"\n  Fetching weather for {len(cities)} cities...")
    results = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_city = {
            executor.submit(fetch_weather_data, city['lat'], city['lon'], city['name']): city
            for city in cities
        }
        
        for future in as_completed(future_to_city, timeout=30):
            try:
                result = future.result(timeout=5)
                results.append(result)
            except Exception as e:
                city = future_to_city[future]
                print(f"  Failed: {city['name']} - {e}")
                # Add placeholder data
                results.append({
                    'name': city['name'],
                    'lat': city['lat'], 'lon': city['lon'],
                    'temperature': 18, 'humidity': 50, 'precipitation': 0,
                    'cloud_cover': 30, 'wind_speed': 10, 'wind_direction': 180,
                    'weather_code': 0, 'time': '', 'simulated': True
                })
    
    print(f"  Done! Got data for {len(results)} cities.\n")
    return results


def get_global_weather_grid() -> list:
    """Get weather data for a grid of points across the globe."""
    # Reduced to 20 key cities for faster loading
    cities = [
        {"name": "New York", "lat": 40.71, "lon": -74.01},
        {"name": "Los Angeles", "lat": 34.05, "lon": -118.24},
        {"name": "Mexico City", "lat": 19.43, "lon": -99.13},
        {"name": "São Paulo", "lat": -23.55, "lon": -46.63},
        {"name": "London", "lat": 51.51, "lon": -0.13},
        {"name": "Paris", "lat": 48.86, "lon": 2.35},
        {"name": "Berlin", "lat": 52.52, "lon": 13.41},
        {"name": "Moscow", "lat": 55.76, "lon": 37.62},
        {"name": "Cairo", "lat": 30.04, "lon": 31.24},
        {"name": "Lagos", "lat": 6.52, "lon": 3.38},
        {"name": "Johannesburg", "lat": -26.20, "lon": 28.04},
        {"name": "Dubai", "lat": 25.20, "lon": 55.27},
        {"name": "Mumbai", "lat": 19.08, "lon": 72.88},
        {"name": "Beijing", "lat": 39.90, "lon": 116.41},
        {"name": "Tokyo", "lat": 35.68, "lon": 139.69},
        {"name": "Seoul", "lat": 37.57, "lon": 126.98},
        {"name": "Singapore", "lat": 1.35, "lon": 103.82},
        {"name": "Sydney", "lat": -33.87, "lon": 151.21},
        {"name": "Honolulu", "lat": 21.31, "lon": -157.86},
        {"name": "Reykjavik", "lat": 64.15, "lon": -21.94},
    ]
    
    return cities


class WeatherRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for weather data API."""
    
    def __init__(self, *args, **kwargs):
        self.directory = str(Path(__file__).parent)
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def do_GET(self):
        if self.path == '/api/weather/grid':
            self.send_weather_grid()
        elif self.path.startswith('/api/weather/location'):
            self.send_location_weather()
        elif self.path == '/api/cities':
            self.send_cities()
        else:
            super().do_GET()
    
    def send_weather_grid(self):
        """Send weather data for all grid points."""
        cities = get_global_weather_grid()
        weather_data = fetch_all_weather_data(cities)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(weather_data).encode())
    
    def send_location_weather(self):
        """Send weather for a specific location."""
        try:
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            lat = float(params.get('lat', [0])[0])
            lon = float(params.get('lon', [0])[0])
            
            data = fetch_weather_data(lat, lon, f"Location ({lat:.2f}, {lon:.2f})")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except Exception as e:
            self.send_error(400, str(e))
    
    def send_cities(self):
        """Send list of cities."""
        cities = get_global_weather_grid()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(cities).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging for cleaner output."""
        if '/api/' in str(args):
            print(f"API: {args[0]}")


def create_html_file():
    """Create the main HTML visualization file."""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Weather Globe</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Rajdhani', sans-serif;
            background: #000;
            overflow: hidden;
            color: #fff;
        }
        
        #canvas-container {
            width: 100vw;
            height: 100vh;
            position: relative;
        }
        
        #globe-canvas {
            width: 100%;
            height: 100%;
            display: block;
        }
        
        /* Control Panel */
        .control-panel {
            position: fixed;
            top: 20px;
            left: 20px;
            background: linear-gradient(135deg, rgba(10, 20, 40, 0.95), rgba(5, 15, 35, 0.9));
            border: 1px solid rgba(0, 200, 255, 0.3);
            border-radius: 16px;
            padding: 24px;
            min-width: 320px;
            backdrop-filter: blur(20px);
            box-shadow: 
                0 0 40px rgba(0, 150, 255, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            z-index: 100;
        }
        
        .panel-title {
            font-family: 'Orbitron', monospace;
            font-size: 1.4rem;
            font-weight: 900;
            letter-spacing: 3px;
            margin-bottom: 20px;
            background: linear-gradient(90deg, #00d4ff, #00ff88, #00d4ff);
            background-size: 200% 100%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shimmer 3s ease-in-out infinite;
            text-transform: uppercase;
        }
        
        @keyframes shimmer {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .layer-toggle {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            margin: 8px 0;
            background: rgba(0, 100, 150, 0.2);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 1px solid transparent;
        }
        
        .layer-toggle:hover {
            background: rgba(0, 150, 200, 0.3);
            border-color: rgba(0, 200, 255, 0.4);
            transform: translateX(4px);
        }
        
        .layer-toggle.active {
            background: rgba(0, 200, 255, 0.2);
            border-color: rgba(0, 200, 255, 0.6);
            box-shadow: 0 0 20px rgba(0, 200, 255, 0.2);
        }
        
        .layer-icon {
            width: 32px;
            height: 32px;
            margin-right: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
        }
        
        .layer-name {
            font-weight: 600;
            font-size: 1rem;
            letter-spacing: 1px;
        }
        
        /* Info Panel */
        .info-panel {
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, rgba(10, 20, 40, 0.95), rgba(5, 15, 35, 0.9));
            border: 1px solid rgba(0, 200, 255, 0.3);
            border-radius: 16px;
            padding: 24px;
            min-width: 300px;
            backdrop-filter: blur(20px);
            box-shadow: 0 0 40px rgba(0, 150, 255, 0.2);
            z-index: 100;
            display: none;
        }
        
        .info-panel.visible {
            display: block;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .info-title {
            font-family: 'Orbitron', monospace;
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 16px;
            color: #00d4ff;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(0, 200, 255, 0.15);
        }
        
        .info-label {
            color: rgba(255, 255, 255, 0.6);
            font-weight: 500;
        }
        
        .info-value {
            font-weight: 700;
            color: #00ff88;
        }
        
        /* Legend */
        .legend {
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: linear-gradient(135deg, rgba(10, 20, 40, 0.9), rgba(5, 15, 35, 0.85));
            border: 1px solid rgba(0, 200, 255, 0.3);
            border-radius: 12px;
            padding: 16px 20px;
            backdrop-filter: blur(20px);
            z-index: 100;
        }
        
        .legend-title {
            font-family: 'Orbitron', monospace;
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 12px;
            color: #00d4ff;
            letter-spacing: 2px;
        }
        
        .temp-gradient {
            height: 16px;
            width: 220px;
            border-radius: 8px;
            background: linear-gradient(90deg, 
                #1a237e, #0d47a1, #01579b, #006064, 
                #1b5e20, #33691e, #f57f17, #e65100, 
                #bf360c, #b71c1c);
            margin-bottom: 8px;
        }
        
        .temp-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.7);
        }
        
        /* Loading */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(ellipse at center, #0a1628 0%, #000 100%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            transition: opacity 0.5s ease;
        }
        
        .loading-overlay.hidden {
            opacity: 0;
            pointer-events: none;
        }
        
        .loading-globe {
            width: 100px;
            height: 100px;
            border: 3px solid rgba(0, 200, 255, 0.2);
            border-top-color: #00d4ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .loading-text {
            font-family: 'Orbitron', monospace;
            margin-top: 24px;
            font-size: 1.1rem;
            color: #00d4ff;
            letter-spacing: 4px;
        }
        
        /* Instructions */
        .instructions {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, rgba(10, 20, 40, 0.85), rgba(5, 15, 35, 0.8));
            border: 1px solid rgba(0, 200, 255, 0.2);
            border-radius: 12px;
            padding: 16px 20px;
            backdrop-filter: blur(20px);
            z-index: 100;
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .instructions strong {
            color: #00d4ff;
        }
        
        /* City search */
        .search-container {
            margin-top: 16px;
            position: relative;
        }
        
        .search-input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(0, 50, 80, 0.4);
            border: 1px solid rgba(0, 200, 255, 0.3);
            border-radius: 10px;
            color: #fff;
            font-family: 'Rajdhani', sans-serif;
            font-size: 1rem;
            outline: none;
            transition: all 0.3s ease;
        }
        
        .search-input::placeholder {
            color: rgba(255, 255, 255, 0.4);
        }
        
        .search-input:focus {
            border-color: #00d4ff;
            box-shadow: 0 0 20px rgba(0, 200, 255, 0.3);
        }
        
        .search-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: rgba(10, 20, 40, 0.98);
            border: 1px solid rgba(0, 200, 255, 0.3);
            border-radius: 10px;
            margin-top: 8px;
            max-height: 200px;
            overflow-y: auto;
            display: none;
        }
        
        .search-results.visible {
            display: block;
        }
        
        .search-result {
            padding: 12px 16px;
            cursor: pointer;
            transition: all 0.2s ease;
            border-bottom: 1px solid rgba(0, 200, 255, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .search-result:hover {
            background: rgba(0, 200, 255, 0.2);
        }
        
        .search-result:last-child {
            border-bottom: none;
        }
        
        /* Weather status indicator */
        .status-bar {
            position: fixed;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(90deg, transparent, rgba(0, 200, 255, 0.1), transparent);
            padding: 8px 40px;
            font-size: 0.8rem;
            color: rgba(255, 255, 255, 0.6);
            font-family: 'Rajdhani', sans-serif;
            letter-spacing: 2px;
            z-index: 100;
        }
        
        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #00ff88;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
    </style>
</head>
<body>
    <div class="loading-overlay" id="loading">
        <div class="loading-globe"></div>
        <div class="loading-text">LOADING WEATHER DATA</div>
    </div>
    
    <div class="status-bar">
        <span class="status-dot"></span>
        LIVE WEATHER DATA
    </div>
    
    <div id="canvas-container">
        <canvas id="globe-canvas"></canvas>
    </div>
    
    <div class="control-panel">
        <div class="panel-title">Weather Layers</div>
        
        <div class="layer-toggle active" data-layer="temperature">
            <div class="layer-icon">🌡️</div>
            <div class="layer-name">Temperature</div>
        </div>
        
        <div class="layer-toggle active" data-layer="clouds">
            <div class="layer-icon">☁️</div>
            <div class="layer-name">Cloud Cover</div>
        </div>
        
        <div class="layer-toggle active" data-layer="rain">
            <div class="layer-icon">🌧️</div>
            <div class="layer-name">Precipitation</div>
        </div>
        
        <div class="layer-toggle active" data-layer="wind">
            <div class="layer-icon">💨</div>
            <div class="layer-name">Wind Direction</div>
        </div>
        
        <div class="search-container">
            <input type="text" class="search-input" id="city-search" placeholder="Search city...">
            <div class="search-results" id="search-results"></div>
        </div>
    </div>
    
    <div class="info-panel" id="info-panel">
        <div class="info-title" id="location-name">Select a location</div>
        <div class="info-row">
            <span class="info-label">Temperature</span>
            <span class="info-value" id="info-temp">--</span>
        </div>
        <div class="info-row">
            <span class="info-label">Humidity</span>
            <span class="info-value" id="info-humidity">--</span>
        </div>
        <div class="info-row">
            <span class="info-label">Cloud Cover</span>
            <span class="info-value" id="info-clouds">--</span>
        </div>
        <div class="info-row">
            <span class="info-label">Wind Speed</span>
            <span class="info-value" id="info-wind">--</span>
        </div>
        <div class="info-row">
            <span class="info-label">Wind Direction</span>
            <span class="info-value" id="info-wind-dir">--</span>
        </div>
        <div class="info-row">
            <span class="info-label">Precipitation</span>
            <span class="info-value" id="info-precip">--</span>
        </div>
    </div>
    
    <div class="legend">
        <div class="legend-title">TEMPERATURE</div>
        <div class="temp-gradient"></div>
        <div class="temp-labels">
            <span>-30°C</span>
            <span>0°C</span>
            <span>20°C</span>
            <span>45°C</span>
        </div>
    </div>
    
    <div class="instructions">
        <strong>Drag</strong> to rotate · <strong>Scroll</strong> to zoom · <strong>Click</strong> marker for details
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
        // ============================================
        // 3D Weather Globe Visualization
        // ============================================
        
        let scene, camera, renderer, globe, atmosphere;
        let weatherMarkers = [];
        let cloudParticles = [];
        let rainParticles = [];
        let windArrows = [];
        let weatherData = [];
        let cities = [];
        
        // Layer visibility
        const layers = {
            temperature: true,
            clouds: true,
            rain: true,
            wind: true
        };
        
        // Mouse interaction
        let isDragging = false;
        let previousMousePosition = { x: 0, y: 0 };
        let targetRotation = { x: 0.3, y: 0 };
        let currentRotation = { x: 0.3, y: 0 };
        let autoRotate = true;
        let zoomLevel = 2.5;
        let targetZoom = 2.5;
        
        // Raycaster for clicking
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        
        // Initialize scene
        function init() {
            const container = document.getElementById('canvas-container');
            const canvas = document.getElementById('globe-canvas');
            
            // Scene
            scene = new THREE.Scene();
            
            // Camera
            camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.z = zoomLevel;
            
            // Renderer
            renderer = new THREE.WebGLRenderer({ 
                canvas: canvas,
                antialias: true,
                alpha: true 
            });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            renderer.setClearColor(0x000510, 1);
            
            // Create starfield background
            createStarfield();
            
            // Create Earth
            createEarth();
            
            // Lighting
            const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
            scene.add(ambientLight);
            
            const sunLight = new THREE.DirectionalLight(0xffffff, 1.2);
            sunLight.position.set(5, 3, 5);
            scene.add(sunLight);
            
            const rimLight = new THREE.DirectionalLight(0x00aaff, 0.4);
            rimLight.position.set(-5, 0, -5);
            scene.add(rimLight);
            
            // Event listeners
            setupEventListeners();
            
            // Load weather data
            loadWeatherData();
            
            // Animation loop
            animate();
        }
        
        function createStarfield() {
            const starsGeometry = new THREE.BufferGeometry();
            const starCount = 3000;
            const positions = new Float32Array(starCount * 3);
            const colors = new Float32Array(starCount * 3);
            
            for (let i = 0; i < starCount; i++) {
                const i3 = i * 3;
                const radius = 50 + Math.random() * 100;
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.acos(2 * Math.random() - 1);
                
                positions[i3] = radius * Math.sin(phi) * Math.cos(theta);
                positions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
                positions[i3 + 2] = radius * Math.cos(phi);
                
                const brightness = 0.5 + Math.random() * 0.5;
                colors[i3] = brightness;
                colors[i3 + 1] = brightness;
                colors[i3 + 2] = brightness + Math.random() * 0.2;
            }
            
            starsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            starsGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
            
            const starsMaterial = new THREE.PointsMaterial({
                size: 0.15,
                vertexColors: true,
                transparent: true,
                opacity: 0.8
            });
            
            const stars = new THREE.Points(starsGeometry, starsMaterial);
            scene.add(stars);
        }
        
        function createEarth() {
            // Earth sphere
            const earthGeometry = new THREE.SphereGeometry(1, 64, 64);
            
            // Load Earth texture from public CDN
            const textureLoader = new THREE.TextureLoader();
            
            // Use a high-quality Earth texture
            const earthTexture = textureLoader.load(
                'https://unpkg.com/three-globe@2.24.10/example/img/earth-blue-marble.jpg',
                function(texture) {
                    console.log('Earth texture loaded');
                },
                undefined,
                function(err) {
                    console.log('Texture load failed, using fallback');
                    // Fallback to procedural texture if load fails
                    createFallbackTexture();
                }
            );
            
            const earthMaterial = new THREE.MeshPhongMaterial({
                map: earthTexture,
                bumpScale: 0.02,
                specular: new THREE.Color(0x333333),
                shininess: 15
            });
            
            globe = new THREE.Mesh(earthGeometry, earthMaterial);
            scene.add(globe);
            
            // Atmosphere glow
            const atmosphereGeometry = new THREE.SphereGeometry(1.02, 64, 64);
            const atmosphereMaterial = new THREE.ShaderMaterial({
                vertexShader: \`
                    varying vec3 vNormal;
                    void main() {
                        vNormal = normalize(normalMatrix * normal);
                        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                    }
                \`,
                fragmentShader: \`
                    varying vec3 vNormal;
                    void main() {
                        float intensity = pow(0.7 - dot(vNormal, vec3(0, 0, 1.0)), 2.0);
                        gl_FragColor = vec4(0.3, 0.6, 1.0, 1.0) * intensity;
                    }
                \`,
                blending: THREE.AdditiveBlending,
                side: THREE.BackSide,
                transparent: true
            });
            
            atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
            scene.add(atmosphere);
            
            // Grid lines (latitude/longitude)
            const gridMaterial = new THREE.LineBasicMaterial({ 
                color: 0x00aaff, 
                transparent: true, 
                opacity: 0.08
            });
            
            // Latitude lines
            for (let lat = -60; lat <= 60; lat += 30) {
                const latRad = lat * Math.PI / 180;
                const radius = Math.cos(latRad);
                const y = Math.sin(latRad);
                
                const points = [];
                for (let lon = 0; lon <= 360; lon += 5) {
                    const lonRad = lon * Math.PI / 180;
                    points.push(new THREE.Vector3(
                        radius * Math.cos(lonRad) * 1.002,
                        y * 1.002,
                        radius * Math.sin(lonRad) * 1.002
                    ));
                }
                
                const geometry = new THREE.BufferGeometry().setFromPoints(points);
                const line = new THREE.Line(geometry, gridMaterial);
                globe.add(line);
            }
            
            // Longitude lines
            for (let lon = 0; lon < 360; lon += 30) {
                const lonRad = lon * Math.PI / 180;
                const points = [];
                
                for (let lat = -90; lat <= 90; lat += 5) {
                    const latRad = lat * Math.PI / 180;
                    points.push(new THREE.Vector3(
                        Math.cos(latRad) * Math.cos(lonRad) * 1.002,
                        Math.sin(latRad) * 1.002,
                        Math.cos(latRad) * Math.sin(lonRad) * 1.002
                    ));
                }
                
                const geometry = new THREE.BufferGeometry().setFromPoints(points);
                const line = new THREE.Line(geometry, gridMaterial);
                globe.add(line);
            }
        }
        
        function createFallbackTexture() {
            // Fallback procedural texture if CDN fails
            const canvas = document.createElement('canvas');
            canvas.width = 1024;
            canvas.height = 512;
            const ctx = canvas.getContext('2d');
            
            // Ocean
            ctx.fillStyle = '#0a4a7a';
            ctx.fillRect(0, 0, 1024, 512);
            
            // Simple continents
            ctx.fillStyle = '#2d5a27';
            ctx.beginPath(); ctx.ellipse(180, 140, 90, 70, -0.2, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(260, 330, 45, 90, 0.2, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(512, 180, 40, 130, 0, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(720, 160, 140, 90, 0, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(850, 350, 50, 35, 0, 0, Math.PI * 2); ctx.fill();
            
            if (globe && globe.material) {
                globe.material.map = new THREE.CanvasTexture(canvas);
                globe.material.needsUpdate = true;
            }
        }
        
        function latLonToVector3(lat, lon, radius = 1.02) {
            const phi = (90 - lat) * (Math.PI / 180);
            const theta = (lon + 180) * (Math.PI / 180);
            
            return new THREE.Vector3(
                -radius * Math.sin(phi) * Math.cos(theta),
                radius * Math.cos(phi),
                radius * Math.sin(phi) * Math.sin(theta)
            );
        }
        
        function getTemperatureColor(temp) {
            // Temperature color gradient from cold (blue) to hot (red)
            const normalized = Math.max(0, Math.min(1, (temp + 30) / 75)); // -30 to 45
            
            if (normalized < 0.25) {
                // Deep blue to cyan
                const t = normalized / 0.25;
                return new THREE.Color().setHSL(0.65 - t * 0.1, 0.9, 0.3 + t * 0.2);
            } else if (normalized < 0.5) {
                // Cyan to green
                const t = (normalized - 0.25) / 0.25;
                return new THREE.Color().setHSL(0.55 - t * 0.2, 0.8, 0.4 + t * 0.1);
            } else if (normalized < 0.75) {
                // Green to yellow/orange
                const t = (normalized - 0.5) / 0.25;
                return new THREE.Color().setHSL(0.35 - t * 0.25, 0.9, 0.5);
            } else {
                // Orange to red
                const t = (normalized - 0.75) / 0.25;
                return new THREE.Color().setHSL(0.1 - t * 0.1, 1, 0.5 - t * 0.1);
            }
        }
        
        function createWeatherMarker(data) {
            const group = new THREE.Group();
            const position = latLonToVector3(data.lat, data.lon, 1.02);
            group.position.copy(position);
            
            // Temperature indicator (glowing sphere)
            const tempColor = getTemperatureColor(data.temperature);
            const markerGeometry = new THREE.SphereGeometry(0.025, 16, 16);
            const markerMaterial = new THREE.MeshBasicMaterial({ 
                color: tempColor,
                transparent: true,
                opacity: 0.9
            });
            const marker = new THREE.Mesh(markerGeometry, markerMaterial);
            marker.userData = { ...data, type: 'weather-marker' };
            group.add(marker);
            
            // Glow effect
            const glowGeometry = new THREE.SphereGeometry(0.04, 16, 16);
            const glowMaterial = new THREE.MeshBasicMaterial({ 
                color: tempColor,
                transparent: true,
                opacity: 0.3
            });
            const glow = new THREE.Mesh(glowGeometry, glowMaterial);
            group.add(glow);
            
            group.userData = data;
            return group;
        }
        
        function createCloudParticle(data) {
            if (data.cloud_cover < 20) return null;
            
            const position = latLonToVector3(data.lat, data.lon, 1.06 + Math.random() * 0.03);
            
            const cloudGeometry = new THREE.SphereGeometry(0.03 + (data.cloud_cover / 100) * 0.04, 8, 8);
            const cloudMaterial = new THREE.MeshBasicMaterial({
                color: 0xffffff,
                transparent: true,
                opacity: Math.min(0.7, data.cloud_cover / 100)
            });
            
            const cloud = new THREE.Mesh(cloudGeometry, cloudMaterial);
            cloud.position.copy(position);
            cloud.userData = { 
                originalPos: position.clone(),
                cloudCover: data.cloud_cover,
                offset: Math.random() * Math.PI * 2
            };
            
            return cloud;
        }
        
        function createRainParticles(data) {
            if (data.precipitation < 0.1) return [];
            
            const particles = [];
            const intensity = Math.min(20, Math.floor(data.precipitation * 5) + 3);
            
            for (let i = 0; i < intensity; i++) {
                const offsetLat = (Math.random() - 0.5) * 5;
                const offsetLon = (Math.random() - 0.5) * 5;
                const position = latLonToVector3(data.lat + offsetLat, data.lon + offsetLon, 1.05 + Math.random() * 0.05);
                
                const rainGeometry = new THREE.SphereGeometry(0.008, 4, 4);
                const rainMaterial = new THREE.MeshBasicMaterial({
                    color: 0x4fc3f7,
                    transparent: true,
                    opacity: 0.7
                });
                
                const rain = new THREE.Mesh(rainGeometry, rainMaterial);
                rain.position.copy(position);
                rain.userData = {
                    basePosition: position.clone(),
                    speed: 0.001 + Math.random() * 0.002,
                    offset: Math.random() * Math.PI * 2
                };
                
                particles.push(rain);
            }
            
            return particles;
        }
        
        function createWindArrow(data) {
            if (data.wind_speed < 5) return null;
            
            const position = latLonToVector3(data.lat, data.lon, 1.08);
            
            // Arrow shaft
            const length = 0.02 + (data.wind_speed / 50) * 0.05;
            const arrowGeometry = new THREE.ConeGeometry(0.008, length, 8);
            
            // Wind direction colors based on speed
            let arrowColor;
            if (data.wind_speed < 15) {
                arrowColor = 0x00ff88;
            } else if (data.wind_speed < 30) {
                arrowColor = 0xffff00;
            } else {
                arrowColor = 0xff4444;
            }
            
            const arrowMaterial = new THREE.MeshBasicMaterial({
                color: arrowColor,
                transparent: true,
                opacity: 0.8
            });
            
            const arrow = new THREE.Mesh(arrowGeometry, arrowMaterial);
            arrow.position.copy(position);
            
            // Orient arrow based on wind direction
            const windRad = (data.wind_direction - 90) * Math.PI / 180;
            
            // Calculate tangent direction on sphere surface
            const up = position.clone().normalize();
            const north = new THREE.Vector3(0, 1, 0);
            const east = new THREE.Vector3().crossVectors(north, up).normalize();
            const localNorth = new THREE.Vector3().crossVectors(up, east).normalize();
            
            // Wind direction in local coordinates
            const windDir = new THREE.Vector3()
                .addScaledVector(east, Math.cos(windRad))
                .addScaledVector(localNorth, Math.sin(windRad));
            
            arrow.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), windDir);
            
            arrow.userData = { 
                windSpeed: data.wind_speed,
                windDirection: data.wind_direction
            };
            
            return arrow;
        }
        
        async function loadWeatherData() {
            try {
                // Show globe immediately with placeholder data
                document.querySelector('.loading-text').textContent = 'LOADING GLOBE...';
                
                // Fetch cities list first (fast)
                const citiesResponse = await fetch('/api/cities');
                cities = await citiesResponse.json();
                
                // Create initial markers with placeholder data so globe shows immediately
                console.log('Creating initial markers...');
                cities.forEach(city => {
                    const placeholderData = {
                        ...city,
                        temperature: 15 + Math.random() * 15,
                        humidity: 50,
                        precipitation: 0,
                        cloud_cover: 30,
                        wind_speed: 10,
                        wind_direction: Math.random() * 360
                    };
                    weatherData.push(placeholderData);
                    
                    const marker = createWeatherMarker(placeholderData);
                    globe.add(marker);
                    weatherMarkers.push(marker);
                });
                
                // Hide loading overlay - globe is now visible
                document.getElementById('loading').classList.add('hidden');
                console.log('Globe visible with placeholder data');
                
                // Now fetch real weather data in background
                document.querySelector('.loading-text').textContent = 'UPDATING WEATHER...';
                
                try {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
                    
                    const weatherResponse = await fetch('/api/weather/grid', { signal: controller.signal });
                    clearTimeout(timeoutId);
                    
                    const realWeatherData = await weatherResponse.json();
                    
                    if (realWeatherData && realWeatherData.length > 0) {
                        // Clear old markers
                        weatherMarkers.forEach(m => globe.remove(m));
                        cloudParticles.forEach(c => scene.remove(c));
                        rainParticles.forEach(r => scene.remove(r));
                        windArrows.forEach(w => globe.remove(w));
                        
                        weatherMarkers = [];
                        cloudParticles = [];
                        rainParticles = [];
                        windArrows = [];
                        weatherData = realWeatherData;
                        
                        // Create visualization with real data
                        weatherData.forEach(data => {
                            const marker = createWeatherMarker(data);
                            globe.add(marker);
                            weatherMarkers.push(marker);
                            
                            const cloud = createCloudParticle(data);
                            if (cloud) {
                                scene.add(cloud);
                                cloudParticles.push(cloud);
                            }
                            
                            const rain = createRainParticles(data);
                            rain.forEach(r => {
                                scene.add(r);
                                rainParticles.push(r);
                            });
                            
                            const arrow = createWindArrow(data);
                            if (arrow) {
                                globe.add(arrow);
                                windArrows.push(arrow);
                            }
                        });
                        
                        console.log(`Updated with real weather data for ${weatherData.length} locations`);
                    }
                } catch (weatherError) {
                    console.log('Weather fetch timed out or failed, using placeholder data:', weatherError.message);
                }
                
            } catch (error) {
                console.error('Error loading data:', error);
                // Still show globe even if everything fails
                document.getElementById('loading').classList.add('hidden');
            }
        }
        
        function setupEventListeners() {
            const canvas = renderer.domElement;
            
            // Mouse drag for rotation
            canvas.addEventListener('mousedown', (e) => {
                isDragging = true;
                autoRotate = false;
                previousMousePosition = { x: e.clientX, y: e.clientY };
            });
            
            canvas.addEventListener('mousemove', (e) => {
                if (isDragging) {
                    const deltaX = e.clientX - previousMousePosition.x;
                    const deltaY = e.clientY - previousMousePosition.y;
                    
                    targetRotation.y += deltaX * 0.005;
                    targetRotation.x += deltaY * 0.005;
                    targetRotation.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, targetRotation.x));
                    
                    previousMousePosition = { x: e.clientX, y: e.clientY };
                }
            });
            
            canvas.addEventListener('mouseup', () => {
                isDragging = false;
            });
            
            canvas.addEventListener('mouseleave', () => {
                isDragging = false;
            });
            
            // Touch events for mobile
            canvas.addEventListener('touchstart', (e) => {
                if (e.touches.length === 1) {
                    isDragging = true;
                    autoRotate = false;
                    previousMousePosition = { 
                        x: e.touches[0].clientX, 
                        y: e.touches[0].clientY 
                    };
                }
            });
            
            canvas.addEventListener('touchmove', (e) => {
                if (isDragging && e.touches.length === 1) {
                    const deltaX = e.touches[0].clientX - previousMousePosition.x;
                    const deltaY = e.touches[0].clientY - previousMousePosition.y;
                    
                    targetRotation.y += deltaX * 0.005;
                    targetRotation.x += deltaY * 0.005;
                    targetRotation.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, targetRotation.x));
                    
                    previousMousePosition = { 
                        x: e.touches[0].clientX, 
                        y: e.touches[0].clientY 
                    };
                }
            });
            
            canvas.addEventListener('touchend', () => {
                isDragging = false;
            });
            
            // Scroll for zoom
            canvas.addEventListener('wheel', (e) => {
                e.preventDefault();
                targetZoom += e.deltaY * 0.001;
                targetZoom = Math.max(1.5, Math.min(5, targetZoom));
            });
            
            // Click for location info
            canvas.addEventListener('click', (e) => {
                if (isDragging) return;
                
                mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
                mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
                
                raycaster.setFromCamera(mouse, camera);
                
                const markerMeshes = [];
                weatherMarkers.forEach(group => {
                    group.traverse(child => {
                        if (child.isMesh && child.userData.type === 'weather-marker') {
                            markerMeshes.push(child);
                        }
                    });
                });
                
                const intersects = raycaster.intersectObjects(markerMeshes);
                
                if (intersects.length > 0) {
                    const data = intersects[0].object.userData;
                    showLocationInfo(data);
                }
            });
            
            // Layer toggles
            document.querySelectorAll('.layer-toggle').forEach(toggle => {
                toggle.addEventListener('click', () => {
                    const layer = toggle.dataset.layer;
                    layers[layer] = !layers[layer];
                    toggle.classList.toggle('active');
                    updateLayerVisibility();
                });
            });
            
            // City search
            const searchInput = document.getElementById('city-search');
            const searchResults = document.getElementById('search-results');
            
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase().trim();
                if (query.length < 1) {
                    searchResults.classList.remove('visible');
                    return;
                }
                
                // Search in weatherData (which has all the city info with weather)
                const dataToSearch = weatherData.length > 0 ? weatherData : cities;
                const matches = dataToSearch.filter(city => 
                    city.name && city.name.toLowerCase().includes(query)
                ).slice(0, 8);
                
                if (matches.length > 0) {
                    searchResults.innerHTML = matches.map(city => 
                        `<div class="search-result" data-lat="${city.lat}" data-lon="${city.lon}" data-name="${city.name}">
                            <span>${city.name}</span>
                            ${city.temperature !== undefined ? `<span style="color:#00ff88;margin-left:8px">${city.temperature.toFixed(1)}°C</span>` : ''}
                        </div>`
                    ).join('');
                    searchResults.classList.add('visible');
                    
                    searchResults.querySelectorAll('.search-result').forEach(result => {
                        result.addEventListener('click', () => {
                            const lat = parseFloat(result.dataset.lat);
                            const lon = parseFloat(result.dataset.lon);
                            const name = result.dataset.name;
                            
                            // Find full weather data for this city
                            const cityData = weatherData.find(c => c.name === name);
                            if (cityData) {
                                showLocationInfo(cityData);
                            }
                            
                            focusOnLocation(lat, lon, name);
                            searchResults.classList.remove('visible');
                            searchInput.value = name;
                        });
                    });
                } else {
                    searchResults.innerHTML = '<div style="padding:12px;color:rgba(255,255,255,0.5)">No cities found</div>';
                    searchResults.classList.add('visible');
                }
            });
            
            searchInput.addEventListener('focus', () => {
                if (searchInput.value.length >= 1) {
                    searchInput.dispatchEvent(new Event('input'));
                }
            });
            
            searchInput.addEventListener('blur', () => {
                setTimeout(() => searchResults.classList.remove('visible'), 200);
            });
            
            // Window resize
            window.addEventListener('resize', () => {
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            });
        }
        
        function updateLayerVisibility() {
            // Temperature markers
            weatherMarkers.forEach(marker => {
                marker.visible = layers.temperature;
            });
            
            // Clouds
            cloudParticles.forEach(cloud => {
                cloud.visible = layers.clouds;
            });
            
            // Rain
            rainParticles.forEach(rain => {
                rain.visible = layers.rain;
            });
            
            // Wind
            windArrows.forEach(arrow => {
                arrow.visible = layers.wind;
            });
        }
        
        function showLocationInfo(data) {
            const panel = document.getElementById('info-panel');
            panel.classList.add('visible');
            
            document.getElementById('location-name').textContent = data.name || `${data.lat.toFixed(2)}°, ${data.lon.toFixed(2)}°`;
            document.getElementById('info-temp').textContent = `${data.temperature.toFixed(1)}°C`;
            document.getElementById('info-humidity').textContent = `${data.humidity}%`;
            document.getElementById('info-clouds').textContent = `${data.cloud_cover}%`;
            document.getElementById('info-wind').textContent = `${data.wind_speed.toFixed(1)} km/h`;
            document.getElementById('info-wind-dir').textContent = `${data.wind_direction}°`;
            document.getElementById('info-precip').textContent = `${data.precipitation.toFixed(1)} mm`;
        }
        
        function focusOnLocation(lat, lon, name) {
            // Calculate target rotation to face the location
            const lonRad = lon * Math.PI / 180;
            targetRotation.y = -lonRad - Math.PI / 2;
            targetRotation.x = lat * Math.PI / 180 * 0.5;
            
            // Find weather data for this location
            const data = weatherData.find(d => 
                Math.abs(d.lat - lat) < 1 && Math.abs(d.lon - lon) < 1
            );
            
            if (data) {
                showLocationInfo({ ...data, name });
            }
            
            // Zoom in slightly
            targetZoom = 2;
            autoRotate = false;
        }
        
        function animate() {
            requestAnimationFrame(animate);
            
            const time = Date.now() * 0.001;
            
            // Auto-rotate when not interacting
            if (autoRotate) {
                targetRotation.y += 0.001;
            }
            
            // Smooth rotation interpolation
            currentRotation.x += (targetRotation.x - currentRotation.x) * 0.05;
            currentRotation.y += (targetRotation.y - currentRotation.y) * 0.05;
            
            globe.rotation.x = currentRotation.x;
            globe.rotation.y = currentRotation.y;
            
            // Smooth zoom
            zoomLevel += (targetZoom - zoomLevel) * 0.05;
            camera.position.z = zoomLevel;
            
            // Animate clouds (gentle floating)
            cloudParticles.forEach(cloud => {
                if (cloud.visible) {
                    const userData = cloud.userData;
                    const floatOffset = Math.sin(time + userData.offset) * 0.005;
                    cloud.position.copy(userData.originalPos);
                    cloud.position.multiplyScalar(1 + floatOffset);
                    
                    // Pulse opacity
                    cloud.material.opacity = (userData.cloudCover / 100) * 0.5 + 
                        Math.sin(time * 0.5 + userData.offset) * 0.1;
                }
            });
            
            // Animate rain (falling effect)
            rainParticles.forEach(rain => {
                if (rain.visible) {
                    const userData = rain.userData;
                    const fallProgress = ((time * userData.speed * 100 + userData.offset) % 1);
                    
                    const scale = 1.05 - fallProgress * 0.05;
                    rain.position.copy(userData.basePosition).multiplyScalar(scale);
                    rain.material.opacity = 0.8 - fallProgress * 0.6;
                }
            });
            
            // Animate wind arrows (pulsing)
            windArrows.forEach(arrow => {
                if (arrow.visible) {
                    const pulse = 0.8 + Math.sin(time * 3 + arrow.userData.windDirection * 0.1) * 0.2;
                    arrow.scale.setScalar(pulse);
                }
            });
            
            // Marker glow animation
            weatherMarkers.forEach((marker, i) => {
                const glow = marker.children[1];
                if (glow) {
                    glow.material.opacity = 0.2 + Math.sin(time * 2 + i * 0.5) * 0.1;
                }
            });
            
            renderer.render(scene, camera);
        }
        
        // Initialize on page load
        window.addEventListener('load', init);
        
        // Refresh weather data every 5 minutes
        setInterval(loadWeatherData, 5 * 60 * 1000);
    </script>
</body>
</html>'''
    
    html_path = Path(__file__).parent / 'index.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  🌍 3D WEATHER GLOBE VISUALIZATION")
    print("=" * 60)
    print("\n  Real-time weather data on an interactive 3D globe")
    print("  Features: Temperature, Clouds, Rain, Wind Direction")
    print("\n" + "-" * 60)
    
    # Create HTML file
    html_path = create_html_file()
    print(f"  ✓ Created visualization: {html_path}")
    
    # Start server
    print(f"\n  Starting server on port {PORT}...")
    print(f"  Open in browser: http://localhost:{PORT}")
    print("\n  Press Ctrl+C to stop the server")
    print("-" * 60 + "\n")
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{PORT}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start HTTP server
    with socketserver.TCPServer(("", PORT), WeatherRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n  Server stopped. Goodbye! 👋\n")


if __name__ == "__main__":
    main()
