import network
import time
import machine
import ujson
import gc
from libs.umqtt.simple import MQTTClient
#from machine import Pin, SoftI2C
from libs.machine_i2c_lcd import I2cLcd
from time import sleep
import math
from collections import deque
from utils.display import LCDControl
from utils.buzzer import BuzzerPreciso
from utils.led import LEDControl
from utils.HX711_Estavel import HX711_Estavel
from utils.balance import Sistema206gInstantaneo

# =============================================
# CONFIGURAÇÕES DO SISTEMA
# =============================================
PIN_HX711_DT = 25
PIN_HX711_SCK = 26
PIN_BUZZER = 27

PIN_LED_VERDE = 18    # LED de ENTRADA 
PIN_LED_VERMELHO = 19 # LED de SAIDA
PIN_LED_AZUL = 23     # LED de AGUARDANDO 

# Pinos do LCD (que funcionaram para você)
PIN_LCD_SDA = 33
PIN_LCD_SCL = 32

# ATENÇÃO: Valores da SUA calibração
# Você DEVE refazer a calibração com a balança vazia.
OFFSET_TARA = 0      # Valor inicial, será calibrado no boot
FATOR_ESCALA = -56.97  # Use o seu valor

# =============================================
# CONFIGURAÇÕES DE REDE (PREENCHA AQUI)
# =============================================

SSID = "KOFUJI_2022"  #
PASSWORD = "psi3542#" #

# ===== RASPBERRY PI =====
# ATENÇÃO: Coloque aqui o IP do seu Raspberry Pi (que deve rodar um broker MQTT)
MQTT_BROKER = "192.168.1.10" # EXEMPLO: MUDE ISSO
MQTT_PORT = 1883
CLIENT_ID = "esp32-balanca-01"

# Tópicos (ESP32 -> RPi)
TOPIC_PESO_RAW = b"balanca/esp32/peso_raw"    # Envia o peso bruto (g)
TOPIC_STATUS = b"balanca/esp32/status"       # Envia "online" ou "offline"

# Tópicos (RPi -> ESP32)
TOPIC_FEEDBACK = b"balanca/rpi/feedback"     # Recebe comandos (ENTRADA_OK, SAIDA_OK, etc)


# =============================================
# FUNÇÕES DE REDE (de main_atividade7.py)
# =============================================
_sta = None
def connect_wifi():
    global _sta
    _sta = network.WLAN(network.STA_IF)
    if not _sta.isconnected():
        _sta.active(True)
        try:
            _sta.config(pm=0xA11140)  # desliga modem-sleep
        except:
            pass
        print(f"Conectando a {SSID}...")
        lcd = LCDControl(PIN_LCD_SDA, PIN_LCD_SCL)
        lcd.mostrar("Conectando...", SSID)
        _sta.connect(SSID, PASSWORD)
        while not _sta.isconnected():
            time.sleep(1)
    print("Wi-Fi conectado:", _sta.ifconfig())
    lcd.mostrar("WiFi Conectado!", _sta.ifconfig()[0])
    time.sleep(1)

# =============================================
# LÓGICA MQTT 
# =============================================
_client = None
lcd = None
buzzer = None
led_azul = None
led_verde = None
led_vermelho = None

def mqtt_callback(topic, msg):
    """Callback para COMANDOS recebidos do RPi."""
    global lcd, buzzer, led_azul, led_verde, led_vermelho

    print(f"Comando recebido: T={topic.decode()}, M={msg.decode()}")

    if topic == TOPIC_FEEDBACK:
        msg_str = msg.decode().upper()
        
        if msg_str == "ENTRADA_OK":
            buzzer.entrada_206g()
            led_verde.piscar_entrada()
            lcd.mostrar("ENTRADA OK", "")
            time.sleep(1) # Mostra no LCD
            
        elif msg_str == "SAIDA_OK":
            buzzer.saida_206g()
            led_vermelho.piscar_saida()
            lcd.mostrar("SAIDA OK", "")
            time.sleep(1) # Mostra no LCD

        elif msg_str == "ERRO":
            led_vermelho.sinal_erro()
            lcd.mostrar("ERRO", "Tente novamente")
            time.sleep(1)
            
        elif msg_str == "AGUARDANDO":
            led_azul.sinal_aguardando()

