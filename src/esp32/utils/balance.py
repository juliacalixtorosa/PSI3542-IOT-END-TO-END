import time
from utils.HX711_Estavel import HX711_Estavel
from utils.buzzer import BuzzerPreciso
from utils.led import LEDControl
from utils.display import LCDControl

# =============================================
# SISTEMA COM DETECÇÃO INSTANTÂNEA
# =============================================
class Sistema206gInstantaneo:
    def __init__(self, PIN_HX711_DT, PIN_HX711_SCK, PIN_BUZZER, lcd):
        self.hx = HX711_Estavel(PIN_HX711_DT, PIN_HX711_SCK)
        self.buzzer = BuzzerPreciso(PIN_BUZZER)
        self.led = LEDControl(2)  # LED onboard
        self.lcd = lcd
        
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

    def calibrar_tara(self, hx):
        """Calibra a tara (offset) da balança."""
        print("Calibrando Tara... Deixe a balanca vazia.")
        self.lcd.mostrar("Calibrando Tara", "Nao toque!")
        
        leituras = []
        for _ in range(15):
            leituras.append(hx.read_stable())
            time.sleep_ms(100)
        
        leituras.sort()
        offset = leituras[len(leituras)//2] # Mediana
        
        print(f"Tara definida: {offset}")
        self.lcd.mostrar("Calibrado!", f"Offset: {offset}")
        time.sleep(1)
        return offset

    def ler_peso_gramas(self, hx, offset_tara, fator_escala):
        # Lê o peso e converte para gramas
        try:
            raw = hx.read_stable()
            peso = (raw - offset_tara) / fator_escala
            return peso
        except Exception as e:
            print(f"Erro ao ler peso: {e}")
            return 0.0 # Retorna 0 se falhar