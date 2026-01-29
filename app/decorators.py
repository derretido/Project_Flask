from functools import wraps
from flask import request, jsonify,current_app
import jwt


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        token = None 
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"message":"Token Malformado"}),
        if not token:
            return jsonify({"error":"Token está faltando!"}),401
        
        try:
            data =  jwt.decode(token,current_app.config['SECRET_KEY'],algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({"Error":"Token expirado!"}),401
        except jwt.InvalidTokenError:
            return jsonify({"Error":"Token inválido!"}),401
        
        return f(data, *args, **kwargs)
    
    return decorated