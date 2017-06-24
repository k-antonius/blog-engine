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
import time
from ndb_models import User, BlogPost, Comment


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
HOME_ERROR = "home_error"
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
DELETE_POST = "delete_post"
DELETE_COMMENT = "delete_comment"

# Form Input Fields
USER = "username"
PASSWORD = "password"
PWD_VERIFY = "pwd_verify"
EMAIL = "email"
SUBJECT = "subject"
CONTENT = "content"
ERROR = "_error"
COMMENT = "comment"
DELETE = "delete"
POST = "post"
LIKE = "like"

# URI status terminators
ACCESS_ERROR = "access_error"
OWN_POST = "own_post"
NOT_AUTHOR = "not_author"
DISPLAY = "display"


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
    
    @classmethod
    def check_logged_in(cls, handler_fun):
        '''Decorator that checks if a user is logged in and redirects to the 
        signup handler if a user is not.
        @param handler_fun: the handler function to be wrapped
        '''
        
        @wraps(handler_fun)
        def wrapper(self, *args, **kwargs):
            helper = HandlerHelper(self, [])
            if not helper.is_logged_in():
                self.redirect(self.uri_for(SIGNUP, ACCESS_ERROR))
            else:
                handler_fun(self, *args, **kwargs)
        return wrapper

    @classmethod
    def check_not_author(cls, handler_fun):
        '''Decorator to check that the current user is not the author of the
        post or comment entity being accessed.
        @param handler_fun: the handler function to be wrapped
        '''
        
        @wraps(handler_fun)
        def wrapper(self, *args, **kwargs):
            post_key = args[0]
            origin = args[1]
            helper = HandlerHelper(self, [], post_key)
            if helper.is_cur_user_author(POST):
                if origin == DISPLAY_POST:
                    self.redirect(self.uri_for(DISPLAY_POST, post_key, 
                                               OWN_POST))
                elif origin == HOME:
                    self.redirect(self.uri_for(HOME_ERROR, post_key))
            else:
                handler_fun(self, *args, **kwargs)
        return wrapper

    @classmethod
    def check_is_author(cls, entity_type):
        '''Parameterized decorator to check that the current user is the author 
        of the post or comment entity being accessed.
        @param handler_fun: the handler function to be wrapped
        @param entity_type: The type of the entity being accessed, use one of 
        the global constants POST, COMMENT etc.
        '''
        def takes_function(handler_fun):
            @wraps(handler_fun)
            def wrapper(self, *args, **kwargs):
                post_key = args[0]
                helper = HandlerHelper(self, [], post_key)
                if not helper.is_cur_user_author(entity_type):
                    self.redirect(self.uri_for(DISPLAY_POST, post_key, 
                                               NOT_AUTHOR + "_" + entity_type))
                else:
                    handler_fun(self, *args, **kwargs)
            return wrapper
        return takes_function

    @classmethod
    def check_post_exists(cls, handler_fun):
        '''If attempt to query database for blog post fails, raise a 404
        error. Otherwise continue handler execution.
        @return: BlogPost entity from key or raise a 404 error.
        '''
        @wraps(handler_fun)
        def wrapper(self, *args, **kwargs):
            post_key = args[0]
            helper = HandlerHelper(self, [], post_key)
            if helper.cur_post is not None:
                return handler_fun(self, *args, **kwargs)
            else:
                return self.error(404)
        return wrapper


