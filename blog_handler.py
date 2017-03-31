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
EDIT_COMMENT = r"/blog/post_id/(\w+-\w+|\w+)/comment/(\w+-\w+|\w+)/edit"
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

    def render(self, template, **template_fields):
        '''
        Prepares a template for rendering and renders the template.
        @param template: the template html
        @param template_files: dictionary of arguments where keys match
        template variables and values are the strings to render in place of
        those variables.
        '''
        def render_template():
            '''
            Helper function to load and render template.
            '''
            template_to_render = JINJA.get_template(template)
            return template_to_render.render(template_fields)
        self.response.out.write(render_template())
            
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
        if cur_like_value == "Like":
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
    
    @classmethod
    def entity_from_uri(cls, comment_uri_key):
        '''
        Returns the comment entity from a uri key string.
        @param comment_uri_key: the url safe key string
        '''
        return ndb.Key(urlsafe=comment_uri_key).get()
    
    @classmethod
    def update_comment(cls, comment_entity, form_data):
        '''
        Updates the content field of a Comment.
        '''
        comment_entity.content = form_data[CONTENT]
        comment_entity.put()
        return comment_entity

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
    
    def _renderPostTemplate(self, helper, comment_key = None,
                            error_type = None):
        '''
        Renders a blog post template.
        @param handler: a HandlerHelper instance.
        @param comment_key: comment whose error msg needs updating
        @param error_type: "edit" or "delete" string literal used to update
            correct error message field in the template.
        '''
        comments = BlogPost.get_all_comments(helper.cur_post)
        
        def _build_error_map():
            '''
            Returns a mapping of URL safe comment entity keys to empty strings.
            '''
            error_map = dict()
            for comment in comments:
                error_map.update({comment.key.urlsafe() : dict(edit_comment_error = "",
                                                               delete_comment_error = "")})
            return error_map
        
        error_map = _build_error_map()
        
        def _update_error_map():
            '''
            Updates the mapping of comment entity key strings to map an error
            message to the correct comment. 
            '''
            error_msg = helper.valid_data.get(error_type)
            if error_msg and ("comment" in error_msg):
                sub_dict = error_map.get(comment_key)
                sub_dict.update(dict({error_type : error_msg}))
                error_map.update({comment_key : sub_dict})
        
        _update_error_map()       
        to_render = dict(current_post = helper.cur_post,
                    comment_link = self.gen_comment_uri(helper.cur_post),
                    like_text = self.gen_like_text(helper.cur_post, 
                                                   helper.cur_user),
                    all_comments = comments,
                    error_map = error_map)
        to_render.update(helper.valid_data)
        self.render(self._choose_template(helper.cur_post),
                    **to_render)
            
    def post(self, post_key):
        '''
        Handles requests to like/unlike a post, or edit a post/comment.
        Re-renders the template with appropriate error messages if a user is
        not logged in, attempts to edit another's post, or like own post.
        '''
        LIKE = "like_button"
        EDIT_POST = "edit_post"
        EDIT_COMMENT = "edit_comment"
        EDIT_ERROR = "edit_error"
        COM_ERROR = "edit_comment_error"
        COM_DEL_ERROR = "delete_comment_error"
        POST_DEL_ERROR = "delete_error"
        DEL_POST = "delete_post"
        DEL_COMMENT = "delete_comment"
        POST_ROUTE = POST_ID + post_key
        helper = HandlerHelper(self, (), post_key)
        edit_c = self.request.get(EDIT_COMMENT)
        del_c = self.request.get(DEL_COMMENT)
        
        # Begin helper functions ------
        def _edit_request(edit_type, error_type, author, route, 
                          comment_key = None):
            '''
            Process an edit request, format an error message or redirect to the
            appropriate handler.
            @param edit_type: "post" or "comment"
            @param error_type: name of the error template field
            @param comment_key: if the edit request is a comment edit request,
            the key string of the comment entity must be supplied
            '''
            def _format_error_msgs(subject):
                '''
                Formats the error messages for attempting to edit a post/comment
                while not logged in or not an author.
                @param subject: "post" or "comment"
                '''
                not_logged_in = "logged in"
                not_own_post = "a {subj_type}'s author"
                
                def _choose_error():
                    '''
                    Selects the correct error message.
                    '''
                    if helper.is_logged_in:
                        return not_logged_in
                    else:
                        return not_own_post
                def _choose_action():
                    if ((error_type == POST_DEL_ERROR) or 
                        (error_type == COM_DEL_ERROR)):
                        return "delete"
                    else:
                        return "edit"
                    
                error_type_base = ("You must be " + _choose_error() + 
                                   " to " + _choose_action() 
                                   + " a {subj_type}.")
                    
                return error_type_base.format(error_condition = _choose_error(), 
                                          subj_type = subject)
                
            if not helper.is_logged_in or (author != helper.cur_user):
                    helper.set_template_field(error_type, 
                                              _format_error_msgs(edit_type))
                    self._renderPostTemplate(helper, comment_key, error_type)
            else:
                if error_type == POST_DEL_ERROR:
                    helper.cur_post.key.delete()
                elif error_type == COM_DEL_ERROR:
                    ndb.Key(urlsafe=del_c).delete()
                self.redirect(route)
        # End helper functions -------
        
        if self.request.get(LIKE):
            self.update_like(helper)
            self._renderPostTemplate(helper)
                
        elif self.request.get(EDIT_POST):
            route = POST_ROUTE + "/edit"
            author = helper.cur_post.post_author
            _edit_request("post", EDIT_ERROR, author, route)
            
        elif edit_c:
            route = POST_ROUTE + "/comment/" + edit_c + "/edit"
            author = Comment.entity_from_uri(edit_c).author
            _edit_request("comment", COM_ERROR, author, route, edit_c)
        
        elif self.request.get(DEL_POST):
             author = helper.cur_post.post_author
             _edit_request("post", POST_DEL_ERROR, author, WELCOME)
        
        elif del_c:
            author = Comment.entity_from_uri(del_c).author
            _edit_request("comment", COM_DEL_ERROR, author, POST_ROUTE, del_c)
            
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
            
