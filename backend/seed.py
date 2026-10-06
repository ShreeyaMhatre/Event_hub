from database import Base,engine,SessionLocal
from models import User
from security import hp
from main import seed
Base.metadata.create_all(engine);db=SessionLocal();seed(db)
if not db.query(User).filter_by(email='student@eventhub.test').first():db.add(User(name='Demo Student',email='student@eventhub.test',college_id='DEMO001',password_hash=hp('student123')));db.commit()
print('Demo student: student@eventhub.test / student123');print('Admin: admin / admin123')
