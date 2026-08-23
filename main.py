from upstash_redis import Redis as UpRedis
# import logging

from flask import Flask, request, Response #, send_file

from dotenv import load_dotenv  # pour les variables d'environnement
import ast
import base64
# import threading
import requests
import os
import json

# apiflash
import uuid
from urllib.parse import quote # urljoin pour selectolax
# Pour la gesion des cles
import hashlib
from Crypto.Cipher import AES

from flask_cors import CORS
app = Flask(__name__)
CORS(app)

#_____________________________________________________________________________________________________

global_bool_envoi_bip = False
nom_site = "html-nine-topaz.vercel.app"


# charger les variables d'environnements
dotenv_path=".env"
reponse_load = load_dotenv(dotenv_path=dotenv_path, override=True) # Mettre un fichier .env dans le répertoire de travail (souvent C:\Users\FTAB)
if reponse_load:
    print("Fichier .env chargé en local")
else:
    dotenv_path="/etc/secrets/secrets.env"
    reponse_load = load_dotenv(dotenv_path=dotenv_path, override=True) # Mettre un fichier .env dans le répertoire de travail (souvent C:\Users\FTAB)
    if reponse_load:
        print("Fichier secrets.env chargé sur cloud")
    else:
        print("Erreur de chargement de secrets.env!")


dico_env={}

redis_trouve = {}


# def trace(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         sortie_log(f"ENTER {func.__name__} args={args} kwargs={kwargs}")
#         t0 = time.time()
#         try:
#             return func(*args, **kwargs)
#         except Exception as e:
#             sortie_log(f"Trace exception : {e}")
#         finally:
#             sortie_log(f"EXIT  {func.__name__} elapsed={time.time() - t0:.6f}s")
#     return wrapper



def creer_liste_env(cle = "arreter"):
    global dico_env
    if not dico_env:
        temp = os.getenv("dict_var") # temp_dict["dict_var"]
        # env_dict = {k: json_loads_sans_erreur(v) for k, v in temp.items()}
        dico_env = ast.literal_eval(temp)
    return dico_env.get(cle, "")



def dict_to_env_file(env_dict, path=".env"):
    with open(path, "w") as f:
        var = f"dict_var={env_dict}"
        f.write(var)



def liste_env_base(cle = "arreter"):
    return creer_liste_env(cle)



redis_base = UpRedis(url = liste_env_base("UPSTASH_REDIS_REST_URL"), token = liste_env_base("UPSTASH_REDIS_REST_TOKEN"))
chemin_var = liste_env_base("chemin")

# A partir d'ici, liste_env
global_redis_rest_url = ""
global_redis_rest_token = ""


def built_redis_base(*args, **kwargs):
    return redis_base


ens_dict_api_telegram = {}
ens_dict_api_telegram["redis_base"] = {"fonc": built_redis_base}


# 1. Dériver une clé AES depuis un texte utilisateur
def derive_key(chemin: str) -> bytes:
    return hashlib.sha256(chemin.encode()).digest()


# 2. Chiffrement AES-GCM
def encrypt_message(message: str, chemin: str) -> str:
    key = derive_key(chemin)
    cipher = AES.new(key, AES.MODE_SIV)
    ciphertext, tag = cipher.encrypt_and_digest(message.encode())
    encoded = base64.b64encode(tag + ciphertext).decode()
    return encoded

# 3. Transformation Base64 → identifiant Python
def transform_for_var(encoded: str) -> str:
    transformed = (
        encoded.replace("+", "1_")
               .replace("/", "2_")
               .replace("=", "3_")
    )
    return "var" + transformed

# 4. Inverse : identifiant Python → Base64 original
def reverse_transform(varname: str) -> str:
    encoded = varname[len("var"):]  # retirer le préfixe
    encoded = (
        encoded.replace("1_", "+")
               .replace("2_", "/")
               .replace("3_", "=")
    )
    return encoded


def decrypt_message(encoded: str, chemin: str) -> str:
    key = derive_key(chemin)
    data = base64.b64decode(encoded)
    tag, ciphertext = data[:16], data[16:]
    cipher = AES.new(key, AES.MODE_SIV)
    decrypted = cipher.decrypt_and_verify(ciphertext, tag)
    return decrypted.decode()



# ajout
def var_en_var(var):
    encoded = encrypt_message(var, chemin_var)
    varname = transform_for_var(encoded)
    return varname


# cle en secret
def inverse_var(texte):
    encoded_back = reverse_transform(texte)
    decoded = decrypt_message(encoded_back, chemin_var)
    return decoded


       
def choisir_redis(nom_api = "", redis_var= "", build = False):
    return redis_base


