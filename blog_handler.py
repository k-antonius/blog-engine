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
EDIT = "edit"
COMMENT = "comment"
DELETE = "delete"
POST = "post"
LIKE = "like"
LIKE_TEXT = "like_text"

# Button Names
BUTTONS = ("edit_comment", "delete_comment", "edit_post", 
           "delete_post", "like_post", "comment_post")    

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
            
#     def update_like(self, helper):
#         '''
#         Updates whether a user has liked a blog post in the database. Generates
#         appropriate error messages if a user attempts to like own post or 
#         visitor who isn't logged in attempts to like a post.
#         @param helper: instance of the HandlerHelper class
#         '''
#         LIKE_TEXT = "like_text"
#         LIKE_ERROR =  "like_error"
#         NOT_LOGGED_IN = "You must be logged in to like or unlike a post."
#         LIKE_OWN_POST = "You cannot like your own post."
#         cur_like_value = self.gen_like_text(helper.cur_post, helper.cur_user)
#         
#         if not helper.is_logged_in:
#             helper.set_template_field(LIKE_ERROR, NOT_LOGGED_IN)
#             helper.set_template_field(LIKE_TEXT, cur_like_value)
#             
#         elif helper.cur_user == helper.cur_post.post_author:
#             helper.set_template_field(LIKE_ERROR, LIKE_OWN_POST)
#             helper.set_template_field(LIKE_TEXT, cur_like_value)
#             
#         else:
#             BlogPost.add_like_unlike(helper.cur_post, helper.cur_user, 
#                                      cur_like_value)
#             helper.set_template_field(LIKE_TEXT, 
#                                       self.rev_like_value(cur_like_value))
    
