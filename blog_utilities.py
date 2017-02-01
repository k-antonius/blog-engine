'''
Created on Jan 14, 2017

@author: kennethalamantia
'''

import hashlib
import hmac
import random
import string

KEY = "fatfriend"
class CookieUtil(object):
    '''
    This is a utility class to be used in support of the blog_handler module.
    It provides a number of methods to set, get, and hash cookies.
    The constructor takes an instance of the Handler object as a parameter.
    This class must be instantiated within a Handler object to be used.
    '''
    
    @classmethod    
    def set_cookie(cls, cookie_name, cookie_value, handler):
        '''
        Sets a cookie, giving it a name and value.
        '''
        handler.response.headers.add_header(
            "Set-Cookie", cls._format_cookie(cookie_name, cookie_value))
    
    @classmethod    
    def get_cookie(cls, cookie_name, handler):
        '''
        Retrives a cookie with @param name from the response header of the 
        handler object. Will return the cookie value if a cookie with name 
        exists, is not empty, and is a validly hashed cookie, otherwise returns
        None.
        '''
        cookie = handler.request.cookies.get(cookie_name)
        if (cookie and not cls._is_empty(cookie) 
                   and cls._validate_cookie(cookie)):
            return cls._get_value(cookie)
        else:
            return None
    
    @classmethod    
    def _is_empty(cls, cookie):
        '''
        Given a cookie string, @param cookie, will return true if the cookie
        value is empty, false otherwise
        '''
        return len(cls._get_value(cookie)) < 1
     
    @classmethod
    def _hash(cls, str_to_hash):
        '''
        Hashes a string value using the hmac algorith using sha256.
        '''
        return str(hmac.new(KEY, str_to_hash, hashlib.sha256).hexdigest())
    
    @classmethod
    def _value_and_hash(cls, value):
        '''
        Takes a string value, hashes it and returns a string in the format
        "value|hash"
        '''
        hashed_value = cls._hash(value)
        return_template = "{value}|{hash}"
        return return_template.format(value=value, hash=hashed_value)
    
    @classmethod
    def _validate_cookie(cls, value_w_hash):
        '''
        Takes a cookie value and unknown hash in the format "value|hash",
        re-hashes the value, and returns true if the re-hashed value is 
        equivalent to the unknown hash.
        '''
        value_w_hash = value_w_hash.encode("utf-8")
        value = cls._get_value(value_w_hash)
        known_hash = value_w_hash[value_w_hash.index("|")+1:]
        if cls._hash(value) == known_hash:
            return True
        else:
            return False
    
    @classmethod
    def _format_cookie(cls, name, value):
        '''
        Convenience method that returns a formatted cookie.
        '''
        cookie_template = "{name}={value}; Path=/"
        if value == "":
            new_value = value
        else:
            new_value = cls._value_and_hash(value)
        return cookie_template.format(name=name, value = new_value)
    
    @classmethod
    def _get_value(cls, value_w_hash):
        '''
        Given an input in the format "value|hash" extracts and returns only the
        value part preceding the pipe character.
        '''
        slice_idx = value_w_hash.index("|")
        return value_w_hash[:slice_idx]

class PwdUtil(object):
    '''
    Class to create salted, hashed passwords for storing in database and for
    checking whether an input password matches an already created password.
    '''    
    
    def __init__(self, clear_text, db_password = None):
        '''
        Takes clear_text and returns a hashed version of that text.
        Takes an optional parameter db_password, which is the hashed password
        and salt combination stored in the database. This option is used when
        verifying a password is correct.
        '''
        
        self.new_salt = None
        self.existing_password = None
        self.existing_salt = None
        if db_password:
            self._extract_pwd_salt(db_password)
        self.hashed_text = self._hash_salt(clear_text)
        
    
    def _hash_salt(self, clear_text):
        '''
        Helper method that hashes and salts a password. For new passwords,
        it makes a new salt. For existing passwords, it uses the salt passed
        in the constructor.
        '''
        hashed_output = None
        if self.existing_password:
            hashed_output = "".join(hashlib.sha256(clear_text + 
                                               self.existing_salt).hexdigest())
        else:
            generator = random.SystemRandom()
            SALT_LEN = 5
            possible_chars = string.letters + string.digits
            new_salt = "".join(generator.choice(possible_chars) 
                               for dummy_idx in range(SALT_LEN))
            hashed_output = "".join(hashlib.sha256(clear_text + 
                                                   new_salt).hexdigest()) 
            self.new_salt = new_salt
        return hashed_output
    
    def verify_password(self):
        '''
        Compares existing password with the unknown password input into the 
        constructor. Returns a boolean value. If this method is called but
        no db_password was passed to the constructor, None will be returned. 
        '''
        if self.existing_password:
            return self.existing_password == self.hashed_text
        else:
            return None
    
    def new_pwd_salt_pair(self):
        '''
        Convenience method that returns the hashed password/salt combination
        for storing in the database.
        '''
        if self.new_salt:
            return self.hashed_text + "," + self.new_salt
        
    def _extract_pwd_salt(self, pwd_and_salt):
        '''
        Convenience method that slices off the salt from the [password,salt]
        pair stored in the database. Stores the resulting parts.
        '''
        slice_idx = pwd_and_salt.rfind(",")
        self.existing_salt = pwd_and_salt[slice_idx + 1:]
        self.existing_password = pwd_and_salt[:slice_idx]    
    