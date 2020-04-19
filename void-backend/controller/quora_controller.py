from flask import Response, request
import json
import ast
from distutils.util import strtobool


from controller import app_controller
from service import quora_service

app = app_controller.app

base_url = '/quora'

@app.route(base_url+'/refreshQuestions', methods=['GET'])
def refresh_questions_data():
    return Response(json.dumps(quora_service.refresh_data('day', True)), status=200, mimetype='application/json')

@app.route(base_url+'/fillAllMissingDates', methods=['GET'])
def fill_all_missing_dates():
    return Response(json.dumps(quora_service.fill_missing_dates()), status=200, mimetype='application/json')

@app.route(base_url, methods=['DELETE'])
def delete_questions():
    return Response(json.dumps(quora_service.delete_questions(ast.literal_eval(request.args.get('questionIds')))), status=200, mimetype='application/json')

@app.route(base_url+'/evaluate', methods=['PUT'])
def mark_as_evaluated():
    return Response(json.dumps(quora_service.update_evaluated(ast.literal_eval(request.args.get('questionIds')), bool(strtobool(request.args.get('evaluated'))))), status=200, mimetype='application/json')

@app.route(base_url, methods=['GET'])
def get_questions():
    return Response(json.dumps(quora_service.get_questions(ast.literal_eval(request.args.get('divisions')), request.args.get('timePeriod'), bool(strtobool(request.args.get('evaluated'))), request.args.get('pageNumber'), request.args.get('pageSize'))), status=200, mimetype='application/json')

@app.route(base_url+'/refreshAccountsData', methods=['GET'])
def refresh_accounts_data():
    return Response(json.dumps(quora_service.refresh_accounts_data()), status=200, mimetype='application/json')

@app.route(base_url+'/refreshRequestedQuestions', methods=['GET'])
def refresh_requested_questions():
    return Response(json.dumps(quora_service.refresh_requested_questions()), status=200, mimetype='application/json')

@app.route(base_url, methods=['POST'])
def add_asked_question():
    print(request.json)
    return Response(json.dumps(quora_service.add_asked_question(request.json, request.args.get('account_id'))), status=200, mimetype='application/json')
