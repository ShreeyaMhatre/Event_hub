import base64,hashlib,hmac,os,time,jwt
from config import get_settings
def hp(p):
 salt=os.urandom(16); d=hashlib.pbkdf2_hmac('sha256',p.encode(),salt,310000); return 'pbkdf2$310000$'+base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(d).decode()
def vp(p,x):
 try:
  _,it,s,d=x.split('$'); a=hashlib.pbkdf2_hmac('sha256',p.encode(),base64.urlsafe_b64decode(s),int(it)); return hmac.compare_digest(a,base64.urlsafe_b64decode(d))
 except: return False
def jwt_make(uid): return jwt.encode({'sub':str(uid),'exp':int(time.time())+86400},get_settings().JWT_SECRET,algorithm='HS256')
def jwt_read(t): return jwt.decode(t,get_settings().JWT_SECRET,algorithms=['HS256'])
def pass_token(uid):
 body='EVP1.'+uid; sig=hmac.new(get_settings().PASS_SECRET.encode(),body.encode(),hashlib.sha256).hexdigest()[:32]; return body+'.'+sig
def pass_id(t):
 p=(t or '').split('.');
 if len(p)!=3 or p[0]!='EVP1': raise ValueError()
 body='.'.join(p[:2]); ex=hmac.new(get_settings().PASS_SECRET.encode(),body.encode(),hashlib.sha256).hexdigest()[:32]
 if not hmac.compare_digest(ex,p[2]): raise ValueError()
 return p[1]
