#!/usr/bin/env python3

from flask import Flask, make_response, jsonify, request, session
from flask_migrate import Migrate
from flask_restful import Api, Resource

from models import db, Article, User

# Import for seeding
from random import randint, choice as rc
from faker import Faker

fake = Faker()

app = Flask(__name__)
app.secret_key = b'Y\xf1Xz\x00\xad|eQ\x80t \xca\x1a\x10K'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False

migrate = Migrate(app, db)

db.init_app(app)

api = Api(app)

class ClearSession(Resource):

    def get(self):
        return self._clear_session()
    
    def delete(self):
        return self._clear_session()
    
    def _clear_session(self):
        session['page_views'] = None
        session['user_id'] = None

        # Seed database if empty
        if not User.query.first():
            print("Seeding database...")
            users = []
            usernames = []
            for i in range(25):
                username = fake.first_name()
                while username in usernames:
                    username = fake.first_name()
                usernames.append(username)
                user = User(username=username)
                users.append(user)
            db.session.add_all(users)
            db.session.commit()

            articles = []
            for i in range(100):
                content = fake.paragraph(nb_sentences=8)
                preview = content[:25] + '...'
                article = Article(
                    author=fake.name(),
                    title=fake.sentence(),
                    content=content,
                    preview=preview,
                    minutes_to_read=randint(1,20),
                    is_member_only=rc([True, False, False])
                )
                articles.append(article)
            db.session.add_all(articles)
            db.session.commit()
            print("Database seeded.")

        return {}, 204

class IndexArticle(Resource):
    
    def get(self):
        articles = [article.to_dict() for article in Article.query.all()]
        return make_response(jsonify(articles), 200)

class ShowArticle(Resource):

    def get(self, id):

        article = Article.query.filter(Article.id == id).first()
        article_json = article.to_dict()

        if not session.get('user_id'):
            session['page_views'] = 0 if not session.get('page_views') else session.get('page_views')
            session['page_views'] += 1

            if session['page_views'] <= 3:
                return article_json, 200

            return {'message': 'Maximum pageview limit reached'}, 401

        return article_json, 200

class Login(Resource):

    def post(self):
        
        username = request.get_json().get('username')
        user = User.query.filter(User.username == username).first()

        if user:
        
            session['user_id'] = user.id
            return user.to_dict(), 200

        return {}, 401

class Logout(Resource):

    def delete(self):

        session['user_id'] = None
        
        return {}, 204

class CheckSession(Resource):

    def get(self):
        
        user_id = session['user_id']
        if user_id:
            user = User.query.filter(User.id == user_id).first()
            return user.to_dict(), 200
        
        return {}, 401

class MemberOnlyIndex(Resource):
    
    def get(self):
        # Check if user is logged in
        if not session.get('user_id'):
            return {'error': 'Unauthorized'}, 401
        
        # Return only member-only articles
        articles = Article.query.filter(Article.is_member_only == True).all()
        return [article.to_dict() for article in articles], 200

class MemberOnlyArticle(Resource):
    
    def get(self, id):
        # Check if user is logged in
        if not session.get('user_id'):
            return {'error': 'Unauthorized'}, 401
        
        # Return the article
        article = Article.query.filter(Article.id == id).first()
        if article:
            return article.to_dict(), 200
        return {'error': 'Article not found'}, 404

api.add_resource(ClearSession, '/clear', endpoint='clear')
api.add_resource(IndexArticle, '/articles', endpoint='article_list')
api.add_resource(ShowArticle, '/articles/<int:id>', endpoint='show_article')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(MemberOnlyIndex, '/members_only_articles', endpoint='member_index')
api.add_resource(MemberOnlyArticle, '/members_only_articles/<int:id>', endpoint='member_article')


if __name__ == '__main__':
    app.run(port=5555, debug=True)
