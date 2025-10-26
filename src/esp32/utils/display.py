from machine import Pin, SoftI2C
from libs.machine_i2c_lcd import I2cLcd
from time import sleep

class LCDControl:
    def __init__(self, sda, scl, addr=0x27, rows=2, cols=16):
        try:
            # Usa SoftI2C como funcionou para você
            i2c = SoftI2C(sda=Pin(sda), scl=Pin(scl), freq=100000)
            self.lcd = I2cLcd(i2c, addr, rows, cols)
            self.cols = cols
            self.lcd.clear()
            self.lcd.putstr("LCD OK")
        except Exception as e:
            print(f"Erro ao iniciar LCD: {e}")
            self.lcd = None

    def scroll_message(self, message, delay=0.3):
        # Add spaces to the beginning of the message to make it appear from the right
        message = " " * self.cols + message + " "
        # Scroll through the message
        for i in range(len(message) - self.cols + 1):
            self.lcd.move_to(0, 0)
            self.lcd.putstr(message[i:i + self.cols])
            sleep(delay)

    
    def mostrar(self, linha1, linha2=""):
        if not self.lcd:
            return
        self.lcd.clear()
        self.lcd.putstr(linha1[:self.cols])
        self.lcd.move_to(0, 1)
        self.lcd.putstr(linha2[:self.cols])
