MAX_STORAGE_MB = 25600  # 25GB in MB

import werkzeug.utils
from cryptography.fernet import InvalidToken
from cryptography.fernet import Fernet
import os
import time 
from flask import Flask, render_template, request, redirect, url_for
from flask import send_file
import io
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


SECRET_KEY = os.environ.get("FERNET_KEY")
if not SECRET_KEY:
    raise ValueError("FERNET_KEY not found in environment variables")

cipher = Fernet(SECRET_KEY.encode())



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


def add_log(user_id, action, file_name):
    try:
        supabase.table("logs").insert({
            "user_id": user_id,
            "action": action,
            "file_name": file_name
        }).execute()
    except Exception as e:
        print("LOG ERROR:", e)
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
        user_data = supabase.table("users").select("name").eq("id", user_id).limit(1).execute()

        if not user_data.data:
            return render_template("signin.html", message="User not found")

        name = user_data.data[0]['name']
        
        # Get File List
        files, space = get_user_files(user_id)
        
        return render_template("dashboard.html", 
                                name=name,
                                files=files, 
                                username=email, 
                                space=space, 
                                nf=len(files))
    except Exception:
        return render_template("signin.html", message="Invalid login credentials")
    
    
@app.route("/upload/<username>", methods=["POST"])
def main4(username):
    try:
        user_res = supabase.table("users").select("id, name").eq("email", username).limit(1).execute()

        if not user_res.data:
            return "User not found"
        user_id = user_res.data[0]['id']
        
        # Capture the files using the correct HTML name attribute
        uploaded_files = request.files.getlist("files[]")
        
        if not uploaded_files:
            print("Debug: No files found in request.files")
            return redirect(url_for('main3'))
        
        # Get current storage usage
        files, current_space = get_user_files(user_id)

        # Convert MB to bytes
        current_bytes = current_space * 1024 * 1024

        # Calculate incoming files size
        incoming_size = 0
        for f in uploaded_files:
            if f.filename != '':
                file_data = f.read()
                incoming_size += len(file_data)
                f.seek(0)  # VERY IMPORTANT (reset pointer)

