"""Persistent menu client. Run on the Pi through SSH."""
import argparse
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    run_menu(args.port)


def run_menu(port, open_viewer=None):
    base = f'http://127.0.0.1:{port}'
    def api(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(base+path, data=data, headers={'Content-Type':'application/json'})
        with urlopen(req, timeout=5) as response:
            return json.load(response)
    while True:
        try:
            s = api('/api/status')
            print('\nTHERMAL PI' + (' [DEMO]' if s['demo'] else ''))
            print('LIVE' if s['connected'] else 'OFFLINE: '+str(s['error']))
            print(s['settings'], '\nHardware:', s['command'])
            print('1 White hot  2 Black hot  3 Iron  4 Rainbow\n5 Zoom  6 Rotation  7 Flip\n8 Shutter calibration  9 Gain high/low\ns Save settings  Enter Refresh  0 Exit menu')
            if open_viewer:
                print('v Open video window')
            choice = input('Choose: ').strip().lower()
            if choice == 'v' and open_viewer:
                open_viewer()
                continue
            if choice == '0':
                return
            if choice in ('1','2','3','4'):
                api('/api/settings', {'palette':dict(zip('1234',('white','black','iron','rainbow')))[choice]})
            elif choice == '5':
                api('/api/settings', {'zoom':float(input('Zoom 1–8: '))})
            elif choice == '6':
                api('/api/settings', {'rotation':int(input('Clockwise degrees 0/90/180/270: '))})
            elif choice == '7':
                api('/api/settings', {'flip':not s['settings']['flip']})
            elif choice == '8':
                print(api('/api/command', {'action':'shutter'}))
            elif choice == '9':
                print(api('/api/command', {'action':input('Gain high/low: ').strip().lower()}))
            elif choice == 's':
                print(api('/api/save', {}))
        except HTTPError as exc:
            print('Request failed:', exc.read().decode())
        except (URLError, OSError) as exc:
            print('Cannot reach camera service:', exc)
            try:
                input('Start the service, then press Enter to retry (Ctrl-C exits).')
            except (EOFError, KeyboardInterrupt):
                return
        except ValueError as exc:
            print('Invalid value:', exc)
        except (EOFError, KeyboardInterrupt):
            print('\nMenu closed.')
            return

if __name__ == '__main__':
    main()
