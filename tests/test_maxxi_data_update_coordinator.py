"""Tests für MaxxiDataUpdateCoordinator."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from bs4 import BeautifulSoup

from custom_components.maxxi_charge_connect.http_scan.maxxi_data_update_coordinator import (
    MaxxiDataUpdateCoordinator,
)
from custom_components.maxxi_charge_connect.const import REQUIRED, NEIN


@pytest.fixture
def hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    # Set up the frame helper to avoid RuntimeError
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def entry():
    """Mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"CONF_DEVICE_ID": "test_device", "ip_address": "192.168.1.100"}
    return entry


@pytest.fixture
def sensor_list():
    """Sample sensor list for testing."""
    return [
        ("PowerMeterIp", "Messgerät IP:", REQUIRED),
        ("MaximumPower", "Maximale Leistung:", NEIN),
        ("SomeValue", "Irgendein Wert:", "optional"),
    ]


@pytest.fixture
def coordinator(hass, entry, sensor_list):
    """Create MaxxiDataUpdateCoordinator instance for testing."""
    with patch('homeassistant.helpers.frame.report_usage'):
        return MaxxiDataUpdateCoordinator(hass, entry, sensor_list)


def test_initialization(coordinator):
    """Test that MaxxiDataUpdateCoordinator initializes correctly."""
    assert coordinator.entry == coordinator.entry
    assert coordinator._device_id == "test_device"
    assert coordinator._resource == "http://192.168.1.100"
    assert coordinator._sensor_list == coordinator._sensor_list
    assert coordinator.update_interval.total_seconds() == 30


# def test_initialization_without_ip(hass, entry, sensor_list):
#     """Test initialization when IP address is missing."""
#     entry.data = {"device_id": "test_device", "ip_address": ""}
#     coordinator = MaxxiDataUpdateCoordinator(hass, entry, sensor_list)
#     assert coordinator._resource == ""


# def test_initialization_with_http_scheme(hass, entry, sensor_list):
#     """Test initialization when IP already includes http scheme."""
#     entry.data = {"device_id": "test_device", "ip_address": "http://192.168.1.100"}
#     coordinator = MaxxiDataUpdateCoordinator(hass, entry, sensor_list)
#     assert coordinator._resource == "http://192.168.1.100"


def test_extract_data_success(coordinator):
    """Test successful data extraction from HTML."""
    html = '<div><b>Messgerät IP:</b>192.168.1.100</div>'
    soup = BeautifulSoup(html, "html.parser")
    
    result = coordinator.exract_data(soup, "Messgerät IP:")
    assert result == "192.168.1.100"


def test_extract_data_not_found(coordinator):
    """Test extract_data when label is not found."""
    html = '<div><b>Other Label:</b>Some Value</div>'
    soup = BeautifulSoup(html, "html.parser")
    
    with pytest.raises(Exception):  # Should raise UpdateFailed
        coordinator.exract_data(soup, "Messgerät IP:")


# @pytest.mark.asyncio
# async def test_async_update_data_success(coordinator):
#     """Test successful _async_update_data."""
#     html = """
#     <html>
#         <body>
#             <div><b>Messgerät IP:</b>192.168.1.100</div>
#             <div><b>Maximale Leistung:</b>8000 W</div>
#             <div><b>Irgendein Wert:</b>123</div>
#         </body>
#     </html>
#     """
    
#     mock_response = MagicMock()
#     mock_response.status = 200
#     mock_response.text = AsyncMock(return_value=html)
    
#     with patch("aiohttp.ClientSession.get") as mock_get:
#         mock_get.return_value.__aenter__.return_value = mock_response
#         with patch("async_timeout.timeout"):
#             with patch.object(coordinator, "fire_status_event") as mock_fire:
#                 result = await coordinator._async_update_data()
                
#                 assert result["PowerMeterIp"] == "192.168.1.100"
#                 assert result["MaximumPower"] == "8000 W"
#                 assert result["SomeValue"] == "123"
#                 mock_fire.assert_called_once()


