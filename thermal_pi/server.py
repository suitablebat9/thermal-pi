import argparse
import io
import json
import logging
import time
from flask import Flask, Response, jsonify, request
from .core import Engine, native_picture

PAGE = '''<!doctype html><html><head><meta name="viewport" content="width=device-width">
<title>Thermal Pi</title><style>body{margin:0;background:#090b10;color:white;font:16px system-ui}
main{height:100vh;display:grid;place-items:center}img{max-width:100vw;max-height:100vh;object-fit:contain}
#status{position:fixed;top:15px;left:15px;background:#721e28;padding:10px;border-radius:8px}
button{position:fixed;bottom:15px;right:15px;padding:10px}button:fullscreen{display:none}</style></head>
<body><main id="view"><img id="image" src="/stream.mjpg" alt="Waiting for thermal camera">
<div id="status">Connecting…</div></main><button onclick="document.getElementById('view').requestFullscreen()">Fullscreen</button>
<script>const badge=document.getElementById('status'),img=document.getElementById('image');
async function poll(){try{let r=await fetch('/api/status',{cache:'no-store',signal:AbortSignal.timeout(1500)});if(!r.ok)throw Error();let s=await r.json();
img.style.visibility=s.connected?'visible':'hidden';badge.hidden=s.connected&&!s.demo;
badge.textContent=s.connected?'DEMO — simulated camera':('NO LIVE VIDEO — '+(s.error||'stale feed'));
}catch(e){img.style.visibility='hidden';badge.hidden=false;badge.textContent='DISCONNECTED — no live video';}}
setInterval(poll,500);poll();</script></body></html>'''


def create_app(engine):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 4096

    @app.before_request
    def local_only():
        # Loopback listener + SSH tunnel; prevent browser cross-origin writes/DNS rebinding.
        if request.host.split(':')[0] not in ('127.0.0.1', 'localhost'):
            return jsonify(error='Use localhost through SSH'), 403
        if request.method == 'POST':
            if not request.is_json or request.headers.get('Origin') not in (None, request.host_url.rstrip('/')):
                return jsonify(error='Local JSON requests only'), 403

    @app.after_request
    def no_cache(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.errorhandler(ValueError)
    def bad_request(exc):
        return jsonify(error=str(exc)), 400

    @app.get('/')
    def index():
        return PAGE

    @app.get('/api/status')
    def status():
        return jsonify(engine.status())

    @app.post('/api/settings')
    def settings():
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError('Expected an object')
        return jsonify(engine.update(data))

    @app.post('/api/command')
    def command():
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError('Expected an object')
        engine.command(data.get('action'))
        return jsonify(queued=True), 202

    @app.post('/api/save')
    def save():
        engine.save()
        return jsonify(saved=True)

    @app.get('/api/field-frame')
    def field_frame():
        quality = request.args.get('quality', 60, type=int)
        if not 25 <= quality <= 90:
            raise ValueError('JPEG quality must be 25–90')
        with engine.lock:
            if not engine.status()['connected'] or engine.latest is None:
                return jsonify(error='Waiting for live camera data'), 503
            capture, sequence = engine.latest, engine.sequence
            if request.args.get('after', type=int) == sequence:
                return Response(status=204)
        native, info = native_picture(*capture)
        if capture[1]['palette'] in ('white', 'black') and not capture[1]['range_on']:
            native = native.convert('L')
        data = io.BytesIO()
        data.write(json.dumps(info, separators=(',', ':')).encode() + b'\n')
        native.save(data, format='JPEG', quality=quality)
        return Response(data.getvalue(), mimetype='application/octet-stream',
                        headers={'X-Frame-Sequence': str(sequence)})

    @app.get('/api/frame')
    def current_frame():
        with engine.lock:
            if not engine.status()['connected'] or engine.jpeg is None:
                return jsonify(error=engine.error or 'Waiting for a fresh frame'), 503
            return Response(engine.jpeg, mimetype='image/jpeg')

    @app.get('/stream.mjpg')
    def stream():
        def frames():
            last = -1
            while not engine.stop.is_set():
                with engine.lock:
                    jpeg, seq = engine.jpeg, engine.sequence
                    live = engine.status()['connected']
                if live and jpeg and seq != last:
                    last = seq
                    yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(jpeg)).encode()+b'\r\n\r\n'+jpeg+b'\r\n'
                else:
                    time.sleep(.02)
        return Response(frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--config')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    engine = Engine(args.demo, args.config)
    engine.thread.start()
    try:
        create_app(engine).run(host='127.0.0.1', port=args.port, threaded=True, use_reloader=False)
    finally:
        engine.stop.set()
        engine.thread.join(timeout=5)

if __name__ == '__main__':
    main()
