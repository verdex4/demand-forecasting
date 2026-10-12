import jwt
import bcrypt

# secret = "flsdfj;lsjeoivnxcm,.vkla;jsdakfgka;sjdfg/fs;dfj;lsdj"

# encoded_jwt = jwt.encode({"some": "payload"}, secret, algorithm="HS256")
# print(encoded_jwt)
# r = jwt.decode(encoded_jwt, secret, algorithms=["HS256"])
# print(r)

salt = bcrypt.gensalt()
hash = bcrypt.hashpw("password".encode("utf-8"), salt)
print(hash)
print(bcrypt.checkpw("password".encode("utf-8"), hash))