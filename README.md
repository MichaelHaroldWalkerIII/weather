# 🌍 3D Weather Globe Visualization

A stunning real-time weather visualization displayed on an interactive 3D globe with realistic animations for clouds, rain, wind direction, and temperature gradients.

![Weather Globe](https://img.shields.io/badge/Python-3.7+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

- **Real-Time Weather Data**: Fetches live weather from Open-Meteo API (free, no API key needed)
- **Interactive 3D Globe**: Fully rotatable and zoomable Earth visualization
- **Weather Layers**:
  - 🌡️ **Temperature**: Color-coded markers from cold (blue) to hot (red)
  - ☁️ **Clouds**: Animated cloud particles based on cloud cover percentage
  - 🌧️ **Rain**: Falling rain particles showing precipitation intensity
  - 💨 **Wind**: Directional arrows showing wind speed and direction
- **45+ Global Cities**: Weather data for major cities worldwide
- **City Search**: Find and focus on any covered city
- **Smooth Animations**: Realistic particle effects and transitions
- **Responsive Design**: Works on desktop and mobile devices

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. **No installation required!** The program uses only Python standard library.

2. Run the application:
   ```bash
   python weather_globe.py
   ```

3. The application will:
   - Start a local web server on port 8080
   - Automatically open your browser to `http://localhost:8080`

## 🎮 Controls

| Action | Control |
|--------|---------|
| **Rotate Globe** | Click and drag |
| **Zoom In/Out** | Scroll wheel |
| **View Location Details** | Click on a weather marker |
| **Toggle Weather Layers** | Click layer buttons in control panel |
| **Search City** | Type in the search box |

## 🌐 Weather Data

Weather data is fetched from the [Open-Meteo API](https://open-meteo.com/), which provides:

- Current temperature
- Humidity
- Cloud cover percentage
- Precipitation amount
- Wind speed and direction
- Weather conditions

Data is cached for 5 minutes to minimize API calls and refreshes automatically.

## 🎨 Visualization Details

### Temperature Colors
- **Deep Blue**: -30°C and below (extremely cold)
- **Cyan/Teal**: -10°C to 0°C (freezing)
- **Green**: 0°C to 15°C (cool)
- **Yellow**: 15°C to 25°C (mild)
- **Orange**: 25°C to 35°C (warm)
- **Red**: 35°C+ (hot)

### Wind Arrows
- **Green**: Light breeze (< 15 km/h)
- **Yellow**: Moderate wind (15-30 km/h)
- **Red**: Strong wind (> 30 km/h)

### Cloud Particles
- Size and opacity scale with cloud cover percentage
- Gentle floating animation for realism

### Rain Particles
- Number of particles indicates precipitation intensity
- Falling animation toward the globe surface

## 📁 Project Structure

```
weather_globe/
├── weather_globe.py   # Main Python application
├── index.html         # Generated web visualization (created on run)
└── README.md          # This file
```

## 🔧 Configuration

You can modify these constants in `weather_globe.py`:

```python
PORT = 8080           # Web server port
CACHE_DURATION = 300  # Weather cache duration in seconds
```

## 🌍 Covered Cities

The globe displays weather for 45+ major cities including:

**North America**: New York, Los Angeles, Chicago, Toronto, Mexico City, Miami, Vancouver, Denver

**South America**: São Paulo, Buenos Aires, Lima, Bogotá

**Europe**: London, Paris, Berlin, Madrid, Rome, Moscow, Stockholm, Athens

**Asia**: Tokyo, Beijing, Shanghai, Mumbai, Delhi, Singapore, Seoul, Bangkok, Dubai, Hong Kong

**Africa**: Cairo, Lagos, Johannesburg, Nairobi, Casablanca

**Oceania**: Sydney, Melbourne, Auckland

## 🛠️ Technical Details

- **Frontend**: Three.js for 3D WebGL rendering
- **Backend**: Python HTTP server with JSON API
- **Weather API**: Open-Meteo (free, no authentication)
- **No external Python dependencies required**

## 📝 API Endpoints

The local server provides these endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /api/weather/grid` | Weather data for all cities |
| `GET /api/weather/location?lat=X&lon=Y` | Weather for specific coordinates |
| `GET /api/cities` | List of all covered cities |

## 🐛 Troubleshooting

**Port already in use:**
```bash
# Change PORT in weather_globe.py or kill the process using port 8080
```

**Browser doesn't open automatically:**
```
Navigate manually to http://localhost:8080
```

**Weather data not loading:**
- Check your internet connection
- Ensure Open-Meteo API is accessible from your network

## 📄 License

MIT License - feel free to use and modify!

## 🙏 Credits

- Weather data: [Open-Meteo](https://open-meteo.com/)
- 3D Engine: [Three.js](https://threejs.org/)
- Fonts: [Google Fonts](https://fonts.google.com/) (Orbitron, Rajdhani)

---

**Enjoy exploring global weather on your 3D globe! 🌍✨**
