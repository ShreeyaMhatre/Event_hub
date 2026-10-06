from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
import io,hmac,hashlib,uuid
import qrcode
try:
 import razorpay
except ImportError:
 razorpay=None
from fastapi import FastAPI,Depends,HTTPException,Header,Request
from fastapi.responses import HTMLResponse,Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func,update
from sqlalchemy.orm import Session
from pydantic import BaseModel,Field
from config import get_settings
from database import Base,engine,get_db,SessionLocal
from models import *
from security import hp,vp,jwt_make,jwt_read,pass_token,pass_id
s=get_settings(); FRONT=Path(__file__).resolve().parents[1]/'frontend'
class Signup(BaseModel):
    name: str
    email: str
    college_id: str
    password: str = Field(min_length=6)

class Login(BaseModel):
    email: str
    password: str
class RegIn(BaseModel): event_id:int
class OrderIn(BaseModel): registration_id:int
class VerifyPay(BaseModel): registration_id:int; razorpay_order_id:str; razorpay_payment_id:str; razorpay_signature:str
class EventIn(BaseModel): name:str; category:str='GENERAL'; description:str=''; event_date:str; venue:str; starts_at:str; ends_at:str; fee:float=0; capacity:int=500; image:str='images/tech-fest.jpeg'
class QRIn(BaseModel): token:str; event_id:int|None=None

def dt(x): return datetime.fromisoformat(x.replace('Z','+00:00')).replace(tzinfo=None)
def ed(e): return {'id':e.id,'name':e.name,'category':e.category,'description':e.description,'event_date':e.event_date,'venue':e.venue,'fee':e.fee_paise/100,'capacity':e.capacity,'image':e.image,'active':e.active,'starts_at':e.starts_at.isoformat(),'ends_at':e.ends_at.isoformat()}
def rd(r): return {'id':r.id,'event_id':r.event_id,'status':r.status,'amount':r.amount_paise/100,'event':ed(r.event),'pass_id':r.pass_obj.pass_uuid if r.pass_obj else None,'pass_url':f'/pass/{r.pass_obj.pass_uuid}' if r.pass_obj else None}
def user_dep(authorization:str|None=Header(None),db:Session=Depends(get_db)):
 if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Login required')
 try:u=db.get(User,int(jwt_read(authorization[7:])['sub']))
 except: raise HTTPException(401,'Invalid or expired login')
 if not u: raise HTTPException(401,'User not found')
 return u
def admin(x_admin_key:str|None=Header(None)):
 if x_admin_key!=s.ADMIN_PASSWORD: raise HTTPException(401,'Invalid admin key')
def scanner(x_scanner_key:str|None=Header(None)):
 if x_scanner_key!=s.SCANNER_KEY: raise HTTPException(401,'Invalid scanner key')
def issue(db,r):
 if r.pass_obj:return r.pass_obj
 p=EventPass(pass_uuid=str(uuid.uuid4()),registration_id=r.id);db.add(p);db.flush();return p
def seed(db):
 if db.query(Event).count(): return
 db.add_all([Event(name='Tech Fest 2026',category='TECHNOLOGY',description='Technology, innovation and creativity on campus.',event_date='25 September 2026',venue='Conclave',starts_at=datetime(2026,9,25,10),ends_at=datetime(2026,9,25,18),fee_paise=19900,capacity=500,image='images/tech-fest.jpeg'),Event(name='Cultural Night',category='CULTURAL',description='Music, dance, performances and cultural celebrations.',event_date='28 September 2026',venue='Atrium',starts_at=datetime(2026,9,28,17),ends_at=datetime(2026,9,28,22),fee_paise=9900,capacity=800,image='images/cultural-night.jpg'),Event(name='Intercollege Sports',category='SPORTS',description='Intercollege sports and team spirit.',event_date='2 October 2026',venue='Sports Ground',starts_at=datetime(2026,10,2,9),ends_at=datetime(2026,10,2,17),fee_paise=0,capacity=1000,image='images/sports.jpg')]);db.commit()
@asynccontextmanager
async def life(app):
 Base.metadata.create_all(engine)
 with SessionLocal() as db: seed(db)
 yield
