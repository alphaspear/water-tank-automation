#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// =====================================================
// SENSOR PINS
// =====================================================

#define LOW_SENSOR_POWER_PIN   5   // D1
#define HIGH_SENSOR_POWER_PIN  4   // D2

#define LOW_SENSOR_PIN         14  // D5
#define HIGH_SENSOR_PIN        12  // D6

// =====================================================
// WIFI
// =====================================================

const char* WIFI_SSID = "ALPSPR_2";
const char* WIFI_PASSWORD = "Abhilash@123";

// =====================================================
// MQTT
// =====================================================

const char* MQTT_SERVER = "192.168.29.10";
const int MQTT_PORT = 1883;

const char* TOPIC_TELEMETRY =
    "tank/sensor/telemetry";

const char* TOPIC_STATUS =
    "tank/sensor/status";

// =====================================================
// CLIENTS
// =====================================================

WiFiClient espClient;
PubSubClient client(espClient);

// =====================================================
// TIMERS
// =====================================================

unsigned long lastPublish = 0;
unsigned long lastMeasurement = 0;

const unsigned long publishInterval = 10000;      // 10 sec
const unsigned long measurementInterval = 5000;   // 5 sec

// =====================================================
// SENSOR STATE
// =====================================================

bool lowSensorWet = false;
bool highSensorWet = false;

// =====================================================
// WIFI
// =====================================================

void connectWiFi() {

  WiFi.mode(WIFI_STA);

  WiFi.begin(
    WIFI_SSID,
    WIFI_PASSWORD
  );

  Serial.println();
  Serial.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi Connected");

  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

// =====================================================
// MQTT
// =====================================================

void connectMQTT() {

  while (!client.connected()) {

    Serial.println("Connecting MQTT");

    String clientId = "tank_sensor_";
    clientId += String(ESP.getChipId());

    if (client.connect(clientId.c_str())) {

      Serial.println("MQTT Connected");

      client.publish(
        TOPIC_STATUS,
        "{\"status\":\"online\"}",
        true
      );

    } else {

      Serial.print("MQTT Failed rc=");
      Serial.println(client.state());

      delay(3000);
    }
  }
}

// =====================================================
// DISCHARGE
// =====================================================

void dischargePin(int pin) {

  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);

  delay(20);

  pinMode(pin, INPUT);
}

// =====================================================
// STABLE SENSOR READ
// =====================================================

bool readStableSensor(int pin) {

  int highCount = 0;
  const int totalReads = 15;

  for (int i = 0; i < totalReads; i++) {

    if (digitalRead(pin) == HIGH) {
      highCount++;
    }

    delay(10);
  }

  return highCount >= 14;
}

// =====================================================
// POWERED SENSOR READ
// =====================================================

bool readPoweredSensor(
  int powerPin,
  int sensorPin
) {

  // remove residual charge
  dischargePin(sensorPin);

  // apply power

  pinMode(powerPin, OUTPUT);
  digitalWrite(powerPin, HIGH);

  delay(100);

  bool result =
    readStableSensor(sensorPin);

  // remove power

  digitalWrite(powerPin, LOW);

  pinMode(powerPin, INPUT);

  dischargePin(sensorPin);

  return result;
}

// =====================================================
// TELEMETRY
// =====================================================

void publishTelemetry() {

  String payload = "{";

  payload += "\"low_sensor_wet\":";
  payload += lowSensorWet ? "true" : "false";

  payload += ",";

  payload += "\"high_sensor_wet\":";
  payload += highSensorWet ? "true" : "false";

  payload += ",";

  payload += "\"rssi\":";
  payload += WiFi.RSSI();

  payload += ",";

  payload += "\"uptime\":";
  payload += millis();

  payload += "}";

  client.publish(
    TOPIC_TELEMETRY,
    payload.c_str(),
    true
  );

  Serial.println(payload);
}

// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);

  pinMode(LOW_SENSOR_PIN, INPUT);
  pinMode(HIGH_SENSOR_PIN, INPUT);

  pinMode(LOW_SENSOR_POWER_PIN, INPUT);
  pinMode(HIGH_SENSOR_POWER_PIN, INPUT);

  delay(1000);

  Serial.println();
  Serial.println("Dual Tank Sensor Boot");

  connectWiFi();

  client.setServer(
    MQTT_SERVER,
    MQTT_PORT
  );
}

// =====================================================
// LOOP
// =====================================================

void loop() {

  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!client.connected()) {
    connectMQTT();
  }

  client.loop();

  // ==========================================
  // SENSOR MEASUREMENT EVERY 5 SECONDS
  // ==========================================

  if (
    millis() - lastMeasurement
    >= measurementInterval
  ) {

    lowSensorWet =
      readPoweredSensor(
        LOW_SENSOR_POWER_PIN,
        LOW_SENSOR_PIN
      );

    highSensorWet =
      readPoweredSensor(
        HIGH_SENSOR_POWER_PIN,
        HIGH_SENSOR_PIN
      );

    Serial.print("LOW SENSOR: ");
    Serial.println(
      lowSensorWet ? "WET" : "DRY"
    );

    Serial.print("HIGH SENSOR: ");
    Serial.println(
      highSensorWet ? "WET" : "DRY"
    );

    lastMeasurement = millis();
  }

  // ==========================================
  // MQTT EVERY 10 SECONDS
  // ==========================================

  if (
    millis() - lastPublish
    >= publishInterval
  ) {

    publishTelemetry();

    lastPublish = millis();
  }

  delay(50);
}