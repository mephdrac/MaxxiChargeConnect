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
PROXY_STATUS_EVENTNAME = "MaxxiChargeStatusEvent"
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
CONF_TIMEOUT_RECEIVE = "CONF_TIMEOUT_RECEIVE"
DEFAULT_TIMEOUT_RECEIVE = 5  # Sekunden


#
MAXXISUN_CLOUD_URL = "maxxisun.app"
CCU = "ccu"
ERROR = "error"
ERRORS = "Errors"


OPTIONAL = "optional"
REQUIRED = "required"
NEIN = "NEIN"


# Webhook Event Names
WEBHOOK_EVENT_STATUS = "MaxxiChargeStatusEvent"
WEBHOOK_EVENT_ERROR = "MaxxiChargeErrorEvent"
WEBHOOK_EVENT_CHARGING = "MaxxiChargeChargingEvent"

# Webhook Signals
WEBHOOK_SIGNAL_UPDATE = "signal_update"
WEBHOOK_SIGNAL_STATE = "signal_state"

WEBHOOK_LAST_UPDATE = "webhook_last_update"
WEBHOOK_WATCHDOG_TASK = "webhook_watchdog_task"

# Winterbetrieb related constants
WINTER_MODE = "winter_mode"
