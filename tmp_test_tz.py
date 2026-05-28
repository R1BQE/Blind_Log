from settings import SettingsManager
from qso_manager import QSOManager
from controller import ApplicationController
sm=SettingsManager()
# ensure timezone UTC
sm.settings['timezone']='UTC'
sm.settings['custom_timezone']='+0'
qm=QSOManager(settings_manager=sm)
ctrl=ApplicationController(qm, sm, None)
print('default components:', ctrl.get_default_datetime_components())
res1=qm.add_qso({'call':'one'})
print('first qso datetime:', res1.data['datetime'])
res2=qm.add_qso({'call':'two'})
print('second qso datetime:', res2.data['datetime'])
print('settings still:', sm.settings['timezone'], sm.settings['custom_timezone'])