app=FastAPI(title='EventHub API',lifespan=life);app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
@app.get('/api/health')
def health():return {'status':'ok'}
@app.post('/api/auth/signup')
def signup(x:Signup,db:Session=Depends(get_db)):
 if db.query(User).filter(func.lower(User.email)==x.email.lower()).first():raise HTTPException(409,'Email already registered')
 u=User(name=x.name,email=x.email.lower(),college_id=x.college_id,password_hash=hp(x.password));db.add(u);db.commit();db.refresh(u);return {'token':jwt_make(u.id),'user':{'id':u.id,'name':u.name,'email':u.email,'college_id':u.college_id}}
@app.post('/api/auth/login')
def login(x:Login,db:Session=Depends(get_db)):
 u=db.query(User).filter(func.lower(User.email)==x.email.lower()).first()
 if not u or not vp(x.password,u.password_hash):raise HTTPException(401,'Invalid email or password')
 return {'token':jwt_make(u.id),'user':{'id':u.id,'name':u.name,'email':u.email,'college_id':u.college_id}}
@app.get('/api/events')
def events(db:Session=Depends(get_db)):return [ed(e) for e in db.query(Event).filter(Event.active==True).order_by(Event.starts_at).all()]
@app.get('/api/events/{eid}')
def event(eid:int,db:Session=Depends(get_db)):
 e=db.get(Event,eid)
 if not e or not e.active:raise HTTPException(404,'Event not found')
 return ed(e)
@app.post('/api/registrations')
@app.post('/api/registrations')
def register(
    x: RegIn,
    u: User = Depends(user_dep),
    db: Session = Depends(get_db)
):
    e = db.get(Event, x.event_id)

    if not e or not e.active:
        raise HTTPException(404, 'Event not found')

    # Check whether this user already has a registration
    existing = (
        db.query(Registration)
        .filter_by(user_id=u.id, event_id=e.id)
        .first()
    )

    if existing:

        # Already completely registered
        if existing.status == 'CONFIRMED':
            return rd(existing)

        # Previous pending registration
        if existing.status == 'PENDING':

            # If the event is FREE, confirm it immediately
            if not e.fee_paise:
                existing.status = 'CONFIRMED'
                existing.confirmed_at = datetime.utcnow()
                issue(db, existing)

                db.commit()
                db.refresh(existing)

            # For paid events, keep it pending so Razorpay can continue
            return rd(existing)

    # Check event capacity
    confirmed_count = (
        db.query(Registration)
        .filter_by(
            event_id=e.id,
            status='CONFIRMED'
        )
        .count()
    )

    if confirmed_count >= e.capacity:
        raise HTTPException(409, 'Event is full')

    # Create new registration
    r = Registration(
        user_id=u.id,
        event_id=e.id,
        amount_paise=e.fee_paise,
        status='PENDING'
    )

    db.add(r)
    db.flush()

    # Free event → confirm immediately
    if not e.fee_paise:
        r.status = 'CONFIRMED'
        r.confirmed_at = datetime.utcnow()
        issue(db, r)

    db.commit()
    db.refresh(r)

    return rd(r)   
 
        
def register(x:RegIn,u:User=Depends(user_dep),db:Session=Depends(get_db)):
 e=db.get(Event,x.event_id)
 if not e or not e.active:raise HTTPException(404,'Event not found')
 if db.query(Registration).filter_by(user_id=u.id,event_id=e.id).first():raise HTTPException(409,'Already registered')
 if db.query(Registration).filter_by(event_id=e.id,status='CONFIRMED').count()>=e.capacity:raise HTTPException(409,'Event is full')
 r=Registration(user_id=u.id,event_id=e.id,amount_paise=e.fee_paise,status='PENDING');db.add(r);db.flush()
 if not e.fee_paise:r.status='CONFIRMED';r.confirmed_at=datetime.utcnow();issue(db,r)
 db.commit();db.refresh(r);return rd(r)
def rp():
 if razorpay is None: raise HTTPException(503,'Install razorpay with pip install -r requirements.txt')
 if not s.RAZORPAY_KEY_ID or not s.RAZORPAY_KEY_SECRET:raise HTTPException(503,'Add Razorpay test keys to backend/.env')
 return razorpay.Client(auth=(s.RAZORPAY_KEY_ID,s.RAZORPAY_KEY_SECRET))
