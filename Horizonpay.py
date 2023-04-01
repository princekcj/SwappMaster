from Swapp.models import User, Transaction, ActiveBid, UserEvents
from Swapp import db, app
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin

admin = Admin(app, name='Swapp', template_mode='bootstrap3')


admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Transaction, db.session))
admin.add_view(ModelView(UserEvents, db.session))
admin.add_view(ModelView(ActiveBid, db.session))

if __name__ == '__main__':
    app.run(debug=True)