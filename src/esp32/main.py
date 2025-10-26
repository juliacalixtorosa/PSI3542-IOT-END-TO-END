import machine
import time
import math
from collections import deque

# =============================================
# CONFIGURAÇÕES DO SISTEMA
# =============================================
PIN_HX711_DT = 25
PIN_HX711_SCK = 26
PIN_BUZZER = 27

# ===== Hardware =====
dht_sensor = None  # Placeholder se necessário
led = machine.Pin(2, machine.Pin.OUT)    # LED onboard (muitos devkits)

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

# =============================================
# SISTEMA COM DETECÇÃO INSTANTÂNEA
# =============================================
class Sistema206gInstantaneo:
    def __init__(self):
        self.hx = HX711_Estavel(PIN_HX711_DT, PIN_HX711_SCK)
        self.buzzer = BuzzerPreciso(PIN_BUZZER)
        self.led = LEDControl(2)  # LED onboard
        
        # Valores da sua calibração
        self.offset_tara = 0
        self.fator_escala = -56.97
        
        # Controle de estado
        self.estado_atual = "VAZIO"
        self.ultimo_peso = 0
        self.estoque = 0  # Contador de estoque
        
    def calibrar_tara_rigorosa(self):
        """Calibração rigorosa com verificação"""
        print("🔧 CALIBRAÇÃO RIGOROSA")
        print("   Deixe a plataforma PERFEITAMENTE VAZIA")
        input("   Pressione ENTER quando estiver pronto...")
        
        leituras = []
        print("   Coletando: ", end="")
        for i in range(15):
            try:
                raw = self.hx.read_stable()
                leituras.append(raw)
                time.sleep_ms(100)
                if i % 5 == 0:
                    print(".", end="")
            except:
                print("E", end="")
        print()
        
        # Mediana para evitar outliers
        leituras.sort()
        self.offset_tara = leituras[len(leituras)//2]
        
        # Verificação com múltiplas leituras
        pesos_verificacao = []
        for i in range(5):
            peso = self.ler_peso_instantaneo()
            pesos_verificacao.append(peso)
            time.sleep_ms(100)
        
        peso_medio = sum(pesos_verificacao) / len(pesos_verificacao)
        print("   ✅ Tara calibrada: {:.1f}g".format(peso_medio))
        
        if abs(peso_medio) > 10:
            print("   ⚠️  Aviso: Peso residual de {:.1f}g".format(peso_medio))
            return False
        return True
    
    def inicializar_sistema(self):
        print("=" * 60)
        print("🎯 SISTEMA 206g - DETECÇÃO INSTANTÂNEA")
        print("=" * 60)
        
        self.hx.power_on()
        time.sleep(1)
        
        # Calibração obrigatória
        if not self.calibrar_tara_rigorosa():
            print("❌ Calibração falhou. Verifique a plataforma.")
            return False
        
        peso_inicial = self.ler_peso_instantaneo()
        print("📊 Peso inicial: {:.1f}g".format(peso_inicial))
        
        if abs(peso_inicial) > 15:
            print("❌ Calibração inadequada.")
            return False
        
        self.buzzer.calibracao_ok()
        print("✅ Sistema calibrado e pronto")
        return True
    
    def ler_peso_instantaneo(self):
        """Lê o peso SEM suavização para detecção instantânea"""
        try:
            raw = self.hx.read_stable()
            return (raw - self.offset_tara) / self.fator_escala
        except:
            return self.ultimo_peso
    
    def detectar_mudanca_instantanea(self, peso_atual):
        """Detecta mudanças de estado instantaneamente"""
        # Limiares conservadores
        ENTRADA_206G = 150  # Acima de 150g = 206g
        SAIDA_206G = 50     # Abaixo de 50g = vazio
        
        mudanca = None
        
        if self.estado_atual == "VAZIO" and peso_atual > ENTRADA_206G:
            mudanca = "ENTRADA"
            self.estado_atual = "206G"
            self.estoque += 1  # Incrementa estoque
            
        elif self.estado_atual == "206G" and peso_atual < SAIDA_206G:
            mudanca = "SAIDA"
            self.estado_atual = "VAZIO"
            if self.estoque > 0:  # Evita estoque negativo
                self.estoque -= 1  # Decrementa estoque
        
        self.ultimo_peso = peso_atual
        return mudanca
    
    def loop_detecção_instantanea(self):
        print("\n" + "=" * 60)
        print("🔄 DETECÇÃO INSTANTÂNEA ATIVA")
        print("=" * 60)
        print("Peso  | Estado | Estoque | Ação")
        print("-" * 35)
        
        contador_acoes = 0
        
        try:
            while True:
                peso = self.ler_peso_instantaneo()
                mudanca = self.detectar_mudanca_instantanea(peso)
                
                if mudanca == "ENTRADA":
                    self.buzzer.entrada_206g()  # 1 beep de 0.1s
                    self.led.piscar_entrada()   # Piscar LED para entrada
                    print("{:5.1f}g | 206g   | {:7d} | ✅ ENTRADA".format(peso, self.estoque))
                    contador_acoes += 1
                    
                elif mudanca == "SAIDA":
                    self.buzzer.saida_206g()    # 2 beeps de 0.1s
                    self.led.piscar_saida()     # Piscar LED para saída
                    print("{:5.1f}g | Vazio  | {:7d} | 🚪 SAÍDA".format(peso, self.estoque))
                    contador_acoes += 1
                
                # Log mínimo do estado atual
                if time.ticks_ms() % 2000 < 100:  # A cada 2 segundos
                    if self.estado_atual == "206G":
                        print("{:5.1f}g | 206g   | {:7d} |".format(peso, self.estoque))
                    else:
                        print("{:5.1f}g | Vazio  | {:7d} |".format(peso, self.estoque))
                
                time.sleep_ms(100)  # Leitura rápida
                
        except KeyboardInterrupt:
            print("\n⏹️  Sistema interrompido")
            print("📊 Total de ações detectadas: {}".format(contador_acoes))
            print("📦 Estoque final: {}".format(self.estoque))
        except Exception as e:
            print("\n❌ Erro: {}".format(e))

# =============================================
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

# =============================================
# PROGRAMA PRINCIPAL
# =============================================
if __name__ == "__main__":
    print("🎯 SISTEMA 206g - DETECÇÃO INSTANTÂNEA")
    print("\nOpções:")
    print("1 - Iniciar Sistema com Calibração")
    print("2 - Testar Buzzer (Verificar Sons)")
    print("3 - Testar LED Onboard")
    
    opcao = input("\nDigite 1-3: ").strip()
    
    sistema = None
    
    try:
        if opcao == "1":
            sistema = Sistema206gInstantaneo()
            if sistema.inicializar_sistema():
                sistema.loop_detecção_instantanea()
            else:
                print("❌ Falha na inicialização")
                
        elif opcao == "2":
            buzzer = BuzzerPreciso(PIN_BUZZER)
            print("\n🔊 TESTE DE SONS - TIMING PRECISO")
            print("=" * 35)
            
            print("1. ENTRADA: 1 beep de 0.1s")
            buzzer.entrada_206g()
            time.sleep(1)
            
            print("2. SAÍDA: 2 beeps de 0.1s com 0.1s entre")
            buzzer.saida_206g()
            time.sleep(1)
            
            print("3. CALIBRAÇÃO: 3 beeps rápidos")
            buzzer.calibracao_ok()
            time.sleep(1)
            
            print("✅ Todos os sons executados corretamente!")
            
        elif opcao == "3":
            led_test = LEDControl(2)
            print("\n💡 TESTE DO LED ONBOARD")
            print("=" * 25)
            
            print("1. Piscar Entrada (1 segundo)")
            led_test.piscar_entrada()
            time.sleep(1)
            
            print("2. Piscar Saída (2 piscadas de 1 segundo)")
            led_test.piscar_saida()
            time.sleep(1)
            
            print("✅ Teste do LED completo!")
            
        else:
            print("❌ Opção inválida")
            
    except KeyboardInterrupt:
        print("\n🛑 Sistema interrompido pelo usuário")
    except Exception as e:
        print("\n💥 Erro: {}".format(e))
    finally:
        if sistema:
            sistema.hx.power_off()
            sistema.buzzer.silencio()
        print("\n👋 Execução finalizada")