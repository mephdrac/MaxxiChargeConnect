from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from custom_components.maxxi_charge_connect.const import DOMAIN
from custom_components.maxxi_charge_connect.tools import is_pccu_ok, is_power_total_ok, is_pr_ok, clean_title, as_float


@pytest.mark.asyncio
async def test_tools__pccu_kleiner_0(caplog):

    pccu = -100
    assert not is_pccu_ok(pccu)


@pytest.mark.asyncio
async def test_tools__pccu_groesser_0_gueltig(caplog):

    pccu = 1100.1234
    assert is_pccu_ok(pccu)


@pytest.mark.asyncio
async def test_tools__pccu_groesser_0_ungueltig(caplog):
    # 2301.5  == (2300 * 1.5) # Obergrenze

    pccu = 2601.6564
    assert not is_pccu_ok(pccu)


@pytest.mark.asyncio
async def test_tools__is_power_total_ok__alle_ok(caplog):
    # 0 < Batterien <= 16
    # 0 <= power_total <= (60 * 138 * anzahl_batterien)

    power_total = 2345.456345
    batterien = {
        543.342,
        356.675,
    }
    assert is_power_total_ok(power_total, batterien)

@pytest.mark.asyncio
async def test_tools__is_power_total_ok__keine_batterien(caplog):
    # 0 < Batterien <= 16
    # 0 <= power_total <= (60 * 138 * anzahl_batterien)

    power_total = 2345.456345
    batterien = {
        
    }
    assert not is_power_total_ok(power_total, batterien)

@pytest.mark.asyncio
async def test_tools__is_power_total_ok__keine_power_untergrenze(caplog):
    # 0 < Batterien <= 16
    # 0 <= power_total <= (60 * 138 * anzahl_batterien)

    power_total = -2345.456345
    batterien = {
        543.342,
    }
    assert not is_power_total_ok(power_total, batterien)

@pytest.mark.asyncio
async def test_tools__is_power_total_ok__groesser_power_obergrenze(caplog):
    # 0 < Batterien <= 16
    # 0 <= power_total <= (60 * 138 * anzahl_batterien)

    power_total = -9128.456345
    batterien = {
        543.342,
    }
    assert not is_power_total_ok(power_total, batterien)

@pytest.mark.asyncio
async def test_tools__is_pr_ok__alles_ok(caplog):
    # 43.600 <= pr <= 43.600

    pr = 9128.456345
    assert is_pr_ok(pr)

@pytest.mark.asyncio
async def test_tools__is_pr_ok__kleiner_untergrenze(caplog):
    # 43.600 <= pr <= 43.600

    pr = -99128.456345
    assert not is_pr_ok(pr)

@pytest.mark.asyncio
async def test_tools__is_pr_ok__groesser_obergrenze(caplog):
    # 43.600 <= pr <= 43.600

    pr = 99128.456345
    assert not is_pr_ok(pr)

@pytest.mark.asyncio
async def test_tools__clean_title (caplog):

    title = "Das ist ein TestTitel"
    assert clean_title(title=title) == "das_ist_ein_testtitel"

@pytest.mark.asyncio
async def test_tools__as_float__alle_ok (caplog):

    value = "Das ist der Wert: 800.45 W"
    assert as_float(value) == 800.45


@pytest.mark.asyncio
async def test_tools__as_float__kein_wert_extrahierbar (caplog):

    value = "Das ist der Wert"
    assert as_float(value) is None
