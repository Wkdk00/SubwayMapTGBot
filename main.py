from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from redis import asyncio as aioredis

from data import nsk as nsk_subway, spb as spb_subway
from funcs import min_time, route

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@cache(expire=20)
async def get_road_time(city: str, start: str, finish: str):
    #await asyncio.sleep(5) проверка работы кэширования
    if city == "nsk":
        subway = nsk_subway
    elif city == "spb":
        subway = spb_subway
    else:
        raise HTTPException(status_code=404)
    if start not in subway or finish not in subway:
        raise HTTPException(status_code=404)
    time, re_way = min_time(subway, start, finish)
    way = route(re_way, start, finish)
    return {"time": time, "way": way}

@app.on_event("startup")
def startup():
    redis = aioredis.from_url("redis://localhost", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)