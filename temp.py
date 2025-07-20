# State Persistence (StateManager)
class StateManager:
    # Initialize with state file path
    def __init__(self, state_file):
        self._state_file = state_file
        self.states = self._load_states()

    # Load device states from JSON file, return defaults if file is missing
    def _load_states(self):
        try:
            with open(self._state_file, "r") as f:
                return json.load(f)
        except:
            return {"soggiorno": False, "cucina": False, "camera": False}

    # Set device state and save to file if required
    def set_state(self, key, value, save=True):
        self.states[key] = value
        if save:
            with open(self._state_file, "w") as f:
                json.dump(self.states, f)

# Display and Touch Initialization (DisplayManager)
class DisplayManager:
    # Initialize display and touch with SPI configuration
    def __init__(self, state_manager, device_manager, standby_timeout=60):
        spi = SPI(2, baudrate=40000000, sck=Pin(18), mosi=Pin(19))
        self.display = st7789.ST7789(spi, 240, 320, dc=Pin(21), backlight=Pin(21))
        self.display.init()
        self.touch = xpt2046.XPT2046(spi, cs=Pin(25))
        self.display.backlight_on()

# UI Navigation (DisplayManager)
class DisplayManager:
    # Draw device states on the screen
    def draw_page(self):
        self.display.fill(st7789.WHITE)
        for i, device in enumerate(["soggiorno", "cucina", "camera"]):
            state = self.state_manager.get_state(device, False)
            self.display.text(f"{device}: {'ON' if state else 'OFF'}", 10, 10 + i*20, st7789.BLACK)

    # Handle touch input to toggle device states
    async def touch_loop(self):
        while True:
            if self.touch.is_touched():
                x, y = self.touch.get_position()
                if 10 <= x <= 230 and 10 <= y < 70:
                    device = ["soggiorno", "cucina", "camera"][y // 20]
                    self.device_manager.set_device_state(device, not self.state_manager.get_state(device, False))
            await asyncio.sleep(0.1)
