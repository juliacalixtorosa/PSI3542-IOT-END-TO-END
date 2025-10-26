import machine
import time

# =============================================
# BUZZER COM TIMING PRECISO (0.1s)
# =============================================
class BuzzerPreciso:
    def __init__(self, pin):
        self.buzzer = machine.Pin(pin, machine.Pin.OUT)
        self.silencio()
    
    def beep(self, duration=0.005):  # Beep de 0.1s exatos
        self.buzzer.value(1)
        time.sleep(duration)
        self.buzzer.value(0)
        time.sleep(0.05)
    
    def entrada_206g(self):
        """UM beep de 0.1s para entrada"""
        self.beep(0.005)
    
    def saida_206g(self):
        """DOIS beeps de 0.1s com 0.1s entre eles para saída"""
        self.beep(0.005)
        time.sleep(0.1)
        self.beep(0.005)
    
    def calibracao_ok(self):
        """Três beeps rápidos para calibração"""
        for i in range(3):
            self.beep(0.005)
            time.sleep(0.1)
    
    def silencio(self):
        self.buzzer.value(0)