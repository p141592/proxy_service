import datetime
import ujson
import httpx
import uvicorn

from httpx import Headers
from starlette.requests import Request
from starlette.responses import Response

# Адрес сервера, на который проксируются запросы
TARGET_SERVER = "http://realserver.ru"

# Эмуляция данных в БД
SECURITY_STORE = {
    "TOKEN_EXAMPLE": {
        "LOGIN": "TEST",
        "PASSWORD": "TEST"
    }
}

# Это можно и нужно потом заменить на REDIS
USERS_CACHE = {}


# Если в кеше нет ключа сессии пользовател, получить его
async def auth(api_key):
    url = TARGET_SERVER + '/vip/v1/authUser'

    async with httpx.AsyncClient() as client:
        r = await client.request(
            "POST",
            url,
            headers={
                "api_key": api_key,
                "date_time": str(datetime.datetime.now()),
                "content-type": "application/x-www-form-urlencoded"
            },
            data={
                "login": SECURITY_STORE[api_key]['LOGIN'],
                "password": SECURITY_STORE[api_key]['PASSWORD']
            }
        )
        data = r.json()
        return data.get('session_id')


# Собираем все запросы, обогащаем заголовки
async def app(scope, receive, send):
    request = Request(scope, receive)

    user_key = request.headers.get('api_key')
    if not USERS_CACHE.get(user_key):
        USERS_CACHE[user_key] = await auth(user_key)

    headers = (tuple(["session_id", USERS_CACHE[user_key]]), *request.headers.items())
    print(headers)

    async with httpx.AsyncClient() as client:
        url = TARGET_SERVER + request.url.path
        r = await client.request(request.method, url, headers=Headers(headers), data=await request.body())

    response = UJSONResponse(r.json())
    #response = Response(content=r.content, headers=r.headers, status_code=r.status_code, media_type="application/json")
    result = await response(scope, receive, send)
    return result

uvicorn.run(app, host="0.0.0.0")

