from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class RegisteredUsers(db.Model):
    __tablename__ = "RegisteredUsers"
    ID = db.Column(db.Integer, primary_key=True)
    NAME = db.Column(db.String(150), nullable=False)
    EMAIL = db.Column(db.String(120), unique=True, nullable=False)
    ADDRESS = db.Column(db.String(250), nullable=False)
    PINCODE = db.Column(db.String(15), nullable=False)
    PHONE = db.Column(db.String(15), nullable=False, unique=True)
    AADHAR_NO = db.Column(db.String(12), nullable=False, unique=True)
    QUALIFICATION = db.Column(db.String(100), nullable=False)
    PASSWORD = db.Column(db.String(120), nullable=False)
    SKILLS = db.Column(db.String(250), nullable=False)
    DISTANCE = db.Column(db.Integer, nullable=False)
    USERID = db.Column(db.String(150), nullable=False)


class JobPosts(db.Model):
    __tablename__ = "JobPosts"
    ID = db.Column(db.Integer, primary_key=True)
    POSTNAME = db.Column(db.String(150), nullable=False)
    LOCATION = db.Column(db.String(120), nullable=False)
    PINCODE = db.Column(db.String(250), nullable=False)
    PHONE = db.Column(db.String(15), nullable=False)
    POSTTYPE = db.Column(db.String(120), nullable=False)
    DESCRIPTION = db.Column(db.Text, nullable=True)
    POSTLASTDATE = db.Column(db.Date, nullable=False)
    POSTBY = db.Column(db.String(150), nullable=False)
    # Optional fields depending on POSTTYPE
    WORK_FROM = db.Column(db.String(10), nullable=True)  # HH:MM (24h)
    WORK_TO = db.Column(db.String(10), nullable=True)    # HH:MM (24h)
    SALARY_PM = db.Column(db.Integer, nullable=True)     # Salary per month
    ONE_TIME_PAY = db.Column(db.Integer, nullable=True)  # One-time payout amount
    PART_FROM_DATE = db.Column(db.Date, nullable=True)   # Part-time start date
    PART_TO_DATE = db.Column(db.Date, nullable=True)     # Part-time end date

class SkillCenters(db.Model):
    __tablename__ = "SkillDevelopment"
    ID = db.Column(db.Integer, primary_key=True)
    NAME = db.Column(db.String(150), nullable=False)
    LOCATION = db.Column(db.String(120), nullable=False)
    WEBSITE = db.Column(db.String(250), nullable=False)
    PHONE = db.Column(db.String(15), nullable=False, unique=True)
    FOR = db.Column(db.String(150), nullable=False)
    
    


class WillingCandisate(db.Model):
    __tablename__ = "WillingCandisate"
    ID = db.Column(db.Integer, primary_key=True)
    POST_ID = db.Column(db.Integer, nullable=False)
    CANDIDATE_USERID = db.Column(db.String(150), nullable=False)
    APPLIED_AT = db.Column(db.DateTime, nullable=False)
    CONNECT = db.Column(db.Boolean, nullable=False, default=False)



