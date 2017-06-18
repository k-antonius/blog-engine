'''
Created on Jun 12, 2017
@author: kennethalamantia

This module contains the ndb model classes used in the blog application.
'''

from google.appengine.ext import ndb
from blog_utilities import PwdUtil
import blog_handler as bh

class User(ndb.Model):
    '''NDB class representity a user entity.
    This is a root entity. Its direct child is a BlogPost.
    Attributes:
        user_name - the str user name, also this entity's key
        password - hashed and salted password
        email - user's email address
        date_created - date this user joined the blog
        posts_made - the cumulative number of posts this user has made
        cur_num_posts - the current number of existing posts of this user;
                        does not count deleted posts
    '''

    user_name = ndb.StringProperty(required=True)
    password = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    posts_made = ndb.IntegerProperty()
    cur_num_posts = ndb.IntegerProperty()

    @classmethod
    def create_new_user(cls, form_data):
        '''Creates a new user account in the database.
        @param form_data: dict holding username, password, and email address
        @return NDB key of this user
        '''
        if not cls.already_exists(form_data.get(bh.USER)):
            secured_pwd = cls._secure_password(form_data.get(bh.PASSWORD))
            new_user = User(user_name=form_data.get(bh.USER),
                            password=secured_pwd,
                            email=form_data.get(bh.EMAIL),
                            id=form_data.get(bh.USER),
                            posts_made=0,
                            cur_num_posts=0)
            new_user_key = new_user.put()
            return new_user_key

    @classmethod
    def already_exists(cls, user_name):
        '''Checks the database to see whether the user exists.
        @param user_name: the user_name to check
        @return: the user entity or None if no such user exists
        '''
        if user_name:
            return cls.get_by_id(user_name)
        else:
            return None

    @classmethod
    def incr_posts_made(cls, user_name):
        '''Increment the total number of posts made and the current number of
        posts outstanding for this user.
        @param user_name: the string id key for this user entity
        @return: the total number of posts this user has ever made
        '''
        user_key = ndb.Key("User", user_name)
        user = user_key.get()
        user.posts_made += 1
        user.cur_num_posts += 1
        user.put()
        return user.posts_made

#     @classmethod
#     def get_num_posts(cls, user_name):
#         '''Given the key id of this user, returns the number of posts this user
#         has made.
#         '''
#         user_key = ndb.Key("User", user_name)
#         user = user_key.get()
#         return user.posts_made

    @classmethod
    def _secure_password(cls, clear_text):
        '''Hash and salt password for storing in database.
        @param clear_text: the clear-text password to make secure
        @return a hashed password
        '''
        pwd_helper = PwdUtil(clear_text)
        return pwd_helper.new_pwd_salt_pair()


