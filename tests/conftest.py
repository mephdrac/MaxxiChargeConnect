import asyncio
import pytest
from homeassistant.setup import async_setup_component

@pytest.fixture
async def hass(loop, hass_storage):
    from homeassistant.core import HomeAssistant

    hass = HomeAssistant()
    
    # Setup config_entries explicit laden
    await async_setup_component(hass, "config", {})  # ggf. config laden, wenn du es brauchst
    await async_setup_component(hass, "config_entries", {})  # WICHTIG: config_entries laden
    await async_setup_component(hass, "homeassistant", {})
    
    yield hass

    await hass.async_stop()
    await asyncio.sleep(0.1)


#  import pytest_asyncio
# from homeassistant.core import HomeAssistant
# from homeassistant.setup import async_setup_component
# from homeassistant.loader import DATA_COMPONENTS, DATA_INTEGRATIONS, DATA_MISSING_PLATFORMS, DATA_PRELOAD_PLATFORMS

# @pytest_asyncio.fixture
# async def hass(tmp_path) -> HomeAssistant:
#     hass = HomeAssistant(config_dir=tmp_path)

#     # Setze alle wichtigen interne Caches, die HA erwartet
#     hass.data[DATA_COMPONENTS] = {}
#     hass.data[DATA_INTEGRATIONS] = {}
    
#     hass.data[DATA_PRELOAD_PLATFORMS] = set()

#     await hass.async_start()
#     await hass.async_block_till_done()

#     # Jetzt klappt das Setup von Core-Integration "homeassistant"
#     assert await async_setup_component(hass, "homeassistant", {})
#     await hass.async_block_till_done()

#     # Optional: andere Komponenten
#     assert await async_setup_component(hass, "sensor", {})
#     await hass.async_block_till_done()

#     yield hass

#     await hass.async_stop()




# import pytest_asyncio
# from homeassistant.core import HomeAssistant
# from homeassistant.setup import async_setup_component
# from homeassistant.const import EVENT_HOMEASSISTANT_START

# @pytest_asyncio.fixture
# async def hass(tmp_path) -> HomeAssistant:
#     hass = HomeAssistant(config_dir=tmp_path)
#     hass.data["integrations"] = {}  # Explizit anlegen, damit Loader nicht meckert
#     await hass.async_start()
#     await hass.async_block_till_done()

#     assert await async_setup_component(hass, "sensor", {})
#     await hass.async_block_till_done()

#     yield hass

#     await hass.async_stop()