# Check limit (25GB)
        if current_bytes + incoming_size > MAX_STORAGE_MB * 1024 * 1024:
            return render_template(
                "dashboard.html",
                name=user_res.data[0]['name'],
                files=files,
                username=username,
                space=current_space,
                nf=len(files),
                error="Storage limit exceeded (Max: 25GB)"
            )
    
        for f in uploaded_files:
            if f.filename == '': continue
            
            # Important: Read content and reset pointer
            file_content = f.read()
            encrypted_content = cipher.encrypt(file_content)
            safe_filename = werkzeug.utils.secure_filename(f.filename)
            file_path = f"{user_id}/{int(time.time())}_{safe_filename}"            
            
            # Check duplicate
            existing = supabase.table("files")\
                .select("id")\
                .eq("owner_id", user_id)\
                .eq("name", f.filename).eq("storage_path", file_path)\
                .eq("is_deleted", False)\
                .execute()

            if existing.data:
                return render_template(
                    "dashboard.html",
                    name=user_res.data[0]['name'],
                    files=files,
                    username=username,
                    space=current_space,
                    nf=len(files),
                    error=f"{f.filename} already exists"
                )

            # 1. Upload to Supabase
            # Add 'upsert=True' to overwrite if testing with the same file
            storage_res = supabase.storage.from_("my-drive").upload(
                path=file_path, 
                file= encrypted_content, 
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
            add_log(user_id, "UPLOAD", f.filename)

        # Refresh Dashboard data
        files, space = get_user_files(user_id)
        return render_template("dashboard.html", name=user_res.data[0]['name'], files=files, username=username, space=space, nf=len(files))

    except Exception as e:
        print(f"CRITICAL UPLOAD ERROR: {e}")
        return redirect(url_for('main3'))
    
    
@app.route("/delete/<username>/name/<name>", methods=["GET"])
def main5(username, name):
    """Soft delete logic"""
    user_res = supabase.table("users").select("id, name").eq("email", username).limit(1).execute()

    if not user_res.data:
        return "User not found"
    user_id = user_res.data[0]['id']
    
    # Mark file as deleted in DB (Trash functionality)
    supabase.table("files").update({"is_deleted": True}).eq("owner_id", user_id).eq("name", name).execute()
    add_log(user_id, "DELETE", name)
    files, space = get_user_files(user_id)
    return render_template("dashboard.html", name=user_res.data[0]['name'], files=files, username=username, space=space, nf=len(files))

@app.route("/download/<username>/name/<name>", methods=["GET"])
def main15(username, name):
    user_res = supabase.table("users").select("id").eq("email", username).limit(1).execute()

    if not user_res.data:
        return "User not found"
        
    user_id = user_res.data[0]['id']

    file_data = supabase.table("files").select("storage_path").eq("owner_id", user_id).eq("name", name).order("id", desc=True).limit(1).execute()
    if not file_data.data:
        return "File not found"
    file_path = file_data.data[0]['storage_path']

    try:
        # Download encrypted file
        res = supabase.storage.from_("my-drive").download(file_path)
        
        encrypted_data = res if isinstance(res, bytes) else res.read()

        # Decrypt
        try:
            decrypted_data = cipher.decrypt(encrypted_data)
        except InvalidToken:
            print("WARNING: File not encrypted or wrong key")
            decrypted_data = encrypted_data  # fallback
        
        add_log(user_id, "DOWNLOAD", name)

        return send_file(
            io.BytesIO(decrypted_data),
            as_attachment=True,
            download_name=name
        )

    except Exception as e:
        print(e)
        return redirect(url_for('main3'))
    

@app.route("/share/<username>/name/<name>")
def share_file(username, name):
    user_res = supabase.table("users").select("id").eq("email", username).limit(1).execute()

    if not user_res.data:
        return "User not found"
    user_id = user_res.data[0]['id']

    file_data = supabase.table("files").select("storage_path").eq("owner_id", user_id).eq("name", name).limit(1).execute()

    if not file_data.data:
        return "File not found"

    file_path = file_data.data[0]['storage_path']

    # Generate signed URL for sharing (5 min)
    res = supabase.storage.from_("my-drive").create_signed_url(file_path, 300)

    if res.get('signedURL'):
        add_log(user_id, "SHARE", name)
        return render_template("share.html", link=res['signedURL'])

    return "Error generating link"


@app.route("/logs/<username>")
def view_logs(username):
    user_res = supabase.table("users").select("id, name").eq("email", username).limit(1).execute()

    if not user_res.data:
        return "User not found"
    user_id = user_res.data[0]['id']

    logs = supabase.table("logs") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("timestamp", desc=True) \
        .execute()

    return render_template(
        "logs.html",
        logs=logs.data,
        name=user_res.data[0]['name'],
        username=username
    )

@app.route("/trash/<username>")
def view_trash(username):
    user_res = supabase.table("users").select("id, name").eq("email", username).limit(1).execute()

    if not user_res.data:
        return "User not found"
    user_id = user_res.data[0]['id']

    # Fetch deleted files
    response = supabase.table("files").select("*").eq("owner_id", user_id).eq("is_deleted", True).execute()

    files = []
    for f in response.data:
        size_mb = f['size'] / (1024 * 1024)
        files.append({
            "name": f['name'],
            "size": f"{round(size_mb, 2)} MB"
        })

    return render_template("trash.html", files=files, username=username, name=user_res.data[0]['name'])


@app.route("/restore/<username>/name/<name>")
def restore_file(username, name):
    user_res = supabase.table("users").select("id").eq("email", username).limit(1).execute()

    if not user_res.data:
        return "User not found"
    user_id = user_res.data[0]['id']

    supabase.table("files").update({"is_deleted": False})\
        .eq("owner_id", user_id)\
        .eq("name", name).execute()

    return redirect(url_for('view_trash', username=username))

@app.route("/delete_permanent/<username>/name/<name>")
def delete_permanent(username, name):
    user_res = supabase.table("users").select("id").eq("email", username).limit(1).execute()

    if not user_res.data:
        return "User not found"
    user_id = user_res.data[0]['id']

    # Get file path first
    file = supabase.table("files").select("storage_path")\
        .eq("owner_id", user_id)\
        .eq("name", name).limit(1).execute()

    if not file.data:
        return "File not found"

    file_path = file.data[0]['storage_path']

    # Delete from storage
    supabase.storage.from_("my-drive").remove([file_path])

    # Delete from DB
    supabase.table("files").delete()\
        .eq("owner_id", user_id)\
        .eq("name", name).execute()

    return redirect(url_for('view_trash', username=username))
@app.errorhandler(404)
def main10(e):
    return render_template("404.html")

if __name__ == '__main__':
    app.run(debug=True)