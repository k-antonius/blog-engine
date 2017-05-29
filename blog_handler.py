'''
Classes that implement the a blog-engine running on google appengine and the
google cloud datastore.

Dependencies:
webapp2
jinja2
blog_utilities module provided with this module

Created on Jan 7, 2017
@author: kennethalamantia
'''


# imports
import os
import re
from functools import wraps
import jinja2
import webapp2
from webapp2_extras import routes
from google.appengine.ext import ndb
from blog_utilities import CookieUtil, PwdUtil
from google.appengine.ext.datastore_admin.config import current


# Template constants
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
                           extensions=['jinja2.ext.autoescape'],
                           autoescape=True)


# HTML Filenames
MAIN_PAGE_TEMPLATE = "blog.html"
NEW_POST_TEMPLATE = "newpost.html"
POST_ONLY_TEMPLATE = "new_post_base.html"
POST_WITH_COMMENTS = "new_post_with_comments.html"
SIGNUP_TEMPLATE = "signup_page.html"
WELCOME_TEMPLATE = "welcome.html"
LOGIN_TEMPLATE = "login_page.html"
COMMENT_TEMPLATE = "new_comment.html"


# URI Routes
HOME = "home"
NEW_POST = "new_post"
SIGNUP = "signup"
WELCOME = "welcome"
LOGIN = "login"
LOGOUT = "logout"
DISPLAY_POST = "display_post"
NEW_COMMENT = "new_comment"
EDIT_COMMENT = "edit_comment"
EDIT_POST = "edit_post"
LIKE_POST = "like_post"

# Form Input Fields
USER = "username"
PASSWORD = "password"
PWD_VERIFY = "pwd_verify"
EMAIL = "email"
SUBJECT = "subject"
CONTENT = "content"
ERROR = "_error"
EDIT = "edit"
COMMENT = "comment"
DELETE = "delete"
POST = "post"
LIKE = "like"
LIKE_TEXT = "like_text"

# Errors
LOGIN_ERROR = "login_error"
OWN_POST = "own_post"
NOT_AUTHOR = "not_author"


# Button Names
BUTTONS = ("edit_comment", "delete_comment", "edit_post",
           "delete_post", "like_post", "comment_post")


class Handler(webapp2.RequestHandler):
    '''Parent class of all request handlers. Provides a rendering convenience
    function used in all child classes.
    '''

    def render(self, template, **template_fields):
        '''Prepares a template for rendering and renders the template. Updates
        the template fields dict with a boolean for whether a user is logged in
        used with rendering the menu bar on all pages.
        @param template: the template html
        @param template_fields: dictionary of arguments where keys match
        template variables and values are the strings to render in place of
        those variables.
        '''

        template_fields.update(dict(
            logged_in=CookieUtil.get_cookie(USER, self)))

        def _render_template():
            '''Helper function to load and render template.
            '''
            template_to_render = JINJA.get_template(template)
            return template_to_render.render(template_fields)

        self.response.out.write(_render_template())
        
    
            
def check_logged_in(handler_fun):
    '''Decorator that checks if a user is logged in and redirects to the 
    signup handler if a user is not.
    @param handler_fun: the handler function to be wrapped
    '''
    
    @wraps(handler_fun)
    def wrapper(self, *args, **kwargs):
        post_key = self.request.route_args[0]
        helper = HandlerHelper(self, [], post_key)
        if not helper.is_logged_in:
            self.redirect(self.uri_for(SIGNUP, LOGIN_ERROR))
        else:
            handler_fun(self, *args, **kwargs)
    return wrapper

def check_not_author(handler_fun):
    '''Decorator to check that the current user is not the author of the
    post or comment entity being accessed.
    @param handler_fun: the handler function to be wrapped
    '''
    
    @wraps(handler_fun)
    def wrapper(self, *args, **kwargs):
        post_key = args[0]
        helper = HandlerHelper(self, [], post_key)
        if helper._is_cur_user_author():
            self.redirect(self.uri_for(DISPLAY_POST, post_key, OWN_POST))
        else:
            handler_fun(self, *args, **kwargs)
        return wrapper


