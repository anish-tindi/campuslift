from flask import Flask, render_template, request, redirect, url_for, session
from database import db, User, Ride
from werkzeug.security import generate_password_hash, check_password_hash
from flask_dance.contrib.google import make_google_blueprint, google
import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'campuslift-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campuslift.db'

# Google OAuth setup
google_bp = make_google_blueprint(
    client_id='41706192550-e8c5nibveun805f61u7v08nrttklmkf3.apps.googleusercontent.com',
    client_secret='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',
    redirect_to='google_login',
    scope=['profile', 'email']
)
app.register_blueprint(google_bp, url_prefix='/login')

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        student_id = request.form['student_id']
        password = generate_password_hash(request.form['password'])

        if not email.endswith('.ac.in') and not email.endswith('edu.in'):
            return render_template('register.html', error='Use your college email only.')

        existing = User.query.filter_by(email=email).first()
        if existing:
            return render_template('register.html', error='Email already registered.')

        user = User(name=name, email=email, phone=phone,
                    student_id=student_id, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('home'))

    return render_template('register.html', error=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Wrong email or password.')

    return render_template('login.html', error=None)

@app.route('/google-login')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))
    
    resp = google.get('/oauth2/v2/userinfo')
    if not resp.ok:
        return redirect(url_for('login'))
    
    google_info = resp.json()
    email = google_info['email']
    name = google_info['name']

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            name=name,
            email=email,
            phone='Not provided',
            student_id='Google',
            password=generate_password_hash('google-auth')
        )
        db.session.add(user)
        db.session.commit()

    session['user_id'] = user.id
    session['user_name'] = user.name
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['user_name'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/offer-ride', methods=['GET', 'POST'])
def offer_ride():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        destination = request.form['destination']
        departure_time = request.form['departure_time']
        seats = request.form['seats']
        charge = request.form['charge']

        ride = Ride(
            user_id=session['user_id'],
            destination=destination,
            departure_time=departure_time,
            seats=int(seats),
            charge=charge
        )
        db.session.add(ride)
        db.session.commit()
        return redirect(url_for('find_ride'))

    return render_template('offer_ride.html')

@app.route('/find-ride')
def find_ride():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    if search:
        rides = Ride.query.filter(
            Ride.destination.ilike(f'%{search}%')
        ).all()
    else:
        rides = Ride.query.order_by(Ride.created_at.desc()).all()

    return render_template('find_ride.html', rides=rides, search=search)

@app.route('/sos')
def sos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('sos.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)