'''
Library of classes that supports password and cookie hashing and secure
setting and retrieval of cookies.

Created on Jan 14, 2017
@author: kennethalamantia
'''

import hashlib
import hmac
import random
import string
import secure_key

# secure key used in hashing
KEY = secure_key.KEY


class CookieUtil(object):
    '''Class providing a number of methods to set, get, and hash cookies.
    Cookies are a string in the format "name=value|hash" where name is the
    unique name of the cookie, value is the plain-text value of the cookie,
    and hash is the hashed version of the value. The hash and the value are
    always separated by the "|" character. Use of the word "cookie" throughout
    this class assumes this format is observed.
    '''

    @classmethod
    def set_cookie(cls, cookie_name, cookie_value, handler):
        '''Sets a secured cookie, giving it a name and value in the header
        of a webapp2 response object.
        @param cookie_name: name given to this cookie
        @param value: the value the cookie holds, pass "" to clear cookie
        @param handler: a webapp2 handler instance
        '''
        handler.response.headers.add_header(
            "Set-Cookie", cls._format_cookie(cookie_name, cookie_value))

    @classmethod
    def get_cookie(cls, cookie_name, handler):
        '''Validates and retrieves the value of a cookie, if valid.
        @param cookie_name: the name of the cookie to retrieve from the handler
        @param handler: the webapp2 request handler holding the cookie
        @return: str value of the cookie or None if cookie was invalid
        '''
        cookie = handler.request.cookies.get(cookie_name)
        if (cookie and not cls._is_empty(cookie)
                and cls._validate_cookie(cookie)):
            return cls._get_value(cookie)
        else:
            return None

    @classmethod
    def _is_empty(cls, cookie):
        '''Returns a boolean value indicating whether the cookie value is an
        empty string.
        @param cookie: cookie in the format described in this class' docstring
        '''
        return len(cls._get_value(cookie)) < 1

    @classmethod
    def _hash(cls, str_to_hash):
        '''Hashes a string value. Requiresthe KEY constant that uses a
        definition from another module.
        @param str_to_hash: the str that needs hashing
        @return: the hashed version of the str
        '''
        return str(hmac.new(KEY, str_to_hash, hashlib.sha256).hexdigest())

    @classmethod
    def _value_and_hash(cls, value):
        '''Hashes and formats the cookie value.
        @param value: the unhashed cookie value to hash
        @return: a string in the format "value|hash"
        '''
        hashed_value = cls._hash(value)
        return_template = "{value}|{hash}"
        return return_template.format(value=value, hash=hashed_value)

    @classmethod
    def _validate_cookie(cls, value_w_hash):
        '''Checks the hash of a pre-existing cookie.
        @param value_w_hash: cookie value with unknown hash
        @return: boolean true if hash valid, false otherwise
        '''
        value_w_hash = value_w_hash.encode("utf-8")
        value = cls._get_value(value_w_hash)
        known_hash = value_w_hash[value_w_hash.index("|") + 1:]
        return cls._hash(value) == known_hash

    @classmethod
    def _format_cookie(cls, name, value):
        '''Returns a formatted cookie.
        @param name: the name of the cookie
        @param value: value|hash pair str or "" if the cookie is being cleared
        @return: cookie
        '''
        cookie_template = "{name}={value}; Path=/"
        if value == "":
            new_value = value
        else:
            new_value = cls._value_and_hash(value)
        return cookie_template.format(name=name, value=new_value)

    @classmethod
    def _get_value(cls, value_w_hash):
        '''Retrieve the part of the value preceding the "|"char.
        '''
        slice_idx = value_w_hash.index("|")
        return value_w_hash[:slice_idx]


class PwdUtil(object):
    '''Class to create salted, hashed passwords for storing in database and for
    checking whether an input password matches an already created password.
    Attributes:
        _new_salt: randomly generated salt used to hash new passwords
        _existing_password: hashed password that comes from database
        _existing_salt: password salt that comes from the database
        _hashed_text: the newly hashed password
    '''

    def __init__(self, clear_text, db_password=None):
        '''Hashes a new password from clear text or compares a password to
        the password and salt stored in the database.
        @param clear_text: the password in clear text
        @param db_password: the hashed password and salt from the database,
        pass this parameter if checking the validity of a preexisting password.
        '''
        self._new_salt = None
        self._existing_password = None
        self._existing_salt = None
        if db_password:
            self._extract_pwd_salt(db_password)
        self._hashed_text = self._hash_salt(clear_text)

    def _hash_salt(self, clear_text):
        '''Returns a salted and hashed password, either based on a new
        randomly generated salt or an existing one. Updates the _new_salt
        class field if necessary.
        @param clear_text: the text to be hashed
        @return: a hashed and salted password
        '''
        hashed_output = None
        if self._existing_password:
            hashed_output = "".join(hashlib.sha256(
                clear_text + self._existing_salt).hexdigest())
        else:
            generator = random.SystemRandom()
            SALT_LEN = 5
            possible_chars = string.letters + string.digits
            new_salt = "".join(generator.choice(possible_chars)
                               for dummy_idx in range(SALT_LEN))
            hashed_output = "".join(hashlib.sha256(
                clear_text + new_salt).hexdigest())
            self._new_salt = new_salt
        return hashed_output

    def verify_password(self):
        '''Compares existing password with the unknown password input into the
        constructor. Returns a boolean value. If this method is called but
        no db_password was passed to the constructor, None will be returned.
        '''
        if self._existing_password:
            return self._existing_password == self._hashed_text
        else:
            return None

    def new_pwd_salt_pair(self):
        '''Returns the hashed password/salt combination
        for storing in the database.
        '''
        if self._new_salt:
            return self._hashed_text + "," + self._new_salt

    def _extract_pwd_salt(self, pwd_and_salt):
        '''Splits the "password,salt" string at the ",". Stores each part
        in the respective class fields.
        @param pwd_and_salt: string in the form "password,salt"
        '''
        slice_idx = pwd_and_salt.rfind(",")
        self._existing_salt = pwd_and_salt[slice_idx + 1:]
        self._existing_password = pwd_and_salt[:slice_idx]