class HandlerHelper(object):
    '''A class that aggregates data about the state of a request handler
    and performs validation and parsing actions on that state. Makes the data
    available for use in templates.
    Attributes:
        handler: the Webapp2 request handler
        is_logged_in: boolean value, true if a login cookie is set
        cur_user: the str user name of a logged in user, if any
        cur_post: the blog post database object relevant to the current page
        cur_comment: the comment database object relevant to the current page
        data_error_msgs: dict of error msgs generated from bad text form input
        valid_data: dict holding data to be rendered to a template
        is_data_valid: boolean, true if text input was valid
        button_subj = the str subject of a POST request, a blog post, comment etc.
        button_action = the str action type of a POST request, edit, delete etc.
    '''

    def __init__(self, handler, field_list, post_id=None):
        self.handler = handler
        self.is_logged_in = self._logged_in()
        self.cur_user = self._logged_in_user()
        self.cur_post = self._get_cur_post(post_id)
        self.cur_comment = None
        self.data_error_msgs = None
        self.valid_data = {}
        self.is_data_valid = False
        self._validate_user_input(field_list)
        self.button_subj = None
        self.button_action = None
        self.error_type = None

    def set_template_field(self, key, value):
        '''Include text for rendering in html template in the valid data dict.
        @param: key - str form field name constant, defined globally
        @param: value - str to render in template
        '''
        self.valid_data[key] = value

    def _logged_in(self):
        '''Returns true if a cookie is set for a logged in user.
        '''
        # this if...else is necessary; get_cookie does not return a boolean
        if CookieUtil.get_cookie(USER, self.handler):
            return True
        else:
            return False

    def _logged_in_user(self):
        '''Returns the str user name of user currently logged in.
        '''
        return CookieUtil.get_cookie(USER, self.handler)

    def _get_cur_post(self, key_from_url):
        '''Returns a blog post ENTITY from url-safe string.
        @param key_from_url: the url-safe key string for a BlogPost
        '''
        if key_from_url:
            return ndb.Key(urlsafe=key_from_url).get()

    def _validate_user_input(self, field_list):
        '''Validate text input into html form using FormHelper class.
        Sets data_error_msgs, is_data_valid, and valid_data class
        attributes accordingly.
        @param field_list: list of template form field names to process. Refer
        to declared global constants for options.
        '''
        form_helper = FormHelper(self.handler)
        form_data = form_helper.validate_form_data(field_list)
        if not form_helper.valid_input:
            self.data_error_msgs = form_data
            self.is_data_valid = False
        else:
            self.valid_data = form_data
            self.is_data_valid = True

    def login_user(self):
        '''Sets a cookie for the user name contained in the valid-data dict.
        '''
        assert self.valid_data.get(USER)
        CookieUtil.set_cookie(USER, self.valid_data.get(USER), self.handler)

    def validate_form_input(self, template, **additional_elements):
        '''Checks the data input into the form for validity based on rules defined
        in the Form Helper class. Re-renders the form with error messages using
        the provided template.
        @param template: template to render - global constant
        @param additional_elements: if the template requires non-form input
        to render correctly, must pass these elements to the template.
        '''
        if not self.is_data_valid:
            self.data_error_msgs.update(additional_elements)
            self.handler.render(template, **self.data_error_msgs)

    def _find_author(self):
        '''Gets the author of a post or comment.
        '''
        if self.button_subj == COMMENT:
            return self.cur_comment.author
        else:
            return self.cur_post.post_author

    def _is_cur_user_author(self):
        return self.cur_user == self._find_author()

    def detect_user_id_error(self):
        '''Returns boolean value based on whether an error condition exists.
        Errors: Users cannot like own posts, users can only edit and delete
        their own posts and comments.
        '''
        if self.button_action == LIKE:
            return self._is_cur_user_author()
        # users can comment on anyone's posts including their own
        elif self.button_action == COMMENT:
            return False
        else:
            return not self._is_cur_user_author()

    def gen_error_msg(self):
        '''Generates an error message for button inputs.
        Args come from button value in POST request. This method should be
        called after determining an error exists on a POST request from a
        button form---it will generate error messages and store them in the
        valid data dict for rendering to the template.
        '''
        base_template = "You {status} to {action} a {postORcomm}"
        not_logged_in = "must be logged in"
        not_own_post = "must be a {postORcomm}'s author"
        like_own_post = "can't be a {postORcomm}'s author"

        def _choose_error():
            '''Selects the correct error message.
            '''
            if  not self.is_logged_in:
                return not_logged_in
            elif self.button_action == LIKE:
                return like_own_post.format(postORcomm=self.button_subj)
            else:
                return not_own_post.format(postORcomm=self.button_subj)

        def _choose_action():
            '''Selects a str to match the current POST action
            '''
            if self.button_action == COMMENT:
                return self.button_action + " on"
            else:
                return self.button_action

        error_msg = base_template.format(status=_choose_error(),
                                         action=_choose_action(),
                                         postORcomm=self.button_subj)
        self.error_type = self.button_action + "_" + self.button_subj + "_error"
        self.set_template_field(self.error_type, error_msg)

    def get_request_type(self):
        '''Parses the value of a template button and set button_subj, button_action,
        and cur_comment as well as cur_post class fields if necessary. This
        method is useful when many buttons exist on a page relating to
        many different entities in the database, or when multiple POST requests
        come from the same page.
        It is an error to call this method when no buttons matching the
        declared global constants exist.
        '''
        get = self.handler.request.get
        for name in BUTTONS:
            if len(get(name)) > 0:  # is this button in the request?
                post_value = get(name)
                temp_list = post_value.split("_")
                self.button_action = temp_list[0]
                self.button_subj = temp_list[1]
                if len(temp_list) > 2:  # if a post or comment url key in value
                    key = ndb.Key(urlsafe=temp_list[2]).get()
                    if self.button_subj == COMMENT:
                        self.cur_comment = key
                    elif self.button_action == LIKE:
                        self.cur_post = key
                    elif self.button_subj == POST:
                        self.cur_post = key
                break
        assert (self.button_subj and self.button_action,
                "POST values did not update.")

    def update_like(self):
        '''Updates the like of users who have liked the current post and the
        text to render for a single post.
        Assumes that the current user can like the current post and that a user
        is logged in.
        '''
        cur_like_value = self.gen_like_text()
        BlogPost.add_like_unlike(self.cur_post, self.cur_user, cur_like_value)

        def _rev_like_value():
            if cur_like_value == "Like":
                return "Unlike"
            else:
                return "Like"

        self.set_template_field(LIKE_TEXT, _rev_like_value())

    def gen_like_text(self):
        '''Returns string literal "like or "unlike" based on whether the
        current user has or hasn't liked the current post.
        '''
        if BlogPost.already_liked(self.cur_post, self.cur_user):
            return "Unlike"
        else:
            return "Like"

    def get_button_error(self):
        '''Convenience method to return error type of an error associated with
        a button error
        @return: str error type or None
        '''
        return self.valid_data.get(self.error_type)

