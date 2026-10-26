import hashlib
import json
import secrets
first = "0" * 64
def hasher(data: dict,prev_hash: str):
   
    curr = {"data": data, "prev_hash": prev_hash}
    curr_json = json.dumps(curr, sort_keys=True, default=str)

    return hashlib.sha256(curr_json.encode("utf-8")).hexdigest()

def gen_token():
    token = secrets.token_urlsafe(32)
    return token

def hashtoken(raw):
    hash_token = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return hash_token

def verify(data: dict, prev_hash: str, curr_hash: str):
    if hasher(data,prev_hash) == curr_hash:
        return True
    else:
        return False
    
# verification
#p = "12345"
#print(hasher(p,first))
#u = "123 5"
#print(hasher(u,first))
