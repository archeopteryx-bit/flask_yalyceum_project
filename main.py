from flask import Flask, Response, render_template, redirect, request, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from data import db_session
from data.login_form import LoginForm
from data.register_form import RegisterForm
from data.edit_form import EditForm
from data.users import User
from data.graphics import Graphic
from data.audio import Audio
from data.writes import Write
from data.comments import Comment

from secret_key import SECRET_KEY


app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY


login_manager = LoginManager()
login_manager.init_app(app)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', form=form, message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', form=form, message="Такой пользователь уже есть")

        file = request.files['file']
        avatar_mt = file.mimetype
        avatar = file.read()

        user = User(name=form.name.data,
                    email=form.email.data,
                    about=form.about.data,
                    avatar=avatar,
                    avatar_mt=avatar_mt)
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', form=form)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/another')
def another():
    return render_template('second_page.html')


@app.route('/user<user_id>')
def profile(user_id):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == user_id).first()
    return render_template('profile.html',
                           name=user.name, id=user_id,
                           about=user.about,
                           user_id=int(user_id))


@app.route('/<user_id>_works')
def user_works(user_id):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == user_id).first()

    graphics = db_sess.query(Graphic).filter(Graphic.author_id == user_id)
    writes = db_sess.query(Write).filter(Write.author_id == user_id)
    audios = db_sess.query(Audio).filter(Audio.author_id == user_id)
    comments = db_sess.query(Comment).filter(Comment.author_id == user_id)

    return render_template('user_works.html', graphics=graphics, name=user.name,
                           writes=writes, audios=audios, comments=comments)


@app.route('/search', methods=['GET', 'POST'])
def search():
    db_sess = db_session.create_session()
    users = db_sess.query(User)
    if request.method == 'POST':
        param = request.form['param']
        users = db_sess.query(User).filter(User.name.like(f'%{param}%'))
        return render_template('search.html', users=users)
    return render_template('search.html', users=users)


@app.route('/avatar<id>')
def user_avatar(id):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == id).first()
    return Response(user.avatar, mimetype=user.avatar_mt)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        if user:
            form.name.data = user.name
            form.about.data = user.about
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        file = request.files['file']
        if user:
            if file:
                file_mt = file.mimetype
                image = file.read()

                user.avatar = image
                user.avatar_mt = file_mt
            user.name = form.name.data
            user.about = form.about.data
        db_sess.commit()
        return redirect('/')
    return render_template('edit_profile.html', form=form)


@app.route('/delete_user', methods=['GET', 'POST'])
@login_required
def del_user():
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == current_user.id).first()

    graph = db_sess.query(Graphic).filter(Graphic.author_id == current_user.id)
    write = db_sess.query(Write).filter(Write.author_id == current_user.id)
    aud = db_sess.query(Audio).filter(Audio.author_id == current_user.id)
    com = db_sess.query(Comment).filter(Comment.author_id == current_user.id)

    if user:
        if graph:
            for work in graph:
                db_sess.delete(work)
        if write:
            for work in write:
                db_sess.delete(work)
        if aud:
            for work in aud:
                db_sess.delete(work)
        if com:
            for work in com:
                db_sess.delete(work)

        db_sess.delete(user)
        db_sess.commit()
        logout()
    return redirect('/')


@app.route('/add_<type>_work', methods=['GET', 'POST'])
@login_required
def add_work(type):
    if request.method == 'POST':
        db_sess = db_session.create_session()
        if type == 'graphic':
            file = request.files['file']
            about = request.form['about']
            file_mt = file.mimetype
            image = file.read()

            work = Graphic(about=about,
                           image=image,
                           mimetype=file_mt,
                           author_id=current_user.id)
        elif type == 'write':
            title = request.form['title']
            text = request.form['text']

            work = Write(title=title,
                         text=text,
                         author_id=current_user.id)
        elif type == 'audio':
            file = request.files['file']
            about = request.form['about']
            file_mt = file.mimetype
            sound = file.read()

            work = Audio(about=about,
                         sound=sound,
                         mimetype=file_mt,
                         author_id=current_user.id)
        db_sess.add(work)
        db_sess.commit()
        return redirect('/')
    return render_template('add_work.html', type=type)


@app.route('/works_<type>')
def works_(type):
    db_sess = db_session.create_session()
    if type == 'graphic':
        works = db_sess.query(Graphic)
    elif type == 'write':
        works = db_sess.query(Write)
    elif type == 'audio':
        works = db_sess.query(Audio)
    authors = db_sess.query(User)
    return render_template('works.html', works=works, type=type,
                           authors=authors, name=username)


@app.route('/comments_<type>_<id>', methods=['GET', 'POST'])
def comments(type, id):
    db_sess = db_session.create_session()
    if request.method == 'POST' and current_user.is_authenticated:
        text = request.form['comment']

        com = Comment(comment=text, type=type, work_id=id,
                      author_id=current_user.id)
        db_sess.add(com)
        db_sess.commit()

    if type == 'graphic':
        work = db_sess.query(Graphic).filter(Graphic.id == id).first()
    elif type == 'write':
        work = db_sess.query(Write).filter(Write.id == id).first()
    elif type == 'audio':
        work = db_sess.query(Audio).filter(Audio.id == id).first()

    comment = db_sess.query(Comment).filter(Comment.type == type,
                                            Comment.work_id == id)
    return render_template('work_comment.html', type=type,
                           comment=comment, work=work,
                           name=username)


def username(id):
    db_sess = db_session.create_session()
    author = db_sess.query(User).filter(User.id == id).first()
    return author.name


@app.route('/graphic<id>')
def graphic(id):
    db_sess = db_session.create_session()
    graphic = db_sess.query(Graphic).filter(Graphic.id == id).first()
    return Response(graphic.image, mimetype=graphic.mimetype)


@app.route('/audio<id>')
def audio(id):
    db_sess = db_session.create_session()
    audio = db_sess.query(Audio).filter(Audio.id == id).first()
    return Response(audio.sound, mimetype=audio.mimetype)


@app.route('/delete_<type><id>', methods=['GET', 'POST'])
@login_required
def delete(type, id):
    db_sess = db_session.create_session()
    coms = None
    if type == 'graphic':
        work = db_sess.query(Graphic).filter(Graphic.id == id).first()
        coms = db_sess.query(Comment).filter(Comment.work_id == id)
    elif type == 'write':
        work = db_sess.query(Write).filter(Write.id == id).first()
        coms = db_sess.query(Comment).filter(Comment.work_id == id)
    elif type == 'audio':
        work = db_sess.query(Audio).filter(Audio.id == id).first()
        coms = db_sess.query(Comment).filter(Comment.work_id == id)
    elif type == 'comment':
        work = db_sess.query(Comment).filter(Comment.id == id).first()
    if work:
        if coms:
            for com in coms:
                db_sess.delete(com)
        db_sess.delete(work)
        db_sess.commit()
    return redirect('/')


@app.route('/salute')
def salute():
    return render_template('salute.html')


def main():
    db_session.global_init('db/blogs.sqlite')
    app.run()


if __name__ == '__main__':
    main()
