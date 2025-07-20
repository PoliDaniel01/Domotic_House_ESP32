"""
Contains all HTML, CSS, and JavaScript templates for the Microdot web server.
"""

# CSS
STYLE_CSS = """
<style>
    body { margin: 0; background: #f5f6fa; font-family: Arial, sans-serif; color: #2f3640; }
    header { background: #0984e3; padding: 20px; text-align: center; color: white; font-size: 24px; }
    .container { padding: 20px; max-width: 600px; margin: auto; }
    .card { background: white; border-radius: 8px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
    .card h3 { margin-top: 0; }
    .status-group { font-weight: bold; margin: 10px 0; }
    .actions { margin-top: 15px;}
    .btn { display: inline-block; padding: 10px 20px; text-decoration: none; color: white; border-radius: 4px; margin-right: 10px; font-size: 14px;}
    .btn-on, .on { background: #00b894; } /* Green */
    .btn-off, .off { background: #d63031; } /* Red */
    .btn-action { background: #0984e3; }
    hr { margin: 15px 0; border: none; border-top: 1px solid #eee; }
</style>
"""

# Main HTML structure. Placeholders like {{TITLE}} and {{CONTENT}} will be replaced.
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    {{STYLES}}
</head>
<body>
    <div class="container">
        <header>
            <h1>{{TITLE}}</h1>
            <p>Controllo centralizzato della casa</p>
        </header>
        <main class="grid">
            {{CONTENT}}
        </main>
    </div>
</body>
</html>
"""

# HTML template for a single device card (e.g., a light).
DEVICE_CARD_TEMPLATE = """
<div class="card">
    <h3>{{DEVICE_NAME}}</h3>
    <div class="status-group">
        <p>Stato: <span class="{{STATUS_CLASS}}">{{STATUS_TEXT}}</span></p>
    </div>
    <div class="actions">
        <a href="/update?id={{DEVICE_ID}}&state=ON" class="btn btn-on">Accendi</a>
        <a href="/update?id={{DEVICE_ID}}&state=OFF" class="btn btn-off">Spegni</a>
    </div>
</div>
"""

# Specific card for the climate control system.
CLIMATE_CARD_TEMPLATE = """
<div class="card">
    <h3>Clima</h3>
    <div class="status-group">
        <p>Temperatura Attuale: <span class="status">{{TEMP}} °C</span></p>
        <p>Temperatura Desiderata: <span class="status">{{DES_TEMP}} °C</span></p>
        <p>Modalità AUTO: <span class="status {{AUTO_MODE_CLASS}}">{{AUTO_MODE}}</span></p>
    </div>
    <div class="actions">
        <a href="/climate_control?action=toggle_auto" class="btn {{AUTO_MODE_CLASS}}">Toggle AUTO</a>
        <a href="/climate_control?action=temp_up" class="btn on">+1 °C</a>
        <a href="/climate_control?action=temp_down" class="btn off">-1 °C</a>
    </div>
</div>
"""

# Specific card for the shutters.
SHUTTERS_CARD_TEMPLATE = """
<div class="card">
    <h3>Tapparelle</h3>
    <div class="status-group">
        <p>Stato: <span>{{SHUTTER_STATE}}</span></p>
    </div>
    <div class="actions">
        <a href="/shutter_control?action=up" class="btn btn-action">SU</a>
        <a href="/shutter_control?action=down" class="btn btn-action">GIU'</a>
    </div>
</div>
"""

# Specific card for the alarm.
ALARM_CARD_TEMPLATE = """
<div class="card">
    <h3>Allarme</h3>
    <div class="status-group">
        <p>Stato: <span class="{{ALARM_CLASS}}">{{ALARM_TEXT}}</span></p>
    </div>
    <div class="actions">
        <a href="/update?id=allarme&state=ON" class="btn btn-on">Attiva</a>
        <a href="/update?id=allarme&state=OFF" class="btn btn-off">Disattiva</a>
    </div>
</div>
"""
