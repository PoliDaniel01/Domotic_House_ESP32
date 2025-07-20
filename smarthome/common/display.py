"""
DisplayManager class, deals with touch-display

Code in this file is responsible for:
- Driving the ST7789 display and handling XPT2046 touch input.
- Providing a user interface to control various smart home devices.
"""

#Standard library imports
import time
import uasyncio as asyncio

# Micropython-specific imports
from machine import Pin, SPI

# Third-party library imports
from st7789 import ST7789, color565
import vga1_8x8 as font
from xpt2046 import Touch


# --- Hardware Pin Configuration ---
PIN_DISP_SPI_SCK = 14
PIN_DISP_SPI_MOSI = 13
PIN_DISP_DC = 2
PIN_DISP_CS = 15
PIN_DISP_RST = 33
PIN_DISP_BL = 21

PIN_TOUCH_SPI_SCK = 25
PIN_TOUCH_SPI_MOSI = 32
PIN_TOUCH_SPI_MISO = 39
PIN_TOUCH_CS = 33


class DisplayManager:
    """
    Handles all display rendering and touch input processing.
    """
    # UI Page Definitions
    PAGE_MAIN = "main"
    PAGE_LUCI = "luci"
    PAGE_RISCALDAMENTO = "riscaldamento"
    PAGE_AUTO_SETTINGS = "auto_settings"
    PAGE_TAPPARELLE = "tapparelle"
    PAGE_ALLARME = "allarme"
    
    def __init__(self, state_manager, device_manager, standby_timeout=60):
        """
        Initializes the DisplayManager.

        :param state_manager: An instance of StateManager.
        :type state_manager: StateManager
        :param device_manager: An instance of DeviceManager to send commands.
        :type device_manager: DeviceManager
        :param standby_timeout: Seconds before display goes to standby.
        :type standby_timeout: int
        """
        self.state_manager = state_manager
        self.device_manager = device_manager
        self.standby_timeout = standby_timeout
        
        self._init_hardware()

        self.current_page = self.PAGE_MAIN
        self.last_touch_time = time.time()
        self.standby = False
        
        # Temporary state for UI feedback
        self.tapparella_feedback_state = None
        self.tapparella_feedback_time = 0

    def _init_hardware(self):
        """Initializes the display and touch controller hardware."""
        # Display SPI
        spi_disp = SPI(1, baudrate=10000000, sck=Pin(PIN_DISP_SPI_SCK), mosi=Pin(PIN_DISP_SPI_MOSI))
        
        # Touch SPI
        spi_touch = SPI(2, baudrate=1000000, sck=Pin(PIN_TOUCH_SPI_SCK), mosi=Pin(PIN_TOUCH_SPI_MOSI), miso=Pin(PIN_TOUCH_SPI_MISO))

        # Display driver
        self.display = ST7789(
            spi_disp, 240, 320,
            reset=Pin(PIN_DISP_RST, Pin.OUT),
            cs=Pin(PIN_DISP_CS, Pin.OUT),
            dc=Pin(PIN_DISP_DC, Pin.OUT),
            rotation=1
        )
        self.display.init()
        
        # Backlight
        self.backlight = Pin(PIN_DISP_BL, Pin.OUT)
        self.set_backlight(True)

        # Touch controller
        self.touch = Touch(spi_touch, cs=Pin(PIN_TOUCH_CS, Pin.OUT))
        
        print("Display: Display and Touch hardware initialized.")

    def set_backlight(self, on):
        """
        Controls the display backlight.

        :param on: True to turn the backlight on, False to turn it off.
        :type on: bool
        """
        self.backlight.value(1 if on else 0)


    def draw_page(self):
        """Clears the screen and draws the current page."""
        if self.standby:
            return
            
        self.display.fill(color565(0, 0, 0))
        
        # Draw header with temperature
        temp = self.state_manager.get_state('current_temperature')
        if temp is not None:
            self.display.text(font, f"T:{temp:.1f}C", 170, 5, color565(255, 255, 255))

        # Page-specific drawing functions
        page_draw_func = getattr(self, f"_draw_{self.current_page}_page", None)
        if callable(page_draw_func):
            page_draw_func()
        else:
            self.display.text(font, "Page not found", 20, 100, color565(255, 0, 0))

            
    def _draw_main_page(self):
        """Draws the main menu page."""
        self.display.text(font, "MENU PRINCIPALE", 40, 10, color565(255, 255, 255))
        buttons = [("LUCI", 40), ("RISCALDAMENTO", 90), ("TAPPARELLE", 140), ("ALLARME", 190)]
        for label, y in buttons:
            self.display.fill_rect(20, y, 200, 40, color565(50, 50, 50))
            self.display.rect(20, y, 200, 40, color565(255, 255, 255))
            self.display.text(font, label, 30, y + 15, color565(255, 255, 255), color565(50, 50, 50))


    def _draw_luci_page(self):
        """Draws the lights control page."""
        self.display.text(font, "CONTROLLO LUCI", 50, 10, color565(255, 255, 255))
        
        # Back button
        self.display.fill_rect(10, 270, 60, 30, color565(100, 100, 100))
        self.display.text(font, "BACK", 20, 280, color565(255, 255, 255))
        
        # Light buttons
        lights = [("Soggiorno", "soggiorno", 60), ("Cucina", "cucina", 110), ("Camera", "camera", 160)]
        for label, device_id, y in lights:
            state = self.state_manager.get_state(device_id, False)
            color = color565(0, 200, 0) if state else color565(200, 0, 0)
            self.display.fill_rect(20, y, 200, 40, color)
            self.display.rect(20, y, 200, 40, color565(255, 255, 255))
            status = "ON" if state else "OFF"
            self.display.text(font, f"{label}: {status}", 30, y + 15, color565(255, 255, 255))


    def _draw_riscaldamento_page(self):
        """Draws the heating/climate control page."""
        self.display.text(font, "CLIMA", 90, 10, color565(255, 255, 255))
        
        # Back button
        self.display.fill_rect(10, 270, 60, 30, color565(100, 100, 100))
        self.display.text(font, "BACK", 20, 280, color565(255, 255, 255))
        
        # Temperature info
        temp = self.state_manager.get_state('current_temperature')
        desired = self.state_manager.get_state('desired_temperature', 22.0)
        auto_mode = self.state_manager.get_state('auto_mode', False)
        
        if temp is not None:
            self.display.text(font, f"Temp: {temp:.1f}C", 20, 50, color565(255, 255, 255))
        self.display.text(font, f"Target: {desired:.1f}C", 20, 80, color565(255, 255, 255))
        
        # Auto mode toggle
        auto_color = color565(0, 200, 0) if auto_mode else color565(200, 0, 0)
        self.display.fill_rect(20, 110, 200, 30, auto_color)
        self.display.text(font, f"AUTO: {'ON' if auto_mode else 'OFF'}", 30, 120, color565(255, 255, 255))
        
        # Manual controls (only show if auto is off)
        if not auto_mode:
            risc_state = self.state_manager.get_state('riscaldamento', False)
            aria_state = self.state_manager.get_state('aria_condizionata', False)
            
            risc_color = color565(200, 100, 0) if risc_state else color565(100, 100, 100)
            aria_color = color565(0, 100, 200) if aria_state else color565(100, 100, 100)
            
            self.display.fill_rect(20, 150, 90, 30, risc_color)
            self.display.text(font, "RISC", 35, 160, color565(255, 255, 255))
            
            self.display.fill_rect(120, 150, 90, 30, aria_color)
            self.display.text(font, "ARIA", 135, 160, color565(255, 255, 255))
        
        # Temperature adjustment buttons
        self.display.fill_rect(20, 200, 40, 40, color565(0, 150, 0))
        self.display.text(font, "+", 35, 215, color565(255, 255, 255))
        
        self.display.fill_rect(70, 200, 40, 40, color565(150, 0, 0))
        self.display.text(font, "-", 85, 215, color565(255, 255, 255))


    def _draw_tapparelle_page(self):
        """Draws the shutters control page."""
        self.display.text(font, "TAPPARELLE", 70, 10, color565(255, 255, 255))
        
        # Back button
        self.display.fill_rect(10, 270, 60, 30, color565(100, 100, 100))
        self.display.text(font, "BACK", 20, 280, color565(255, 255, 255))
        
        # Shutter state
        shutter_state = self.state_manager.get_state('tapparella_state', 'unknown')
        self.display.text(font, f"Stato: {shutter_state}", 20, 50, color565(255, 255, 255))
        
        # Control buttons
        self.display.fill_rect(20, 100, 80, 50, color565(0, 150, 0))
        self.display.text(font, "SU", 50, 120, color565(255, 255, 255))
        
        self.display.fill_rect(120, 100, 80, 50, color565(150, 0, 0))
        self.display.text(font, "GIU", 145, 120, color565(255, 255, 255))


    def _draw_allarme_page(self):
        """Draws the alarm control page."""
        self.display.text(font, "ALLARME", 80, 10, color565(255, 255, 255))
        
        # Back button
        self.display.fill_rect(10, 270, 60, 30, color565(100, 100, 100))
        self.display.text(font, "BACK", 20, 280, color565(255, 255, 255))
        
        # Alarm state
        alarm_state = self.state_manager.get_state('allarme', False)
        state_color = color565(200, 0, 0) if alarm_state else color565(0, 200, 0)
        state_text = "ATTIVO" if alarm_state else "DISATTIVO"
        
        self.display.fill_rect(20, 80, 200, 50, state_color)
        self.display.text(font, f"Stato: {state_text}", 30, 100, color565(255, 255, 255))
        
        # Toggle button
        toggle_color = color565(0, 200, 0) if not alarm_state else color565(200, 0, 0)
        toggle_text = "ATTIVA" if not alarm_state else "DISATTIVA"
        self.display.fill_rect(20, 150, 200, 40, toggle_color)
        self.display.text(font, toggle_text, 30, 165, color565(255, 255, 255))


    def check_touch(self):
        """Checks for touch input and handles it based on the current page."""
        pos = self.touch.get_touch()
        if not pos:
            return

        self.last_touch_time = time.time()
        if self.standby:
            self.standby = False
            self.set_backlight(True)
            self.draw_page()
            return
            
        # x and y need to be switched
        x, y = pos[1], pos[0]

        # Page-specific touch handler
        page_touch_func = getattr(self, f"_handle_{self.current_page}_touch", None)
        if callable(page_touch_func):
            page_touch_func(x, y)



    def _handle_main_touch(self, x, y):
        """Handles touch events on the main menu page."""
        if 20 <= x <= 220:
            if 40 <= y <= 80:
                self.current_page = self.PAGE_LUCI
            elif 90 <= y <= 130:
                self.current_page = self.PAGE_RISCALDAMENTO
            elif 140 <= y <= 180:
                self.current_page = self.PAGE_TAPPARELLE
            elif 190 <= y <= 230:
                self.current_page = self.PAGE_ALLARME
            self.draw_page()


    def _handle_luci_touch(self, x, y):
        """Handles touch events on the lights page."""
        # Back button
        if 10 <= x <= 70 and 270 <= y <= 300:
            self.current_page = self.PAGE_MAIN
            self.draw_page()
            return
            
        # Light buttons
        lights = [("soggiorno", 60), ("cucina", 110), ("camera", 160)]
        for device_id, button_y in lights:
            if 20 <= x <= 220 and button_y <= y <= button_y + 40:
                current_state = self.state_manager.get_state(device_id, False)
                self.device_manager.set_device_state(device_id, not current_state)
                self.draw_page()
                break


    def _handle_riscaldamento_touch(self, x, y):
        """Handles touch events on the climate page."""
        # Back button
        if 10 <= x <= 70 and 270 <= y <= 300:
            self.current_page = self.PAGE_MAIN
            self.draw_page()
            return
            
        # Auto mode toggle
        if 20 <= x <= 220 and 110 <= y <= 140:
            current_auto = self.state_manager.get_state('auto_mode', False)
            self.state_manager.set_state('auto_mode', not current_auto)
            self.device_manager.evaluate_auto_logic()
            self.draw_page()
            return
            
        auto_mode = self.state_manager.get_state('auto_mode', False)
        
        # Manual controls (only if auto is off)
        if not auto_mode:
            # Heating button
            if 20 <= x <= 110 and 150 <= y <= 180:
                current_state = self.state_manager.get_state('riscaldamento', False)
                self.device_manager.set_device_state('riscaldamento', not current_state)
                self.draw_page()
                return
                
            # AC button
            if 120 <= x <= 210 and 150 <= y <= 180:
                current_state = self.state_manager.get_state('aria_condizionata', False)
                self.device_manager.set_device_state('aria_condizionata', not current_state)
                self.draw_page()
                return
        
        # Temperature adjustment buttons
        if 20 <= x <= 60 and 200 <= y <= 240:  # + button
            current_temp = self.state_manager.get_state('desired_temperature', 22.0)
            new_temp = min(current_temp + 0.5, 30.0)
            self.state_manager.set_state('desired_temperature', new_temp)
            self.device_manager.evaluate_auto_logic()
            self.draw_page()
        elif 70 <= x <= 110 and 200 <= y <= 240:  # - button
            current_temp = self.state_manager.get_state('desired_temperature', 22.0)
            new_temp = max(current_temp - 0.5, 16.0)
            self.state_manager.set_state('desired_temperature', new_temp)
            self.device_manager.evaluate_auto_logic()
            self.draw_page()


    def _handle_tapparelle_touch(self, x, y):
        """Handles touch events on the shutters page."""
        # Back button
        if 10 <= x <= 70 and 270 <= y <= 300:
            self.current_page = self.PAGE_MAIN
            self.draw_page()
            return
            
        # Up button
        if 20 <= x <= 100 and 100 <= y <= 150:
            self.device_manager.pubblish_shutter_command("up")
            self.draw_page()
        # Down button
        elif 120 <= x <= 200 and 100 <= y <= 150:
            self.device_manager.pubblish_shutter_command("down")
            self.draw_page()


    def _handle_allarme_touch(self, x, y):
        """Handles touch events on the alarm page."""
        # Back button
        if 10 <= x <= 70 and 270 <= y <= 300:
            self.current_page = self.PAGE_MAIN
            self.draw_page()
            return
            
        # Toggle button
        if 20 <= x <= 220 and 150 <= y <= 190:
            current_state = self.state_manager.get_state('allarme', False)
            self.device_manager.set_device_state('allarme', not current_state)
            self.draw_page()


    async def standby_task(self):
        """Asynchronous task to manage display standby mode."""
        while True:
            if not self.standby and (time.time() - self.last_touch_time > STANDBY_TIMEOUT):
                print("Entering standby mode.")
                self.standby = True
                self.set_backlight(False)
                self.display.fill(0)
            await asyncio.sleep(1)

    
    async def touch_loop(self):
        """Asynchronous task to continuously check for touch input."""
        while True:
            self.check_touch()
            await asyncio.sleep_ms(50)
