import os
import threading
import traceback
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


def _uid():
    return session.setdefault('uid', uuid.uuid4())


_progress_dict = {}
_stop_requests = set()


def _update_progress(uid, json):
    logger.debug(json);
    _progress_dict[uid] = json


def _analyze_thread(flow, uid):
    logger.debug('Analyzing...')
    try:
        result = flow.debug()
    except:
        tb = traceback.format_exc()
        json = {
            'status': 'error',
            'error': tb
        }
        logger.error('An error occurred', tb)
    else:
        logger.debug('Finished analysis')
        json = {
            'status': 'complete',
            'result': result,
        }
    _update_progress(uid, json)


def _analyze(flow):
    thread = threading.Thread(
        target=_analyze_thread, args=(flow, _uid()))
    thread.start()


def _optimize_thread(flow, inputs, outputs, uid):
    logger.debug('Optimizing...')
    class TerminateException(Exception):
        pass
    try:
        no_of_steps = steps(flow)
        class ProgressReportingDiscoverer(GreedyDiscoverer):
            def _execute(self, expr, state, out_vars, context=None):
                if uid in _stop_requests:
                    raise TerminateException
                results = super()._execute(expr, state, out_vars, context)
                json = {
                    'status': 'working',
                    'step': self.step_count,
                    'total': no_of_steps,
                }
                _update_progress(uid, json)
                return results
        result = ProgressReportingDiscoverer()(flow, inputs, outputs)
    except TerminateException:
        json = {
            'status': 'complete',
            'result': 'Stopped by user',
        }
        logger.debug('Stopped optimization')
    except:
        tb = traceback.format_exc()
        json = {
            'status': 'error',
            'error': tb
        }
        logger.error('An error occurred', tb)
    else:
        json = {
            'status': 'complete',
            'result':  '[' + '\n '.join(str(r) for r in result) + ']',
        }
        logger.debug('Finished optimization')
    _update_progress(uid, json)
    if uid in _stop_requests:
        _stop_requests.remove(uid)


def _optimize(flow):
    inputs = flow.inputs()
    outputs = flow.outputs()
    flow = flow_to_meta_state(flow)
    thread = threading.Thread(
        target=_optimize_thread, args=(flow, inputs, outputs, _uid()))
    thread.start()


@app.route("/progress")
def progress():
    default = {
        'status': 'ready',
    }
    return jsonify(_progress_dict.get(_uid(), default))


@app.route("/run", methods=['POST'])
def run():
    rv = jsonify({'success': True})
    uid = _uid
    if uid in _stop_requests:
        _stop_requests.remove(uid)
    req = request.get_json()
    action = req['action']
    code = req['code']
    json = {
        'action': action,
        'code': code,
    }
    try:
        flow = parse(code)
        json['status'] = 'starting'
        _update_progress(_uid(), json)
        if action == 'analyze':
            _analyze(flow)
            return rv
        if action == 'optimize':
            _optimize(flow)
            return rv
        json['error'] = 'Unrecognized action ' + action
    except Exception:
        json['error'] = tb = traceback.format_exc()
        logger.error('An error occurred', tb)
    json['status'] = 'error'
    return rv


@app.route("/stop")
def stop():
    uid = _uid()
    if _progress_dict[uid]['status'] == 'working':
        _stop_requests.add(uid)
        json = {'status': 'stopping'}
        _update_progress(uid, json)
    return jsonify({'success': True})


@app.route("/")
def index():
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
