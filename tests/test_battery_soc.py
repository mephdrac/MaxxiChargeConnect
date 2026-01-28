"""Tests für die BatterySoc Entity der MaxxiChargeConnect Integration."""

from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import PERCENTAGE
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
import pytest
from custom_components.maxxi_charge_connect.const import (
    DOMAIN,
    CONF_WINTER_MODE,
    CONF_WINTER_MAX_CHARGE,
    CONF_WINTER_MIN_CHARGE,
)
from custom_components.maxxi_charge_connect.devices.battery_soc import (
    BatterySoc,
)


@pytest.mark.asyncio
async def test_battery_soc__init():
    """ Initialisierung der BatterySoc Entity testen."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.entry_id = "1234abcd"
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoc(dummy_config_entry)

    # Grundlegende Attribute prüfen
    assert sensor._entry == dummy_config_entry  # pylint: disable=protected-access
    assert sensor._attr_device_class == SensorDeviceClass.BATTERY  # pylint: disable=protected-access
    assert sensor._attr_state_class == SensorStateClass.MEASUREMENT  # pylint: disable=protected-access
    assert sensor._attr_native_unit_of_measurement == PERCENTAGE  # pylint: disable=protected-access
    assert sensor.icon == "mdi:battery-unknown"
    assert sensor._attr_unique_id == "1234abcd_battery_soc"  # pylint: disable=protected-access
    assert sensor._attr_native_value is None  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soc__device_info():
    """ Testet die device_info Eigenschaft der BatterySoc Entity."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.title = "Test Entry"

    sensor = BatterySoc(dummy_config_entry)

    # device_info liefert Dict mit erwarteten Keys
    device_info = sensor.device_info
    assert "identifiers" in device_info
    assert device_info["name"] == dummy_config_entry.title


@pytest.mark.asyncio
async def test_battery_soc__handle_update_alles_ok():
    """ _handle_update Methode der BatterySoc Entity testen, wenn alle Bedingungen erfüllt sind."""

    hass = MagicMock()
    hass.async_add_job = AsyncMock()
    hass.data = {
        DOMAIN: {
            CONF_WINTER_MODE: False,
        }
    }

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    soc = 37.623

    data = {
        "SOC": soc
    }

    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass  # <<< WICHTIG

    with patch(
        "custom_components.maxxi_charge_connect.devices.battery_soc.BatterySoc.async_write_ha_state",
        new_callable=MagicMock,
    ) as mock_write_ha_state:

        await sensor.handle_update(data)
        mock_write_ha_state.assert_called_once()

    assert sensor._attr_native_value == soc  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_battery_soc__icon_0_Prozent():  # pylint: disable=invalid-name
    """ Testet das Icon der BatterySoc Entity bei 0 Prozent SOC."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 0  # pylint: disable=protected-access

    assert sensor.icon == "mdi:battery-outline"


@pytest.mark.asyncio
async def test_battery_soc__icon_18_Prozent():  # pylint: disable=invalid-name
    """ Testet das Icon der BatterySoc Entity bei 18 Prozent SOC."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 18  # pylint: disable=protected-access

    assert sensor.icon == "mdi:battery-20"