# @trace
def get_valeur_redis(cle, redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    val_redis = redis_var.get(cle_redis)
    if val_redis:
        val = json.loads(inverse_var(val_redis))
        return val
    
    return ""

# @trace

def fonct_id(val): return val
def fonct_transformer_valeur(val): return json.loads(inverse_var(val))

def set_valeur_redis(cle, valeur, redis_var=None, get=False, nx = False, px = 0):    
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    val_redis = var_en_var(json.dumps(valeur, ensure_ascii=False))
    if get or nx or px:
        params = {}
        params = params|{"get": get} if get else params
        fonct_get = fonct_transformer_valeur if get else fonct_id
        params = params|{"nx": nx} if nx else params
        params = params|{"px": px} if px else params                
        return fonct_get(redis_var.set(cle_redis, val_redis, **params))
    else:
        return redis_var.set(cle_redis, val_redis)
    
    



#setnx(redis_key, id_auto)
def setnx_valeur_redis(cle, valeur, redis_var=None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    val_redis = var_en_var(json.dumps(valeur, ensure_ascii=False))
    return redis_var.setnx(cle_redis, val_redis)
  




def hget_dict_redis(cle, key_dict, redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    key_dict_redis = var_en_var(key_dict)
    val_redis = redis_var.hget(cle_redis, key_dict_redis)
    if val_redis:
        val = json.loads(inverse_var(val_redis))
        return val
        
    return ""



def hgetall_dict_redis(cle, redis_var=None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    dict_redis = redis_var.hgetall(cle_redis)
    if dict_redis:
        dict_final = {inverse_var(key_dict_redis):json.loads(inverse_var(val_redis)) for key_dict_redis, val_redis in dict_redis.items()}
        return dict_final
        
    return ""


def hset_dict_redis(cle, key_dict = "aucun", valeur = "", redis_var = None, mapping = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    cle_redis = var_en_var(cle)
    # mapping_redis = {}
    if mapping:
        for key_mapping, valeur_mapping in mapping.items():
            key_dict_redis = var_en_var(key_mapping)
            val_redis = var_en_var(json.dumps(valeur_mapping, ensure_ascii=False))
            redis_var.hset(cle_redis, key_dict_redis, val_redis)
        return True
    else:
        key_dict_redis = var_en_var(key_dict)
        val_redis = var_en_var(json.dumps(valeur, ensure_ascii=False))
        return redis_var.hset(cle_redis, key_dict_redis, val_redis)



    
# @trace
def lrange_liste_redis(cle, redis_var = None):
    print(cle, redis_var)
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    print(str(redis_var))
    cle_redis = var_en_var(cle)
    liste_valeurs_redis = redis_var.lrange(cle_redis, 0, -1)
    liste_valeurs = [json.loads(inverse_var(t)) for t in liste_valeurs_redis]
    return liste_valeurs
    


# @trace
def rpush_liste_redis(cle, valeur, redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    val_redis = var_en_var(json.dumps(valeur, ensure_ascii=False))
    return redis_var.rpush(cle_redis, val_redis)

    
    

# @trace
def lpush_liste_redis(cle, valeur, redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    val_redis = var_en_var(json.dumps(valeur, ensure_ascii=False))
    return redis_var.lpush(cle_redis, val_redis)
    



def lpos_liste_redis(cle, valeur, redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    val_redis = var_en_var(json.dumps(valeur, ensure_ascii=False))
    valeur_retour = redis_var.lpos(cle_redis, val_redis)
    if valeur_retour:
        return json.loads(inverse_var(valeur_retour))
    
    return ""
    


def lpop_liste_redis(cle, redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    cle_redis = var_en_var(cle)
    valeur_retour = redis_var.lpop(cle_redis)
    if valeur_retour:
        return json.loads(inverse_var(valeur_retour))

    return ""
    

def lrem_liste_redis(cle, pos = 0, valeur = "", redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    val_redis = var_en_var(json.dumps(valeur, ensure_ascii=False))
    return redis_var.lrem(cle_redis, pos, val_redis)



def llen_liste_redis(cle, redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    return redis_var.llen(cle_redis)



# @trace
def incr_valeur_redis(cle, redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    return redis_var.incr(cle_redis)





# @trace
def decr_valeur_redis(cle, redis_var = None):
    redis_var = choisir_redis(nom_api = cle, redis_var = redis_var, build = True)
    
    cle_redis = var_en_var(cle)
    return redis_var.decr(cle_redis)

   
            

# @trace
def liste_env(cle = "arreter"):
    val1 = creer_liste_env(cle)
    if val1:
        return val1
    else:
        return recuperer_valeur_actuelle(cle)
        


standard_requests = requests.Session()
telegram_requests = requests.Session()

    


@app.route("/envoi", methods=['GET', 'POST'])
def envoi():
    try :
        data = request.get_json(force=True)
        nom = data.get("nom")
        body = data["html"]
        nomsite = data.get("site") or nom_site
        nouveau = data.get("nouveau")
        if not nom:
            nom = str(uuid.uuid4())
        elif str(nouveau)==str(True):
            test_nom = hget_dict_redis("html:par_defaut", nom, redis_var = "redis_base")
            if test_nom :
                id_auto = str(uuid.uuid4())
                nom = nom + id_auto
        hset_dict_redis("html:par_defaut", nom, body, redis_var = "redis_base")
        nom_encode = quote(nom, safe='')
        return Response(nomsite + "/html?nom=" + nom_encode, status=200)

    except Exception as e:
        return Response(f"Erreur lors du traitement de la requête !\n{e}", status=200)


@app.route("/html", methods=['GET', 'POST'])
def page_web_html():
    try :
        data = request.get_json(force=True)
        nom = data["nom"]
        page_html = hget_dict_redis("html:par_defaut", nom, redis_var = "redis_base")
        if page_html:
            return page_html
        else:
            return Response("Page web introuvable !", status=200)
            
    except Exception as e:
        return Response(f"Erreur lors du traitement de la requête !\n{e}", status=200)


    
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

 







