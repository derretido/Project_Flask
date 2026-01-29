import re
from flask import Blueprint, jsonify, request, current_app
from app.models.user import LoginPayload
from pydantic import ValidationError
from app import db
from bson import ObjectId
from app.models.products import *
from app.models.sale import Sale
from app.decorators import token_required
from datetime import datetime, timedelta, timezone
import jwt
import csv
import os
import io


main_bp = Blueprint('main_bp',__name__)

# O sistema deve permitir que um usuario se autentique para obter um token
@main_bp.route('/login',methods=['POST'])
def login():
    try:
        raw_data = request.get_json()
        user_data = LoginPayload(**raw_data)

    except ValidationError as e:
        return jsonify({"errors":e.errors()}), 400 
    except Exception:
        return jsonify({"error":"Erro durante a requisição do dado ou não é um json valido"})
    
    if user_data.username == "admin" and user_data.password == "supersecret":
        token = jwt.encode(
        {
            "user_id": user_data.username,
            "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=30)
        },
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
        )
        return jsonify({"token":token}),200
    
    return jsonify({"messege":"Login invalido!"}),401


# O sistema deve permitir listagem de todos os produtos 
@main_bp.route('/products',methods=['GET'])
def get_products():
    products_cursor = db.products.find({})
    products_list = [productDBModel(**product).model_dump(by_alias=True,exclude_none=True) for product in products_cursor]
    return jsonify(products_list)

# O sistema deve permitir a criação de um novo produto
@main_bp.route('/products',methods=['POST'])
@token_required
def create_product(token):
    try:
        product = Product(**request.get_json())
    except ValidationError as e:
        return jsonify({"error":e.errors()})
    
    result = db.products.insert_one(product.model_dump())
    
    return jsonify({"message":"Criar um produto",
                    "id": str(result.inserted_id)}),201

# O sistema deve permitir a visualização dos detalhes de um unico produto
@main_bp.route('/product/<string:product_id>',methods=['GET'])
def get_product_by_id(product_id):
    try:
        oid = ObjectId(product_id)
    except Exception as e:
        return jsonify({"Erro": f"ao transformar o{product_id} em ObjectId {e}"})
    
    product = db.products.find_one({'_id':oid})
    if product:
        product_model = productDBModel(**product).model_dump(by_alias=True,exclude_none=True)
        return jsonify(product_model)
    else:
        return jsonify({"error":f"Produto com id{product_id}- Não encotrado"})

# O sistema deve permitir a atualização de um unico produto
@main_bp.route('/product/<string:product_id>',methods=['PUT'])
@token_required
def update_product(token,product_id):
    try:
        oid = ObjectId(product_id)
        update_data = UpdateProduct(**request.get_json())
    except ValidationError as e:
        return jsonify({"error":e.errors()})
    
    update_result = db.products.update_one(
        {"_id":oid},
        {"$set":update_data.model_dump(exclude_unset=True)}
    )

    if update_result.matched_count == 0:
        return jsonify({"error":"Produto não encontrado"}),404
    


    update_product = db.products.find_one({"_id":oid})
    return jsonify(productDBModel(**update_product).model_dump(by_alias=True,exclude=None))

# O sistema deve permitir a deleçao um unico produto e produto existente
@main_bp.route('/product/<string:product_id>',methods=['DELETE'])
@token_required
def delete_product(token,product_id):
    try:
        oid = ObjectId(product_id)
    except Exception:
        return jsonify({"Erro":"id do produto inválido"}),400
    
    delete_product = db.products.delete_one({'_id':oid})

    if delete_product.deleted_count ==0:
        return jsonify({"error":"Produto não encontrado"}),404

    return "",204

# O sistemas deve permitir a importacao de vendas atraves de um arquivo
@main_bp.route('/sales/update',methods=['POST'])
@token_required
def update_sales(token):
    if 'file' not in request.files:
        return jsonify({"error":"Nenhum arquivo enviado"}),400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error":"Nenhum arquivo selecionado"}),400
    
    if file and file.filename.endswith('.csv'):
        csv_stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        #faz a trasferencia para dicionario
        csv_reader = csv.DictReader(csv_stream)


        sales_to_insert = []
        error = []

        for row_num, row in enumerate (csv_reader,1):
            try:
                sale_data = Sale(**row)

                sales_to_insert.append(sale_data.model_dump(mode='json'))
            except ValidationError as e:
                error.append(f'Linha {row_num}com dados inválidos:')
            except Exception:
                error.append(f'Linha {row_num} com erro desconhecido.')

        if sales_to_insert:
            try:
                db.sales.insert_many(sales_to_insert)
            except Exception as e:
                return jsonify({"error": f'{e}'}),500
        return jsonify({
            "message" : "Upload concluído",
            "vendas importadas": len(sales_to_insert),
            "error encontrados": error
        }),200




    return jsonify({"message":"Esta é a rota de upload do arquivos de vendas"})


@main_bp.route('/')
def index():
    return jsonify({"message":"Bem vindo ao Advenge!"})