class EditComment(Handler):
    '''
    Handles requests to edit a comment.
    @constant POST_KEY: URI supplied id of the post entity parent, always the 
        first in the list hence constant 0.
    @constant COM_KEY: same thing but with a comment entity child, always
        second item in the list.
    '''
    POST_KEY = 0
    COM_KEY = 1
    
    def get(self, *key_list):
        '''
        Retrieves the content of a comment and renders it to a form for 
        editing.
        @param post_key: string id of a BlogPost entity supplied in the URI
        '''
        helper = HandlerHelper(self, (), key_list[self.POST_KEY])
        if helper.is_logged_in:
            cur_comment = Comment.entity_from_uri(key_list[self.COM_KEY])
            self.render(COMMENT_TEMPLATE, current_post=helper.cur_post,
                        content=cur_comment.content)
        else: self.redirect(SIGNUP)
    
    def post(self, *key_list):
        '''
        Handles submission of edited comment form. Validates data submitted and
        updates the database.
        '''
        helper = HandlerHelper(self, [CONTENT], key_list[self.POST_KEY])
        if helper.is_logged_in and helper.is_data_valid:
            cur_comment = Comment.entity_from_uri(key_list[self.COM_KEY])
            Comment.update_comment(cur_comment, helper.valid_data)
            self.redirect(POST_ID + key_list[self.POST_KEY])
        else:
            helper.validate_form_input(COMMENT_TEMPLATE,
                                       current_post = helper.cur_post)
        
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
            return self._handler.request.get(
                            PWD_VERIFY) == self._handler.request.get(PASSWORD)
        else:
            pattern = re.compile(self._regex_table[input_name])
            return pattern.match(self._handler.request.get(input_name))
        
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
                to_render[input_name] = self._handler.request.get(input_name)
        return to_render
        
app = webapp2.WSGIApplication([(HOME, BlogMainPage),
                               (NEWPOST, NewPost),
                               (POSTDISPLAY, BlogPostDisplay),
                               (NEWCOMMENT, NewComment),
                               (EDIT_COMMENT, EditComment),
                               (EDIT_POST, EditPost),
                               (SIGNUP, Signup),
                               (WELCOME, Welcome),
                               (LOGIN, Login),
                               (LOGOUT, Logout)], debug=True)

