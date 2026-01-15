import cv2
import time
import threading
import serial
import speech_recognition as sr
from cvzone.HandTrackingModule import HandDetector

# Конфигурация
SERIAL_PORT = 'COM8'
BAUDRATE = 9600
COOLDOWN_SECONDS = 1.5

# Состояния
state = {
    "Light": "OFF",
    "Window": "CLOSED",
    "Door": "CLOSED",
    "Alarm": "OFF",
    "Properties": "VISIBLE"
}

# Режимы (по умолчанию выключены)
gesture_enabled = False
voice_enabled = False

# Комманда соответствия (фразы -> команды для Arduino)
command_map = {
    "light off": "sleep",
    "wake up": "wake",
    "turn the light on": "light_on",
    "open window": "curtains_open",
    "close window": "curtains_close",
    "open main door": "door_open",
    "close main door": "door_close",
    "show properties": "show_properties",
    "close properties": "close_properties",
    "activate alarm": "alarm_on",
    "alarm off": "alarm_off"
}

# Инициализация Serial (только для записи). Если не доступен — работа в режиме симуляции.
arduino = serial.Serial('COM8',9600, timeout=1)
time.sleep(2)
# --Автоопределение сом-порта--

# import serial.tools.list_ports
#
# def find_arduino():
#     ports = serial.tools.list_ports.comports()
#     for port in ports:
#         try:
#             ar = serial.Serial(port.device, 9600, timeout=1)
#             time.sleep(2)
#             ar.flushInput()
#             print(f"Подключено к Arduino на порту: {port.device}")
#             return ar
#         except Exception:
#             pass
#     print("Arduino не найден. Работа в симуляции.")
#     return None
#
# arduino = find_arduino()

# Отправка команды (односторонняя)
def send_command(cmd: str):
    global state
    # Отправляем в Arduino, если доступно
    try:
        if arduino:
            # Обязательно добавляем \n и используем .write
            arduino.write((cmd + '\n').encode())
    except Exception as e:
        print(f"Error writing to serial: {e}")

    # Обновляем локальное состояние
    if cmd == "sleep":
        state["Light"] = "OFF"
    elif cmd in ("light_on", "wake"):
        state["Light"] = "ON"
    elif cmd == "curtains_open":
        state["Window"] = "OPEN"
    elif cmd == "curtains_close":
        state["Window"] = "CLOSED"
    elif cmd == "door_open":
        state["Door"] = "OPEN"
    elif cmd == "door_close":
        state["Door"] = "CLOSED"
    elif cmd == "alarm_on":
        state["Alarm"] = "ON"
    elif cmd == "alarm_off":
        state["Alarm"] = "OFF"

    print(f"Command sent: {cmd}")

# Голосовой поток — работает постоянно, но слушает только когда voice_event установлен
voice_event = threading.Event()
recognizer = sr.Recognizer()
mic = None
try:
    mic = sr.Microphone()
except Exception as e:
    print(f"Microphone init error: {e}. Voice recognition will not work.")


def voice_thread_func():
    global voice_enabled
    while True:
        # Ждём включения распознавания речи
        voice_event.wait()
        if not mic:
            time.sleep(0.5)
            continue
        with mic as source:
            try:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("Listening for voice command...")
                audio = recognizer.listen(source, phrase_time_limit=4)
                try:
                    speech_text = recognizer.recognize_google(audio).lower()
                    print(f"Recognized: {speech_text}")
                    # Ищем подходящую команду
                    matched = False
                    for phrase, cmd in command_map.items():
                        if phrase in speech_text:
                            send_command(cmd)
                            matched = True
                            break
                    if not matched:
                        print("No matching voice command.")
                except sr.UnknownValueError:
                    print("Could not understand audio.")
                except sr.RequestError as e:
                    print(f"Speech recognition error: {e}")
            except Exception as e:
                print(f"Voice recognition exception: {e}")
        # Небольшая пауза перед следующим прослушиванием
        time.sleep(0.2)

# Запускаем голосовой поток демоном
vt = threading.Thread(target=voice_thread_func, daemon=True)
vt.start()

# Видео и жесты
cap = cv2.VideoCapture(0)
detector = HandDetector(maxHands=1, detectionCon=0.7)

last_gesture = None
last_gesture_time = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        # Отображаем затемнённую панель для текста
        cv2.rectangle(frame, (10, 10), (520, 200), (0, 0, 0), -1)

        # Если включены жесты — распознаём, иначе просто пишем 'No Hand Detected' или режим
        gesture_text = "No Hand Detected"
        if gesture_enabled:
            hands, frame = detector.findHands(frame)
            if hands:
                hand = hands[0]
                fingers = detector.fingersUp(hand)
                totalFingers = sum(fingers)
                gesture = None
                if totalFingers == 0:
                    gesture = "sleep"
                    gesture_text = "Light Off"
                elif totalFingers == 1:
                    gesture = "light_on"
                    gesture_text = "Light On"
                elif totalFingers == 2:
                    gesture = "curtains_open"
                    gesture_text = "Window Open"
                elif totalFingers == 3:
                    gesture = "curtains_close"
                    gesture_text = "Window Close"
                elif totalFingers == 4:
                    gesture = "door_open"
                    gesture_text = "Door Open"
                elif totalFingers == 5:
                    gesture = "door_close"
                    gesture_text = "Door Close"

                # Проверяем cooldown
                if gesture is not None:
                    now = time.time()
                    if gesture != last_gesture or (now - last_gesture_time) > COOLDOWN_SECONDS:
                        send_command(gesture)
                        last_gesture = gesture
                        last_gesture_time = now
            else:
                gesture_text = "No Hand Detected"
        else:
            gesture_text = "Gesture Mode OFF"

        # Отображение параметров (всегда)
        y = 40
        cv2.putText(frame, f"Gesture Mode: {'ON' if gesture_enabled else 'OFF'}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        y += 25
        cv2.putText(frame, f"Voice Mode: {'ON' if voice_enabled else 'OFF'}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        y += 25
        for key, val in state.items():
            cv2.putText(frame, f"{key}: {val}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            y += 25

        cv2.putText(frame, f"Gesture: {gesture_text}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        cv2.imshow("Smart Home Control (G=toggle gestures, V=toggle voice, Q=quit)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('g'):
            gesture_enabled = not gesture_enabled
            print(f"Gesture mode set to {gesture_enabled}")
        elif key == ord('v'):
            voice_enabled = not voice_enabled
            print(f"Voice mode set to {voice_enabled}")
            if voice_enabled:
                voice_event.set()
            else:
                voice_event.clear()
        elif key == ord('a'):
            send_command("alarm_on")
            print("Alarm turned ON (button)")
        elif key == ord('f'):
            send_command("alarm_off")
            print("Alarm turned OFF (button)")

finally:
    cap.release()
    cv2.destroyAllWindows()
    # Не закрываем Serial целиком; если нужно, можно освободить
    if arduino:
        try:
            arduino.close()
        except Exception:
            pass



