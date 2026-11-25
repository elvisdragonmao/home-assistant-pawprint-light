"""PawPrint V1.1 local BLE light bridge, YAML configured."""
import asyncio
import logging
import time
import voluptuous as vol
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.helpers import config_validation as cv, discovery
from .gesture import Gesture, decode, decode_battery

DOMAIN='pawprint_light'
_LOGGER=logging.getLogger(__name__)
WRITE='0000150a-0000-1000-8000-00805f9b34fb'
NOTIFY='0000150b-0000-1000-8000-00805f9b34fb'
INIT=bytes([0x50,1,0xD0,1])+bytes(13)
PALETTE=[[255,255,255],[255,0,0],[255,160,0],[0,255,0],[0,255,255],[0,0,255],[160,0,255]]
SCHEMA=vol.Schema({vol.Required('light'):cv.entity_id,vol.Optional('address'):cv.string,
 vol.Optional('axis',default='x'):vol.In(['x','y','z']),
 vol.Optional('left',default=-60):vol.All(vol.Coerce(int),vol.Range(min=-128,max=127)),
 vol.Optional('right',default=60):vol.All(vol.Coerce(int),vol.Range(min=-128,max=127)),
 vol.Optional('hold_seconds',default=.5):vol.All(vol.Coerce(float),vol.Range(min=.3,max=3)),
 vol.Optional('motion_threshold',default=12):vol.All(vol.Coerce(int),vol.Range(min=2,max=100)),
 vol.Optional('speed_threshold',default=35):vol.All(vol.Coerce(float),vol.Range(min=1)),
 vol.Optional('debug',default=False):cv.boolean,vol.Optional('dry_run',default=False):cv.boolean})
CONFIG_SCHEMA=vol.Schema({DOMAIN:SCHEMA},extra=vol.ALLOW_EXTRA)

async def async_setup(hass,config):
    if DOMAIN not in config: return True
    cfg=config[DOMAIN]
    if not cfg['light'].startswith('light.') or cfg['left']==cfg['right']:
        _LOGGER.error('Expected a light entity and distinct left/right endpoints'); return False
    bridge=Bridge(hass,cfg)
    hass.data[DOMAIN]=bridge
    await discovery.async_load_platform(hass,Platform.SENSOR,DOMAIN,{},config)
    task=hass.async_create_background_task(bridge.run(), 'pawprint_light bridge')
    _LOGGER.info('PawPrint bridge ready for %s (dry_run=%s)', cfg['light'], cfg['dry_run'])
    async def stop(_event):
        task.cancel()
        await asyncio.gather(task,return_exceptions=True)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,stop)
    return True

class Bridge:
    def __init__(self,hass,cfg):
        self.hass,self.cfg=hass,cfg
        self.gesture=Gesture('xyz'.index(cfg['axis']),cfg['left'],cfg['right'],cfg['hold_seconds'],cfg['motion_threshold'],cfg['speed_threshold'])
        self.color=-1
        self.address=cfg.get('address')
        self.battery=None
        self.battery_sensor=None
    def record_battery(self,data):
        level=decode_battery(data)
        if level is None: return False
        self.battery=level
        if self.battery_sensor is not None and self.battery_sensor.hass is not None:
            self.battery_sensor.async_write_ha_state()
        return True
    async def action(self,action):
        kind,value=action
        self.hass.bus.async_fire('pawprint_light_gesture',{'gesture':kind,'brightness_pct':value})
        _LOGGER.debug('Gesture: %s',action)
        if self.cfg['dry_run']: return
        entity=self.cfg['light']; data={'entity_id':entity}; service='turn_on'
        if kind=='off' or (kind=='brightness' and value==0): service='turn_off'
        elif kind=='brightness': data['brightness_pct']=value
        elif kind=='color':
            state=self.hass.states.get(entity)
            if state is None or state.state in ('unknown','unavailable'): return
            if state.state=='on': self.color=(self.color+1)%len(PALETTE)
            elif self.color<0: self.color=0
            data['rgb_color']=PALETTE[self.color]
        try:
            await asyncio.wait_for(self.hass.services.async_call('light',service,data,blocking=True),timeout=5)
        except Exception:
            _LOGGER.exception('Light service failed')
    async def run(self):
        while True:
            try:
                if not self.address:
                    found={s.address for s in bluetooth.async_discovered_service_info(self.hass,connectable=True) if s.name=='47L120300'}
                    if len(found)==1:
                        self.address=found.pop(); _LOGGER.info('PawPrint found: %s',self.address)
                    elif len(found)>1:
                        _LOGGER.warning('Multiple PawPrints found; configure address in YAML')
                device=bluetooth.async_ble_device_from_address(self.hass,self.address,connectable=True) if self.address else None
                if device is None:
                    await asyncio.sleep(5); continue
                await self.session(device)
            except asyncio.CancelledError: raise
            except Exception as err: _LOGGER.warning('PawPrint disconnected/retry: %s',err)
            await asyncio.sleep(3)
    async def session(self,device):
        client=await establish_connection(BleakClientWithServiceCache,device,'PawPrint')
        self.gesture.reset()
        queue=asyncio.Queue(maxsize=32)
        def notify(_sender,data):
            if self.record_battery(data): return
            sample=decode(data)
            if sample is None: return
            if self.cfg['debug']: _LOGGER.debug('D0 %s pressed=%s XYZ=%s',bytes(data).hex(),*sample)
            if queue.full():
                while not queue.empty(): queue.get_nowait()
                self.gesture.reset()
            queue.put_nowait((time.monotonic(),*sample))
        try:
            await client.start_notify(NOTIFY,notify)
            await client.write_gatt_char(WRITE,INIT,response=False)
            first_sample=await asyncio.wait_for(queue.get(),timeout=2)
            self.gesture.feed(*first_sample)
            _LOGGER.info('PawPrint connected and reporting sensor data: %s',device.address)
            while client.is_connected:
                sample=await asyncio.wait_for(queue.get(),timeout=2)
                if time.monotonic()-sample[0]>.65:
                    self.gesture.reset(); continue
                action=self.gesture.feed(*sample)
                if action: await self.action(action)
        finally:
            self.gesture.reset()
            if client.is_connected: await client.disconnect()
