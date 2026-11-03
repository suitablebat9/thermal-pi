"""Single-key camera controls shared by the Pi and Mac launchers."""
import argparse
import curses
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PAGES = {
    'Main': ['1 White hot     2 Black hot', '3 Iron          4 Rainbow',
             '5 Zoom          6 Rotation', '7 Flip          8 Calibrate shutter',
             '9 Gain'],
    'Zoom': ['+ / Right   Zoom in 0.25x', '- / Left    Zoom out 0.25x',
             '1–8         Jump to that zoom'],
    'Rotation': ['+ / Right   Rotate clockwise 90°', '- / Left    Rotate counterclockwise 90°',
                 '0           Reset rotation'],
    'Gain': ['h   High gain', 'l   Low gain'],
}


def run_menu(port, open_viewer=None, pause_viewer=None, events=None):
    def api(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(f'http://127.0.0.1:{port}/api/{path}', data=data,
                      headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=5) as response:
            return json.load(response)

    def session(screen):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        screen.keypad(True)
        screen.timeout(300)
        page, message, status = 'Main', '', {}
        key = 'r'
        while True:
            try:
                settings = status.get('settings', {})
                patch = {}
                if key == 'r':
                    status = api('status')
                    message = status['command']
                elif key == 'v' and open_viewer:
                    message = open_viewer() or 'Video window opened'
                elif key in ('b', 27):
                    page, message = 'Main', ''
                elif page == 'Main' and key in ('0', 'q'):
                    return
                elif key == 's':
                    api('save', {})
                    message = 'Settings saved'
                elif page == 'Main' and key in ('5', '6', '9'):
                    page = {'5':'Zoom', '6':'Rotation', '9':'Gain'}[key]
                    message = ''
                elif page == 'Main' and key in ('1','2','3','4'):
                    patch['palette'] = {'1':'white','2':'black','3':'iron','4':'rainbow'}[key]
                elif page == 'Main' and key == '7' and settings:
                    patch['flip'] = not settings['flip']
                elif page == 'Main' and key == '8':
                    api('command', {'action':'shutter'})
                    message = 'Calibration queued. Press r to check.'
                elif page == 'Gain' and key in ('h','l'):
                    gain = 'high' if key == 'h' else 'low'
                    api('command', {'action':gain})
                    message = f'{gain.title()} gain queued. Press r to check.'
                elif page == 'Zoom' and key in tuple('12345678'):
                    patch['zoom'] = int(key)
                elif page == 'Rotation' and key == '0':
                    patch['rotation'] = 0
                elif settings and key in ('+', '=', '-', curses.KEY_RIGHT, curses.KEY_LEFT):
                    direction = -1 if key in ('-', curses.KEY_LEFT) else 1
                    if page == 'Zoom':
                        patch['zoom'] = min(8, max(1, settings['zoom'] + direction * .25))
                    elif page == 'Rotation':
                        patch['rotation'] = (settings['rotation'] + direction * 90) % 360
                if patch:
                    status['settings'] = api('settings', patch)
                    message = ''
            except HTTPError as exc:
                message = f'Request failed: {exc.read().decode(errors="replace")}'
            except (URLError, OSError) as exc:
                if pause_viewer:
                    pause_viewer()
                status = {}
                message = f'Connection error: {exc}. Press r to retry.'
            if events and not events.empty():
                message = events.get_nowait()
            settings = status.get('settings', {})
            title = 'THERMAL PI' + ('  [DEMO]' if status.get('demo') else '') + '  /  ' + page
            if settings:
                summary = (f"{settings['palette']}   {settings['zoom']:g}x   {settings['rotation']}°"
                           f"   flip {'on' if settings['flip'] else 'off'}   gain {settings['gain']}")
            else:
                summary = 'Waiting for camera service'
            if settings and not status['connected']:
                summary = 'OFFLINE   ' + summary
            lines = [title, summary, '', *PAGES[page], '']
            if open_viewer:
                lines.append('v Open video window')
            lines += ['s Save   r Check status', '0 Quit' if page == 'Main' else 'b / Esc Back', '', message]
            # curses diffs the virtual screen; unchanged rows stay in place.
            height, width = screen.getmaxyx()
            screen.erase()
            for row, line in enumerate(lines[:height]):
                if width > 1:
                    screen.addnstr(row, 0, line, width - 1, curses.A_BOLD if row == 0 else 0)
            screen.refresh()
            while True:
                number = screen.getch()
                if number != -1 or (events and not events.empty()):
                    break
            key = chr(number).lower() if 32 <= number < 127 else number

    try:
        curses.wrapper(session)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    run_menu(parser.parse_args().port)
