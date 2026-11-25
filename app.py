import os, re, calendar
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

from models.expense_model import ExpenseAI

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=3000)
db = client[os.getenv("DB_NAME", "ai_expense_tracker")]
users, transactions, budgets = db.users, db.transactions, db.budgets
ai = ExpenseAI()
ai.train()

CATEGORIES = ["Food","Transport","Shopping","Entertainment","Bills","Education","Healthcare","Travel","Other"]
PAYMENTS = ["Cash","UPI","Card","Bank Transfer"]

def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "user_id" not in session: return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper

def uid(): return ObjectId(session["user_id"])

def month_bounds(year=None, month=None):
    now = datetime.now()
    year, month = year or now.year, month or now.month
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end

def parse_natural(text):
    amount = None
    m = re.search(r'(?:₹|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)', text.lower())
    if m:
        amount = float(m.group(1))
    lower = text.lower()
    d = datetime.now()
    if "yesterday" in lower: d -= timedelta(days=1)
    elif "day before yesterday" in lower: d -= timedelta(days=2)
    elif "tomorrow" in lower: d += timedelta(days=1)

    payment = "UPI" if any(x in lower for x in ["upi","gpay","google pay","phonepe","paytm"]) else \
              "Card" if any(x in lower for x in ["card","credit card","debit card"]) else \
              "Cash" if "cash" in lower else "Bank Transfer" if "bank transfer" in lower else None
    category = ai.predict(text)
    return {"amount": amount, "category": category, "payment_method": payment, "date": d.strftime("%Y-%m-%d")}

@app.route("/")
def index():
    return redirect(url_for("dashboard")) if "user_id" in session else render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name,email,password = request.form.get("name","").strip(),request.form.get("email","").strip().lower(),request.form.get("password","")
        if not name or not email or len(password)<6:
            flash("Enter a name, valid email and password of at least 6 characters.","danger")
            return render_template("register.html")
        if users.find_one({"email":email}):
            flash("Email is already registered.","warning"); return render_template("register.html")
        r=users.insert_one({"name":name,"email":email,"password":generate_password_hash(password),"created_at":datetime.utcnow()})
        session["user_id"]=str(r.inserted_id); session["user_name"]=name
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); password=request.form.get("password","")
        u=users.find_one({"email":email})
        if u and check_password_hash(u["password"],password):
            session["user_id"]=str(u["_id"]); session["user_name"]=u["name"]; return redirect(url_for("dashboard"))
        flash("Invalid email or password.","danger")
    return render_template("login.html")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    start,end=month_bounds()
    docs=list(transactions.find({"user_id":uid(),"date":{"$gte":start,"$lt":end}}).sort("date",-1))
    income=sum(float(x["amount"]) for x in docs if x["type"]=="income")
    expense=sum(float(x["amount"]) for x in docs if x["type"]=="expense")
    cats={}
    for x in docs:
        if x["type"]=="expense": cats[x["category"]]=cats.get(x["category"],0)+float(x["amount"])
    budget_doc=budgets.find_one({"user_id":uid(),"year":start.year,"month":start.month})
    budget=float(budget_doc["amount"]) if budget_doc else 0
    pct=min((expense/budget*100),100) if budget else 0
    top=max(cats,key=cats.get) if cats else None
    if not docs: insight="Add a few transactions and AI will start analyzing your spending."
    elif budget and expense>budget: insight=f"You have exceeded your budget by ₹{expense-budget:.0f}. Review your largest expense categories."
    elif budget and expense>=budget*.8: insight=f"You've used {expense/budget*100:.0f}% of your budget. Your biggest category is {top or '—'}."
    elif top: insight=f"{top} is your highest expense category this month at ₹{cats[top]:.0f}."
    else: insight="Your income and expense activity is recorded. Add more expenses for deeper analysis."
    return render_template("dashboard.html",user=users.find_one({"_id":uid()}),income=income,expense=expense,balance=income-expense,budget=budget,pct=pct,cats=cats,recent=docs[:8],insight=insight)

