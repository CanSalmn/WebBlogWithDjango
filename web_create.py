from os import name
import re
from MySQLdb.cursors import Cursor
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask.typing import AppOrBlueprintKey
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.handlers.sha2_crypt import sha256_crypt
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Before you must log in","warning")
            return redirect(url_for("login"))
    return decorated_function


class Registerform(Form):
    name=StringField("Name:",validators=[validators.DataRequired(message="This Field is Required.")])
    username=StringField("User Name: ",validators=[validators.length(min=3,max=20),validators.DataRequired(message="This Field is Required.")])
    password=PasswordField("Password:",validators=[
        validators.length(min=6,max=20),validators.DataRequired(message="This Field is Required."),
        validators.EqualTo("confirm",message="Passwords doesn't match")])
    confirm=PasswordField("Password verify:",validators=[validators.EqualTo("password",message="Passwords doesn't match"),validators.DataRequired(message="This Field is Required.")])
    email=StringField("Email:",validators=[validators.Email(message="Your Email is wrong"),validators.DataRequired(message="This Field is Required.")])
    
class Loginform(Form):
    username=StringField("User Name:")
    password=PasswordField("Password:")

class Articleform(Form):
    title=StringField("Title:",validators=[validators.length(min=2,max=100,message="Article Title must be between 2 and 100 characters")])
    content=TextAreaField("Article Content:",validators=[validators.length(min=10,message="Article length must be over 10 character")])



app=Flask(__name__)
app.secret_key="myblog"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"]= "root"
app.config["MYSQL_PASSWORD"]= ""
app.config["MYSQL_DB"]= "myblog"
app.config["MYSQL_CURSORCLASS"]= "DictCursor"

myquery= MySQL(app)


@app.route("/")
def mainpage():
    return render_template("mainpage.html")


@app.route("/dashboard")
@login_required
def dashboard():
    cursor=myquery.connection.cursor()
    query="Select * From articles Where author= %s"
    result=cursor.execute(query,(session["username"],))
    data = cursor.fetchall()
    cursor.close
    if result >0:
        return render_template("dashboard.html",data=data)
    else:
        flash("You Add Article first.","warning")
        return redirect(url_for("addarticle"))
    
@app.route("/login",methods=['GET','POST'])
def login():
    form2 = Loginform(request.form)
    if request.method == "POST":
        username=form2.username.data
        enpassword = form2.password.data
        cursor=myquery.connection.cursor()
        query="Select * From users where username= %s"
        result=cursor.execute(query,(username,))
        if result >0:
            data=cursor.fetchone()
            password=data["password"]
            if sha256_crypt.verify(enpassword,password):
                flash("Log in Succesful","success")
                session["logged_in"]= True
                session["username"]=username    
                return redirect(url_for("mainpage"))  
            else:
                flash("Your password is wrong.","danger")
                return redirect(url_for("login"))   
        else:
            flash("Your info is wrong.","danger")
            return redirect(url_for("login"))    
        
    else:
        return render_template("login.html",form2=form2)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/signup",methods=['GET','POST'])
def signup():
    form1 = Registerform(request.form)

    if request.method== "POST" and form1.validate() :
        cursor=myquery.connection.cursor()
        name=form1.name.data
        username=form1.username.data
        query="Select * From users where username= %s"
        result=cursor.execute(query,(username,))
        password= sha256_crypt.encrypt(form1.password.data)
        email= form1.email.data
        if result==0:
            query="Insert into users(name,email,username,password) Values(%s,%s,%s,%s)"
            cursor.execute(query,(name,email,username,password))
            myquery.connection.commit()
            cursor.close
            flash("Thank you for registering.","success")
            return redirect(url_for("login"))
        else:
            flash("The User Name is being used .Change it ","info")
            return redirect(url_for("signup"))
    else:
        return render_template("singup.html",form1=form1)




@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/addarticles",methods= ["GET","POST"])
@login_required
def addarticle():
    article=Articleform(request.form)
    if request.method=="POST" and article.validate :
        title=article.title.data
        content=article.content.data
        cursor=myquery.connection.cursor()
        query="Insert into articles(title,author,content) Values(%s,%s,%s)"
        cursor.execute(query,(title,session["username"],content))
        myquery.connection.commit()
        cursor.close()
        flash("Article have been Creating succesfully.","success")
        return redirect(url_for("dashboard"))
    return render_template("addarticles.html",article=article)

@app.route("/articles")
def articles():
    cursor=myquery.connection.cursor()
    query= "Select * From articles "
    result=cursor.execute(query)
    data=cursor.fetchall()
    if result>0:
        return render_template("articles.html",data=data,result=result)
      
    else:
        return redirect(url_for("dashboard"))


@app.route("/article/<string:id>")
def article(id):
    cursor= myquery.connection.cursor()
    query="Select * From articles where id = %s "
    result=cursor.execute(query,(id,))
    data=cursor.fetchone()
    if result >0 :
        id=int(id)
        if id <=data["id"]:
            return render_template("/article.html",data=data,id=id)
        else:
            flash("Doesn't Have This Article","warning")
            return redirect(url_for("article"))

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor= myquery.connection.cursor()
    query= "Select * From articles where author =%s and id = %s"
    result=cursor.execute(query,(session["username"],id))

    if result>0:
        query1="Delete From articles where id = %s "
        cursor.execute(query1,(id,))
        myquery.connection.commit()
        flash("The Article Have Removed Succesfully.","info")
        return redirect(url_for("dashboard"))
    else:
        flash("You don't Delete This Article.","warning")
        return redirect(url_for("dashboard"))


@app.route("/update/<string:id>",methods=["GET","POST"])
@login_required
def update(id):
    if request.method== "GET":
        cursor= myquery.connection.cursor()
        query= "Select * From articles where author =%s and id = %s "
        result = cursor.execute(query,(session["username"],id))

        if result==0 :
            flash("You doesn't Change this Article","danger")
            return  redirect(url_for("mainpage"))

        else:
            uform=Articleform()
            data= cursor.fetchone()
            uform.title.data=data["title"]
            uform.content.data= data["content"]
            return render_template("update.html",uform=uform)
    else: 
        
        uform=Articleform(request.form)
        newtitle= uform.title.data
        newcontent= uform.content.data
        cursor= myquery.connection.cursor()
        query="Update articles SET title=%s, content= %s where id=%s"
        cursor.execute(query,(newtitle,newcontent,id))
        myquery.connection.commit()
        flash("Article have Updated Succesfully.")
        return redirect(url_for("dashboard"))








@app.route("/search",methods= ["GET","POST"])


def search():
    if request.method== "GET":
        return redirect(url_for("mainpage"))

    else:
        keyword= request.form.get("keyargv")

        cursor= myquery.connection.cursor()
        query="Select * from articles where title like '%"+ keyword +"%'"

        result=cursor.execute(query)
        
        if result==0:
            flash("Searched word not found","warning")
            return redirect(url_for("articles"))
        else:
            data= cursor.fetchall()

            return render_template("articles.html",data=data)
            



if __name__=="__main__":
    app.run(debug=True)
    