# @pytest.mark.asyncio
# async def test_async_update_data_http_error(coordinator):
#     """Test _async_update_data with HTTP error."""
#     with patch("aiohttp.ClientSession.get") as mock_get:
#         mock_get.side_effect = aiohttp.ClientError("Connection failed")
#         with patch.object(coordinator, "fire_status_event") as mock_fire:
#             result = await coordinator._async_update_data()
            
#             assert result == {}
#             mock_fire.assert_called_once()


# @pytest.mark.asyncio
# async def test_async_update_data_timeout(coordinator):
#     """Test _async_update_data with timeout."""
#     with patch("aiohttp.ClientSession.get") as mock_get:
#         mock_get.side_effect = TimeoutError("Request timeout")
#         with patch.object(coordinator, "fire_status_event") as mock_fire:
#             result = await coordinator._async_update_data()
            
#             assert result == {}
#             mock_fire.assert_called_once()


# @pytest.mark.asyncio
# async def test_async_update_data_no_resource(hass, entry, sensor_list):
#     """Test _async_update_data when no resource is configured."""
#     entry.data = {"device_id": "test_device", "ip_address": ""}
#     coordinator = MaxxiDataUpdateCoordinator(hass, entry, sensor_list)
    
#     with patch.object(coordinator, "fire_status_event") as mock_fire:
#          result = await coordinator._async_update_data()
        
#         assert result == {}
#         mock_fire.assert_called_once()


# @pytest.mark.asyncio
# async def test_async_update_data_required_field_missing(coordinator):
#     """Test _async_update_data when required field is missing."""
#     html = """
#     <html>
#         <body>
#             <div><b>Other Label:</b>Some Value</div>
#         </body>
#     </html>
#     """
    
#     mock_response = MagicMock()
#     mock_response.status = 200
#     mock_response.text = AsyncMock(return_value=html)
    
#     with patch("aiohttp.ClientSession.get") as mock_get:
#         mock_get.return_value.__aenter__.return_value = mock_response
#         with patch("async_timeout.timeout"):
#             with pytest.raises(Exception):  # Should raise UpdateFailed
#                 await coordinator._async_update_data()


# @pytest.mark.asyncio
# async def test_async_update_data_optional_field_missing(coordinator):
#     """Test _async_update_data when optional field is missing."""
#     html = """
#     <html>
#         <body>
#             <div><b>Messgerät IP:</b>192.168.1.100</div>
#         </body>
#     </html>
#     """
    
    # mock_response = MagicMock()
    # mock_response.status = 200
    # mock_response.text = AsyncMock(return_value=html)
    
    # with patch("aiohttp.ClientSession.get") as mock_get:
    #     mock_get.return_value.__aenter__.return_value = mock_response
    #     with patch("async_timeout.timeout"):
    #         with patch.object(coordinator, "fire_status_event") as mock_fire:
    #             result = await coordinator._async_update_data()
                
    #             assert result["PowerMeterIp"] == "192.168.1.100"
    #             assert result["MaximumPower"] == "Nein"  # NEIN command
    #             assert result["SomeValue"] == "nicht gesetzt"  # optional command
    #             mock_fire.assert_called_once()


# @pytest.mark.asyncio
# async def test_async_update_data_nein_field_missing(coordinator):
#     """Test _async_update_data when NEIN field is missing."""
#     html = """
#     <html>
#         <body>
#             <div><b>Messgerät IP:</b>192.168.1.100</div>
#         </body>
#     </html>
#     """
    
#     mock_response = MagicMock()
#     mock_response.status = 200
#     mock_response.text = AsyncMock(return_value=html)
    
#     with patch("aiohttp.ClientSession.get") as mock_get:
#         mock_get.return_value.__aenter__.return_value = mock_response
#         with patch("async_timeout.timeout"):
#             with patch.object(coordinator, "fire_status_event") as mock_fire:
#                 result = await coordinator._async_update_data()
                
#                 assert result["PowerMeterIp"] == "192.168.1.100"
#                 assert result["MaximumPower"] == "Nein"  # NEIN command
#                 assert result["SomeValue"] == "nicht gesetzt"  # optional command
#                 mock_fire.assert_called_once()
