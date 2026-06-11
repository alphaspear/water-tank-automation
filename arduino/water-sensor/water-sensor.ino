#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// =====================================================
// SENSOR PINS
// =====================================================

#define SENSOR_POWER_PIN 5    // D1

#define LOW_SENSOR_PIN 14     // D5
#define HIGH_SENSOR_PIN 12    // D6

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

unsigned long lastCheck = 0;
unsigned long lastTelemetry = 0;

const unsigned long sensorCheckInterval = 5000;
const unsigned long telemetryInterval = 10000;

// =====================================================
// STORED STATE
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

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
  }
}

// =====================================================
// MQTT
// =====================================================

void connectMQTT() {

  while (!client.connected()) {

    String clientId = "tank_sensor_";

    clientId += String(
      ESP.getChipId()
    );

    if (client.connect(clientId.c_str())) {

      client.publish(
        TOPIC_STATUS,
        "{\"status\":\"online\"}",
        true
      );

    } else {

      delay(3000);
    }
  }
}

// =====================================================
// SENSOR READ
// =====================================================

bool readSensor(int pin) {

  digitalWrite(
    SENSOR_POWER_PIN,
    HIGH
  );

  delay(20);

  int highCount = 0;

  for (int i = 0; i < 20; i++) {

    if (
      digitalRead(pin) == HIGH
    ) {
      highCount++;
    }

    delay(5);
  }

  digitalWrite(
    SENSOR_POWER_PIN,
    LOW
  );

  return highCount >= 18;
}

// =====================================================
// TELEMETRY
// =====================================================

void publishTelemetry() {

  String payload = "{";

  payload += "\"low_sensor_wet\":";
  payload += lowSensorWet
    ? "true"
    : "false";

  payload += ",";

  payload += "\"high_sensor_wet\":";
  payload += highSensorWet
    ? "true"
    : "false";

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

  pinMode(
    SENSOR_POWER_PIN,
    OUTPUT
  );

  digitalWrite(
    SENSOR_POWER_PIN,
    LOW
  );

  pinMode(
    LOW_SENSOR_PIN,
    INPUT
  );

  pinMode(
    HIGH_SENSOR_PIN,
    INPUT
  );

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

  if (
    WiFi.status() != WL_CONNECTED
  ) {
    connectWiFi();
  }

  if (
    !client.connected()
  ) {
    connectMQTT();
  }

  client.loop();

  // ----------------------------------
  // SENSOR CHECK
  // ----------------------------------

  if (
    millis() - lastCheck >=
    sensorCheckInterval
  ) {

    bool newLow =
      readSensor(
        LOW_SENSOR_PIN
      );

    bool newHigh =
      readSensor(
        HIGH_SENSOR_PIN
      );

    // Impossible state

    if (
      newHigh &&
      !newLow
    ) {

      Serial.println(
        "SENSOR FAULT"
      );

      newHigh = false;
    }

    lowSensorWet = newLow;
    highSensorWet = newHigh;

    Serial.print(
      "LOW: "
    );

    Serial.println(
      lowSensorWet
        ? "WET"
        : "DRY"
    );

    Serial.print(
      "HIGH: "
    );

    Serial.println(
      highSensorWet
        ? "WET"
        : "DRY"
    );

    lastCheck = millis();
  }

  // ----------------------------------
  // MQTT
  // ----------------------------------

  if (
    millis() - lastTelemetry >=
    telemetryInterval
  ) {

    publishTelemetry();

    lastTelemetry = millis();
  }

  delay(100);
}