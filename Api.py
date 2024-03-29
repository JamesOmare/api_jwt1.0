from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps


app = Flask(__name__)

app.config['SECRET_KEY'] = 'jisungparkfromspace'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://james:foxtrot09er@localhost/todos'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    public_id = db.Column(db.String(50), unique = True)
    name = db.Column(db.String(50))
    password = db.Column(db.String(80))
    admin = db.Column(db.Boolean)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    text = db.Column(db.String(80))
    complete = db.Column(db.Boolean)
    user_id = db.Column(db.Integer)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
            current_user = User.query.filter_by(public_id = data['public_id']).first()

        except:
            return jsonify({'message' : 'Token is invalid'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@app.route('/get_users', methods = ['GET'])
@token_required
def get_all_users(current_user):

    if not current_user.admin:
        return jsonify({'message' : 'The action required Admin access! Please contact the Admin '})

    users = User.query.all()

    output = []

    for user in users:
        user_data = {}
        user_data['public_id'] = user.public_id
        user_data['name'] = user.name
        user_data['password'] = user.password
        user_data['admin'] = user.admin
        output.append(user_data)

    return jsonify({'users': output})



@app.route('/get_user/<public_id>', methods = ['GET'])
@token_required
def get_user(current_user, public_id):

    if not current_user.admin:
        return jsonify({'message' : 'The action required Admin access! Please contact the Admin '})

    user = User.query.filter_by(public_id = public_id).first()

    if not user:
        return jsonify({'message': 'No user found'})

    user_data = {}
    user_data['public_id'] = user.public_id
    user_data['name'] = user.name
    user_data['password'] = user.password
    user_data['admin'] = user.admin


    return jsonify({'user': user_data})



@app.route('/create_user', methods = ['POST'])
@token_required
def create_user(current_user):

    if not current_user.admin:
        return jsonify({'message' : 'The action required Admin access! Please contact the Admin '})

    data = request.get_json()

    hashed_password = generate_password_hash(data['password'], method= 'md5')

    new_user = User(public_id = str(uuid.uuid4()), name = data['name'], password = hashed_password, admin = False)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message' : 'New user created!'})



@app.route('/promote_user/<public_id>', methods = ['PUT'])
@token_required
def promote_user(current_user, public_id):

    if not current_user.admin:
        return jsonify({'message' : 'The action required Admin access! Please contact the Admin '})

    user = User.query.filter_by(public_id = public_id).first()

    if not user:
        return jsonify({'message': 'No user found'})

    user.admin = True
    db.session.commit()

    return jsonify({'message' : 'The user has been promoted'})



@app.route('/delete_user/<public_id>', methods = ["DELETE"])
@token_required
def delete_user(current_user, public_id):

    if not current_user.admin:
        return jsonify({'message' : 'The action required Admin access! Please contact the Admin '})

    user = User.query.filter_by(public_id = public_id).first()

    if not user:
        return jsonify({'message': 'No user found!'})

    db.session.delete(user)
    db.session.commit()

    return jsonify({'message' : 'The user has been deleted!'})


@app.route('/get_todos', methods = ['GET'])
@token_required
def get_all_todos(current_user):

    todos = Todo.query.filter_by(user_id = current_user.id).all()

    if not todo:
        return jsonify({'message' : 'No todo found!'})

    output = []

    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['text'] = todo.text
        todo_data['complete'] = todo.complete

        output.append(todo_data)

    return jsonify({'todos' : output})



@app.route('/get_todo/<todo_id>', methods = ['GET'])
@token_required
def get_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id = todo_id, user_id = current_user.id).first()

    if not todo:
        return jsonify({'message' : 'No todo found!'})

    todo_data = {}
    todo_data['id'] = todo.id
    todo_data['text'] = todo.text
    todo_data['complete'] = todo.complete


    return jsonify(todo_data)



@app.route('/create_todo', methods = ['POST'])
@token_required
def create_todo(current_user):
    data = request.get_json()

    new_todo= Todo(text = data['text'], complete = False, user_id = current_user.id )
    db.session.add(new_todo)
    db.session.commit()

    return jsonify({'message' : 'Todo created!'})



@app.route('/complete_todo/<todo_id>', methods = ['PUT'])
@token_required
def upgrade_todo_rights(current_user, todo_id):
    todo = Todo.query.filter_by(id= todo_id, user_id = current_user.id).first()

    if not todo:
        return jsonify({'massage' : 'No todo found!'})

    todo.complete = True
    db.session.commit()

    return jsonify({'message' : 'Todo item has been completed!'})



@app.route('/delete_todo/<todo_id>', methods = ['DELETE'])
@token_required
def delete_todo(current_user, todo_id):
    todo = Todo.query.filter_by(id= todo_id, user_id = current_user.id).first()

    if not todo:
        return jsonify({'massage' : 'No todo found!'})

    db.session.delete(todo)
    db.session.commit()

    return jsonify({'message' : 'Todo item deleted!'})




@app.route('/login')
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('Missing information, could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    user = User.query.filter_by(name = auth.username).first()

    if not user:
        return make_response('Wrong  username or pasword, Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'public_id': user.public_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)}, app.config['SECRET_KEY'])

        return jsonify({'token' : token.decode('UTF-8')})

    return make_response('Wrong  username or pasword, Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})



if __name__ == '__main__':
    db.create_all()
    app.run(port= 5050, debug = True)