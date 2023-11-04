from pathlib import Path
import logging

def start():

    path_socket=Path('/amniotic.socket')

    if path_socket.exists():
        msg=f'Pulse socket found at "{path_socket}". Using host-shared audio.'
        logging.info(msg)
        import os
        os.environ['PULSE_SERVER'] = "unix://amniotic.socket"
        os.environ['PULSE_COOKIE'] = "/amniotic.cookie"
    else:
        msg = f'No Pulse socket found at "{path_socket}". Using dedicated audio.'
        logging.warning(msg)

    from amniotic.mqtt import loop
    loop.start()

if __name__ == '__main__':
    start()
