from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, jsonify
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, IntegerField, SelectField, SelectFieldBase, RadioField, BooleanField, FieldList, TextField, SubmitField
from functools import wraps
import firebase_admin
from firebase_admin import db
import requests as rq
import json
import pyrebase
from credentials import fb_config
from credentials import cred
from datetime import datetime
from initTableTemplate import InitialTableTemplate


app = Flask(__name__)


firebase = pyrebase.initialize_app(fb_config)
auth = firebase.auth()
firebase_admin.initialize_app(cred, {
    'databaseURL': fb_config['databaseURL']
})
app.secret_key = fb_config['apiKey']


class HomeForm(Form):
    name = BooleanField("Name")
    adj = BooleanField("Adjektive")
    verb = BooleanField("Verb")
    adv = BooleanField("Adverb")
    setze = BooleanField("Sentence")
    note = BooleanField("Note")
    tabelle = BooleanField("Table")

class FilterForm(Form):
    one = BooleanField("1 Day ago")
    three = BooleanField("3 Days ago")
    six = BooleanField("6 Days ago")


class Dataform(Form):
    de = StringField("Deutsch")
    en = StringField("English")
    tr = StringField("Türkçe")
    zb = StringField("Example")
    komment = StringField("Comment:")
    

class TableAndNotesForm(Form):
    title = StringField("Title")
    context = TextAreaField("Context")


