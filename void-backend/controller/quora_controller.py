from flask import Response, request
import json
import ast
from distutils.util import strtobool


from controller import app_controller
from service import quora_service

app = app_controller.app

base_url = '/quora'

@app.route(base_url+'/refresh', methods=['GET'])
def test():
    return Response(json.dumps(quora_service.refresh_data('day')), status=200, mimetype='application/json')

@app.route(base_url+'/1')
def test1():
    return Response(json.dumps(quora_service.fill_missing_dates()), status=200, mimetype='application/json')

@app.route(base_url+'/test', methods=['GET'])
def test2():
    return Response({'5':'5'}, status=200, mimetype='application/json')

@app.route(base_url+'/delete')
def test3():
    return Response(json.dumps(quora_service.delete_questions([65, 66])), status=200, mimetype='application/json')

@app.route(base_url+'/update')
def test4():
    return Response(json.dumps(quora_service.update_evaluated([65, 66], False)), status=200, mimetype='application/json')

@app.route(base_url, methods=['GET'])
def test5():
    return Response(json.dumps(quora_service.get_questions(ast.literal_eval(request.args.get('divisions')), request.args.get('timePeriod'), bool(strtobool(request.args.get('evaluated'))), request.args.get('pageNumber'), request.args.get('pageSize'))), status=200, mimetype='application/json')
