import time
import machine

# =============================================
# CONTROLE DO LED ONBOARD
# =============================================
class LEDControl:
    def __init__(self, pin):
        self.led = machine.Pin(pin, machine.Pin.OUT)
        self.led.off()
    
    def piscar_entrada(self):
        """Pisca uma vez por 1 segundo para entrada"""
        self.led.on()
        time.sleep(0.5)
        self.led.off()
    
    def piscar_saida(self):
        """Pisca duas vezes (1 segundo cada) para saída"""
        for i in range(2):
            self.led.on()
            time.sleep(0.5)
            self.led.off()
            if i == 0:  # Intervalo apenas entre as piscadas
                time.sleep(0.5)

    def sinal_aguardando(self):
        """Sinal de AGUARDANDO (Azul) """
        self.off()
        self.led.on()
    
    def sinal_erro(self):
        """Sinal de ERRO (Vermelho piscando)"""
        self.off()
        for _ in range(3):
            self.led.on()
            time.sleep(0.1)
            self.led.off()
            time.sleep(0.1)
        self.sinal_aguardando()

    def off(self):
        self.led.off()