class HandlerHelper(object):
    '''A class that aggregates data about the state of a request handler
    and performs validation and parsing actions on that state. Makes the data
    available for use in templates.
    Attributes:
        handler: the Webapp2 request handler
        cur_user: the str user name of a logged in user, if any
        cur_post: the blog post database object relevant to the current page
        data_error_msgs: dict of error msgs generated from bad text form input
        valid_data: dict holding data to be rendered to a template
        is_data_valid: boolean, true if text input was valid
    '''

    def __init__(self, handler, field_list, post_id=None):
        '''
        @param handler: the Webapp2 request handler
        @param field_list: list of form input fields to verify, named by
        global constants
        @param post_id: the url-safe NDB key id of a post entity, used to 
        retrieve the post entity upon initialization, if desired
        '''
        self.handler = handler
        self.cur_user = self._logged_in_user()
        self.cur_post = self.get_cur_post(post_id)
        self.data_error_msgs = None
        self.valid_data = {}
        self.is_data_valid = False
        self._validate_user_input(field_list)

    def set_template_field(self, key, value):
        '''Include text for rendering in html template in the valid data dict.
        @param: key - str form field name constant, defined globally
        @param: value - str to render in template
        '''
        self.valid_data[key] = value

    def is_logged_in(self):
        '''Returns true if a cookie is set for a logged in user.
        '''
        return CookieUtil.get_cookie(USER, self.handler) is not None
            

    def _logged_in_user(self):
        '''Returns the str user name of user currently logged in.
        '''
        return CookieUtil.get_cookie(USER, self.handler)

    def get_cur_post(self, key_from_url):
        '''Returns a blog post ENTITY from url-safe string.
        @param key_from_url: the url-safe key string for a BlogPost
        '''
        if key_from_url:
            try:
                return ndb.Key(urlsafe=key_from_url).get()
            except:
                return None

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

    def is_cur_user_author(self, entity_type):
        if entity_type == COMMENT:
            comment = Comment.entity_from_uri(
                      self.handler.request.get("comment_key"))
            return comment.author == self.cur_user
        elif entity_type == POST:
            return self.cur_post.post_author == self.cur_user
        else:
            raise Exception("Entity type not 'post' or 'comment'")

    def gen_like_text(self):
        '''Returns string literal "like or "unlike" based on whether the
        current user has or hasn't liked the current post.
        '''
        if BlogPost.already_liked(self.cur_post, self.cur_user):
            return "Unlike"
        else:
            return "Like"


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

    def __init__(self, error_msg, entity_id):
        '''
        Create a new error helper instance holding an error message.
        @param error_msg: error message text
        @param error_type: type of the error message, matches button name
        @param entity_id: the url key id of the NDB entity re: the message
        '''
        self._message = error_msg
        self._target_id = entity_id
        self._like_text_map = None

    def get_error(self, current_entity):
        '''Return an error message if one is required.
        @param current_entity: the database entity whose data is being rendered
        @param current_error: type of the error message to render
        '''
        if current_entity.key.urlsafe() == self._target_id:
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
            if button_helper.cur_post is None:
                continue
            else:
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
    
    @Handler.check_not_author
    @Handler.check_logged_in
    @Handler.check_post_exists
    def post(self, post_key, origin):
        helper = HandlerHelper(self, [], post_key)
        BlogPost.add_like_unlike(helper.cur_post, helper.cur_user, 
                                 helper.gen_like_text())
        if origin == HOME:
            # remove this in deployment
            time.sleep(0.1)
            return self.redirect(self.uri_for(HOME, "update"))
        elif origin == DISPLAY_POST or origin == OWN_POST:
            self.redirect(self.uri_for(DISPLAY_POST, post_key, DISPLAY_POST))


class BlogMainPage(Handler):
    '''Class to handle requests on the main page.
    '''

    def get(self, status):
        '''Displays the main page, including recent blog posts.
        '''
        if status == HOME:
            helper =  ErrorHelper(None, None)
        else:
            helper = ErrorHelper("You cannot like your own post", status)
        HandlerHelper(self, ())
        self._render_main_page(helper)

    def _render_main_page(self, error_helper_inst):
        '''Convenience function to render the main page.
        @param error_helper_inst: instance of ErrorHelper from post/get
        '''
        recent_posts = BlogPost.most_recent_20()
        error_helper_inst.setup_main_page_like_buttons(recent_posts, self)
        self.render(MAIN_PAGE_TEMPLATE, recent_blog_posts=recent_posts,
                    error_helper=error_helper_inst)


class NewPost(Handler):
    '''Class to handle create of new blog posts.
    '''

    @Handler.check_logged_in
    def get(self):
        '''Renders the new post form on an initial request.
        '''
        self.render(NEW_POST_TEMPLATE)

    @Handler.check_logged_in    
    def post(self):
        '''Handles form submission of new blog post form.
        '''
        helper = HandlerHelper(self, (SUBJECT, CONTENT))
        if helper.is_data_valid:
            new_post_key = BlogPost.create_new_post(helper.cur_user,
                                                    helper.valid_data)
            self.redirect(self.uri_for(DISPLAY_POST, new_post_key.urlsafe(),
                                       DISPLAY))
        else:
            helper.validate_form_input(NEW_POST_TEMPLATE)


