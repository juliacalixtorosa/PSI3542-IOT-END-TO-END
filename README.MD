# Sistema IoT de Gestão de Estoque de Uniformes (Edge-Cloud)

Este repositório contém o código-fonte completo para o projeto "Sistema IoT de Gestão de Estoque de Uniformes com Balança", como descrito no documento `proposta.pdf`.

### Participantes

- Júlia Calixto
- Rafael Muniz

## 1. Descrição do Projeto

A solução consiste em uma Estação IoT Inteligente com Balança que registra automaticamente as variações de peso dos uniformes para inferir a quantidade em estoque. Os dados de peso são lidos por um ESP32, processados localmente em um dispositivo Edge (Raspberry Pi) e, em seguida, enviados para a Nuvem (AWS) para análise, persistência e visualização em um dashboard.

## 2. Arquitetura e Separação de Responsabilidades

O projeto segue uma arquitetura Edge-Cloud, separando estritamente as responsabilidades de cada componente para garantir um sistema robusto e escalável.

* **1. ESP32 (Dispositivo/Coletor):**
    * **Responsabilidade:** Apenas coletar dados crus e controlar atuadores.
    * Lê o peso bruto da balança (HX711).
    * Publica o peso (em gramas) via MQTT para o Raspberry Pi.
    * **Não** toma decisões. Apenas espera por comandos.
    * Recebe comandos do Raspberry Pi (via MQTT) para acionar o feedback local (LCD, LEDs e Buzzer).

* **2. Raspberry Pi (Edge):**
    * **Responsabilidade:** Processar dados, tomar decisões locais e comunicar com a nuvem.
    * Roda o broker MQTT local (ex: Mosquitto) para se comunicar com o ESP32.
    * Ouve o tópico de peso (`balanca/esp32/peso_raw`).
    * Aplica a lógica de negócio (ex: "se o peso foi de 0g para 206g, isso foi uma `ENTRADA`").
    * Envia o comando de feedback (`ENTRADA_OK`) de volta para o ESP32 no tópico `balanca/rpi/feedback`.
    * Envia o dado processado (ex: `{"delta_unidades": 1}`) para a nuvem (AWS IoT Core).

* **3. AWS (Nuvem):**
    * **Responsabilidade:** Persistência, análise e visualização de dados.
    * Recebe o dado processado do Raspberry Pi.
    * Uma regra do IoT Core aciona uma função Lambda.
    * A Lambda atualiza a contagem de estoque no DynamoDB.
    * Os dados são enviados ao InfluxDB para serem exibidos no dashboard do Grafana.

## 3. Estrutura do Repositório

```

PSI3542-IOT-END-TO-END/
├── proposta.pdf         # Proposta detalhada do projeto
└── src/
    ├── esp32/           # Código MicroPython para o ESP32
    │   ├── main.py      # Lógica principal: Wi-Fi, MQTT, leitura da balança
    │   ├── libs/        # Bibliotecas de terceiros (MQTT, LCD, HX711)
    │   └── utils/       # Módulos de hardware (Buzzer, LED, Display, Balança)
    ├── raspberry/       # (TODO) Código Python para o Raspberry Pi (Edge)
    │   └── edge\_logic.py
    └── cloud/           # (TODO) Código e configuração da Nuvem
    ├── lambda/
    │   └── lambda\_function.py
    └── template.yaml

````

## 4. Componentes

### `src/esp32` (Dispositivo Coletor)

O código em `main.py` é responsável por orquestrar todo o hardware conectado ao ESP32.

* **Hardware:**
    * Célula de Carga + Módulo HX711 (Pinos DT: 25, SCK: 26)
    * Display LCD 16x2 (SDA: 33, SCL: 32)
    * LED Verde (Entrada, Pino 18)
    * LED Vermelho (Saída, Pino 19)
    * LED Azul (Aguardando, Pino 23)
    * Buzzer (Pino 27)

* **Setup (ESP32):**
    1.  Suba todos os arquivos e pastas de `src/esp32/` para a raiz do ESP32.
    2.  **Importante:** Edite o arquivo `src/esp32/main.py` e configure suas credenciais de Wi-Fi (`SSID`, `PASSWORD`) e o IP do seu Raspberry Pi (`MQTT_BROKER`).

### `src/raspberry` (Processamento Edge)

Esta pasta conterá o script Python que atua como o "cérebro" do sistema.

* **Serviços Necessários:**
    1.  **Broker MQTT:** (Ex: Mosquitto) Deve estar rodando localmente.
        ```bash
        sudo apt install mosquitto mosquitto-clients
        ```
    2.  **Script de Lógica (Python):** (A ser criado).

* **Lógica do Script (`edge_logic.py`):**
    1.  Conectar-se ao broker MQTT local (ex: `localhost`).
    2.  Assinar o tópico `balanca/esp32/peso_raw`.
    3.  Manter o estado (`peso_anterior`) e comparar com o `peso_atual` recebido para detectar eventos (Entrada/Saída).
    4.  Publicar `ENTRADA_OK` ou `SAIDA_OK` no tópico `balanca/rpi/feedback`.
    5.  Conectar-se ao AWS IoT Core (usando certificados) e publicar o evento processado (ex: `{"delta_unidades": -1}`).

### `src/cloud` (Nuvem AWS)

Esta pasta conterá os artefatos para a infraestrutura de nuvem.

* **Serviços:** AWS IoT Core, Lambda, DynamoDB.
* **Fluxo:**
    1.  **IoT Core:** Recebe dados do RPi.
    2.  **Regra IoT:** Aciona a função Lambda.
    3.  **Lambda:** Lê o evento, busca o estoque atual no DynamoDB, calcula o novo estoque e o salva de volta na tabela.

## 5. Proposta do Projeto

Para uma descrição detalhada da arquitetura, cronograma, materiais e fases do projeto, consulte o documento oficial:

* **[proposta.pdf](proposta.pdf)**