def login_required_uye(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in_member" in session:
            return f(*args, **kwargs)
        else:
            flash("You don't have a permission to see this page. Please log in.", "danger")
            return redirect(url_for("login"))
    return decorated_function




class RegisterForm(Form):
    email = StringField("E-mail: ", validators=[validators.Email(
        message="Please enter a valid email."), validators.DataRequired()])
    password = PasswordField("Password", validators=[
        validators.DataRequired(message="Please fill the password field."),
        validators.EqualTo(fieldname="password_again",
                           message="Your passwords don't match..."),
        validators.Length(min=6, message="Your password must be contains minimum 6 characters.")])
    password_again = PasswordField("Password again: ")

# kayıt
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        try:
           
            user = auth.create_user_with_email_and_password(
                form.email.data, form.password.data)

            session["id"] = (auth.get_account_info(
                user["idToken"])["users"])[0]["email"]
            session["id"] = (auth.get_account_info(
                user["idToken"])["users"])[0]["localId"]
            session["logged_in_member"] = True
           
            flash("Kaydınız gerçekleşti.", "success")
            return redirect(url_for("home"))
        except rq.exceptions.HTTPError as e:
            error_json = e.args[1]
            message = json.loads(error_json)['error']["message"]
            flash(message, "danger")
            return redirect(url_for("home"))
    else:
        return render_template("register.html", form=form)


class Loginform(Form):
    mail = StringField("Email: ")
    sifre = PasswordField("Password: ") 

# index login
@app.route("/",methods=["GET","POST"])
def login():
    form = Loginform(request.form)
    if request.method == "POST":
        try:
            user = auth.sign_in_with_email_and_password(form.mail.data,form.sifre.data)
            session["mail"] = (auth.get_account_info(user["idToken"])["users"])[0]["email"]
            session["uid"] = (auth.get_account_info(user["idToken"])["users"])[0]["localId"] 
            session["logged_in_member"] = True
            flash("Login successful","success")
            return redirect(url_for("home"))
            
        except rq.exceptions.HTTPError as e:
            error_json = e.args[1]
            message = json.loads(error_json)['error']["message"]
            flash("There is not any member with this email {}".format(message),"danger")
            return redirect(url_for("login")) 
    else:
        return render_template("login.html",form = form)


# logout
@app.route("/logout")
def logout():
    session.clear()
    session["logged_in_member"] = False
    return redirect(url_for("login"))


# home
@app.route("/home", methods=["GET", "POST"])
@login_required_uye
def home():
    form_idx = HomeForm(request.form)
    filterform = FilterForm(request.form)
    if request.method == "POST":
        text = request.form.get("text")
        if form_idx.tabelle.data is True:
            addData("Table",text)
            flash("Successfully added.", "success")
            return redirect(url_for("home"))
        elif form_idx.note.data is True:
            addData("Note",text)
            flash("Successfully added.", "success")
            return redirect(url_for("home"))
        elif filterform.one.data is True:
            data = retrieveOldEntries(1)
            flash("{} results - 1 day ago".format(len(data)), "success")
            return render_template("index.html", data=data, form_idx=form_idx, filterform=filterform )
        elif filterform.three.data is True:
            data = retrieveOldEntries(3)
            flash("{} results - 3 days ago".format(len(data)), "success")
            return render_template("index.html", data=data, form_idx=form_idx, filterform=filterform )
        elif filterform.six.data is True:
            data = retrieveOldEntries(6)
            flash("{} results - 6 days ago".format(len(data)), "success")
            return render_template("index.html", data=data, form_idx=form_idx, filterform=filterform )

        else:
            if form_idx.adj.data is True:
                addData("Adjektiv",text)
            elif form_idx.adv.data is True:
                addData("Adverb",text)
            elif form_idx.name.data is True:
                addData("Name",text)
            elif form_idx.setze.data is True:
                addData("Sentence",text)
            elif form_idx.verb.data is True:
                addData("Verb",text)
            else:
                flash("Please select any type.", "danger")
                return redirect(url_for("home"))

            flash("Successfully added.", "success")
            return redirect(url_for("home"))

    else:
        ref = db.reference('/{}/'.format(session["uid"]))
        data = ref.get()
        
        # noten = note.query.all()
        # tabelle = Tabelle.query.all()
        return render_template("index.html", data=data, form_idx=form_idx, filterform=filterform )


# edit
@app.route("/edit/<string:id>", methods=["GET", "POST"])
@login_required_uye
def edit(id):
    form = Dataform(request.form)
    ref = db.reference('/').child(session["uid"]).child(id)
    dat = ref.get()
    
    if request.method == "POST":
        
        now = datetime.now()
        datum = datetime.strftime(now,"%d-%m-%Y %X")

        ref.update({
            "DE":form.de.data,
            "EN":form.en.data,
            "TR":form.tr.data,
            "zb":form.zb.data,
            "komment":form.komment.data,
            "modified_datum": datum

        })
        flash("Successfully added.")
        return redirect(url_for("home"))
    else:
        if dat["typ"] == "Table" or dat["typ"] == "Note":
            return redirect(url_for("editTabNote",cat = dat["typ"], id=id))
        
        else:
            
            form.de.data = dat["DE"]
            form.en.data = dat["EN"]
            form.tr.data = dat["TR"]
            form.zb.data = dat["zb"]
            form.komment.data = dat['komment']
            return render_template("edit.html", form=form)

 # remove
@app.route("/remove/<string:id>")
@login_required_uye
def remove(id):
    ref = db.reference('/{}/'.format(session["uid"])).child(id)
    data = ref.get()
    newRef = db.reference('/').child("deleted").child(session["uid"])
    newRef.push(data)
    ref.delete()
    flash("The entry was moved to archive", "success")
    return redirect(request.referrer)


# showPage
@app.route("/show-<string:cat>", methods=["GET", "POST"])
@login_required_uye
def showCat(cat):
    ref = db.reference('/{}/'.format(session["uid"])).order_by_child("typ").equal_to(cat)
    data = ref.get()
    if cat == "Note" or cat == "Table":   
        return render_template("showTabsNotes.html", data=data,cat=cat)
    else:
        if request.method == "POST":
            text = request.form.get("text")
            addData(cat,text)
            flash("Successfully added.", "success")
            return redirect(request.referrer)
        else:
            return render_template("data.html", data=data,cat=cat)


# archive
@app.route("/archive")
@login_required_uye
def archive():
    ref = db.reference('/deleted/{}/'.format(session["uid"]))
    data = ref.get()
    return render_template("archive.html", data=data)

# delete
@app.route("/archive/delete/<string:id>")
@login_required_uye
def delete(id):
    ref = db.reference('/deleted/{}/'.format(session["uid"])).child(id)
    ref.delete()
    flash("The entry was deleted from archive", "success")
    return redirect(request.referrer)

# recover entry
@app.route("/archive/recover/<string:id>")
@login_required_uye
def recover(id):
    ref = db.reference('/deleted/{}/'.format(session["uid"])).child(id)
    data = ref.get()
    newRef = db.reference('/{}/'.format(session["uid"]))
    newRef.push(data)
    ref.delete()
    flash("The entry was recoved from archive", "success")
    return redirect(request.referrer)

# add empty TableorNote
@app.route("/add_<string:cat>")
@login_required_uye
def addTableorNote(cat):
    addData(cat,"New {}".format(cat))
    flash("Successfully added", "success")
    return redirect(request.referrer)

# showSingleTabNote
@app.route("/show_<string:cat>/<string:id>")
@login_required_uye
def showSingleTabNote(cat,id):
    ref = db.reference('/{}/'.format(session["uid"])).child(id)
    data = ref.get()
    return render_template("showSingleTabNote.html", data=data, id=id, cat=cat)

# editTabNote
@app.route("/edit_<string:cat>/<string:id>", methods=["GET", "POST"])
@login_required_uye
def editTabNote(cat,id):
    form = TableAndNotesForm(request.form)
    ref = db.reference('/{}/'.format(session["uid"])).child(id)
    data = ref.get()
    if request.method == "POST":
        now = datetime.now()
        datum = datetime.strftime(now,"%d-%m-%Y %X")
        ref.update({
            "title": form.title.data,
            "context": form.context.data,
            "modified_datum":datum,
            "DE": "{}: {}".format(cat,form.title.data)
        })
        flash("Successfully saved.", "success")
        return redirect(url_for("showCat",cat=cat))
    else:
        form.title.data = data['title']
        form.context.data = data['context']
        return render_template("editTabNote.html", form=form, data=data)


#addData
def addData(typ,text):
    now = datetime.now()
    datum = datetime.strftime(now,"%d-%m-%Y %X")
    ref = db.reference('/{}'.format(session["uid"]))
    if typ== "Table":
        template = InitialTableTemplate
        ref.push({
            "title":"Table: {}".format(text),
            "context": template,
            "typ": "Table",
            "datum": datum,
            "DE": "Table: New_Table"
        })  

    elif typ == "Note":
        ref.push({
        "title":"Note: {}".format(text),
        "context": " ",
        "typ": "Note",
        "datum": datum,
        "DE": "Note: New_Note"
    })
    else:
        ref.push({
            "DE":text,
            "EN": "", 
            "TR":"",
            "zb":"", 
            "komment": "",
            "typ":typ,
            "datum":datum,
            })
       



def retrieveOldEntries(day):
    # now = datetime.now()
    # datum = datetime.strftime(now,"%d-%m-%Y %X")
    dayToday = datetime.now().day
    monthToday = datetime.now().month
    yearToday = datetime.now().year
    dayAgo = dayToday-day

    ref = db.reference('/{}'.format(session["uid"]))
    alldata = ref.get()
    filteredData = dict()
    for i in alldata:
        # print(alldata[i]["datum"]) 
        datum = alldata[i]["datum"]
        if datum.startswith("{}-{}-{}".format(dayAgo,monthToday,yearToday)):
            filteredData[i] =alldata[i]
            
    return filteredData
    # print(datum)
    # print(day)
    # print(month)
    # print(year)
    # print(alldata)
    # print(len(filteredData))





if __name__ == "__main__":
    app.run(debug=False)
