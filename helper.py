"""Contains helper functions to be used in server."""

from sqlalchemy.sql import *

from flask import (Flask, render_template, redirect, request, flash,
                   session)
from model import *

###################################################
# VALIDATION

def check_credentials(username, password):
    """Logic for checking login credentials."""

    user = User.query.filter(User.username == username).first()

    if user and user.password == password:

        session['user_id'] = user.user_id
        flash("Logged in.")

        return redirect('/')
    
    else:
        flash("Username/password combination not recognized.")
        return redirect('/login')

def process_registration(username, email, password):
    """Directs user trying to register, depending on user's input."""

    email_check = User.query.filter(User.email == email).first()
    username_check = User.query.filter(User.username == username).first()

    if email_check:
        flash("Sorry, that email is already in use.")
        return redirect('/register')

    elif username_check:
        flash("Sorry, that username is already in use.")
        return redirect('/register')

    else:
        create_user(username, email, password)

        flash("You've been registered. Game on!")
        return redirect('/login')


def check_login_status():
    """Checks to see if user is logged in."""

    if session.get('user_id'):
        user_id = session['user_id']

        return user_id

    else:
        return None


def check_tags(user_status):
    """Returns a user's tags."""

    if user_status:
        tags = Tag.query.filter(Tag.user_id == user_status).all()

        return tags

    else:
        return None


def check_vg_tags(game_id):
    """Returns a user's tags."""

    if game_id:
        user_id = session.get('user_id')

        user_query = VgTag.query.join(Tag).filter(Tag.user_id == user_id)  # Only display user's tags for a specific game.
        vg_tags = user_query.filter(VgTag.game_id == game_id).all()

        return vg_tags

    else:
        return None


def check_review_status(game):
    """Checks to see if user is logged in and if game has been reviewed before."""

    user_id = check_login_status()

    if user_id:
        review = Review.query.filter(Review.user_id == user_id, Review.game_id == game.game_id).first()
        return review

    else:
        review = None

        return review


def handle_review_status(game, user_status):
    """Checks if other users have reviewed the game the user is currently looking at."""

    if user_status:
        user_id = check_login_status()
        reviews = retrieve_game_reviews(user_id, game.game_id)

    else:
        reviews = None

    return reviews


###################################################
# UPDATING THE DATABASE

def create_user(username, email, password):
    """Takes info from '/register' and submits user to database."""
    new_user = User(username=username,
                    email=email,
                    password=password)

    db.session.add(new_user)
    db.session.commit()

def create_review(game_id, review, user_score):
    """Takes info from '/game/<title>' and submits review to database."""

    user_id = session['user_id']

    new_review = Review(user_id=user_id,
                        game_id=game_id,
                        user_score=user_score,
                        review=review)

    db.session.add(new_review)
    db.session.commit()


def create_tags(user_id, tags):
    """Adds a user's newly created tags in the database and returns that data as JSON."""

    # FIX ME: User can add multiples of the same text 
    # (i.e. two copies of "i love tags" with different IDs)

    tag_data = [] 

    for tag in tags:
        tag = tag.lower()
        tag = tag.lstrip()

        new_tag = Tag(user_id=user_id,
                      tag=tag)
        db.session.add(new_tag)
        db.session.commit()
        
        tag_data.append(
            {
            "tag_id": new_tag.tag_id,  # new_tag is an instance of Tag class, has .tag_id
            "user_id": user_id,
            "tag": tag
            }
        )

    return tag_data  # List of dictionaries


def create_vg_tags(game_id, tag_ids):
    """Adds a user's tags to a video game and returns that data as JSON."""

    vg_tag_data = []

    for tag_id in tag_ids:

        if VgTag.query.filter(VgTag.tag_id == tag_id, VgTag.game_id == game_id).first():
            pass
        
        else:
            new_vg_tag = VgTag(game_id=game_id,
                               tag_id=tag_id)
            db.session.add(new_vg_tag)
            db.session.commit()

            vg_tag_data.append(
                {
                "vg_tag_id": new_vg_tag.vg_tag_id,
                "game_id": game_id,
                "tag_id": tag_id,
                "tag": new_vg_tag.tag.tag
                }
            )
    
    return vg_tag_data

