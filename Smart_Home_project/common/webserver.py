"""
Web Server class, contains code to run a web server with microdot 

Code in this file is responsible for:
- Running a Microdot web server for remote control via Wi-Fi.
"""

from microdot_asyncio import Microdot, Response, redirect

# Local imports
from . import html_templates

# --- Server Init ---
app = Microdot()


class WebServer:
    """
    A Microdot web server for remote control, using dynamic templating.
    """
    # We store the managers as class variables so the route functions can access them.
    state_manager = None
    device_manager = None

    def __init__(self, state_manager, device_manager):
        """
        Initializes the WebServer.

        :param state_manager: An instance of StateManager.
        :param device_manager: An instance of DeviceManager.
        """
        # Assign the managers to the class variables
        WebServer.state_manager = state_manager
        WebServer.device_manager = device_manager

    @staticmethod
    def _render_template(template, **kwargs):
        """
        Replaces placeholders in a template string with provided values.

        :param template: The template string (e.g., html_templates.MAIN_TEMPLATE).
        :param kwargs: Key-value pairs for replacement.
        :return: The rendered HTML string.
        """
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template

    @staticmethod
    def _generate_content_cards():
        """
        Generates the HTML for all device cards based on the current state.

        :return: A string of HTML containing all device cards.
        """
        cards_html = ""
        sm = WebServer.state_manager # Shortcut
        
        # --- Climate Card ---
        temp = sm.get_state('current_temperature', '--')
        desired_temp = sm.get_state('desired_temperature', 22.0)
        auto_mode = sm.get_state('auto_mode', False)
        risc_on = sm.get_state('riscaldamento', False)
        aria_on = sm.get_state('aria_condizionata', False)
        
        cards_html += WebServer._render_template(
            html_templates.CLIMATE_CARD_TEMPLATE,
            TEMP=f"{temp:.1f}" if isinstance(temp, float) else temp,
            DES_TEMP=f"{desired_temp:.1f}",
            AUTO_MODE="ON" if auto_mode else "OFF",
            AUTO_MODE_CLASS="on" if auto_mode else "off"
        )
        
        # --- Shutter and Alarm Cards ---
        # Note: We need a way to get the shutter state. Let's assume it's stored.
        shutter_state = sm.get_state('tapparella_state', 'unknown')
        cards_html += WebServer._render_template(
            html_templates.SHUTTERS_CARD_TEMPLATE, 
            SHUTTER_STATE=shutter_state.replace('_', ' ').title()
        )

        alarm_on = sm.get_state('allarme', False)
        cards_html += WebServer._render_template(
            html_templates.ALARM_CARD_TEMPLATE,
            ALARM_TEXT="ATTIVO" if alarm_on else "DISATTIVATO",
            ALARM_CLASS="on" if alarm_on else "off"
        )

        # --- Dynamic Light Cards ---
        light_devices = ["soggiorno", "cucina", "camera"]
        for device_id in light_devices:
            state = sm.get_state(device_id, False)
            cards_html += WebServer._render_template(
                html_templates.DEVICE_CARD_TEMPLATE,
                DEVICE_NAME=device_id.replace('_', ' ').title(),
                DEVICE_ID=device_id,
                STATUS_TEXT="ON" if state else "OFF",
                STATUS_CLASS="on" if state else "off"
            )
            
        return cards_html
        
    # --- Route Definitions ---

    @app.route("/")
    async def index(request):
        """Serves the main HTML page, dynamically filling it with content."""
        content = WebServer._generate_content_cards()
        html = WebServer._render_template(
            html_templates.MAIN_TEMPLATE,
            TITLE="Smart Home Dashboard",
            STYLES=html_templates.STYLE_CSS,
            CONTENT=content
        )
        return Response(body=html, headers={"Content-Type": "text/html"})

    @app.route("/update")
    async def update(request):
        """Handles requests to update a device's state (lights, alarm)."""
        device_id = request.args.get("id")
        state_str = request.args.get("state")
        
        if device_id in WebServer.state_manager.states and state_str in ["ON", "OFF"]:
            new_state = (state_str == "ON")
            WebServer.device_manager.set_device_state(device_id, new_state)
        else:
            return Response("Invalid request", status_code=400)
        return redirect("/")

    @app.route("/climate_control")
    async def climate_control(request):
        """Handles actions related to the climate control card."""
        action = request.args.get("action")
        sm = WebServer.state_manager
        dm = WebServer.device_manager

        if action == "auto_toggle":
            current_auto = sm.get_state("auto_mode", False)
            sm.set_state("auto_mode", not current_auto)
            dm.evaluate_auto_logic()
        elif action == "temp_up":
            current_temp = sm.get_state("desired_temperature", 22.0)
            sm.set_state("desired_temperature", min(current_temp + 0.5, 30.0))
            dm.evaluate_auto_logic()
        elif action == "temp_down":
            current_temp = sm.get_state("desired_temperature", 22.0)
            sm.set_state("desired_temperature", max(current_temp - 0.5, 16.0))
            dm.evaluate_auto_logic()
        
        return redirect("/")

    @app.route("/shutter_control")
    async def shutter_control(request):
        """Handles actions for the shutters."""
        action = request.args.get("action")
        if action in ["up", "down"]:
            topic = MQTT_COMMAND_TOPICS.get("tapparella")
            if topic:
                WebServer.device_manager.mqtt_client.publish(topic, action)
        
        WebServer.display_manager.draw_page()
        return redirect("/")

    async def run(self):
        """Starts the web server."""
        print("WebServer: Starting web server on port 80.")
        # The `app` object is now global, so we can run it directly.
        await app.start_server(port=80, debug=True)