class BlogPost(ndb.Model):
    '''NDB class representing a single blog post.
    Parent is the user-author of the post. It's direct children are comment
    entities.
    Attributes:
        post_subject: subject of the post
        post_content: the context of a post
        post_author: the User entity who authored the post, i.e. this entity's
                     parent.
        post_number: number unique to this post, n, where n equals the nth
                     post a user has made
        date_created: the date/time of the post's create
        comments_made: the cumulative total of comments made on this post,
                       including deleted comments
        cur_num_comments: number of current comments on this post, not
                          including deleted comments
    '''

    post_subject = ndb.StringProperty(required=True)
    post_content = ndb.TextProperty(required=True)
    post_author = ndb.StringProperty(required=True)
    post_number = ndb.StringProperty()
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    users_liked = ndb.StringProperty(repeated=True)
    comments_made = ndb.IntegerProperty()
    cur_num_comments = ndb.IntegerProperty()

    @classmethod
    def create_new_post(cls, user_name, form_data):
        '''Creates a new post in the database, setting its subject, content,
        and author.
        @param user_name: the user name of the post's author
        @param form_data: dict containing the subject and content of the post,
        keyed to global constants
        @return: an NDB BlogPost entity
        '''

        post_number = str(User.incr_posts_made(user_name))
        new_post = BlogPost(post_subject=form_data.get(bh.SUBJECT),
                            post_content=form_data.get(bh.CONTENT),
                            post_author=user_name,
                            parent=ndb.Key("User", user_name))
        new_post.post_number = post_number
        new_post.key = ndb.Key("User", user_name, "BlogPost", post_number)
        new_post.users_liked = []
        new_post.comments_made = 0
        new_post.cur_num_comments = 0
        new_post_key = new_post.put()

        return new_post_key

    @classmethod
    def incr_comments_made(cls, post_entity):
        '''Increments both the total number of comments made to date on and the
        number of comments currently outstanding.
        @param post_entity: the BlogPost entity to be updated.
        @return: the total number of comments made.
        '''
        post_entity.comments_made += 1
        post_entity.cur_num_comments += 1
        post_entity.put()
        return post_entity.comments_made

    @classmethod
    def incr_cur_num_comments(cls, post_entity):
        '''Increment the current number of comments on this post.
        @param post_entity: the BlogPost entity to be updated.
        '''
        post_entity.cur_num_comments += 1
        post_entity.put()
        return post_entity.cur_num_comments

    @classmethod
    def add_like_unlike(cls, post_entity, user_name, like_status):
        '''Add or remove a user from users_liked list.
        @param post_entity: BlogPost entity being updated
        @param user_name: the user liking/unliking the post
        @param like_status: current str value of the like button
        '''
        if like_status == "Like":
            post_entity.users_liked.append(user_name)
        else:
            post_entity.users_liked.remove(user_name)
        post_entity.put()

    @classmethod
    def already_liked(cls, post_entity, user_name):
        '''Has a given user has liked a blog post?
        @param post_entity: the BlogPost entity check
        @param user_name: the user name of the user to check
        @return: boolean
        '''
        result = user_name in post_entity.users_liked
        return result

    @classmethod
    def get_all_comments(cls, post_entity):
        '''Returns a list of all the comments for a given post.
        @param post_entity: the blog post entity to retreive comments for
        @return: a list of Comment entities
        '''
        comments_query = Comment.query(ancestor=post_entity.key)
        all_comments = comments_query.order(-Comment.date_created).fetch()
        return all_comments

    @classmethod
    def most_recent_20(cls):
        '''Returns up to the most recent 20 blog posts in descending order of
        date created.
        '''
        posts_query = cls.query()
        recent_posts = posts_query.order(-cls.date_created).fetch(20)
        return recent_posts

    @classmethod
    def update_post(cls, post_entity, form_data):
        '''Updates the subject and content of a post upon editing.
        @param post_entity: the post entity to be updated
        @parm form_data: dict keyed to global constants containing edited
              subject and content strs.
        @return: updated BlogPost entity
        '''
        post_entity.post_subject = form_data[bh.SUBJECT]
        post_entity.post_content = form_data[bh.CONTENT]
        post_entity.put()
        return post_entity

    @classmethod
    def delete_post(cls, post_entity):
        '''Deletes this post entity and decrement the current number of posts
        outstanding for the post's author.
        @param post_entity: the NDB entity BlogPost to be deleted
        '''
        user_entity = ndb.Key("User", post_entity.post_author).get()
        user_entity.cur_num_posts -= 1
        assert user_entity.cur_num_posts >= 0, "Num posts can't be < 0."
        post_entity.key.delete()
        user_entity.put()

class Comment(ndb.Model):
    '''NDB entity model representing a comment made on a blog post.
    Parent is a BlogPost entity.
    Attributes:
        content: the text of a comment
        date_created: the date the comment was created
        author: the user name of the user who authored the comment
    '''

    content = ndb.TextProperty(required=True)
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    author = ndb.StringProperty(required=True)

    @classmethod
    def create_new_comment(cls, user_name, url_string, form_data):
        '''Creates a new comment entity in the database.
        @param user_name: the user name of the author of this comment
        @param url_string: the url key of the parent BlogPost entity
        @param form_data: dict keyed to global constant containing the
        content of this comment
        '''
        parent_key = ndb.Key(urlsafe=url_string)
        parent_post = parent_key.get()
        new_comment = Comment(content=form_data.get(bh.CONTENT),
                              author=user_name,
                              parent=parent_key)
        comment_num = BlogPost.incr_comments_made(parent_post)
        new_comment.key = ndb.Key("Comment", str(comment_num),
                                  parent=parent_key)
        new_comment.put()
        return new_comment.key

    @classmethod
    def get_comment_key(cls, comment_num, post_key):
        '''Returns the a comment entity's key.
        @param comment_num: unique string number of this coment
        @param post_key: the key of the BlogPost parent of this comment
        '''
        return ndb.Key("Comment", str(comment_num), parent=post_key)

    @classmethod
    def entity_from_uri(cls, comment_uri_key):
        '''Returns the comment entity.
        @param comment_uri_key: the url safe key string
        '''
        try:
            return ndb.Key(urlsafe=comment_uri_key).get()
        except:
            return None

    @classmethod
    def update_comment(cls, comment_entity, form_data):
        '''Updates the content field of a Comment.
        @param comment_entity: the comment to update
        @param form_data: dict keyed to global constant containing updated
        content.
        '''
        comment_entity.content = form_data[bh.CONTENT]
        comment_entity.put()
        return comment_entity

    @classmethod
    def delete_comment(cls, comment_entity):
        '''
        Deletes the comment and decrements the number of comments currently
        outstanding for its parent post.
        '''
        parent_post = comment_entity.key.parent().get()
        parent_post.cur_num_comments -= 1
        assert parent_post.cur_num_comments >= 0, "Num comments can't be < 0."
        comment_entity.key.delete()
        parent_post.put()
