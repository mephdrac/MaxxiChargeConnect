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
CONF_REAL_CLOUD_URL = "real_cloud_url"
CONF_ENABLE_FORWARD_TO_CLOUD = "conf_enable_forward_to_cloud"
DEFAULT_ENABLE_FORWARD_TO_CLOUD = False
DEFAULT_REAL_CLOUD_URL = "http://real.maxxisun.app:3001/text"

DEVICE_INFO = {
    "manufacturer": "mephdrac",
    "model": "CCU - Maxxicharge",
}
NOTIFY_MIGRATION = "notify_migration"
