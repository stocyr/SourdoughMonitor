WIFI_AUTH = [
    ("SSID1", "PASSWORD_OF_SSID1"),
    ("SSID2", "PASSWORD_OF_SSID2"),
]
INFLUXDB_URL_WRITE = "https://<AWS_LOCATION>.aws.cloud2.influxdata.com/api/v2/write"
INFLUXDB_ORG = "ORGANIZATION_NAME"
INFLUXDB_BUCKET = "BUCKET_NAME"
INFLUXDB_API_TOKEN = "TOKEN_BASE64"
INFLUXDB_URL = f"{INFLUXDB_URL_WRITE}?org={INFLUXDB_ORG}&bucket={INFLUXDB_BUCKET}"
