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
POSTDISPLAY = r"/blog/post_id/(\w+-\w+|\w+)"
NEWCOMMENT = r"/blog/post_id/(\w+-\w+|\w+)/comment"

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
        Returns a blog post entity from url-safe string.
        @param post_string: the url-safe post key string
        @param username: the post-author's username
        '''
        current_user = User.get_by_id(CookieUtil.get_cookie(USER, self))
        post = ndb.Key(urlsafe=post_string)
        return post
    
    def update_like(self):
        '''
        Receives a post request and likes/unlikes a blogpost.
        '''
        to_render = {}
        like_tuple = self.get_like_id_pair()
        author = like_tuple[0]
        post_num = like_tuple[1]
        cur_user = self.logged_in_user()
        
        if not self.logged_in():
            to_render["like_error"] = "You must be logged in to like a post."
        elif cur_user == author:
            to_render["like_error"] = "You cannot like your own post."
        else:
            cur_post = ndb.Key("User", author, "BlogPost", post_num).get()
            cur_like_value = self.get_like_value()
            assert (BlogPost.validate_like(cur_post, cur_user, cur_like_value),
                    "Like status in html and database were inconsistent.")
            BlogPost.add_like_unlike(cur_post, cur_user, cur_like_value)
            to_render["like_text"] = self.rev_like_value(cur_like_value)
            
        return to_render
            
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
        
    def get_like_id_pair(self):
        '''
        Extracts the name of the like button sending the POST request.
        @return: tuple of strings in the format (username, postnumber)
        '''
        post_dict = self.request.POST.items()
        assert ((len(post_dict) == 1), "POST multidict was " +
                "wrong length: " + str(post_dict))
        id_string = post_dict[0][0] # POST from like has 1 key/value
        slice_idx = id_string.find("|")
        return str(id_string[:slice_idx]), str(id_string[slice_idx + 1:])
    
    def get_like_value(self):
        '''
        Gets the value of the like button from the post request.
        '''
        post_dict = self.request.POST.items()
        assert ((len(post_dict) == 1), "POST multidict was " +
                "wrong length: " + str(post_dict))
        id_string = post_dict[0][0]
        return self.request.get(id_string)
        
    
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
            secured_pwd = cls.secure_password(form_data.get(PASSWORD))
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
        return cls.get_by_id(user_name)
        
    
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
    def secure_password(cls, clear_text):
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
    post_number = ndb.IntegerProperty()
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
        
        post_number = User.increment_num_posts(user_name)
        new_post = BlogPost(post_subject = form_data.get(SUBJECT),
                            post_content = form_data.get(CONTENT),
                            post_author = user_name,
                            parent = ndb.Key("User", user_name))
        new_post.post_number = post_number
        new_post.key = ndb.Key("User", user_name, "BlogPost", str(post_number))
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
            post_entity.users_liked.apppend(user_name)
        else:
            post_entity.users_liked.remove(user_name)
        post_entity.put()
        
    @classmethod
    def already_liked(cls, post_entity, user_name):
        '''
        Returns boolean value whether given user has liked a blog post.
        @param post_entity: the subject post
        @param user_name: the user to test
        '''
        return user_name in post_entity.users_liked
    
    @classmethod
    def validate_like(cls, post_entity, user_name, like_request):
        '''
        Returns a boolean value based on whether the current like request
        is consistent with the database.
        @param post_entity: the post being liked/unliked
        @param user_name: the user attempting to like the post
        @param like_request: a string, like or unlike request
        @return: True if the request matches the database, 
        '''
        return ((self.already_liked(post_entity, user_name) and 
                 like_request == "Like")
                or
                (not self.already_liked(post_entity, user_name) and 
                 like_request == "Unlike"))

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
    def get(self):
        
        all_posts = BlogPost.all()
        all_posts.order('date_created')
        self.render(MAIN_PAGE_TEMPLATE, blog_posts = all_posts)

class NewPost(Handler):
    
    def get(self):
        '''
        Renders the new post form on an initial request.
        '''
        self.render(NEW_POST_TEMPLATE)
        user_name = self._check_logged_in(SIGNUP)
        
    def post(self):
        '''
        Takes input from the new post form, validates the input, and 
        adds a new entity to the database, storing the information from
        the new blog post.
        '''
        user_name = self._check_logged_in(SIGNUP)
        if user_name:
            valid_data = self._validate_user_input(SUBJECT, CONTENT)
            if self._was_valid(valid_data):
                new_post_key = BlogPost.create_new_post(user_name, 
                                                        self._get_form_data(valid_data))
                self.redirect('/blog/post_id/' + new_post_key.urlsafe())
            else:
                self.render(NEW_POST_TEMPLATE, **self._get_form_data(valid_data))
    
        
class BlogPostDisplay(Handler):
    def get(self, post_id):
        '''
        Renders an individual blog post an all comments made on that post.
        '''
        current_blog_post = self.get_cur_post(post_id)
        comment_url = post_id + "/comment"
         # set button_name, like_text which are based on state of 
        # blog post entity
        b_name = (current_blog_post.post_author + "|" + 
                  str(current_blog_post.post_number))
        l_value = BlogPost.already_liked(current_blog_post, 
                                    CookieUtil.get_cookie(USER, self))
        l_text = self.like_button_text(l_value)
        
        
        if current_blog_post.num_comments == 0:
            self.render(POST_ONLY_TEMPLATE, current_post=current_blog_post,
                        comment_link=comment_url,
                        button_name= b_name,
                        like_text =l_text,
                        like_value=l_value)
        else:
            comments_query = Comment.query(ancestor=current_blog_post_key)
            comments = comments_query.order(-Comment.date_created).fetch()
            self.render(POST_WITH_COMMENTS, all_comments=comments,
                        current_post = current_blog_post, 
                        comment_link=comment_url,
                        button_name= b_name,
                        like_text =l_text,
                        like_value=l_value)
            
    def post(self, post_id):
        '''
        Handles like and unliking of an individual post.
        '''
        to_render = self.update_like()
        self.render()
        
        
class Signup(Handler):
    '''
    Class to handle requests to sign up for a new account.
    '''

    def get(self):
        '''
        Renders the template for signing up for a new account.
        '''
        # Add check for a logged in user and redirect.
        self.render(SIGNUP_TEMPLATE)
        
    def post(self):
        '''
        Receives and validates input from signup form.
        If the visitor signing up for the first time chooses a user name that
        already exists, an error message is generated.
        Otherwise a new user account is created and the user is logged in and
        directed to a welcome page.
        '''
        form_data = self._validate_user_input(USER, PASSWORD, PWD_VERIFY,
                                                    EMAIL)
        
        if self._was_valid(form_data):
            valid_form_data = self._get_form_data(form_data)
            if User.already_exists(valid_form_data.get(USER)):
                valid_form_data[USER + ERROR] = ("User already exists. Please" +
                                       " choose another user name.")
                self.render(SIGNUP_TEMPLATE, **valid_form_data)
            else:
                CookieUtil.set_cookie(USER, valid_form_data.get(USER), self)
                pwd_helper = PwdUtil(valid_form_data.get(PASSWORD))
                valid_form_data[PASSWORD] = pwd_helper.new_pwd_salt_pair()
                User.create_new_user(valid_form_data)
                self.redirect(WELCOME)
        else:
            self.render(SIGNUP_TEMPLATE, **self._get_form_data(form_data))

class NewComment(Handler):
    '''
    Handles new comment requests.
    '''
    def get(self, post_key):
        '''
        Renders the new comment html.
        '''
        if self._check_logged_in(SIGNUP):
            current_user = User.get_by_id(CookieUtil.get_cookie(USER, self))
            post = ndb.Key(urlsafe=post_key)
            self.render(COMMENT_TEMPLATE, current_post=post.get())
    
    def post(self, *args):
        '''
        Handles form submission of new comment.
        '''
        user_name = self._check_logged_in(SIGNUP)
        if user_name:
            valid_data = self._validate_user_input(CONTENT)
            if self._was_valid(valid_data):
                post_key_string = args[0]
                new_comment_key = Comment.create_new_comment(user_name,
                                                             post_key_string,
                                                             self._get_form_data(valid_data))
                self.redirect('/blog/post_id/' + post_key_string)
            else:
                to_render = self._get_form_data(valid_data)
                to_render["current_post"] = self.get_cur_post(args[0])
                self.render(COMMENT_TEMPLATE, **to_render)
                                                             
    
class Welcome(Handler):
    def get(self):
        username = CookieUtil.get_cookie(USER, self)
        if username:
            self.render(WELCOME_TEMPLATE, username = username)
        else:
            self.redirect(LOGIN) # Eventually change for to allow 
                                         # for either signup or login
                
class Login(Handler):
    def get(self):
        '''
        Renders the login page. If a user is already logged in, redirects to
        the welcome page.
        '''
        if CookieUtil.get_cookie(USER, self):
            self.redirect(WELCOME)
        self.render(LOGIN_TEMPLATE)
    
    def post(self):
        '''
        Receives data input into login form. Verifies that input against
        regular expressions and then the database. Redirects the user to
        the welcome page if login was successful.
        '''
        form_data = self._validate_user_input(USER, PASSWORD)
        if self._was_valid(form_data):
            valid_form_data = self._get_form_data(form_data)
            current_user = User.already_exists(valid_form_data.get(USER))
            if current_user:
                pwd_helper = PwdUtil(valid_form_data.get(PASSWORD), 
                                     current_user.password)
                if pwd_helper.verify_password():
                    CookieUtil.set_cookie(USER, valid_form_data.get(USER), self)
                    self.redirect(WELCOME)
                else:
                    valid_form_data["password_error"] = "Incorrect password."
                    self.render(LOGIN_TEMPLATE, **valid_form_data)
            else:
                valid_form_data["username_error"] = "That user does not exist."
                self.render(LOGIN_TEMPLATE, **valid_form_data)
        else:
            self.render(LOGIN_TEMPLATE, **self._get_form_data(form_data))
                
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
                        SUBJECT : "You must have a subject of less than" 
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
                               (SIGNUP, Signup),
                               (WELCOME, Welcome),
                               (LOGIN, Login),
                               (LOGOUT, Logout)], debug=True)

