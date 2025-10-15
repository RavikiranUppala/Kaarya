from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from DataModels import RegisteredUsers, db, JobPosts, SkillCenters, WillingCandisate
from passlib.hash import bcrypt
from datetime import datetime
import pgeocode
import os


App = Flask(__name__)
App.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Build absolute SQLite path and ensure directory exists (prevents 'unable to open database file')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)
DB_PATH = os.path.join(INSTANCE_DIR, 'KaaryaInfo.db')
App.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
App.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

BLUE_COLLER_JOBS = ["Electricians","Plumbers","Welders","Carpenters","Construction workers","Mechanics","Painters",
    "Lorry Drivers","Drivers (car & Bike)","Delivery Executives","Loading Workers","Factory Workers","Machine Operators",
    "Garment Workers","Packers & Helpers","Flooring Workers","Housekeeping Staff","Security Guards","Gardeners",
    "Agricultural Laborers","Dairy & Poultry Workers","Shop Assistants","Cashiers", "Not in List"]

db.init_app(App)
nomi = pgeocode.Nominatim('IN')

with App.app_context():
    db.create_all()
    # Safe runtime migration: add DESCRIPTION column to JobPosts if missing (SQLite)
    try:
        from sqlalchemy import text
        # Use a direct connection to avoid implicit session transaction issues
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info('JobPosts')")).fetchall()
            column_names = {row[1] for row in result}
            if 'DESCRIPTION' not in column_names:
                conn.execute(text("ALTER TABLE JobPosts ADD COLUMN DESCRIPTION TEXT"))
            # Add new optional fields if missing
            if 'WORK_FROM' not in column_names:
                conn.execute(text("ALTER TABLE JobPosts ADD COLUMN WORK_FROM VARCHAR(10)"))
            if 'WORK_TO' not in column_names:
                conn.execute(text("ALTER TABLE JobPosts ADD COLUMN WORK_TO VARCHAR(10)"))
            if 'SALARY_PM' not in column_names:
                conn.execute(text("ALTER TABLE JobPosts ADD COLUMN SALARY_PM INTEGER"))
            if 'ONE_TIME_PAY' not in column_names:
                conn.execute(text("ALTER TABLE JobPosts ADD COLUMN ONE_TIME_PAY INTEGER"))
            if 'PART_FROM_DATE' not in column_names:
                conn.execute(text("ALTER TABLE JobPosts ADD COLUMN PART_FROM_DATE DATE"))
            if 'PART_TO_DATE' not in column_names:
                conn.execute(text("ALTER TABLE JobPosts ADD COLUMN PART_TO_DATE DATE"))
            conn.commit()
    except Exception:
        # Intentionally swallow to avoid breaking app start; Home route would fail otherwise
        pass
    
    # Safe runtime migration: ensure WillingCandisate table and CONNECT column exist (SQLite)
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS WillingCandisate (\n                ID INTEGER PRIMARY KEY AUTOINCREMENT,\n                POST_ID INTEGER NOT NULL,\n                CANDIDATE_USERID VARCHAR(150) NOT NULL,\n                APPLIED_AT DATETIME NOT NULL,\n                CONNECT BOOLEAN NOT NULL DEFAULT 0\n            )"))
            result = conn.execute(text("PRAGMA table_info('WillingCandisate')")).fetchall()
            column_names = {row[1] for row in result}
            if 'CONNECT' not in column_names:
                conn.execute(text("ALTER TABLE WillingCandisate ADD COLUMN CONNECT BOOLEAN NOT NULL DEFAULT 0"))
            conn.commit()
    except Exception:
        # Avoid crashing app if migration fails; features depending on it will show error page
        pass
    
#User ID Generation

def GenerateUserID():
    Present = RegisteredUsers.query.count()
    return f"KYUSER{Present+1}"

