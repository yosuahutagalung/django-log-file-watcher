import uvicorn
from decouple import config

if __name__ == "__main__":
    config = uvicorn.Config(
        'core.asgi:application',
        host=config('SERVER_HOST', default='127.0.0.1'),
        port=config('SERVER_PORT', default='8000'),
        workers=1,
        log_level='info'
    )
    server = uvicorn.Server(config)
    server.run()