@app.post('/api/payments/order')
def order(x:OrderIn,u:User=Depends(user_dep),db:Session=Depends(get_db)):
 r=db.get(Registration,x.registration_id)
 if not r or r.user_id!=u.id:raise HTTPException(404,'Registration not found')
 if r.status=='CONFIRMED':return rd(r)
 o=rp().order.create({'amount':r.amount_paise,'currency':'INR','receipt':f'eventhub_{r.id}','notes':{'registration_id':str(r.id)}});r.razorpay_order_id=o['id'];db.add(Payment(registration_id=r.id,razorpay_order_id=o['id'],amount_paise=r.amount_paise));db.commit()
 return {'key_id':s.RAZORPAY_KEY_ID,'order_id':o['id'],'amount':r.amount_paise,'currency':'INR','registration_id':r.id,'name':u.name,'email':u.email,'event_name':r.event.name}
@app.post('/api/payments/verify')
def verify(x:VerifyPay,u:User=Depends(user_dep),db:Session=Depends(get_db)):
 r=db.get(Registration,x.registration_id)
 if not r or r.user_id!=u.id:raise HTTPException(404,'Registration not found')
 if r.razorpay_order_id!=x.razorpay_order_id:raise HTTPException(400,'Order mismatch')
 msg=f'{x.razorpay_order_id}|{x.razorpay_payment_id}';ex=hmac.new(s.RAZORPAY_KEY_SECRET.encode(),msg.encode(),hashlib.sha256).hexdigest()
 if not hmac.compare_digest(ex,x.razorpay_signature):raise HTTPException(400,'Invalid payment signature')
 r.status='CONFIRMED';r.razorpay_payment_id=x.razorpay_payment_id;r.confirmed_at=datetime.utcnow();issue(db,r);p=db.query(Payment).filter_by(razorpay_order_id=x.razorpay_order_id).first()
 if p:p.status='SUCCESS';p.razorpay_payment_id=x.razorpay_payment_id
 db.commit();db.refresh(r);return rd(r)
@app.get('/api/registrations/my')
def mine(u:User=Depends(user_dep),db:Session=Depends(get_db)):return [rd(r) for r in db.query(Registration).filter_by(user_id=u.id).order_by(Registration.id.desc()).all()]
@app.get('/pass/{pid}',response_class=HTMLResponse)
def pass_page(pid:str,db:Session=Depends(get_db)):
 p=db.query(EventPass).filter_by(pass_uuid=pid).first()
 if not p:raise HTTPException(404,'Pass not found')
 r=p.registration;e=r.event;t=pass_token(pid)
 return HTMLResponse(f'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>EventHub Pass</title><style>body{{font-family:Arial;background:#090b16;color:#fff;display:grid;place-items:center;min-height:100vh}}.p{{background:#151827;padding:30px;border-radius:25px;max-width:700px;text-align:center}}img{{width:250px;background:white;padding:10px;border-radius:12px}}.muted{{color:#9ca3b5}}</style></head><body><div class=p><h1>🎟️ EventHub Pass</h1><h2>{e.name}</h2><p>{r.user.name} • {r.user.email}</p><p class=muted>{e.event_date} • {e.venue}</p><img src="/pass/{pid}/qr.png"><p class=muted>Show this QR at the entrance</p><a style="color:white" href="/my-registrations.html">← My Passes</a></div></body></html>''')
@app.get('/pass/{pid}/qr.png')
def qr(pid:str,db:Session=Depends(get_db)):
 if not db.query(EventPass).filter_by(pass_uuid=pid).first():raise HTTPException(404,'Pass not found')
 b=io.BytesIO();qrcode.make(pass_token(pid)).save(b,format='PNG');return Response(b.getvalue(),media_type='image/png')
