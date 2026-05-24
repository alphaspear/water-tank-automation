#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// =====================================================
// SENSOR PINS
// =====================================================

#define LOW_SENSOR_PIN 14
#define HIGH_SENSOR_PIN 12

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

unsigned long lastTelemetry = 0;

const unsigned long telemetryInterval = 5000;

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
// DISCHARGE PIN
// =====================================================

void dischargePin(int pin) {

  pinMode(pin, OUTPUT);

  digitalWrite(pin, LOW);

  delay(50);

  pinMode(pin, INPUT);
}

// =====================================================
// STABLE SENSOR READ
// =====================================================

bool readStableSensor(int pin) {

  int highCount = 0;

  int totalReads = 15;

  for (int i = 0; i < totalReads; i++) {

    int value = digitalRead(pin);

    if (value == HIGH) {
      highCount++;
    }

    delay(50);
  }

  return highCount >= 14;
}

// =====================================================
// TELEMETRY
// =====================================================

void publishTelemetry(
  bool lowSensorWet,
  bool highSensorWet
) {

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

  pinMode(LOW_SENSOR_PIN, INPUT);

  pinMode(HIGH_SENSOR_PIN, INPUT);

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

  // WiFi reconnect

  if (WiFi.status() != WL_CONNECTED) {

    connectWiFi();
  }

  // MQTT reconnect

  if (!client.connected()) {

    connectMQTT();
  }

  client.loop();

  // ===================================================
  // DISCHARGE
  // ===================================================

  dischargePin(LOW_SENSOR_PIN);

  dischargePin(HIGH_SENSOR_PIN);

  // ===================================================
  // READ SENSORS
  // ===================================================

  bool lowSensorWet =
    readStableSensor(LOW_SENSOR_PIN);

  bool highSensorWet =
    readStableSensor(HIGH_SENSOR_PIN);

  // ===================================================
  // DEBUG
  // ===================================================

  Serial.print("LOW SENSOR: ");

  Serial.println(
    lowSensorWet ? "WET" : "DRY"
  );

  Serial.print("HIGH SENSOR: ");

  Serial.println(
    highSensorWet ? "WET" : "DRY"
  );

  // ===================================================
  // TELEMETRY
  // ===================================================

  if (
    millis() - lastTelemetry
    >= telemetryInterval
  ) {

    publishTelemetry(
      lowSensorWet,
      highSensorWet
    );

    lastTelemetry = millis();
  }

  delay(500);
}