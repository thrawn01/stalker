from flask import Flask, request, abort, jsonify, render_template
from flask.ext.pymongo import PyMongo
import pymongo
from time import time
from random import choice

app = Flask(__name__, instance_relative_config=True)
app.config['MONGO_DBNAME'] = 'stalkerweb'
mongo = PyMongo(app)

REGISTER_KEY = 'itsamario'


def _rand_start():
    """Used to randomize the first check (and hopefully stagger
    checks on a single host)"""
    return time() + choice(xrange(300))


def _valid_registration(content):
    fields = [('hostname', basestring), ('checks', dict), ('roles', list)]
    for field in fields:
        if field[0] in content:
            if not isinstance(content[field[0]], field[1]):
                return False
        else:
            return False
    # validate checks each should have a interval and args field
    for check in content['checks']:
        if not isinstance(content['checks'][check], dict):
            return False
        if 'interval' not in content['checks'][check]:
            return False
        if not isinstance(content['checks'][check]['interval'], int):
            return False
        if 'args' not in content['checks'][check]:
            return False
        if not isinstance(content['checks'][check]['args'], basestring):
            return False
    # validate roles shoudl just be a list of strings
    for role in content['roles']:
        if not isinstance(role, basestring):
            return False
    # everything checked out
    return True


@app.route("/register", methods=['POST', 'PUT'])
def register():
    if request.headers.get('X-REGISTER-KEY') != REGISTER_KEY:
        abort(412)
    if not request.json:
        abort(400)
    if not _valid_registration(request.json):
        abort(400)
    hid = request.json['hostname']
    checks = request.json['checks']
    roles = request.json['roles']
    try:
        # TODO: need a unique constraint on hostname (or just do _id =
        # hostname)
        q = mongo.db.hosts.update({'hostname': hid},
                                  {"$set": {'hostname': hid,
                                            'ip': request.remote_addr,
                                            'checks': checks, 'roles': roles}},
                                  upsert=True)
        # TODO: Since this is just a POC we'll just blow away ALL of the
        # existing checks for the host and readd them.
        mongo.db.checks.remove({'hostname': hid})
        bulk_load = []
        for i in checks:
            bulk_load.append({'hostname': hid, 'ip': request.remote_addr,
                              'check': i, 'last': 0, 'next': _rand_start(),
                              'interval': checks[i]['interval'],
                              'pending': False,
                              'status': True, 'in_maintenance': False,
                              'suspended': False, 'out': ''})
        mongo.db.checks.insert(bulk_load)
    except pymongo.errors.DuplicateKeyError as err:
        print err
        abort(400)
    return jsonify({'status': 'ok'})


@app.route("/hosts/", defaults={'host': None})
@app.route("/hosts/<host>")
def hosts(host):
    if not host:
        q = [x for x in mongo.db.hosts.find(fields={'_id': False})]
        if q:
            q = {'hosts': q}
    else:
        q = mongo.db.hosts.find_one({'hostname': host}, fields={'_id': False})
    if q:
        return jsonify(q)
    else:
        abort(404)


@app.route("/checks/", defaults={'host': None})
@app.route("/checks/<host>")
def checks(host):
    if not host:
        q = [x for x in mongo.db.checks.find(fields={'_id': False})]
    else:
        q = [x for x in mongo.db.checks.find(
            {'hostname': host}, fields={'_id': False})]
    if q:
        return jsonify({'checks': q})
    else:
        abort(404)


@app.route('/checks/state/<state>')
def check_state(state):
    if state == 'alerting':
        q = [x for x in mongo.db.checks.find(
            {'status': False}, fields={'_id': False})]
        if q:
            return jsonify({'alerting': q})
        else:
            return jsonify({'alerting': []})
    elif state == 'pending':
        q = [x for x in mongo.db.checks.find(
            {'pending': True}, fields={'_id': False})]
        if q:
            return jsonify({'pending': q})
        else:
            return jsonify({'pending': []})
    elif state == 'maintenance':
        q = [x for x in mongo.db.checks.find(
            {'in_maintenance': True}, fields={'_id': False})]
        if q:
            return jsonify({'in_maintenance': q})
        else:
            return jsonify({'in_maintenance': []})
    else:
        abort(400)


@app.route('/findhost')
def findhost():
    """Just used for the type ahead"""
    # probably should cache hosts in memcached/redis for type ahead crap
    if not request.args.get('q'):
        abort(400)
    q = [x['hostname'] for x in mongo.db.hosts.find({'hostname': {'$regex': '^%s' % request.args.get('q')}}, fields={'hostname': True, '_id': False})]
    print q
    return ",".join(q)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/view/checks')
def view_checks():
    return render_template('allchecks.html')


@app.route('/view/hosts')
def view_hosts():
    return render_template('hosts.html')


@app.route("/view/host/", defaults={'hostname': None})
@app.route('/view/host/<hostname>')
def view_single_host(hostname):
    if request.args.get('search'):
        hostname = request.args.get('search')
    if not hostname:
        abort(404)
    else:
        return render_template('host.html', target=hostname)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    debug = True
    app.run(host='0.0.0.0', debug=debug)