# Function to Compute Distance
def ComputesDistance(pin_from, pin_to):
    loc_from = nomi.query_postal_code(pin_from)
    loc_to = nomi.query_postal_code(pin_to)
    
    if loc_from is None or loc_to is None or loc_from.latitude is None or loc_to.latitude is None:
        return {"distance_km": 0, "duration_min": 0}
    
    # Simple distance calculation (Haversine formula)
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r
    
    distance_km = haversine(loc_from.longitude, loc_from.latitude, loc_to.longitude, loc_to.latitude)
    duration_min = distance_km * 2  # Rough estimate: 2 minutes per km
    
    return {
        "distance_km": round(distance_km, 2),
        "duration_min": round(duration_min, 1)
    }
# Function to Compute Distance

@App.route("/get_cities", methods=["POST"])
def get_cities():
    try:
        data = request.get_json()
        pin = data.get('pin')
        
        print(f"Received PIN code: {pin}")  # Debug print
        
        if not pin or len(pin) < 6:
            print("PIN code too short or empty")
            return jsonify({"cities": [], "error": "PIN code must be 6 digits"})
        
        # Ensure PIN is exactly 6 digits
        if len(pin) != 6:
            print("PIN code not exactly 6 digits")
            return jsonify({"cities": [], "error": "PIN code must be exactly 6 digits"})
        
        print(f"Querying pgeocode for PIN: {pin}")
        location = nomi.query_postal_code(pin)
        print(f"Location result: {location}")
        
        if location is not None and hasattr(location, 'place_name') and location.place_name:
            print(f"Found place name: {location.place_name}")
            # Split by comma to get multiple cities if available
            cities = [city.strip() for city in str(location.place_name).split(',') if city.strip()]
            return jsonify({"cities": cities})
        else:
            print("No location found for this PIN code")
            return jsonify({"cities": [], "error": "No cities found for this PIN code"})
            
    except Exception as e:
        print(f"Error in get_cities: {str(e)}")
        return jsonify({"cities": [], "error": f"Error: {str(e)}"})

@App.route("/Home/Myposts")
def MyPosts():
    UserData = RegisteredUsers.query.filter_by(EMAIL = session.get("Email")).first()
    UserPosts = JobPosts.query.filter_by(POSTBY = UserData.USERID).all()
    return render_template("MyPosts.html" , Allposts = UserPosts,  UserName = session.get("Name")   )


@App.route('/Home/WillingCandidates/<int:post_id>')
def WillingCandidates(post_id: int):
    if not session.get("IslogedIn"):
        return redirect(url_for("LoginPage"))

    post = JobPosts.query.filter_by(ID=post_id, POSTBY=session.get("UserID")).first()
    if not post:
        return render_template("error.html", Error=f"Post #{post_id} not found or not owned by you")

    candidates = []
    try:
        applied = WillingCandisate.query.filter_by(POST_ID=post.ID).all()
        user_ids = [wc.CANDIDATE_USERID for wc in applied]
        if user_ids:
            users = RegisteredUsers.query.filter(RegisteredUsers.USERID.in_(user_ids)).all()
            user_map = {u.USERID: u for u in users}
            for wc in applied:
                user = user_map.get(wc.CANDIDATE_USERID)
                if not user:
                    continue
                dist_info = ComputesDistance(user.PINCODE, post.PINCODE)
                candidates.append({
                    "name": user.NAME,
                    "email": user.EMAIL,
                    "phone": user.PHONE,
                    "address": user.ADDRESS,
                    "pincode": user.PINCODE,
                    "qualification": user.QUALIFICATION,
                    "skills": user.SKILLS,
                    "distance_km": dist_info["distance_km"],
                    "connect": wc.CONNECT,
                    "user_id": user.USERID,
                })
    except Exception:
        candidates = []

    return render_template(
        "WillingCandisate.html",
        UserName=session.get("Name"),
        post=post,
        candidates=candidates,
    )

