#include <Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

#define DHTPIN 5
#define DHTTYPE DHT11

const int lightPin = 10;
const int curtainServoPin = 6;
const int doorServoPin = 9;
const int buzzerPin = 11;

Servo curtainServo;
Servo doorServo;
LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(DHTPIN, DHTTYPE);

//переменные состояния
bool lightIsOn = false;        // false = выключен, true = включен (полностью)
bool curtainsOpen = false;     // false = закрыты (0°), true = открыты (150°)
bool doorOpen = false;         // false = закрыта (0°), true = открыта (90°)
bool alarmActive = false;

void setup() {
  pinMode(lightPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  curtainServo.attach(curtainServoPin);
  doorServo.attach(doorServoPin);

  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("Smart Home");
  lcd.setCursor(0,1);
  lcd.print("Starting...");
  
  dht.begin();

  curtainServo.write(0);
  doorServo.write(0);
  digitalWrite(lightPin, LOW);

  Serial.begin(9600);
  delay(1000);

  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("System Ready");
  delay(1000);
  lcd.clear();
}

unsigned long lastDisplay = 0;

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    handleCommand(command);
  }

  // Мигаем и пищим при тревоге
  if (alarmActive) {
    digitalWrite(lightPin, HIGH);
    tone(buzzerPin, 1000);
    delay(200);
    digitalWrite(lightPin, LOW);
    noTone(buzzerPin);
    delay(200);
  }

  // Обновление LCD каждые 2 сек
  if (millis() - lastDisplay > 2000) {
    showProperties();
    lastDisplay = millis();
  }
}

void handleCommand(String command) {
  if (command == "sleep") {
    turnLightOff();
  } 
  else if (command == "wake") {
    wakeUp();
  } 
  else if (command == "light_on") {
    turnLightOn();
  } 
  // else if (command == "light_off") {      
  //   turnLightOff();
  // }
  else if (command == "curtains_open") {
    openCurtains();
  } 
  else if (command == "curtains_close") {
    closeCurtains();
  } 
  else if (command == "door_open") {
    openDoor();
  } 
  else if (command == "door_close") {
    closeDoor();
  } 
  else if (command == "alarm_on") {
    activateAlarm();
  } 
  else if (command == "alarm_off") {
    deactivateAlarm();
  }
}

//Проверка состояния
void turnLightOn() {
  if (lightIsOn) {
    Serial.println("Свет уже включён");
    return;
  }
  digitalWrite(lightPin, HIGH);
  lightIsOn = true;
  Serial.println("Свет включён");
}

void turnLightOff() {
  if (!lightIsOn) {
    Serial.println("Свет уже выключен");
    return;
  }
  digitalWrite(lightPin, LOW);
  lightIsOn = false;
  Serial.println("Свет выключен");
}

void wakeUp() {
  // "wake" делаем полувключение (128), считаем это тоже "включённым"
  if (lightIsOn && digitalRead(lightPin) == HIGH) {
    Serial.println("Свет уже яркий");
    return;
  }
  analogWrite(lightPin, 128);  // или digitalWrite(HIGH) если не нужен ШИМ
  lightIsOn = true;
  Serial.println("Режим пробуждения (половина яркости)");
}

void openCurtains() {
  if (curtainsOpen) {
    Serial.println("Шторы уже открыты");
    return;
  }
  for (int pos = curtainServo.read(); pos <= 150; pos += 5) {
    curtainServo.write(pos);
    delay(40);
  }
  curtainsOpen = true;
  Serial.println("Шторы открыты");
}

void closeCurtains() {
    if (!curtainsOpen) {
    Serial.println("Шторы уже закрыты");
    return;
  }
  for (int pos = curtainServo.read(); pos >= 0; pos -= 5) {
    curtainServo.write(pos);
    delay(40);
  }
  curtainsOpen = false;
  Serial.println("Шторы закрыты");
}

void openDoor() {
  if (doorOpen) {
    Serial.println("Дверь уже открыта");
    return;
  }
  for (int pos = doorServo.read(); pos <= 90; pos += 5) {
    doorServo.write(pos);
    delay(40);
  }
  doorOpen = true;
  Serial.println("Дверь открыта");
}

void closeDoor() {
  if (!doorOpen) {
    Serial.println("Дверь уже закрыта");
    return;
  }
  for (int pos = doorServo.read(); pos >= 0; pos -= 5) {
    doorServo.write(pos);
    delay(40);
  }
  doorOpen = false;
  Serial.println("Дверь закрыта");
}

void activateAlarm() {
  if (alarmActive) {
    Serial.println("Тревога уже активна");
    return;
  }
  alarmActive = true;
  Serial.println("ALARM!");
}

void deactivateAlarm() {
  if (!alarmActive) {
    Serial.println("Alarm is already on");
    return;
  }
  alarmActive = false;
  noTone(buzzerPin);
  digitalWrite(lightPin, LOW);
  Serial.println("Тревога выключена");
}

void showProperties() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  lcd.clear();
  lcd.setCursor(0,0);
  // if (isnan(h) || isnan(t)) {
  //   lcd.print("DHT Error");
  // } 
  // else {
    lcd.print("T:");
    lcd.print(t, 1);
    lcd.print((char)223);
    lcd.print("C H:");
    lcd.print(h, 0);
    lcd.print("%");
  // }

  lcd.setCursor(0,1);
  lcd.print("L:");
  lcd.print(lightIsOn ? "ON " : "OFF");

  lcd.print(" C:");
  lcd.print(curtainsOpen ? "OP" : "CL");

  lcd.print(" D:");
  lcd.print(doorOpen ? "OP" : "CL");
}