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
    
    def __init__(self, handler):
        self.handler = handler
        
    def set_cookie(self, cookie_name, cookie_value):
        self.handler.response.headers.add_header(
            "Set-Cookie", self.format_cookie(cookie_name, cookie_value))
        
    def hash(self, str_to_hash):
        '''
        Hashes a string value using the hmac algorith using sha256.
        '''
        return str(hmac.new(KEY, str_to_hash, hashlib.sha256).hexdigest())
    
    def value_and_hash(self, value):
        '''
        Takes a string value, hashes it and returns a string in the format
        "value|hash"
        '''
        hashed_value = self.hash(value)
        return_template = "{value}|{hash}"
        return return_template.format(value=value, hash=hashed_value)
    
    def validate_hash(self, value_w_hash):
        '''
        Takes a cookie value and unknown hash in the format "value|hash",
        re-hashes the value, and returns true if the re-hashed value is 
        equivalent to the unknown hash.
        '''
        value_w_hash = value_w_hash.encode("utf-8")
        value = self.get_value(value_w_hash)
        known_hash = value_w_hash[value_w_hash.index("|")+1:]
        if self.hash(value) == known_hash:
            return True
        else:
            return False
    
    def format_cookie(self, name, value):
        '''
        Convenience method that returns a formatted cookie.
        '''
        cookie_template = "{name}={value}; Path=/"
        return cookie_template.format(name=name, value = 
                                      self.value_and_hash(value))
    
    def get_value(self, value_w_hash):
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
        and salt combination stored in the database. This option is ued when
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
    