@App.route('/Home/WillingCandidates/<int:post_id>/connect', methods=['POST'])
def SetConnectedCandidate(post_id: int):
    if not session.get("IslogedIn"):
        return redirect(url_for("LoginPage"))

    # Ensure the requester owns the post
    post = JobPosts.query.filter_by(ID=post_id, POSTBY=session.get("UserID")).first()
    if not post:
        return render_template("error.html", Error=f"Post #{post_id} not found or not owned by you")

    try:
        data = request.get_json(silent=True) or {}
        candidate_userid = data.get('candidate_userid')

        # First, clear all existing connections for this post
        all_wc = WillingCandisate.query.filter_by(POST_ID=post.ID).all()
        for wc in all_wc:
            wc.CONNECT = False

        selected = None
        if candidate_userid:
            selected = WillingCandisate.query.filter_by(
                POST_ID=post.ID,
                CANDIDATE_USERID=candidate_userid
            ).first()
            if selected:
                selected.CONNECT = True

        db.session.commit()

        return jsonify({
            "status": "ok",
            "connected_userid": selected.CANDIDATE_USERID if selected else None
        })
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error"}), 500

@App.route("/", methods=["GET", "POST"])
def LoginPage():
    if request.method == "POST":
        try:
            username = request.form.get("user_email")
            password = request.form.get("user_code")
            
            if not username or not password:
                return render_template("Login.html", Error = "Email and password are required")
            
            IsValidUser = RegisteredUsers.query.filter_by(EMAIL = username).first()
            if IsValidUser and bcrypt.verify(password, IsValidUser.PASSWORD):
                session["IslogedIn"] = True
                session["Name"] = IsValidUser.NAME
                session["Email"] = IsValidUser.EMAIL
                session["UserID"] = IsValidUser.USERID
                return redirect(url_for("HomePage"))
            else:
                return render_template("Login.html", Error = "Invalid Login Details")
        except Exception as e:
            return render_template("Login.html", Error = "Login failed. Please try again.")
        
    return render_template("Login.html")

@App.route("/register", methods=["GET", "POST"])
def Register():
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        qualification = request.form.get("qualification")
        address = request.form.get("city")
        pincode = request.form.get("pincode")
        password = request.form.get("password")
        confirmpassword = request.form.get("confirmpassword")
        aadharnumber = request.form.get("aadharnumber")
        postdistance = request.form.get("distance")
        # file = request.files["aadharfile"]
        skills1 = request.form.get("skill1")
        skills2 = request.form.get("skill2")
        skills3 = request.form.get("skill3")

        # Validate password confirmation
        if password != confirmpassword:
            return render_template("Register.html", bluecollorjobs = BLUE_COLLER_JOBS, error="Passwords do not match")
        
        # Check if email already exists
        existing_user = RegisteredUsers.query.filter_by(EMAIL=email).first()
        if existing_user:
            return render_template("Register.html", bluecollorjobs = BLUE_COLLER_JOBS, error="Email already registered")
        
        # Check if phone already exists
        existing_phone = RegisteredUsers.query.filter_by(PHONE=phone).first()
        if existing_phone:
            return render_template("Register.html", bluecollorjobs = BLUE_COLLER_JOBS, error="Phone number already registered")
        
        # Check if Aadhar already exists
        existing_aadhar = RegisteredUsers.query.filter_by(AADHAR_NO=aadharnumber).first()
        if existing_aadhar:
            return render_template("Register.html", bluecollorjobs = BLUE_COLLER_JOBS, error="Aadhar number already registered")
        
        try:
            NewUser = RegisteredUsers(NAME = name, EMAIL = email, ADDRESS = address,PINCODE = pincode, PHONE = phone, AADHAR_NO = aadharnumber, 
                        QUALIFICATION = qualification, PASSWORD = bcrypt.hash(password) , SKILLS = f"{skills1},{skills2},{skills3}", 
                        DISTANCE = postdistance, USERID = GenerateUserID())
            
            db.session.add(NewUser)
            db.session.commit()
            return redirect(url_for('LoginPage'))
        except Exception as e:
            db.session.rollback()
            return render_template("Register.html", bluecollorjobs = BLUE_COLLER_JOBS, error="Registration failed. Please try again.")
    return render_template("Register.html", bluecollorjobs = BLUE_COLLER_JOBS, error=request.args.get('error', ''))


