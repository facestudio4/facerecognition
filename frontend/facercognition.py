"""
Face Studio — Recognition & Generation
=======================================
Home page GUI with two modes:

  1. Face Recognition — Identify people in real-time via webcam
     • Reads ALL person folders + entire archive dataset (incl. n###### IDs)
     • Caches trained model to disk for fast subsequent starts
     • Register unknown faces — updates existing person if name already exists

  2. Face Generation  — Search by name, choose artistic style, generate image
     • Styles: Sketch, Cartoon, Oil Painting, HDR, Ghibli Art, Anime, Ghost, Emboss
     • If name not found, captures photo from webcam

Requirements:
  pip install opencv-python opencv-contrib-python numpy

Usage:
  python facercognition.py                        # launches home page GUI
  python facercognition.py recognize              # direct webcam recognition
  python facercognition.py generate               # direct face generation
  python facercognition.py identify --image pic.jpg
  python facercognition.py retrain                # force model retrain
"""

import argparse 
import csv 
import hashlib 
import json 
import math 
import os 
import pickle 
import queue 
import random 
import shutil 
import smtplib 
import sqlite3 
import string 
import sys 
import time 
import threading 
import tkinter as tk 
from email .mime .text import MIMEText 
from email .mime .multipart import MIMEMultipart 
from tkinter import ttk ,filedialog ,messagebox ,simpledialog 
from collections import deque ,Counter 
from datetime import datetime ,timedelta 


def _prefer_standard_python ():
    """Relaunch with python.exe when running under free-threaded pythonX.Yt.exe."""
    exe_name =os .path .basename (sys .executable ).lower ()
    if not exe_name .endswith ("t.exe"):
        return 

    standard_python =os .path .join (os .path .dirname (sys .executable ),"python.exe")
    if os .path .exists (standard_python ):
        os .execv (standard_python ,[standard_python ,*sys .argv ])


_prefer_standard_python ()

import cv2 
import numpy as np 

PROJECT_ROOT =os .path .dirname (os .path .dirname (os .path .abspath (__file__ )))
if PROJECT_ROOT not in sys .path :
    sys .path .insert (0 ,PROJECT_ROOT )

from backend .advanced_project_pack import launch_advanced_lab ,run_advanced_cli 
from backend .phase2_enterprise_pack import launch_enterprise_control_center ,run_enterprise_cli 
from backend .phase3_services_pack import launch_phase3_services_gui ,run_phase3_cli 
from backend .phase4_showcase_pack import launch_phase41_showcase_gui ,run_phase41_cli 
from backend .phase5_evaluator_pack import launch_evaluator_bundle_gui ,run_phase5_cli 
from backend .phase6_judge_mode_pack import launch_judge_mode_gui ,run_phase6_cli 
from backend .phase7_demo_launcher_pack import launch_phase7_demo_launcher_gui ,run_phase7_cli 
from backend .phase8_presentation_pack import launch_phase8_presentation_gui ,run_phase8_cli 


_SCROLLABLE_PARENTS :dict ={}
_TK_ORIGINALS :dict ={}


def _patch_scroll_parent_redirection ():
    """Redirect widgets created with a mapped toplevel parent into its scrollable frame."""
    if _TK_ORIGINALS :
        return 

    def _patch_one (module ,name :str ):
        original =getattr (module ,name )
        _TK_ORIGINALS [f"{module .__name__}.{name}"]=original 

        if isinstance (original ,type ):
            def __init__ (self ,master =None ,*args ,**kwargs ):
                mapped_master =_SCROLLABLE_PARENTS .get (master ,master )
                original .__init__ (self ,mapped_master ,*args ,**kwargs )

            redirected =type (f"Redirected{name }",(original ,),{"__init__":__init__})
            setattr (module ,name ,redirected )
        else :
            def _wrapped (master =None ,*args ,**kwargs ):
                mapped_master =_SCROLLABLE_PARENTS .get (master ,master )
                return original (mapped_master ,*args ,**kwargs )

            setattr (module ,name ,_wrapped )

    for n in ["Frame","Label","Button","Entry","Canvas","Text",
    "Scale","Listbox","Checkbutton","Radiobutton","Spinbox"]:
        if hasattr (tk ,n ):
            _patch_one (tk ,n )

    for n in ["Frame","Label","Button","Entry","Combobox",
    "Treeview","Scrollbar","Progressbar","Notebook"]:
        if hasattr (ttk ,n ):
            _patch_one (ttk ,n )


def _tk_original (module_name :str ,cls_name :str ):
    return _TK_ORIGINALS .get (f"{module_name}.{cls_name}")


def _activate_page_scroll (win ,bg :str ="#1a1a2e"):
    """Attach one vertical scrollbar to the page and map future children into scroll body."""
    if win in _SCROLLABLE_PARENTS :
        return _SCROLLABLE_PARENTS [win ]

    tk_frame =_tk_original ("tkinter","Frame")
    tk_canvas =_tk_original ("tkinter","Canvas")
    ttk_scrollbar =_tk_original ("tkinter.ttk","Scrollbar")

    host =tk_frame (win ,bg =bg )
    host .pack (fill ="both",expand =True )

    canvas =tk_canvas (host ,bg =bg ,highlightthickness =0 ,bd =0 )
    vbar =ttk_scrollbar (host ,orient ="vertical",command =canvas .yview )
    body =tk_frame (canvas ,bg =bg )

    body_window =canvas .create_window ((0 ,0 ),window =body ,anchor ="nw")
    canvas .configure (yscrollcommand =vbar .set )

    canvas .pack (side ="left",fill ="both",expand =True )
    vbar .pack (side ="right",fill ="y")

    def _sync_scroll (_evt =None ):
        canvas .configure (scrollregion =canvas .bbox ("all"))

    def _sync_width (evt ):
        canvas .itemconfigure (body_window ,width =evt .width )

    def _wheel (evt ):
        if evt .delta :
            delta =-int (evt .delta /120 )
        elif getattr (evt ,"num",None )==5 :
            delta =1 
        else :
            delta =-1 
        canvas .yview_scroll (delta ,"units")

    body .bind ("<Configure>",_sync_scroll )
    canvas .bind ("<Configure>",_sync_width )
    canvas .bind ("<MouseWheel>",_wheel )
    canvas .bind ("<Button-4>",_wheel )
    canvas .bind ("<Button-5>",_wheel )
    body .bind ("<MouseWheel>",_wheel )
    body .bind ("<Button-4>",_wheel )
    body .bind ("<Button-5>",_wheel )

    _SCROLLABLE_PARENTS [win ]=body 
    return body 


_patch_scroll_parent_redirection ()




BASE_DIR =PROJECT_ROOT 
DATA_DIR =os .path .join (BASE_DIR ,"database")
FACES_ROOT =os .path .join (DATA_DIR ,"faces")
KNOWN_FACES_DIR =os .path .join (FACES_ROOT ,"known_faces")
ARCHIVE_DIR =os .path .join (FACES_ROOT ,"archive")
ENCODINGS_PATH =os .path .join (DATA_DIR ,"face_encodings.pkl")

RECOGNITION_THRESHOLD =0.363 
FRAME_SCALE =0.5 
IMAGE_EXTENSIONS ={".jpg",".jpeg",".png",".bmp",".webp"}
STABILITY_WINDOW =5 
IOU_THRESHOLD =0.15 
MAX_GONE_FRAMES =8 
GENERATED_IMAGE_SIZE =(512 ,512 )
MAX_ARCHIVE_SAMPLES =3 
LOAD_ARCHIVE =False 



SKIP_DIRS ={"known_faces","known_face","__pycache__",".git",".vscode",
"archive","models","output","generated","screenshots",
".idea","node_modules","env","venv"}

FACE_LOG_PATH =os .path .join (DATA_DIR ,"face_log.json")
SCREENSHOT_DIR =os .path .join (BASE_DIR ,"docs","screenshots")
ATTENDANCE_DIR =os .path .join (DATA_DIR ,"attendance")
ACTIVITY_LOG_PATH =os .path .join (DATA_DIR ,"activity_log.json")
SETTINGS_PATH =os .path .join (BASE_DIR ,"config","settings.json")


ADMIN_USERNAME ="shishir"
ADMIN_PASSWORD ="shishir@2009"

DEFAULT_USER_USERNAME ="user"
DEFAULT_USER_PASSWORD ="user@123"






SMTP_EMAIL ="shishirbhavsar4@gmail.com"
SMTP_APP_PASSWORD ="mlyu ajgr zorl foog"
SMTP_SERVER ="smtp.gmail.com"
SMTP_PORT =587 





TWILIO_SID ="AC8063a3d5412d73f2f09803bf7d9cd1ff"
TWILIO_AUTH_TOKEN ="245e8292a822132bfb450c311cf8f3fb"
TWILIO_PHONE_NUMBER ="+917400301950"


_current_role ="user"
_current_username =""


SQL_DB_PATH =os .path .join (DATA_DIR ,"facestudio.db")
USERS_DB_PATH =os .path .join (DATA_DIR ,"users.json")
FACE_LOG_JSON_PATH =FACE_LOG_PATH
ACTIVITY_LOG_JSON_PATH =ACTIVITY_LOG_PATH
SETTINGS_JSON_PATH =SETTINGS_PATH
ATTENDANCE_LOG_PATH =os .path .join (ATTENDANCE_DIR ,"attendance.json")


_pending_codes :dict ={}


class DiskBackedRetryQueue :
    """Small JSONL queue that survives app restarts and retries failed jobs."""

    def __init__ (self ,path :str ,max_attempts :int =5 ,retry_delay_seconds :int =30 ):
        self .path =path
        self .max_attempts =max_attempts
        self .retry_delay_seconds =retry_delay_seconds
        self ._lock =threading .Lock ()
        self ._worker_started =False
        self ._stop_event =threading .Event ()
        os .makedirs (os .path .dirname (path ),exist_ok =True )

    def enqueue (self ,kind :str ,payload :dict ,reason :str =""):
        job ={
        "id":f"{int (time .time ()*1000 )}_{random .randint (1000 ,9999 )}",
        "kind":kind ,
        "payload":payload ,
        "attempts":0 ,
        "next_retry_at":time .time (),
        "reason":str (reason or ""),
        "created_at":datetime .now ().isoformat (timespec ="seconds"),
        }
        with self ._lock :
            with open (self .path ,"a",encoding ="utf-8")as f :
                f .write (json .dumps (job ,ensure_ascii =False )+"\n")
        self .start_worker ()
        print (f"[RETRY QUEUE] Queued {kind } job {job ['id']} after failure: {reason }")
        return job ["id"]

    def _load_jobs (self )->list :
        if not os .path .exists (self .path ):
            return []
        jobs =[]
        with self ._lock :
            with open (self .path ,"r",encoding ="utf-8")as f :
                for line in f :
                    line =line .strip ()
                    if not line :
                        continue
                    try :
                        job =json .loads (line )
                        if isinstance (job ,dict ):
                            jobs .append (job )
                    except json .JSONDecodeError :
                        pass
        return jobs

    def _save_jobs (self ,jobs :list ):
        tmp =self .path +".tmp"
        with self ._lock :
            with open (tmp ,"w",encoding ="utf-8")as f :
                for job in jobs :
                    f .write (json .dumps (job ,ensure_ascii =False )+"\n")
            os .replace (tmp ,self .path )

    def process_once (self ,handler )->int :
        jobs =self ._load_jobs ()
        if not jobs :
            return 0
        now =time .time ()
        remaining =[]
        processed =0
        for job in jobs :
            if float (job .get ("next_retry_at",0 )or 0 )>now :
                remaining .append (job )
                continue
            attempts =int (job .get ("attempts",0 )or 0 )
            if attempts >=self .max_attempts :
                print (f"[RETRY QUEUE] Dropping {job .get ('kind')} job {job .get ('id')} after {attempts } attempts")
                processed +=1
                continue
            try :
                ok =bool (handler (job ))
            except Exception as e :
                ok =False
                job ["reason"]=str (e )
            if ok :
                print (f"[RETRY QUEUE] Completed {job .get ('kind')} job {job .get ('id')}")
                processed +=1
            else :
                job ["attempts"]=attempts +1
                job ["next_retry_at"]=now +self .retry_delay_seconds *(2 **attempts )
                remaining .append (job )
        self ._save_jobs (remaining )
        return processed

    def start_worker (self ):
        if self ._worker_started :
            return
        self ._worker_started =True
        def _loop ():
            while not self ._stop_event .wait (self .retry_delay_seconds ):
                self .process_once (_process_retry_job )
        threading .Thread (target =_loop ,daemon =True ,name ="FaceStudioRetryQueue").start ()


RETRY_QUEUE_PATH =os .path .join (DATA_DIR ,"retry_queue.jsonl")
_retry_queue =DiskBackedRetryQueue (RETRY_QUEUE_PATH )
_retry_delivery_active =False





def _hash_password (password :str )->str :
    """Hash a password with SHA-256 + salt for secure storage."""
    salt ="FaceStudio_v2_salt"
    return hashlib .sha256 (f"{salt }{password }".encode ()).hexdigest ()


def _verify_password (password :str ,hashed :str )->bool :
    """Check if a password matches its hash."""
    return _hash_password (password )==hashed 






_last_demo_code :dict ={"code":None ,"method":None }


def _send_email (to_email :str ,subject :str ,body_html :str )->bool :
    """Send an email via SMTP. Returns True on success.
    If SMTP is not configured, runs in demo mode (code shown in app)."""
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD :
        print ("[EMAIL] SMTP not configured — running in demo mode.")
        print (f"  To: {to_email }")
        print (f"  Subject: {subject }")
        _last_demo_code ["method"]="email"
        return True 

    try :
        msg =MIMEMultipart ("alternative")
        msg ["From"]=f"Face Studio <{SMTP_EMAIL }>"
        msg ["To"]=to_email 
        msg ["Subject"]=subject 
        msg .attach (MIMEText (body_html ,"html"))

        with smtplib .SMTP (SMTP_SERVER ,SMTP_PORT ,timeout =10 )as server :
            server .ehlo ()
            server .starttls ()
            server .ehlo ()
            server .login (SMTP_EMAIL ,SMTP_APP_PASSWORD )
            server .sendmail (SMTP_EMAIL ,to_email ,msg .as_string ())
        print (f"[EMAIL] Sent to {to_email }")
        _last_demo_code ["method"]=None 
        return True 
    except Exception as e :
        print (f"[EMAIL ERROR] {e }")
        if _retry_delivery_active :
            return False
        _retry_queue .enqueue ("email",{
        "to_email":to_email ,
        "subject":subject ,
        "body_html":body_html ,
        },str (e ))

        print ("[EMAIL] Falling back to demo mode — code will be shown in app.")
        _last_demo_code ["method"]="email_fallback"
        return True 


def _process_retry_job (job :dict )->bool :
    """Retry one queued outbound job without enqueuing another duplicate on failure."""
    global _retry_delivery_active
    payload =job .get ("payload")or {}
    kind =job .get ("kind")
    _retry_delivery_active =True
    try :
        if kind =="email":
            return _send_email (
            str (payload .get ("to_email")or ""),
            str (payload .get ("subject")or ""),
            str (payload .get ("body_html")or ""),
            )
        if kind =="sms":
            return _send_sms (
            str (payload .get ("to_phone")or ""),
            str (payload .get ("message")or ""),
            )
        print (f"[RETRY QUEUE] Unknown job kind: {kind }")
        return True
    finally :
        _retry_delivery_active =False


_retry_queue .start_worker ()


def _send_verification_email (to_email :str ,code :str )->bool :
    """Send a 6-digit verification code via email."""
    html =f"""
    <div style="font-family:Segoe UI,Arial; max-width:480px; margin:auto;
                padding:30px; background:#1a1a2e; color:white; border-radius:12px;">
        <h1 style="color:#e94560; text-align:center;">🧑 Face Studio</h1>
        <p style="text-align:center; color:#a0a0b8;">Your verification code is:</p>
        <h2 style="text-align:center; color:#e94560; font-size:36px;
                   letter-spacing:8px; background:#16213e; padding:15px;
                   border-radius:8px;">{code }</h2>
        <p style="text-align:center; color:#777; font-size:12px;">
            This code expires in 10 minutes.<br>
            If you did not request this, please ignore this email.
        </p>
    </div>
    """
    return _send_email (to_email ,f"Face Studio — Verification Code: {code }",html )


def _send_password_reset_email (to_email :str ,code :str )->bool :
    """Send a password reset code via email."""
    html =f"""
    <div style="font-family:Segoe UI,Arial; max-width:480px; margin:auto;
                padding:30px; background:#1a1a2e; color:white; border-radius:12px;">
        <h1 style="color:#e94560; text-align:center;">🧑 Face Studio</h1>
        <p style="text-align:center; color:#a0a0b8;">
            You requested a password reset. Use this code:</p>
        <h2 style="text-align:center; color:#e94560; font-size:36px;
                   letter-spacing:8px; background:#16213e; padding:15px;
                   border-radius:8px;">{code }</h2>
        <p style="text-align:center; color:#777; font-size:12px;">
            This code expires in 10 minutes.<br>
            If you did not request this, your account is safe — ignore this email.
        </p>
    </div>
    """
    return _send_email (to_email ,f"Face Studio — Password Reset Code: {code }",html )





def _send_sms (to_phone :str ,message :str )->bool :
    """Send SMS via Twilio. Returns True on success.
    If Twilio is not configured, runs in demo mode (code shown in app)."""
    if not TWILIO_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER :
        print ("[SMS] Twilio not configured — running in demo mode.")
        print (f"  To: {to_phone }")
        print (f"  Message: {message }")
        _last_demo_code ["method"]="sms"
        return True 

    try :
        import urllib .request 
        import urllib .parse 

        url =f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID }/Messages.json"
        data =urllib .parse .urlencode ({
        "To":to_phone ,
        "From":TWILIO_PHONE_NUMBER ,
        "Body":message ,
        }).encode ()

        credentials =f"{TWILIO_SID }:{TWILIO_AUTH_TOKEN }"
        import base64 
        auth_header ="Basic "+base64 .b64encode (credentials .encode ()).decode ()

        req =urllib .request .Request (url ,data =data ,method ="POST")
        req .add_header ("Authorization",auth_header )
        req .add_header ("Content-Type","application/x-www-form-urlencoded")

        with urllib .request .urlopen (req ,timeout =10 )as resp :
            if resp .status ==201 :
                print (f"[SMS] Sent to {to_phone }")
                return True 
        if not _retry_delivery_active :
            _retry_queue .enqueue ("sms",{"to_phone":to_phone ,"message":message },f"HTTP status {resp .status}")
        return False 
    except Exception as e :
        print (f"[SMS ERROR] {e }")
        if not _retry_delivery_active :
            _retry_queue .enqueue ("sms",{"to_phone":to_phone ,"message":message },str (e ))
        return False 


def _send_verification_sms (to_phone :str ,code :str )->bool :
    """Send a 6-digit verification code via SMS."""
    return _send_sms (to_phone ,f"Face Studio — Your verification code is: {code }. Expires in 10 minutes.")





def _generate_code (key :str ,length :int =6 )->str :
    """Generate a random numeric code and store it with a 10-min expiry."""
    code ="".join (random .choices (string .digits ,k =length ))
    _pending_codes [key ]={
    "code":code ,
    "expires":datetime .now ()+timedelta (minutes =10 ),
    }
    return code 


def _validate_code (key :str ,entered_code :str )->bool :
    """Check if the entered code matches and hasn't expired."""
    entry =_pending_codes .get (key )
    if not entry :
        return False 
    if datetime .now ()>entry ["expires"]:
        _pending_codes .pop (key ,None )
        return False 
    if entry ["code"]==entered_code .strip ():
        _pending_codes .pop (key ,None )
        return True 
    return False 


def _sql_connect ():
    conn =sqlite3 .connect (SQL_DB_PATH )
    conn .row_factory =sqlite3 .Row
    conn .execute ("PRAGMA journal_mode=WAL")
    conn .execute ("PRAGMA synchronous=NORMAL")
    conn .execute ("PRAGMA foreign_keys=ON")
    return conn


def _init_sql_db ():
    with _sql_connect ()as conn :
        conn .execute (
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            email TEXT,
            phone TEXT,
            role TEXT,
            created TEXT,
            logins_json TEXT,
            verified_email INTEGER,
            data_json TEXT
        )
        """
        )
        conn .execute (
        """
        CREATE TABLE IF NOT EXISTS kv_store (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        )
        """
        )
        conn .execute (
        """
        CREATE TABLE IF NOT EXISTS face_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            distance REAL,
            event_time TEXT,
            payload_json TEXT NOT NULL
        )
        """
        )
        conn .execute (
        """
        CREATE TABLE IF NOT EXISTS activity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT,
            username TEXT,
            role TEXT,
            action TEXT,
            detail TEXT,
            payload_json TEXT NOT NULL
        )
        """
        )
        conn .execute (
        """
        CREATE TABLE IF NOT EXISTS attendance_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload_json TEXT NOT NULL
        )
        """
        )
        conn .execute (
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        )
        """
        )
        conn .execute ("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        conn .execute ("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)")
        conn .execute ("CREATE INDEX IF NOT EXISTS idx_face_events_time ON face_events(event_time)")
        conn .execute ("CREATE INDEX IF NOT EXISTS idx_activity_events_time ON activity_events(event_time)")
        conn .commit ()


def _kv_legacy_load (key :str ,default ):
    with _sql_connect ()as conn :
        row =conn .execute ("SELECT value_json FROM kv_store WHERE key=?",(key ,)).fetchone ()
    if not row :
        return default 
    try :
        return json .loads (row ["value_json"])
    except (json .JSONDecodeError ,TypeError ):
        return default 


def _load_face_log_entries ()->list :
    with _sql_connect ()as conn :
        rows =conn .execute ("SELECT payload_json FROM face_events ORDER BY id").fetchall ()
    out =[]
    for row in rows :
        try :
            obj =json .loads (row ["payload_json"])
            if isinstance (obj ,dict ):
                out .append (obj )
        except (json .JSONDecodeError ,TypeError ):
            pass 
    return out 


def _replace_face_log_entries (entries :list ):
    rows =[]
    for e in entries :
        if not isinstance (e ,dict ):
            continue 
        rows .append ((
        e .get ("name",""),
        float (e .get ("distance",0 )or 0 ),
        e .get ("time",""),
        json .dumps (e ,ensure_ascii =False ),
        ))
    with _sql_connect ()as conn :
        conn .execute ("DELETE FROM face_events")
        if rows :
            conn .executemany (
            "INSERT INTO face_events(name, distance, event_time, payload_json) VALUES (?, ?, ?, ?)",
            rows ,
            )
        conn .commit ()


def _append_face_log_entries (entries :list ):
    rows =[]
    for e in entries :
        if not isinstance (e ,dict ):
            continue 
        rows .append ((
        e .get ("name",""),
        float (e .get ("distance",0 )or 0 ),
        e .get ("time",""),
        json .dumps (e ,ensure_ascii =False ),
        ))
    if not rows :
        return 
    with _sql_connect ()as conn :
        conn .executemany (
        "INSERT INTO face_events(name, distance, event_time, payload_json) VALUES (?, ?, ?, ?)",
        rows ,
        )
        conn .commit ()


def _load_activity_entries ()->list :
    with _sql_connect ()as conn :
        rows =conn .execute ("SELECT payload_json FROM activity_events ORDER BY id").fetchall ()
    out =[]
    for row in rows :
        try :
            obj =json .loads (row ["payload_json"])
            if isinstance (obj ,dict ):
                out .append (obj )
        except (json .JSONDecodeError ,TypeError ):
            pass 
    return out 


def _replace_activity_entries (entries :list ):
    rows =[]
    for e in entries :
        if not isinstance (e ,dict ):
            continue 
        rows .append ((
        e .get ("time",""),
        e .get ("user",""),
        e .get ("role",""),
        e .get ("action",""),
        e .get ("detail",""),
        json .dumps (e ,ensure_ascii =False ),
        ))
    with _sql_connect ()as conn :
        conn .execute ("DELETE FROM activity_events")
        if rows :
            conn .executemany (
            "INSERT INTO activity_events(event_time, username, role, action, detail, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
            rows ,
            )
        conn .commit ()


def _append_activity_entry (entry :dict ):
    if not isinstance (entry ,dict ):
        return 
    with _sql_connect ()as conn :
        conn .execute (
        "INSERT INTO activity_events(event_time, username, role, action, detail, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
        (
        entry .get ("time",""),
        entry .get ("user",""),
        entry .get ("role",""),
        entry .get ("action",""),
        entry .get ("detail",""),
        json .dumps (entry ,ensure_ascii =False ),
        ),
        )
        conn .execute (
        "DELETE FROM activity_events WHERE id IN (SELECT id FROM activity_events ORDER BY id ASC LIMIT MAX((SELECT COUNT(*) FROM activity_events) - 2000, 0))"
        )
        conn .commit ()


def _load_attendance_entries ()->list :
    with _sql_connect ()as conn :
        rows =conn .execute ("SELECT payload_json FROM attendance_entries ORDER BY id").fetchall ()
    out =[]
    for row in rows :
        try :
            obj =json .loads (row ["payload_json"])
            if isinstance (obj ,dict ):
                out .append (obj )
        except (json .JSONDecodeError ,TypeError ):
            pass 
    return out 


def _replace_attendance_entries (entries :list ):
    rows =[]
    for e in entries :
        if isinstance (e ,dict ):
            rows .append ((json .dumps (e ,ensure_ascii =False ),))
    with _sql_connect ()as conn :
        conn .execute ("DELETE FROM attendance_entries")
        if rows :
            conn .executemany ("INSERT INTO attendance_entries(payload_json) VALUES (?)",rows )
        conn .commit ()


def _load_settings_dict ()->dict :
    with _sql_connect ()as conn :
        rows =conn .execute ("SELECT setting_key, value_json FROM app_settings").fetchall ()
    out ={}
    for row in rows :
        key =row ["setting_key"]
        try :
            out [key ]=json .loads (row ["value_json"])
        except (json .JSONDecodeError ,TypeError ):
            pass 
    return out 


def _save_settings_dict (settings :dict ):
    rows =[]
    for k ,v in settings .items ():
        rows .append ((str (k ),json .dumps (v ,ensure_ascii =False )))
    with _sql_connect ()as conn :
        conn .execute ("DELETE FROM app_settings")
        if rows :
            conn .executemany ("INSERT INTO app_settings(setting_key, value_json) VALUES (?, ?)",rows )
        conn .commit ()


def _kv_load (key :str ,default ):
    if key =="face_log":
        loaded =_load_face_log_entries ()
        return default if (not loaded and default is None )else loaded 
    if key =="activity_log":
        loaded =_load_activity_entries ()
        return default if (not loaded and default is None )else loaded 
    if key =="attendance_log":
        loaded =_load_attendance_entries ()
        return default if (not loaded and default is None )else loaded 
    if key =="settings":
        loaded =_load_settings_dict ()
        return default if (not loaded and default is None )else (loaded if loaded else default )
    return _kv_legacy_load (key ,default )


def _kv_save (key :str ,value ):
    if key =="face_log":
        if isinstance (value ,list ):
            _replace_face_log_entries (value )
        return 
    if key =="activity_log":
        if isinstance (value ,list ):
            _replace_activity_entries (value )
        return 
    if key =="attendance_log":
        if isinstance (value ,list ):
            _replace_attendance_entries (value )
        return 
    if key =="settings":
        if isinstance (value ,dict ):
            _save_settings_dict (value )
        return 
    payload =json .dumps (value ,ensure_ascii =False )
    with _sql_connect ()as conn :
        conn .execute ("INSERT OR REPLACE INTO kv_store (key, value_json) VALUES (?, ?)",(key ,payload ))
        conn .commit ()


def _migrate_json_to_sql ():
    with _sql_connect ()as conn :
        users_count =conn .execute ("SELECT COUNT(*) FROM users").fetchone ()[0 ]
    if users_count ==0 and os .path .exists (USERS_DB_PATH ):
        try :
            with open (USERS_DB_PATH ,"r",encoding ="utf-8")as f :
                legacy_users =json .load (f )
            if isinstance (legacy_users ,dict ) and legacy_users :
                _save_users_db (legacy_users )
        except (json .JSONDecodeError ,IOError ):
            pass 

    if _kv_load ("face_log",None )is None and os .path .exists (FACE_LOG_JSON_PATH ):
        try :
            with open (FACE_LOG_JSON_PATH ,"r",encoding ="utf-8")as f :
                _kv_save ("face_log",json .load (f ))
        except (json .JSONDecodeError ,IOError ):
            pass 
    elif _kv_load ("face_log",None )is None :
        legacy =_kv_legacy_load ("face_log",None )
        if isinstance (legacy ,list ):
            _kv_save ("face_log",legacy )

    if _kv_load ("activity_log",None )is None and os .path .exists (ACTIVITY_LOG_JSON_PATH ):
        try :
            with open (ACTIVITY_LOG_JSON_PATH ,"r",encoding ="utf-8")as f :
                _kv_save ("activity_log",json .load (f ))
        except (json .JSONDecodeError ,IOError ):
            pass 
    elif _kv_load ("activity_log",None )is None :
        legacy =_kv_legacy_load ("activity_log",None )
        if isinstance (legacy ,list ):
            _kv_save ("activity_log",legacy )

    if _kv_load ("settings",None )is None and os .path .exists (SETTINGS_JSON_PATH ):
        try :
            with open (SETTINGS_JSON_PATH ,"r",encoding ="utf-8")as f :
                _kv_save ("settings",json .load (f ))
        except (json .JSONDecodeError ,IOError ):
            pass 
    elif _kv_load ("settings",None )is None :
        legacy =_kv_legacy_load ("settings",None )
        if isinstance (legacy ,dict ):
            _kv_save ("settings",legacy )

    if _kv_load ("attendance_log",None )is None and os .path .exists (ATTENDANCE_LOG_PATH ):
        try :
            with open (ATTENDANCE_LOG_PATH ,"r",encoding ="utf-8")as f :
                _kv_save ("attendance_log",json .load (f ))
        except (json .JSONDecodeError ,IOError ):
            pass 
    elif _kv_load ("attendance_log",None )is None :
        legacy =_kv_legacy_load ("attendance_log",None )
        if isinstance (legacy ,list ):
            _kv_save ("attendance_log",legacy )


def _load_users_db ()->dict :
    data ={}
    with _sql_connect ()as conn :
        rows =conn .execute (
        "SELECT username, password, email, phone, role, created, logins_json, verified_email, data_json FROM users"
        ).fetchall ()
    for row in rows :
        info ={
        "password":row ["password"]or "",
        "email":row ["email"]or "",
        "phone":row ["phone"]or "",
        "role":row ["role"]or "user",
        "created":row ["created"]or "",
        "logins":[],
        }
        if row ["logins_json"]:
            try :
                parsed =json .loads (row ["logins_json"])
                if isinstance (parsed ,list ):
                    info ["logins"]=parsed 
            except (json .JSONDecodeError ,TypeError ):
                pass 
        if row ["verified_email"]is not None :
            info ["verified_email"]=bool (row ["verified_email"])
        if row ["data_json"]:
            try :
                extra =json .loads (row ["data_json"])
                if isinstance (extra ,dict ):
                    info .update (extra )
            except (json .JSONDecodeError ,TypeError ):
                pass 
        data [row ["username"]]=info 
    return data 


