from flask import Flask, render_template, request, jsonify, abort
import subprocess
import requests
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPException
import os
import logging

app = Flask(__name__, template_folder='templates')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    logger.info("Rendering index.html")
    return render_template('index.html')

@app.route('/connect', methods=['POST'])
def connect():
    if not request.is_json:
        abort(400, description="Invalid or missing JSON")

    data = request.get_json()
    case = data.get('case')

    if case == 'ldap':
        return handle_ldap(data)
    elif case == 'database':
        return handle_database(data)
    elif case == 'webservice':
        return handle_webservice(data)
    else:
        abort(400, description="Invalid connection case")

def handle_ldap(data):
    try:
        host = data['host']
        port = int(data['port'])

        server = Server(host=host, port=port, use_ssl=False, get_info=ALL)
        conn = Connection(server)

        if not conn.bind():
            abort(500, description=f"LDAP bind failed: {conn.result}")
        return jsonify({"message": "Bind Successful", "details": conn.result})

    except LDAPException as e:
        abort(500, description=f"LDAP error: {str(e)}")
    except Exception as e:
        abort(500, description=f"Unexpected error: {str(e)}")

def run_java_jar(command_args):
    try:
        result = subprocess.run(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if result.returncode != 0:
            abort(500, description=result.stderr.strip())
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        abort(504, description="Java command timed out")
    except Exception as e:
        abort(500, description=f"Java execution error: {str(e)}")

def handle_database(data):
    try:
        args = [
            'java', '-cp', '/app/lib/sqlconnection.jar',
            'connectdb',
            data['host'], data['port'], data['database'],
            data['username'], data['password']
        ]
        output = run_java_jar(args)
        if 'Connection refused' in output:
            abort(500, description=output)
        return output
    except KeyError as e:
        abort(400, description=f"Missing required DB field: {str(e)}")

def handle_webservice(data):
    try:
        url = data['host']
        response = requests.get(url, timeout=5)
        return response.content
    except requests.exceptions.RequestException as e:
        abort(502, description=f"Web service error: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
