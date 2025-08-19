"""Konstanten für die MaxxiChargeConnect Integration.

Attributes:
    DOMAIN (str): Der Domain-Name der Integration, wird als eindeutiger Namespace
        in Home Assistant verwendet.
    WEBHOOK_NAME (str): Der Name des registrierten Webhooks, der bei der Integration verwendet wird.
    ONLY_ONE_IP (str): Schlüssel für die Option, die angibt, ob nur eine IP-Adresse für
        den Zugriff erlaubt ist.

"""

DOMAIN = "maxxi_charge_connect"
WEBHOOK_NAME = "MaxxiCharge Webhook"
ONLY_ONE_IP = "only_accept_one_ip"
CONF_ENABLE_LOCAL_CLOUD_PROXY = "enable_local_cloud_proxy"
CONF_ENABLE_FORWARD_TO_CLOUD = "conf_enable_forward_to_cloud"
CONF_DEVICE_ID = "CONF_DEVICE_ID"
CONF_NEEDS_DEVICE_ID = "CONF_NEEDS_DEVICE_ID"

DEFAULT_ENABLE_FORWARD_TO_CLOUD = False
DEFAULT_ENABLE_LOCAL_CLOUD_PROXY = False

DEVICE_INFO = {
    "manufacturer": "mephdrac",
    "model": "CCU - Maxxicharge",
}
NOTIFY_MIGRATION = "notify_migration"

# Fehler die per Reverse-Proxy reinkommen
PROXY_ERROR_EVENTNAME = "MaxxiChargeErrorEvent"
PROXY_ERROR_CCU = "ccu"
PROXY_ERROR_IP = "ip_addr"
PROXY_ERROR_DEVICE_ID = "deviceId"
PROXY_ERROR_CODE = "error"
PROXY_ERROR_MESSAGE = "message"
PROXY_ERROR_TOTAL = "totalErrors"
PROXY_PAYLOAD = "payload"
PROXY_FORWARDED = "forwarded"
CONF_ENABLE_CLOUD_DATA = "CONF_ENABLE_CLOUD_DATA"
CONF_REFRESH_CONFIG_FROM_CLOUD = "CONF_REFRESH_CONFIG_FROM_CLOUD"


#
MAXXISUN_CLOUD_URL = "maxxisun.app"