@pytest.mark.asyncio
async def test_battery_soc__icon_38_Prozent():  # pylint: disable=invalid-name
    """ Testet das Icon der BatterySoc Entity bei 38 Prozent SOC."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 38  # pylint: disable=protected-access

    assert sensor.icon == "mdi:battery-40"


@pytest.mark.asyncio
async def test_battery_soc__icon_100_Prozent():  # pylint: disable=invalid-name
    """ Testet das Icon der BatterySoc Entity bei 100 Prozent SOC."""

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    sensor = BatterySoc(dummy_config_entry)
    sensor._attr_native_value = 100  # pylint: disable=protected-access

    assert sensor.icon == "mdi:battery"


@pytest.mark.asyncio
async def test_battery_soc__check_upper_limit_reached1():  # pylint: disable=invalid-name
    """ Testet die _check_upper_limit_reached Methode der BatterySoc Entity.

    Test den Fall, dass die obere Grenze erreicht ist. Also der Returnwert True ist.
    """

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    hass = MagicMock()

    hass.data = {
        DOMAIN: {
            CONF_WINTER_MAX_CHARGE: 60,
            CONF_WINTER_MIN_CHARGE: 20
        }
    }

    cur_value = float(60)
    cur_min_limit = float(60)  # aktuelles Entladelimmit der CCU

    # Testobjekt erstellen
    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass  # <<< WICHTIG

    result = await sensor._check_upper_limit_reached(cur_value=cur_value, cur_min_limit=cur_min_limit)  # pylint: disable=protected-access
    assert result is True


@pytest.mark.asyncio
async def test_battery_soc__check_upper_limit_reached2():  # pylint: disable=invalid-name
    """ Testet die _check_upper_limit_reached Methode der BatterySoc Entity.

    Test den Fall, dass die obere Grenze noch nicht erreicht ist. Also der Returnwert False ist.
    """

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    hass = MagicMock()

    hass.data = {
        DOMAIN: {
            CONF_WINTER_MAX_CHARGE: 60,
            CONF_WINTER_MIN_CHARGE: 20
        }
    }

    cur_value = float(46)
    cur_min_limit = float(60)  # aktuelles Entladelimmit der CCU

    # Testobjekt erstellen
    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass  # <<< WICHTIG

    result = await sensor._check_upper_limit_reached(cur_value=cur_value, cur_min_limit=cur_min_limit)  # pylint: disable=protected-access
    assert result is False


@pytest.mark.asyncio
async def test_battery_soc__check_upper_limit_reached3():  # pylint: disable=invalid-name
    """ Testet die _check_upper_limit_reached Methode der BatterySoc Entity.

    Test den Fall, dass die obere Grenze erreicht ist. Aber das cur_min_limit - bereits
    auf dem unteren WinterMinLimit steht.Also der Returnwert False ist.
    """

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    hass = MagicMock()

    hass.data = {
        DOMAIN: {
            CONF_WINTER_MAX_CHARGE: 60,
            CONF_WINTER_MIN_CHARGE: 20
        }
    }

    cur_value = float(61)
    cur_min_limit = float(20)  # aktuelles Entladelimmit der CCU

    # Testobjekt erstellen
    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass  # <<< WICHTIG

    result = await sensor._check_upper_limit_reached(cur_value=cur_value, cur_min_limit=cur_min_limit)  # pylint: disable=protected-access
    assert result is False


@pytest.mark.asyncio
async def test_battery_soc__check_lower_limit_reached1():  # pylint: disable=invalid-name
    """ Testet die _check_lower_limit_reached Methode der BatterySoc Entity.

    Test den Fall, dass die untere Grenze erreicht ist. Also der Returnwert True ist.
    """

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    hass = MagicMock()

    hass.data = {
        DOMAIN: {
            CONF_WINTER_MAX_CHARGE: 60,
            CONF_WINTER_MIN_CHARGE: 20
        }
    }

    cur_value = float(20)
    cur_min_limit = float(20)  # aktuelles Entladelimmit der CCU

    # Testobjekt erstellen
    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass  # <<< WICHTIG

    result = await sensor._check_lower_limit_reached(cur_value=cur_value, cur_min_limit=cur_min_limit)  # pylint: disable=protected-access
    assert result is True


@pytest.mark.asyncio
async def test_battery_soc__check_lower_limit_reached2():  # pylint: disable=invalid-name
    """ Testet die _check_upper_limit_reached Methode der BatterySoc Entity.

    Test den Fall, dass die untere Grenze noch nicht erreicht ist. Also der Returnwert False ist.
    """

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    hass = MagicMock()

    hass.data = {
        DOMAIN: {
            CONF_WINTER_MAX_CHARGE: 60,
            CONF_WINTER_MIN_CHARGE: 20
        }
    }

    cur_value = float(41)
    cur_min_limit = float(20)  # aktuelles Entladelimmit der CCU

    # Testobjekt erstellen
    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass  # <<< WICHTIG

    result = await sensor._check_lower_limit_reached(cur_value=cur_value, cur_min_limit=cur_min_limit)  # pylint: disable=protected-access
    assert result is False


@pytest.mark.asyncio
async def test_battery_soc__check_lower_limit_reached3():  # pylint: disable=invalid-name
    """ Testet die _check_upper_limit_reached Methode der BatterySoc Entity.

    Test den Fall, dass die untere Grenze erreicht ist. Aber das cur_min_limit - bereits
    auf dem oberen WinterMinLimit steht. Also der Returnwert False ist.
    """

    dummy_config_entry = MagicMock()
    dummy_config_entry.data = {}

    hass = MagicMock()

    hass.data = {
        DOMAIN: {
            CONF_WINTER_MAX_CHARGE: 60,
            CONF_WINTER_MIN_CHARGE: 20
        }
    }

    cur_value = float(61)
    cur_min_limit = float(20)  # aktuelles Entladelimmit der CCU

    # Testobjekt erstellen
    sensor = BatterySoc(dummy_config_entry)
    sensor.hass = hass  # <<< WICHTIG

    result = await sensor._check_lower_limit_reached(cur_value=cur_value, cur_min_limit=cur_min_limit)  # pylint: disable=protected-access
    assert result is False


@pytest.mark.asyncio
async def test_battery_soc___get_min_soc_entity1():  # pylint: disable=invalid-name
    """Testet den Fall für alles OK, d.h. die Entity wurde gefunden."""
    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"

    mock_coordinator = AsyncMock()
    mock_coordinator.entry = mock_config_entry

    rest_key = "minSOC"
    unique_id = f"{mock_coordinator.entry.entry_id}_{rest_key}"

    mock_entity = MagicMock()
    mock_entity.entity_id = "number.my_entity"

    mock_state = MagicMock()
    mock_state.state = 42

    mock_hass.states.get.return_value = mock_state

    mock_hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "coordinator": mock_coordinator
            }
        }
    }

    with patch("custom_components.maxxi_charge_connect.devices.battery_soc.get_entity", return_value=mock_entity) as mock_get_entity:
        sensor = BatterySoc(mock_config_entry)
        sensor.hass = mock_hass

        min_soc_entity, cur_state = await sensor._get_min_soc_entity()  # pylint: disable=protected-access

        # Prüfen, dass get_entity aufgerufen wurde
        mock_get_entity.assert_called_once_with(
            hass=mock_hass,
            plattform=DOMAIN,
            unique_id=unique_id
        )

        assert min_soc_entity is not None
        assert min_soc_entity == mock_entity

        mock_hass.states.get.assert_called_once_with(mock_entity.entity_id)
        assert cur_state.state == 42


@pytest.mark.asyncio
async def test_battery_soc___get_min_soc_entity2():  # pylint: disable=invalid-name
    """Testet den Fall die Entity wurde nicht gefunden."""
    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"

    mock_coordinator = AsyncMock()
    mock_coordinator.entry = mock_config_entry

    rest_key = "minSOC"
    unique_id = f"{mock_coordinator.entry.entry_id}_{rest_key}"

    mock_entity = MagicMock()
    mock_entity.entity_id = "number.my_entity"

    mock_hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "coordinator": mock_coordinator
            }
        }
    }

    with patch("custom_components.maxxi_charge_connect.devices.battery_soc.get_entity", return_value=None) as mock_get_entity:
        sensor = BatterySoc(mock_config_entry)
        sensor.hass = mock_hass

        min_soc_entity, cur_state = await sensor._get_min_soc_entity()  # pylint: disable=protected-access

        # Prüfen, dass get_entity aufgerufen wurde
        mock_get_entity.assert_called_once_with(
            hass=mock_hass,
            plattform=DOMAIN,
            unique_id=unique_id
        )

        assert min_soc_entity is None
        mock_hass.states.get.assert_not_called()
        assert cur_state is None


@pytest.mark.asyncio
async def test_battery_soc___get_min_soc_entity3():  # pylint: disable=invalid-name
    """Testet den Fall, die Entity wurde gefunden aber mit state unknown."""
    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"

    mock_coordinator = AsyncMock()
    mock_coordinator.entry = mock_config_entry

    rest_key = "minSOC"
    unique_id = f"{mock_coordinator.entry.entry_id}_{rest_key}"

    mock_entity = MagicMock()
    mock_entity.entity_id = "number.my_entity"

    mock_state = MagicMock()
    mock_state.state = "unknown"

    mock_hass.states.get.return_value = mock_state

    mock_hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "coordinator": mock_coordinator
            }
        }
    }

    with patch("custom_components.maxxi_charge_connect.devices.battery_soc.get_entity", return_value=mock_entity) as mock_get_entity:
        sensor = BatterySoc(mock_config_entry)
        sensor.hass = mock_hass

        min_soc_entity, cur_state = await sensor._get_min_soc_entity()  # pylint: disable=protected-access

        # Prüfen, dass get_entity aufgerufen wurde
        mock_get_entity.assert_called_once_with(
            hass=mock_hass,
            plattform=DOMAIN,
            unique_id=unique_id
        )

        assert min_soc_entity is not None
        assert min_soc_entity == mock_entity

        mock_hass.states.get.assert_called_once_with(mock_entity.entity_id)
        assert cur_state.state == "unknown"


@pytest.mark.asyncio
async def test_battery_soc___do_wintermode():  # pylint: disable=invalid-name
    """Test des Winterbetriebs beim Erreichen der oberen Grenze"""

    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"

    winter_max_charge = float(60)
    winter_min_charge = float(20)

    mock_hass.data = {
        DOMAIN: {
            CONF_WINTER_MAX_CHARGE: winter_max_charge,
            CONF_WINTER_MIN_CHARGE: winter_min_charge
        }
    }
    mock_entity = MagicMock()
    mock_entity.set_change_limitation = AsyncMock()

    mock_state = MagicMock()

    cur_value = 45  # Aktueller Messerwert von CCU
    cur_state = 60  # Aktueller Status der minSoc-Entität
    mock_state.state = cur_state

    sensor = BatterySoc(mock_config_entry)
    sensor.hass = mock_hass

    sensor._get_min_soc_entity = AsyncMock(    # pylint: disable=protected-access
        return_value=(mock_entity, mock_state)
    )

    sensor._check_lower_limit_reached = MagicMock(    # pylint: disable=protected-access
        return_value=True
    )

    sensor._check_upper_limit_reached = MagicMock(    # pylint: disable=protected-access
        return_value=False
    )

    await sensor._do_wintermode(cur_value)   # pylint: disable=protected-access

    sensor._get_min_soc_entity.assert_awaited_once()   # pylint: disable=protected-access
    sensor._check_lower_limit_reached.assert_called_once_with(cur_value, cur_state)   # pylint: disable=protected-access
    sensor._check_upper_limit_reached.assert_not_called()   # pylint: disable=protected-access
    mock_entity.set_change_limitation.assert_awaited_once_with(winter_max_charge, 5)   # pylint: disable=protected-access