class BlogPostDisplay(Handler):
    '''Class to handle displaying static page for individual blog post. This
    page includes displaying all comments made on a post. From this page a user
    can choose to edit or delete the post, make a new comment, or edit and
    delete existing comments.
    '''
    
    @Handler.check_post_exists
    def get(self, post_key, error):
        '''Renders an individual blog post and all comments made on that post.
        @param post_key: the url key from the uri of for the post being viewed
        '''
        helper = HandlerHelper(self, (), post_key)
        if error == OWN_POST:
            error_helper = ErrorHelper("You cannot like your own post.",
                                       post_key)
        elif "not_author" in error:
            entity_type = self.parse_url_error(error)
            error_helper = ErrorHelper("You must be a " + 
                                       entity_type +"'s author " + 
                                       "to do that.", post_key)
        else:
            error_helper = ErrorHelper(None, None)
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
        
    def parse_url_error(self, error_string):
        split_text = error_string.split("_")
        return split_text[2]


class EditPost(Handler):
    '''Class to handle rendering and submission of edit post form.
    '''
    
    @Handler.check_is_author(POST)
    @Handler.check_logged_in
    @Handler.check_post_exists
    def get(self, post_key):
        '''Handles requests to display the edit post form.
        @param post_key: string id of a BlogPost entity supplied in the URI
        '''
        helper = HandlerHelper(self, (), post_key)
        self.render(NEW_POST_TEMPLATE, subject=helper.cur_post.post_subject,
                    content=helper.cur_post.post_content)

    @Handler.check_is_author(POST)
    @Handler.check_logged_in
    @Handler.check_post_exists
    def post(self, post_key):
        '''Handles submission of edited post form. Validates form data and
        submits edited content to the database.
        @param post_key: string id of a BlogPost entity supplied in the URI
        '''
        helper = HandlerHelper(self, (SUBJECT, CONTENT), post_key)
        if helper.is_data_valid:
            BlogPost.update_post(helper.cur_post, helper.valid_data)
            self.redirect(self.uri_for(DISPLAY_POST, post_key, DISPLAY_POST))
        else:
            helper.validate_form_input(NEW_POST_TEMPLATE)


class DeletePost(Handler):
    '''Handles deletion of posts
    '''
    
    @Handler.check_is_author(POST)
    @Handler.check_logged_in
    @Handler.check_post_exists
    def post(self, post_key):
        BlogPost.delete_post(ndb.Key(urlsafe=post_key).get())
        self.redirect(self.uri_for(HOME, HOME))

class DeleteComment(Handler):
    '''Handles deletion of comments.
    '''
    
    @Handler.check_is_author(COMMENT)
    @Handler.check_logged_in
    @Handler.check_post_exists
    def post(self, post_key):
        comment_key = self.request.get("comment_key")
        Comment.delete_comment(ndb.Key(urlsafe=comment_key).get())
        self.redirect(self.uri_for(DISPLAY_POST, post_key, DISPLAY_POST))


class Signup(Handler):
    '''
    Class to handle requests to sign up for a new account.
    '''

    def get(self, *args):
        '''Handles requets to display the new user signup form.
        '''
        helper = HandlerHelper(self, ())
        if helper.is_logged_in():
            self.redirect_to(WELCOME)
        else:
            self.render(SIGNUP_TEMPLATE)

    def post(self, *args):
        '''Handles submission of the new user signup form. Verifies the form
        input and creates the new user account.
        '''
        helper = HandlerHelper(self, (USER, PASSWORD, PWD_VERIFY, EMAIL))
        helper.validate_form_input(SIGNUP_TEMPLATE)
        try:
            user_entity = User.already_exists(helper.valid_data.get(USER))
        except:
            return self.error(404)
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

    @Handler.check_logged_in
    @Handler.check_post_exists
    def get(self, post_key, origin):
        '''Displays the form to add a new comment to a blog post. If a user
        attempts to visit this page without being logged in, they are directed
        to the signup page.
        @param post_key: string id of a BlogPost entity supplied in the URI
        @param origin: the leaf of the URI tree where this request originated
        '''
        helper = HandlerHelper(self, (), post_key)
        self.render(COMMENT_TEMPLATE, current_post=helper.cur_post,
                    error_helper=ErrorHelper(None, None))
        
    @Handler.check_post_exists
    def post(self, post_key, origin):
        '''Handles form submission of new comment.
        @param post_key: string id of a BlogPost entity supplied in the URI
        @param origin: the leaf of the URI tree where this request originated
        '''
        helper = HandlerHelper(self, [CONTENT], post_key)
        helper.validate_form_input(COMMENT_TEMPLATE,
                                   current_post=helper.cur_post)
        if helper.is_data_valid:
            Comment.create_new_comment(helper.cur_user,
                                       post_key, helper.valid_data)
            self.redirect(self.uri_for(DISPLAY_POST, post_key, origin))

