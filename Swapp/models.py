from Swapp import db, login_manager, app
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from flask_login import UserMixin
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    location = db.Column(db.String(120), unique=False, nullable=False)
    is_superuser = db.Column(db.Boolean, nullable=True, default= False)
    phone = db.Column(db.String(120), unique=True, nullable=False)
    user_events = db.relationship('UserEvents', backref='UserEvents', lazy=True)
    password = db.Column(db.String(60), nullable=False)
    transactions = db.relationship('Transaction', primaryjoin="and_(User.id==Transaction.Requester_user_id, User.id==Transaction.RequestAcceptor_user_id)", lazy=True)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)



    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Transaction(db.Model):
    __tablename__ = 'Transaction'
    id = db.Column(db.Integer, primary_key=True)
    Requester_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    Requester_username = db.relationship('User', backref=db.backref('requested_transactions', uselist=False, lazy='joined'), foreign_keys=[Requester_user_id])

    RequestAcceptor_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    RequestAcceptor_username = db.relationship('User', backref=db.backref('accepted_transactions', uselist=False, lazy='joined'), foreign_keys=[RequestAcceptor_user_id ])
    RequestAmount = db.Column(db.Integer, nullable=False)
    Rate = db.Column(db.Integer, nullable=False)
    BaseCurrency = db.Column(db.String, nullable=False)
    NewCurrency = db.Column(db.String, nullable=False)
    Fufilled = db.Column(db.Boolean, nullable=False)
    AcceptedRequest = db.Column(db.Boolean, nullable=False)
    date_accepted = db.Column(db.DateTime, nullable=True)
    RequesterAcceptorCompletion = db.Column(db.Boolean, nullable=False)
    RequesterCompletion = db.Column(db.Boolean, nullable=False)
    Active_bids = db.relationship("ActiveBid", primaryjoin="and_(Transaction.id==ActiveBid.request_id)", lazy=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
       return f"Transaction('{self.id}' ,'{self.Requester_username}','{self.Requester_user_id}','{self.Fufilled}','{self.AcceptedRequest}' ,'{self.RequestAmount}','{self.BaseCurrency}','{self.NewCurrency}', '{self.RequestAcceptor_username}', '{self.date_posted}')"

class ActiveBid(db.Model):
    __tablename__ = 'ActiveBid'

    id = db.Column(db.Integer, primary_key=True)
    request_owner = db.relationship('Transaction', backref='active_bids', lazy=True)
    bidder_user_id = db.Column(db.Integer, nullable=False)
    BidAmount = db.Column(db.Integer, nullable=False)
    BidRate = db.Column(db.Integer, nullable=False)
    BidCurrency = db.Column(db.String, nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey("Transaction.id"))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    still_active = db.Column(db.Boolean, nullable=False)
    status = db.Column(db.String, nullable=False)


    def __repr__(self):
       return f"ActiveBid('{self.id}' ,'{self.bidder_user_id}','{self.BidAmount}','{self.still_active}','{self.BidCurrency}','{self.date_posted}')"



class UserEvents(db.Model):
    __tablename__ = 'UserEvents'
    id = db.Column(db.Integer, primary_key=True)
    _user_idOfEvents = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    _usernameOfEvents = db.relationship('User', backref=db.backref('events', uselist=False, lazy='joined'), foreign_keys=[_user_idOfEvents])
    with_id = db.Column(db.Integer, nullable=False)
    corresponding_event_id = db.Column(db.Integer, nullable=False)
    event_type = db.Column(db.String, nullable=False)
    event_content = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    amount = db.Column(db.Integer)
    proposed_rate = db.Column(db.Integer)
    attachment = db.Column(db.String)
    proof_of_pay = db.Column(db.String)
    exchangebasecurrency = db.Column(db.String)
    exchangenewcurrency = db.Column(db.String)
    date_occurred = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
       return f"UserEvents('{self.id}' ,'{self._user_idOfEvents}','{self.event_type}','{self.event_content}','{self.status}','{self.exchangebasecurrency}','{self.exchangenewcurrency}','{self.date_occurred}')"


with app.app_context():
    db.create_all()
