from sources.udp_listener import listen_udp
from dispatcher import *


dispatcher = Dispatcher()
listen_udp(10110, dispatcher.dispatch)
while True:
    pass