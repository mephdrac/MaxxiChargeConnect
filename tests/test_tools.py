"""Testet die Hilfsfunktionen in tools.py des MaxxiChargeConnect Integrations."""

from unittest.mock import MagicMock
import pytest

from custom_components.maxxi_charge_connect.tools import (
    is_pccu_ok,
    is_power_total_ok,
    is_pr_ok,
    clean_title,
    as_float,
    async_get_min_soc_entity
)

from custom_components.maxxi_charge_connect.const import (
    DOMAIN
)


@pytest.mark.asyncio
async def test_tools__pccu_kleiner_0():
    """ Testet die is_pccu_ok Funktion mit pccu < 0 """

    pccu = -100
    assert not is_pccu_ok(pccu)


@pytest.mark.asyncio
async def test_tools__pccu_groesser_0_gueltig():
    """ Testet die is_pccu_ok Funktion mit gültigem pccu Wert """

    pccu = 1100.1234
    assert is_pccu_ok(pccu)


@pytest.mark.asyncio
async def test_tools__pccu_groesser_0_ungueltig():
    """ Testet die is_pccu_ok Funktion mit ungültigem pccu Wert """
    # 2301.5  == (2300 * 1.5) # Obergrenze

    pccu = 3450.6564
    assert not is_pccu_ok(pccu)


@pytest.mark.asyncio
async def test_tools__is_power_total_ok__alle_ok():
    """ Alle Bedingungen für is_power_total_ok sind erfüllt."""

    # 0 < Batterien <= 16
    # 0 <= power_total <= (60 * 138 * anzahl_batterien)

    power_total = 2345.456345
    batterien = [
        543.342,
        356.675,
    ]
    assert is_power_total_ok(power_total, batterien)


@pytest.mark.asyncio
async def test_tools__is_power_total_ok__keine_batterien():
    """Keine Batterien im Datenpaket."""

    # 0 < Batterien <= 16
    # 0 <= power_total <= (60 * 138 * anzahl_batterien)

    power_total = 2345.456345
    batterien = {
    }
    assert not is_power_total_ok(power_total, batterien)


@pytest.mark.asyncio
async def test_tools__is_power_total_ok__keine_power_untergrenze():
    """Keine untergrenze für power_total erfüllt."""
    # 0 < Batterien <= 16
    # 0 <= power_total <= (60 * 138 * anzahl_batterien)

    power_total = -2345.456345
    batterien = {
        543.342,
    }
    assert not is_power_total_ok(power_total, batterien)


@pytest.mark.asyncio
async def test_tools__is_power_total_ok__groesser_power_obergrenze():
    """Keine obergrenze für power_total erfüllt."""
    # 0 < Batterien <= 16
    # 0 <= power_total <= (60 * 138 * anzahl_batterien)

    power_total = -9128.456345
    batterien = {
        543.342,
    }
    assert not is_power_total_ok(power_total, batterien)


@pytest.mark.asyncio
async def test_tools__is_pr_ok__alles_ok():
    """ Alle Bedingungen für is_pr_ok sind erfüllt."""
    # 43.600 <= pr <= 43.600

    pr = 9128.456345
    assert is_pr_ok(pr)


@pytest.mark.asyncio
async def test_tools__is_pr_ok__kleiner_untergrenze():
    """ Untergrenze für is_pr_ok nicht erfüllt."""
    # 43.600 <= pr <= 43.600

    pr = -99128.456345
    assert not is_pr_ok(pr)


@pytest.mark.asyncio
async def test_tools__is_pr_ok__groesser_obergrenze():
    """ Obergrenze für is_pr_ok nicht erfüllt."""
    # 43.600 <= pr <= 43.600

    pr = 99128.456345
    assert not is_pr_ok(pr)


@pytest.mark.asyncio
async def test_tools__clean_title():
    """ Testet die clean_title Funktion """
    title = "Das ist ein TestTitel"
    assert clean_title(title=title) == "das_ist_ein_testtitel"


@pytest.mark.asyncio
async def test_tools__as_float__alle_ok():
    """ Testet die as_float Funktion """
    value = "Das ist der Wert: 800.45 W"
    assert as_float(value) == 800.45


@pytest.mark.asyncio
async def test_tools__as_float__is_lower_than_0():
    """ Testet die as_float Funktion mit negativem Wert """

    value = "Das ist der Wert: -800.45 W"
    assert as_float(value) == -800.45


@pytest.mark.asyncio
async def test_tools__as_float__kein_wert_extrahierbar():
    """ Testet die as_float Funktion wenn kein Wert extrahierbar ist """

    value = "Das ist der Wert"
    assert as_float(value) is None


@pytest.mark.asyncio
async def test_tools__as_float__param_ist_none():
    """ Testet die as_float Funktion wenn der Parameter None ist """

    value = None
    assert as_float(value) is None


@pytest.mark.asyncio
async def test_tools___get_min_soc_entity1():  # pylint: disable=invalid-name
    """Testet den Fall für alles OK, d.h. die Entity wurde gefunden."""
    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"

    mock_entity = MagicMock()
    mock_entity.entity_id = "number.my_entity"

    mock_state = MagicMock()
    mock_state.state = 42

    mock_hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "entities": {
                    "minSOC": mock_entity
                }
            }
        }
    }

    mock_hass.states.get.return_value = mock_state
    min_soc_entity, cur_state = await async_get_min_soc_entity(mock_hass, mock_config_entry.entry_id)

    assert min_soc_entity is not None
    assert min_soc_entity == mock_entity

    mock_hass.states.get.assert_called_once_with(mock_entity.entity_id)
    assert cur_state.state == 42


@pytest.mark.asyncio
async def test_battery_soc___get_min_soc_entity2():  # pylint: disable=invalid-name
    """Testet den Fall die Entity is None."""
    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"

    mock_entity = MagicMock()
    mock_entity.entity_id = "number.my_entity"

    mock_state = MagicMock()
    mock_state.state = 42

    mock_hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "entities": {
                    "minSOC": None
                }
            }
        }
    }

    mock_hass.states.get.return_value = mock_state
    min_soc_entity, cur_state = await async_get_min_soc_entity(mock_hass, mock_config_entry.entry_id)

    assert min_soc_entity is None
    mock_hass.states.get.assert_not_called()
    assert cur_state is None


@pytest.mark.asyncio
async def test_battery_soc___get_min_soc_entity3():  # pylint: disable=invalid-name
    """Testet den Fall, die Entity wurde gefunden aber mit state unknown."""
    mock_hass = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "1234abcd"

    mock_entity = MagicMock()
    mock_entity.entity_id = "number.my_entity"

    mock_state = MagicMock()
    mock_state.state = 42

    mock_hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "entities": {
                    "minSOC": mock_entity
                }
            }
        }
    }

    mock_hass.states.get.return_value = None
    min_soc_entity, cur_state = await async_get_min_soc_entity(mock_hass, mock_config_entry.entry_id)

    assert min_soc_entity is not None
    assert min_soc_entity == mock_entity

    mock_hass.states.get.assert_called_once_with(mock_entity.entity_id)
    assert cur_state is None