def _save_users_db (db :dict ):
    with _sql_connect ()as conn :
        existing ={row ["username"]for row in conn .execute ("SELECT username FROM users").fetchall ()}
        for username ,info in db .items ():
            reserved ={"password","email","phone","role","created","logins","verified_email"}
            extra ={k :v for k ,v in info .items ()if k not in reserved }
            conn .execute (
            """
            INSERT INTO users (username, password, email, phone, role, created, logins_json, verified_email, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password=excluded.password,
                email=excluded.email,
                phone=excluded.phone,
                role=excluded.role,
                created=excluded.created,
                logins_json=excluded.logins_json,
                verified_email=excluded.verified_email,
                data_json=excluded.data_json
            """,
            (
            username ,
            info .get ("password",""),
            info .get ("email",""),
            info .get ("phone",""),
            info .get ("role","user"),
            info .get ("created",""),
            json .dumps (info .get ("logins",[]),ensure_ascii =False ),
            1 if info .get ("verified_email",False )else 0 ,
            json .dumps (extra ,ensure_ascii =False ),
            ),
            )
        to_delete =existing -set (db .keys ())
        if to_delete :
            q_marks =",".join (["?"]*len (to_delete ))
            conn .execute (f"DELETE FROM users WHERE username IN ({q_marks})",tuple (to_delete ))
        conn .commit ()


_init_sql_db ()
_migrate_json_to_sql ()


def _record_login (username :str ):
    """Append current timestamp to the user's login history."""
    ts =datetime .now ().strftime ("%Y-%m-%d %H:%M:%S")
    with _sql_connect ()as conn :
        row =conn .execute ("SELECT logins_json FROM users WHERE username=?",(username ,)).fetchone ()
        if not row :
            return 
        try :
            logins =json .loads (row ["logins_json"]or "[]")
            if not isinstance (logins ,list ):
                logins =[]
        except (json .JSONDecodeError ,TypeError ):
            logins =[]
        logins .append (ts )
        conn .execute (
        "UPDATE users SET logins_json=? WHERE username=?",
        (json .dumps (logins ,ensure_ascii =False ),username ),
        )
        conn .commit ()


def _find_user_by_email (email :str )->str |None :
    """Find username by email address."""
    with _sql_connect ()as conn :
        row =conn .execute (
        "SELECT username FROM users WHERE lower(email)=lower(?) LIMIT 1",
        (email ,),
        ).fetchone ()
    return row ["username"]if row else None 


def _find_user_by_phone (phone :str )->str |None :
    """Find username by phone number."""
    with _sql_connect ()as conn :
        row =conn .execute ("SELECT username FROM users WHERE phone=? LIMIT 1",(phone ,)).fetchone ()
    return row ["username"]if row else None 


def _ensure_admin_in_db ():
    """Make sure the admin account exists in the users DB."""
    db =_load_users_db ()
    if ADMIN_USERNAME not in db :
        db [ADMIN_USERNAME ]={
        "password":_hash_password (ADMIN_PASSWORD ),
        "email":"shishirbhavsar4@gmail.com",
        "phone":"+917400301950",
        "role":"admin",
        "created":datetime .now ().strftime ("%Y-%m-%d %H:%M:%S"),
        "logins":[],
        }
        _save_users_db (db )
    else :

        info =db [ADMIN_USERNAME ]
        if len (info .get ("password",""))<60 :
            info ["password"]=_hash_password (ADMIN_PASSWORD )

        if not info .get ("email"):
            info ["email"]="shishirbhavsar4@gmail.com"
        if not info .get ("phone"):
            info ["phone"]="+917400301950"
        _save_users_db (db )


def _ensure_default_user_in_db ():
    """Ensure a standard user account exists for quick user-mode validation."""
    db =_load_users_db ()
    username =DEFAULT_USER_USERNAME
    info =db .get (username ,{})

    info ["password"]=_hash_password (DEFAULT_USER_PASSWORD )
    info ["role"]="user"
    if not info .get ("created"):
        info ["created"]=datetime .now ().strftime ("%Y-%m-%d %H:%M:%S")
    if not isinstance (info .get ("logins"),list ):
        info ["logins"]=[]
    if not info .get ("email"):
        info ["email"]="user@facestudio.local"
    if not info .get ("phone"):
        info ["phone"]=""

    db [username ]=info
    _save_users_db (db )


YUNET_MODEL =os .path .join (BASE_DIR ,"config","models","face_detection_yunet_2023mar.onnx")
SFACE_MODEL =os .path .join (BASE_DIR ,"config","models","face_recognition_sface_2021dec.onnx")

os .makedirs (KNOWN_FACES_DIR ,exist_ok =True )


def _download_models ():
    """Download YuNet and SFace ONNX models if not present."""
    import urllib .request 
    models ={
    YUNET_MODEL :"https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    SFACE_MODEL :"https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    }
    for path ,url in models .items ():
        if not os .path .exists (path ):
            print (f"[INFO] Downloading {os .path .basename (path )} ...")
            urllib .request .urlretrieve (url ,path )
            print (f"[INFO] Saved: {path }")

_download_models ()


_sface_recognizer =cv2 .FaceRecognizerSF .create (SFACE_MODEL ,"")


def _create_yunet (width :int ,height :int ):
    """Create a YuNet face detector sized for the given frame dimensions."""
    det =cv2 .FaceDetectorYN .create (YUNET_MODEL ,"",(width ,height ),0.7 ,0.3 ,5000 )
    return det 


def detect_and_encode (bgr_frame :np .ndarray ,detector ):
    """Detect faces with YuNet and compute SFace embeddings.

    Returns list of (x, y, w, h, embedding) tuples.
    """
    _ ,raw_faces =detector .detect (bgr_frame )
    if raw_faces is None :
        return []

    results =[]
    for face_info in raw_faces :
        aligned =_sface_recognizer .alignCrop (bgr_frame ,face_info )
        embedding =_sface_recognizer .feature (aligned )
        x ,y ,w ,h =int (face_info [0 ]),int (face_info [1 ]),int (face_info [2 ]),int (face_info [3 ])
        results .append ((x ,y ,w ,h ,embedding .flatten ()))
    return results 


def compute_embedding (bgr_frame :np .ndarray ):
    """Compute the first face's SFace embedding from a BGR image. Returns embedding or None."""
    h ,w =bgr_frame .shape [:2 ]
    det =_create_yunet (w ,h )
    _ ,faces =det .detect (bgr_frame )
    if faces is None or len (faces )==0 :
        return None 
    aligned =_sface_recognizer .alignCrop (bgr_frame ,faces [0 ])
    return _sface_recognizer .feature (aligned ).flatten ()


def match_embedding (embedding ,known_names ,known_encs_arr ):
    """Match a single embedding against known encodings.

    Returns (name, score) — "Unknown" if no match.
    FR_COSINE returns cosine similarity: higher = more similar (1.0 = identical).
    """
    if len (known_encs_arr )==0 :
        return "Unknown",0.0 
    best_score =-1.0 
    second_best =-1.0 
    best_name ="Unknown"
    for i ,known_enc in enumerate (known_encs_arr ):
        score =_sface_recognizer .match (
        embedding .reshape (1 ,-1 ),
        known_enc .reshape (1 ,-1 ),
        cv2 .FaceRecognizerSF_FR_COSINE ,
        )
        if score >best_score :
            if best_name != known_names[i]:
                second_best =best_score 
            best_score =score 
            best_name =known_names [i ]
        elif score >second_best and known_names[i] != best_name:
            second_best =score 

    effective_threshold =float (RECOGNITION_THRESHOLD )
    margin_raw =os .getenv ("LEGACY_RECOGNITION_MARGIN","0.03")
    try :
        confidence_gate =float (margin_raw )
    except Exception :
        confidence_gate =0.03 
    confidence_gate =max (0.0 ,min (0.2 ,confidence_gate ))
    confidence_margin =best_score -second_best if second_best >=0 else best_score 

    if best_score >=effective_threshold and confidence_margin >=confidence_gate :
        return best_name ,float (best_score )
    return "Unknown",0.0 





def iou (boxA ,boxB ):
    """Intersection-over-Union for two (x,y,w,h) boxes."""
    ax ,ay ,aw ,ah =boxA 
    bx ,by ,bw ,bh =boxB 
    x1 =max (ax ,bx )
    y1 =max (ay ,by )
    x2 =min (ax +aw ,bx +bw )
    y2 =min (ay +ah ,by +bh )
    inter =max (0 ,x2 -x1 )*max (0 ,y2 -y1 )
    union =aw *ah +bw *bh -inter 
    return inter /union if union >0 else 0 





