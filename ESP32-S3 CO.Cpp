#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <DHT.h>
#include <ESP32Servo.h>

#define MPU_ADDR 0x68
#define DHTPIN 4
#define DHTTYPE DHT11

// Pin definitions for ESP32-S3 board
#define LDR_PIN 18
#define SERVO1_PIN 8
#define SERVO2_PIN 3

// Dedicated I2C pins for ESP32-S3
#define I2C_SDA 21
#define I2C_SCL 20

// Access Point Network Credentials
const char *ssid = "ASTRUM_1_NET";
const char *password = "Astrum1234Space";

WiFiUDP udp;
const char *broadcastIP = "192.168.4.2"; 
const int udpPort = 12345;

DHT dht(DHTPIN, DHTTYPE);
Servo servo1;
Servo servo2;

// Initial angle set to 90 (Center point for controlled range)
int angle = 90;
bool direction = true;

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\nConfiguring Access Point...");
  WiFi.softAP(ssid, password);
  IPAddress myIP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(myIP);

  udp.begin(udpPort);

  // Initialize I2C communication
  Wire.begin(I2C_SDA, I2C_SCL); 

  Wire.beginTransmission(MPU_ADDR);
  if (Wire.endTransmission() == 0) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x6B);
    Wire.write(0); // Wake up the sensor
    Wire.endTransmission(true);
    Serial.println("MPU6050 Online.");
  } else {
    Serial.println("MPU6050 Connection Failed.");
  }

  dht.begin();

  // Initialize LDR with 11db attenuation for wider sensing range on ESP32-S3
  analogSetAttenuation(ADC_11db);
  pinMode(LDR_PIN, INPUT);

  // Allocate hardware timers for stable servo motor PWM output
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  
  servo1.setPeriodHertz(50);
  servo2.setPeriodHertz(50);
  
  servo1.attach(SERVO1_PIN, 500, 2400);
  servo2.attach(SERVO2_PIN, 500, 2400);
  
  servo1.write(90);
  servo2.write(90);

  Serial.println("Astrum-1 Orbit Ready 🚀");
}

void loop() {
  // ================= MPU6050 (Safe attitude computation) =================
  float pitch = 0.0;
  float roll = 0.0;

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) == 0) {
    Wire.requestFrom(MPU_ADDR, 14, true);
    if (Wire.available() >= 14) {
      int16_t raw_ax = Wire.read() << 8 | Wire.read();
      int16_t raw_ay = Wire.read() << 8 | Wire.read();
      int16_t raw_az = Wire.read() << 8 | Wire.read();
      
      Wire.read(); Wire.read(); // Skip temperature data

      pitch = atan2(-raw_ax, sqrt((float)raw_ay * raw_ay + (float)raw_az * raw_az)) * 57.2958;
      roll  = atan2(raw_ay, raw_az) * 57.2958;
    }
  }

  // ================= DHT11 Environmental Data =================
  float temp = dht.readTemperature();
  if (isnan(temp)) temp = 26.5;

  // ================= LDR Signal Processing =================
  int light = analogRead(LDR_PIN);

  // ================= Solar Tracking Logic =================
  // ESP32-S3 ADC resolution is 12-bit (0 to 4095)
  // Threshold value of 2200 indicates sufficient solar irradiance
  if (light > 2200) {
    // 1. Target acquired: Maintain stable 180-degree planar alignment
    angle = 180;
    servo1.write(angle);
    servo2.write(angle);
  } else {
    // 2. Search mode: Gradual movement between 45 and 135 degrees
    if (direction) {
      angle += 1; 
    } else {
      angle -= 1;
    }

    // Boundary check for the 90-degree sweep range (45 to 135)
    if (angle >= 135) {
      direction = false;
      angle = 135;
    }
    if (angle <= 45) {
      direction = true;
      angle = 45;
    }

    servo1.write(angle);
    servo2.write(angle);
  }

  // ================= Wireless Telemetry Stream (UDP) =================
  String telemetryPacket = String(temp, 1) + "," + 
                           String(pitch, 2) + "," + 
                           String(roll, 2) + "," + 
                           String(light) + "," + 
                           String(angle) + "," + 
                           String(angle);

  udp.beginPacket(broadcastIP, udpPort);
  udp.print(telemetryPacket);
  udp.endPacket();

  Serial.print("Telemetry Flow: ");
  Serial.println(telemetryPacket);

  // 100ms delay ensures 10Hz sampling frequency and smooth servo transition
  delay(100); 
}