class ErrorHelper(object):
    '''Stores error messages for individual database entities. Useful for
    passing error messages to the template.
    Attributes:
        _message: error message text as a str
        _error_type: str type of the error message e.g. "delete_button_error"
        _target_id: the url key id of the database entity the messages relates
                    to
        _like_text_map: dict for rendering like buttons to main page
    '''

    def __init__(self, error_msg, error_type, entity_id):
        '''
        Create a new error helper instance holding an error message.
        @param error_msg: error message text
        @param error_type: type of the error message, matches button name
        @param entity_id: the url key id of the NDB entity re: the message
        '''
        self._message = error_msg
        self._error_type = error_type
        self._target_id = entity_id
        self._like_text_map = None

    def get_error(self, current_entity, current_error):
        '''Return an error message if one is required.
        @param current_entity: the database entity whose data is being rendered
        @param current_error: type of the error message to render
        '''
        if ((current_entity.key.urlsafe() == self._target_id) and
                (current_error == self._error_type)):
            return self._message
        else:
            return ""

    def setup_main_page_like_buttons(self, recent_posts, handler):
        '''Setup the like button text for retrieval in the template.
        @param recent_posts: list of posts to render to the template
        that have like buttons.
        @param handler: handler instance this method is being called from
        '''
        button_text_map = {}
        for post in recent_posts:
            post_url_key = post.key.urlsafe()
            button_helper = HandlerHelper(handler, [], post_url_key)
            button_text_map[post_url_key] = button_helper.gen_like_text()
        self._like_text_map = button_text_map

    def get_like_text(self, current_post_key):
        '''Return the correct like text for a like button in the template.
        @param current_post_key: the NDB url key identifying the entity for
        which to retrieve the like status
        '''
        return self._like_text_map.get(current_post_key)

