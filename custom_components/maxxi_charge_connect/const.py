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
DEVICE_INFO = {
    "manufacturer": "mephdrac",
    "model": "CCU - Maxxicharge",
}
NOTIFY_MIGRATION = "notify_migration"
