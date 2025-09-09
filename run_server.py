import uvicorn
from decouple import config

if __name__ == "__main__":
    config = uvicorn.Config(
        'core.asgi:application',
        host=config('SERVER_HOST', cast=str, default='127.0.0.1'),
        port=config('SERVER_PORT', cast=int, default='8000'),
        workers=1,  # Due to Channels currently uses in-memory channels layer, worker count is limited to only one.
        log_level='info',
        reload=False
    )
    server = uvicorn.Server(config)
    server.run()
