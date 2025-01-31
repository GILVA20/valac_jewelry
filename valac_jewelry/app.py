#from flask import Flask
#import firebase_admin
#from firebase_admin import credentials, db
#
#import os
#
#app = Flask(__name__)
#
## 1. Inicializar Firebase
#base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#cred_path = os.path.join(base_dir, 'instance', 'valacjoyas-e23f2-firebase-adminsdk-fbsvc-f4e24e9ab4.json')
#cred = credentials.Certificate(cred_path)
#firebase_admin.initialize_app(cred, {
#    'databaseURL': 'https://valacjoyas-e23f2-default-rtdb.firebaseio.com/'
#})
#
## 2. Referencia a la Realtime Database
#ref = db.reference('/')
#
#@app.route('/')
#def hello():
#    return "¡Hola, VALAC Joyas con Firebase!"
#
## 3. Ruta para probar lectura/escritura en Realtime Database
#@app.route('/test-firebase')
#def test_firebase():
#    # Escribir en Realtime Database
#    demo_ref = ref.child('test').child('demo')
#    demo_ref.set({
#        'mensaje': 'Hola desde Flask!',
#        'status': 'Funciona'
#    })
#
#    return "Datos escritos en Realtime Database con éxito."
#
#if __name__ == '__main__':
#    app.run(debug=True)
#
from flask import Flask, render_template
import firebase_admin
from firebase_admin import credentials, db
import os

app = Flask(__name__, static_folder='../static')


# 1. Inicializar Firebase
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cred_path = os.path.join(base_dir, 'instance', 'valacjoyas-e23f2-firebase-adminsdk-fbsvc-f4e24e9ab4.json')
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://valacjoyas-e23f2-default-rtdb.firebaseio.com/'
})

# 2. Referencia a la Realtime Database
ref = db.reference('/')

# Ruta para la página de inicio (home.html)
@app.route('/')
def home():
    return render_template('home.html')  # Carga el archivo home.html

# 3. Ruta para probar lectura/escritura en Realtime Database
@app.route('/test-firebase')
def test_firebase():
    # Escribir en Realtime Database
    demo_ref = ref.child('test').child('demo')
    demo_ref.set({
        'mensaje': 'Hola desde Flask!',
        'status': 'Funciona'
    })

    # Leer desde Realtime Database
    demo_data = demo_ref.get()  # Obtiene los datos del nodo 'test/demo'
    
    # Imprimir los datos de Firebase en la terminal o en el navegador
    print(demo_data)
    
    return f"Datos escritos en Realtime Database con éxito. Datos: {demo_data}"

if __name__ == '__main__':
    app.run(debug=True)
