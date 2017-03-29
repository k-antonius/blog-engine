'''
Created on Jan 7, 2017

@author: kennethalamantia
'''
import os
import re

import jinja2
import webapp2
from google.appengine.ext import ndb
from blog_utilities import CookieUtil, PwdUtil
from google.appengine.ext.datastore_admin.config import current

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA = jinja2.Environment(loader = jinja2.FileSystemLoader(TEMPLATE_DIR),
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
HOME = "/blog"
NEWPOST = HOME + "/new_post"
SIGNUP = HOME + "/signup"
WELCOME = HOME + "/user_welcome"
LOGIN =  HOME + "/login"
LOGOUT = HOME + "/logout"
POST_ID = HOME + "/post_id/" # N.B. the final "/" - never terminates URI
POSTDISPLAY = r"/blog/post_id/(\w+-\w+|\w+)"
NEWCOMMENT = r"/blog/post_id/(\w+-\w+|\w+)/comment"
EDIT_POST = r"/blog/post_id/(\w+-\w+|\w+)/edit"

# Form Input Fields
USER = "username"
PASSWORD = "password"
PWD_VERIFY = "pwd_verify"
EMAIL = "email"
SUBJECT = "subject"
CONTENT = "content"
ERROR = "_error"    

class Handler(webapp2.RequestHandler):
        
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    def render_str(self, a, **kw):
        t = JINJA.get_template(a)
        return t.render(kw)
    
    def render(self, *a, **kw):
        self.write(self.render_str(*a, **kw))
    
    def get_attribute(self, type):
        '''
        Returns the value of the specified request type.
        '''
        return self.request.get(type)
    
    def _check_logged_in(self, route):
        '''
        Checks to make sure correct user is logged in. If not redirects to 
        @param URI route.
        If a user is logged in returns the user's name as a string.
        '''
        # get user name from cookie
        # check to make sure user is logged in
        logged_in_user = CookieUtil.get_cookie(USER, self)
        if not logged_in_user:
            self.redirect(route)
        else:
            return logged_in_user
        
    def logged_in(self):
        '''
        Returns true if a user is logged in, false otherwise
        '''
        if CookieUtil.get_cookie(USER, self):
            return True
        else:
            return False
        
    def logged_in_user(self):
        '''
        Returns the user currently logged in.
        '''
        user = CookieUtil.get_cookie(USER, self)
        assert (user, "Attempted to retrieve a logged in user where" +
                " none was logged in.")
        return user
        
            
    def _validate_user_input(self, *args):
        '''
        Checks that user input into the form is valid. If it is not,
        generates suitable error messages and re-renders the page. If valid,
        returns the data input into the form in a dict keyed to the global
        constants.
        @param args: the names of the form fields that need verifying.
        '''
        form_helper = FormHelper(self)
        form_data = form_helper.validate_form_data(args)
        if not form_helper.valid_input:
            return False, form_data
        else:
            return True, form_data
    
    def _was_valid(self, form_tuple):
        '''
        Helper method to determine whether processed form data was valid.
        Takes a tuple of length 2 where element 0 is a boolean. 
        Returns the value of that boolean.
        '''
        return form_tuple[0]
    
    def _get_form_data(self, form_tuple):
        '''
        Helper method to get form data back from form processor.
        Takes a tuple of length 2 where element 1 is a dictionary.
        Returns the dictionary.
        '''
        return form_tuple[1]
    
    def get_cur_post(self, post_string):
        '''
        Returns a blog post ENTITY from url-safe string.
        @param post_string: the url-safe post key string
        @param username: the post-author's username
        '''
        return ndb.Key(urlsafe=post_string).get()
    
    def update_like(self, helper):
        '''
        Updates whether a user has liked a blog post in the database. Generates
        appropriate error messages if a user attempts to like own post or 
        visitor who isn't logged in attempts to like a post.
        @param helper: instance of the HandlerHelper class
        '''
        LIKE_TEXT = "like_text"
        LIKE_ERROR =  "like_error"
        NOT_LOGGED_IN = "You must be logged in to like or unlike a post."
        LIKE_OWN_POST = "You cannot like your own post."
        cur_like_value = self.gen_like_text(helper.cur_post, helper.cur_user)
        
        if not helper.is_logged_in:
            helper.set_template_field(LIKE_ERROR, NOT_LOGGED_IN)
            helper.set_template_field(LIKE_TEXT, cur_like_value)
            
        elif helper.cur_user == helper.cur_post.post_author:
            helper.set_template_field(LIKE_ERROR, LIKE_OWN_POST)
            helper.set_template_field(LIKE_TEXT, cur_like_value)
            
        else:
            BlogPost.add_like_unlike(helper.cur_post, helper.cur_user, 
                                     cur_like_value)
            helper.set_template_field(LIKE_TEXT, 
                                      self.rev_like_value(cur_like_value))

    def rev_like_value(self, cur_like_value):
        '''
        Returns a string that is the opposite of the current "like" status,
        e.g. if "Like" is input, returns "Unlike."
        '''
        assert (cur_like_value == "Like" or cur_like_value == "Unlike",
                "Impossible value for cur_like_value, was " + cur_like_value)
        if cur_like_value == "Like":
            return "Unlike"
        else:
            return "Like"
        
    def like_button_text(self, like_value):
        '''
        Returns a string for like button.
        @param like_value: boolean value whether post has been liked
        @return: "Like" or "Unlike" string literal
        '''
        if like_value:
            return "Unlike"
        else:
            return "Like"
    
    def gen_like_text(self, post_entity, cur_user):
        '''
        Returns the proper string, "Like" or "Unlike" based on whether the
        user logged in has like a given post.
        @param post_entity: the blog post that is the subject of the like/unlike
        @param cur_user: the user id string of the viewing user
        @return: appropriate string literal
        '''
        if BlogPost.already_liked(post_entity, cur_user):
            return "Unlike"
        else:
            return "Like"
    
    def gen_comment_uri(self, post_entity):
        '''
        Returns a comment URI for linking to comment page.
        @param post_entity: the BlogPost entity to add comment to
        @return: the string URI leading to the NewCommend handler
        '''
        return post_entity.key.urlsafe() + "/comment"
    
class HandlerHelper(object):
    '''
    A class that aggregates data about the state of a request handler.
    '''
    def __init__(self, handler, field_list, post_id=None):
        self.handler = handler
        self.is_logged_in = self._logged_in()
        self.cur_user = self._logged_in_user()
        self.cur_post = self._get_cur_post(post_id)
        self.data_error_msgs = None
        self.valid_data = {}
        self.is_data_valid = False
        self._validate_user_input(field_list)
        
    def set_template_field(self, key, value):
        '''
        Include text for rendering in html template.
        @params:
            key - a form field name constant, defined globally
            value - text to render in template
        '''
        self.valid_data[key] = value
    
    def _logged_in(self):
        '''
        Returns true if a user is logged in, false otherwise
        '''
        if CookieUtil.get_cookie(USER, self.handler):
            return True
        else:
            return False
        
    def _logged_in_user(self):
        '''
        Returns the user currently logged in.
        '''
        return CookieUtil.get_cookie(USER, self.handler)
    
    def _get_cur_post(self, post_string):
        '''
        Returns a blog post ENTITY from url-safe string.
        @param post_string: the url-safe post key string
        @param username: the post-author's username
        '''
        if post_string:
            return ndb.Key(urlsafe=post_string).get()
        
    def _validate_user_input(self, field_list):
        '''
        Checks that user input into the form is valid. Sets class fields
        appropriately based on whether data was valid or invalid, using
        error messages.
        @param 
            field_list: name of fields to process as global constants
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
        '''
        Sets a cookie for the user name contained in the valid-data dictionary.
        Will raise an exception if no username string is present.
        '''
        assert self.valid_data.get(USER)
        CookieUtil.set_cookie(USER, self.valid_data.get(USER), self.handler)
        
    def validate_form_input(self, template, **additional_elements):
        '''
        Checks the data input into the form for validity based on rules defined
        in the Form Helper class. Re-renders the form with error messages using
        the provided template.
        @param template: the template to render error messages to
        @param additional_elements: if the template requires non-form input
        to render correctly, must pass these elements to the template.
        '''
        if not self.is_data_valid:
            self.data_error_msgs.update(additional_elements)
            self.handler.render(template, **self.data_error_msgs)
    
class User(ndb.Model):
    '''
    This is a root entity.
    '''
    user_name = ndb.StringProperty(required = True)
    password = ndb.StringProperty(required = True)
    email = ndb.StringProperty()
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    user_picture = ndb.StringProperty()
    num_posts = ndb.IntegerProperty()
    
    @classmethod
    def create_new_user(cls, form_data):
        '''
        Creates a new user account in the database. If account is successfully
        created returns the user's key. If the user already exists, this 
        method returns a string error message.
        
        @param user_name is a str -- also the id of the key.
        @param password is a str -- the user's password.
        @param email - optional email address
        '''
        if not cls.already_exists(form_data.get(USER)):
            secured_pwd = cls._secure_password(form_data.get(PASSWORD))
            new_user = User(user_name = form_data.get(USER), 
                            password = secured_pwd, 
                            email= form_data.get(EMAIL), 
                            id = form_data.get(USER),
                            num_posts = 0)
            new_user_key = new_user.put()
            return new_user_key
                            
    @classmethod
    def already_exists(cls, user_name):
        '''
        Checks the database to see whether the user exists.
        @param user_name: the string to check
        @return: the user entity or None if no such user exists 
        '''
        if user_name:
            return cls.get_by_id(user_name)
        else:
            return None
        
    
    @classmethod
    def increment_num_posts(cls, user_name):
        '''
        Increment the number of posts this user has made by one, 
        given the user name, the key id of a user entity. Returns the number
        of posts for this user resulting from the increment operation.
        '''
        user_key = ndb.Key("User", user_name)
        user = user_key.get()
        user.num_posts += 1
        user.put()
        return user.num_posts
    
    @classmethod
    def get_num_posts(cls, user_name):
        '''
        Given the key id of this user, returns the number of posts this user
        has made.
        '''
        user_key = ndb.Key("User", user_name)
        user = user_key.get()
        return user.num_posts
    
    @classmethod
    def _secure_password(cls, clear_text):
        '''
        Returns a hashed and salted password for storing in database.
        @param clear_text: the clear-text password to make secure
        @return a secure password in the form "hasedpassword,salt"
        '''
        pwd_helper = PwdUtil(clear_text)
        return pwd_helper.new_pwd_salt_pair()

class BlogPost(ndb.Model):
    '''
    Parent is the user-author of the post.
    '''
    post_subject = ndb.StringProperty(required = True)
    post_content = ndb.TextProperty(required = True)
    post_author = ndb.StringProperty(required = True)
    post_number = ndb.StringProperty()
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    last_edited = ndb.DateTimeProperty()
    users_liked = ndb.StringProperty(repeated=True)
    num_comments = ndb.IntegerProperty()
    
    
    @classmethod
    def create_new_post(cls, user_name, form_data):
        '''
        Creates a new post in the database, setting its subject, content,
        and author. The key for the post is in the form:
        ("User", user_name, "post_id", post_number) post number is the number
        of posts a given user has made.
        An ndb User entity is the parent of every post.
        '''
        
        post_number = str(User.increment_num_posts(user_name))
        new_post = BlogPost(post_subject = form_data.get(SUBJECT),
                            post_content = form_data.get(CONTENT),
                            post_author = user_name,
                            parent = ndb.Key("User", user_name))
        new_post.post_number = post_number
        new_post.key = ndb.Key("User", user_name, "BlogPost", post_number)
        new_post.users_liked = []
        new_post.num_comments = 0
        new_post_key = new_post.put()
       
        return new_post_key
    
    @classmethod
    def increment_num_comments(cls, post_entity):
        '''
        Increments the number of comments on this post. The number of 
        comments of a post is also the id of a given child comment entity.
        '''
        if post_entity.num_comments:
            post_entity.num_comments += 1
        else:
            post_entity.num_comments = 1
        post_entity.put()
        return post_entity.num_comments
    
    @classmethod 
    def get_post_key(cls, user_name, post_id):
        '''
        Returns the key object of a post entity given its author and int id.
        '''
        pass
    
    @classmethod
    def add_like_unlike(cls, post_entity, user_name, like_status):
        '''
        Adds a user to the list of users who have liked this post.
        Throws an exception if the user is already in this list.
        @param post_entity: the post being liked
        @param user_name: the user liking the post
        '''
        if like_status == "Like":
            post_entity.users_liked.append(user_name)
        else:
            post_entity.users_liked.remove(user_name)
        post_entity.put()
        
    @classmethod
    def already_liked(cls, post_entity, user_name):
        '''
        Returns boolean value whether given user has liked a blog post.
        @param post_entity: the subject post
        @param user_name: the string username of the user entity to test
        '''
        result = user_name in post_entity.users_liked
        return result
        
    @classmethod
    def get_all_comments(cls, post_entity):
        '''
        Returns a list of all the comments for a given post.
        @param post_entity: the blog post entity to retreive comments for
        @return: a list of Comment entities
        '''
        comments_query = Comment.query(ancestor=post_entity.key)
        all_comments = comments_query.order(-Comment.date_created).fetch()
        return all_comments
    
    @classmethod
    def most_recent_20(cls):
        '''
        Returns up to the most recent 20 blog posts in descending order of
        date created.
        '''
        posts_query = cls.query()
        recent_posts = posts_query.order(-cls.date_created).fetch(20)
        return recent_posts
    
    @classmethod
    def update_post(cls, post_entity, form_data):
        '''
        Updates the subject and content of a post upon editing.
        @params:
            post_entity - the the entity to be updated
            form_data - the form data dictionary containing the new subject
            and content
        @return:
            the post_entity with updated fields
        '''
        post_entity.post_subject = form_data[SUBJECT]
        post_entity.post_content = form_data[CONTENT]
        post_entity.put()
        return post_entity

class Comment(ndb.Model):
    '''
    Parent is the blog post.
    '''
    content = ndb.TextProperty(required = True)
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    last_edited = ndb.DateTimeProperty()
    author = ndb.StringProperty(required = True)
    num_likes = ndb.IntegerProperty()
    
    @classmethod
    def create_new_comment(cls, user_name, url_string, form_data):
        '''
        Creates a new comment for a specific post.
        user_name - user making the comment
        post_id - id of blog post user is commenting on
        form_data - dictionary of data from post response
        '''
        parent_key = ndb.Key(urlsafe=url_string)
        parent_post = parent_key.get()
        new_comment = Comment(content = form_data.get(CONTENT),
                              author = user_name,
                              parent = parent_key)
        comment_num = BlogPost.increment_num_comments(parent_post)
        new_comment.key = ndb.Key("Comment", str(comment_num), parent=parent_key)
        new_comment.put()
        return new_comment.key
        
    @classmethod
    def get_comment_key(cls, comment_num, post_key):
        '''
        Returns the key object of a given comment, given its ancestor path
        ids.
        '''
        return ndb.Key("Comment", str(comment_num), parent=post_key)

class BlogMainPage(Handler):
    '''
    Note on properly displaying like/unlike status of a given post:
    Map url-safe entity key to "Like" or "Unlike" per status of that
    post re: user or visitor. Then pass that map to the template.
    Have the template retrieve the correct value and render based on the 
    key of the current post. BAM.
    '''
    def get(self):
        '''
        - query 10 most recent posts
        - for each post: determine like status, build comment URI
        - render the page
        '''
        helper = HandlerHelper(self, ())
        recent_posts = BlogPost.most_recent_20()
        self.render(MAIN_PAGE_TEMPLATE, recent_blog_posts = recent_posts,
                    button_data = self.setup_buttons(recent_posts, helper))
        
    def setup_buttons(self, posts_to_render, helper):
        '''
        Gathers information about like status, comment uri, and error message
        status for each blog post that will be displayed and organizes the
        information in a dictionary for retrieval in the template.
        @param posts_to_render: list of post entity objects for rendering
        @return: dictionary {post_entity : {"like_status" : "like/unlike",
                                            "comment_uri" : the uri,
                                            "error_msg" : "" or msg}} 
        '''
        LIKE_TEXT = "like_text"
        COMMENT_URI = "comment_uri"
        LIKE_ERROR = "like_error"
        to_render = {}
        for post in posts_to_render:
            key_string = post.key.urlsafe()
            button_text = self.gen_like_text(post, helper.cur_user)
            uri_text = "/blog/post_id/" + self.gen_comment_uri(post)
            to_render[key_string] = {LIKE_TEXT : button_text,
                               COMMENT_URI : uri_text,
                               LIKE_ERROR : ""}
        return to_render
            
        
    def post(self):
        '''
        - only post request is a like/unlike
        - determine which post is being liked/unliked
        - update using same method is in BlogPostDisplay
        - render page in same was as get method
        '''
        helper = HandlerHelper(self, (), self.request.get("like_button"))
        self.update_like(helper)
        changed_post_dict = helper.valid_data
        changed_post_dict.update(dict(comment_uri = 
                                 self.gen_comment_uri(helper.cur_post)))
        recent_posts = BlogPost.most_recent_20()
        button_info = self.setup_buttons(recent_posts, helper)
        button_info.update({helper.cur_post.key.urlsafe() : changed_post_dict})
        self.render(MAIN_PAGE_TEMPLATE, recent_blog_posts = recent_posts,
                    button_data = button_info)             

class NewPost(Handler):
    '''
    Handles requests to make a new blog post.
    '''
    
    def get(self):
        '''
        Renders the new post form on an initial request. If no user is logged 
        in directs to the signup page.
        '''
        helper = HandlerHelper(self, ())
        if helper.is_logged_in:
            self.render(NEW_POST_TEMPLATE)
        else:
            self.redirect(SIGNUP)
        
    def post(self):
        '''
        Takes input from the new post form, validates the input, and 
        adds a new entity to the database, storing the information from
        the new blog post.
        '''
        helper = HandlerHelper(self, (SUBJECT, CONTENT))
        if helper.is_logged_in and helper.is_data_valid:
            new_post_key = BlogPost.create_new_post(helper.cur_user, 
                                                    helper.valid_data)
            self.redirect(POST_ID + new_post_key.urlsafe())
        else:
            helper.validate_form_input(NEW_POST_TEMPLATE)
        
class BlogPostDisplay(Handler):
    
    def get(self, post_key):
        '''
        Renders an individual blog post an all comments made on that post.
        '''
        helper = HandlerHelper(self, (), post_key)
        self._renderPostTemplate(helper)
    
    def _choose_template(self, post_entity):
        '''
        Returns the proper template for rendering based on whether this post
        has comments.
        @param post_entity: the BlogPost entity to be rendered
        '''
        if post_entity.num_comments == 0:
            return POST_ONLY_TEMPLATE
        else:
            return POST_WITH_COMMENTS
    
    def _renderPostTemplate(self, helper):
        '''
        Renders a blog post template.
        @param handler: a HandlerHelper instance.
        '''
        to_render = dict(current_post = helper.cur_post,
                    comment_link = self.gen_comment_uri(helper.cur_post),
                    like_text = self.gen_like_text(helper.cur_post, 
                                                   helper.cur_user),
                    all_comments = BlogPost.get_all_comments(helper.cur_post))
        to_render.update(helper.valid_data)
        self.render(self._choose_template(helper.cur_post),
                    **to_render)
            
    def post(self, post_key):
        '''
        Handles requests to like/unlike a post, or edit a post.
        Re-renders the template with appropriate error messages if a user is
        not logged in, attempts to edit another's post, or like own post.
        '''
        LIKE = "like_button"
        EDIT = "edit_button"
        EDIT_ERROR = "edit_error"
        NOT_LOGGED_IN = "You must be logged in to edit a post."
        NOT_OWN_POST = "You can't edit another user's post."
        helper = HandlerHelper(self, (), post_key)
        
        if self.request.get(LIKE):
            self.update_like(helper)
            self._renderPostTemplate(helper)
            
        if self.request.get(EDIT):
            if not helper.is_logged_in:
                helper.set_template_field(EDIT_ERROR, NOT_LOGGED_IN)
                self._renderPostTemplate(helper)
            elif helper.cur_post.post_author != helper.cur_user:
                helper.set_template_field(EDIT_ERROR, NOT_OWN_POST)
                self._renderPostTemplate(helper)
            else:
                self.redirect(POST_ID + post_key + "/edit")
            
class EditPost(Handler):
    '''
    Handles requests to edit posts.
    '''
    def get(self, post_key):
        '''
        Retrieves the current subject and content of a post and renders them
        to a form for editing.
        @param post_key: string id of a BlogPost entity supplied in the URI
        '''
        helper = HandlerHelper(self, (), post_key)
        if helper.is_logged_in:
            self.render(NEW_POST_TEMPLATE, subject=helper.cur_post.post_subject,
                        content=helper.cur_post.post_content)
        else:
            self.redirect(SIGNUP)
        
    def post(self, post_key):
        '''
        Handles submission of edited post form. Validates form data and 
        submits edited content to the database.
        @param post_key: string id of a BlogPost entity supplied in the URI
        '''
        helper = HandlerHelper(self, (SUBJECT, CONTENT), post_key)
        if helper.is_logged_in and helper.is_data_valid:
            BlogPost.update_post(helper.cur_post, helper.valid_data)
            self.redirect(POST_ID + post_key)
        else:
            helper.validate_form_input(NEW_POST_TEMPLATE)
        
class Signup(Handler):
    '''
    Class to handle requests to sign up for a new account.
    '''

    def get(self):
        '''
        Renders the template for signing up for a new account.
        '''
        helper = HandlerHelper(self,())
        if helper.is_logged_in:
            self.redirect(WELCOME)
        else:
            self.render(SIGNUP_TEMPLATE)
        
    def post(self):
        '''
        Receives and validates input from signup form.
        If the visitor signing up for the first time chooses a user name that
        already exists, an error message is generated.
        Otherwise a new user account is created and the user is logged in and
        directed to a welcome page.
        '''
        helper = HandlerHelper(self, (USER, PASSWORD, PWD_VERIFY, EMAIL))
        helper.validate_form_input(SIGNUP_TEMPLATE)
        
        user_entity = User.already_exists(helper.valid_data.get(USER))
        if helper.is_data_valid and user_entity:
            helper.set_template_field(USER + ERROR, "User already exists. Please" +
                                  " choose another user name.")
            self.render(SIGNUP_TEMPLATE, **helper.valid_data)
        elif helper.is_data_valid:
            helper.login_user()
            User.create_new_user(helper.valid_data)
            self.redirect(WELCOME)

class NewComment(Handler):
    '''
    Handles new comment requests.
    '''
    def get(self, post_key):
        '''
        Displays the form to add a new comment to a blog post. If a user 
        attempts to visit this page without being logged in, they are directed
        to the signup page.
        '''
        helper = HandlerHelper(self, (), post_key)
        if helper.is_logged_in:
            self.render(COMMENT_TEMPLATE, current_post=helper.cur_post)
        else:
            self.redirect(SIGNUP)
    
    def post(self, post_key):
        '''
        Handles form submission of new comment.
        '''
        helper = HandlerHelper(self, [CONTENT], post_key)
        helper.validate_form_input(COMMENT_TEMPLATE,
                                   current_post = helper.cur_post)
        if helper.is_data_valid:
            Comment.create_new_comment(helper.cur_user,
                                       post_key, helper.valid_data)
            self.redirect(POST_ID + post_key)
    
class Welcome(Handler):
    '''
    Handles displaying the wecome page after a user has logged in or signed up.
    '''
    def get(self):
        '''
        Displays the wecome page. If a user reaches this page without being 
        logged in, directs them to the signup page.
        '''
        helper = HandlerHelper(self, ())
        if helper.is_logged_in:
            self.render(WELCOME_TEMPLATE, username = helper.cur_user)
        else:
            self.redirect(LOGIN)
                
class Login(Handler):
    '''
    Handles displaying and accepting input from the login form.
    '''
    def get(self):
        '''
        Renders the login page. If a user is already logged in, redirects to
        the welcome page.
        '''
        helper = HandlerHelper(self, ())
        if helper.is_logged_in:
            self.redirect(WELCOME)
        else:
            self.render(LOGIN_TEMPLATE)
    
    def post(self):
        '''
        Handles login requests. Renders appropriate error messages, verifies
        the input password and redirects to welcome page upon successful login.
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
                helper.set_template_field(PASSWORD + ERROR, "Incorrect password.")
                self.render(LOGIN_TEMPLATE, **helper.valid_data)
        elif helper.valid_data:
            helper.set_template_field(USER + ERROR, "That user does not exist.")
            self.render(LOGIN_TEMPLATE, **helper.valid_data)
                
class Logout(Handler):
    def get(self):
        '''
        Logs the user out and redirects to the signup page.
        '''
        CookieUtil.set_cookie(USER, "", self)
        self.redirect(SIGNUP)
        
class FormHelper(object):
    '''
    Class to help process form input. 
    @param hander is the Handler sub-class instance using this class.
    '''
    # Form Input Verification regex (type : regex) where type is one
    # of the defined form input fields above.
    def __init__(self, handler):
        self._regex_table = {
                        USER : r"^[a-zA-Z0-9_-]{3,20}$",
                        PASSWORD: r"^.{3,20}$",
                        PWD_VERIFY : r"^.{3,20}$",
                        EMAIL: r"(^[\S]+@[\S]+.[\S]+$)|(^(?![\s\S]))",
                        SUBJECT : "^.{1,100}$",
                        CONTENT : "^.{1,}$"
                        }
        # Form Input Verification Error Messages
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
        '''
        Helper method.
        If returns true if the form_data is valid, false otherwise.
        field_name - name of the form field.
        '''
        if input_name == PWD_VERIFY:
            return self._handler.get_attribute(
                            PWD_VERIFY) == self._handler.get_attribute(PASSWORD)
        else:
            pattern = re.compile(self._regex_table[input_name])
            return pattern.match(self._handler.get_attribute(input_name))
        
    def validate_form_data(self, args):
        '''
        Checks each input form element to make sure it matches the specified
        requirements and updates the appropriate form output. If the input
        is not correct, generates an error message.
        '''
        to_render = {}
        for input_name in args:
            if not self._is_input_valid(input_name):
                to_render[input_name + ERROR] = self._error_table.get(input_name)
                to_render[input_name] = ""
                self.valid_input = False
            else:
                to_render[input_name] = self._handler.get_attribute(input_name)
        return to_render
        
app = webapp2.WSGIApplication([(HOME, BlogMainPage),
                               (NEWPOST, NewPost),
                               (POSTDISPLAY, BlogPostDisplay),
                               (NEWCOMMENT, NewComment),
                               (EDIT_POST, EditPost),
                               (SIGNUP, Signup),
                               (WELCOME, Welcome),
                               (LOGIN, Login),
                               (LOGOUT, Logout)], debug=True)

