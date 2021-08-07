import json
from flask import Flask
from flask_restful import Resource, Api
from flask import jsonify
from flask import request
import bugs_integration

app = Flask(__name__)
api = Api(app)

class ElkLogController(Resource):

    @app.route('/', methods=['GET'])
    def status():
        """get service health check status."""
        app.logger.info('App status is fire !')
        return {'status': 'Health'}

    @app.route('/open-bugs', methods=['POST'])
    def open_bugs():
        """open bugs based on logs."""

        app.logger.info('Open bugs is fire !')
        try:
            bugs_integration.start()
            return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

        except Exception as ex:
            app.logger.error(str(ex))
            return json.dumps({'success': False, 'message': str(ex)}), 500, {'ContentType': 'application/json'}

api.add_resource(ElkLogController, '/')

if __name__ == '__main__':
    app.run(debug=True)
