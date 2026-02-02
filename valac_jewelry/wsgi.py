"""
WSGI entry point para la aplicación Flask.
Permite que Flask encuentre la app fácilmente.
"""
from valac_jewelry import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
