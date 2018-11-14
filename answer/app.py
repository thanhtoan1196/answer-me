from flask import Flask, request, render_template, session
from flask_socketio import SocketIO
import random
import time

from answer import config
from answer.extensions import db
from answer.helpers import gen_response, require_admin
from answer.models import Player, Question
from answer.game import Game

# initialize app with config params
app = Flask(__name__)
app.config.from_object(config)
socketio = SocketIO(app)
game = Game('/game')
socketio.on_namespace(game)


# initialize connection to db
with app.app_context():
    # initialize connection to db
    db.init_app(app)


@app.route("/")
def index():
    """ Server index """
    return render_template("index.html")


@app.route("/tv")
@require_admin
def tv():
    """ TV index """
    return render_template("tv.html")


@app.route("/login", methods=['POST'])
def login():
    """ Login to obtain session cookie if available """
    # regular user
    if request.form.get('username') is not None:
        username = request.form.get('username')
        if Player.query.filter_by(player_name=username).first() is not None:
            session['username'] = username
            return gen_response({'success': True, 'username': username})
        else:
            return gen_response({'success': False})


@app.route("/logout", methods=["POST"])
def logout():
    session['username'] = None
    return gen_response({'success': True})


@app.route("/lee/admin")
def admin():
    """ Auto logs in as admin and gives control panel """
    return render_template("admin.html")


@app.route("/admin/register", methods=["POST"])
@require_admin
def register_players():
    """
    Registers the players to the database based on (SOME) as follows:

    [to be filled in]
    """
    # TODO: complete this function

    for name in ['choyin.yong', 'bowei.liu']:
        player = Player(player_name=name)
        # add player to database queue
        db.session.add(player)
    # commit everything to the database
    db.session.commit()


@app.route("/admin/import_questions", methods=["POST"])
@require_admin
def import_questions():
    """
    Imports the questions
    """
    # reset everything
    Question.query.delete()
    db.session.commit()

    questions_list = []

    # TODO: read some csv into list

    # shuffle order here
    random.shuffle(questions_list)

    # import into database for each
    for question_dict in questions_list:
        question_obj = Question(**question_dict)
        db.session.add(question_obj)
    db.session.commit()


@app.route("/admin/next_question", methods=['POST'])
@require_admin
def next_question():
    """
    Selects the next question in the database and broadcast it to all
    """
    question: Question = Question.query.filter_by(asked=False).first()
    if question:
        question_dict = question.get_dict()
        # a multiple choice question has been emitted
        game.emit("multiple_choice", question_dict)

        # reset starting time and players who answered the question
        game.starting_time = time.time()
        game.answered = set()

        # keep track of the question id in the game singleton
        game.correct_answer_idx = question_dict['answers'].index(question.correct_answer) + 1

        # the question is now asked and cannot be selected again
        question.asked = True
        db.session.add(question)
        db.session.commit()

        return gen_response({'success': True})
    else:
        return gen_response({'success': False})


@app.route("/admin/reset", methods=['POST'])
@require_admin
def reset_everyone():
    game.emit("logout_everyone")
    return gen_response({'success': True})


@app.route("/admin/bump_to_lobby", methods=['POST'])
@require_admin
def back_to_lobby():
    game.emit("lobby")
    return gen_response({'success': True})
