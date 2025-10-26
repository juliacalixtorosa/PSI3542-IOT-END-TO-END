import machine
import time

# ====/=========================================
# HX711 CONFIÁVEL
# =============================================
class HX711_Estavel:
    def __init__(self, d_out, pd_sck, channel=1):
        self.d_out_pin = machine.Pin(d_out, machine.Pin.IN)
        self.pd_sck_pin = machine.Pin(pd_sck, machine.Pin.OUT, value=0)
        self.channel = channel

    def _convert_from_twos_complement(self, value):
        if value & (1 << (24 - 1)):
            value -= 1 << 24
        return value

    def _wait(self, timeout_ms=5000):
        start_time = time.ticks_ms()
        while not self.is_ready():
            if time.ticks_diff(time.ticks_ms(), start_time) > timeout_ms:
                raise Exception("Timeout")
            time.sleep_ms(5)

    def is_ready(self):
        return self.d_out_pin.value() == 0

    def power_off(self):
        self.pd_sck_pin.value(0)
        self.pd_sck_pin.value(1)
        time.sleep_us(100)

    def power_on(self):
        self.pd_sck_pin.value(0)
        time.sleep_us(80)

    def read_stable(self):
        try:
            if not self.is_ready():
                self._wait()
            
            raw_data = 0
            for i in range(24):
                self.pd_sck_pin.value(1)
                self.pd_sck_pin.value(0)
                raw_data = raw_data << 1 | self.d_out_pin.value()
            
            for _ in range(self.channel):
                self.pd_sck_pin.value(1)
                self.pd_sck_pin.value(0)
            
            return self._convert_from_twos_complement(raw_data)
            
        except Exception as e:
            print("Erro leitura: {}".format(e))
            return 0
