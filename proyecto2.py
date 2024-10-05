import smbus2
import time
import max30100

# Dirección I2C del sensor AM2320
AM2320_ADDRESS = 0x5c

# Dirección I2C de la pantalla (cambia esto según lo que detectaste)
I2C_ADDR = 0x27
LCD_WIDTH = 16

# Constantes de comandos LCD
LCD_CHR = 1  # Modo enviar datos
LCD_CMD = 0  # Modo enviar comando
LCD_LINE_1 = 0x80  # Dirección RAM para línea 1
LCD_LINE_2 = 0xC0  # Dirección RAM para línea 2
LCD_BACKLIGHT = 0x08  # Control de luz de fondo
ENABLE = 0b00000100  # Habilitar bit

# Configurar I2C bus
bus = smbus2.SMBus(1)

# Inicializa el sensor MAX30100
sensor = max30100.MAX30100()
sensor.enable_spo2()

# Funciones de la pantalla LCD
def lcd_byte(bits, mode):
    """Enviar comando o datos"""
    bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
    bits_low = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT
    bus.write_byte(I2C_ADDR, bits_high)
    lcd_toggle_enable(bits_high)
    bus.write_byte(I2C_ADDR, bits_low)
    lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
    """Habilitar bit toggle"""
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits | ENABLE))
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits & ~ENABLE))
    time.sleep(0.0005)

def lcd_init():
    """Inicializar pantalla"""
    lcd_byte(0x33, LCD_CMD)
    lcd_byte(0x32, LCD_CMD)
    lcd_byte(0x06, LCD_CMD)
    lcd_byte(0x0C, LCD_CMD)
    lcd_byte(0x28, LCD_CMD)
    lcd_byte(0x01, LCD_CMD)
    time.sleep(0.0005)

def lcd_string(message, line):
    """Escribir cadena en la pantalla"""
    message = message.ljust(LCD_WIDTH, " ")
    lcd_byte(line, LCD_CMD)
    for i in range(LCD_WIDTH):
        lcd_byte(ord(message[i]), LCD_CHR)

# Función para leer el sensor AM2320
def read_am2320():
    # Despertar el sensor
    try:
        bus.write_i2c_block_data(AM2320_ADDRESS, 0x00, [])
    except OSError:
        pass
    
    time.sleep(0.001)
    
    # Enviar comando de lectura de datos (0x03, leer 4 registros)
    bus.write_i2c_block_data(AM2320_ADDRESS, 0x03, [0x00, 0x04])
    time.sleep(0.002)
    
    # Leer 8 bytes de datos (humedad + temperatura)
    data = bus.read_i2c_block_data(AM2320_ADDRESS, 0x00, 8)
    
    humidity = (data[2] << 8 | data[3]) / 10.0
    temperature = (data[4] << 8 | data[5]) / 10.0

    return humidity, temperature

# Inicializar la pantalla LCD
lcd_init()

# Bucle principal alternando entre sensores
sensor_interval = 3  # Intervalo de cambio entre sensores en segundos
last_switch_time = time.time()  # Tiempo del último cambio
show_am2320 = True  # Alterna entre los dos sensores

while True:
    try:
        current_time = time.time()
        
        # Alternar entre los sensores cada `sensor_interval` segundos
        if current_time - last_switch_time > sensor_interval:
            show_am2320 = not show_am2320  # Cambia el sensor a mostrar
            last_switch_time = current_time
        
        if show_am2320:
            # Leer el sensor AM2320
            humidity, temperature = read_am2320()
            
            # Mostrar en consola
            print(f'Humedad: {humidity:.1f}%')
            print(f'Temperatura: {temperature:.1f}°C')

            # Mostrar en la pantalla LCD
            lcd_string(f'Temp: {temperature:.1f}C', LCD_LINE_1)
            lcd_string(f'Hum: {humidity:.1f}%', LCD_LINE_2)
        else:
            # Leer el sensor MAX30100
            sensor.read_sensor()
            hr = sensor.ir / 100.0  # Ritmo cardíaco
            spo2 = sensor.red / 100.0  # Nivel de oxígeno en sangre

            # Mostrar en consola
            print(f'Pulsos: {hr:.1f} bpm, Oxigeno: {spo2:.1f}%')

            # Mostrar en la pantalla LCD
            lcd_string(f'Pulsos: {hr:.1f}bpm', LCD_LINE_1)
            lcd_string(f'Oxigeno: {spo2:.1f}%', LCD_LINE_2)

        # Esperar antes de la siguiente actualización de datos
        time.sleep(2)

    except OSError as e:
        print(f'Error al leer el sensor: {e}')
        lcd_string("Error sensor", LCD_LINE_1)
        time.sleep(2)

    except KeyboardInterrupt:
        print("Programa interrumpido")
        sensor.shutdown()
        break