@App.route("/Home")
def HomePage():
    if session.get("IslogedIn"):
        Userdetails = RegisteredUsers.query.filter_by(EMAIL = session.get("Email")).first()
        UsersSkills = str(Userdetails.SKILLS).split(',')
        Userlocation = Userdetails.PINCODE
        UserWillingDist = Userdetails.DISTANCE
        RelatedPosts = JobPosts.query.filter(JobPosts.POSTBY != session.get("UserID")).all()

        # Determine which posts the current user has already applied to
        try:
            related_ids = [p.ID for p in RelatedPosts]
            applied_rows = []
            if related_ids:
                applied_rows = WillingCandisate.query.filter(
                    WillingCandisate.POST_ID.in_(related_ids),
                    WillingCandisate.CANDIDATE_USERID == session.get("UserID")
                ).all()
            applied_post_ids = {row.POST_ID for row in applied_rows}
        except Exception:
            applied_post_ids = set()

        Result = []
        for post in RelatedPosts:
            Dist = ComputesDistance(Userlocation, post.PINCODE)
            if Dist["distance_km"] <= UserWillingDist  and post.POSTNAME in UsersSkills:
                # Precompute a safe 50-word preview for the template
                try:
                    if post.DESCRIPTION:
                        _words = str(post.DESCRIPTION).split()
                        preview = " ".join(_words[:50])
                        if len(_words) > 50:
                            preview += "..."
                        setattr(post, "DESC_PREVIEW", preview)
                    else:
                        setattr(post, "DESC_PREVIEW", "")
                except Exception:
                    setattr(post, "DESC_PREVIEW", str(post.DESCRIPTION) if post.DESCRIPTION else "")
                # Mark whether current user has already applied to this post
                try:
                    setattr(post, "ALREADY_APPLIED", post.ID in applied_post_ids)
                except Exception:
                    setattr(post, "ALREADY_APPLIED", False)
                Result.append(post)

        return render_template("Home.html", UserName = session.get("Name"), AllRelated = Result)
    else:
        return redirect(url_for("LoginPage"))


@App.route("/Home/Apply/<int:post_id>", methods=["POST"])
def ApplyForPost(post_id: int):
    if not session.get("IslogedIn"):
        return redirect(url_for("LoginPage"))

    post = JobPosts.query.filter_by(ID=post_id).first()
    if not post:
        return render_template("error.html", Error=f"Post #{post_id} not found")

    # Prevent applying to own post
    if post.POSTBY == session.get("UserID"):
        return render_template("error.html", Error="You cannot apply to your own post")

    existing = WillingCandisate.query.filter_by(POST_ID=post.ID, CANDIDATE_USERID=session.get("UserID")).first()
    if existing:
        return redirect(url_for("HomePage"))

    try:
        wc = WillingCandisate(
            POST_ID=post.ID,
            CANDIDATE_USERID=session.get("UserID"),
            APPLIED_AT=datetime.utcnow(),
            CONNECT=False
        )
        db.session.add(wc)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return render_template("error.html", Error="Failed to apply. Please try again.")

    return redirect(url_for("HomePage"))

