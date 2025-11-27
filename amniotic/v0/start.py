import logging
from pathlib import Path


def start():
    path_pulse = Path('/amniotic/pulse')
    path_socket = path_pulse / 'amniotic.socket'
    path_cookie = path_socket.with_suffix('.cookie')

    path_conf = path_socket.with_suffix(f'.client.conf')

    if path_pulse.exists():
        msg = f'Pulse socket data found at "{path_pulse}". Using host-shared audio.'
        logging.info(msg)

        if not path_socket.exists():
            msg = f'Pulse path found "{path_pulse}", but it does not contain a Pulse socket "{path_socket}".'
            raise FileNotFoundError(msg)

        if not path_conf.exists():
            msg = f'Pulse socket found "{path_socket}", but it has no client config "{path_conf}". Will be created...'
            logging.warning(msg)
            text_conf = Path(f'/{path_conf.name}.template').read_text().format(path=path_socket)
            path_conf.write_text(text_conf)

        import os
        os.environ['PULSE_SERVER'] = f"unix:/{path_socket}"
        os.environ['PULSE_COOKIE'] = str(path_cookie)
    else:
        msg = f'No Pulse socket found at "{path_pulse}". Using dedicated audio.'
        logging.warning(msg)

    from amniotic.v0 import loop
    loop.start()

if __name__ == '__main__':
    start()
