from flask import Flask, render_template, request, abort, json
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
import os
import atexit
import subprocess

# Antes que nada se deben importar los datos a nuestro mongoDB.
# Comando: mongoimport --db <nombre_de_la_DB_a_crear/usar> --collection <nombre_de_la_tabla> --drop --file <nombre_archivo.json> --jsonArray
# Comando 1: mongoimport --db entrega_4 --collection users --drop --type csv --headerline --file users.csv
# Comando 2: mongoimport --db entrega_4 --collection messages --drop --file messages.json --jsonArray

# Links de interes:
# Link 1: busqueda por texto https://github.com/IIC2413/Syllabus-2019-1/blob/master/Actividades/Text%20Search/Text%20Search.ipynb
# Link 2: mongoDB https://github.com/IIC2413/Syllabus-2019-1/blob/master/Actividades/MongoDB/MongoDB.ipynb
# Link 3: enunciado https://github.com/IIC2413/Syllabus-2019-1/blob/master/Proyecto/Entregas/Entrega%204.pdf

USER_KEYS = ["uid","nombre","nacimiento","correo","nacionalidad","contraseña"]
MESSAGES_KEYS = ["message","lat","long","date"] # deleted sender and receptant

# Levantamos el servidor de mongo. Esto no es necesario, puede abrir
# una terminal y correr mongod. El DEVNULL hace que no vemos el output
mongod = subprocess.Popen('mongod', stdout=subprocess.DEVNULL)
# Nos aseguramos que cuando el programa termine, mongod no quede corriendo
atexit.register(mongod.kill)

# El cliente se levanta en localhost:5432
client = MongoClient('localhost')
# Utilizamos la base de datos 'entidades'
db = client["entrega_4"]
# Seleccionamos la colección de usuarios y mensajes
users = db.users
messages = db.messages

# Iniciamos la aplicación de flask
app = Flask(__name__)


@app.route("/")
def home():
    return """
    <h1>Bueeeena loh cabro!</h1>
    <h3>Soy el Micha! xD </h3>
    <h5> Ta wena la app oe zi </h5>
    """

@app.route("/messages")
@app.route("/messages/")
def get_messages():
    """
    Obtiene todos los mensajes en caso de no haber request.
    Dependiendo de request hace text search.
    Formato body: {"obligadas": ["3000", "me"], "deseables": ["Cómo"], "prohibidas": ["salu3"]}
    """

    resultados = [u for u in messages.find({}, {"_id": 0})]
    # Omitir el _id porque no es json serializable.
    if not request.json:
        return json.jsonify(resultados)
    else:
        string = ""
        messages.create_index([("message", "text")])
        if request.json.get("obligadas"):
            if string:
                string += " "
            string += " ".join([f"\"{palabra}\"" for palabra in request.json["obligadas"]])
        if request.json.get("deseables"):
            if string:
                string += " "
            string += " ".join([f"{palabra}" for palabra in request.json["deseables"]])
        if request.json.get("prohibidas"):
            if string:
                string += " "
            string += " ".join([f"-{palabra}" for palabra in request.json["prohibidas"]])
        resultados = list(messages.find({"$text": {"$search": string}},{}))
        finales = []
        uid = request.json.get("uid")
        for value in resultados:
            if uid or uid==0:
                finales += list(messages.find({"_id": value["_id"], "sender": uid}, {"_id": 0}))
            else:
                finales += list(messages.find({"_id": value["_id"]}, {"_id": 0}))
        return json.jsonify(finales)

@app.route("/messages/<int:mid>")
@app.route("/messages/<int:mid>/")
def get_message(mid):
    """
    Obtiene un mensaje desde la db.
    Requiere un mid.
    """

    # Consulta mensaje con su mid.
    listed_messages = list(messages.find({"mid": mid}, {"_id": 0}))

    # Retorno el texto plano de un json.
    return json.jsonify(listed_messages)

@app.route("/users")
@app.route("/users/")
def get_users():
    """
    Obtiene todos los usuarios desde la db.
    """

    # Consulta por todos los usuarios.
    resultados = [u for u in users.find({}, {"_id": 0, "contraseña": 0})]
    
    # Retorno el texto plano de un json.
    return json.jsonify(resultados)

@app.route("/users/<int:uid>")
@app.route("/users/<int:uid>/")
def get_user(uid):
    """Obtiene un usuarios y sus mensages desde la db.
    Requiere el uid del usuario.
    """

    # Obtiene al usuarios.
    listed_users = list(users.find({"uid": uid}, {"_id": 0, "contraseña": 0}))

    # Obtiene mensajes del usuario.
    mensajes_enviados = list(messages.find({"sender": uid}, {"_id": 0}))

    # Crea nueva llave en data del usuario con sus mensajes enviados. 
    listed_users[0]["mensajes enviados"] = (mensajes_enviados)

    # Retorno el texto plano de un json.
    return json.jsonify(listed_users)

@app.route("/messages/from/<int:uid_sender>/to/<int:uid_reciver>")
@app.route("/messages/from/<int:uid_sender>/to/<int:uid_reciver>/")
def get_chat(uid_sender, uid_reciver):
    """
    Obtiene mensajes entre dos usuarios de la db.
    Requiere uid de sender y receptant.
    """

    # Obtiene mensajes según su sender y receptant.
    listed_messages = list(messages.find({"sender": uid_sender, "receptant": uid_reciver}, {"_id": 0, "contraseña": 0}))
    return json.jsonify(listed_messages)

@app.route("/messages/from/<int:uid_sender>/to/<int:uid_reciver>", methods=['POST'])
@app.route("/messages/from/<int:uid_sender>/to/<int:uid_reciver>/", methods=['POST'])
def new_chat(uid_sender, uid_reciver):
    """
    Crea un nuevo mensaje entre dos usuarios en la db.
    Requiere uid de sender y receptant.
    Formato body request: {"message": <var>,"lat": <var>, "long": <var>, "date": <var>}
    """

    # Obtiene el último mid.
    resultados = [u for u in messages.find({}, {"_id": 0})]
    max_mid = max(resultados, key=lambda msg: msg["mid"])
    mid = max_mid["mid"] + 1

    # Obtiene la data del request.
    data = {key: request.json[key] for key in MESSAGES_KEYS}

    # Agrega los datos de la ruta.
    data["sender"] = uid_sender
    data["receptant"] = uid_reciver
    data["mid"] = mid

    # Agrega el mensaje.
    result = messages.insert_one(data)

    if (result):
        message = "Mensaje creado!"
        success = True
    else:
        message = "No se pudo crear el usuario"
        success = False
    
    # Retorno el texto plano de un json.
    return json.jsonify({'success': success, 'message': message})

@app.route('/messages/<int:mid>', methods=['DELETE'])
@app.route('/messages/<int:mid>/', methods=['DELETE'])
def delete_message(mid):
    '''
    Elimina un mensaje de la db.
    Se requiere llave mid.
    '''

    # Borra el primer resultado. Si hay mas, no los borra.
    messages.delete_one({"mid": mid})

    message = f'Mensaje con id={mid} ha sido eliminado.'

    # Retorno el texto plano de un json.
    return json.jsonify({'result': 'success', 'message': message})

if os.name == 'nt':
    app.run()# if __name__ == "__main__":

