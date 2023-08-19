from flask_login import current_user
from Swapp.models import User, Transaction, ActiveBid, UserEvents
from Swapp import db, app
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin

class SuperuserModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_superuser

admin = Admin(app, name='Swapp', template_mode='bootstrap3')

admin.add_view(SuperuserModelView(User, db.session))
admin.add_view(SuperuserModelView(Transaction, db.session))
admin.add_view(SuperuserModelView(UserEvents, db.session))
admin.add_view(SuperuserModelView(ActiveBid, db.session))

if __name__ == '__main__':
    app.run(debug=False)