@app.post('/api/verify')
def verify_qr(x:QRIn, _:None=Depends(scanner),db:Session=Depends(get_db)):
 try:pid=pass_id(x.token)
 except:return {'ok':False,'result':'BAD_TOKEN','message':'Invalid EventHub QR code'}
 p=db.query(EventPass).filter_by(pass_uuid=pid).first()
 if not p:return {'ok':False,'result':'NOT_FOUND','message':'Pass not found'}
 r=p.registration;e=r.event
 if x.event_id and e.id!=x.event_id:res,msg='WRONG_EVENT','Wrong event'
 elif p.status=='USED':res,msg='ALREADY_USED','Pass already used'
 elif p.status=='REVOKED':res,msg='REVOKED','Pass revoked'
 elif not s.ALLOW_EARLY_SCAN and (datetime.utcnow()<e.starts_at or datetime.utcnow()>e.ends_at):res,msg='GATE_CLOSED','Gate is closed'
 else:res,msg='VALID','Entry approved. Welcome!'
 if res=='VALID':
  changed=db.execute(update(EventPass).where(EventPass.id==p.id,EventPass.status=='ISSUED').values(status='USED',scanned_at=datetime.utcnow(),scanned_by='Gate A')).rowcount;db.commit()
  if not changed:res,msg='ALREADY_USED','Pass was already used'
 db.add(ScanLog(pass_id=p.pass_uuid,event_id=e.id,result=res,gate='Gate A'));db.commit();return {'ok':res=='VALID','result':res,'message':msg,'holder_name':r.user.name,'event_name':e.name,'pass_id':p.pass_uuid}
@app.post('/api/admin/login')
def alogin(x:Login):
 if x.email!=s.ADMIN_USERNAME or x.password!=s.ADMIN_PASSWORD:raise HTTPException(401,'Invalid admin credentials')
 return {'admin_key':s.ADMIN_PASSWORD}
@app.get('/api/admin/stats')
def stats(_:None=Depends(admin),db:Session=Depends(get_db)):
 total=db.query(Registration).filter_by(status='CONFIRMED').count();present=db.query(EventPass).filter_by(status='USED').count();return {'total_registered':total,'present':present,'absent':max(total-present,0),'attendance_pct':round(present*100/total,1) if total else 0,'events':db.query(Event).filter_by(active=True).count()}
@app.get('/api/admin/events')
def ae(_:None=Depends(admin),db:Session=Depends(get_db)):return [ed(e) for e in db.query(Event).order_by(Event.id.desc()).all()]
@app.post('/api/admin/events')
def ce(x:EventIn,_:None=Depends(admin),db:Session=Depends(get_db)):
 e=Event(name=x.name,category=x.category.upper(),description=x.description,event_date=x.event_date,venue=x.venue,starts_at=dt(x.starts_at),ends_at=dt(x.ends_at),fee_paise=round(x.fee*100),capacity=x.capacity,image=x.image);db.add(e);db.commit();db.refresh(e);return ed(e)
@app.put('/api/admin/events/{eid}')
def ue(eid:int,x:EventIn,_:None=Depends(admin),db:Session=Depends(get_db)):
 e=db.get(Event,eid)
 if not e:raise HTTPException(404,'Event not found')
 for k in ['name','description','event_date','venue','capacity','image']:setattr(e,k,getattr(x,k))
 e.category=x.category.upper();e.starts_at=dt(x.starts_at);e.ends_at=dt(x.ends_at);e.fee_paise=round(x.fee*100);db.commit();return ed(e)
@app.delete('/api/admin/events/{eid}')
def de(eid:int,_:None=Depends(admin),db:Session=Depends(get_db)):
 e=db.get(Event,eid)
 if not e:raise HTTPException(404,'Event not found')
 e.active=False;db.commit();return {'ok':True}
@app.get('/api/admin/registrations')
def ars(_:None=Depends(admin),db:Session=Depends(get_db)):
 return [{'id':r.id,'name':r.user.name,'email':r.user.email,'college_id':r.user.college_id,'event':r.event.name,'status':r.status,'pass_id':r.pass_obj.pass_uuid if r.pass_obj else ''} for r in db.query(Registration).order_by(Registration.id.desc()).all()]
@app.get('/api/admin/attendance')
def att(_:None=Depends(admin),db:Session=Depends(get_db)):
 return [{'name':r.user.name,'college_id':r.user.college_id,'event':r.event.name,'pass_id':r.pass_obj.pass_uuid if r.pass_obj else '','attendance':'Present' if r.pass_obj and r.pass_obj.status=='USED' else 'Absent','scanned_at':r.pass_obj.scanned_at.isoformat() if r.pass_obj and r.pass_obj.scanned_at else None} for r in db.query(Registration).filter_by(status='CONFIRMED').all()]
app.mount('/',StaticFiles(directory=str(FRONT),html=True),name='frontend')