def update_review(game_id, review_text, user_score):
    """Takes info from '/game/<title>' and updates game's score."""

    user_id = session['user_id']

    review = Review.query.filter(Review.user_id == user_id, Review.game_id == game_id).one()

    review.review = review_text
    review.user_score = user_score

    db.session.commit()


def update_aggregate_score(game):
    """Update user score anytime a user adds or edits a review."""

    reviews = Review.query.filter(Review.game_id == game.game_id).all()

    user_scores = []

    for review in reviews:
        user_scores.append(review.user_score)

    aggregate_score = sum(user_scores) / len(user_scores)

    game.aggregate_score = aggregate_score

    db.session.commit()

    print "{title} now has a user score of {score}.".format(title=game.title,
                                                            score=game.aggregate_score)


def delete_tags(tag_ids):
    """Deletes user's tags."""

    user_id = session['user_id']

    # If the user deletes a tag from their profile page, 
    # we want to delete all the video-game tags associated with that tag_id, 
    # otherwise they get orphaned


    # Runtime is not ideal but wall time should be fine
    
    for tag_id in tag_ids:
        tag = Tag.query.filter(Tag.tag_id == tag_id, Tag.user_id == user_id).one()
        vg_tags = VgTag.query.filter(VgTag.tag_id == tag_id).all()
        
        for vg_tag in vg_tags:
            db.session.delete(vg_tag)
        
        db.session.delete(tag)

    db.session.commit()


def remove_vg_tags(game_id, vg_tag_ids):
    """Removes a user's tags from a game."""

    user_id = session['user_id']

    vg_tags = []

    for vg_tag_id in vg_tag_ids:
        vg_tag = VgTag.query.join(Tag).filter(VgTag.game_id == game_id, VgTag.vg_tag_id == vg_tag_id, Tag.user_id == user_id).one()
        vg_tags.append(vg_tag)
        db.session.delete(vg_tag)

    db.session.commit()


###################################################
# SEARCH FILTERING

def apply_filters(critic_score, aggregate_score, platform, specific_platform, genres):
    """Checks how to query database based on user's filters."""

    games = Game.query

    if critic_score:
        games = games.filter(Game.critic_score >= critic_score)

    if aggregate_score:
        games = games.filter(Game.aggregate_score >= aggregate_score)

    if specific_platform:
        games = games.filter(Game.platform == specific_platform)

    elif platform:
        games = games.filter(Game.platform.ilike('%' + platform + '%'))

    if genres:
        games = games.join(VgGen).filter(VgGen.genre_id.in_(genres))

    games = games.all()

    return games

###################################################
# QUERIES

def retrieve_user(user_id):
    """Gets user info from '/user/<user_id>'"""

    user = User.query.filter(User.user_id == user_id).one()

    return user


def retrieve_game(game_id):
    """Returns game object based on game's ID#."""

    game = Game.query.filter(Game.game_id == game_id).one()

    return game


def retrieve_user_reviews(user_id):

    query = Review.query.filter(Review.user_id == user_id)

    num_reviews = query.count()
    reviews = query.limit(15)

    return num_reviews, reviews


def retrieve_game_reviews(user_id, game_id):
    """Returns all reviews for a specific game from OTHER users."""

    reviews = Review.query.filter(Review.game_id == game_id, Review.user_id != user_id).limit(10).all()

    return reviews


def retrieve_genres(game_id):
    """Returns all the genres associated with a specific game."""

    vg_genres = VgGen.query.filter(VgGen.game_id == game_id).all()

    return vg_genres


def retrieve_title(title):  # Takes in request.args.get() value
    """Returns a query by title."""
    
    if title:
        title = Game.query.filter(Game.title.ilike('%' + title + '%')).all()
    
    return title

def retrieve_tagged_games(vg_tag):
    """Grabs all the games a user has tagged."""

    user_id = session['user_id']

    tagged_games = Game.query.join(VgTag).join(Tag).join(User).filter(Tag.tag == vg_tag.tag.tag, User.user_id == user_id).all()

    return tagged_games

def retrieve_all_tagged_games(vg_tags):
    """Accounts for multiple tags on a game profile page."""

    all_tagged_games = {}

    for vg_tag in vg_tags:
        games = retrieve_tagged_games(vg_tag)
        all_tagged_games[vg_tag] = games

    return all_tagged_games
