from socketio import AsyncServer
from aiohttp import web
from aiohttp_session import get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from hashlib import sha3_512
from redis import Redis
import pickle


database = Redis(host='localhost', port=6379, db=0)

app = web.Application()
setup(app, EncryptedCookieStorage(b'ghnrty1twoo7234th66ytewtke3arer&'))
sio = AsyncServer(async_mode='aiohttp')
sio.attach(app)


routes = web.RouteTableDef()

@routes.get("/")
async def index_route(request):
    with open('index.html', 'rb') as file:
        index = file.read()
        return web.Response(body=index,
                            content_type="text/html")

@routes.post("/app")
async def app_route(request):
    session = await get_session(request)
    data = await request.post()
    if 'secret' in data:
        code = sha3_512()
        code.update(data['secret'].encode())
        session['secret'] = code.hexdigest()
    else:
        return web.Response(text='401',
                            content_type='text/plain',
                            status=401)
    with open('app.html', 'rb') as file:
        app = file.read()
        return web.Response(body=app,
                            content_type="text/html")

@routes.get("/app")
async def app_wrong_route(request):
    return web.HTTPPermanentRedirect('/')

app.add_routes(routes)


async def auth(environ):
    req = environ['aiohttp.request']
    session = await get_session(req)
    return session['secret']

@sio.on('connect')
async def on_connect(sid, environ):
    i = await auth(environ)
    if not database.get(i):
        database.set(i, pickle.dumps(list()))
    await sio.save_session(sid, {'identificator': i})

@sio.on('add todo')
async def on_add_todo(sid, data):
    session = await sio.get_session(sid)
    i = session['identificator']
    user_todos = pickle.loads(database.get(i))
    user_todos.append(data)
    database.set(i, pickle.dumps(user_todos))
    await sio.emit('todos', pickle.loads(database.get(i)), room=sid)

@sio.on('done todo')
async def on_done_todo(sid, data):
    session = await sio.get_session(sid)
    i = session['identificator']
    user_todos = pickle.loads(database.get(i))
    user_todos.remove(data)
    database.set(i, pickle.dumps(user_todos))
    await sio.emit('todos', pickle.loads(database.get(i)), room=sid)

@sio.on('get todo')
async def on_get_todo(sid):
    session = await sio.get_session(sid)
    i = session['identificator']
    await sio.emit('todos', pickle.loads(database.get(i)), room=sid)


if __name__ == '__main__':
    web.run_app(app)