@App.route("/Home/Apply/<int:post_id>/cancel", methods=["POST"])
def CancelApplication(post_id: int):
    if not session.get("IslogedIn"):
        return redirect(url_for("LoginPage"))

    post = JobPosts.query.filter_by(ID=post_id).first()
    if not post:
        return render_template("error.html", Error=f"Post #{post_id} not found")

    try:
        existing = WillingCandisate.query.filter_by(POST_ID=post.ID, CANDIDATE_USERID=session.get("UserID")).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            # For fetch callers, return simple JSON
            return jsonify({"status": "cancelled"}), 200
        # Nothing to cancel; still return success for idempotency
        return jsonify({"status": "not_applied"}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error"}), 500

@App.route("/Home/Post" , methods=["GET", "POST"])
def PostAJob():
    if session.get("IslogedIn"):
        if request.method == "POST":
            try:
                postfor = request.form.get("postfor")
                postpincode = request.form.get("postcode")
                postlocation = request.form.get("city")
                postcontact = request.form.get("postcont")
                posttype = request.form.get("postype")
                postenddate = request.form.get("duedate")
                postdesc = request.form.get("description")
                work_from = request.form.get("work_from")
                work_to = request.form.get("work_to")
                salary_pm = request.form.get("salary_pm")
                one_time_pay = request.form.get("one_time_pay")
                part_from_date = request.form.get("part_from_date")
                part_to_date = request.form.get("part_to_date")
                
                # Validate required fields
                if not all([postfor, postpincode, postlocation, postcontact, posttype, postenddate]):
                    return render_template("Post.html", UserName = session.get("Name"), Allposts = BLUE_COLLER_JOBS, error="All fields are required")
                
                # Conditional validation
                if posttype in ["Full Time", "Part Time"]:
                    if not all([work_from, work_to, salary_pm]):
                        return render_template("Post.html", UserName=session.get("Name"), Allposts=BLUE_COLLER_JOBS, error="Please provide working hours and monthly salary")
                    try:
                        salary_pm_val = int(salary_pm)
                    except Exception:
                        return render_template("Post.html", UserName=session.get("Name"), Allposts=BLUE_COLLER_JOBS, error="Salary per month must be a number")
                    # For part time, dates are required
                    part_from_val = None
                    part_to_val = None
                    if posttype == "Part Time":
                        if not all([part_from_date, part_to_date]):
                            return render_template("Post.html", UserName=session.get("Name"), Allposts=BLUE_COLLER_JOBS, error="Please provide part-time from and to dates")
                        try:
                            part_from_val = datetime.strptime(part_from_date, "%Y-%m-%d").date()
                            part_to_val = datetime.strptime(part_to_date, "%Y-%m-%d").date()
                            if part_from_val > part_to_val:
                                return render_template("Post.html", UserName=session.get("Name"), Allposts=BLUE_COLLER_JOBS, error="Part-time from date cannot be after to date")
                        except Exception:
                            return render_template("Post.html", UserName=session.get("Name"), Allposts=BLUE_COLLER_JOBS, error="Invalid part-time dates")
                    one_time_pay_val = None
                elif posttype == "One Time":
                    if not one_time_pay:
                        return render_template("Post.html", UserName=session.get("Name"), Allposts=BLUE_COLLER_JOBS, error="Please provide one-time pay amount")
                    try:
                        one_time_pay_val = int(one_time_pay)
                    except Exception:
                        return render_template("Post.html", UserName=session.get("Name"), Allposts=BLUE_COLLER_JOBS, error="One-time pay must be a number")
                    salary_pm_val = None
                    work_from = None
                    work_to = None
                    part_from_val = None
                    part_to_val = None
                else:
                    salary_pm_val = None
                    one_time_pay_val = None
                    work_from = None
                    work_to = None
                    part_from_val = None
                    part_to_val = None

                postduedate = datetime.strptime(postenddate, "%Y-%m-%d").date()
                NewPost = JobPosts(POSTNAME = postfor, LOCATION = postlocation, PINCODE = postpincode, PHONE = postcontact, 
                                   POSTTYPE = posttype, DESCRIPTION = postdesc, POSTLASTDATE = postduedate, POSTBY = session.get("UserID"),
                                   WORK_FROM=work_from, WORK_TO=work_to, SALARY_PM=salary_pm_val, ONE_TIME_PAY=one_time_pay_val,
                                   PART_FROM_DATE=part_from_val, PART_TO_DATE=part_to_val)
                db.session.add(NewPost)
                db.session.commit()
                return render_template("Post.html", UserName = session.get("Name"), Allposts = BLUE_COLLER_JOBS, success="Job posted successfully!")
            except ValueError:
                return render_template("Post.html", UserName = session.get("Name"), Allposts = BLUE_COLLER_JOBS, error="Invalid date format")
            except Exception as e:
                db.session.rollback()
                return render_template("Post.html", UserName = session.get("Name"), Allposts = BLUE_COLLER_JOBS, error="Failed to post job. Please try again.")
        
        return render_template("Post.html", UserName = session.get("Name"), Allposts = BLUE_COLLER_JOBS)
    else:
        return redirect(url_for("LoginPage"))
    

@App.route("/Home/EditPost/<int:post_id>", methods=["GET", "POST"])
def EditPost(post_id: int):
    if not session.get("IslogedIn"):
        return redirect(url_for("LoginPage"))

    post = JobPosts.query.filter_by(ID=post_id, POSTBY=session.get("UserID")).first()
    if not post:
        return render_template("error.html", Error=f"Post #{post_id} not found or not owned by you")

    if request.method == "POST":
        try:
            postfor = request.form.get("postfor")
            postpincode = request.form.get("postcode")
            postlocation = request.form.get("city")
            postcontact = request.form.get("postcont")
            posttype = request.form.get("postype")
            postenddate = request.form.get("duedate")
            postdesc = request.form.get("description")
            work_from = request.form.get("work_from")
            work_to = request.form.get("work_to")
            salary_pm = request.form.get("salary_pm")
            one_time_pay = request.form.get("one_time_pay")
            part_from_date = request.form.get("part_from_date")
            part_to_date = request.form.get("part_to_date")
            work_from = request.form.get("work_from")
            work_to = request.form.get("work_to")
            salary_pm = request.form.get("salary_pm")
            one_time_pay = request.form.get("one_time_pay")

            if not all([postfor, postpincode, postlocation, postcontact, posttype, postenddate]):
                return render_template(
                    "EditPost.html",
                    UserName=session.get("Name"),
                    Allposts=BLUE_COLLER_JOBS,
                    post=post,
                    error="All fields are required"
                )

            # Conditional validation and assignment
            if posttype in ["Full Time", "Part Time"]:
                if not all([work_from, work_to, salary_pm]):
                    return render_template(
                        "EditPost.html",
                        UserName=session.get("Name"),
                        Allposts=BLUE_COLLER_JOBS,
                        post=post,
                        error="Please provide working hours and monthly salary"
                    )
                try:
                    salary_pm_val = int(salary_pm)
                except Exception:
                    return render_template(
                        "EditPost.html",
                        UserName=session.get("Name"),
                        Allposts=BLUE_COLLER_JOBS,
                        post=post,
                        error="Salary per month must be a number"
                    )
                post.WORK_FROM = work_from
                post.WORK_TO = work_to
                post.SALARY_PM = salary_pm_val
                post.ONE_TIME_PAY = None
            elif posttype == "One Time":
                if not one_time_pay:
                    return render_template(
                        "EditPost.html",
                        UserName=session.get("Name"),
                        Allposts=BLUE_COLLER_JOBS,
                        post=post,
                        error="Please provide one-time pay amount"
                    )
                try:
                    one_time_pay_val = int(one_time_pay)
                except Exception:
                    return render_template(
                        "EditPost.html",
                        UserName=session.get("Name"),
                        Allposts=BLUE_COLLER_JOBS,
                        post=post,
                        error="One-time pay must be a number"
                    )
                post.WORK_FROM = None
                post.WORK_TO = None
                post.SALARY_PM = None
                post.ONE_TIME_PAY = one_time_pay_val
            else:
                post.WORK_FROM = None
                post.WORK_TO = None
                post.SALARY_PM = None
                post.ONE_TIME_PAY = None

            # Conditional validation and assignment
            if posttype in ["Full Time", "Part Time"]:
                if not all([work_from, work_to, salary_pm]):
                    return render_template(
                        "EditPost.html",
                        UserName=session.get("Name"),
                        Allposts=BLUE_COLLER_JOBS,
                        post=post,
                        error="Please provide working hours and monthly salary"
                    )
                try:
                    salary_pm_val = int(salary_pm)
                except Exception:
                    return render_template(
                        "EditPost.html",
                        UserName=session.get("Name"),
                        Allposts=BLUE_COLLER_JOBS,
                        post=post,
                        error="Salary per month must be a number"
                    )
                post.WORK_FROM = work_from
                post.WORK_TO = work_to
                post.SALARY_PM = salary_pm_val
                post.ONE_TIME_PAY = None
                # For part time, handle dates
                if posttype == "Part Time":
                    if not all([part_from_date, part_to_date]):
                        return render_template(
                            "EditPost.html",
                            UserName=session.get("Name"),
                            Allposts=BLUE_COLLER_JOBS,
                            post=post,
                            error="Please provide part-time from and to dates"
                        )
                    try:
                        part_from_val = datetime.strptime(part_from_date, "%Y-%m-%d").date()
                        part_to_val = datetime.strptime(part_to_date, "%Y-%m-%d").date()
                        if part_from_val > part_to_val:
                            return render_template(
                                "EditPost.html",
                                UserName=session.get("Name"),
                                Allposts=BLUE_COLLER_JOBS,
                                post=post,
                                error="Part-time from date cannot be after to date"
                            )
                    except Exception:
                        return render_template(
                            "EditPost.html",
                            UserName=session.get("Name"),
                            Allposts=BLUE_COLLER_JOBS,
                            post=post,
                            error="Invalid part-time dates"
                        )
                    post.PART_FROM_DATE = part_from_val
                    post.PART_TO_DATE = part_to_val
                else:
                    post.PART_FROM_DATE = None
                    post.PART_TO_DATE = None
            elif posttype == "One Time":
                if not one_time_pay:
                    return render_template(
                        "EditPost.html",
                        UserName=session.get("Name"),
                        Allposts=BLUE_COLLER_JOBS,
                        post=post,
                        error="Please provide one-time pay amount"
                    )
                try:
                    one_time_pay_val = int(one_time_pay)
                except Exception:
                    return render_template(
                        "EditPost.html",
                        UserName=session.get("Name"),
                        Allposts=BLUE_COLLER_JOBS,
                        post=post,
                        error="One-time pay must be a number"
                    )
                post.WORK_FROM = None
                post.WORK_TO = None
                post.SALARY_PM = None
                post.ONE_TIME_PAY = one_time_pay_val
                post.PART_FROM_DATE = None
                post.PART_TO_DATE = None
            else:
                post.WORK_FROM = None
                post.WORK_TO = None
                post.SALARY_PM = None
                post.ONE_TIME_PAY = None
                post.PART_FROM_DATE = None
                post.PART_TO_DATE = None

            post.POSTNAME = postfor
            post.PINCODE = postpincode
            post.LOCATION = postlocation
            post.PHONE = postcontact
            post.POSTTYPE = posttype
            post.POSTLASTDATE = datetime.strptime(postenddate, "%Y-%m-%d").date()
            post.DESCRIPTION = postdesc

            db.session.commit()
            return redirect(url_for("MyPosts"))
        except ValueError:
            return render_template(
                "EditPost.html",
                UserName=session.get("Name"),
                Allposts=BLUE_COLLER_JOBS,
                post=post,
                error="Invalid date format"
            )
        except Exception:
            db.session.rollback()
            return render_template(
                "EditPost.html",
                UserName=session.get("Name"),
                Allposts=BLUE_COLLER_JOBS,
                post=post,
                error="Failed to update post. Please try again."
            )

    return render_template(
        "EditPost.html",
        UserName=session.get("Name"),
        Allposts=BLUE_COLLER_JOBS,
        post=post
    )

@App.route("/Home/Upgrade")
def Upgrade():
    AllSkillcenters = SkillCenters.query.all()
    return render_template("Upgrade.html", UserName = session.get("Name"), allcenters = AllSkillcenters)


@App.route("/Home/Profile", methods = ["POST", "GET"])
def Profile():
    UserData = RegisteredUsers.query.filter_by(EMAIL = session.get("Email")).first()

    return render_template("Profile.html", UserName = session.get("Name"), bluecollorjobs = BLUE_COLLER_JOBS, ProfileData = UserData)


@App.route("/SignOut")
def Signout():
    session.clear()
    return redirect(url_for("LoginPage"))


if __name__ == "__main__":
    App.run(debug=True, host="0.0.0.0", port=5000)