#     def gen_like_text(self, post_entity, cur_user):
#         '''
#         Returns the proper string, "Like" or "Unlike" based on whether the
#         user logged in has like a given post.
#         @param post_entity: the blog post that is the subject of the like/unlike
#         @param cur_user: the user id string of the viewing user
#         @return: appropriate string literal
#         '''
#         if BlogPost.already_liked(post_entity, cur_user):
#             return "Unlike"
#         else:
#             return "Like"
    
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
        self.cur_comment = None
        self.data_error_msgs = None
        self.valid_data = {}
        self.is_data_valid = False
        self._validate_user_input(field_list)
        self.POST_subj = None
        self.POST_action = None
        self.error_type = None
        
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
    
    def _find_author(self):
        '''Gets the author of the subject post or comment.
        '''
        if self.POST_subj == COMMENT:
            return self.cur_comment.author
        else:
            return self.cur_post.post_author
        
    def isCurUserAuthor(self):
        '''Return true if the current user logged in is the author.
        Throw an exception if no user is logged in.
        '''
        return self.cur_user == self._find_author()
    
    def detect_userID_error(self):
        '''Returns boolean value based on whether an error condition exists.
        Errors: Users cannot like own posts, users can only edit and delete
        their own posts and comments.
        '''
        if self.POST_action == LIKE:
            return self.isCurUserAuthor()
        elif self.POST_action == COMMENT:
            return False
        else:
            return not self.isCurUserAuthor()
    
    def gen_error_msg(self):
        '''Generates an error message.
        Args come from button value in POST request.
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
            elif self.POST_action == LIKE:
                return like_own_post.format(postORcomm = self.POST_subj)
            else:
                return not_own_post.format(postORcomm = self.POST_subj)
            
        def _choose_action():
            if self.POST_action == COMMENT:
                return self.POST_action + " on"
            else:
                return self.POST_action
            
        error_msg = base_template.format(status = _choose_error(),
                                    action = _choose_action(),
                                    postORcomm = self.POST_subj)
        self.error_type = self.POST_action + "_" + self.POST_subj + "_error"
        self.set_template_field(self.error_type, error_msg)
        
    def get_request_type(self):
        '''Retrieves a button value from a POST request and updates the
        POST subj, action, and cur_comment fields. Button values are formatted
        action, value, url_safe_key (for pages with multiple entities displayed)
        '''
        get = self.handler.request.get
        for name in BUTTONS:
            if len(get(name)) > 0: # is this button in the request?
                POST_value = get(name)
                temp_list = POST_value.split("_")
                self.POST_action = temp_list[0]
                self.POST_subj = temp_list[1]
                if len(temp_list) > 2:
                    key = ndb.Key(urlsafe=temp_list[2]).get()
                    if self.POST_subj == COMMENT:
                        self.cur_comment = key
                    elif self.POST_action == LIKE:
                        self.cur_post = key
                    elif self.POST_subj == POST:
                        self.cur_post = key
                break
        assert (self.POST_subj and self.POST_action, 
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
            '''Reverse the current like text.
            '''
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
        return self.valid_data.get(self.error_type)

class ErrorHelper(object):
    '''Returns error messages to the template.
    '''
    def __init__(self, error_msg, error_type, entity_id):
        '''Returns new instance holding the error message to render,
        the id of the database entity to which the error relates,
        and the type of the error message, if the target entity has more than
        one error type in the template.
        '''
        self._message = error_msg
        self._error_type = error_type
        self._target_ID = entity_id
        self._like_text_map = None
    
    def get_error(self, current_entity, current_error):
        '''Return an error message if one is required.
        @param current_entity: the database entity whose data is being rendered
        '''
        if ((current_entity.key.urlsafe() == self._target_ID) and
            (current_error == self._error_type)):
            return self._message
        else:
            return ""
        
    def setup_main_page_like_buttons(self, recent_posts, handler):
        '''Setup the like button text for retrieval in the template.
        @param recent_posts: list of posts to render to the template
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
        @param current_post_key: the post to retrieve like text for 
        '''
        return self._like_text_map.get(current_post_key)
        
                
    
class User(ndb.Model):
    '''
    This is a root entity.
    '''
    user_name = ndb.StringProperty(required = True)
    password = ndb.StringProperty(required = True)
    email = ndb.StringProperty()
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    user_picture = ndb.StringProperty()
    posts_made = ndb.IntegerProperty()
    cur_num_posts = ndb.IntegerProperty()
    
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
                            posts_made = 0,
                            cur_num_posts = 0)
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
    def incr_posts_made(cls, user_name):
        '''
        Increment the total number of posts made and the current number of
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
    
    @classmethod
    def get_num_posts(cls, user_name):
        '''
        Given the key id of this user, returns the number of posts this user
        has made.
        '''
        user_key = ndb.Key("User", user_name)
        user = user_key.get()
        return user.posts_made
    
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
    comments_made = ndb.IntegerProperty()
    cur_num_comments = ndb.IntegerProperty()
    
    
    @classmethod
    def create_new_post(cls, user_name, form_data):
        '''
        Creates a new post in the database, setting its subject, content,
        and author. The key for the post is in the form:
        ("User", user_name, "post_id", post_number) post number is the number
        of posts a given user has made.
        An ndb User entity is the parent of every post.
        '''
        
        post_number = str(User.incr_posts_made(user_name))
        new_post = BlogPost(post_subject = form_data.get(SUBJECT),
                            post_content = form_data.get(CONTENT),
                            post_author = user_name,
                            parent = ndb.Key("User", user_name))
        new_post.post_number = post_number
        new_post.key = ndb.Key("User", user_name, "BlogPost", post_number)
        new_post.users_liked = []
        new_post.comments_made = 0
        new_post.cur_num_comments = 0
        new_post_key = new_post.put()
       
        return new_post_key
    
    @classmethod
    def incr_comments_made(cls, post_entity):
        '''
        Increments both the total number of comments made to date on and the
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
        '''
        Increment the current number of comments on this post.
        @param post_entity: the BlogPost entity to be updated.
        '''
        post_entity.cur_num_comments += 1
        post_entity.put()
        return post_entity.cur_num_comments
    
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
    
    @classmethod
    def delete_post(cls, post_entity):
        '''
        Deletes this post entity and decrement the current number of posts
        outstanding for the post's author.
        @param post_entity: the post to be deleted
        '''
        user_entity = ndb.Key("User", post_entity.post_author).get()
        user_entity.cur_num_posts -= 1
        assert user_entity.cur_num_posts >= 0, "Num posts can't be < 0."
        post_entity.key.delete()
        user_entity.put()

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
        comment_num = BlogPost.incr_comments_made(parent_post)
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
        self._render_main_page(helper, ErrorHelper(None, None, None))
    
    def _render_main_page(self, helper, error_helper_inst):
        recent_posts = BlogPost.most_recent_20()
        error_helper_inst.setup_main_page_like_buttons(recent_posts, self)
        self.render(MAIN_PAGE_TEMPLATE, recent_blog_posts = recent_posts,
                    error_helper = error_helper_inst)  
        
    def post(self):
        '''
        - only post request is a like/unlike
        - determine which post is being liked/unliked
        - update using same method is in BlogPostDisplay
        - render page in same was as get method
        '''
        helper = HandlerHelper(self, [])
        helper.get_request_type()
        if (not helper.is_logged_in) or helper.detect_userID_error():
            helper.gen_error_msg()
            error_helper = ErrorHelper(helper.get_button_error(),
                                   helper.error_type,
                                   helper.cur_post.key.urlsafe())
            self._render_main_page(helper, error_helper)
        elif helper.POST_action == LIKE:
            helper.update_like()
            error_helper = ErrorHelper(None, None, None)
            self._render_main_page(helper, error_helper)
        else:
            POST_ROUTE = POST_ID + helper.cur_post.key.urlsafe()
            self.redirect(POST_ROUTE + "/" + COMMENT)             

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
        self._renderPostTemplate(helper, ErrorHelper(None, None, None))
    
    def _choose_template(self, post_entity):
        '''
        Returns the proper template for rendering based on whether this post
        has comments.
        @param post_entity: the BlogPost entity to be rendered
        '''
        if post_entity.cur_num_comments == 0:
            return POST_ONLY_TEMPLATE
        else:
            return POST_WITH_COMMENTS
    
    def _renderPostTemplate(self, helper, error_helper_instance):
        '''Renders a blog post template.
        @param handler: a HandlerHelper instance.
        @param error_helper_instance: an ErrorHelper instance.
        '''
        comments = BlogPost.get_all_comments(helper.cur_post)      
        to_render = dict(current_post = helper.cur_post,
#                     comment_link = self.gen_comment_uri(helper.cur_post),
                    like_text = helper.gen_like_text(),
                    all_comments = comments,
                    error_helper = error_helper_instance)
        to_render.update(helper.valid_data)
        self.render(self._choose_template(helper.cur_post),
                    **to_render)
            
    def post(self, post_key):
        '''Handles requests to like/unlike a post, or edit a post/comment.
        Re-renders the template with appropriate error messages if a user is
        not logged in, attempts to edit another's post, or like own post.
        '''
        helper = HandlerHelper(self, (), post_key)                
        helper.get_request_type()
        if (not helper.is_logged_in) or helper.detect_userID_error():
            
            def _get_cur_action_key():
                '''Return the key of the current POST request's subject.
                '''
                if helper.POST_subj == COMMENT:
                    return helper.cur_comment.key.urlsafe()
                else:
                    return helper.cur_post.key.urlsafe()
                
            helper.gen_error_msg()
            error_helper = ErrorHelper(helper.get_button_error(),
                                       helper.error_type,
                                       _get_cur_action_key())
            self._renderPostTemplate(helper, error_helper)
        elif helper.POST_action == LIKE:
            helper.update_like()
            self._renderPostTemplate(helper, ErrorHelper(None, None, None))
        elif helper.POST_action == DELETE:
                self._delete(helper)
                # simple re-rendering does not give DB time to update.
                # welcome page will list stats for this user
                self.redirect(WELCOME)
        else:
            self.redirect(self._build_edit_route(helper)) 
                
    def _build_edit_route(self, helper):
            '''Builds a route for redirecting to the right URI on an edit 
            request. 
            @param helper: HandlerHelper instance
            '''
            POST_ROUTE = POST_ID + helper.cur_post.key.urlsafe()
            if helper.POST_action == COMMENT:
                return POST_ROUTE + "/" + COMMENT
            else:
                base_template = POST_ROUTE + "{prefix}/edit"
                if helper.POST_subj == COMMENT:
                    return base_template.format(prefix="/comment/" + 
                                                helper.cur_comment.key.urlsafe())
                else:
                    return base_template.format(prefix = "")
        
    def _delete(self, helper):
        '''Determines whether a post or comment is to be deleted and calls
        the appropriate function.
        @param helper: HandlerHelper instance
        '''
        assert (helper.POST_subj == COMMENT or helper.POST_subj == POST,
                "wrong string passed; was:" + helper.POST_subj)
        if helper.POST_subj == COMMENT:
            Comment.delete_comment(helper.cur_comment)
        else:
            BlogPost.delete_post(helper.cur_post)
            
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
            self.render(COMMENT_TEMPLATE, current_post=helper.cur_post,
                        error_helper = ErrorHelper(None, None, None))
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