class LikePost(Handler):
    '''Handles requests to like posts. Checks if the current user has 
    permission to like the post. Likes the post if the post is not 
    already liked and vice versa.
    Receives requests on two URIs /home and /post_display.
    '''
    
    @check_not_author
    @check_logged_in
    def post(self, post_key, origin):
        helper = HandlerHelper(self, [], post_key)
        
#         if not helper.is_logged_in:
#             self.redirect_to(SIGNUP, LOGIN_ERROR)
#         elif helper._is_cur_user_author():
#             self.redirect(self.uri_for(DISPLAY_POST, post_key, OWN_POST))
#         else:
        BlogPost.add_like_unlike(helper.cur_post, helper.cur_user, 
                                 helper.gen_like_text())
        if origin == HOME:
            self.redirect_to(HOME)
        elif origin == DISPLAY_POST:
            self.redirect_to(self.uri_for(DISPLAY_POST, post_key))


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
        if not cls.already_exists(form_data.get(USER)):
            secured_pwd = cls._secure_password(form_data.get(PASSWORD))
            new_user = User(user_name=form_data.get(USER),
                            password=secured_pwd,
                            email=form_data.get(EMAIL),
                            id=form_data.get(USER),
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
        new_post = BlogPost(post_subject=form_data.get(SUBJECT),
                            post_content=form_data.get(CONTENT),
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
        post_entity.post_subject = form_data[SUBJECT]
        post_entity.post_content = form_data[CONTENT]
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
        new_comment = Comment(content=form_data.get(CONTENT),
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
        return ndb.Key(urlsafe=comment_uri_key).get()

    @classmethod
    def update_comment(cls, comment_entity, form_data):
        '''Updates the content field of a Comment.
        @param comment_entity: the comment to update
        @param form_data: dict keyed to global constant containing updated
        content.
        '''
        comment_entity.content = form_data[CONTENT]
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

class BlogMainPage(Handler):
    '''Class to handle requests on the main page.
    '''

    def get(self, **kw):
        '''Displays the main page, including recent blog posts.
        '''
        HandlerHelper(self, ())
        self._render_main_page(ErrorHelper(None, None, None))

    def _render_main_page(self, error_helper_inst):
        '''Convenience function to render the main page.
        @param error_helper_inst: instance of ErrorHelper from post/get
        '''
        recent_posts = BlogPost.most_recent_20()
        error_helper_inst.setup_main_page_like_buttons(recent_posts, self)
        self.render(MAIN_PAGE_TEMPLATE, recent_blog_posts=recent_posts,
                    error_helper=error_helper_inst)

    def post(self):
        '''Handles requests to like posts and initiate a comment on a post.
        '''
        helper = HandlerHelper(self, [])
        helper.get_request_type()
        if (not helper.is_logged_in) or helper.detect_user_id_error():
            helper.gen_error_msg()
            error_helper = ErrorHelper(helper.get_button_error(),
                                       helper.error_type,
                                       helper.cur_post.key.urlsafe())
            self._render_main_page(error_helper)
        elif helper.button_action == LIKE:
            helper.update_like()
            error_helper = ErrorHelper(None, None, None)
            self._render_main_page(error_helper)
        else:
            self.redirect_to(NEW_COMMENT, helper.cur_post.key.urlsafe()) 


class NewPost(Handler):
    '''Class to handle create of new blog posts.
    '''

    def get(self):
        '''Renders the new post form on an initial request.
        '''
        helper = HandlerHelper(self, ())
        if helper.is_logged_in:
            self.render(NEW_POST_TEMPLATE)
        else:
            self.redirect_to(SIGNUP, "")

    def post(self):
        '''Handles form submission of new blog post form.
        '''
        helper = HandlerHelper(self, (SUBJECT, CONTENT))
        if helper.is_logged_in and helper.is_data_valid:
            new_post_key = BlogPost.create_new_post(helper.cur_user,
                                                    helper.valid_data)
            self.redirect_to(DISPLAY_POST, new_post_key.urlsafe())
        else:
            helper.validate_form_input(NEW_POST_TEMPLATE)


class BlogPostDisplay(Handler):
    '''Class to handle displaying static page for individual blog post. This
    page includes displaying all comments made on a post. From this page a user
    can choose to edit or delete the post, make a new comment, or edit and
    delete existing comments.
    '''

    def get(self, post_key, error):
        '''Renders an individual blog post and all comments made on that post.
        @param post_key: the url key from the uri of for the post being viewed
        '''
        helper = HandlerHelper(self, (), post_key)
        if error == OWN_POST:
            error_helper = ErrorHelper("You cannot like your own post.",
                                       "like_post_error",
                                       post_key)
        else:
            error_helper = ErrorHelper(None, None, None)
        self._render_post_template(helper, error_helper)

    def _choose_template(self, post_entity):
        '''Returns the proper template for rendering based on whether this post
        has comments.
        @param post_entity: the BlogPost entity to be rendered
        '''
        if post_entity.cur_num_comments == 0:
            return POST_ONLY_TEMPLATE
        else:
            return POST_WITH_COMMENTS

    def _render_post_template(self, helper, error_helper_instance):
        '''Renders a blog post template.
        @param helper: a HandlerHelper instance from get/post
        @param error_helper_instance: an ErrorHelper instance from same
        '''
        comments = BlogPost.get_all_comments(helper.cur_post)
        to_render = dict(current_post=helper.cur_post,
                         like_text=helper.gen_like_text(),
                         all_comments=comments,
                         error_helper=error_helper_instance)
        to_render.update(helper.valid_data)
        self.render(self._choose_template(helper.cur_post),
                    **to_render)

#     def post(self, post_key):
#         '''Handles requests to like/unlike a post, or edit/delete
#         a post/comment, and make new comment.
#         @param post_key: the url key from the uri of for the post being viewed
#         '''
#         helper = HandlerHelper(self, (), post_key)
#         helper.get_request_type()
# #         if (not helper.is_logged_in) or helper.detect_user_id_error():
# # 
# #             def _get_cur_action_key():
# #                 '''Return the key of the current button request's subject.
# #                 '''
# #                 if helper.button_subj == COMMENT:
# #                     return helper.cur_comment.key.urlsafe()
# #                 else:
# #                     return helper.cur_post.key.urlsafe()
# # 
# #             helper.gen_error_msg()
# #             error_helper = ErrorHelper(helper.get_button_error(),
# #                                        helper.error_type,
# #                                        _get_cur_action_key())
# #             self._render_post_template(helper, error_helper)
# #         elif helper.button_action == LIKE:
# #             helper.update_like()
# #             self._render_post_template(helper, ErrorHelper(None, None, None))
#         elif helper.button_action == DELETE:
#             self._delete(helper)
#             self.redirect_to(WELCOME) # re-direct to allow DB time to update.
#         else:
#             self.redirect(self._build_edit_route(helper))

    def _build_edit_route(self, helper):
        '''Builds a route for redirecting to the right URI on an edit
        request.
        @param helper: HandlerHelper instance
        '''
        pass
#         post_route = POST_ID + helper.cur_post.key.urlsafe()
#         if helper.button_action == COMMENT:
#             return post_route + "/" + COMMENT
#         else:
#             base_template = post_route + "{prefix}/edit"
#             if helper.button_subj == COMMENT:
#                 return base_template.format(prefix="/comment/" +
#                                             helper.cur_comment.key.urlsafe())
#             else:
#                 return base_template.format(prefix="")


    def _delete(self, helper):
        '''Determines whether a post or comment is to be deleted and calls
        the appropriate function.
        @param helper: HandlerHelper instance
        '''
        assert (helper.button_subj == COMMENT or helper.button_subj == POST,
                "wrong string passed; was:" + helper.button_subj)
        if helper.button_subj == COMMENT:
            Comment.delete_comment(helper.cur_comment)
        else:
            BlogPost.delete_post(helper.cur_post)


class EditPost(Handler):
    '''Class to handle rendering and submission of edit post form.
    '''

    def get(self, post_key):
        '''Handles requests to display the edit post form.
        @param post_key: string id of a BlogPost entity supplied in the URI
        '''
        helper = HandlerHelper(self, (), post_key)
        if helper.is_logged_in:
            self.render(NEW_POST_TEMPLATE, subject=helper.cur_post.post_subject,
                        content=helper.cur_post.post_content)
        else:
            self.redirect_to(SIGNUP)

    def post(self, post_key):
        '''Handles submission of edited post form. Validates form data and
        submits edited content to the database.
        @param post_key: string id of a BlogPost entity supplied in the URI
        '''
        helper = HandlerHelper(self, (SUBJECT, CONTENT), post_key)
        if helper.is_logged_in and helper.is_data_valid:
            BlogPost.update_post(helper.cur_post, helper.valid_data)
            self.redirect_to(DISPLAY_POST, post_key)
        else:
            helper.validate_form_input(NEW_POST_TEMPLATE)


class Signup(Handler):
    '''
    Class to handle requests to sign up for a new account.
    '''

    def get(self, *args):
        '''Handles requets to display the new user signup form.
        '''
        helper = HandlerHelper(self, ())
        if helper.is_logged_in:
            self.redirect_to(WELCOME)
        else:
            self.render(SIGNUP_TEMPLATE)

    def post(self, *args):
        '''Handles submission of the new user signup form. Verifies the form
        input and creates the new user account.
        '''
        helper = HandlerHelper(self, (USER, PASSWORD, PWD_VERIFY, EMAIL))
        helper.validate_form_input(SIGNUP_TEMPLATE)

        user_entity = User.already_exists(helper.valid_data.get(USER))
        if helper.is_data_valid and user_entity:
            helper.set_template_field(USER + ERROR, "User already exists. " +
                                      "Please choose another user name.")
            self.render(SIGNUP_TEMPLATE, **helper.valid_data)
        elif helper.is_data_valid:
            helper.login_user()
            User.create_new_user(helper.valid_data)
            self.redirect(WELCOME)


class NewComment(Handler):
    '''Class to handle requets to make a new comment on a post.
    '''

    def get(self, post_key):
        '''Displays the form to add a new comment to a blog post. If a user
        attempts to visit this page without being logged in, they are directed
        to the signup page.
        @param post_key: string id of a BlogPost entity supplied in the URI
        '''
        helper = HandlerHelper(self, (), post_key)
        if helper.is_logged_in:
            self.render(COMMENT_TEMPLATE, current_post=helper.cur_post,
                        error_helper=ErrorHelper(None, None, None))
        else:
            self.redirect_to(SIGNUP)

    def post(self, post_key):
        '''Handles form submission of new comment.
        @param post_key: string id of a BlogPost entity supplied in the URI
        '''
        helper = HandlerHelper(self, [CONTENT], post_key)
        helper.validate_form_input(COMMENT_TEMPLATE,
                                   current_post=helper.cur_post)
        if helper.is_data_valid:
            Comment.create_new_comment(helper.cur_user,
                                       post_key, helper.valid_data)
            self.redirect_to(DISPLAY_POST, post_key)

class EditComment(Handler):
    '''Handles requests to edit a comment.
    Constants:
        POST_KEY: URI supplied id of the post entity parent, always the
        first in the list.
        COM_KEY: same thing but with a comment entity child, always
        second item in the list.
    '''

    POST_KEY = 0
    COM_KEY = 1

    def get(self, *key_list):
        '''Retrieves the content of a comment and renders it to a form for
        editing.
        @param key_list: list of entity keys from url for post and comment
        '''
        helper = HandlerHelper(self, (), key_list[self.POST_KEY])
        if helper.is_logged_in:
            cur_comment = Comment.entity_from_uri(key_list[self.COM_KEY])
            self.render(COMMENT_TEMPLATE, current_post=helper.cur_post,
                        content=cur_comment.content)
        else: self.redirect_to(SIGNUP)

    def post(self, *key_list):
        '''Handles submission of edited comment form. Validates data submitted and
        updates the database.
        @param key_list: list of entity keys from url for post and comment
        '''
        helper = HandlerHelper(self, [CONTENT], key_list[self.POST_KEY])
        if helper.is_logged_in and helper.is_data_valid:
            cur_comment = Comment.entity_from_uri(key_list[self.COM_KEY])
            Comment.update_comment(cur_comment, helper.valid_data)
            self.redirect_to(DISPLAY_POST, key_list[self.POST_KEY])
        else:
            helper.validate_form_input(COMMENT_TEMPLATE,
                                       current_post=helper.cur_post)


class Welcome(Handler):
    '''Class to handle displaying the wecome page after a user has logged
    in or signed up.
    '''

    def get(self):
        '''Handles requests for the wecome page.
        '''
        helper = HandlerHelper(self, ())
        if helper.is_logged_in:
            self.render(WELCOME_TEMPLATE, username=helper.cur_user)
        else:
            self.redirect(LOGIN)


class Login(Handler):
    '''Class to handle displaying and accepting input from the login form.
    '''

    def get(self):
        '''Handles requests to display the login page.
        '''
        helper = HandlerHelper(self, ())
        if helper.is_logged_in:
            self.redirect(WELCOME)
        else:
            self.render(LOGIN_TEMPLATE)

    def post(self):
        '''Handles form submission and verification from the login page.
        '''
        helper = HandlerHelper(self, (USER, PASSWORD))
        helper.validate_form_input(LOGIN_TEMPLATE)
        user_entity = User.already_exists(helper.valid_data.get(USER))
        if helper.valid_data and user_entity:
            pwd_helper = PwdUtil(helper.valid_data.get(PASSWORD),
                                 user_entity.password)
            if pwd_helper.verify_password():
                helper.login_user()
                self.redirect(WELCOME)
            else:
                helper.set_template_field(PASSWORD + ERROR,
                                          "Incorrect password.")
                self.render(LOGIN_TEMPLATE, **helper.valid_data)
        elif helper.valid_data:
            helper.set_template_field(USER + ERROR, "That user does not exist.")
            self.render(LOGIN_TEMPLATE, **helper.valid_data)


class Logout(Handler):
    '''Class to handler user logout.
    '''

    def get(self):
        '''Logs the user out and redirects to the signup page.
        '''
        CookieUtil.set_cookie(USER, "", self)
        self.redirect_to(SIGNUP)


class FormHelper(object):
    '''Class to help process form input.
    Attributes:
        _regex_table: regular expressions keyed to global constants matching
                      the form field name in the template. Text input
                      into form needs to match these expressions.
        _error_table: same use of global constants, values are error messages
                      that result when regex does not match
        valid_input: boolean flag - true if all form fields match regex
        _handler: webapp2 request handler instance using this class
    '''

    def __init__(self, handler):
        self._regex_table = {
                        USER : r"^[a-zA-Z0-9_-]{3,20}$",
                        PASSWORD: r"^.{3,20}$",
                        PWD_VERIFY : r"^.{3,20}$",
                        EMAIL: r"(^[\S]+@[\S]+.[\S]+$)|(^(?![\s\S]))",
                        SUBJECT : "^.{1,100}$",
                        CONTENT : "^.{1,}$"
                        }
        self._error_table = {
                        USER : "The username is invalid.",
                        PASSWORD : "The password is invalid.",
                        PWD_VERIFY : "The passwords do not match.",
                        EMAIL : "Invalid email address.",
                        SUBJECT : "You must have a subject of less than "
                                   + "100 chars in length.",
                        CONTENT: "You must include some content."
                        }
        self.valid_input = True
        self._handler = handler

    def _is_input_valid(self, input_name):
        '''Checks if form field input matches regex.
        @param input_name: global constant name of the form field. Assumes this
        constant is present in both class dicts.
        @return: boolean - does the form field match
        '''
        if input_name == PWD_VERIFY:
            return self._handler.request.get(
                PWD_VERIFY) == self._handler.request.get(PASSWORD)
        else:
            pattern = re.compile(self._regex_table[input_name])
            return pattern.match(self._handler.request.get(input_name))

    def validate_form_data(self, all_fields):
        '''Checks each form field to make sure it matches the regex, supplies
        error messages if it does not.
        @param all_fields: the names of the form fields to check, they must be
        present in _regex_table and _error_table.
        @return: either a copy of the dict passed to this method or a dict
        containing error messages keyed to the form field name.
        '''
        to_render = {}
        for input_name in all_fields:
            if not self._is_input_valid(input_name):
                to_render[input_name + ERROR] = self._error_table.get(
                    input_name)
                to_render[input_name] = ""
                self.valid_input = False
            else:
                to_render[input_name] = self._handler.request.get(input_name)
        return to_render

# register page handlers
# app = webapp2.WSGIApplication([(HOME, BlogMainPage),
#                                (NEW_POST, NewPost),
#                                (POST_DISPLAY, BlogPostDisplay),
#                                (NEW_COMMENT, NewComment),
#                                (EDIT_COMMENT, EditComment),
#                                (EDIT_POST, EditPost),
#                                (SIGN_UP, Signup),
#                                (WELCOME, Welcome),
#                                (LOGIN, Login),
#                                (LOGOUT, Logout)], debug=True)
app = webapp2.WSGIApplication([
    routes.PathPrefixRoute("/blog", [
        webapp2.Route("/", BlogMainPage, HOME),
        webapp2.Route("/new_post", NewPost, NEW_POST),
        routes.PathPrefixRoute("/post_id/<:\w+-\w+|\w+>", [
            webapp2.Route("/display/<:\w+>", BlogPostDisplay, DISPLAY_POST),
            webapp2.Route("/comment", NewComment, NEW_COMMENT),
            webapp2.Route("/comment/<:(\w+-\w+|\w+)>/edit", 
                          EditComment, EDIT_COMMENT),
            webapp2.Route("/edit", EditPost, EDIT_POST),
            webapp2.Route("/like_post/<:\w+>", LikePost, LIKE_POST)]),
        webapp2.Route("/user_welcome", Welcome, WELCOME),
        webapp2.Route("/login", Login, LOGIN),
        webapp2.Route("/logout", Logout, LOGOUT),
        webapp2.Route("/signup/<:\w+>", Signup, SIGNUP)
    ])
])



