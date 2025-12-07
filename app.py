from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import os
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-secret-for-local")
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///blog.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)

    posts = db.relationship("Post", backref="author", lazy=True, cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="author", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    comments = db.relationship("Comment", backref="post", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Post {self.title}>"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)

    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    def __repr__(self):
        return f"<Comment {self.id} on post {self.post_id}>"

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    post_count = Post.query.count()
    user_count = User.query.count()
    comment_count = Comment.query.count()
    return render_template("index.html",
                           post_count=post_count,
                           user_count=user_count,
                           comment_count=comment_count)


@app.route("/analytics")
def analytics():
    post_count = Post.query.count()
    user_count = User.query.count()
    comment_count = Comment.query.count()
    return render_template("analytics.html",
                           post_count=post_count,
                           user_count=user_count,
                           comment_count=comment_count)

@app.route("/users")
def users_list():
    users = User.query.order_by(User.username).all()
    return render_template("user_list.html", users=users)

@app.route("/users/new", methods=["GET", "POST"])
def new_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            flash("Username is required", "error")
            return redirect(url_for("new_user"))
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
            return redirect(url_for("new_user"))

        u = User(username=username)
        db.session.add(u)
        db.session.commit()
        flash(f"Created user {username}", "success")
        return redirect(url_for("users_list"))
    return render_template("new_user.html")

@app.route("/posts")
def posts_list():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template("post_list.html", posts=posts)

@app.route("/posts/new", methods=["GET", "POST"])
def new_post():
    users = User.query.order_by(User.username).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        user_id = request.form.get("user_id") or None

        if not title or not content:
            flash("Title and content are required", "error")
            return redirect(url_for("new_post"))

        post = Post(title=title, content=content, user_id=user_id)
        db.session.add(post)
        db.session.commit()
        flash("Post created", "success")
        return redirect(url_for("posts_list"))

    return render_template("new_post.html", users=users)

@app.route("/posts/<int:post_id>")
def post_details(post_id):
    post = Post.query.get_or_404(post_id)
    users = User.query.order_by(User.username).all()
    return render_template("post_details.html", post=post, users=users)

@app.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    users = User.query.order_by(User.username).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        user_id = request.form.get("user_id") or None

        if not title or not content:
            flash("Title and content are required", "error")
            return redirect(url_for("edit_post", post_id=post_id))

        post.title = title
        post.content = content
        post.user_id = user_id
        db.session.commit()
        flash("Post updated", "success")
        return redirect(url_for("post_details", post_id=post.id))

    return render_template("edit_post.html", post=post, users=users)

@app.route("/posts/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted", "success")
    return redirect(url_for("posts_list"))

@app.route("/posts/<int:post_id>/comment", methods=["POST"])
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    body = request.form.get("body", "").strip()
    user_id = request.form.get("user_id") or None

    if not body:
        flash("Comment cannot be empty", "error")
        return redirect(url_for("post_details", post_id=post_id))

    comment = Comment(body=body, post_id=post.id, user_id=user_id)
    db.session.add(comment)
    db.session.commit()
    flash("Comment added", "success")
    return redirect(url_for("post_details", post_id=post_id))

@app.route("/_seed_sample_data")
def seed_sample_data():
    if User.query.first():
        flash("DB already has data, skipping seed.", "info")
        return redirect(url_for("index"))

    u1 = User(username="Kaden")
    u2 = User(username=" Ben")
    db.session.add_all([u1, u2])
    db.session.commit()

    p1 = Post(title="Welcome to Ben's blog site", content="This is the first post.", user_id=u2.id)
    p2 = Post(title="About the project", content="This project is built with Flask.", user_id=u1.id)
    db.session.add_all([p1, p2])
    db.session.commit()

    c1 = Comment(body="Nice work!", post_id=p1.id, user_id=u1.id)
    db.session.add(c1)
    db.session.commit()

    flash("Sample data created", "success")
    return redirect(url_for("index"))

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)


@app.route("/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    Post.query.filter_by(user_id=user.id).delete()
    Comment.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash("User deleted", "success")
    return redirect(url_for("users_list"))