def make_client():
    c = MQTTClient(
        CLIENT_ID,
        MQTT_BROKER,
        MQTT_PORT,
        ssl=False # Sem SSL para MQTT local
    )
    c.set_last_will(TOPIC_STATUS, b"offline")
    c.set_callback(mqtt_callback)
    return c


# =============================================
# LOOP PRINCIPAL
# =============================================
def run():
    global _client, lcd, buzzer, led_azul, led_verde, led_vermelho
    
    # 1. Inicializa Hardware (agora nas globais)
    try:
        buzzer = BuzzerPreciso(PIN_BUZZER)
        led_azul = LEDControl(PIN_LED_AZUL)
        led_verde = LEDControl(PIN_LED_VERDE)
        led_vermelho = LEDControl(PIN_LED_VERMELHO)
        lcd = LCDControl(PIN_LCD_SDA, PIN_LCD_SCL)
    except Exception as e:
        print(f"Falha ao iniciar hardware basico: {e}")
        time.sleep(5)
        machine.reset()

    try:
        hx = HX711_Estavel(PIN_HX711_DT, PIN_HX711_SCK)
        hx.power_on()
        time.sleep(1)
    except Exception as e:
        print(f"Falha ao iniciar HX711: {e}")
        lcd.mostrar("Erro HX711", "Reiniciando...")
        time.sleep(5)
        machine.reset()

    # 2. Conecta Wi-Fi
    connect_wifi()

    # 3. Calibra a Balança
    balance = Sistema206gInstantaneo(PIN_HX711_DT, PIN_HX711_SCK, PIN_BUZZER, lcd)
    OFFSET_TARA = balance.calibrar_tara(hx)

    # 4. Conecta MQTT (ao RPi)
    _client = make_client()
    backoff = 5
    
    peso_atual = 0.0

    while True:
        try:
            print("Conectando ao RPi (MQTT)...")
            lcd.mostrar("Conectando RPi", MQTT_BROKER)
            _client.connect()
            _client.subscribe(TOPIC_FEEDBACK)
            _client.publish(TOPIC_STATUS, b"online")
            
            print("Conectado! Aguardando...")
            lcd.mostrar("Conectado!", "Aguardando...")
            led_azul.sinal_aguardando()

            last_pub_peso = 0
            last_ping = 0
            
            PUB_PESO_EVERY_MS = 500  # Envia o peso 2x por segundo
            PING_EVERY_S = 5

            while True:
                now_ms = time.ticks_ms()
                now_s = time.time()

                # A. Envia o peso bruto para o RPi
                if time.ticks_diff(now_ms, last_pub_peso) >= PUB_PESO_EVERY_MS:
                    peso_atual = balance.ler_peso_gramas(hx, OFFSET_TARA, FATOR_ESCALA)

                    # Envia o peso como string simples
                    _client.publish(TOPIC_PESO_RAW, b"{}".format(peso_atual))
                    
                    # Atualiza o LCD localmente
                    lcd.mostrar(f"Peso: {peso_atual:.1f}g", "Aguardando...")
                    last_pub_peso = now_ms

                # B. Verifica comandos recebidos do RPi
                _client.check_msg()

                # C. Ping periódico (mantém sessão viva)
                if now_s - last_ping >= PING_EVERY_S:
                    _client.ping()
                    last_ping = now_s

                # Loop cooperativo
                time.sleep_ms(100)

        except Exception as e:
            print(f"MQTT/Loop caiu: {e}")
            lcd.mostrar("MQTT CAIU", "Reconectando...")
            try:
                _client.disconnect()
            except:
                pass
            time.sleep(backoff)
            backoff = min(backoff * 2, 30) # Aumenta o backoff

# --- Ponto de Entrada ---
try:
    run()
except Exception as e:
    print(f"Erro fatal: {e}")
    time.sleep(5)
    machine.reset()