@app.route("/transactions", methods=["GET","POST"])
@login_required
def transaction_list():
    if request.method=="POST":
        description=request.form.get("description","").strip()
        try: amount=float(request.form.get("amount","0"))
        except: amount=0
        typ=request.form.get("type","expense")
        category=request.form.get("category") or ai.predict(description)
        payment=request.form.get("payment_method","Cash")
        date_raw=request.form.get("date")
        if not description or amount<=0:
            flash("Enter a valid description and amount.","danger"); return redirect(url_for("transaction_list"))
        try: dt=datetime.strptime(date_raw,"%Y-%m-%d") if date_raw else datetime.now()
        except: dt=datetime.now()
        transactions.insert_one({"user_id":uid(),"description":description,"amount":amount,"type":typ,"category":category if typ=="expense" else "Income","payment_method":payment,"date":dt,"created_at":datetime.utcnow()})
        flash(f"{typ.title()} added successfully.","success"); return redirect(url_for("transaction_list"))
    q={"user_id":uid()}
    typ=request.args.get("type","all"); cat=request.args.get("category","all")
    start_s=request.args.get("start",""); end_s=request.args.get("end","")
    if typ in ("income","expense"): q["type"]=typ
    if cat!="all": q["category"]=cat
    if start_s or end_s:
        q["date"]={}
        if start_s:
            try:q["date"]["$gte"]=datetime.strptime(start_s,"%Y-%m-%d")
            except:pass
        if end_s:
            try:q["date"]["$lt"]=datetime.strptime(end_s,"%Y-%m-%d")+timedelta(days=1)
            except:pass
    docs=list(transactions.find(q).sort("date",-1))
    return render_template("transactions.html",transactions=docs,categories=CATEGORIES,filters=request.args)

@app.route("/transaction/delete/<id>",methods=["POST"])
@login_required
def delete_transaction(id):
    try: transactions.delete_one({"_id":ObjectId(id),"user_id":uid()}); flash("Transaction deleted.","success")
    except: flash("Invalid transaction.","danger")
    return redirect(url_for("transaction_list"))

@app.route("/budget",methods=["GET","POST"])
@login_required
def budget():
    now=datetime.now()
    if request.method=="POST":
        try: amount=float(request.form.get("amount","0"))
        except: amount=0
        if amount<=0: flash("Enter a valid budget.","danger")
        else:
            budgets.update_one({"user_id":uid(),"year":now.year,"month":now.month},{"$set":{"amount":amount}},upsert=True)
            flash("Monthly budget saved.","success")
        return redirect(url_for("budget"))
    d=budgets.find_one({"user_id":uid(),"year":now.year,"month":now.month})
    return render_template("budget.html",amount=d["amount"] if d else 0)

@app.route("/ai-insights")
@login_required
def ai_insights():
    start,end=month_bounds()
    docs=list(transactions.find({"user_id":uid(),"type":"expense","date":{"$gte":start,"$lt":end}}))
    cats={}
    for x in docs: cats[x["category"]]=cats.get(x["category"],0)+float(x["amount"])
    total=sum(cats.values())
    top=max(cats,key=cats.get) if cats else "—"
    suggestions=[]
    if total: suggestions.append(f"Your highest expense category is {top}, totaling ₹{cats[top]:.0f}.")
    if total and cats.get("Food",0)>total*.3: suggestions.append("Food is above 30% of your current expenses. Review restaurant and delivery spending.")
    if total and cats.get("Entertainment",0)>total*.15: suggestions.append("Entertainment is a noticeable part of your spending this month.")
    if not suggestions: suggestions.append("Add more expenses to generate more meaningful AI insights.")
    return render_template("ai_insights.html",cats=cats,total=total,top=top,suggestions=suggestions)

@app.route("/api/natural",methods=["POST"])
@login_required
def natural():
    text=(request.get_json(silent=True) or {}).get("text","").strip()
    if not text:return jsonify({"error":"Enter an expense sentence"}),400
    return jsonify(parse_natural(text))

@app.route("/reports")
@login_required
def reports():
    docs=list(transactions.find({"user_id":uid()}).sort("date",1))
    cats={}; months={}
    for x in docs:
        if x["type"]!="expense": continue
        cats[x["category"]]=cats.get(x["category"],0)+float(x["amount"])
        k=x["date"].strftime("%b %Y"); months[k]=months.get(k,0)+float(x["amount"])
    return render_template("reports.html",cats=cats,months=months)

@app.route("/export/csv")
@login_required
def export_csv():
    import csv, io
    docs=list(transactions.find({"user_id":uid()}).sort("date",-1))
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(["Date","Type","Description","Category","Amount","Payment Method"])
    for x in docs:w.writerow([x["date"].strftime("%Y-%m-%d"),x["type"],x["description"],x["category"],x["amount"],x["payment_method"]])
    r=make_response(out.getvalue()); r.headers["Content-Disposition"]="attachment; filename=expense_report.csv"; r.headers["Content-Type"]="text/csv"
    return r

if __name__=="__main__": app.run(debug=True)