class EditComment(Handler):
    '''Handles requests to edit a comment.
    Constants:
        POST_KEY: URI supplied id of the post entity parent, always the
        first in the list.
        COM_KEY: same thing but with a comment entity child, always
        second item in the list.
    '''

    @Handler.check_is_author(COMMENT)
    @Handler.check_logged_in
    @Handler.check_post_exists
    def get(self, post_key):
        '''Retrieves the content of a comment and renders it to a form for
        editing.
        @param post_key: url-safe ndb entity key
        '''
        helper = HandlerHelper(self, (), post_key)
        cur_comment = ndb.Key(urlsafe=self.request.get("comment_key")).get() 
        self.render(COMMENT_TEMPLATE, current_post=helper.cur_post,
                        content=cur_comment.content)

    @Handler.check_is_author(COMMENT)
    @Handler.check_logged_in
    @Handler.check_post_exists
    def post(self, post_key):
        '''Handles submission of edited comment form. Validates data submitted 
        and updates the database.
        @param post_key: url-safe ndb entity key
        '''
        helper = HandlerHelper(self, [CONTENT], post_key)
        if helper.is_data_valid:
            cur_comment = Comment.entity_from_uri(self.request.get("comment_key"))
            Comment.update_comment(cur_comment, helper.valid_data)
            self.redirect(self.uri_for(DISPLAY_POST, post_key, DISPLAY_POST))
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
        if helper.is_logged_in():
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
        if helper.is_logged_in():
            self.redirect(WELCOME)
        else:
            self.render(LOGIN_TEMPLATE)

    def post(self):
        '''Handles form submission and verification from the login page.
        '''
        helper = HandlerHelper(self, (USER, PASSWORD))
        helper.validate_form_input(LOGIN_TEMPLATE)
        try:
            user_entity = User.already_exists(helper.valid_data.get(USER))
        except:
            return self.error(404)
        if helper.valid_data and user_entity:
            pwd_helper = PwdUtil(helper.valid_data.get(PASSWORD),
                                 user_entity.password)
            if pwd_helper.verify_password():
                helper.login_user()
                self.redirect(self.uri_for(WELCOME))
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
        self.redirect(self.uri_for(SIGNUP, DISPLAY))


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


app = webapp2.WSGIApplication([
    routes.PathPrefixRoute("/blog", [
        webapp2.Route("/display/<:\w+>", BlogMainPage, HOME),
        webapp2.Route("/error/<:\w+-\w+|\w+>", BlogMainPage, HOME_ERROR),
        webapp2.Route("/new_post", NewPost, NEW_POST),
        routes.PathPrefixRoute("/post_id/<:\w+-\w+|\w+>", [
            webapp2.Route("/display/<:\w+>", BlogPostDisplay, DISPLAY_POST),
            webapp2.Route("/comment/new/<:\w+>", NewComment, NEW_COMMENT),
            webapp2.Route("/comment/edit", 
                          EditComment, EDIT_COMMENT),
            webapp2.Route("/edit", EditPost, EDIT_POST),
            webapp2.Route("/delete", DeletePost, DELETE_POST),
            webapp2.Route("/comment/delete", 
                          DeleteComment, DELETE_COMMENT),
            webapp2.Route("/like_post/<:\w+>", LikePost, LIKE_POST)]),
        webapp2.Route("/user_welcome", Welcome, WELCOME),
        webapp2.Route("/login", Login, LOGIN),
        webapp2.Route("/logout", Logout, LOGOUT),
        webapp2.Route("/signup/<:\w+>", Signup, SIGNUP)
    ])
])