class FaceTracker :
    """
    Keeps a small history buffer per tracked face region.
    Returns the majority-voted name instead of the raw per-frame prediction,
    eliminating flickering when the person moves.

    Improvements over a naive tracker:
    - Tracks survive up to MAX_GONE_FRAMES without a matching detection,
      so a momentary detection miss doesn't erase the name label.
    - Bounding boxes are exponentially smoothed to reduce jitter.
    - IoU matching uses a low threshold so slight head movement still
      matches the existing track.
    """

    SMOOTH =0.35 

    def __init__ (self ,window :int =STABILITY_WINDOW ):
        self .window =window 
        self .tracks :list [dict ]=[]

    @staticmethod 
    def _smooth_box (old ,new ,alpha ):
        """Exponentially smooth bounding box coordinates."""
        return tuple (int (o *(1 -alpha )+n *alpha )for o ,n in zip (old ,new ))

    def update (self ,detections :list [tuple ])->list [tuple ]:
        """
        detections: [(x, y, w, h, raw_name, confidence), ...]
        Returns:    [(x, y, w, h, stable_name, best_confidence), ...]
        """
        used_trk =set ()
        used_det =set ()
        matches =[]


        pairs =[]
        for di ,det in enumerate (detections ):
            dx ,dy ,dw ,dh =det [:4 ]
            dbox =(dx ,dy ,dw ,dh )
            for ti ,trk in enumerate (self .tracks ):
                score =iou (dbox ,trk ["box"])
                if score >=IOU_THRESHOLD :
                    pairs .append ((score ,di ,ti ))
        pairs .sort (reverse =True )

        for score ,di ,ti in pairs :
            if di in used_det or ti in used_trk :
                continue 
            used_det .add (di )
            used_trk .add (ti )
            matches .append ((di ,ti ))

        new_tracks =[]


        for di ,ti in matches :
            det =detections [di ]
            dx ,dy ,dw ,dh ,raw_name ,conf =det 
            trk =self .tracks [ti ]
            trk ["box"]=self ._smooth_box (trk ["box"],(dx ,dy ,dw ,dh ),
            self .SMOOTH )
            trk ["history"].append (raw_name )
            trk ["conf_history"].append (conf )
            trk ["gone"]=0 
            new_tracks .append (trk )


        for di ,det in enumerate (detections ):
            if di in used_det :
                continue 
            dx ,dy ,dw ,dh ,raw_name ,conf =det 
            new_tracks .append ({
            "box":(dx ,dy ,dw ,dh ),
            "history":deque ([raw_name ],maxlen =self .window ),
            "conf_history":deque ([conf ],maxlen =self .window ),
            "gone":0 ,
            })


        for ti ,trk in enumerate (self .tracks ):
            if ti in used_trk :
                continue 
            trk ["gone"]+=1 
            if trk ["gone"]<=MAX_GONE_FRAMES :
                new_tracks .append (trk )

        self .tracks =new_tracks 

        results =[]
        for trk in self .tracks :
            dx ,dy ,dw ,dh =trk ["box"]
            counts =Counter (trk ["history"])
            stable_name =counts .most_common (1 )[0 ][0 ]


            name_confs =[c for n ,c in zip (trk ["history"],trk ["conf_history"])
            if n ==stable_name ]
            median_conf =sorted (name_confs )[len (name_confs )//2 ]

            results .append ((dx ,dy ,dw ,dh ,stable_name ,median_conf ))

        return results 

    def get_stable (self )->list [tuple ]:
        """Return current tracked results without modifying state."""
        results =[]
        for trk in self .tracks :
            dx ,dy ,dw ,dh =trk ["box"]
            counts =Counter (trk ["history"])
            stable_name =counts .most_common (1 )[0 ][0 ]
            name_confs =[c for n ,c in zip (trk ["history"],trk ["conf_history"])
            if n ==stable_name ]
            median_conf =sorted (name_confs )[len (name_confs )//2 ]
            results .append ((dx ,dy ,dw ,dh ,stable_name ,median_conf ))
        return results 





def _is_person_folder (entry :str ,folder_path :str )->bool :
    """Check if a directory should be treated as a person folder."""
    if not os .path .isdir (folder_path ):
        return False 
    if entry .lower ()in {s .lower ()for s in SKIP_DIRS }:
        return False 

    if entry .startswith ('.')or entry .startswith ('_'):
        return False 

    if len (entry )>2 and entry [0 ]=='n'and entry [1 :].isdigit ():
        return False 

    has_image =False 
    for fname in os .listdir (folder_path ):
        ext =os .path .splitext (fname )[1 ].lower ()
        if ext in IMAGE_EXTENSIONS :
            has_image =True 
            break 
    return has_image 


def load_encodings_from_folders ()->dict :
    """
    Scan BASE_DIR for sub-folders (each = a person).
    Compute 128-d face encodings for every image inside.
    Returns dict: {person_name: [encoding, ...], ...}
    """
    known :dict [str ,list ]={}

    for entry in sorted (os .listdir (FACES_ROOT )):
        folder_path =os .path .join (FACES_ROOT ,entry )
        if not _is_person_folder (entry ,folder_path ):
            continue 

        person_name =entry 
        encodings =[]

        for fname in os .listdir (folder_path ):
            ext =os .path .splitext (fname )[1 ].lower ()
            if ext not in IMAGE_EXTENSIONS :
                continue 

            img_path =os .path .join (folder_path ,fname )
            img =cv2 .imread (img_path )
            if img is None :
                print (f"  [SKIP] Cannot read: {img_path }")
                continue 

            emb =compute_embedding (img )
            if emb is not None :
                encodings .append (emb )
            else :
                print (f"  [SKIP] No face found in {img_path }")

        if encodings :
            known [person_name ]=encodings 
            print (f"  [OK] {person_name }: {len (encodings )} encoding(s)")

    return known 





def load_archive_encodings ()->dict :
    """
    Load sampled faces from the archive dataset and compute encodings.
    Returns dict: {identity: [encoding, ...], ...}
    """
    known :dict [str ,list ]={}
    if not os .path .isdir (ARCHIVE_DIR ):
        print ("  [ARCHIVE] No archive folder found — skipping.")
        return known 

    total_loaded =0 
    for split in ("train","val","test"):
        split_dir =os .path .join (ARCHIVE_DIR ,split )
        if not os .path .isdir (split_dir ):
            continue 

        identities =sorted (os .listdir (split_dir ))
        id_count =len (identities )
        print (f"  [ARCHIVE] Scanning {split }/ — {id_count } identities ...")

        for i ,identity in enumerate (identities ):
            id_path =os .path .join (split_dir ,identity )
            if not os .path .isdir (id_path ):
                continue 

            img_files =[f for f in os .listdir (id_path )
            if os .path .splitext (f )[1 ].lower ()in IMAGE_EXTENSIONS ]
            if not img_files :
                continue 

            sampled =random .sample (img_files ,min (MAX_ARCHIVE_SAMPLES ,len (img_files )))

            for fname in sampled :
                img =cv2 .imread (os .path .join (id_path ,fname ))
                if img is None :
                    continue 
                emb =compute_embedding (img )
                if emb is not None :
                    known .setdefault (identity ,[]).append (emb )
                    total_loaded +=1 

            if (i +1 )%1000 ==0 :
                print (f"    ... {i +1 }/{id_count } identities processed")

        print (f"    ... {split }/ done.")

    print (f"  [ARCHIVE] Total: {total_loaded } encodings loaded from archive.")
    return known 





def save_encodings (known_encodings :dict )->None :
    """Persist known face encodings dict to disk via pickle."""
    with open (ENCODINGS_PATH ,"wb")as f :
        pickle .dump (known_encodings ,f )


def load_cached_encodings ()->dict |None :
    """Load previously saved encodings. Returns dict or None."""
    if not os .path .exists (ENCODINGS_PATH ):
        return None 
    with open (ENCODINGS_PATH ,"rb")as f :
        return pickle .load (f )


def load_and_train (force_retrain =False )->dict :
    """
    Load encodings from cache or compute from scratch.
    Returns dict: {name: [encoding, ...], ...}
    """
    if not force_retrain :
        cached =load_cached_encodings ()
        if cached is not None :
            print (f"[INFO] Loaded cached encodings — {len (cached )} people.")
            return cached 

    print ("[INFO] Computing encodings from scratch (person folders + archive) ...")
    known =load_encodings_from_folders ()

    if LOAD_ARCHIVE :
        archive =load_archive_encodings ()
        for name ,encs in archive .items ():
            known .setdefault (name ,[]).extend (encs )
    else :
        print ("[INFO] Archive loading disabled (LOAD_ARCHIVE=False) — skipping.")

    if not known :
        print ("[WARN] No face encodings found. Starting empty.")
        return {}

    total =sum (len (v )for v in known .values ())
    print (f"[INFO] {len (known )} people, {total } encodings. Saving cache...")
    save_encodings (known )
    return known 





def register_unknown_face (frame ,known_encodings :dict )->dict :
    """
    Prompt for the person's name in an app dialog.
    Compute face encoding and add to known_encodings.
    """
    cv2 .imshow ("Face Recognition - ESC to quit",frame )
    cv2 .waitKey (1 )

    dialog_parent =tk ._default_root 
    temp_parent =None 
    if dialog_parent is None :
        temp_parent =tk .Tk ()
        temp_parent .withdraw ()
        dialog_parent =temp_parent 

    name =simpledialog .askstring (
    "Register Unknown Face",
    "Unknown face detected. Enter person's name:",
    parent =dialog_parent ,
    )

    name ,person_dir =_resolve_person_folder_for_registration (name ,dialog_parent )
    if temp_parent is not None :
        temp_parent .destroy ()
    if not name or not person_dir :
        print ("  [SKIP] No name entered.")
        return known_encodings 

    os .makedirs (person_dir ,exist_ok =True )
    ts =int (time .time ())
    img_path =os .path .join (person_dir ,f"{name }_{ts }.jpg")
    cv2 .imwrite (img_path ,frame )
    print (f"  [SAVED] {img_path }")


    emb =compute_embedding (frame )
    if emb is not None :
        known_encodings .setdefault (name ,[]).append (emb )
        save_encodings (known_encodings )
        existing =len (known_encodings [name ])>1 
        action ="Updated"if existing else "Registered"
        print (f"  [OK] {action } '{name }'. Now tracking {len (known_encodings )} people.\n")
    else :
        print ("  [WARN] Could not compute face encoding from frame.")

    return known_encodings 


def _find_existing_person_dir (name :str )->str |None :
    wanted =(name or "").strip ().lower ()
    if not wanted or not os .path .isdir (FACES_ROOT ):
        return None
    for entry in os .listdir (FACES_ROOT ):
        path =os .path .join (FACES_ROOT ,entry )
        if os .path .isdir (path )and entry .strip ().lower ()==wanted :
            return path
    return None


def _first_face_image_in_dir (person_dir :str )->str |None :
    try :
        names =sorted (os .listdir (person_dir ))
    except OSError :
        return None
    for filename in names :
        ext =os .path .splitext (filename )[1 ].lower ()
        if ext in IMAGE_EXTENSIONS :
            return os .path .join (person_dir ,filename )
    return None


def _confirm_existing_person_folder (name :str ,person_dir :str ,parent )->bool :
    sample =_first_face_image_in_dir (person_dir )
    window_name =f"Existing face for {name }"
    if sample :
        img =cv2 .imread (sample )
        if img is not None :
            cv2 .imshow (window_name ,img )
            cv2 .waitKey (1 )
    answer =messagebox .askyesno (
    "Same name already exists",
    f"A face folder named '{os .path .basename (person_dir )}' already exists.\n\nIs this you?\n\nYes: save this capture in the existing folder.\nNo: enter your full name.",
    parent =parent ,
    )
    try :
        cv2 .destroyWindow (window_name )
    except Exception :
        pass
    return bool (answer )


def _resolve_person_folder_for_registration (initial_name :str ,parent )->tuple [str |None ,str |None ]:
    name =(initial_name or "").strip ()
    while name :
        existing_dir =_find_existing_person_dir (name )
        if not existing_dir :
            return name ,os .path .join (FACES_ROOT ,name )
        if _confirm_existing_person_folder (name ,existing_dir ,parent ):
            return os .path .basename (existing_dir ),existing_dir
        name =simpledialog .askstring (
        "Enter Full Name",
        "That folder belongs to someone else. Please enter your full name:",
        parent =parent ,
        )
        name =(name or "").strip ()
    return None ,None





def draw_face_label (frame ,name ,x ,y ,w ,h ):
    """
    Draw a tight bounding box around the face, with the person's name
    displayed in a label bar that sits right on top of the box.
    """
    is_known =name !="Unknown"
    color =(0 ,220 ,0 )if is_known else (0 ,0 ,255 )


    cv2 .rectangle (frame ,(x ,y ),(x +w ,y +h ),color ,2 )


    font =cv2 .FONT_HERSHEY_SIMPLEX 
    font_scale =0.7 
    thickness =2 
    display_text =name 

    (text_w ,text_h ),baseline =cv2 .getTextSize (
    display_text ,font ,font_scale ,thickness 
    )


    label_h =text_h +baseline +12 
    label_top =y -label_h 
    if label_top <0 :
        label_top =y 
        text_y_pos =y +text_h +4 
    else :
        text_y_pos =y -baseline -4 

    text_x =x +(w -text_w )//2 
    text_x =max (text_x ,2 )


    cv2 .rectangle (
    frame ,
    (x ,label_top ),
    (x +w ,label_top +label_h ),
    color ,-1 
    )


    cv2 .putText (
    frame ,display_text ,(text_x ,text_y_pos ),
    font ,font_scale ,(255 ,255 ,255 ),thickness ,cv2 .LINE_AA 
    )





def _recognize_webcam_with_model (known_encodings :dict )->None :
    """Run webcam recognition with threaded detection for smooth rendering.

    Architecture:
      Main thread  — captures frames + draws labels at full camera FPS.
      Worker thread — runs face detection + encoding asynchronously.
    HUD overlay: FPS, face count, timestamp, key hints.
    Keys:  R = register unknown | S = screenshot | ESC = quit
    """

    def _build_live_match_index (src :dict ,max_per_person :int =15 ):
        names :list [str ]=[]
        encs :list =[]
        for n ,e_list in src .items ():
            if not e_list :
                continue 
            if len (e_list )<=max_per_person :
                picks =e_list 
            else :
                picks =[]
                span =len (e_list )-1 
                for i in range (max_per_person ):
                    idx =int (round ((i *span )/max (1 ,max_per_person -1 )))
                    picks .append (e_list [idx ])
            for e in picks :
                names .append (n )
                encs .append (e )
        arr =np .array (encs )if encs else np .empty ((0 ,128 ))
        return names ,arr 

    known_names ,known_encs_arr =_build_live_match_index (known_encodings )


    _lock =threading .Lock ()
    _frame_slot =[None ]
    _worker_detections =[[]]
    _new_results =[False ]
    _running =[True ]


    _kn ={"names":known_names ,"arr":known_encs_arr }

    def detection_worker ():
        """Background: detect + encode + match faces on the latest frame."""
        yunet =None 
        while _running [0 ]:

            with _lock :
                frame =_frame_slot [0 ]
                _frame_slot [0 ]=None 
                cur_names =_kn ["names"]
                cur_arr =_kn ["arr"]

            if frame is None :
                time .sleep (0.005 )
                continue 

            h ,w =frame .shape [:2 ]
            if yunet is None :
                yunet =_create_yunet (w ,h )
            else :
                yunet .setInputSize ((w ,h ))

            results =detect_and_encode (frame ,yunet )

            detections :list [tuple ]=[]
            for (fx ,fy ,fw ,fh ,emb )in results :
                name ,conf =match_embedding (emb ,cur_names ,cur_arr )
                detections .append ((fx ,fy ,fw ,fh ,name ,conf ))

            with _lock :
                _worker_detections [0 ]=detections 
                _new_results [0 ]=True 


    worker =threading .Thread (target =detection_worker ,daemon =True )
    worker .start ()

    cap =cv2 .VideoCapture (0 ,cv2 .CAP_DSHOW )
    if not cap .isOpened ():
        _running [0 ]=False 
        print ("[ERROR] Cannot open webcam.")
        return 

    cap .set (cv2 .CAP_PROP_FRAME_WIDTH ,640 )
    cap .set (cv2 .CAP_PROP_FRAME_HEIGHT ,480 )
    cap .set (cv2 .CAP_PROP_BUFFERSIZE ,1 )

    tracker =FaceTracker ()
    last_unknown_crop =None 
    last_unknown_cache_ts =0.0 

    fps_timer =time .time ()
    fps_frame_count =0 
    fps_display =0.0 
    face_log_entries :list [dict ]=[]
    logged_names_this_sec :set =set ()
    log_timer =time .time ()

    print ("[INFO] Webcam started (threaded detection).")
    print ("[INFO] Keys: R = register | S = screenshot | ESC = quit")

    while True :
        ret ,frame =cap .read ()
        if not ret :
            break 


        fps_frame_count +=1 
        now =time .time ()
        if now -fps_timer >=1.0 :
            fps_display =fps_frame_count /(now -fps_timer )
            fps_frame_count =0 
            fps_timer =now 


        with _lock :
            _frame_slot [0 ]=frame 


        with _lock :
            if _new_results [0 ]:
                tracker .update (_worker_detections [0 ])
                _new_results [0 ]=False 


        stable =tracker .get_stable ()

        has_unknown =False 
        for (sx ,sy ,sw ,sh ,stable_name ,conf )in stable :
            draw_face_label (frame ,stable_name ,sx ,sy ,sw ,sh )

            if stable_name =="Unknown":
                has_unknown =True 
                if now -last_unknown_cache_ts >=0.25 :
                    last_unknown_cache_ts =now 
                    pad =int (max (sw ,sh )*0.2 )
                    x1 =max (0 ,sx -pad )
                    y1 =max (0 ,sy -pad )
                    x2 =min (frame .shape [1 ],sx +sw +pad )
                    y2 =min (frame .shape [0 ],sy +sh +pad )
                    if x2 >x1 and y2 >y1 :
                        last_unknown_crop =frame [y1 :y2 ,x1 :x2 ].copy ()
                    else :
                        last_unknown_crop =frame .copy ()
            else :
                if now -log_timer >=1.0 :
                    logged_names_this_sec .clear ()
                    log_timer =now 
                if stable_name not in logged_names_this_sec :
                    logged_names_this_sec .add (stable_name )
                    face_log_entries .append ({
                    "name":stable_name ,
                    "distance":round (conf ,4 ),
                    "time":time .strftime ("%Y-%m-%d %H:%M:%S"),
                    })


        h ,w_frame =frame .shape [:2 ]
        cv2 .putText (frame ,f"FPS: {fps_display :.1f}",(10 ,25 ),
        cv2 .FONT_HERSHEY_SIMPLEX ,0.55 ,(0 ,255 ,0 ),2 ,
        cv2 .LINE_AA )
        cv2 .putText (frame ,f"Faces: {len (stable )}",(w_frame -140 ,25 ),
        cv2 .FONT_HERSHEY_SIMPLEX ,0.55 ,(0 ,255 ,0 ),2 ,
        cv2 .LINE_AA )
        cv2 .putText (frame ,time .strftime ("%H:%M:%S"),(w_frame -110 ,h -12 ),
        cv2 .FONT_HERSHEY_SIMPLEX ,0.45 ,(180 ,180 ,180 ),1 ,
        cv2 .LINE_AA )

        if has_unknown :
            cv2 .putText (
            frame ,"R=register | S=screenshot | ESC=quit",
            (10 ,h -15 ),
            cv2 .FONT_HERSHEY_SIMPLEX ,0.5 ,(0 ,200 ,255 ),1 ,cv2 .LINE_AA ,
            )
        else :
            cv2 .putText (
            frame ,"S=screenshot | ESC=quit",
            (10 ,h -15 ),
            cv2 .FONT_HERSHEY_SIMPLEX ,0.45 ,(150 ,150 ,150 ),1 ,
            cv2 .LINE_AA ,
            )

        cv2 .imshow ("Face Recognition - ESC to quit",frame )
        key =cv2 .waitKey (1 )&0xFF 

        if key ==27 :
            break 


        if key in (ord ("s"),ord ("S")):
            os .makedirs (SCREENSHOT_DIR ,exist_ok =True )
            ss_path =os .path .join (
            SCREENSHOT_DIR ,f"screenshot_{int (time .time ())}.jpg")
            cv2 .imwrite (ss_path ,frame )
            print (f"[SCREENSHOT] Saved: {ss_path }")


        if key in (ord ("r"),ord ("R")):
            if last_unknown_crop is not None :
                known_encodings =register_unknown_face (
                last_unknown_crop ,known_encodings ,
                )

                new_names ,new_arr =_build_live_match_index (known_encodings )
                with _lock :
                    _kn ["names"]=new_names 
                    _kn ["arr"]=new_arr 
                tracker =FaceTracker ()
                last_unknown_crop =None 
            else :
                print ("[INFO] No unknown face currently visible to register.")

    _running [0 ]=False 
    worker .join (timeout =2 )
    cap .release ()
    cv2 .destroyAllWindows ()


    if face_log_entries :
        _append_face_log_entries (face_log_entries )
        print (f"[LOG] Saved {len (face_log_entries )} recognition events "
        f"to SQL database")


def recognize_webcam ()->None :
    """Load encodings and run webcam recognition (CLI entry point)."""
    known_encodings =load_and_train ()
    _recognize_webcam_with_model (known_encodings )





def identify_image (image_path :str )->None :
    known_encodings =load_and_train ()
    if not known_encodings :
        print ("[WARN] No faces registered. Add photos to person folders first.")
        return 

    frame =cv2 .imread (image_path )
    if frame is None :
        print (f"[ERROR] Cannot read image: {image_path }")
        sys .exit (1 )

    h_img ,w_img =frame .shape [:2 ]
    yunet =_create_yunet (w_img ,h_img )
    results =detect_and_encode (frame ,yunet )


    known_names :list [str ]=[]
    known_encs_list :list =[]
    for name ,encs in known_encodings .items ():
        for enc in encs :
            known_names .append (name )
            known_encs_list .append (enc )
    known_encs_arr =np .array (known_encs_list )if known_encs_list else np .empty ((0 ,128 ))

    for (x ,y ,w ,h ,emb )in results :
        name ,dist =match_embedding (emb ,known_names ,known_encs_arr )

        draw_face_label (frame ,name ,x ,y ,w ,h )

        if name !="Unknown":
            print (f"  Found: {name }  (distance {dist :.4f})")
        else :
            print (f"  Unknown face at ({x },{y })")

    cv2 .imshow ("Identified - press any key",frame )
    cv2 .waitKey (0 )
    cv2 .destroyAllWindows ()





STYLE_LIST =["Sketch","Cartoon","Oil Painting","HDR",
"Ghibli Art","Anime","Ghost","Emboss",
"Watercolor","Pop Art","Neon Glow","Vintage",
"Pixel Art","Thermal","Glitch","Pencil Color"]


def search_person_images (name :str )->list :
    """Search all folders (person folders + archive) for images matching *name*."""
    results =[]


    for entry in os .listdir (FACES_ROOT ):
        if entry .lower ()==name .lower ():
            folder =os .path .join (FACES_ROOT ,entry )
            if os .path .isdir (folder ):
                for f in os .listdir (folder ):
                    if os .path .splitext (f )[1 ].lower ()in IMAGE_EXTENSIONS :
                        results .append (os .path .join (folder ,f ))


    if os .path .isdir (ARCHIVE_DIR ):
        for split in ("train","val","test"):
            id_dir =os .path .join (ARCHIVE_DIR ,split ,name )
            if os .path .isdir (id_dir ):
                for f in os .listdir (id_dir ):
                    if os .path .splitext (f )[1 ].lower ()in IMAGE_EXTENSIONS :
                        results .append (os .path .join (id_dir ,f ))

    return results 


def _capture_from_webcam ():
    """Open webcam and let user capture a photo with SPACE. Returns BGR frame or None."""
    cap =cv2 .VideoCapture (0 ,cv2 .CAP_DSHOW )
    if not cap .isOpened ():
        return None 

    print ("[INFO] Webcam open — press SPACE to capture, ESC to cancel.")
    captured =None 
    while True :
        ret ,frame =cap .read ()
        if not ret :
            break 
        display =frame .copy ()
        cv2 .putText (display ,"SPACE = capture | ESC = cancel",(10 ,30 ),
        cv2 .FONT_HERSHEY_SIMPLEX ,0.7 ,(0 ,255 ,255 ),2 ,cv2 .LINE_AA )
        cv2 .imshow ("Capture Photo",display )
        key =cv2 .waitKey (1 )&0xFF 
        if key ==32 :
            captured =frame 
            break 
        elif key ==27 :
            break 

    cap .release ()
    cv2 .destroyWindow ("Capture Photo")
    return captured 


def apply_face_filter (frame :np .ndarray ,filter_name :str )->np .ndarray :
    """Apply an artistic filter to the frame."""
    h ,w =frame .shape [:2 ]
    short_side =max (1 ,min (h ,w ))

    def _quantize (img :np .ndarray ,k :int )->np .ndarray :
        data =np .float32 (img ).reshape (-1 ,3 )
        criteria =(cv2 .TERM_CRITERIA_EPS +cv2 .TERM_CRITERIA_MAX_ITER ,20 ,1.0 )
        _ ,labels ,centers =cv2 .kmeans (data ,k ,None ,criteria ,4 ,cv2 .KMEANS_PP_CENTERS )
        return centers [labels .flatten ()].reshape (img .shape ).astype (np .uint8 )

    if filter_name =="Sketch":
        gray =cv2 .cvtColor (frame ,cv2 .COLOR_BGR2GRAY )
        inv =cv2 .bitwise_not (gray )
        blur =cv2 .GaussianBlur (inv ,(25 ,25 ),0 )
        pencil =cv2 .divide (gray ,255 -blur ,scale =256 )
        return cv2 .cvtColor (pencil ,cv2 .COLOR_GRAY2BGR )

    elif filter_name =="Cartoon":
        smooth =cv2 .bilateralFilter (frame ,11 ,180 ,180 )
        smooth =cv2 .bilateralFilter (smooth ,9 ,140 ,140 )
        gray =cv2 .cvtColor (smooth ,cv2 .COLOR_BGR2GRAY )
        edges =cv2 .adaptiveThreshold (gray ,255 ,cv2 .ADAPTIVE_THRESH_GAUSSIAN_C ,cv2 .THRESH_BINARY ,9 ,2 )
        edges =cv2 .erode (edges ,np .ones ((2 ,2 ),np .uint8 ),iterations =1 )
        return cv2 .bitwise_and (smooth ,cv2 .cvtColor (edges ,cv2 .COLOR_GRAY2BGR ))

    elif filter_name =="Oil Painting":
        painted =cv2 .stylization (frame ,sigma_s =90 ,sigma_r =0.45 )
        painted =_quantize (painted ,18 )
        return cv2 .convertScaleAbs (painted ,alpha =1.08 ,beta =8 )

    elif filter_name =="HDR":
        hdr =cv2 .detailEnhance (frame ,sigma_s =12 ,sigma_r =0.2 )
        lab =cv2 .cvtColor (hdr ,cv2 .COLOR_BGR2LAB )
        l ,a ,b =cv2 .split (lab )
        l =cv2 .createCLAHE (clipLimit =4.0 ,tileGridSize =(8 ,8 )).apply (l )
        return cv2 .cvtColor (cv2 .merge ([l ,a ,b ]),cv2 .COLOR_LAB2BGR )

    elif filter_name =="Ghibli Art":
        base =cv2 .stylization (frame ,sigma_s =70 ,sigma_r =0.33 )
        hsv =cv2 .cvtColor (base ,cv2 .COLOR_BGR2HSV ).astype (np .float32 )
        hsv [:,:,0 ]=(hsv [:,:,0 ]+6 )%180 
        hsv [:,:,1 ]=np .clip (hsv [:,:,1 ]*1.22 +10 ,0 ,255 )
        hsv [:,:,2 ]=np .clip (hsv [:,:,2 ]*1.08 +16 ,0 ,255 )
        warm =cv2 .cvtColor (hsv .astype (np .uint8 ),cv2 .COLOR_HSV2BGR )
        glow =cv2 .GaussianBlur (warm ,(0 ,0 ),8 )
        return cv2 .addWeighted (warm ,0.78 ,glow ,0.32 ,6 )

    elif filter_name =="Anime":
        down =cv2 .pyrDown (frame )
        down =cv2 .pyrDown (down )
        down =cv2 .bilateralFilter (down ,9 ,120 ,120 )
        down =cv2 .bilateralFilter (down ,9 ,120 ,120 )
        up =cv2 .pyrUp (cv2 .pyrUp (down ))
        up =cv2 .resize (up ,(w ,h ),interpolation =cv2 .INTER_LINEAR )
        quant =_quantize (up ,7 )

        gray =cv2 .cvtColor (frame ,cv2 .COLOR_BGR2GRAY )
        line =cv2 .adaptiveThreshold (cv2 .medianBlur (gray ,7 ),255 ,cv2 .ADAPTIVE_THRESH_MEAN_C ,cv2 .THRESH_BINARY ,7 ,3 )
        line =cv2 .erode (line ,np .ones ((2 ,2 ),np .uint8 ),iterations =1 )

        hsv =cv2 .cvtColor (quant ,cv2 .COLOR_BGR2HSV ).astype (np .float32 )
        hsv [:,:,1 ]=np .clip (hsv [:,:,1 ]*1.55 +8 ,0 ,255 )
        hsv [:,:,2 ]=np .clip (hsv [:,:,2 ]*1.10 ,0 ,255 )
        anime =cv2 .cvtColor (hsv .astype (np .uint8 ),cv2 .COLOR_HSV2BGR )
        return cv2 .bitwise_and (anime ,cv2 .cvtColor (line ,cv2 .COLOR_GRAY2BGR ))

    elif filter_name =="Ghost":
        gray =cv2 .cvtColor (frame ,cv2 .COLOR_BGR2GRAY )
        inv =cv2 .bitwise_not (gray )
        aura =cv2 .GaussianBlur (inv ,(0 ,0 ),11 )
        blue =cv2 .addWeighted (inv ,0.6 ,aura ,0.7 ,0 )
        green =cv2 .GaussianBlur (gray ,(0 ,0 ),7 )
        red =np .zeros_like (gray )
        return cv2 .merge ([blue ,green ,red ])

    elif filter_name =="Emboss":
        kernel =np .array ([[-2 ,-1 ,0 ],[-1 ,1 ,1 ],[0 ,1 ,2 ]],dtype =np .float32 )
        emboss =cv2 .filter2D (frame ,-1 ,kernel )
        return cv2 .add (emboss ,128 )

    elif filter_name =="Watercolor":
        paint =cv2 .edgePreservingFilter (frame ,flags =1 ,sigma_s =80 ,sigma_r =0.45 )
        paint =cv2 .bilateralFilter (paint ,9 ,90 ,90 )
        hsv =cv2 .cvtColor (paint ,cv2 .COLOR_BGR2HSV ).astype (np .float32 )
        hsv [:,:,1 ]=np .clip (hsv [:,:,1 ]*0.78 ,0 ,255 )
        hsv [:,:,2 ]=np .clip (hsv [:,:,2 ]*1.08 +6 ,0 ,255 )
        return cv2 .cvtColor (hsv .astype (np .uint8 ),cv2 .COLOR_HSV2BGR )

    elif filter_name =="Pop Art":
        flat =_quantize (frame ,5 )
        lut =np .zeros ((256 ,1 ),dtype =np .uint8 )
        bands =[0 ,64 ,128 ,192 ,255 ]
        for i in range (256 ):
            lut [i ,0 ]=min (bands ,key =lambda v :abs (v -i ))
        b ,g ,r =cv2 .split (flat )
        b =cv2 .LUT (b ,lut )
        g =cv2 .LUT (g ,lut )
        r =cv2 .LUT (r ,lut )
        return cv2 .merge ([b ,g ,r ])

    elif filter_name =="Neon Glow":
        gray =cv2 .cvtColor (frame ,cv2 .COLOR_BGR2GRAY )
        edges =cv2 .Canny (gray ,70 ,180 )
        neon =np .zeros_like (frame )
        neon [:,:,0 ]=edges
        neon [:,:,1 ]=cv2 .dilate (edges ,np .ones ((3 ,3 ),np .uint8 ),iterations =1 )
        neon [:,:,2 ]=np .roll (edges ,2 ,axis =1 )
        neon =cv2 .GaussianBlur (neon ,(0 ,0 ),4 )
        dark =cv2 .convertScaleAbs (frame ,alpha =0.28 ,beta =0 )
        return cv2 .addWeighted (dark ,1.0 ,neon ,1.2 ,0 )

    elif filter_name =="Vintage":
        sepia_kernel =np .array ([[0.272 ,0.534 ,0.131 ],[0.349 ,0.686 ,0.168 ],[0.393 ,0.769 ,0.189 ]])
        sepia =cv2 .transform (frame ,sepia_kernel )
        sepia =np .clip (sepia ,0 ,255 ).astype (np .uint8 )
        mask_x =cv2 .getGaussianKernel (w ,w *0.45 )
        mask_y =cv2 .getGaussianKernel (h ,h *0.45 )
        vignette =(mask_y *mask_x .T )
        vignette =vignette /max (1e-6 ,float (vignette .max ()))
        out =sepia .astype (np .float32 )
        for c in range (3 ):
            out [:,:,c ]*=vignette
        return np .clip (out +6 ,0 ,255 ).astype (np .uint8 )

    elif filter_name =="Pixel Art":
        pix =max (6 ,short_side //72 )
        small_w =max (8 ,w //pix )
        small_h =max (8 ,h //pix )
        small =cv2 .resize (frame ,(small_w ,small_h ),interpolation =cv2 .INTER_AREA )
        small =_quantize (small ,10 )
        return cv2 .resize (small ,(w ,h ),interpolation =cv2 .INTER_NEAREST )

    elif filter_name =="Thermal":
        gray =cv2 .cvtColor (frame ,cv2 .COLOR_BGR2GRAY )
        gray =cv2 .equalizeHist (gray )
        return cv2 .applyColorMap (gray ,cv2 .COLORMAP_INFERNO )

    elif filter_name =="Glitch":
        result =frame .copy ()
        bands =random .randint (10 ,18 )
        for _ in range (bands ):
            y0 =random .randint (0 ,max (0 ,h -6 ))
            bh =random .randint (2 ,max (3 ,h //28 ))
            y1 =min (h ,y0 +bh )
            shift =random .randint (-max (2 ,w //7 ),max (2 ,w //7 ))
            result [y0 :y1 ]=np .roll (result [y0 :y1 ],shift ,axis =1 )
        b ,g ,r =cv2 .split (result )
        r =np .roll (r ,5 ,axis =1 )
        b =np .roll (b ,-5 ,axis =0 )
        result =cv2 .merge ([b ,g ,r ])
        noise =np .random .randint (0 ,38 ,(h ,w ,3 ),dtype =np .uint8 )
        result =cv2 .add (result ,noise )
        result [::4 ,:]=cv2 .convertScaleAbs (result [::4 ,:],alpha =0.7 ,beta =0 )
        return result

    elif filter_name =="Pencil Color":
        _gray ,color =cv2 .pencilSketch (frame ,sigma_s =72 ,sigma_r =0.08 ,shade_factor =0.04 )
        return color

    return frame 


def face_generation_gui (parent =None ,on_close_callback =None ):
    """
    Face Generation window:
    1. User types a person's name
    2. Chooses an artistic style
    3. If name found → generates styled image from stored photo
    4. If not found → captures webcam photo → generates styled image
    """
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Face Generation")
    win .geometry ("540x900")
    win .resizable (False ,True )
    win .configure (bg ="#1a1a2e")


    _activate_page_scroll (win ,bg ="#1a1a2e")
    button_bar =tk .Frame (win ,bg ="#1a1a2e")
    button_bar .pack (side ="bottom",fill ="x",pady =(0 ,8 ))

    fmt_var =tk .StringVar (value ="JPG")
    fmt_row =tk .Frame (button_bar ,bg ="#1a1a2e")
    fmt_row .pack (pady =(4 ,4 ))
    tk .Label (fmt_row ,text ="Format:",font =("Segoe UI",10 ),
    fg ="#a0a0b8",bg ="#1a1a2e").pack (side ="left",padx =(0 ,6 ))
    for f in ("JPG","PNG"):
        tk .Radiobutton (
        fmt_row ,text =f ,variable =fmt_var ,value =f ,
        font =("Segoe UI",10 ),fg ="white",bg ="#1a1a2e",
        selectcolor ="#0f3460",activebackground ="#1a1a2e",
        activeforeground ="white",indicatoron =True 
        ).pack (side ="left",padx =4 )

    btn_row =tk .Frame (button_bar ,bg ="#1a1a2e")
    btn_row .pack (pady =(0 ,4 ))

    download_btn =tk .Frame (btn_row ,bg ="#0f3460",cursor ="hand2")
    download_btn .pack (side ="left",ipadx =16 ,ipady =5 ,padx =(0 ,10 ))
    dl_label =tk .Label (
    download_btn ,text ="\U0001F4BE  Download",
    font =("Segoe UI",11 ,"bold"),fg ="white",bg ="#0f3460",
    cursor ="hand2"
    )
    dl_label .pack ()

    fs_btn =tk .Frame (btn_row ,bg ="#533483",cursor ="hand2")
    fs_btn .pack (side ="left",ipadx =16 ,ipady =5 )
    fs_label =tk .Label (
    fs_btn ,text ="\U0001F50D  Full Screen",
    font =("Segoe UI",11 ,"bold"),fg ="white",bg ="#533483",
    cursor ="hand2"
    )
    fs_label .pack ()


    preview_section =tk .Frame (win ,bg ="#1a1a2e")
    preview_section .pack (side ="bottom",fill ="x")

    status_var =tk .StringVar (value ="")
    tk .Label (
    preview_section ,textvariable =status_var ,
    font =("Segoe UI",9 ),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(2 ,0 ))

    preview_label =tk .Label (preview_section ,bg ="#1a1a2e",cursor ="hand2")
    preview_label .pack (pady =(2 ,4 ))


    top =tk .Frame (win ,bg ="#1a1a2e")
    top .pack (side ="top",fill ="both",expand =True )


    tk .Label (
    top ,text ="\U0001F3A8 Face Generation",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,2 ))

    tk .Label (
    top ,
    text ="Enter a person's name to find their photo,\n"
    "or capture a new one via webcam.",
    font =("Segoe UI",9 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,8 ))


    entry_frame =tk .Frame (top ,bg ="#1a1a2e")
    entry_frame .pack (pady =3 )
    tk .Label (
    entry_frame ,text ="Name:",font =("Segoe UI",11 ),
    fg ="white",bg ="#1a1a2e"
    ).pack (side ="left",padx =(0 ,8 ))
    name_var =tk .StringVar ()
    tk .Entry (
    entry_frame ,textvariable =name_var ,font =("Segoe UI",12 ),width =25 ,
    bg ="#16213e",fg ="white",insertbackground ="white",relief ="flat",bd =5 
    ).pack (side ="left")


    tk .Label (
    top ,text ="Choose Style:",font =("Segoe UI",11 ,"bold"),
    fg ="white",bg ="#1a1a2e"
    ).pack (pady =(8 ,2 ))

    style_var =tk .StringVar (value =STYLE_LIST [0 ])
    styles_frame =tk .Frame (top ,bg ="#1a1a2e")
    styles_frame .pack ()
    for i ,s in enumerate (STYLE_LIST ):
        tk .Radiobutton (
        styles_frame ,text =s ,variable =style_var ,value =s ,
        font =("Segoe UI",9 ),fg ="white",bg ="#1a1a2e",
        selectcolor ="#0f3460",activebackground ="#1a1a2e",
        activeforeground ="white",indicatoron =True ,width =14 ,anchor ="w"
        ).grid (row =i //3 ,column =i %3 ,padx =4 ,pady =1 ,sticky ="w")


    def do_generate ():
        name =name_var .get ().strip ()
        style =style_var .get ()
        if not name :
            status_var .set ("Please enter a name.")
            return 

        status_var .set (f"Searching for '{name }' ...")
        win .update ()

        found_images =search_person_images (name )

        if found_images :

            chosen_path =random .choice (found_images )
            img =cv2 .imread (chosen_path )
            if img is None :
                status_var .set ("Found file but couldn't read it.")
                return 
            status_var .set (
            f"Found {len (found_images )} image(s). Using random photo. Generating {style } ..."
            )
            win .update ()
        else :
            status_var .set (f"'{name }' not found. Opening webcam to capture ...")
            win .update ()
            img =_capture_from_webcam ()
            if img is None :
                status_var .set ("Capture cancelled.")
                return 

            person_dir =os .path .join (FACES_ROOT ,name )
            os .makedirs (person_dir ,exist_ok =True )
            ts =int (time .time ())
            cv2 .imwrite (os .path .join (person_dir ,f"{name }_{ts }.jpg"),img )
            status_var .set (f"Photo saved. Generating {style } ...")
            win .update ()


        result =apply_face_filter (img ,style )
        result =cv2 .resize (result ,GENERATED_IMAGE_SIZE ,
        interpolation =cv2 .INTER_LANCZOS4 )


        nonlocal _last_result ,_last_name ,_last_style 
        _last_result =result 
        _last_name =name 
        _last_style =style 


        preview_rgb =cv2 .cvtColor (result ,cv2 .COLOR_BGR2RGB )
        from PIL import Image ,ImageTk 
        pil_img =Image .fromarray (preview_rgb ).resize ((220 ,220 ),
        Image .LANCZOS )
        tk_img =ImageTk .PhotoImage (pil_img )
        preview_label .config (image =tk_img )
        preview_label .image =tk_img 

        status_var .set (f"Done! {GENERATED_IMAGE_SIZE [0 ]}x{GENERATED_IMAGE_SIZE [1 ]}  (click image to view full screen)")

    def do_download ():
        if _last_result is None :
            status_var .set ("Generate an image first.")
            return 
        fmt =fmt_var .get ()
        ext =".jpg"if fmt =="JPG"else ".png"
        default_name =f"{_last_name }_{_last_style }{ext }"
        path =filedialog .asksaveasfilename (
        defaultextension =ext ,
        filetypes =[(fmt ,f"*{ext }"),("All","*.*")],
        initialfile =default_name ,
        )
        if path :
            cv2 .imwrite (path ,_last_result )
            status_var .set (f"Saved: {os .path .basename (path )}")
            print (f"  [SAVED] {path }")

    def do_fullscreen ():
        if _last_result is None :
            status_var .set ("Generate an image first.")
            return 
        from PIL import Image ,ImageTk 
        fs =tk .Toplevel (win )
        fs .title (f"{_last_name } — {_last_style }")
        fs .configure (bg ="black")
        fs .attributes ("-fullscreen",True )


        scr_w =fs .winfo_screenwidth ()
        scr_h =fs .winfo_screenheight ()
        img_h ,img_w =_last_result .shape [:2 ]
        scale =min (scr_w /img_w ,scr_h /img_h )
        new_w ,new_h =int (img_w *scale ),int (img_h *scale )
        resized =cv2 .resize (_last_result ,(new_w ,new_h ),
        interpolation =cv2 .INTER_LANCZOS4 )
        rgb =cv2 .cvtColor (resized ,cv2 .COLOR_BGR2RGB )
        pil =Image .fromarray (rgb )
        tk_img =ImageTk .PhotoImage (pil )

        lbl =tk .Label (fs ,image =tk_img ,bg ="black")
        lbl .image =tk_img 
        lbl .pack (expand =True )


        fs .bind ("<Escape>",lambda e :fs .destroy ())
        fs .bind ("<Button-1>",lambda e :fs .destroy ())


    _last_result =None 
    _last_name =""
    _last_style =""


    gen_btn =tk .Frame (top ,bg ="#533483",cursor ="hand2")
    gen_btn .pack (pady =(10 ,5 ),ipadx =30 ,ipady =8 )
    gen_label =tk .Label (
    gen_btn ,text ="\u2728  Generate",
    font =("Segoe UI",13 ,"bold"),fg ="white",bg ="#533483",
    cursor ="hand2"
    )
    gen_label .pack ()
    for widget in (gen_btn ,gen_label ):
        widget .bind ("<Button-1>",lambda e :do_generate ())


    preview_label .bind ("<Button-1>",lambda e :do_fullscreen ())
    for widget in (download_btn ,dl_label ):
        widget .bind ("<Button-1>",lambda e :do_download ())
    for widget in (fs_btn ,fs_label ):
        widget .bind ("<Button-1>",lambda e :do_fullscreen ())


    def on_close ():
        cv2 .destroyAllWindows ()
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )

    if standalone :
        win .mainloop ()





class LoadingScreen :
    """A loading screen with animated progress bar and threaded task execution.

    The key fix: loading runs in a BACKGROUND THREAD while the tkinter
    event loop keeps the UI responsive.  Progress messages flow from
    the worker thread to the UI via a queue, polled every 30 ms.
    """

    def __init__ (self ,parent ,title ="Loading..."):
        self .parent =parent 
        self .win =tk .Toplevel (parent )if parent else tk .Tk ()
        self .win .title (title )
        self .win .geometry ("450x280")
        self .win .resizable (False ,False )
        self .win .configure (bg ="#1a1a2e")
        self .win .overrideredirect (True )
        self .win .attributes ("-topmost",True )


        self .win .update_idletasks ()
        x =(self .win .winfo_screenwidth ()//2 )-225 
        y =(self .win .winfo_screenheight ()//2 )-140 
        self .win .geometry (f"450x280+{x }+{y }")


        tk .Label (
        self .win ,text ="\U0001F9D1 Face Studio",
        font =("Segoe UI",22 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
        ).pack (pady =(25 ,5 ))

        tk .Label (
        self .win ,text =title ,
        font =("Segoe UI",12 ),fg ="white",bg ="#1a1a2e"
        ).pack (pady =(0 ,15 ))

        style =ttk .Style ()
        style .theme_use ("default")
        style .configure (
        "Custom.Horizontal.TProgressbar",
        troughcolor ="#16213e",
        background ="#e94560",
        thickness =20 ,
        )

        self .progress_var =tk .DoubleVar (value =0 )
        self .progress_bar =ttk .Progressbar (
        self .win ,variable =self .progress_var ,
        maximum =100 ,length =380 ,
        style ="Custom.Horizontal.TProgressbar",
        )
        self .progress_bar .pack (pady =(10 ,5 ))

        self .percent_label =tk .Label (
        self .win ,text ="0%",
        font =("Segoe UI",14 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
        )
        self .percent_label .pack ()

        self .status_label =tk .Label (
        self .win ,text ="Initializing...",
        font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
        )
        self .status_label .pack (pady =(10 ,0 ))

        self .step_label =tk .Label (
        self .win ,text ="Step 1 of 4",
        font =("Segoe UI",9 ),fg ="#555570",bg ="#1a1a2e"
        )
        self .step_label .pack (pady =(5 ,0 ))


        self ._msg_queue =queue .Queue ()
        self ._result =None 
        self ._done_var =tk .BooleanVar (value =False )

        self .win .update ()



    def _set_progress (self ,percent ,status ,step =None ,total_steps =None ):
        """Push new values into the UI widgets."""
        self .progress_var .set (percent )
        self .percent_label .config (text =f"{int (percent )}%")
        self .status_label .config (text =status )
        if step and total_steps :
            self .step_label .config (text =f"Step {step } of {total_steps }")

    def _poll_queue (self ):
        """Drain pending messages from the worker thread and repaint."""
        try :
            while True :
                msg =self ._msg_queue .get_nowait ()
                if msg [0 ]=="progress":
                    self ._set_progress (msg [1 ],msg [2 ],msg [3 ],msg [4 ])
                elif msg [0 ]=="done":
                    self ._result =msg [1 ]
                    self ._set_progress (100 ,"Complete!",4 ,4 )
                    self ._done_var .set (True )
                    return 
                elif msg [0 ]=="error":
                    self ._result =(None ,[])
                    self ._set_progress (100 ,"Error — see terminal",4 ,4 )
                    self ._done_var .set (True )
                    return 
        except queue .Empty :
            pass 
        self .win .after (30 ,self ._poll_queue )



    def run_task (self ,task_func ):
        """Run *task_func(progress_callback)* in a background thread.

        The UI remains fully responsive because `wait_variable` lets
        tkinter process events while we wait for the thread to finish.
        Returns the value produced by *task_func*.
        """
        def _worker ():
            def progress_cb (pct ,status ,step ,total ):
                self ._msg_queue .put (("progress",pct ,status ,step ,total ))
            try :
                result =task_func (progress_cb )
                self ._msg_queue .put (("done",result ))
            except Exception as exc :
                print (f"[ERROR] Loading failed: {exc }")
                self ._msg_queue .put (("error",str (exc )))

        thread =threading .Thread (target =_worker ,daemon =True )
        thread .start ()
        self .win .after (30 ,self ._poll_queue )
        self .win .wait_variable (self ._done_var )
        return self ._result 

    def close (self ):
        """Destroy the loading window."""
        self .win .destroy ()


def load_and_train_with_progress (progress_callback =None ,force_retrain =False ):
    """
    Load encodings with progress updates — safe to call from a background thread.
    progress_callback(percent, status, step, total_steps)
    Returns dict: {name: [encoding, ...], ...}
    """
    total_steps =4 
    hide_names =(_current_role !="admin")

    def update (pct ,msg ,step ):
        print (f"  [{int (pct ):3d}%] {msg }")
        if progress_callback :
            progress_callback (pct ,msg ,step ,total_steps )


    update (5 ,"Checking for cached encodings...",1 )
    if not force_retrain :
        cached =load_cached_encodings ()
        if cached is not None :
            update (100 ,f"Loaded cached encodings — {len (cached )} people",4 )
            print (f"[INFO] Encodings loaded from cache ({len (cached )} people)")
            return cached 

    update (10 ,"No cache found — computing encodings...",1 )
    print ("[INFO] Computing encodings from scratch (person folders + archive) ...")


    update (15 ,"Scanning person folders...",2 )
    known :dict [str ,list ]={}

    entries =sorted (os .listdir (FACES_ROOT ))
    valid_folders =[e for e in entries 
    if _is_person_folder (e ,os .path .join (BASE_DIR ,e ))]
    print (f"[INFO] Found {len (valid_folders )} person folders")

    for idx ,entry in enumerate (valid_folders ):
        folder_path =os .path .join (FACES_ROOT ,entry )
        person_name =entry 
        loaded =0 

        pct =15 +(idx /max (len (valid_folders ),1 ))*15 
        if hide_names :
            update (pct ,f"Encoding face {idx +1 } of {len (valid_folders )}...",2 )
        else :
            update (pct ,f"Encoding {person_name }...",2 )

        for fname in os .listdir (folder_path ):
            ext =os .path .splitext (fname )[1 ].lower ()
            if ext not in IMAGE_EXTENSIONS :
                continue 

            img_path =os .path .join (folder_path ,fname )
            img =cv2 .imread (img_path )
            if img is None :
                continue 

            emb =compute_embedding (img )
            if emb is not None :
                known .setdefault (person_name ,[]).append (emb )
                loaded +=1 

        if loaded >0 :
            print (f"    [OK] {person_name }: {loaded } encoding(s)")

    total_enc =sum (len (v )for v in known .values ())
    update (30 ,f"Loaded {len (valid_folders )} person folders ({total_enc } encodings)",2 )
    print (f"[INFO] Person folders done: {total_enc } encodings from "
    f"{len (valid_folders )} people")


    update (35 ,"Loading archive dataset...",3 )

    if LOAD_ARCHIVE and os .path .isdir (ARCHIVE_DIR ):
        total_identities =0 
        split_counts ={}
        for split in ("train","val","test"):
            split_dir =os .path .join (ARCHIVE_DIR ,split )
            if os .path .isdir (split_dir ):
                dirs =[d for d in os .listdir (split_dir )
                if os .path .isdir (os .path .join (split_dir ,d ))]
                split_counts [split ]=len (dirs )
                total_identities +=len (dirs )

        print (f"[INFO] Archive: {total_identities } identities across "
        f"{len (split_counts )} split(s)")

        processed =0 
        for split in ("train","val","test"):
            split_dir =os .path .join (ARCHIVE_DIR ,split )
            if not os .path .isdir (split_dir ):
                continue 

            identities =sorted (os .listdir (split_dir ))
            id_count =len (identities )
            print (f"  [ARCHIVE] Scanning {split }/ — {id_count } identities ...")

            for i ,identity in enumerate (identities ):
                id_path =os .path .join (split_dir ,identity )
                if not os .path .isdir (id_path ):
                    processed +=1 
                    continue 

                pct =35 +(processed /max (total_identities ,1 ))*40 
                if processed %200 ==0 :
                    update (min (pct ,75 ),
                    f"Archive: {split }/ — {i +1 }/{id_count }...",3 )

                img_files =[f for f in os .listdir (id_path )
                if os .path .splitext (f )[1 ].lower ()in IMAGE_EXTENSIONS ]
                if not img_files :
                    processed +=1 
                    continue 

                sampled =random .sample (
                img_files ,min (MAX_ARCHIVE_SAMPLES ,len (img_files )))

                for fname in sampled :
                    img =cv2 .imread (os .path .join (id_path ,fname ))
                    if img is None :
                        continue 
                    emb =compute_embedding (img )
                    if emb is not None :
                        known .setdefault (identity ,[]).append (emb )

                processed +=1 

            print (f"    ... {split }/ done.")

        total_enc =sum (len (v )for v in known .values ())
        update (75 ,f"Archive loaded — {total_enc } total encodings",3 )
        print (f"[INFO] Archive loaded: {total_enc } total encodings")
    else :
        if not LOAD_ARCHIVE :
            update (75 ,"Archive skipped (LOAD_ARCHIVE=False)",3 )
            print ("[INFO] Archive loading disabled — skipping")
        else :
            update (75 ,"No archive folder found — skipping",3 )
            print ("[INFO] No archive folder found — skipping")


    if not known :
        update (100 ,"No face encodings found",4 )
        print ("[WARN] No face encodings found. Starting empty.")
        return {}

    total_enc =sum (len (v )for v in known .values ())
    update (90 ,f"Saving {total_enc } encodings to cache...",4 )
    save_encodings (known )

    update (100 ,f"Done! {len (known )} people, {total_enc } encodings",4 )
    print (f"[INFO] {len (known )} people, {total_enc } encodings. Cache saved.")

    return known 





def face_comparison_gui (parent =None ,on_close_callback =None ):
    """GUI to load two face images, compute embeddings, and show similarity."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Face Comparison")
    win .geometry ("640x620")
    win .resizable (False ,False )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F50E Face Comparison",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(15 ,2 ))
    tk .Label (
    win ,text ="Compare two face images — check if they're the same person",
    font =("Segoe UI",9 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,10 ))


    _images ={"left":None ,"right":None }
    _embeddings ={"left":None ,"right":None }


    img_row =tk .Frame (win ,bg ="#1a1a2e")
    img_row .pack (pady =5 )

    left_frame =tk .Frame (img_row ,bg ="#16213e",width =250 ,height =250 )
    left_frame .pack (side ="left",padx =15 )
    left_frame .pack_propagate (False )
    left_label =tk .Label (left_frame ,text ="Image 1\n(Click to load)",
    font =("Segoe UI",11 ),fg ="#777",bg ="#16213e")
    left_label .pack (expand =True )

    right_frame =tk .Frame (img_row ,bg ="#16213e",width =250 ,height =250 )
    right_frame .pack (side ="left",padx =15 )
    right_frame .pack_propagate (False )
    right_label =tk .Label (right_frame ,text ="Image 2\n(Click to load)",
    font =("Segoe UI",11 ),fg ="#777",bg ="#16213e")
    right_label .pack (expand =True )


    result_var =tk .StringVar (value ="")
    result_label =tk .Label (
    win ,textvariable =result_var ,
    font =("Segoe UI",14 ,"bold"),fg ="white",bg ="#1a1a2e"
    )
    result_label .pack (pady =(15 ,0 ))

    score_var =tk .StringVar (value ="")
    tk .Label (
    win ,textvariable =score_var ,
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(4 ,0 ))


    gauge_canvas =tk .Canvas (win ,width =500 ,height =40 ,bg ="#1a1a2e",
    highlightthickness =0 )
    gauge_canvas .pack (pady =(10 ,5 ))

    def _draw_gauge (similarity ):
        gauge_canvas .delete ("all")
        bar_w =480 
        bar_h =22 
        x0 ,y0 =10 ,9 

        gauge_canvas .create_rectangle (x0 ,y0 ,x0 +bar_w ,y0 +bar_h ,
        fill ="#16213e",outline ="#333")

        fill_w =int (bar_w *max (0 ,min (1 ,similarity )))
        if similarity >=0.5 :
            color ="#00c853"
        elif similarity >=0.363 :
            color ="#ffc107"
        else :
            color ="#e94560"
        if fill_w >0 :
            gauge_canvas .create_rectangle (x0 ,y0 ,x0 +fill_w ,y0 +bar_h ,
            fill =color ,outline ="")

        thresh_x =x0 +int (bar_w *RECOGNITION_THRESHOLD )
        gauge_canvas .create_line (thresh_x ,y0 -4 ,thresh_x ,y0 +bar_h +4 ,
        fill ="#e94560",width =2 ,dash =(4 ,2 ))
        gauge_canvas .create_text (thresh_x ,y0 +bar_h +10 ,
        text =f"Threshold ({RECOGNITION_THRESHOLD })",
        fill ="#e94560",font =("Segoe UI",7 ))

    def _load_image (side ):
        path =filedialog .askopenfilename (
        filetypes =[("Images","*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if not path :
            return 
        img =cv2 .imread (path )
        if img is None :
            return 
        _images [side ]=img 
        emb =compute_embedding (img )
        _embeddings [side ]=emb 


        from PIL import Image ,ImageTk 
        rgb =cv2 .cvtColor (img ,cv2 .COLOR_BGR2RGB )
        pil =Image .fromarray (rgb ).resize ((240 ,240 ),Image .LANCZOS )
        tk_img =ImageTk .PhotoImage (pil )
        lbl =left_label if side =="left"else right_label 
        lbl .config (image =tk_img ,text ="")
        lbl .image =tk_img 

        if emb is None :
            result_var .set ("No face detected in that image.")
            return 

        _compare ()

    def _compare ():
        e1 ,e2 =_embeddings ["left"],_embeddings ["right"]
        if e1 is None or e2 is None :
            return 
        score =_sface_recognizer .match (
        e1 .reshape (1 ,-1 ),e2 .reshape (1 ,-1 ),
        cv2 .FaceRecognizerSF_FR_COSINE ,
        )
        pct =max (0 ,score )*100 
        if score >=RECOGNITION_THRESHOLD :
            result_var .set (f"\u2705  MATCH — {pct :.1f}% similar")
            result_label .config (fg ="#00c853")
        else :
            result_var .set (f"\u274C  NO MATCH — {pct :.1f}% similar")
            result_label .config (fg ="#e94560")
        score_var .set (f"Cosine similarity: {score :.4f}  |  Threshold: {RECOGNITION_THRESHOLD }")
        _draw_gauge (score )


    for w in (left_frame ,left_label ):
        w .bind ("<Button-1>",lambda e :_load_image ("left"))
        w .config (cursor ="hand2")
    for w in (right_frame ,right_label ):
        w .bind ("<Button-1>",lambda e :_load_image ("right"))
        w .config (cursor ="hand2")


    def _webcam_capture (side ):
        img =_capture_from_webcam ()
        if img is None :
            return 
        _images [side ]=img 
        emb =compute_embedding (img )
        _embeddings [side ]=emb 
        from PIL import Image ,ImageTk 
        rgb =cv2 .cvtColor (img ,cv2 .COLOR_BGR2RGB )
        pil =Image .fromarray (rgb ).resize ((240 ,240 ),Image .LANCZOS )
        tk_img =ImageTk .PhotoImage (pil )
        lbl =left_label if side =="left"else right_label 
        lbl .config (image =tk_img ,text ="")
        lbl .image =tk_img 
        if emb is not None :
            _compare ()

    cam_row =tk .Frame (win ,bg ="#1a1a2e")
    cam_row .pack (pady =(10 ,0 ))
    for side ,text in [("left","\U0001F4F7 Capture Image 1"),
    ("right","\U0001F4F7 Capture Image 2")]:
        btn_f =tk .Frame (cam_row ,bg ="#0f3460",cursor ="hand2")
        btn_f .pack (side ="left",padx =10 ,ipadx =12 ,ipady =4 )
        lbl_b =tk .Label (btn_f ,text =text ,font =("Segoe UI",10 ,"bold"),
        fg ="white",bg ="#0f3460",cursor ="hand2")
        lbl_b .pack ()
        _side =side 
        for w in (btn_f ,lbl_b ):
            w .bind ("<Button-1>",lambda e ,s =_side :_webcam_capture (s ))

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def _load_attendance_log ()->list :
    entries =_kv_load ("attendance_log",[])
    return entries if isinstance (entries ,list )else []


def _save_attendance_log (entries :list ):
    _kv_save ("attendance_log",entries )


def attendance_webcam (known_encodings :dict )->None :
    """Run webcam-based attendance. Each person is logged once per session."""
    known_names :list [str ]=[]
    known_encs_list :list =[]
    for name ,encs in known_encodings .items ():
        for enc in encs :
            known_names .append (name )
            known_encs_list .append (enc )
    known_encs_arr =np .array (known_encs_list )if known_encs_list else np .empty ((0 ,128 ))

    cap =cv2 .VideoCapture (0 ,cv2 .CAP_DSHOW )
    if not cap .isOpened ():
        print ("[ERROR] Cannot open webcam.")
        return 

    yunet =None 
    session_date =datetime .now ().strftime ("%Y-%m-%d")
    session_time_start =datetime .now ().strftime ("%H:%M:%S")
    marked :dict [str ,str ]={}

    attendance_log =_load_attendance_log ()

    print ("[ATTENDANCE] Webcam started. Recognized people will be marked present.")
    print ("[ATTENDANCE] Press Q to finish and save, ESC to cancel.")

    while True :
        ret ,frame =cap .read ()
        if not ret :
            break 

        h ,w =frame .shape [:2 ]
        if yunet is None :
            yunet =_create_yunet (w ,h )
        else :
            yunet .setInputSize ((w ,h ))

        results =detect_and_encode (frame ,yunet )

        for (fx ,fy ,fw ,fh ,emb )in results :
            name ,score =match_embedding (emb ,known_names ,known_encs_arr )
            color =(0 ,220 ,0 )if name !="Unknown"else (0 ,0 ,255 )
            cv2 .rectangle (frame ,(fx ,fy ),(fx +fw ,fy +fh ),color ,2 )

            if name !="Unknown":
                if name not in marked :
                    marked [name ]=datetime .now ().strftime ("%H:%M:%S")
                    print (f"  [PRESENT] {name } — marked at {marked [name ]}")
                label =f"{name } [PRESENT]"
                cv2 .putText (frame ,label ,(fx ,fy -10 ),
                cv2 .FONT_HERSHEY_SIMPLEX ,0.6 ,(0 ,220 ,0 ),2 ,
                cv2 .LINE_AA )
            else :
                cv2 .putText (frame ,"Unknown",(fx ,fy -10 ),
                cv2 .FONT_HERSHEY_SIMPLEX ,0.6 ,(0 ,0 ,255 ),2 ,
                cv2 .LINE_AA )


        present_count =len (marked )
        total_known =len (known_encodings )
        cv2 .putText (frame ,f"Attendance: {present_count }/{total_known }",
        (10 ,25 ),cv2 .FONT_HERSHEY_SIMPLEX ,0.6 ,(0 ,255 ,255 ),2 ,
        cv2 .LINE_AA )
        cv2 .putText (frame ,f"Date: {session_date }",(10 ,50 ),
        cv2 .FONT_HERSHEY_SIMPLEX ,0.5 ,(180 ,180 ,180 ),1 ,
        cv2 .LINE_AA )
        cv2 .putText (frame ,"Q = save & quit | ESC = cancel",
        (10 ,h -15 ),cv2 .FONT_HERSHEY_SIMPLEX ,0.45 ,
        (150 ,150 ,150 ),1 ,cv2 .LINE_AA )

        cv2 .imshow ("Attendance - Q to save, ESC to cancel",frame )
        key =cv2 .waitKey (1 )&0xFF 

        if key ==27 :
            print ("[ATTENDANCE] Cancelled — nothing saved.")
            break 
        if key in (ord ("q"),ord ("Q")):

            session ={
            "date":session_date ,
            "time_start":session_time_start ,
            "time_end":datetime .now ().strftime ("%H:%M:%S"),
            "total_registered":total_known ,
            "present_count":present_count ,
            "present":{name :ts for name ,ts in marked .items ()},
            "absent":[n for n in known_encodings if n not in marked ],
            }
            attendance_log .append (session )
            _save_attendance_log (attendance_log )
            print (f"[ATTENDANCE] Saved! {present_count }/{total_known } present.")
            _export_attendance_csv (session )
            break 

    cap .release ()
    cv2 .destroyAllWindows ()


def _export_attendance_csv (session :dict ):
    """Export a single attendance session to a CSV file."""
    os .makedirs (ATTENDANCE_DIR ,exist_ok =True )
    date_str =session ["date"].replace ("-","")
    csv_path =os .path .join (ATTENDANCE_DIR ,f"attendance_{date_str }.csv")
    with open (csv_path ,"w",newline ="",encoding ="utf-8")as f :
        writer =csv .writer (f )
        writer .writerow (["Name","Status","Time Marked","Date"])
        for name ,ts in session ["present"].items ():
            writer .writerow ([name ,"Present",ts ,session ["date"]])
        for name in session ["absent"]:
            writer .writerow ([name ,"Absent","",session ["date"]])
    print (f"[ATTENDANCE] CSV exported: {csv_path }")


def attendance_report_gui (parent =None ,on_close_callback =None ):
    """GUI to view past attendance sessions and export reports."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Attendance Reports")
    win .geometry ("600x500")
    win .resizable (False ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F4CB Attendance Reports",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(15 ,5 ))

    log =_load_attendance_log ()
    if not log :
        tk .Label (
        win ,text ="No attendance sessions recorded yet.\n"
        "Use Face Recognition → Attendance mode first.",
        font =("Segoe UI",11 ),fg ="#a0a0b8",bg ="#1a1a2e"
        ).pack (expand =True )
    else :

        total_sessions =len (log )
        all_present =set ()
        for s in log :
            all_present .update (s .get ("present",{}).keys ())
        tk .Label (
        win ,text =f"{total_sessions } session(s) | "
        f"{len (all_present )} unique attendees",
        font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
        ).pack (pady =(0 ,10 ))


        cols =("Date","Time","Present","Absent","Rate")
        tree =ttk .Treeview (win ,columns =cols ,show ="headings",height =12 )
        for c in cols :
            tree .heading (c ,text =c )
            tree .column (c ,width =110 ,anchor ="center")

        for s in reversed (log ):
            present =s .get ("present_count",0 )
            total =s .get ("total_registered",0 )
            rate =f"{present /total *100 :.0f}%"if total >0 else "N/A"
            absent =len (s .get ("absent",[]))
            tree .insert ("","end",values =(
            s ["date"],
            s .get ("time_start",""),
            present ,
            absent ,
            rate ,
            ))

        tree .pack (padx =15 ,fill ="both",expand =True )


        def _export_all ():
            path =filedialog .asksaveasfilename (
            defaultextension =".csv",
            filetypes =[("CSV","*.csv")],
            initialfile ="attendance_all.csv",
            )
            if not path :
                return 
            with open (path ,"w",newline ="",encoding ="utf-8")as f :
                writer =csv .writer (f )
                writer .writerow (["Date","Time Start","Time End",
                "Present","Total","Rate",
                "Present Names","Absent Names"])
                for s in log :
                    present =s .get ("present_count",0 )
                    total =s .get ("total_registered",0 )
                    rate =f"{present /total *100 :.0f}%"if total else "N/A"
                    writer .writerow ([
                    s ["date"],
                    s .get ("time_start",""),
                    s .get ("time_end",""),
                    present ,total ,rate ,
                    "; ".join (s .get ("present",{}).keys ()),
                    "; ".join (s .get ("absent",[])),
                    ])
            messagebox .showinfo ("Exported",f"Saved to {path }",parent =win )

        btn_f =tk .Frame (win ,bg ="#0f3460",cursor ="hand2")
        btn_f .pack (pady =10 ,ipadx =16 ,ipady =5 )
        lbl_b =tk .Label (btn_f ,text ="\U0001F4E5  Export All Sessions (CSV)",
        font =("Segoe UI",11 ,"bold"),fg ="white",
        bg ="#0f3460",cursor ="hand2")
        lbl_b .pack ()
        for w in (btn_f ,lbl_b ):
            w .bind ("<Button-1>",lambda e :_export_all ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def face_database_gui (parent =None ,on_close_callback =None ):
    """GUI to manage the face database — view people, preview images, delete."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Face Database Manager")
    win .geometry ("680x580")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F5C3 Face Database Manager",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,2 ))


    people :list [dict ]=[]
    for entry in sorted (os .listdir (FACES_ROOT )):
        folder =os .path .join (FACES_ROOT ,entry )
        if _is_person_folder (entry ,folder ):
            imgs =[f for f in os .listdir (folder )
            if os .path .splitext (f )[1 ].lower ()in IMAGE_EXTENSIONS ]
            people .append ({"name":entry ,"folder":folder ,"images":imgs })

    tk .Label (
    win ,text =f"{len (people )} registered people | "
    f"{sum (len (p ['images'])for p in people )} total images",
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,8 ))


    content =tk .Frame (win ,bg ="#1a1a2e")
    content .pack (fill ="both",expand =True ,padx =10 )


    left_panel =tk .Frame (content ,bg ="#16213e",width =220 )
    left_panel .pack (side ="left",fill ="y",padx =(0 ,8 ))
    left_panel .pack_propagate (False )

    listbox =tk .Listbox (
    left_panel ,bg ="#16213e",fg ="white",font =("Segoe UI",11 ),
    selectbackground ="#0f3460",selectforeground ="white",
    highlightthickness =0 ,relief ="flat"
    )
    listbox .pack (fill ="both",expand =True ,padx =4 ,pady =4 )

    for p in people :
        listbox .insert ("end",f"  {p ['name']}  ({len (p ['images'])} imgs)")


    right_panel =tk .Frame (content ,bg ="#1a1a2e")
    right_panel .pack (side ="left",fill ="both",expand =True )

    info_var =tk .StringVar (value ="Select a person from the list")
    tk .Label (right_panel ,textvariable =info_var ,font =("Segoe UI",11 ),
    fg ="white",bg ="#1a1a2e").pack (pady =(5 ,5 ))


    thumb_frame =tk .Frame (right_panel ,bg ="#1a1a2e")
    thumb_frame .pack (fill ="both",expand =True )

    _thumb_refs =[]

    def _show_person (event ):
        idx =listbox .curselection ()
        if not idx :
            return 
        person =people [idx [0 ]]
        info_var .set (f"{person ['name']} — {len (person ['images'])} image(s)")


        for w in thumb_frame .winfo_children ():
            w .destroy ()
        _thumb_refs .clear ()

        from PIL import Image ,ImageTk 
        for i ,fname in enumerate (person ["images"][:12 ]):
            img_path =os .path .join (person ["folder"],fname )
            img =cv2 .imread (img_path )
            if img is None :
                continue 
            rgb =cv2 .cvtColor (img ,cv2 .COLOR_BGR2RGB )
            pil =Image .fromarray (rgb ).resize ((90 ,90 ),Image .LANCZOS )
            tk_img =ImageTk .PhotoImage (pil )
            _thumb_refs .append (tk_img )
            lbl =tk .Label (thumb_frame ,image =tk_img ,bg ="#1a1a2e")
            lbl .grid (row =i //4 ,column =i %4 ,padx =4 ,pady =4 )

    listbox .bind ("<<ListboxSelect>>",_show_person )


    btn_bar =tk .Frame (win ,bg ="#1a1a2e")
    btn_bar .pack (pady =(8 ,10 ))

    def _delete_person ():
        idx =listbox .curselection ()
        if not idx :
            messagebox .showwarning ("Select","Select a person first.",parent =win )
            return 
        person =people [idx [0 ]]
        confirm =messagebox .askyesno (
        "Delete Person",
        f"Delete '{person ['name']}' and all {len (person ['images'])} images?\n"
        f"This cannot be undone.",
        parent =win ,
        )
        if not confirm :
            return 
        import shutil 
        shutil .rmtree (person ["folder"])

        cached =load_cached_encodings ()
        if cached and person ["name"]in cached :
            del cached [person ["name"]]
            save_encodings (cached )
        listbox .delete (idx [0 ])
        people .pop (idx [0 ])
        info_var .set (f"Deleted '{person ['name']}'")
        for w in thumb_frame .winfo_children ():
            w .destroy ()
        print (f"[DB] Deleted person '{person ['name']}' and their images.")

    def _retrain ():
        if os .path .exists (ENCODINGS_PATH ):
            os .remove (ENCODINGS_PATH )
        load_and_train (force_retrain =True )
        messagebox .showinfo ("Retrained","Face encodings rebuilt from scratch.",
        parent =win )

    del_btn =tk .Frame (btn_bar ,bg ="#e94560",cursor ="hand2")
    del_btn .pack (side ="left",padx =8 ,ipadx =14 ,ipady =5 )
    del_lbl =tk .Label (del_btn ,text ="\U0001F5D1  Delete Person",
    font =("Segoe UI",10 ,"bold"),fg ="white",
    bg ="#e94560",cursor ="hand2")
    del_lbl .pack ()
    for w in (del_btn ,del_lbl ):
        w .bind ("<Button-1>",lambda e :_delete_person ())

    retrain_btn =tk .Frame (btn_bar ,bg ="#0f3460",cursor ="hand2")
    retrain_btn .pack (side ="left",padx =8 ,ipadx =14 ,ipady =5 )
    retrain_lbl =tk .Label (retrain_btn ,text ="\U0001F504  Retrain All",
    font =("Segoe UI",10 ,"bold"),fg ="white",
    bg ="#0f3460",cursor ="hand2")
    retrain_lbl .pack ()
    for w in (retrain_btn ,retrain_lbl ):
        w .bind ("<Button-1>",lambda e :_retrain ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def analytics_dashboard_gui (parent =None ,on_close_callback =None ):
    """Show recognition analytics: most seen people, activity by hour, etc."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Analytics Dashboard")
    win .geometry ("700x620")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F4CA Analytics Dashboard",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,5 ))


    entries =_kv_load ("face_log",[])
    if not isinstance (entries ,list ):
        entries =[]

    if not entries :
        tk .Label (
        win ,text ="No recognition data yet.\n"
        "Use Face Recognition via webcam to generate logs.",
        font =("Segoe UI",12 ),fg ="#a0a0b8",bg ="#1a1a2e"
        ).pack (expand =True )
    else :

        name_counts :Counter =Counter ()
        hour_counts :Counter =Counter ()
        date_counts :Counter =Counter ()
        scores :list [float ]=[]

        for e in entries :
            name_counts [e .get ("name","Unknown")]+=1 
            ts =e .get ("time","")
            if len (ts )>=13 :
                hour =ts [11 :13 ]
                hour_counts [hour ]+=1 
            if len (ts )>=10 :
                date_counts [ts [:10 ]]+=1 
            d =e .get ("distance",0 )
            if d >0 :
                scores .append (d )

        total_detections =len (entries )
        unique_people =len (name_counts )
        avg_score =sum (scores )/len (scores )if scores else 0 


        cards =tk .Frame (win ,bg ="#1a1a2e")
        cards .pack (fill ="x",padx =20 ,pady =(5 ,10 ))
        for label ,value ,color in [
        ("Total Detections",str (total_detections ),"#0f3460"),
        ("Unique People",str (unique_people ),"#533483"),
        ("Avg. Similarity",f"{avg_score :.3f}","#e94560"),
        ("Sessions (Days)",str (len (date_counts )),"#16213e"),
        ]:
            card =tk .Frame (cards ,bg =color ,width =150 ,height =70 )
            card .pack (side ="left",padx =6 ,expand =True ,fill ="x")
            card .pack_propagate (False )
            tk .Label (card ,text =value ,font =("Segoe UI",18 ,"bold"),
            fg ="white",bg =color ).pack (pady =(8 ,0 ))
            tk .Label (card ,text =label ,font =("Segoe UI",8 ),
            fg ="#ccc",bg =color ).pack ()


        tk .Label (win ,text ="Most Recognized People",
        font =("Segoe UI",12 ,"bold"),fg ="white",
        bg ="#1a1a2e").pack (pady =(5 ,2 ))

        chart_canvas =tk .Canvas (win ,width =660 ,height =180 ,bg ="#16213e",
        highlightthickness =0 )
        chart_canvas .pack (padx =15 ,pady =(0 ,8 ))

        top_people =name_counts .most_common (10 )
        if top_people :
            max_val =top_people [0 ][1 ]
            bar_max_w =450 
            y_start =15 
            bar_h =14 
            gap =3 
            for i ,(name ,count )in enumerate (top_people ):
                y =y_start +i *(bar_h +gap )
                w_bar =int ((count /max_val )*bar_max_w )if max_val >0 else 0 
                chart_canvas .create_text (120 ,y +bar_h //2 ,text =name ,
                anchor ="e",fill ="white",
                font =("Segoe UI",9 ))
                chart_canvas .create_rectangle (130 ,y ,130 +w_bar ,y +bar_h ,
                fill ="#e94560",outline ="")
                chart_canvas .create_text (135 +w_bar ,y +bar_h //2 ,
                text =str (count ),anchor ="w",
                fill ="#aaa",font =("Segoe UI",8 ))


        tk .Label (win ,text ="Activity by Hour of Day",
        font =("Segoe UI",12 ,"bold"),fg ="white",
        bg ="#1a1a2e").pack (pady =(5 ,2 ))

        hour_canvas =tk .Canvas (win ,width =660 ,height =130 ,bg ="#16213e",
        highlightthickness =0 )
        hour_canvas .pack (padx =15 ,pady =(0 ,8 ))

        max_hour =max (hour_counts .values ())if hour_counts else 1 
        bar_w =24 
        x_start =20 
        chart_h =100 
        for h in range (24 ):
            count =hour_counts .get (f"{h :02d}",0 )
            bar_h_px =int ((count /max_hour )*80 )if max_hour >0 else 0 
            x =x_start +h *(bar_w +3 )
            y_bottom =chart_h 
            y_top =y_bottom -bar_h_px 
            color ="#e94560"if bar_h_px >0 else "#2a2a4e"
            hour_canvas .create_rectangle (x ,y_top ,x +bar_w ,y_bottom ,
            fill =color ,outline ="")
            hour_canvas .create_text (x +bar_w //2 ,chart_h +12 ,
            text =f"{h }",fill ="#888",
            font =("Segoe UI",7 ))


        def _export_log ():
            path =filedialog .asksaveasfilename (
            defaultextension =".csv",
            filetypes =[("CSV","*.csv")],
            initialfile ="recognition_log.csv",
            )
            if not path :
                return 
            with open (path ,"w",newline ="",encoding ="utf-8")as f :
                writer =csv .writer (f )
                writer .writerow (["Name","Similarity","Timestamp"])
                for e in entries :
                    writer .writerow ([
                    e .get ("name",""),
                    e .get ("distance",""),
                    e .get ("time",""),
                    ])
            messagebox .showinfo ("Exported",f"Saved {len (entries )} entries.",
            parent =win )

        exp_f =tk .Frame (win ,bg ="#0f3460",cursor ="hand2")
        exp_f .pack (pady =(5 ,10 ),ipadx =16 ,ipady =5 )
        exp_l =tk .Label (exp_f ,text ="\U0001F4E5  Export Recognition Log (CSV)",
        font =("Segoe UI",11 ,"bold"),fg ="white",
        bg ="#0f3460",cursor ="hand2")
        exp_l .pack ()
        for w in (exp_f ,exp_l ):
            w .bind ("<Button-1>",lambda e :_export_log ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()









def _make_styled_entry (parent ,textvariable ,show =None ,placeholder ="",width =24 ):
    """Create a dark styled entry field with an optional placeholder."""
    entry =tk .Entry (
    parent ,textvariable =textvariable ,
    font =("Segoe UI",11 ),width =width ,
    bg ="#0a0a1a",fg ="white",insertbackground ="white",
    relief ="flat",highlightthickness =1 ,
    highlightcolor ="#e94560",highlightbackground ="#333",
    )
    if show :
        entry .config (show =show )

    if placeholder :
        _ph_color ="#666"
        _fg_color ="white"

        def _on_focus_in (e ):
            if textvariable .get ()==placeholder :
                textvariable .set ("")
                entry .config (fg =_fg_color ,show =show or "")

        def _on_focus_out (e ):
            if not textvariable .get ():
                textvariable .set (placeholder )
                entry .config (fg =_ph_color ,show ="")

        textvariable .set (placeholder )
        entry .config (fg =_ph_color ,show ="")
        entry .bind ("<FocusIn>",_on_focus_in )
        entry .bind ("<FocusOut>",_on_focus_out )
    return entry 


def _make_action_button (parent ,text ,color ,command ,font_size =12 ):
    """Create a colored button with hover effect."""
    bf =tk .Frame (parent ,bg =color ,cursor ="hand2")
    bf .pack (pady =6 ,ipadx =20 ,ipady =7 ,fill ="x",padx =30 )
    lbl =tk .Label (bf ,text =text ,font =("Segoe UI",font_size ,"bold"),
    fg ="white",bg =color ,cursor ="hand2")
    lbl .pack ()

    def _to_rgb (hx ):
        h =hx .lstrip ("#")
        return tuple (int (h [i :i +2 ],16 )for i in (0 ,2 ,4 ))

    def _to_hex (rgb ):
        return f"#{rgb [0 ]:02x}{rgb [1 ]:02x}{rgb [2 ]:02x}"

    def _blend (c1 ,c2 ,t ):
        a =_to_rgb (c1 )
        b =_to_rgb (c2 )
        return _to_hex (tuple (int (a [i ]+(b [i ]-a [i ])*t )for i in range (3 )))

    base_color =color 
    hover_color =_blend (color ,"#ffffff",0.18 )
    state ={"token":0 }

    def _animate (to_hover ):
        state ["token"]+=1 
        token =state ["token"]
        start =bf .cget ("bg")
        end =hover_color if to_hover else base_color 

        def _step (i ):
            if state ["token"]!=token :
                return 
            t =i /6.0 
            c =_blend (start ,end ,t )
            bf .config (bg =c )
            lbl .config (bg =c )
            if i <6 :
                bf .after (16 ,lambda :_step (i +1 ))

        _step (0 )

    for w in (bf ,lbl ):
        w .bind ("<Button-1>",lambda e :command ())
        w .bind ("<Enter>",lambda e :_animate (True ))
        w .bind ("<Leave>",lambda e :_animate (False ))
    return bf 


def _make_link_label (parent ,text ,command ,fg ="#e94560"):
    """Create a clickable link-styled label."""
    lbl =tk .Label (parent ,text =text ,font =("Segoe UI",10 ,"bold underline"),
    fg =fg ,bg ="#1a1a2e",cursor ="hand2")
    lbl .bind ("<Button-1>",lambda e :command ())

    def _to_rgb (hx ):
        h =hx .lstrip ("#")
        return tuple (int (h [i :i +2 ],16 )for i in (0 ,2 ,4 ))

    def _to_hex (rgb ):
        return f"#{rgb [0 ]:02x}{rgb [1 ]:02x}{rgb [2 ]:02x}"

    def _blend (c1 ,c2 ,t ):
        a =_to_rgb (c1 )
        b =_to_rgb (c2 )
        return _to_hex (tuple (int (a [i ]+(b [i ]-a [i ])*t )for i in range (3 )))

    base_fg =fg 
    hover_fg =_blend (fg ,"#ffffff",0.25 )
    state ={"token":0 }

    def _animate (to_hover ):
        state ["token"]+=1 
        token =state ["token"]
        start =lbl .cget ("fg")
        end =hover_fg if to_hover else base_fg 

        def _step (i ):
            if state ["token"]!=token :
                return 
            t =i /5.0 
            lbl .config (fg =_blend (start ,end ,t ))
            if i <5 :
                lbl .after (16 ,lambda :_step (i +1 ))

        _step (0 )

    lbl .bind ("<Enter>",lambda e :_animate (True ))
    lbl .bind ("<Leave>",lambda e :_animate (False ))
    return lbl 


def _animate_window_fade_in (window ,duration_ms =260 ,steps =16 ):
    try :
        window .attributes ("-alpha",0.0 )
    except Exception :
        return 

    total_steps =max (1 ,int (steps ))
    delay =max (8 ,int (duration_ms /total_steps ))

    def _step (i ):
        alpha =min (1.0 ,i /float (total_steps ))
        try :
            window .attributes ("-alpha",alpha )
        except Exception :
            return 
        if i <total_steps :
            window .after (delay ,lambda :_step (i +1 ))

    _step (0 )


def launch_login ():
    """Professional login page with Email, Google auth, Sign Up, Forgot Password."""
    global _current_role ,_current_username 
    _ensure_admin_in_db ()
    _ensure_default_user_in_db ()

    win =tk .Tk ()
    win .title ("Face Studio")
    win .geometry ("480x680")
    win .resizable (False ,False )
    win .configure (bg ="#1a1a2e")
    _activate_page_scroll (win ,bg ="#1a1a2e")
    _animate_window_fade_in (win )


    win .update_idletasks ()
    sw ,sh =win .winfo_screenwidth (),win .winfo_screenheight ()
    win .geometry (f"480x680+{sw //2 -240 }+{sh //2 -340 }")


    _container =tk .Frame (win ,bg ="#1a1a2e")
    _container .pack (fill ="both",expand =True )

    def _clear ():
        for child in _container .winfo_children ():
            child .destroy ()

    def _finish_login (username ):
        """Common login completion — record, set globals, launch home."""
        global _current_role ,_current_username 
        db =_load_users_db ()
        _current_role =db .get (username ,{}).get ("role","user")
        _current_username =username 
        _record_login (username )
        win .destroy ()
        launch_home ()




    def _show_main_login ():
        _clear ()


        tk .Label (_container ,text ="\U0001F9D1",font =("Segoe UI",48 ),
        fg ="#e94560",bg ="#1a1a2e").pack (pady =(30 ,0 ))
        tk .Label (_container ,text ="Face Studio",
        font =("Segoe UI",28 ,"bold"),fg ="#e94560",
        bg ="#1a1a2e").pack (pady =(0 ,5 ))
        tk .Label (_container ,text ="Sign in to continue",
        font =("Segoe UI",11 ),fg ="#a0a0b8",
        bg ="#1a1a2e").pack (pady =(0 ,20 ))


        card =tk .Frame (_container ,bg ="#16213e")
        card .pack (padx =35 ,fill ="x",ipady =10 )


        tk .Label (card ,text ="Username or Email",font =("Segoe UI",9 ),
        fg ="#a0a0b8",bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(12 ,2 ))
        uname_var =tk .StringVar ()
        uname_entry =_make_styled_entry (card ,uname_var )
        uname_entry .pack (padx =30 ,pady =(0 ,6 ))


        tk .Label (card ,text ="Password",font =("Segoe UI",9 ),
        fg ="#a0a0b8",bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(4 ,2 ))
        pw_var =tk .StringVar ()
        pw_entry =_make_styled_entry (card ,pw_var ,show ="\u2022")
        pw_entry .pack (padx =30 ,pady =(0 ,4 ))


        show_pw =tk .BooleanVar (value =False )
        def _toggle_pw ():
            pw_entry .config (show =""if show_pw .get ()else "\u2022")
        tk .Checkbutton (card ,text ="Show password",variable =show_pw ,
        command =_toggle_pw ,font =("Segoe UI",8 ),
        fg ="#888",bg ="#16213e",selectcolor ="#0a0a1a",
        activebackground ="#16213e",activeforeground ="#888"
        ).pack (anchor ="w",padx =30 )


        err_var =tk .StringVar ()
        tk .Label (card ,textvariable =err_var ,font =("Segoe UI",9 ),
        fg ="#e94560",bg ="#16213e").pack (pady =(2 ,0 ))


        def _do_login ():
            uname =uname_var .get ().strip ()
            pw =pw_var .get ()
            if not uname or not pw :
                err_var .set ("Please enter username/email and password")
                return 
            db =_load_users_db ()

            target_user =None 
            if uname in db :
                target_user =uname 
            else :
                target_user =_find_user_by_email (uname )
            if not target_user :
                err_var .set ("Account not found")
                return 
            info =db [target_user ]

            stored =info .get ("password","")
            if len (stored )==64 :
                if not _verify_password (pw ,stored ):
                    err_var .set ("Incorrect password")
                    return 
            else :
                if stored !=pw :
                    err_var .set ("Incorrect password")
                    return 
            _finish_login (target_user )

        _make_action_button (card ,"Log In","#e94560",_do_login )


        fp_frame =tk .Frame (card ,bg ="#16213e")
        fp_frame .pack (pady =(4 ,8 ))
        fp_lbl =tk .Label (fp_frame ,text ="Forgot password?",
        font =("Segoe UI",9 ,"underline"),
        fg ="#e94560",bg ="#16213e",cursor ="hand2")
        fp_lbl .pack ()
        fp_lbl .bind ("<Button-1>",lambda e :_show_forgot_password ())


        div_frame =tk .Frame (_container ,bg ="#1a1a2e")
        div_frame .pack (fill ="x",padx =50 ,pady =(12 ,8 ))
        tk .Frame (div_frame ,bg ="#333",height =1 ).pack (side ="left",expand =True ,fill ="x")
        tk .Label (div_frame ,text ="  OR  ",font =("Segoe UI",9 ,"bold"),
        fg ="#555",bg ="#1a1a2e").pack (side ="left")
        tk .Frame (div_frame ,bg ="#333",height =1 ).pack (side ="left",expand =True ,fill ="x")


        def _start_google ():
            _show_google_login ()

        g_frame =tk .Frame (_container ,bg ="#db4437",cursor ="hand2")
        g_frame .pack (padx =35 ,fill ="x",ipady =8 ,pady =4 )
        g_inner =tk .Frame (g_frame ,bg ="#db4437")
        g_inner .pack ()
        tk .Label (g_inner ,text ="\U0001F4E7",font =("Segoe UI",14 ),
        fg ="white",bg ="#db4437").pack (side ="left",padx =(0 ,8 ))
        g_lbl =tk .Label (g_inner ,text ="Continue with Google",
        font =("Segoe UI",12 ,"bold"),fg ="white",
        bg ="#db4437",cursor ="hand2")
        g_lbl .pack (side ="left")
        for w in (g_frame ,g_inner ,g_lbl ):
            w .bind ("<Button-1>",lambda e :_start_google ())


        su_frame =tk .Frame (_container ,bg ="#1a1a2e")
        su_frame .pack (pady =(16 ,0 ))
        tk .Label (su_frame ,text ="Don't have an account? ",
        font =("Segoe UI",10 ),fg ="#a0a0b8",
        bg ="#1a1a2e").pack (side ="left")
        su_lbl =tk .Label (su_frame ,text ="Sign Up",
        font =("Segoe UI",10 ,"bold underline"),
        fg ="#e94560",bg ="#1a1a2e",cursor ="hand2")
        su_lbl .pack (side ="left")
        su_lbl .bind ("<Button-1>",lambda e :_show_signup ())

        uname_entry .focus_set ()
        pw_entry .bind ("<Return>",lambda e :_do_login ())




    def _show_google_login ():
        _clear ()

        tk .Label (_container ,text ="\U0001F4E7",font =("Segoe UI",40 ),
        fg ="#db4437",bg ="#1a1a2e").pack (pady =(35 ,0 ))
        tk .Label (_container ,text ="Google Sign In",
        font =("Segoe UI",22 ,"bold"),fg ="white",
        bg ="#1a1a2e").pack (pady =(0 ,3 ))
        tk .Label (_container ,text ="We'll send a verification code to your email",
        font =("Segoe UI",10 ),fg ="#a0a0b8",
        bg ="#1a1a2e").pack (pady =(0 ,18 ))

        card =tk .Frame (_container ,bg ="#16213e")
        card .pack (padx =40 ,fill ="x",ipady =12 )

        tk .Label (card ,text ="Email Address",font =("Segoe UI",9 ),
        fg ="#a0a0b8",bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(12 ,2 ))
        email_var =tk .StringVar ()
        email_entry =_make_styled_entry (card ,email_var )
        email_entry .pack (padx =30 ,pady =(0 ,6 ))

        tk .Label (card ,text ="Password",font =("Segoe UI",9 ),
        fg ="#a0a0b8",bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(4 ,2 ))
        gpw_var =tk .StringVar ()
        gpw_entry =_make_styled_entry (card ,gpw_var ,show ="\u2022")
        gpw_entry .pack (padx =30 ,pady =(0 ,6 ))

        err_var =tk .StringVar ()
        tk .Label (card ,textvariable =err_var ,font =("Segoe UI",9 ),
        fg ="#e94560",bg ="#16213e").pack (pady =(2 ,0 ))

        status_var =tk .StringVar ()
        tk .Label (card ,textvariable =status_var ,font =("Segoe UI",9 ),
        fg ="#25d366",bg ="#16213e").pack (pady =(0 ,2 ))

        def _send_code ():
            email =email_var .get ().strip ()
            pw =gpw_var .get ()
            if not email or "@"not in email :
                err_var .set ("Please enter a valid email address")
                return 
            if not pw :
                err_var .set ("Please enter your password")
                return 

            username =_find_user_by_email (email )
            if not username :
                err_var .set ("No account linked to this email. Sign up first.")
                return 

            db =_load_users_db ()
            stored =db [username ].get ("password","")
            if len (stored )==64 :
                if not _verify_password (pw ,stored ):
                    err_var .set ("Incorrect password")
                    return 
            else :
                if stored !=pw :
                    err_var .set ("Incorrect password")
                    return 


            if str (db [username ].get ("role","")).lower ()=="admin":
                err_var .set ("")
                status_var .set ("Admin login successful")
                _finish_login (username )
                return 

            code =_generate_code (f"google_{email }")
            status_var .set ("Sending code...")
            err_var .set ("")
            win .update ()

            def _bg_send ():
                success =_send_verification_email (email ,code )
                if success :
                    demo =_last_demo_code .get ("method")in ("email","email_fallback")
                    def _update_ui ():
                        if demo :
                            status_var .set (f"Demo mode — code: {code }")
                        else :
                            status_var .set (f"Code sent to {email }!")
                        _show_verify_code_after_send (email ,username ,code )
                    win .after (0 ,_update_ui )
                else :
                    win .after (0 ,lambda :err_var .set ("Failed to send email. Check SMTP settings."))

            threading .Thread (target =_bg_send ,daemon =True ).start ()

        _make_action_button (card ,"Send Verification Code","#db4437",_send_code )


        code_frame =tk .Frame (card ,bg ="#16213e")

        tk .Label (card ,text ="",bg ="#16213e").pack (pady =2 )

        code_var =tk .StringVar ()
        code_entry =None 

        def _show_verify_code_after_send (email ,username ,code ):
            nonlocal code_entry 
            if code_frame .winfo_children ():
                return 
            tk .Label (code_frame ,text ="Enter 6-digit code:",font =("Segoe UI",9 ),
            fg ="#a0a0b8",bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(8 ,2 ))
            code_entry =_make_styled_entry (code_frame ,code_var ,width =12 )
            code_entry .pack (padx =30 ,pady =(0 ,6 ))
            code_entry .focus_set ()

            def _verify ():
                if _validate_code (f"google_{email }",code_var .get ()):
                    _finish_login (username )
                else :
                    err_var .set ("Invalid or expired code")

            def _resend ():
                new_code =_generate_code (f"google_{email }")
                status_var .set ("Resending code...")
                err_var .set ("")

                def _bg_resend ():
                    success =_send_verification_email (email ,new_code )
                    if success :
                        demo =_last_demo_code .get ("method")in ("email","email_fallback")
                        def _ok ():
                            if demo :
                                status_var .set (f"Demo mode — code: {new_code }")
                            else :
                                status_var .set (f"Code resent to {email }!")
                        win .after (0 ,_ok )
                    else :
                        win .after (0 ,lambda :err_var .set ("Failed to resend code"))

                threading .Thread (target =_bg_resend ,daemon =True ).start ()

            _make_action_button (code_frame ,"Verify & Sign In","#0f3460",_verify )
            _make_action_button (code_frame ,"Resend Code","#1a5276",_resend )
            code_frame .pack (fill ="x")
            code_entry .bind ("<Return>",lambda e :_verify ())


        back =tk .Label (_container ,text ="\u2190 Back to Login",
        font =("Segoe UI",10 ,"underline"),
        fg ="#e94560",bg ="#1a1a2e",cursor ="hand2")
        back .pack (pady =(15 ,0 ))
        back .bind ("<Button-1>",lambda e :_show_main_login ())

        email_entry .focus_set ()




    def _show_signup ():
        _clear ()

        tk .Label (_container ,text ="\U0001F4DD",font =("Segoe UI",40 ),
        fg ="#e94560",bg ="#1a1a2e").pack (pady =(25 ,0 ))
        tk .Label (_container ,text ="Create Account",
        font =("Segoe UI",22 ,"bold"),fg ="white",
        bg ="#1a1a2e").pack (pady =(0 ,3 ))
        tk .Label (_container ,text ="Sign up with your details",
        font =("Segoe UI",10 ),fg ="#a0a0b8",
        bg ="#1a1a2e").pack (pady =(0 ,12 ))

        card =tk .Frame (_container ,bg ="#16213e")
        card .pack (padx =35 ,fill ="x",ipady =8 )

        fields ={}
        for label ,key ,show in [
        ("Username","username",None ),
        ("Email Address","email",None ),
        ("Phone Number (optional)","phone",None ),
        ("Password","password","\u2022"),
        ("Confirm Password","confirm","\u2022"),
        ]:
            tk .Label (card ,text =label ,font =("Segoe UI",9 ),
            fg ="#a0a0b8",bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(6 ,1 ))
            var =tk .StringVar ()
            entry =_make_styled_entry (card ,var ,show =show )
            entry .pack (padx =30 ,pady =(0 ,2 ))
            fields [key ]=var 

        err_var =tk .StringVar ()
        tk .Label (card ,textvariable =err_var ,font =("Segoe UI",9 ),
        fg ="#e94560",bg ="#16213e").pack (pady =(4 ,2 ))

        status_var =tk .StringVar ()
        tk .Label (card ,textvariable =status_var ,font =("Segoe UI",9 ),
        fg ="#25d366",bg ="#16213e").pack (pady =(0 ,2 ))


        _signup_state ={"step":"form","code_sent":False }

        verify_frame =tk .Frame (card ,bg ="#16213e")
        code_var =tk .StringVar ()

        def _do_signup ():
            uname =fields ["username"].get ().strip ()
            email =fields ["email"].get ().strip ()
            phone =fields ["phone"].get ().strip ()
            pw =fields ["password"].get ()
            confirm =fields ["confirm"].get ()
            err_var .set ("")
            status_var .set ("")

            if not uname or len (uname )<2 :
                err_var .set ("Username must be at least 2 characters")
                return 
            if not email or "@"not in email or "."not in email :
                err_var .set ("Please enter a valid email address")
                return 
            if not pw or len (pw )<4 :
                err_var .set ("Password must be at least 4 characters")
                return 
            if pw !=confirm :
                err_var .set ("Passwords do not match")
                return 

            db =_load_users_db ()
            if uname in db :
                err_var .set ("Username already taken")
                return 
            if _find_user_by_email (email ):
                err_var .set ("Email already registered")
                return 

            if _signup_state ["step"]=="form":

                code =_generate_code (f"signup_{email }")
                status_var .set ("Sending verification code to your email...")
                win .update ()

                def _bg_send ():
                    success =_send_verification_email (email ,code )
                    if success :
                        demo =_last_demo_code .get ("method")in ("email","email_fallback")
                        def _update_ui ():
                            if demo :
                                status_var .set (f"Demo mode \u2014 code: {code }")
                            else :
                                status_var .set (f"Code sent to {email }!")
                            _show_signup_verify (email ,uname ,pw ,phone )
                        win .after (0 ,_update_ui )
                    else :
                        win .after (0 ,lambda :err_var .set ("Failed to send email"))

                threading .Thread (target =_bg_send ,daemon =True ).start ()
                _signup_state ["step"]="verify"
                return 

        def _show_signup_verify (email ,uname ,pw ,phone ):
            if verify_frame .winfo_children ():
                return 
            tk .Label (verify_frame ,text ="Enter the 6-digit code sent to your email:",
            font =("Segoe UI",9 ),fg ="#a0a0b8",
            bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(8 ,2 ))
            c_entry =_make_styled_entry (verify_frame ,code_var ,width =12 )
            c_entry .pack (padx =30 ,pady =(0 ,6 ))
            c_entry .focus_set ()

            def _verify_and_create ():
                if not _validate_code (f"signup_{email }",code_var .get ()):
                    err_var .set ("Invalid or expired code")
                    return 

                db =_load_users_db ()
                db [uname ]={
                "password":_hash_password (pw ),
                "email":email ,
                "phone":phone ,
                "role":"user",
                "created":datetime .now ().strftime ("%Y-%m-%d %H:%M:%S"),
                "logins":[datetime .now ().strftime ("%Y-%m-%d %H:%M:%S")],
                "verified_email":True ,
                }
                _save_users_db (db )
                _finish_login (uname )

            def _resend_signup_code ():
                new_code =_generate_code (f"signup_{email }")
                status_var .set ("Resending verification code...")
                err_var .set ("")

                def _bg_resend ():
                    success =_send_verification_email (email ,new_code )
                    if success :
                        demo =_last_demo_code .get ("method")in ("email","email_fallback")
                        def _ok ():
                            if demo :
                                status_var .set (f"Demo mode — code: {new_code }")
                            else :
                                status_var .set (f"Code resent to {email }!")
                        win .after (0 ,_ok )
                    else :
                        win .after (0 ,lambda :err_var .set ("Failed to resend code"))

                threading .Thread (target =_bg_resend ,daemon =True ).start ()

            _make_action_button (verify_frame ,"Verify & Create Account",
            "#0f3460",_verify_and_create )
            _make_action_button (verify_frame ,"Resend Code",
            "#1a5276",_resend_signup_code )
            verify_frame .pack (fill ="x")
            c_entry .bind ("<Return>",lambda e :_verify_and_create ())

        _make_action_button (card ,"Sign Up","#e94560",_do_signup )


        la_frame =tk .Frame (_container ,bg ="#1a1a2e")
        la_frame .pack (pady =(10 ,0 ))
        tk .Label (la_frame ,text ="Already have an account? ",
        font =("Segoe UI",10 ),fg ="#a0a0b8",
        bg ="#1a1a2e").pack (side ="left")
        la_lbl =tk .Label (la_frame ,text ="Log In",
        font =("Segoe UI",10 ,"bold underline"),
        fg ="#e94560",bg ="#1a1a2e",cursor ="hand2")
        la_lbl .pack (side ="left")
        la_lbl .bind ("<Button-1>",lambda e :_show_main_login ())




    def _show_forgot_password ():
        _clear ()

        tk .Label (_container ,text ="\U0001F510",font =("Segoe UI",40 ),
        fg ="#e94560",bg ="#1a1a2e").pack (pady =(35 ,0 ))
        tk .Label (_container ,text ="Reset Password",
        font =("Segoe UI",22 ,"bold"),fg ="white",
        bg ="#1a1a2e").pack (pady =(0 ,3 ))
        tk .Label (_container ,text ="Choose how to reset your password",
        font =("Segoe UI",10 ),fg ="#a0a0b8",
        bg ="#1a1a2e").pack (pady =(0 ,18 ))


        tab_frame =tk .Frame (_container ,bg ="#1a1a2e")
        tab_frame .pack (pady =(0 ,8 ))
        method_var =tk .StringVar (value ="email")

        tab_btns ={}
        for method ,text in [("email","\U0001F4E7 Email"),
        ("username","\U0001F464 Username")]:
            bf =tk .Frame (tab_frame ,bg ="#333",cursor ="hand2")
            bf .pack (side ="left",padx =4 ,ipadx =10 ,ipady =4 )
            l =tk .Label (bf ,text =text ,font =("Segoe UI",9 ,"bold"),
            fg ="#ccc",bg ="#333",cursor ="hand2")
            l .pack ()
            tab_btns [method ]=(bf ,l )

        card =tk .Frame (_container ,bg ="#16213e")
        card .pack (padx =40 ,fill ="x",ipady =12 )

        input_label_var =tk .StringVar (value ="Email Address")
        tk .Label (card ,textvariable =input_label_var ,font =("Segoe UI",9 ),
        fg ="#a0a0b8",bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(12 ,2 ))
        input_var =tk .StringVar ()
        input_entry =_make_styled_entry (card ,input_var )
        input_entry .pack (padx =30 ,pady =(0 ,6 ))

        err_var =tk .StringVar ()
        tk .Label (card ,textvariable =err_var ,font =("Segoe UI",9 ),
        fg ="#e94560",bg ="#16213e").pack (pady =(2 ,0 ))

        status_var =tk .StringVar ()
        tk .Label (card ,textvariable =status_var ,font =("Segoe UI",9 ),
        fg ="#25d366",bg ="#16213e").pack (pady =(0 ,2 ))

        reset_frame =tk .Frame (card ,bg ="#16213e")
        code_var =tk .StringVar ()
        new_pw_var =tk .StringVar ()
        confirm_pw_var =tk .StringVar ()

        def _switch_tab (m ):
            method_var .set (m )
            for met ,(bf ,l )in tab_btns .items ():
                if met ==m :
                    bf .config (bg ="#e94560")
                    l .config (bg ="#e94560",fg ="white")
                else :
                    bf .config (bg ="#333")
                    l .config (bg ="#333",fg ="#ccc")
            labels ={"email":"Email Address","username":"Username"}
            input_label_var .set (labels [m ])
            input_var .set ("")
            err_var .set ("")
            status_var .set ("")

        for m in ("email","username"):
            bf ,l =tab_btns [m ]
            for w in (bf ,l ):
                w .bind ("<Button-1>",lambda e ,method =m :_switch_tab (method ))
        _switch_tab ("email")

        _reset_state ={"target_user":None }

        def _send_reset_code ():
            val =input_var .get ().strip ()
            method =method_var .get ()
            err_var .set ("")
            status_var .set ("")

            if not val :
                err_var .set ("Please enter your "+method )
                return 

            db =_load_users_db ()
            target_user =None 
            send_to_email =None 

            if method =="email":
                target_user =_find_user_by_email (val )
                send_to_email =val 
            elif method =="username":
                if val in db :
                    target_user =val 
                    send_to_email =db [val ].get ("email")

            if not target_user :
                err_var .set ("No account found")
                return 

            _reset_state ["target_user"]=target_user 
            code =_generate_code (f"reset_{target_user }")

            if not send_to_email :
                err_var .set ("No email on file for this account")
                return 
            status_var .set (f"Sending reset code to {send_to_email }...")
            win .update ()

            def _bg ():
                ok =_send_password_reset_email (send_to_email ,code )
                if ok :
                    demo =_last_demo_code .get ("method")in ("email","email_fallback")
                    def _update_ui ():
                        if demo :
                            status_var .set (f"Demo mode \u2014 code: {code }")
                        else :
                            status_var .set (f"Code sent to {send_to_email }!")
                        _show_reset_verify (target_user )
                    win .after (0 ,_update_ui )
                else :
                    win .after (0 ,lambda :err_var .set ("Failed to send email"))

            threading .Thread (target =_bg ,daemon =True ).start ()

        _make_action_button (card ,"Send Reset Code","#e94560",_send_reset_code )

        def _show_reset_verify (target_user ):
            if reset_frame .winfo_children ():
                return 
            tk .Label (reset_frame ,text ="Enter 6-digit reset code:",
            font =("Segoe UI",9 ),fg ="#a0a0b8",
            bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(10 ,2 ))
            c_entry =_make_styled_entry (reset_frame ,code_var ,width =12 )
            c_entry .pack (padx =30 ,pady =(0 ,6 ))

            tk .Label (reset_frame ,text ="New Password:",
            font =("Segoe UI",9 ),fg ="#a0a0b8",
            bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(4 ,2 ))
            pw_entry =_make_styled_entry (reset_frame ,new_pw_var ,show ="\u2022")
            pw_entry .pack (padx =30 ,pady =(0 ,4 ))

            tk .Label (reset_frame ,text ="Confirm New Password:",
            font =("Segoe UI",9 ),fg ="#a0a0b8",
            bg ="#16213e").pack (anchor ="w",padx =32 ,pady =(4 ,2 ))
            cpw_entry =_make_styled_entry (reset_frame ,confirm_pw_var ,show ="\u2022")
            cpw_entry .pack (padx =30 ,pady =(0 ,6 ))

            reset_err =tk .StringVar ()
            tk .Label (reset_frame ,textvariable =reset_err ,font =("Segoe UI",9 ),
            fg ="#e94560",bg ="#16213e").pack (pady =(2 ,0 ))

            def _do_reset ():
                if not _validate_code (f"reset_{target_user }",code_var .get ()):
                    reset_err .set ("Invalid or expired code")
                    return 
                npw =new_pw_var .get ()
                if len (npw )<4 :
                    reset_err .set ("Password must be at least 4 characters")
                    return 
                if npw !=confirm_pw_var .get ():
                    reset_err .set ("Passwords do not match")
                    return 
                db =_load_users_db ()
                if target_user in db :
                    db [target_user ]["password"]=_hash_password (npw )
                    _save_users_db (db )
                    messagebox .showinfo ("Success",
                    "Password reset successfully! You can now log in.",
                    parent =win )
                    _show_main_login ()

            def _resend_reset_code ():
                db =_load_users_db ()
                user_info =db .get (target_user ,{})
                send_to_email =user_info .get ("email","")
                if not send_to_email :
                    reset_err .set ("No email found for this account")
                    return 

                new_code =_generate_code (f"reset_{target_user }")
                status_var .set ("Resending reset code...")

                def _bg_resend ():
                    ok =_send_password_reset_email (send_to_email ,new_code )
                    if ok :
                        demo =_last_demo_code .get ("method")in ("email","email_fallback")
                        def _ok ():
                            if demo :
                                status_var .set (f"Demo mode — code: {new_code }")
                            else :
                                status_var .set (f"Code resent to {send_to_email }!")
                        win .after (0 ,_ok )
                    else :
                        win .after (0 ,lambda :reset_err .set ("Failed to resend code"))

                threading .Thread (target =_bg_resend ,daemon =True ).start ()

            _make_action_button (reset_frame ,"Reset Password","#0f3460",_do_reset )
            _make_action_button (reset_frame ,"Resend Code","#1a5276",_resend_reset_code )
            reset_frame .pack (fill ="x")
            c_entry .focus_set ()


        back =tk .Label (_container ,text ="\u2190 Back to Login",
        font =("Segoe UI",10 ,"underline"),
        fg ="#e94560",bg ="#1a1a2e",cursor ="hand2")
        back .pack (pady =(12 ,0 ))
        back .bind ("<Button-1>",lambda e :_show_main_login ())

        input_entry .focus_set ()


    _show_main_login ()
    win .mainloop ()





def user_registry_gui (parent =None ,on_close_callback =None ):
    """Admin GUI showing all registered users, their roles, credentials, and login timestamps."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("User Registry")
    win .geometry ("960x650")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F4CB User Registry",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,2 ))

    db =_load_users_db ()
    total_users =len (db )
    total_logins =sum (len (u .get ("logins",[]))for u in db .values ())

    tk .Label (
    win ,text =f"{total_users } registered account(s) | {total_logins } total login(s)",
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,8 ))


    settings_cache =_load_settings ()

    control_frame =tk .Frame (win ,bg ="#1a1a2e")
    control_frame .pack (fill ="x",padx =15 ,pady =(0 ,8 ))

    tk .Label (control_frame ,text ="Search:",font =("Segoe UI",10 ,"bold"),
    fg ="#a0a0b8",bg ="#1a1a2e").pack (side ="left",padx =(0 ,6 ))

    search_var =tk .StringVar (value =str (settings_cache .get ("user_registry_search","")))
    search_entry =tk .Entry (control_frame ,textvariable =search_var ,
    font =("Segoe UI",10 ),width =32 ,bg ="#16213e",fg ="white",
    insertbackground ="white",relief ="flat")
    search_entry .pack (side ="left",padx =(0 ,6 ))

    clear_search_btn =tk .Button (control_frame ,text ="Clear",font =("Segoe UI",9 ,"bold"),
    command =lambda :search_var .set (""),bg ="#0f3460",fg ="white",
    activebackground ="#1a5276",activeforeground ="white",relief ="flat",cursor ="hand2")
    clear_search_btn .pack (side ="left",padx =(0 ,14 ))

    tk .Label (control_frame ,text ="Sort By:",font =("Segoe UI",10 ,"bold"),
    fg ="#a0a0b8",bg ="#1a1a2e").pack (side ="left",padx =(0 ,6 ))

    sort_choices =[
    "Name (A-Z)",
    "Name (Z-A)",
    "Date Created (Newest)",
    "Date Created (Oldest)",
    "Date Modified (Newest)",
    "Date Modified (Oldest)",
    "Role",
    "Most Logins",
    "Least Logins", 
    ]
    initial_sort =str (settings_cache .get ("user_registry_sort","Name (A-Z)"))
    if initial_sort not in sort_choices :
        initial_sort ="Name (A-Z)"
    sort_var =tk .StringVar (value =initial_sort )
    sort_combo =ttk .Combobox (control_frame ,textvariable =sort_var ,state ="readonly",
    values =sort_choices ,width =24 )
    sort_combo .pack (side ="left")

    result_count_var =tk .StringVar (value ="")
    tk .Label (control_frame ,textvariable =result_count_var ,font =("Segoe UI",9 ),
    fg ="#a0a0b8",bg ="#1a1a2e").pack (side ="right")

    cols =("Username","Role","Email","Phone","Created","Modified","Logins")
    tree =ttk .Treeview (win ,columns =cols ,show ="headings",height =12 )
    _header_sort_cycles ={
    "Username":["Name (A-Z)","Name (Z-A)"],
    "Role":["Role","Name (A-Z)"],
    "Email":["Name (A-Z)","Name (Z-A)"],
    "Phone":["Name (A-Z)","Name (Z-A)"],
    "Created":["Date Created (Newest)","Date Created (Oldest)"],
    "Modified":["Date Modified (Newest)","Date Modified (Oldest)"],
    "Logins":["Most Logins","Least Logins"],
    }
    _header_sort_index ={k :0 for k in _header_sort_cycles }

    def _cycle_sort_for_column (column_name :str ):
        modes =_header_sort_cycles .get (column_name ,[])
        if not modes :
            return
        idx =_header_sort_index .get (column_name ,0 )
        sort_var .set (modes [idx %len (modes )])
        _header_sort_index [column_name ]=idx +1

    for c in cols :
        tree .heading (c ,text =c ,command =lambda col =c :_cycle_sort_for_column (col ))
    tree .column ("Username",width =100 )
    tree .column ("Role",width =60 ,anchor ="center")
    tree .column ("Email",width =190 )
    tree .column ("Phone",width =110 )
    tree .column ("Created",width =140 ,anchor ="center")
    tree .column ("Modified",width =140 ,anchor ="center")
    tree .column ("Logins",width =55 ,anchor ="center")

    registry_rows =[]

    def _parse_dt (value :str ):
        if not value or value in ("Unknown","Never"):
            return datetime .min
        try :
            return datetime .strptime (value ,"%Y-%m-%d %H:%M:%S")
        except ValueError :
            return datetime .min

    def _rebuild_registry_rows ():
        registry_rows .clear ()
        for uname ,info in db .items ():
            logins =info .get ("logins",[])
            if not isinstance (logins ,list ):
                logins =[]
            created =info .get ("created","Unknown")or "Unknown"
            modified =logins [-1 ]if logins else "Never"
            registry_rows .append ({
            "username":uname ,
            "role":info .get ("role","user"),
            "email":info .get ("email","")or "-",
            "phone":info .get ("phone","")or "-",
            "created":created ,
            "modified":modified ,
            "logins":len (logins ),
            "logins_list":logins ,
            })

    def _sort_rows (rows :list ):
        mode =sort_var .get ()
        if mode =="Name (Z-A)":
            rows .sort (key =lambda r :r ["username"].lower (),reverse =True )
        elif mode =="Date Created (Newest)":
            rows .sort (key =lambda r :_parse_dt (r ["created"]),reverse =True )
        elif mode =="Date Created (Oldest)":
            rows .sort (key =lambda r :_parse_dt (r ["created"]))
        elif mode =="Date Modified (Newest)":
            rows .sort (key =lambda r :_parse_dt (r ["modified"]),reverse =True )
        elif mode =="Date Modified (Oldest)":
            rows .sort (key =lambda r :_parse_dt (r ["modified"]))
        elif mode =="Role":
            rows .sort (key =lambda r :(r ["role"].lower (),r ["username"].lower ()))
        elif mode =="Most Logins":
            rows .sort (key =lambda r :r ["logins"],reverse =True )
        elif mode =="Least Logins":
            rows .sort (key =lambda r :r ["logins"])
        else :
            rows .sort (key =lambda r :r ["username"].lower ())
        return rows

    def _apply_search_and_sort (*_args ):
        q =search_var .get ().strip ().lower ()
        filtered =[]
        for row in registry_rows :
            haystack =" ".join ([
            row ["username"],
            row ["role"],
            row ["email"],
            row ["phone"],
            row ["created"],
            row ["modified"],
            str (row ["logins"]),
            ]).lower ()
            if q and q not in haystack :
                continue
            filtered .append (row )

        _sort_rows (filtered )

        for item in tree .get_children ():
            tree .delete (item )

        for row in filtered :
            tree .insert ("","end",values =(
            row ["username"],
            row ["role"].capitalize (),
            row ["email"],
            row ["phone"],
            row ["created"],
            row ["modified"],
            row ["logins"],
            ))
        result_count_var .set (f"{len (filtered )} shown / {len (registry_rows )} total")

    _rebuild_registry_rows ()
    _apply_search_and_sort ()
    search_var .trace_add ("write",_apply_search_and_sort )
    sort_var .trace_add ("write",_apply_search_and_sort )

    tree .pack (padx =15 ,fill ="both",expand =True )


    cred_frame =tk .Frame (win ,bg ="#16213e")
    cred_frame .pack (fill ="x",padx =15 ,pady =(5 ,0 ))

    detail_var =tk .StringVar (value ="Select a user to see credentials & login history")
    detail_lbl =tk .Label (cred_frame ,textvariable =detail_var ,font =("Segoe UI",9 ),
    fg ="#a0a0b8",bg ="#16213e",wraplength =900 ,
    justify ="left")
    detail_lbl .pack (padx =10 ,pady =(5 ,0 ),anchor ="w")


    hash_var =tk .StringVar (value ="")
    hash_lbl =tk .Label (cred_frame ,textvariable =hash_var ,font =("Consolas",9 ),
    fg ="#e94560",bg ="#16213e",wraplength =900 ,
    justify ="left")
    hash_lbl .pack (padx =10 ,pady =(2 ,5 ),anchor ="w")

    _hash_visible ={"show":False ,"selected_user":None }

    def _on_select (event ):
        sel =tree .selection ()
        if not sel :
            return 
        uname =tree .item (sel [0 ])["values"][0 ]
        _hash_visible ["selected_user"]=uname 
        _hash_visible ["show"]=False 
        hash_var .set ("")
        info =db .get (uname ,{})
        logins =info .get ("logins",[])
        email =info .get ("email","")or "Not set"
        phone =info .get ("phone","")or "Not set"
        role =info .get ("role","user")
        login_str =""
        if logins :
            recent =logins [-10 :]
            login_str =f" | Last {len (recent )} login(s): "+", ".join (recent )
        else :
            login_str =" | Never logged in"
        detail_var .set (
        f"\U0001F464 {uname }  |  Role: {role }  |  Email: {email }  |  "
        f"Phone: {phone }{login_str }"
        )

    tree .bind ("<<TreeviewSelect>>",_on_select )


    btn_bar =tk .Frame (win ,bg ="#1a1a2e")
    btn_bar .pack (pady =(8 ,10 ))

    def _toggle_hash ():
        uname =_hash_visible ["selected_user"]
        if not uname :
            messagebox .showwarning ("Select","Select a user first.",parent =win )
            return 
        if _hash_visible ["show"]:
            hash_var .set ("")
            _hash_visible ["show"]=False 
        else :
            info =db .get (uname ,{})
            pw_hash =info .get ("password","N/A")
            hash_var .set (f"\U0001F512 Password Hash: {pw_hash }")
            _hash_visible ["show"]=True 

    def _export ():
        path =filedialog .asksaveasfilename (
        defaultextension =".csv",
        filetypes =[("CSV","*.csv")],
        initialfile ="user_registry.csv",
        )
        if not path :
            return 
        with open (path ,"w",newline ="",encoding ="utf-8")as f :
            writer =csv .writer (f )
            writer .writerow (["Username","Role","Email","Phone",
            "Password Hash","Created","Modified","Total Logins",
            "All Logins"])
            export_rows =_sort_rows (list (registry_rows ))
            for row in export_rows :
                uname =row ["username"]
                info =db .get (uname ,{})
                logins =row ["logins_list"]
                writer .writerow ([
                uname ,
                row ["role"],
                row ["email"],
                row ["phone"],
                info .get ("password",""),
                row ["created"],
                row ["modified"],
                len (logins ),
                "; ".join (logins ),
                ])
        messagebox .showinfo ("Exported",f"Saved to {path }",parent =win )

    def _delete_user ():
        sel =tree .selection ()
        if not sel :
            messagebox .showwarning ("Select","Select a user first.",parent =win )
            return 
        uname =tree .item (sel [0 ])["values"][0 ]
        if uname ==ADMIN_USERNAME :
            messagebox .showerror ("Error","Cannot delete the admin account.",
            parent =win )
            return 
        if not messagebox .askyesno ("Delete User",
        f"Delete user '{uname }'? This cannot be undone.",
        parent =win ):
            return 
        db .pop (uname ,None )
        _save_users_db (db )
        _rebuild_registry_rows ()
        _apply_search_and_sort ()
        detail_var .set (f"Deleted user '{uname }'. Registry refreshed.")
        hash_var .set ("")


    hash_f =tk .Frame (btn_bar ,bg ="#533483",cursor ="hand2")
    hash_f .pack (side ="left",padx =8 ,ipadx =14 ,ipady =5 )
    hash_l =tk .Label (hash_f ,text ="\U0001F510  Show/Hide Password Hash",
    font =("Segoe UI",10 ,"bold"),fg ="white",
    bg ="#533483",cursor ="hand2")
    hash_l .pack ()
    for w in (hash_f ,hash_l ):
        w .bind ("<Button-1>",lambda e :_toggle_hash ())

    exp_f =tk .Frame (btn_bar ,bg ="#0f3460",cursor ="hand2")
    exp_f .pack (side ="left",padx =8 ,ipadx =14 ,ipady =5 )
    exp_l =tk .Label (exp_f ,text ="\U0001F4E5  Export CSV",
    font =("Segoe UI",10 ,"bold"),fg ="white",
    bg ="#0f3460",cursor ="hand2")
    exp_l .pack ()
    for w in (exp_f ,exp_l ):
        w .bind ("<Button-1>",lambda e :_export ())

    del_f =tk .Frame (btn_bar ,bg ="#e94560",cursor ="hand2")
    del_f .pack (side ="left",padx =8 ,ipadx =14 ,ipady =5 )
    del_l =tk .Label (del_f ,text ="\U0001F5D1  Delete User",
    font =("Segoe UI",10 ,"bold"),fg ="white",
    bg ="#e94560",cursor ="hand2")
    del_l .pack ()
    for w in (del_f ,del_l ):
        w .bind ("<Button-1>",lambda e :_delete_user ())

    def on_close ():
        settings_cache ["user_registry_search"]=search_var .get ().strip ()
        settings_cache ["user_registry_sort"]=sort_var .get ()
        _save_settings (settings_cache )
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def _log_activity (action :str ,detail :str =""):
    """Append an activity entry to the activity log."""
    _append_activity_entry ({
    "time":datetime .now ().strftime ("%Y-%m-%d %H:%M:%S"),
    "user":_current_username ,
    "role":_current_role ,
    "action":action ,
    "detail":detail ,
    })


def activity_log_gui (parent =None ,on_close_callback =None ):
    """Admin GUI to view all activity logs with filtering."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Activity Log")
    win .geometry ("850x600")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F4DC Activity Log",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,2 ))

    entries =_kv_load ("activity_log",[])
    if not isinstance (entries ,list ):
        entries =[]

    tk .Label (
    win ,text =f"{len (entries )} activity entries recorded",
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,5 ))


    filter_frame =tk .Frame (win ,bg ="#1a1a2e")
    filter_frame .pack (fill ="x",padx =15 ,pady =(0 ,5 ))

    tk .Label (filter_frame ,text ="Filter:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(0 ,5 ))

    filter_var =tk .StringVar ()
    filter_entry =tk .Entry (filter_frame ,textvariable =filter_var ,
    font =("Segoe UI",10 ),width =30 ,
    bg ="#0a0a1a",fg ="white",insertbackground ="white",
    relief ="flat")
    filter_entry .pack (side ="left",padx =(0 ,10 ))

    role_filter =tk .StringVar (value ="All")
    tk .Label (filter_frame ,text ="Role:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(0 ,5 ))
    role_combo =ttk .Combobox (filter_frame ,textvariable =role_filter ,
    values =["All","admin","user"],
    state ="readonly",width =8 )
    role_combo .pack (side ="left")


    cols =("Time","User","Role","Action","Detail")
    tree =ttk .Treeview (win ,columns =cols ,show ="headings",height =18 )
    tree .heading ("Time",text ="Time")
    tree .heading ("User",text ="User")
    tree .heading ("Role",text ="Role")
    tree .heading ("Action",text ="Action")
    tree .heading ("Detail",text ="Detail")
    tree .column ("Time",width =150 )
    tree .column ("User",width =100 )
    tree .column ("Role",width =60 ,anchor ="center")
    tree .column ("Action",width =160 )
    tree .column ("Detail",width =320 )

    scrollbar =ttk .Scrollbar (win ,orient ="vertical",command =tree .yview )
    tree .configure (yscrollcommand =scrollbar .set )

    tree .pack (side ="left",fill ="both",expand =True ,padx =(15 ,0 ),pady =(0 ,10 ))
    scrollbar .pack (side ="left",fill ="y",pady =(0 ,10 ),padx =(0 ,15 ))

    def _populate (entries_list ):
        for item in tree .get_children ():
            tree .delete (item )
        text_filter =filter_var .get ().lower ().strip ()
        role_f =role_filter .get ()
        for e in reversed (entries_list ):
            if role_f !="All"and e .get ("role","")!=role_f :
                continue 
            if text_filter :
                combined =f"{e .get ('user','')} {e .get ('action','')} {e .get ('detail','')}".lower ()
                if text_filter not in combined :
                    continue 
            tree .insert ("","end",values =(
            e .get ("time",""),
            e .get ("user",""),
            e .get ("role",""),
            e .get ("action",""),
            e .get ("detail",""),
            ))

    _populate (entries )

    def _apply_filter (*args ):
        _populate (entries )

    filter_var .trace_add ("write",_apply_filter )
    role_filter .trace_add ("write",_apply_filter )

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def _load_settings ()->dict :
    defaults ={
    "recognition_threshold":RECOGNITION_THRESHOLD ,
    "frame_scale":FRAME_SCALE ,
    "stability_window":STABILITY_WINDOW ,
    "iou_threshold":IOU_THRESHOLD ,
    "max_gone_frames":MAX_GONE_FRAMES ,
    "generated_image_size":512 ,
    "max_archive_samples":MAX_ARCHIVE_SAMPLES ,
    "load_archive":LOAD_ARCHIVE ,
    "theme":"dark",
    "webcam_index":0 ,
    }
    saved =_kv_load ("settings",{})
    if isinstance (saved ,dict ):
        defaults .update (saved )
    return defaults 


def _save_settings (settings :dict ):
    _kv_save ("settings",settings )


def _apply_settings_to_globals (settings :dict ):
    """Push settings values into global configuration variables."""
    global RECOGNITION_THRESHOLD ,FRAME_SCALE ,STABILITY_WINDOW 
    global IOU_THRESHOLD ,MAX_GONE_FRAMES ,MAX_ARCHIVE_SAMPLES ,LOAD_ARCHIVE 
    RECOGNITION_THRESHOLD =settings .get ("recognition_threshold",RECOGNITION_THRESHOLD )
    FRAME_SCALE =settings .get ("frame_scale",FRAME_SCALE )
    STABILITY_WINDOW =settings .get ("stability_window",STABILITY_WINDOW )
    IOU_THRESHOLD =settings .get ("iou_threshold",IOU_THRESHOLD )
    MAX_GONE_FRAMES =settings .get ("max_gone_frames",MAX_GONE_FRAMES )
    MAX_ARCHIVE_SAMPLES =settings .get ("max_archive_samples",MAX_ARCHIVE_SAMPLES )
    LOAD_ARCHIVE =settings .get ("load_archive",LOAD_ARCHIVE )


def settings_gui (parent =None ,on_close_callback =None ):
    """GUI to view and edit application settings."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Settings")
    win .geometry ("520x620")
    win .resizable (False ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\u2699\uFE0F  Settings",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,10 ))

    settings =_load_settings ()


    canvas =tk .Canvas (win ,bg ="#1a1a2e",highlightthickness =0 )
    sbar =ttk .Scrollbar (win ,orient ="vertical",command =canvas .yview )
    scroll_frame =tk .Frame (canvas ,bg ="#1a1a2e")

    scroll_frame .bind ("<Configure>",
    lambda e :canvas .configure (scrollregion =canvas .bbox ("all")))
    canvas .create_window ((0 ,0 ),window =scroll_frame ,anchor ="nw")
    canvas .configure (yscrollcommand =sbar .set )

    canvas .pack (side ="left",fill ="both",expand =True ,padx =15 )
    sbar .pack (side ="right",fill ="y")

    entries_map ={}

    def _add_setting (label ,key ,row ,var_type ="float"):
        tk .Label (scroll_frame ,text =label ,font =("Segoe UI",10 ),
        fg ="white",bg ="#1a1a2e",anchor ="w").grid (
        row =row ,column =0 ,padx =10 ,pady =6 ,sticky ="w")
        var =tk .StringVar (value =str (settings .get (key ,"")))
        ent =tk .Entry (scroll_frame ,textvariable =var ,font =("Segoe UI",10 ),
        width =14 ,bg ="#0a0a1a",fg ="white",insertbackground ="white",
        relief ="flat")
        ent .grid (row =row ,column =1 ,padx =10 ,pady =6 )
        entries_map [key ]=(var ,var_type )

    def _add_bool_setting (label ,key ,row ):
        var =tk .BooleanVar (value =bool (settings .get (key ,False )))
        tk .Checkbutton (scroll_frame ,text =label ,variable =var ,
        font =("Segoe UI",10 ),fg ="white",bg ="#1a1a2e",
        selectcolor ="#0a0a1a",activebackground ="#1a1a2e",
        activeforeground ="white").grid (
        row =row ,column =0 ,columnspan =2 ,padx =10 ,pady =6 ,sticky ="w")
        entries_map [key ]=(var ,"bool")


    tk .Label (scroll_frame ,text ="Recognition",font =("Segoe UI",12 ,"bold"),
    fg ="#e94560",bg ="#1a1a2e").grid (
    row =0 ,column =0 ,columnspan =2 ,padx =10 ,pady =(5 ,2 ),sticky ="w")

    _add_setting ("Cosine Similarity Threshold","recognition_threshold",1 )
    _add_setting ("Frame Scale (0.25–1.0)","frame_scale",2 )
    _add_setting ("Stability Window (frames)","stability_window",3 ,"int")
    _add_setting ("IoU Threshold","iou_threshold",4 )
    _add_setting ("Max Gone Frames","max_gone_frames",5 ,"int")


    tk .Label (scroll_frame ,text ="Generation",font =("Segoe UI",12 ,"bold"),
    fg ="#e94560",bg ="#1a1a2e").grid (
    row =6 ,column =0 ,columnspan =2 ,padx =10 ,pady =(15 ,2 ),sticky ="w")

    _add_setting ("Generated Image Size","generated_image_size",7 ,"int")


    tk .Label (scroll_frame ,text ="Archive",font =("Segoe UI",12 ,"bold"),
    fg ="#e94560",bg ="#1a1a2e").grid (
    row =8 ,column =0 ,columnspan =2 ,padx =10 ,pady =(15 ,2 ),sticky ="w")

    _add_setting ("Max Archive Samples","max_archive_samples",9 ,"int")
    _add_bool_setting ("Load Archive Dataset","load_archive",10 )


    tk .Label (scroll_frame ,text ="Webcam",font =("Segoe UI",12 ,"bold"),
    fg ="#e94560",bg ="#1a1a2e").grid (
    row =11 ,column =0 ,columnspan =2 ,padx =10 ,pady =(15 ,2 ),sticky ="w")

    _add_setting ("Webcam Index (0, 1, ...)","webcam_index",12 ,"int")


    def _save ():
        new_settings ={}
        for key ,(var ,vtype )in entries_map .items ():
            try :
                if vtype =="bool":
                    new_settings [key ]=var .get ()
                elif vtype =="int":
                    new_settings [key ]=int (var .get ())
                else :
                    new_settings [key ]=float (var .get ())
            except ValueError :
                messagebox .showerror ("Invalid",
                f"Invalid value for {key }",parent =win )
                return 
        _save_settings (new_settings )
        _apply_settings_to_globals (new_settings )
        _log_activity ("Settings Changed",str (new_settings ))
        messagebox .showinfo ("Saved","Settings saved and applied.",parent =win )

    def _reset ():
        _kv_save ("settings",{})
        messagebox .showinfo ("Reset","Settings reset to defaults.\n"
        "Restart the app to apply.",parent =win )

    btn_bar =tk .Frame (win ,bg ="#1a1a2e")
    btn_bar .pack (pady =10 )

    save_f =tk .Frame (btn_bar ,bg ="#0f3460",cursor ="hand2")
    save_f .pack (side ="left",padx =8 ,ipadx =16 ,ipady =5 )
    save_l =tk .Label (save_f ,text ="\U0001F4BE  Save Settings",
    font =("Segoe UI",11 ,"bold"),fg ="white",
    bg ="#0f3460",cursor ="hand2")
    save_l .pack ()
    for w in (save_f ,save_l ):
        w .bind ("<Button-1>",lambda e :_save ())

    reset_f =tk .Frame (btn_bar ,bg ="#e94560",cursor ="hand2")
    reset_f .pack (side ="left",padx =8 ,ipadx =16 ,ipady =5 )
    reset_l =tk .Label (reset_f ,text ="\U0001F504  Reset Defaults",
    font =("Segoe UI",11 ,"bold"),fg ="white",
    bg ="#e94560",cursor ="hand2")
    reset_l .pack ()
    for w in (reset_f ,reset_l ):
        w .bind ("<Button-1>",lambda e :_reset ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def user_profile_gui (parent =None ,on_close_callback =None ):
    """User profile page — view account info, change password, view login history."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("My Profile")
    win .geometry ("480x560")
    win .resizable (False ,False )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F464  My Profile",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(15 ,10 ))

    db =_load_users_db ()
    user_info =db .get (_current_username ,{})


    avatar_canvas =tk .Canvas (win ,width =80 ,height =80 ,bg ="#1a1a2e",
    highlightthickness =0 )
    avatar_canvas .pack (pady =(0 ,5 ))
    avatar_canvas .create_oval (5 ,5 ,75 ,75 ,fill ="#0f3460",outline ="#e94560",width =2 )
    initials =_current_username [:2 ].upper ()if _current_username else "?"
    avatar_canvas .create_text (40 ,40 ,text =initials ,fill ="white",
    font =("Segoe UI",22 ,"bold"))

    tk .Label (
    win ,text =_current_username ,
    font =("Segoe UI",16 ,"bold"),fg ="white",bg ="#1a1a2e"
    ).pack (pady =(2 ,0 ))

    role_txt =_current_role .capitalize ()
    role_col ="#e94560"if _current_role =="admin"else "#0f3460"
    tk .Label (
    win ,text =role_txt ,
    font =("Segoe UI",10 ,"bold"),fg =role_col ,bg ="#1a1a2e"
    ).pack (pady =(0 ,10 ))


    info_frame =tk .Frame (win ,bg ="#16213e")
    info_frame .pack (padx =30 ,fill ="x",ipady =8 )

    def _info_row (label ,value ,row ):
        tk .Label (info_frame ,text =label ,font =("Segoe UI",10 ),
        fg ="#a0a0b8",bg ="#16213e").grid (
        row =row ,column =0 ,padx =12 ,pady =4 ,sticky ="e")
        tk .Label (info_frame ,text =value ,font =("Segoe UI",10 ,"bold"),
        fg ="white",bg ="#16213e").grid (
        row =row ,column =1 ,padx =12 ,pady =4 ,sticky ="w")

    _info_row ("Account Created:",user_info .get ("created","Unknown"),0 )
    logins =user_info .get ("logins",[])
    _info_row ("Total Logins:",str (len (logins )),1 )
    _info_row ("Last Login:",logins [-1 ]if logins else "Never",2 )


    tk .Label (
    win ,text ="Recent Login History",
    font =("Segoe UI",11 ,"bold"),fg ="white",bg ="#1a1a2e"
    ).pack (pady =(15 ,5 ))

    history_frame =tk .Frame (win ,bg ="#16213e")
    history_frame .pack (padx =30 ,fill ="x",ipady =5 )

    recent =logins [-8 :]if logins else []
    if recent :
        for i ,ts in enumerate (reversed (recent )):
            tk .Label (history_frame ,text =f"  {i +1 }. {ts }",
            font =("Segoe UI",9 ),fg ="#a0a0b8",bg ="#16213e",
            anchor ="w").pack (anchor ="w",padx =10 ,pady =1 )
    else :
        tk .Label (history_frame ,text ="  No login history yet",
        font =("Segoe UI",9 ),fg ="#555",bg ="#16213e").pack (padx =10 ,pady =5 )


    tk .Label (
    win ,text ="Change Password",
    font =("Segoe UI",11 ,"bold"),fg ="white",bg ="#1a1a2e"
    ).pack (pady =(15 ,5 ))

    pw_frame =tk .Frame (win ,bg ="#16213e")
    pw_frame .pack (padx =30 ,fill ="x",ipady =8 )

    tk .Label (pw_frame ,text ="Current:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#16213e").grid (row =0 ,column =0 ,padx =8 ,pady =3 ,sticky ="e")
    old_pw =tk .Entry (pw_frame ,show ="\u2022",font =("Segoe UI",10 ),width =18 ,
    bg ="#0a0a1a",fg ="white",insertbackground ="white",relief ="flat")
    old_pw .grid (row =0 ,column =1 ,padx =8 ,pady =3 )

    tk .Label (pw_frame ,text ="New:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#16213e").grid (row =1 ,column =0 ,padx =8 ,pady =3 ,sticky ="e")
    new_pw =tk .Entry (pw_frame ,show ="\u2022",font =("Segoe UI",10 ),width =18 ,
    bg ="#0a0a1a",fg ="white",insertbackground ="white",relief ="flat")
    new_pw .grid (row =1 ,column =1 ,padx =8 ,pady =3 )

    pw_msg =tk .StringVar (value ="")
    tk .Label (pw_frame ,textvariable =pw_msg ,font =("Segoe UI",9 ),
    fg ="#e94560",bg ="#16213e").grid (row =2 ,column =0 ,columnspan =2 ,pady =2 )

    def _change_pw ():
        old =old_pw .get ()
        new =new_pw .get ()
        db2 =_load_users_db ()
        uinfo =db2 .get (_current_username ,{})
        stored =str (uinfo .get ("password",""))
        if len (stored )==64 :
            valid_current =_verify_password (old ,stored )
        else :
            valid_current =(stored ==old )
        if not valid_current :
            pw_msg .set ("Current password incorrect")
            return 
        if len (new )<4 :
            pw_msg .set ("New password must be at least 4 characters")
            return 
        db2 [_current_username ]["password"]=_hash_password (new )
        _save_users_db (db2 )
        _log_activity ("Password Changed",_current_username )
        pw_msg .set ("")
        old_pw .delete (0 ,"end")
        new_pw .delete (0 ,"end")
        messagebox .showinfo ("Success","Password changed!",parent =win )

    change_f =tk .Frame (pw_frame ,bg ="#0f3460",cursor ="hand2")
    change_f .grid (row =3 ,column =0 ,columnspan =2 ,pady =8 )
    change_l =tk .Label (change_f ,text ="  Update Password  ",
    font =("Segoe UI",10 ,"bold"),fg ="white",
    bg ="#0f3460",cursor ="hand2")
    change_l .pack (ipadx =10 ,ipady =3 )
    for w in (change_f ,change_l ):
        w .bind ("<Button-1>",lambda e :_change_pw ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def help_about_gui (parent =None ,on_close_callback =None ):
    """Help and About page with documentation and credits."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Help & About")
    win .geometry ("580x650")
    win .resizable (False ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\u2753  Help & About",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(15 ,5 ))


    text_frame =tk .Frame (win ,bg ="#16213e")
    text_frame .pack (fill ="both",expand =True ,padx =20 ,pady =10 )

    text_widget =tk .Text (text_frame ,bg ="#16213e",fg ="white",
    font =("Segoe UI",10 ),wrap ="word",
    relief ="flat",highlightthickness =0 ,
    padx =15 ,pady =10 )
    text_scroll =ttk .Scrollbar (text_frame ,orient ="vertical",
    command =text_widget .yview )
    text_widget .configure (yscrollcommand =text_scroll .set )
    text_widget .pack (side ="left",fill ="both",expand =True )
    text_scroll .pack (side ="right",fill ="y")

    help_text ="""
\U0001F9D1 FACE STUDIO — Help & Documentation
========================================

OVERVIEW
--------
Face Studio is a comprehensive face recognition and management application
built with Python, OpenCV (YuNet + SFace), and Tkinter.

FEATURES FOR ALL USERS:
• Face Recognition — Real-time webcam face identification
• Face Generation — Create stylized images (Sketch, Cartoon, Ghibli, etc.)
• Face Comparison — Compare two images for similarity
• Batch Processing — Process multiple images at once
• Image Enhancement — Improve photo quality with various tools
• Face Search — Find a person across all stored images
• User Profile — View account info, change password

KEYBOARD SHORTCUTS:
• ESC — Return to home page (from webcam modes)
• Q — Save and quit attendance mode
• S — Take screenshot (during webcam recognition)

RECOGNITION ENGINE:
• Detection: OpenCV YuNet (ONNX) — ~33ms per frame
• Encoding: OpenCV SFace (ONNX) — ~48ms per face
• Matching: Cosine Similarity (threshold: 0.363)
• Tracking: IoU-based FaceTracker with exponential smoothing

ARTISTIC FILTERS (16):
Sketch, Cartoon, Oil Painting, HDR, Ghibli Art, Anime, Ghost,
Emboss, Watercolor, Pop Art, Neon Glow, Vintage, Pixel Art,
Thermal, Glitch, Pencil Color

REQUIREMENTS:
pip install opencv-python opencv-contrib-python numpy pillow
s
CREDITS:
• OpenCV Team — YuNet & SFace models
• Python / Tkinter — GUI framework
• NumPy — Numerical computing

For more information please contact facestudio4@gmail.com

VERSION: 2.0 | Built with Python
"""
    text_widget .insert ("1.0",help_text )
    text_widget .config (state ="disabled")


    info_frame =tk .Frame (win ,bg ="#1a1a2e")
    info_frame .pack (fill ="x",padx =20 ,pady =(0 ,5 ))

    people_count =len ([e for e in os .listdir (FACES_ROOT )
    if _is_person_folder (e ,os .path .join (BASE_DIR ,e ))])
    db =_load_users_db ()
    if _current_role =="admin":
        sys_text =(f"Python {sys .version .split ()[0 ]} | "
        f"OpenCV {cv2 .__version__ } | "
        f"{people_count } registered faces | "
        f"{len (db )} user accounts")
    else :
        sys_text =(f"Python {sys .version .split ()[0 ]} | "
        f"OpenCV {cv2 .__version__ } | User Mode")
    tk .Label (info_frame ,text =sys_text ,font =("Segoe UI",9 ),
    fg ="#a0a0b8",bg ="#1a1a2e").pack ()

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def face_search_gui (parent =None ,on_close_callback =None ):
    """Search for a person by uploading their photo, find matches in database."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Face Search")
    win .geometry ("700x620")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F50D  Face Search",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,2 ))

    tk .Label (
    win ,text ="Upload a face photo — find matching people in the database",
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,10 ))


    preview_frame =tk .Frame (win ,bg ="#16213e",width =180 ,height =180 )
    preview_frame .pack (pady =(0 ,5 ))
    preview_frame .pack_propagate (False )
    preview_label =tk .Label (preview_frame ,text ="Click to upload\na face photo",
    font =("Segoe UI",10 ),fg ="#777",bg ="#16213e")
    preview_label .pack (expand =True )

    _state ={"embedding":None ,"searching":False }


    result_frame =tk .Frame (win ,bg ="#1a1a2e")
    result_frame .pack (fill ="both",expand =True ,padx =15 ,pady =(5 ,10 ))

    result_label =tk .Label (result_frame ,text ="",
    font =("Segoe UI",11 ,"bold"),
    fg ="white",bg ="#1a1a2e")
    result_label .pack (pady =(5 ,5 ))


    cols =("Name","Similarity","Match")
    result_tree =ttk .Treeview (result_frame ,columns =cols ,show ="headings",height =10 )
    result_tree .heading ("Name",text ="Person Name")
    result_tree .heading ("Similarity",text ="Similarity Score")
    result_tree .heading ("Match",text ="Status")
    result_tree .column ("Name",width =200 )
    result_tree .column ("Similarity",width =150 ,anchor ="center")
    result_tree .column ("Match",width =120 ,anchor ="center")
    result_tree .pack (fill ="both",expand =True )


    thumb_frame =tk .Frame (result_frame ,bg ="#1a1a2e")
    thumb_frame .pack (fill ="x",pady =(5 ,0 ))
    _thumb_refs =[]

    def _search ():
        if _state ["embedding"]is None :
            return 

        for item in result_tree .get_children ():
            result_tree .delete (item )
        for w in thumb_frame .winfo_children ():
            w .destroy ()
        _thumb_refs .clear ()

        query_emb =_state ["embedding"]


        known =load_and_train ()
        if not known :
            result_label .config (text ="No faces in database to search against.")
            return 

        results =[]
        for name ,encs in known .items ():
            best_score =0.0 
            for enc in encs :
                score =_sface_recognizer .match (
                query_emb .reshape (1 ,-1 ),enc .reshape (1 ,-1 ),
                cv2 .FaceRecognizerSF_FR_COSINE ,
                )
                if score >best_score :
                    best_score =score 
            results .append ((name ,best_score ))

        results .sort (key =lambda x :x [1 ],reverse =True )
        matches =[r for r in results if r [1 ]>=RECOGNITION_THRESHOLD ]

        result_label .config (
        text =f"Found {len (matches )} match(es) out of {len (results )} people"
        )

        for name ,score in results [:15 ]:
            pct =max (0 ,score )*100 
            status ="\u2705 Match"if score >=RECOGNITION_THRESHOLD else "\u274C No Match"
            result_tree .insert ("","end",values =(
            name ,f"{pct :.1f}%",status 
            ))


        from PIL import Image ,ImageTk 
        count =0 
        for name ,score in matches [:6 ]:
            folder =os .path .join (FACES_ROOT ,name )
            if not os .path .isdir (folder ):
                continue 
            imgs =[f for f in os .listdir (folder )
            if os .path .splitext (f )[1 ].lower ()in IMAGE_EXTENSIONS ]
            if not imgs :
                continue 
            img =cv2 .imread (os .path .join (folder ,imgs [0 ]))
            if img is None :
                continue 
            rgb =cv2 .cvtColor (img ,cv2 .COLOR_BGR2RGB )
            pil =Image .fromarray (rgb ).resize ((70 ,70 ),Image .LANCZOS )
            tk_img =ImageTk .PhotoImage (pil )
            _thumb_refs .append (tk_img )
            col_frame =tk .Frame (thumb_frame ,bg ="#1a1a2e")
            col_frame .pack (side ="left",padx =5 )
            tk .Label (col_frame ,image =tk_img ,bg ="#1a1a2e").pack ()
            tk .Label (col_frame ,text =name ,font =("Segoe UI",8 ),
            fg ="#ccc",bg ="#1a1a2e").pack ()
            count +=1 

    def _upload (event =None ):
        path =filedialog .askopenfilename (
        filetypes =[("Images","*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if not path :
            return 
        img =cv2 .imread (path )
        if img is None :
            return 

        emb =compute_embedding (img )
        if emb is None :
            result_label .config (text ="No face detected in that image.")
            return 

        _state ["embedding"]=emb 

        from PIL import Image ,ImageTk 
        rgb =cv2 .cvtColor (img ,cv2 .COLOR_BGR2RGB )
        pil =Image .fromarray (rgb ).resize ((170 ,170 ),Image .LANCZOS )
        tk_img =ImageTk .PhotoImage (pil )
        preview_label .config (image =tk_img ,text ="")
        preview_label .image =tk_img 

        _log_activity ("Face Search",f"Searched face from {os .path .basename (path )}")
        _search ()

    for w in (preview_frame ,preview_label ):
        w .bind ("<Button-1>",_upload )
        w .config (cursor ="hand2")


    def _webcam_search ():
        img =_capture_from_webcam ()
        if img is None :
            return 
        emb =compute_embedding (img )
        if emb is None :
            result_label .config (text ="No face detected in webcam capture.")
            return 
        _state ["embedding"]=emb 
        from PIL import Image ,ImageTk 
        rgb =cv2 .cvtColor (img ,cv2 .COLOR_BGR2RGB )
        pil =Image .fromarray (rgb ).resize ((170 ,170 ),Image .LANCZOS )
        tk_img =ImageTk .PhotoImage (pil )
        preview_label .config (image =tk_img ,text ="")
        preview_label .image =tk_img 
        _log_activity ("Face Search","Searched face from webcam")
        _search ()

    cam_f =tk .Frame (win ,bg ="#0f3460",cursor ="hand2")
    cam_f .pack (pady =(5 ,0 ),ipadx =14 ,ipady =5 )
    cam_l =tk .Label (cam_f ,text ="\U0001F4F7  Capture from Webcam",
    font =("Segoe UI",10 ,"bold"),fg ="white",
    bg ="#0f3460",cursor ="hand2")
    cam_l .pack ()
    for w in (cam_f ,cam_l ):
        w .bind ("<Button-1>",lambda e :_webcam_search ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def batch_processing_gui (parent =None ,on_close_callback =None ):
    """Process multiple images at once: apply filters, recognize faces, export."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Batch Processing")
    win .geometry ("700x600")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F4E6  Batch Processing",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,2 ))

    tk .Label (
    win ,text ="Process multiple images — apply filters or recognize faces in bulk",
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,10 ))

    _file_list =[]


    list_frame =tk .Frame (win ,bg ="#1a1a2e")
    list_frame .pack (fill ="both",expand =True ,padx =15 ,pady =(0 ,5 ))

    listbox =tk .Listbox (list_frame ,bg ="#16213e",fg ="white",
    font =("Segoe UI",10 ),selectbackground ="#0f3460",
    selectforeground ="white",highlightthickness =0 ,
    relief ="flat")
    listbox .pack (side ="left",fill ="both",expand =True )
    list_scroll =ttk .Scrollbar (list_frame ,orient ="vertical",
    command =listbox .yview )
    listbox .configure (yscrollcommand =list_scroll .set )
    list_scroll .pack (side ="right",fill ="y")

    file_count_var =tk .StringVar (value ="No files selected")
    tk .Label (win ,textvariable =file_count_var ,font =("Segoe UI",9 ),
    fg ="#a0a0b8",bg ="#1a1a2e").pack (pady =(0 ,5 ))


    ctrl_frame =tk .Frame (win ,bg ="#1a1a2e")
    ctrl_frame .pack (fill ="x",padx =15 ,pady =(0 ,5 ))

    def _add_files ():
        paths =filedialog .askopenfilenames (
        filetypes =[("Images","*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        for p in paths :
            if p not in _file_list :
                _file_list .append (p )
                listbox .insert ("end",f"  {os .path .basename (p )}")
        file_count_var .set (f"{len (_file_list )} file(s) selected")

    def _clear_files ():
        _file_list .clear ()
        listbox .delete (0 ,"end")
        file_count_var .set ("No files selected")

    add_f =tk .Frame (ctrl_frame ,bg ="#0f3460",cursor ="hand2")
    add_f .pack (side ="left",padx =5 ,ipadx =12 ,ipady =4 )
    add_l =tk .Label (add_f ,text ="\U0001F4C2 Add Files",
    font =("Segoe UI",10 ,"bold"),fg ="white",
    bg ="#0f3460",cursor ="hand2")
    add_l .pack ()
    for w in (add_f ,add_l ):
        w .bind ("<Button-1>",lambda e :_add_files ())

    clear_f =tk .Frame (ctrl_frame ,bg ="#e94560",cursor ="hand2")
    clear_f .pack (side ="left",padx =5 ,ipadx =12 ,ipady =4 )
    clear_l =tk .Label (clear_f ,text ="\U0001F5D1 Clear",
    font =("Segoe UI",10 ,"bold"),fg ="white",
    bg ="#e94560",cursor ="hand2")
    clear_l .pack ()
    for w in (clear_f ,clear_l ):
        w .bind ("<Button-1>",lambda e :_clear_files ())


    op_frame =tk .Frame (win ,bg ="#1a1a2e")
    op_frame .pack (fill ="x",padx =15 ,pady =(5 ,0 ))

    tk .Label (op_frame ,text ="Operation:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(0 ,8 ))

    op_var =tk .StringVar (value ="Recognize Faces")
    ops =["Recognize Faces","Apply Sketch Filter","Apply Cartoon Filter",
    "Apply Oil Painting","Apply HDR","Apply Ghibli Art",
    "Apply Anime","Apply Watercolor","Apply Pop Art",
    "Apply Neon Glow","Apply Vintage","Apply Pixel Art",
    "Apply Thermal","Apply Glitch","Apply Pencil Color",
    "Detect Faces Only"]
    op_combo =ttk .Combobox (op_frame ,textvariable =op_var ,values =ops ,
    state ="readonly",width =25 )
    op_combo .pack (side ="left")


    progress_var =tk .DoubleVar (value =0 )
    progress_bar =ttk .Progressbar (win ,variable =progress_var ,maximum =100 ,
    length =600 )
    progress_bar .pack (padx =15 ,pady =(8 ,3 ))

    status_var =tk .StringVar (value ="Ready")
    tk .Label (win ,textvariable =status_var ,font =("Segoe UI",9 ),
    fg ="#a0a0b8",bg ="#1a1a2e").pack (pady =(0 ,5 ))

    def _process ():
        if not _file_list :
            messagebox .showwarning ("No Files","Add files first.",parent =win )
            return 

        output_dir =filedialog .askdirectory (title ="Select output folder")
        if not output_dir :
            return 

        operation =op_var .get ()
        total =len (_file_list )
        success =0 
        known =None 

        if operation =="Recognize Faces":
            known =load_and_train ()

        for i ,path in enumerate (_file_list ):
            try :
                img =cv2 .imread (path )
                if img is None :
                    continue 

                basename =os .path .splitext (os .path .basename (path ))[0 ]

                if operation =="Recognize Faces":
                    if known is None :
                        continue 
                    known_names =[]
                    known_encs =[]
                    for name ,encs in known .items ():
                        for enc in encs :
                            known_names .append (name )
                            known_encs .append (enc )
                    known_arr =np .array (known_encs )if known_encs else np .empty ((0 ,128 ))

                    h ,w =img .shape [:2 ]
                    yunet =_create_yunet (w ,h )
                    results =detect_and_encode (img ,yunet )
                    for (fx ,fy ,fw ,fh ,emb )in results :
                        name ,score =match_embedding (emb ,known_names ,known_arr )
                        color =(0 ,220 ,0 )if name !="Unknown"else (0 ,0 ,255 )
                        cv2 .rectangle (img ,(fx ,fy ),(fx +fw ,fy +fh ),color ,2 )
                        cv2 .putText (img ,f"{name } ({score :.2f})",
                        (fx ,fy -10 ),cv2 .FONT_HERSHEY_SIMPLEX ,
                        0.6 ,color ,2 ,cv2 .LINE_AA )

                    out_path =os .path .join (output_dir ,f"{basename }_recognized.jpg")
                    cv2 .imwrite (out_path ,img )

                elif operation =="Detect Faces Only":
                    h ,w =img .shape [:2 ]
                    yunet =_create_yunet (w ,h )
                    _ ,faces =yunet .detect (img )
                    if faces is not None :
                        for face in faces :
                            x ,y ,fw ,fh =face [:4 ].astype (int )
                            cv2 .rectangle (img ,(x ,y ),(x +fw ,y +fh ),
                            (0 ,255 ,0 ),2 )
                    out_path =os .path .join (output_dir ,f"{basename }_detected.jpg")
                    cv2 .imwrite (out_path ,img )

                else :

                    filter_name =operation .replace ("Apply ","")
                    filtered =apply_face_filter (img .copy (),filter_name )
                    safe_name =filter_name .lower ().replace (" ","_")
                    out_path =os .path .join (output_dir ,f"{basename }_{safe_name }.jpg")
                    cv2 .imwrite (out_path ,filtered )

                success +=1 

            except Exception as exc :
                print (f"[BATCH] Error processing {path }: {exc }")

            pct =((i +1 )/total )*100 
            progress_var .set (pct )
            status_var .set (f"Processing {i +1 }/{total }...")
            win .update_idletasks ()

        status_var .set (f"Done! {success }/{total } processed successfully")
        progress_var .set (100 )
        _log_activity ("Batch Processing",
        f"{operation }: {success }/{total } files to {output_dir }")
        messagebox .showinfo ("Batch Complete",
        f"Processed {success }/{total } images.\n"
        f"Output: {output_dir }",parent =win )

    proc_f =tk .Frame (win ,bg ="#533483",cursor ="hand2")
    proc_f .pack (pady =(5 ,10 ),ipadx =20 ,ipady =6 )
    proc_l =tk .Label (proc_f ,text ="\u25B6  Start Processing",
    font =("Segoe UI",12 ,"bold"),fg ="white",
    bg ="#533483",cursor ="hand2")
    proc_l .pack ()
    for w in (proc_f ,proc_l ):
        w .bind ("<Button-1>",lambda e :_process ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def image_enhance_gui (parent =None ,on_close_callback =None ):
    """Image enhancement tool — adjust brightness, contrast, sharpen, etc."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Image Enhancement")
    win .geometry ("750x640")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F4F8  Image Enhancement",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(10 ,5 ))

    _state ={"original":None ,"current":None }
    _img_refs =[]


    preview_canvas =tk .Canvas (win ,width =400 ,height =320 ,bg ="#16213e",
    highlightthickness =0 )
    preview_canvas .pack (pady =(5 ,5 ))

    def _update_preview ():
        if _state ["current"]is None :
            return 
        from PIL import Image ,ImageTk 
        img =_state ["current"]
        rgb =cv2 .cvtColor (img ,cv2 .COLOR_BGR2RGB )
        h ,w =rgb .shape [:2 ]
        scale =min (400 /w ,320 /h )
        new_w ,new_h =int (w *scale ),int (h *scale )
        pil =Image .fromarray (rgb ).resize ((new_w ,new_h ),Image .LANCZOS )
        tk_img =ImageTk .PhotoImage (pil )
        _img_refs .clear ()
        _img_refs .append (tk_img )
        preview_canvas .delete ("all")
        preview_canvas .create_image (200 ,160 ,image =tk_img )


    sliders_frame =tk .Frame (win ,bg ="#1a1a2e")
    sliders_frame .pack (fill ="x",padx =20 ,pady =(5 ,0 ))

    brightness_var =tk .IntVar (value =0 )
    contrast_var =tk .IntVar (value =100 )
    sharpen_var =tk .IntVar (value =0 )
    denoise_var =tk .IntVar (value =0 )
    saturation_var =tk .IntVar (value =100 )
    rotation_var =tk .IntVar (value =0 )

    def _make_slider (label ,var ,from_ ,to ,row ):
        tk .Label (sliders_frame ,text =label ,font =("Segoe UI",9 ),
        fg ="#ccc",bg ="#1a1a2e",width =12 ,anchor ="w").grid (
        row =row ,column =0 ,padx =5 ,pady =2 )
        s =tk .Scale (sliders_frame ,from_ =from_ ,to =to ,variable =var ,
        orient ="horizontal",length =250 ,bg ="#1a1a2e",
        fg ="white",troughcolor ="#16213e",highlightthickness =0 ,
        sliderrelief ="flat",command =lambda v :_apply_adjustments ())
        s .grid (row =row ,column =1 ,padx =5 ,pady =2 )
        val_lbl =tk .Label (sliders_frame ,textvariable =var ,
        font =("Segoe UI",9 ),fg ="#e94560",
        bg ="#1a1a2e",width =5 )
        val_lbl .grid (row =row ,column =2 ,padx =5 ,pady =2 )

    _make_slider ("Brightness",brightness_var ,-100 ,100 ,0 )
    _make_slider ("Contrast %",contrast_var ,10 ,300 ,1 )
    _make_slider ("Sharpen",sharpen_var ,0 ,10 ,2 )
    _make_slider ("Denoise",denoise_var ,0 ,30 ,3 )
    _make_slider ("Saturation %",saturation_var ,0 ,300 ,4 )
    _make_slider ("Rotation °",rotation_var ,-180 ,180 ,5 )

    def _apply_adjustments ():
        if _state ["original"]is None :
            return 
        img =_state ["original"].copy ()


        b =brightness_var .get ()
        if b !=0 :
            img =cv2 .convertScaleAbs (img ,alpha =1.0 ,beta =b )


        c =contrast_var .get ()/100.0 
        if c !=1.0 :
            img =cv2 .convertScaleAbs (img ,alpha =c ,beta =0 )


        sat =saturation_var .get ()/100.0 
        if sat !=1.0 :
            hsv =cv2 .cvtColor (img ,cv2 .COLOR_BGR2HSV ).astype (np .float32 )
            hsv [:,:,1 ]=np .clip (hsv [:,:,1 ]*sat ,0 ,255 )
            img =cv2 .cvtColor (hsv .astype (np .uint8 ),cv2 .COLOR_HSV2BGR )


        sh =sharpen_var .get ()
        if sh >0 :
            kernel =np .array ([[-1 ,-1 ,-1 ],
            [-1 ,9 +sh ,-1 ],
            [-1 ,-1 ,-1 ]],dtype =np .float32 )
            kernel /=kernel .sum ()if kernel .sum ()!=0 else 1 
            img =cv2 .filter2D (img ,-1 ,kernel )


        dn =denoise_var .get ()
        if dn >0 :
            img =cv2 .fastNlMeansDenoisingColored (img ,None ,dn ,dn ,7 ,21 )


        rot =rotation_var .get ()
        if rot !=0 :
            h ,w =img .shape [:2 ]
            center =(w //2 ,h //2 )
            M =cv2 .getRotationMatrix2D (center ,rot ,1.0 )
            img =cv2 .warpAffine (img ,M ,(w ,h ),
            borderMode =cv2 .BORDER_REFLECT )

        _state ["current"]=img 
        _update_preview ()


    btn_row =tk .Frame (win ,bg ="#1a1a2e")
    btn_row .pack (pady =(8 ,8 ))

    def _load_image ():
        path =filedialog .askopenfilename (
        filetypes =[("Images","*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if not path :
            return 
        img =cv2 .imread (path )
        if img is None :
            return 
        _state ["original"]=img 
        _state ["current"]=img .copy ()
        brightness_var .set (0 )
        contrast_var .set (100 )
        sharpen_var .set (0 )
        denoise_var .set (0 )
        saturation_var .set (100 )
        rotation_var .set (0 )
        _update_preview ()

    def _save_image ():
        if _state ["current"]is None :
            return 
        path =filedialog .asksaveasfilename (
        defaultextension =".jpg",
        filetypes =[("JPEG","*.jpg"),("PNG","*.png"),("BMP","*.bmp")],
        )
        if path :
            cv2 .imwrite (path ,_state ["current"])
            _log_activity ("Image Enhancement",f"Saved to {os .path .basename (path )}")
            messagebox .showinfo ("Saved",f"Image saved: {path }",parent =win )

    def _reset ():
        if _state ["original"]is not None :
            _state ["current"]=_state ["original"].copy ()
            brightness_var .set (0 )
            contrast_var .set (100 )
            sharpen_var .set (0 )
            denoise_var .set (0 )
            saturation_var .set (100 )
            rotation_var .set (0 )
            _update_preview ()

    def _auto_enhance ():
        if _state ["original"]is None :
            return 
        img =_state ["original"].copy ()

        lab =cv2 .cvtColor (img ,cv2 .COLOR_BGR2LAB )
        clahe =cv2 .createCLAHE (clipLimit =2.0 ,tileGridSize =(8 ,8 ))
        lab [:,:,0 ]=clahe .apply (lab [:,:,0 ])
        img =cv2 .cvtColor (lab ,cv2 .COLOR_LAB2BGR )

        kernel =np .array ([[0 ,-0.5 ,0 ],[-0.5 ,3 ,-0.5 ],[0 ,-0.5 ,0 ]])
        img =cv2 .filter2D (img ,-1 ,kernel )
        _state ["current"]=img 
        _update_preview ()

    for text ,color ,cmd in [
    ("\U0001F4C2 Load","#0f3460",_load_image ),
    ("\U0001F4BE Save","#0e6655",_save_image ),
    ("\U0001F504 Reset","#e94560",_reset ),
    ("\u2728 Auto Enhance","#533483",_auto_enhance ),
    ]:
        bf =tk .Frame (btn_row ,bg =color ,cursor ="hand2")
        bf .pack (side ="left",padx =5 ,ipadx =10 ,ipady =4 )
        bl =tk .Label (bf ,text =text ,font =("Segoe UI",10 ,"bold"),
        fg ="white",bg =color ,cursor ="hand2")
        bl .pack ()
        for w in (bf ,bl ):
            w .bind ("<Button-1>",lambda e ,c =cmd :c ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def group_photo_gui (parent =None ,on_close_callback =None ):
    """Detect and identify all faces in a group photo, show annotated result."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Group Photo Analysis")
    win .geometry ("800x700")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F46A  Group Photo Analysis",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(10 ,2 ))

    tk .Label (
    win ,text ="Upload a group photo — detect and identify all faces",
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,8 ))

    _state ={"annotated":None }
    _img_refs =[]


    preview_canvas =tk .Canvas (win ,width =740 ,height =440 ,bg ="#16213e",
    highlightthickness =0 )
    preview_canvas .pack (padx =20 ,pady =(0 ,5 ))


    info_var =tk .StringVar (value ="Load a group photo to start")
    tk .Label (win ,textvariable =info_var ,font =("Segoe UI",11 ,"bold"),
    fg ="white",bg ="#1a1a2e").pack (pady =(5 ,2 ))

    detail_var =tk .StringVar (value ="")
    tk .Label (win ,textvariable =detail_var ,font =("Segoe UI",9 ),
    fg ="#a0a0b8",bg ="#1a1a2e",wraplength =700 ).pack (pady =(0 ,5 ))


    result_frame =tk .Frame (win ,bg ="#1a1a2e")
    result_frame .pack (fill ="both",expand =True ,padx =20 ,pady =(0 ,5 ))

    cols =("Face #","Name","Similarity","Position")
    result_tree =ttk .Treeview (result_frame ,columns =cols ,show ="headings",
    height =6 )
    result_tree .heading ("Face #",text ="#")
    result_tree .heading ("Name",text ="Name")
    result_tree .heading ("Similarity",text ="Score")
    result_tree .heading ("Position",text ="Position (x, y, w, h)")
    result_tree .column ("Face #",width =50 ,anchor ="center")
    result_tree .column ("Name",width =180 )
    result_tree .column ("Similarity",width =100 ,anchor ="center")
    result_tree .column ("Position",width =200 ,anchor ="center")
    result_tree .pack (fill ="both",expand =True )

    def _analyze (path ):
        img =cv2 .imread (path )
        if img is None :
            info_var .set ("Failed to load image.")
            return 

        known =load_and_train ()
        known_names =[]
        known_encs =[]
        if known :
            for name ,encs in known .items ():
                for enc in encs :
                    known_names .append (name )
                    known_encs .append (enc )
        known_arr =np .array (known_encs )if known_encs else np .empty ((0 ,128 ))

        h ,w =img .shape [:2 ]
        yunet =_create_yunet (w ,h )
        results =detect_and_encode (img ,yunet )

        annotated =img .copy ()
        face_data =[]

        for i ,(fx ,fy ,fw ,fh ,emb )in enumerate (results ):
            name ,score =match_embedding (emb ,known_names ,known_arr )
            pct =max (0 ,score )*100 
            color =(0 ,220 ,0 )if name !="Unknown"else (0 ,140 ,255 )
            cv2 .rectangle (annotated ,(fx ,fy ),(fx +fw ,fy +fh ),color ,2 )

            label =f"{name } ({pct :.0f}%)"
            label_size =cv2 .getTextSize (label ,cv2 .FONT_HERSHEY_SIMPLEX ,
            0.5 ,1 )[0 ]
            cv2 .rectangle (annotated ,(fx ,fy -label_size [1 ]-8 ),
            (fx +label_size [0 ]+4 ,fy ),color ,-1 )
            cv2 .putText (annotated ,label ,(fx +2 ,fy -5 ),
            cv2 .FONT_HERSHEY_SIMPLEX ,0.5 ,(255 ,255 ,255 ),
            1 ,cv2 .LINE_AA )


            cv2 .circle (annotated ,(fx +fw ,fy ),14 ,(30 ,30 ,30 ),-1 )
            cv2 .putText (annotated ,str (i +1 ),(fx +fw -7 ,fy +5 ),
            cv2 .FONT_HERSHEY_SIMPLEX ,0.45 ,(255 ,255 ,255 ),
            1 ,cv2 .LINE_AA )

            face_data .append ({
            "num":i +1 ,
            "name":name ,
            "score":pct ,
            "pos":f"({fx }, {fy }, {fw }, {fh })",
            })

        _state ["annotated"]=annotated 


        from PIL import Image ,ImageTk 
        rgb =cv2 .cvtColor (annotated ,cv2 .COLOR_BGR2RGB )
        scale =min (740 /w ,440 /h )
        new_w ,new_h =int (w *scale ),int (h *scale )
        pil =Image .fromarray (rgb ).resize ((new_w ,new_h ),Image .LANCZOS )
        tk_img =ImageTk .PhotoImage (pil )
        _img_refs .clear ()
        _img_refs .append (tk_img )
        preview_canvas .delete ("all")
        preview_canvas .create_image (370 ,220 ,image =tk_img )

        recognized =[f for f in face_data if f ["name"]!="Unknown"]
        info_var .set (f"Detected {len (face_data )} face(s) — "
        f"{len (recognized )} identified")

        names_list =[f ["name"]for f in face_data if f ["name"]!="Unknown"]
        if names_list :
            detail_var .set ("People found: "+", ".join (set (names_list )))
        else :
            detail_var .set ("No recognized faces in this photo.")

        for item in result_tree .get_children ():
            result_tree .delete (item )
        for f in face_data :
            result_tree .insert ("","end",values =(
            f ["num"],f ["name"],f"{f ['score']:.1f}%",f ["pos"]
            ))

        _log_activity ("Group Photo Analysis",
        f"{len (face_data )} faces, {len (recognized )} identified")


    btn_row =tk .Frame (win ,bg ="#1a1a2e")
    btn_row .pack (pady =(5 ,8 ))

    def _load ():
        path =filedialog .askopenfilename (
        filetypes =[("Images","*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if path :
            _analyze (path )

    def _save ():
        if _state ["annotated"]is None :
            return 
        path =filedialog .asksaveasfilename (
        defaultextension =".jpg",
        filetypes =[("JPEG","*.jpg"),("PNG","*.png")],
        initialfile ="group_annotated.jpg",
        )
        if path :
            cv2 .imwrite (path ,_state ["annotated"])
            messagebox .showinfo ("Saved",f"Saved: {path }",parent =win )

    for text ,color ,cmd in [
    ("\U0001F4C2  Load Group Photo","#0f3460",_load ),
    ("\U0001F4BE  Save Annotated","#0e6655",_save ),
    ]:
        bf =tk .Frame (btn_row ,bg =color ,cursor ="hand2")
        bf .pack (side ="left",padx =8 ,ipadx =14 ,ipady =5 )
        bl =tk .Label (bf ,text =text ,font =("Segoe UI",11 ,"bold"),
        fg ="white",bg =color ,cursor ="hand2")
        bl .pack ()
        for w in (bf ,bl ):
            w .bind ("<Button-1>",lambda e ,c =cmd :c ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def face_collage_gui (parent =None ,on_close_callback =None ):
    """Create a collage of a person's photos from the database."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Face Collage Maker")
    win .geometry ("650x580")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F5BC  Face Collage Maker",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,5 ))


    people =[]
    for entry in sorted (os .listdir (FACES_ROOT )):
        folder =os .path .join (FACES_ROOT ,entry )
        if _is_person_folder (entry ,folder ):
            imgs =[f for f in os .listdir (folder )
            if os .path .splitext (f )[1 ].lower ()in IMAGE_EXTENSIONS ]
            if imgs :
                people .append ({"name":entry ,"folder":folder ,"images":imgs })

    tk .Label (
    win ,text =f"Select a person ({len (people )} available)",
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,5 ))


    sel_frame =tk .Frame (win ,bg ="#1a1a2e")
    sel_frame .pack (fill ="x",padx =20 ,pady =(0 ,5 ))

    tk .Label (sel_frame ,text ="Person:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(0 ,8 ))

    person_names =[p ["name"]for p in people ]
    person_var =tk .StringVar (value =person_names [0 ]if person_names else "")
    person_combo =ttk .Combobox (sel_frame ,textvariable =person_var ,
    values =person_names ,state ="readonly",width =20 )
    person_combo .pack (side ="left")

    tk .Label (sel_frame ,text ="Grid:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(15 ,5 ))

    grid_var =tk .StringVar (value ="3x3")
    grid_combo =ttk .Combobox (sel_frame ,textvariable =grid_var ,
    values =["2x2","3x3","4x4","2x3","3x2"],
    state ="readonly",width =6 )
    grid_combo .pack (side ="left")

    tk .Label (sel_frame ,text ="Size:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(15 ,5 ))

    size_var =tk .StringVar (value ="150")
    size_combo =ttk .Combobox (sel_frame ,textvariable =size_var ,
    values =["100","150","200","250"],
    state ="readonly",width =5 )
    size_combo .pack (side ="left")


    _img_refs =[]
    preview_canvas =tk .Canvas (win ,width =600 ,height =380 ,bg ="#16213e",
    highlightthickness =0 )
    preview_canvas .pack (padx =20 ,pady =5 )

    _state ={"collage_img":None }

    def _generate_collage ():
        name =person_var .get ()
        if not name :
            return 

        person =next ((p for p in people if p ["name"]==name ),None )
        if not person :
            return 

        grid_str =grid_var .get ()
        cols ,rows =map (int ,grid_str .split ("x"))
        cell_size =int (size_var .get ())
        total_cells =rows *cols 

        selected_imgs =person ["images"][:total_cells ]
        if not selected_imgs :
            return 

        collage_w =cols *cell_size 
        collage_h =rows *cell_size 
        collage =np .zeros ((collage_h ,collage_w ,3 ),dtype =np .uint8 )
        collage [:]=(30 ,26 ,26 )

        for idx ,fname in enumerate (selected_imgs ):
            r ,c =divmod (idx ,cols )
            if r >=rows :
                break 
            img =cv2 .imread (os .path .join (person ["folder"],fname ))
            if img is None :
                continue 
            resized =cv2 .resize (img ,(cell_size ,cell_size ))
            y0 ,x0 =r *cell_size ,c *cell_size 
            collage [y0 :y0 +cell_size ,x0 :x0 +cell_size ]=resized 


        banner_h =30 
        full_h =collage_h +banner_h 
        full =np .zeros ((full_h ,collage_w ,3 ),dtype =np .uint8 )
        full [:]=(30 ,26 ,26 )
        full [banner_h :,:]=collage 
        cv2 .putText (full ,f"{name }'s Face Collage",
        (10 ,22 ),cv2 .FONT_HERSHEY_SIMPLEX ,0.7 ,
        (233 ,69 ,96 ),2 ,cv2 .LINE_AA )

        _state ["collage_img"]=full 


        from PIL import Image ,ImageTk 
        rgb =cv2 .cvtColor (full ,cv2 .COLOR_BGR2RGB )
        h ,w =rgb .shape [:2 ]
        scale =min (600 /w ,380 /h )
        new_w ,new_h =int (w *scale ),int (h *scale )
        pil =Image .fromarray (rgb ).resize ((new_w ,new_h ),Image .LANCZOS )
        tk_img =ImageTk .PhotoImage (pil )
        _img_refs .clear ()
        _img_refs .append (tk_img )
        preview_canvas .delete ("all")
        preview_canvas .create_image (300 ,190 ,image =tk_img )

        _log_activity ("Face Collage",
        f"Created {grid_str } collage for {name }")

    def _save_collage ():
        if _state ["collage_img"]is None :
            return 
        path =filedialog .asksaveasfilename (
        defaultextension =".jpg",
        filetypes =[("JPEG","*.jpg"),("PNG","*.png")],
        initialfile =f"collage_{person_var .get ()}.jpg",
        )
        if path :
            cv2 .imwrite (path ,_state ["collage_img"])
            messagebox .showinfo ("Saved",f"Collage saved: {path }",parent =win )


    btn_row =tk .Frame (win ,bg ="#1a1a2e")
    btn_row .pack (pady =(5 ,10 ))

    for text ,color ,cmd in [
    ("\u25B6  Generate Collage","#533483",_generate_collage ),
    ("\U0001F4BE  Save","#0e6655",_save_collage ),
    ]:
        bf =tk .Frame (btn_row ,bg =color ,cursor ="hand2")
        bf .pack (side ="left",padx =8 ,ipadx =14 ,ipady =5 )
        bl =tk .Label (bf ,text =text ,font =("Segoe UI",11 ,"bold"),
        fg ="white",bg =color ,cursor ="hand2")
        bl .pack ()
        for w in (bf ,bl ):
            w .bind ("<Button-1>",lambda e ,c =cmd :c ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def face_stats_gui (parent =None ,on_close_callback =None ):
    """Show per-person recognition statistics from the face log."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Face Statistics")
    win .geometry ("750x600")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F4C8  Face Statistics",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,5 ))


    entries =_kv_load ("face_log",[])
    if not isinstance (entries ,list ):
        entries =[]

    if _current_role =="admin":
        scoped_entries =entries 
    else :
        scoped_entries =[
        e for e in entries
        if e .get ("name","Unknown")in (_current_username ,"Unknown")
        ]

    if not scoped_entries :
        tk .Label (
        win ,text ="No face recognition data available yet.\n"
        "Use webcam recognition to generate data.",
        font =("Segoe UI",12 ),fg ="#a0a0b8",bg ="#1a1a2e"
        ).pack (expand =True )
    else :

        person_stats ={}
        for e in scoped_entries :
            name =e .get ("name","Unknown")
            score =e .get ("distance",0 )
            ts =e .get ("time","")
            if name not in person_stats :
                person_stats [name ]={
                "count":0 ,"scores":[],"first":ts ,"last":ts 
                }
            person_stats [name ]["count"]+=1 
            if score >0 :
                person_stats [name ]["scores"].append (score )
            if ts :
                person_stats [name ]["last"]=ts 

        if _current_role =="admin":
            summary_text =f"{len (scoped_entries )} total detections | {len (person_stats )} unique people"
        else :
            summary_text ="User Mode: showing your detections only"
        tk .Label (
        win ,text =summary_text ,
        font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
        ).pack (pady =(0 ,5 ))


        cols =("Name","Detections","Avg Score","Best Score",
        "First Seen","Last Seen")
        tree =ttk .Treeview (win ,columns =cols ,show ="headings",height =14 )
        tree .heading ("Name",text ="Name")
        tree .heading ("Detections",text ="Count")
        tree .heading ("Avg Score",text ="Avg Score")
        tree .heading ("Best Score",text ="Best Score")
        tree .heading ("First Seen",text ="First Seen")
        tree .heading ("Last Seen",text ="Last Seen")
        tree .column ("Name",width =130 )
        tree .column ("Detections",width =70 ,anchor ="center")
        tree .column ("Avg Score",width =90 ,anchor ="center")
        tree .column ("Best Score",width =90 ,anchor ="center")
        tree .column ("First Seen",width =150 ,anchor ="center")
        tree .column ("Last Seen",width =150 ,anchor ="center")

        for name in sorted (person_stats ,key =lambda n :person_stats [n ]["count"],
        reverse =True ):
            ps =person_stats [name ]
            avg =sum (ps ["scores"])/len (ps ["scores"])if ps ["scores"]else 0 
            best =max (ps ["scores"])if ps ["scores"]else 0 
            tree .insert ("","end",values =(
            name ,ps ["count"],
            f"{avg :.3f}",f"{best :.3f}",
            ps ["first"][:19 ]if ps ["first"]else "",
            ps ["last"][:19 ]if ps ["last"]else "",
            ))

        tree .pack (padx =15 ,fill ="both",expand =True ,pady =(0 ,5 ))


        tk .Label (win ,text ="Score Distribution",
        font =("Segoe UI",11 ,"bold"),fg ="white",
        bg ="#1a1a2e").pack (pady =(5 ,2 ))

        chart_canvas =tk .Canvas (win ,width =700 ,height =100 ,bg ="#16213e",
        highlightthickness =0 )
        chart_canvas .pack (padx =15 ,pady =(0 ,10 ))

        all_scores =[e .get ("distance",0 )for e in scoped_entries if e .get ("distance",0 )>0 ]
        if all_scores :

            bins =[0 ]*10 
            for s in all_scores :
                idx =min (int (s *10 ),9 )
                bins [idx ]+=1 
            max_bin =max (bins )if bins else 1 
            bar_w =60 
            x_start =30 
            for i ,count in enumerate (bins ):
                bar_h =int ((count /max_bin )*70 )if max_bin >0 else 0 
                x =x_start +i *(bar_w +8 )
                y_bottom =85 
                y_top =y_bottom -bar_h 
                color ="#00c853"if (i /10 )>=RECOGNITION_THRESHOLD else "#e94560"
                chart_canvas .create_rectangle (x ,y_top ,x +bar_w ,y_bottom ,
                fill =color ,outline ="")
                chart_canvas .create_text (x +bar_w //2 ,y_bottom +10 ,
                text =f"{i /10 :.1f}",
                fill ="#888",font =("Segoe UI",7 ))
                if count >0 :
                    chart_canvas .create_text (x +bar_w //2 ,y_top -8 ,
                    text =str (count ),fill ="#aaa",
                    font =("Segoe UI",7 ))

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def export_center_gui (parent =None ,on_close_callback =None ):
    """Central export hub — export face log, attendance, users, activity."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Export Center")
    win .geometry ("520x480")
    win .resizable (False ,False )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F4E5  Export Center",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(15 ,5 ))

    tk .Label (
    win ,text ="Export all your data in one place",
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,15 ))

    def _make_export_card (label ,description ,export_func ,row ):
        card =tk .Frame (win ,bg ="#16213e")
        card .pack (padx =30 ,fill ="x",pady =5 ,ipady =8 )

        tk .Label (card ,text =label ,font =("Segoe UI",12 ,"bold"),
        fg ="white",bg ="#16213e").pack (anchor ="w",padx =12 ,pady =(5 ,0 ))
        tk .Label (card ,text =description ,font =("Segoe UI",9 ),
        fg ="#a0a0b8",bg ="#16213e").pack (anchor ="w",padx =12 )

        exp_btn =tk .Frame (card ,bg ="#0f3460",cursor ="hand2")
        exp_btn .pack (anchor ="e",padx =12 ,pady =(5 ,8 ),ipadx =10 ,ipady =3 )
        exp_lbl =tk .Label (exp_btn ,text ="\U0001F4E5 Export CSV",
        font =("Segoe UI",9 ,"bold"),fg ="white",
        bg ="#0f3460",cursor ="hand2")
        exp_lbl .pack ()
        for w in (exp_btn ,exp_lbl ):
            w .bind ("<Button-1>",lambda e ,fn =export_func :fn ())

    def _export_face_log ():
        entries =_kv_load ("face_log",[])
        if not isinstance (entries ,list ):
            entries =[]
        path =filedialog .asksaveasfilename (
        defaultextension =".csv",filetypes =[("CSV","*.csv")],
        initialfile ="face_log_export.csv")
        if not path :
            return 
        with open (path ,"w",newline ="",encoding ="utf-8")as f :
            writer =csv .writer (f )
            writer .writerow (["Name","Similarity","Timestamp"])
            for e in entries :
                writer .writerow ([e .get ("name",""),e .get ("distance",""),
                e .get ("time","")])
        messagebox .showinfo ("Exported",f"{len (entries )} entries saved.",parent =win )

    def _export_activity_log ():
        entries =_kv_load ("activity_log",[])
        if not isinstance (entries ,list ):
            entries =[]
        path =filedialog .asksaveasfilename (
        defaultextension =".csv",filetypes =[("CSV","*.csv")],
        initialfile ="activity_log_export.csv")
        if not path :
            return 
        with open (path ,"w",newline ="",encoding ="utf-8")as f :
            writer =csv .writer (f )
            writer .writerow (["Time","User","Role","Action","Detail"])
            for e in entries :
                writer .writerow ([e .get ("time",""),e .get ("user",""),
                e .get ("role",""),e .get ("action",""),
                e .get ("detail","")])
        messagebox .showinfo ("Exported",f"{len (entries )} entries saved.",parent =win )

    def _export_users ():
        db =_load_users_db ()
        path =filedialog .asksaveasfilename (
        defaultextension =".csv",filetypes =[("CSV","*.csv")],
        initialfile ="users_export.csv")
        if not path :
            return 
        with open (path ,"w",newline ="",encoding ="utf-8")as f :
            writer =csv .writer (f )
            writer .writerow (["Username","Role","Created","Total Logins",
            "Last Login"])
            for uname ,info in sorted (db .items ()):
                logins =info .get ("logins",[])
                writer .writerow ([uname ,info .get ("role","user"),
                info .get ("created",""),
                len (logins ),
                logins [-1 ]if logins else ""])
        messagebox .showinfo ("Exported",f"{len (db )} users saved.",parent =win )

    def _export_all_attendance ():
        log =_load_attendance_log ()
        path =filedialog .asksaveasfilename (
        defaultextension =".csv",filetypes =[("CSV","*.csv")],
        initialfile ="all_attendance_export.csv")
        if not path :
            return 
        with open (path ,"w",newline ="",encoding ="utf-8")as f :
            writer =csv .writer (f )
            writer .writerow (["Date","Time Start","Time End","Present",
            "Total","Rate","Present Names","Absent Names"])
            for s in log :
                present =s .get ("present_count",0 )
                total =s .get ("total_registered",0 )
                rate =f"{present /total *100 :.0f}%"if total else "N/A"
                writer .writerow ([
                s ["date"],s .get ("time_start",""),s .get ("time_end",""),
                present ,total ,rate ,
                "; ".join (s .get ("present",{}).keys ()),
                "; ".join (s .get ("absent",[])),
                ])
        messagebox .showinfo ("Exported",f"{len (log )} sessions saved.",parent =win )

    _make_export_card (
    "\U0001F50D Recognition Log",
    "All face recognition events with timestamps and scores",
    _export_face_log ,0 )
    _make_export_card (
    "\U0001F4DC Activity Log",
    "All user actions performed in the app",
    _export_activity_log ,1 )
    _make_export_card (
    "\U0001F464 User Accounts",
    "All registered users with login history",
    _export_users ,2 )
    _make_export_card (
    "\U0001F4CB Attendance Records",
    "All attendance sessions with present/absent data",
    _export_all_attendance ,3 )

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def live_face_counter_gui (parent =None ,on_close_callback =None ):
    """Live webcam face counter — shows count, bounding boxes, FPS."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Live Face Counter")
    win .geometry ("400x200")
    win .resizable (False ,False )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F3AF  Live Face Counter",
    font =("Segoe UI",18 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(15 ,5 ))

    tk .Label (
    win ,text ="Opens webcam — counts faces in real-time with FPS display",
    font =("Segoe UI",9 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,10 ))

    def _start_counter ():
        win .withdraw ()
        cap =cv2 .VideoCapture (0 ,cv2 .CAP_DSHOW )
        if not cap .isOpened ():
            messagebox .showerror ("Error","Cannot open webcam.",parent =win )
            win .deiconify ()
            return 

        yunet =None 
        frame_count =0 
        fps =0.0 
        start_time =time .time ()
        total_faces_detected =0 
        max_simultaneous =0 

        while True :
            ret ,frame =cap .read ()
            if not ret :
                break 

            h ,w =frame .shape [:2 ]
            if yunet is None :
                yunet =_create_yunet (w ,h )
            else :
                yunet .setInputSize ((w ,h ))

            _ ,faces =yunet .detect (frame )
            face_count =len (faces )if faces is not None else 0 
            total_faces_detected +=face_count 
            max_simultaneous =max (max_simultaneous ,face_count )

            if faces is not None :
                for face in faces :
                    x ,y ,fw ,fh =face [:4 ].astype (int )
                    conf =face [14 ]if len (face )>14 else 0 
                    color =(0 ,220 ,0 )if conf >0.8 else (0 ,180 ,255 )
                    cv2 .rectangle (frame ,(x ,y ),(x +fw ,y +fh ),color ,2 )
                    cv2 .putText (frame ,f"{conf :.0%}",
                    (x ,y -5 ),cv2 .FONT_HERSHEY_SIMPLEX ,
                    0.4 ,color ,1 ,cv2 .LINE_AA )


            frame_count +=1 
            elapsed =time .time ()-start_time 
            if elapsed >=1.0 :
                fps =frame_count /elapsed 
                frame_count =0 
                start_time =time .time ()


            hud_y =25 
            cv2 .putText (frame ,f"Faces: {face_count }",(10 ,hud_y ),
            cv2 .FONT_HERSHEY_SIMPLEX ,0.7 ,(0 ,255 ,255 ),2 ,
            cv2 .LINE_AA )
            cv2 .putText (frame ,f"FPS: {fps :.1f}",(10 ,hud_y +30 ),
            cv2 .FONT_HERSHEY_SIMPLEX ,0.6 ,(180 ,180 ,180 ),1 ,
            cv2 .LINE_AA )
            cv2 .putText (frame ,f"Max: {max_simultaneous }",(10 ,hud_y +55 ),
            cv2 .FONT_HERSHEY_SIMPLEX ,0.5 ,(180 ,180 ,180 ),1 ,
            cv2 .LINE_AA )
            cv2 .putText (frame ,f"Total: {total_faces_detected }",
            (10 ,hud_y +75 ),
            cv2 .FONT_HERSHEY_SIMPLEX ,0.5 ,(180 ,180 ,180 ),1 ,
            cv2 .LINE_AA )
            cv2 .putText (frame ,"ESC to exit",(10 ,h -15 ),
            cv2 .FONT_HERSHEY_SIMPLEX ,0.4 ,(120 ,120 ,120 ),1 ,
            cv2 .LINE_AA )

            cv2 .imshow ("Live Face Counter — ESC to exit",frame )
            if cv2 .waitKey (1 )&0xFF ==27 :
                break 

        cap .release ()
        cv2 .destroyAllWindows ()
        _log_activity ("Live Face Counter",
        f"Max {max_simultaneous } faces, total {total_faces_detected }")
        win .deiconify ()

    start_f =tk .Frame (win ,bg ="#0f3460",cursor ="hand2")
    start_f .pack (pady =(5 ,10 ),ipadx =18 ,ipady =6 )
    start_l =tk .Label (start_f ,text ="\u25B6  Start Counter",
    font =("Segoe UI",12 ,"bold"),fg ="white",
    bg ="#0f3460",cursor ="hand2")
    start_l .pack ()
    for w in (start_f ,start_l ):
        w .bind ("<Button-1>",lambda e :_start_counter ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def face_crop_gui (parent =None ,on_close_callback =None ):
    """Detect faces in an image and crop each one into separate files."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Face Crop Tool")
    win .geometry ("650x550")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\u2702\uFE0F  Face Crop Tool",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,2 ))

    tk .Label (
    win ,text ="Upload an image — extract all detected faces as individual files",
    font =("Segoe UI",10 ),fg ="#a0a0b8",bg ="#1a1a2e"
    ).pack (pady =(0 ,8 ))

    _img_refs =[]
    _state ={"crops":[],"source_name":""}


    preview_frame =tk .Frame (win ,bg ="#16213e")
    preview_frame .pack (fill ="both",expand =True ,padx =20 ,pady =(0 ,5 ))

    info_var =tk .StringVar (value ="No image loaded")
    tk .Label (preview_frame ,textvariable =info_var ,font =("Segoe UI",11 ,"bold"),
    fg ="white",bg ="#16213e").pack (pady =(8 ,5 ))


    crop_frame =tk .Frame (preview_frame ,bg ="#16213e")
    crop_frame .pack (fill ="both",expand =True ,padx =10 ,pady =5 )


    margin_frame =tk .Frame (win ,bg ="#1a1a2e")
    margin_frame .pack (fill ="x",padx =20 ,pady =(5 ,0 ))

    tk .Label (margin_frame ,text ="Margin (px):",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(0 ,8 ))
    margin_var =tk .IntVar (value =20 )
    tk .Scale (margin_frame ,from_ =0 ,to =80 ,variable =margin_var ,
    orient ="horizontal",length =200 ,bg ="#1a1a2e",
    fg ="white",troughcolor ="#16213e",highlightthickness =0 ,
    sliderrelief ="flat").pack (side ="left")


    tk .Label (margin_frame ,text ="Resize:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(15 ,5 ))
    crop_size_var =tk .StringVar (value ="Original")
    ttk .Combobox (margin_frame ,textvariable =crop_size_var ,
    values =["Original","128x128","256x256","512x512"],
    state ="readonly",width =10 ).pack (side ="left")

    def _detect_and_crop (path ):
        img =cv2 .imread (path )
        if img is None :
            info_var .set ("Failed to load image.")
            return 

        _state ["source_name"]=os .path .splitext (os .path .basename (path ))[0 ]
        h ,w =img .shape [:2 ]
        yunet =_create_yunet (w ,h )
        _ ,faces =yunet .detect (img )

        if faces is None or len (faces )==0 :
            info_var .set ("No faces detected in this image.")
            _state ["crops"]=[]
            return 

        margin =margin_var .get ()
        crops =[]
        for face in faces :
            x ,y ,fw ,fh =face [:4 ].astype (int )
            x1 =max (0 ,x -margin )
            y1 =max (0 ,y -margin )
            x2 =min (w ,x +fw +margin )
            y2 =min (h ,y +fh +margin )
            crop =img [y1 :y2 ,x1 :x2 ].copy ()

            size_str =crop_size_var .get ()
            if size_str !="Original":
                sz =int (size_str .split ("x")[0 ])
                crop =cv2 .resize (crop ,(sz ,sz ))

            crops .append (crop )

        _state ["crops"]=crops 
        info_var .set (f"Detected {len (crops )} face(s) — click Save to export")


        for w_child in crop_frame .winfo_children ():
            w_child .destroy ()
        _img_refs .clear ()

        from PIL import Image ,ImageTk 
        for i ,crop in enumerate (crops [:16 ]):
            rgb =cv2 .cvtColor (crop ,cv2 .COLOR_BGR2RGB )
            pil =Image .fromarray (rgb ).resize ((90 ,90 ),Image .LANCZOS )
            tk_img =ImageTk .PhotoImage (pil )
            _img_refs .append (tk_img )
            col_f =tk .Frame (crop_frame ,bg ="#16213e")
            col_f .grid (row =i //6 ,column =i %6 ,padx =4 ,pady =4 )
            tk .Label (col_f ,image =tk_img ,bg ="#16213e").pack ()
            tk .Label (col_f ,text =f"Face {i +1 }",font =("Segoe UI",8 ),
            fg ="#aaa",bg ="#16213e").pack ()

    def _load ():
        path =filedialog .askopenfilename (
        filetypes =[("Images","*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if path :
            _detect_and_crop (path )

    def _save_crops ():
        if not _state ["crops"]:
            messagebox .showwarning ("No crops","Load an image first.",parent =win )
            return 
        output_dir =filedialog .askdirectory (title ="Select output folder")
        if not output_dir :
            return 
        for i ,crop in enumerate (_state ["crops"]):
            out_path =os .path .join (
            output_dir ,f"{_state ['source_name']}_face_{i +1 }.jpg")
            cv2 .imwrite (out_path ,crop )
        _log_activity ("Face Crop",
        f"Cropped {len (_state ['crops'])} faces from {_state ['source_name']}")
        messagebox .showinfo (
        "Saved",f"{len (_state ['crops'])} faces saved to {output_dir }",
        parent =win )

    btn_row =tk .Frame (win ,bg ="#1a1a2e")
    btn_row .pack (pady =(8 ,10 ))

    for text ,color ,cmd in [
    ("\U0001F4C2  Load Image","#0f3460",_load ),
    ("\U0001F4BE  Save All Crops","#0e6655",_save_crops ),
    ]:
        bf =tk .Frame (btn_row ,bg =color ,cursor ="hand2")
        bf .pack (side ="left",padx =8 ,ipadx =14 ,ipady =5 )
        bl =tk .Label (bf ,text =text ,font =("Segoe UI",11 ,"bold"),
        fg ="white",bg =color ,cursor ="hand2")
        bl .pack ()
        for w in (bf ,bl ):
            w .bind ("<Button-1>",lambda e ,c =cmd :c ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()





def side_by_side_gui (parent =None ,on_close_callback =None ):
    """Load an image, pick two filters, and show them side-by-side."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("Side-by-Side Filter Comparison")
    win .geometry ("800x560")
    win .resizable (True ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F5BC  Side-by-Side Comparison",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(10 ,5 ))

    _state ={"original":None }
    _img_refs =[]


    sel_frame =tk .Frame (win ,bg ="#1a1a2e")
    sel_frame .pack (fill ="x",padx =20 ,pady =(5 ,5 ))

    all_filters =["Original","Sketch","Cartoon","Oil Painting","HDR",
    "Ghibli Art","Anime","Ghost","Emboss","Watercolor",
    "Pop Art","Neon Glow","Vintage","Pixel Art",
    "Thermal","Glitch","Pencil Color"]

    tk .Label (sel_frame ,text ="Left:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(0 ,5 ))
    left_var =tk .StringVar (value ="Original")
    ttk .Combobox (sel_frame ,textvariable =left_var ,values =all_filters ,
    state ="readonly",width =14 ).pack (side ="left")

    tk .Label (sel_frame ,text ="  Right:",font =("Segoe UI",10 ),
    fg ="#ccc",bg ="#1a1a2e").pack (side ="left",padx =(15 ,5 ))
    right_var =tk .StringVar (value ="Sketch")
    ttk .Combobox (sel_frame ,textvariable =right_var ,values =all_filters ,
    state ="readonly",width =14 ).pack (side ="left")


    canvas_frame =tk .Frame (win ,bg ="#1a1a2e")
    canvas_frame .pack (fill ="both",expand =True ,padx =10 ,pady =5 )

    left_canvas =tk .Canvas (canvas_frame ,width =370 ,height =350 ,bg ="#16213e",
    highlightthickness =0 )
    left_canvas .pack (side ="left",padx =5 )

    right_canvas =tk .Canvas (canvas_frame ,width =370 ,height =350 ,bg ="#16213e",
    highlightthickness =0 )
    right_canvas .pack (side ="left",padx =5 )

    def _render ():
        if _state ["original"]is None :
            return 
        _img_refs .clear ()
        from PIL import Image ,ImageTk 

        for canvas ,fvar in [(left_canvas ,left_var ),
        (right_canvas ,right_var )]:
            fname =fvar .get ()
            if fname =="Original":
                img =_state ["original"].copy ()
            else :
                img =apply_face_filter (_state ["original"].copy (),fname )

            rgb =cv2 .cvtColor (img ,cv2 .COLOR_BGR2RGB )
            h ,w =rgb .shape [:2 ]
            scale =min (370 /w ,350 /h )
            new_w ,new_h =int (w *scale ),int (h *scale )
            pil =Image .fromarray (rgb ).resize ((new_w ,new_h ),Image .LANCZOS )
            tk_img =ImageTk .PhotoImage (pil )
            _img_refs .append (tk_img )
            canvas .delete ("all")
            canvas .create_image (185 ,175 ,image =tk_img )
            canvas .create_text (185 ,10 ,text =fname ,fill ="white",
            font =("Segoe UI",10 ,"bold"))

    left_var .trace_add ("write",lambda *a :_render ())
    right_var .trace_add ("write",lambda *a :_render ())


    btn_row =tk .Frame (win ,bg ="#1a1a2e")
    btn_row .pack (pady =(5 ,8 ))

    def _load ():
        path =filedialog .askopenfilename (
        filetypes =[("Images","*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if not path :
            return 
        img =cv2 .imread (path )
        if img is not None :
            _state ["original"]=img 
            _render ()

    def _save ():
        if _state ["original"]is None :
            return 
        path =filedialog .asksaveasfilename (
        defaultextension =".jpg",
        filetypes =[("JPEG","*.jpg"),("PNG","*.png")],
        initialfile ="side_by_side.jpg",
        )
        if not path :
            return 
        left_f =left_var .get ()
        right_f =right_var .get ()
        left_img =(_state ["original"].copy ()if left_f =="Original"
        else apply_face_filter (_state ["original"].copy (),left_f ))
        right_img =(_state ["original"].copy ()if right_f =="Original"
        else apply_face_filter (_state ["original"].copy (),right_f ))

        h =max (left_img .shape [0 ],right_img .shape [0 ])
        left_img =cv2 .resize (left_img ,(int (left_img .shape [1 ]*h /left_img .shape [0 ]),h ))
        right_img =cv2 .resize (right_img ,(int (right_img .shape [1 ]*h /right_img .shape [0 ]),h ))
        combined =np .hstack ([left_img ,right_img ])
        cv2 .imwrite (path ,combined )
        messagebox .showinfo ("Saved",f"Side-by-side saved: {path }",parent =win )

    for text ,color ,cmd in [
    ("\U0001F4C2  Load Image","#0f3460",_load ),
    ("\U0001F4BE  Save Combined","#0e6655",_save ),
    ]:
        bf =tk .Frame (btn_row ,bg =color ,cursor ="hand2")
        bf .pack (side ="left",padx =8 ,ipadx =14 ,ipady =5 )
        bl =tk .Label (bf ,text =text ,font =("Segoe UI",11 ,"bold"),
        fg ="white",bg =color ,cursor ="hand2")
        bl .pack ()
        for w in (bf ,bl ):
            w .bind ("<Button-1>",lambda e ,c =cmd :c ())

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()




def system_info_gui (parent =None ,on_close_callback =None ):
    """Show system info: Python version, OpenCV, model sizes, DB stats."""
    if parent is None :
        win =tk .Tk ()
        standalone =True 
    else :
        win =tk .Toplevel (parent )
        standalone =False 

    win .title ("System Info")
    win .geometry ("550x520")
    win .resizable (False ,True )
    win .configure (bg ="#1a1a2e")

    _activate_page_scroll (win ,bg ="#1a1a2e")
    tk .Label (
    win ,text ="\U0001F4BB  System Info",
    font =("Segoe UI",20 ,"bold"),fg ="#e94560",bg ="#1a1a2e"
    ).pack (pady =(12 ,8 ))

    info_frame =tk .Frame (win ,bg ="#16213e")
    info_frame .pack (fill ="both",expand =True ,padx =20 ,pady =(0 ,10 ))

    def _row (label ,value ,row ):
        tk .Label (info_frame ,text =label ,font =("Segoe UI",10 ),
        fg ="#a0a0b8",bg ="#16213e",anchor ="e",width =22 ).grid (
        row =row ,column =0 ,padx =10 ,pady =3 ,sticky ="e")
        tk .Label (info_frame ,text =str (value ),font =("Segoe UI",10 ,"bold"),
        fg ="white",bg ="#16213e",anchor ="w").grid (
        row =row ,column =1 ,padx =10 ,pady =3 ,sticky ="w")


    _row ("Python Version",sys .version .split ()[0 ],0 )
    _row ("OpenCV Version",cv2 .__version__ ,1 )
    _row ("NumPy Version",np .__version__ ,2 )
    _row ("Platform",sys .platform ,3 )


    yunet_size =os .path .getsize (YUNET_MODEL )/1024 if os .path .exists (YUNET_MODEL )else 0 
    sface_size =os .path .getsize (SFACE_MODEL )/(1024 *1024 )if os .path .exists (SFACE_MODEL )else 0 
    _row ("YuNet Model",f"{yunet_size :.0f} KB",4 )
    _row ("SFace Model",f"{sface_size :.1f} MB",5 )

    if _current_role =="admin":
        people_dirs =[e for e in os .listdir (FACES_ROOT )
        if _is_person_folder (e ,os .path .join (BASE_DIR ,e ))]
        total_images =0 
        for p in people_dirs :
            folder =os .path .join (FACES_ROOT ,p )
            total_images +=len ([f for f in os .listdir (folder )
            if os .path .splitext (f )[1 ].lower ()in IMAGE_EXTENSIONS ])
        _row ("Registered People",len (people_dirs ),6 )
        _row ("Total Face Images",total_images ,7 )

        enc_size =os .path .getsize (ENCODINGS_PATH )/1024 if os .path .exists (ENCODINGS_PATH )else 0 
        _row ("Encodings Cache",f"{enc_size :.0f} KB",8 )

        face_log_entries =_kv_load ("face_log",[])
        face_log_count =len (face_log_entries )if isinstance (face_log_entries ,list )else 0 
        _row ("Face Log Entries",face_log_count ,9 )

        activity_entries =_kv_load ("activity_log",[])
        activity_count =len (activity_entries )if isinstance (activity_entries ,list )else 0 
        _row ("Activity Log Entries",activity_count ,10 )

        db =_load_users_db ()
        _row ("User Accounts",len (db ),11 )

        att_log =_load_attendance_log ()
        _row ("Attendance Sessions",len (att_log ),12 )

        _row ("Recognition Threshold",RECOGNITION_THRESHOLD ,13 )
        _row ("Frame Scale",FRAME_SCALE ,14 )
        _row ("Stability Window",STABILITY_WINDOW ,15 )

        total_size =0 
        for root ,dirs ,files in os .walk (BASE_DIR ):
            for f in files :
                fp =os .path .join (root ,f )
                try :
                    total_size +=os .path .getsize (fp )
                except OSError :
                    pass 
        _row ("Total Project Size",f"{total_size /(1024 *1024 ):.1f} MB",16 )
    else :
        _row ("Mode","User (restricted view)",6 )
        _row ("Recognition Threshold",RECOGNITION_THRESHOLD ,7 )
        _row ("Frame Scale",FRAME_SCALE ,8 )
        _row ("Stability Window",STABILITY_WINDOW ,9 )

    def on_close ():
        win .destroy ()
        if on_close_callback :
            on_close_callback ()

    win .protocol ("WM_DELETE_WINDOW",on_close )
    if standalone :
        win .mainloop ()






def launch_home ():
    """Launch home UI via frontend module."""
    from frontend .home_screen import launch_home_ui
    return launch_home_ui (sys .modules [__name__ ])



def main ():
    """Run CLI dispatch via backend module."""
    from backend .cli_dispatcher import run_from_argv
    return run_from_argv (sys .modules [__name__ ])

if __name__ =="__main__":
    main ()
 
