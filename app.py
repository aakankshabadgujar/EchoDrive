import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="template")

# 1. Connect to Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- HELPER FUNCTIONS ---

def get_user_files(user_id):
    """Fetch file metadata from PostgreSQL"""
    # Only fetch files that are NOT marked as deleted
    response = supabase.table("files").select("*").eq("owner_id", user_id).eq("is_deleted", False).execute()
    files = []
    total_space = 0
    for f in response.data:
        size_mb = f['size'] / (1024 * 1024)
        files.append({
            "name": f['name'], 
            "size": f"{round(size_mb, 2)} MB", 
            "id": f['id']
        })
        total_space += size_mb
    return files, round(total_space, 2)

# --- ROUTES ---

@app.route("/", methods=["GET"])
def main():
    return render_template("index.html")

@app.route("/sign_up", methods=["GET", "POST"])
def main2():
    if request.method == "GET":
        return render_template("signup.html", message="")
    
    email = request.form["email"]
    password = request.form["password"]
    name = request.form["name"]
    
    try:
        # Create User in Supabase Auth
        auth_response = supabase.auth.sign_up({"email": email, "password": password})
        user_id = auth_response.user.id
        
        # Save profile data to PostgreSQL table
        supabase.table("users").insert({"id": user_id, "email": email, "name": name}).execute()
        
        # Redirect to sign in to ensure the session is activated correctly
        return render_template("signin.html", message="Account created! Please sign in.")
    except Exception as e:
        return render_template("signup.html", message=str(e))

@app.route("/sign_in", methods=["GET", "POST"])
def main3():
    if request.method == "GET":
        return render_template("signin.html", message="")
    
    email = request.form["username"] # HTML input name is "username"
    password = request.form["password"]
    
    try:
        # Auth with Supabase
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user_id = auth_response.user.id
        
        # Get User Profile Name
        user_data = supabase.table("users").select("name").eq("id", user_id).single().execute()
        
        # Get File List
        files, space = get_user_files(user_id)
        
        return render_template("dashboard.html", 
                               name=user_data.data['name'], 
                               files=files, 
                               username=email, 
                               space=space, 
                               nf=len(files))
    except Exception:
        return render_template("signin.html", message="Invalid login credentials")
    
    
@app.route("/upload/<username>", methods=["POST"])
def main4(username):
    try:
        user_res = supabase.table("users").select("id, name").eq("email", username).single().execute()
        user_id = user_res.data['id']
        
        # Capture the files using the correct HTML name attribute
        uploaded_files = request.files.getlist("files[]")
        
        if not uploaded_files:
            print("Debug: No files found in request.files")
            
        for f in uploaded_files:
            if f.filename == '': continue
            
            # Important: Read content and reset pointer
            file_content = f.read()
            file_path = f"{user_id}/{f.filename}"
            
            # 1. Upload to Supabase
            # Add 'upsert=True' to overwrite if testing with the same file
            storage_res = supabase.storage.from_("my-drive").upload(
                path=file_path, 
                file=file_content,
                file_options={"upsert": "true"} 
            )
            
            # 2. Insert Metadata (Ensure 'size' column exists!)
            supabase.table("files").insert({
                "name": f.filename,
                "size": len(file_content),
                "storage_path": file_path,
                "owner_id": user_id,
                "is_deleted": False
            }).execute()
            
            print(f"DEBUG: Successfully uploaded {f.filename}")

        # Refresh Dashboard data
        files, space = get_user_files(user_id)
        return render_template("dashboard.html", name=user_res.data['name'], files=files, username=username, space=space, nf=len(files))

    except Exception as e:
        print(f"CRITICAL UPLOAD ERROR: {e}")
        return redirect(url_for('main3', message="Upload failed. Check terminal for error."))
    
    
@app.route("/delete/<username>/name/<name>", methods=["GET"])
def main5(username, name):
    """Soft delete logic"""
    user_res = supabase.table("users").select("id, name").eq("email", username).single().execute()
    user_id = user_res.data['id']
    
    # Mark file as deleted in DB (Trash functionality)
    supabase.table("files").update({"is_deleted": True}).eq("owner_id", user_id).eq("name", name).execute()
    
    files, space = get_user_files(user_id)
    return render_template("dashboard.html", name=user_res.data['name'], files=files, username=username, space=space, nf=len(files))

@app.route("/download/<username>/name/<name>", methods=["GET"])
def main15(username, name):
    """Generates a secure signed URL for download"""
    user_res = supabase.table("users").select("id").eq("email", username).single().execute()
    file_path = f"{user_res.data['id']}/{name}"
    
    # Create signed URL valid for 1 minute
    res = supabase.storage.from_("my-drive").create_signed_url(file_path, 60)
    
    # Check if signedURL exists in response
    if 'signedURL' in res:
        return redirect(res['signedURL'])
    return redirect(url_for('main10'))

@app.errorhandler(404)
def main10(e):
    return render_template("404.html")

if __name__ == '__main__':
    app.run(debug=True)