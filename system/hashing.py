import hashlib, binascii


def get_safe_hash(pswd='', salt=''):
    byte_pswd = pswd.encode()
    byte_salt = salt.encode()
    hash_ = hashlib.pbkdf2_hmac('sha256', byte_pswd, byte_salt, 10)
    return binascii.hexlify(hash_).decode()


