import os
import threading
import uuid

from akpytemp.utils import code_gobble
import jinja2
import flask
from flask import request, session, jsonify

import soap
from soap import logger
from soap.context import context
from soap.parser.program import parse
from soap.semantics import flow_to_meta_state
from soap.transformer.discover import GreedyDiscoverer, steps


directory = os.path.dirname(__file__)
app = flask.Flask(
    soap.__name__, static_folder=os.path.join(directory, 'templates/static'))
app.jinja_loader = jinja2.FileSystemLoader(
    os.path.join(directory, 'templates'))
app.secret_key = os.urandom(24)

_progress_dict = {}


def _analyze(flow):
    return flow.debug()


def _step_callback(uid, json):
    _progress_dict[uid] = json


def _greedy(flow, inputs, outputs, uid):
    logger.debug('Optimizing...')
    no_of_steps = steps(flow)

    class ProgressReportingDiscoverer(GreedyDiscoverer):
        def _execute(self, expr, state, out_vars, context=None):
            results = super()._execute(expr, state, out_vars, context)
            json = {
                'status': 'working',
                'step': self.step_count,
                'total': no_of_steps,
            }
            _step_callback(uid, json)
            return results

    try:
        result = ProgressReportingDiscoverer()(flow, inputs, outputs)
    except Exception as e:
        json = {
            'status': 'error',
            'error': str(e),
        }
    else:
        json = {
            'status': 'complete',
            'result':  '[' + '\n '.join(str(r) for r in result) + ']',
        }
    _step_callback(uid, json)
    logger.debug('Finished optimization')


def _optimize(flow):
    inputs = flow.inputs()
    outputs = flow.outputs()
    flow = flow_to_meta_state(flow)
    thread = threading.Thread(
        target=_greedy, args=(flow, inputs, outputs, session['uid']))
    thread.start()


@app.route("/progress")
def progress():
    default = {
        'status': 'ready',
    }
    return jsonify(_progress_dict.get(session['uid'], default))


@app.route("/run", methods=['POST'])
def run():
    req = request.get_json()
    action = req['action']
    code = req['code']
    json = {
        'action': action,
        'code': code,
    }
    try:
        flow = parse(code)
        if action == 'analyze':
            rv = _analyze(flow)
            json['status'] = 'complete'
            json['result'] = rv
        elif action == 'optimize':
            _optimize(flow)
            json['status'] = 'starting'
        else:
            json['status'] = 'error'
            json['error'] = 'Do not recognize action ' + action
    except Exception as e:
        json['status'] = 'error'
        json['error'] = '{}: {}'.format(e.__class__.__name__, e)
    _step_callback(session['uid'], json)
    return jsonify({'success': True})


@app.route("/")
def index():
    if 'uid' not in session:
        session['uid'] = uuid.uuid4()
    program = code_gobble(
        """
        input (
            a: [1.0, 2.0][0, 0],
            b: [10.0, 20.0][0, 0],
            c: [100.0, 200.0][0, 0]
        );
        output (x);
        x := (a + b) * c;
        """)
    return flask.render_template('index.html', soap=soap, program=program)


def main():
    debug = context.logger.level == soap.logger.levels.debug
    return app.run(port=context.port, debug=debug)
