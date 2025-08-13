import os
from dotenv import load_dotenv

load_dotenv()  # loads values from .env into environment
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")

if not TWILIO_ACCOUNT_SID:
    raise RuntimeError("TWILIO_ACCOUNT_SID missing. Add it to your .env file.")



import streamlit as st
import paramiko
import boto3
import pandas as pd
import pickle
import smtplib
from email.message import EmailMessage
from twilio.rest import Client
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import pywhatkit
import datetime
from urllib.parse import quote_plus
from streamlit_webrtc import webrtc_streamer, RTCConfiguration
from streamlit_geolocation import streamlit_geolocation
import av
import threading
import os
import io
import contextlib

# --- LangChain Agent Imports ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from langchain_community.tools.file_management import ListDirectoryTool, ReadFileTool
from langchain.chains.summarize import load_summarize_chain
from langchain_core.documents import Document
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.chains import LLMMathChain

# --- Page Configuration ---
st.set_page_config(page_title="Smart Orion Dashboard", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# =====================================================================================
# --- Configurations & Secrets ---
# FILL IN ALL YOUR CREDENTIALS HERE
# =====================================================================================
RHEL_HOST = "10.46.22.166"
RHEL_USER = "root"
RHEL_PASSWORD = "redhat"
AWS_REGION = "ap-south-1"
GMAIL_ADDRESS = "Ayaanajmed2351@gmail.com"
GMAIL_APP_PASSWORD = "wvxf uqbz edsp jjta"
TWILIO_AUTH_TOKEN = "83c41a9f355d5d03ff0be6c956b6e7f5"
TWILIO_PHONE_NUMBER = "+13185366969"
GEMINI_API_KEY = "AIzaSyBuLR8bcsak0eF70T7nnJSBcRrz39FlboI"
INSTANCE_TYPE = 't3.micro'
Maps_API_KEY = "AIzaSyCjUHSaJ66pgjX8V4EJhFO7_QViRELyr4M" # <-- ADD YOUR GOOGLE MAPS KEY HERE
os.environ["GOOGLE_API_KEY"] = "AIzaSyBuLR8bcsak0eF70T7nnJSBcRrz39FlboI"
os.environ["SERPAPI_API_KEY"] ="89a3e27d3a4c6b6886b29ef57ab20f4d2aa829c7dfeda0f56cac860dae2f1fb4"
# =====================================================================================

# --- Helper Class for Video Recording ---
output_video_path = "recorded_video.mp4"
class VideoRecorder:
    def __init__(self) -> None:
        self.output_container = None; self.recording = False
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        if self.recording:
            if self.output_container is None:
                self.output_container = av.open(output_video_path, mode="w")
                self.stream = self.output_container.add_stream("mpeg4", rate=24)
                self.stream.width = frame.width; self.stream.height = frame.height
            for p in self.stream.encode(frame): self.output_container.mux(p)
        return frame
    def start(self):
        self.recording = True; st.toast("Recording started!")
    def stop(self):
        if self.recording and self.output_container:
            for p in self.stream.encode(): self.output_container.mux(p)
            self.output_container.close(); self.output_container = None
        self.recording = False; st.toast(f"Recording stopped! File saved as {output_video_path}")

# --- Reusable Helper Functions ---
@st.cache_data(ttl=60)
def execute_ssh_command(command):
    try:
        client = paramiko.SSHClient(); client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=RHEL_HOST, username=RHEL_USER, password=RHEL_PASSWORD, port=22)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode(); errors = stderr.read().decode(); client.close()
        return output, errors
    except Exception as e: return None, str(e)
@st.cache_resource
def load_salary_model():
    with open('salary_model.pkl', 'rb') as file: return pickle.load(file)
@st.cache_resource
def load_titanic_model():
    with open('titanic_pipeline.pkl', 'rb') as file: return pickle.load(file)
@st.cache_resource
def load_scores_model():
    with open('scores_model.pkl', 'rb') as file: return pickle.load(file)
ec2_client = boto3.client("ec2", region_name=AWS_REGION)
@st.cache_data(ttl=30)
def list_ec2_instances():
    instances_info = []
    try:
        response = ec2_client.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}])
        for r in response['Reservations']:
            for i in r['Instances']:
                instances_info.append({"Instance ID": i['InstanceId'], "Type": i['InstanceType'], "State": i['State']['Name'], "Launch Time": i['LaunchTime'].strftime("%Y-%m-%d %H:%M:%S")})
        return pd.DataFrame(instances_info)
    except Exception as e:
        st.error(f"Error listing instances: {e}")
        return pd.DataFrame()
def launch_ec2_instance():
    try:
        response = ec2_client.run_instances(ImageId='ami-0f5ee92e2d63afc18', InstanceType='t3.micro', MinCount=1, MaxCount=1)
        return response['Instances'][0]['InstanceId'], None
    except Exception as e: return None, str(e)
def terminate_ec2_instance(instance_id):
    try:
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        return f"Terminated {instance_id}.", None
    except Exception as e: return None, str(e)
@st.cache_data
def get_address_from_coords(lat, lon):
    if not GOOGLE_MAPS_API_KEY: return "Google Maps API Key not configured."
    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_MAPS_API_KEY}"
        response = requests.get(url); data = response.json()
        if data['status'] == 'OK': return data['results'][0]['formatted_address']
        else: return "Could not find address."
    except Exception as e: return f"Error: {e}"

# =====================================================================================
# --- Page-Specific Functions ---
# =====================================================================================

def show_home_page():
    st.title("🚀 Welcome to the Smart Orion Dashboard")
    st.markdown("Select a feature from the cards below or use the sidebar to navigate.")
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.subheader("⚙️ Python Automation")
            st.write("Trigger scripts for Email, SMS, AI, and more.")
            if st.button("Go to Python Automation", use_container_width=True, key='nav_py'):
                st.session_state.page = "Python Automation"
                st.rerun()
        with st.container(border=True):
            st.subheader("🐧 Linux & Docker Controls")
            st.write("Manage your RHEL 9 server and Docker containers remotely.")
            if st.button("Go to Linux & Docker", use_container_width=True, key='nav_ld'):
                st.session_state.page = "Linux & Docker Controls"
                st.rerun()
    with col2:
        with st.container(border=True):
            st.subheader("🤖 Machine Learning Hub")
            st.write("Use your trained models to make live predictions.")
            if st.button("Go to ML Hub", use_container_width=True, key='nav_ml'):
                st.session_state.page = "Machine Learning Hub"
                st.rerun()
        with st.container(border=True):
            st.subheader("☁️ AWS Cloud Controls")
            st.write("Launch and manage EC2 instances on the AWS cloud.")
            if st.button("Go to AWS Controls", use_container_width=True, key='nav_aws'):
                st.session_state.page = "AWS Cloud Controls"
                st.rerun()
    with col3:
        with st.container(border=True):
            st.subheader("🌐 Web & Mapping Tools")
            st.write("Replicas of our HTML/JS projects using Streamlit components.")
            if st.button("Go to Web & Mapping", use_container_width=True, key='nav_web'):
                st.session_state.page = "Web & Mapping Tools"
                st.rerun()
        with st.container(border=True):
            st.subheader("🧠 Agentic AI Automation")
            st.write("Interact with intelligent AI agents that can use tools.")
            if st.button("Go to AI Agents", use_container_width=True, key='nav_agents'):
                st.session_state.page = "Agentic AI Automation"
                st.rerun()

def show_python_automation_page():
    st.title("⚙️ Python Automation Toolkit")
    st.markdown("Trigger the original Python automation scripts.")
    st.divider()
    with st.expander("✉️ Send an Email"):
        recipient = st.text_input("Recipient Email:", key="email_to")
        subject = st.text_input("Email Subject:", key="email_subj")
        body = st.text_area("Email Body:", key="email_body")
        if st.button("Send Email"):
            if not all([recipient, subject, body, GMAIL_ADDRESS, GMAIL_APP_PASSWORD]): st.error("Please fill in all fields and configure credentials.")
            else:
                with st.spinner("Sending email..."):
                    try:
                        msg = EmailMessage(); msg['Subject'] = subject; msg['From'] = GMAIL_ADDRESS; msg['To'] = recipient; msg.set_content(body)
                        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s: s.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD); s.send_message(msg)
                        st.success("Email sent successfully!")
                    except Exception as e: st.error(f"Failed to send email: {e}")
    with st.expander("💬 Send an SMS / 📞 Make a Phone Call (Twilio)"):
        to_number = st.text_input("Recipient Phone Number:", placeholder="+91...", key="twilio_num")
        col1, col2 = st.columns(2)
        with col1:
            sms_body = st.text_input("SMS Message:", key="twilio_sms")
            if st.button("Send SMS"):
                if not all([to_number, sms_body, TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]): st.error("Please fill fields and configure Twilio credentials.")
                else:
                    with st.spinner("Sending SMS..."):
                        try:
                            client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
                            message = client.messages.create(to=to_number, from_=TWILIO_PHONE_NUMBER, body=sms_body)
                            st.success(f"SMS sent! SID: {message.sid}")
                        except Exception as e: st.error(f"Failed to send SMS: {e}")
        with col2:
            call_body = st.text_input("Voice Message for Call:", "Hello from the Orion Dashboard.", key="twilio_call")
            if st.button("Make Call"):
                if not all([to_number, call_body, TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]): st.error("Please fill fields and configure Twilio credentials.")
                else:
                    with st.spinner("Initiating call..."):
                        try:
                            client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
                            call = client.calls.create(twiml=f'<Response><Say>{call_body}</Say></Response>', to=to_number, from_=TWILIO_PHONE_NUMBER)
                            st.success(f"Call initiated! SID: {call.sid}")
                        except Exception as e: st.error(f"Failed to make call: {e}")
    with st.expander("🤖 Ask Gemini AI"):
        prompt = st.text_area("Your question for Gemini:", key="gemini_prompt")
        if st.button("Ask Gemini"):
            if not all([prompt, os.environ.get("GOOGLE_API_KEY")]): st.error("Please enter a prompt and configure your Gemini API key.")
            else:
                with st.spinner("Thinking..."):
                    try:
                        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest")
                        response = llm.invoke(prompt)
                        st.markdown(response.content)
                    except Exception as e: st.error(f"Error with Gemini: {e}")
    with st.expander("📱 Send a WhatsApp Message"):
        st.warning("Limitation: This automates your local browser. It only works if the browser and this app are on the same computer.")
        wa_number = st.text_input("WhatsApp Recipient Number:", placeholder="+91...", key="wa_num")
        wa_message = st.text_input("WhatsApp Message:", key="wa_msg")
        if st.button("Send on WhatsApp"):
            if not all([wa_number, wa_message]): st.error("Please provide a number and a message.")
            else:
                with st.spinner("Opening WhatsApp Web..."):
                    try:
                        pywhatkit.sendwhatmsg_instantly(wa_number, wa_message, wait_time=15)
                        st.success("WhatsApp tab opened! Please check your browser.")
                    except Exception as e: st.error(f"Failed to open WhatsApp: {e}")
    with st.expander("🕸️ Scrape a Website"):
        url_to_scrape = st.text_input("Enter URL to Scrape:", "http://quotes.toscrape.com/", key="scrape_url")
        if st.button("Scrape Titles/Text"):
            with st.spinner(f"Scraping {url_to_scrape}..."):
                try:
                    response = requests.get(url_to_scrape); soup = BeautifulSoup(response.content, 'html.parser')
                    scraped_text = soup.find_all(['h1', 'h2', 'span', 'p'])
                    result = "\n".join([tag.get_text().strip() for tag in scraped_text[:20]])
                    st.text("Scraped Content:"); st.code(result)
                except Exception as e: st.error(f"Failed to scrape website: {e}")

def show_web_and_mapping_page():
    st.title("🌐 Web & Mapping Tools")
    st.markdown("Replicating our HTML/JS projects using Streamlit's Python components.")
    st.divider()
    with st.expander("📸 Capture & Send Photo"):
        img_file_buffer = st.camera_input("Take a picture")
        if img_file_buffer is not None:
            st.image(img_file_buffer, caption="Photo Captured!")
            with st.form("email_photo_form"):
                recipient = st.text_input("Recipient Email for Photo:")
                submitted = st.form_submit_button("Send Photo via Email")
                if submitted:
                    if not all([recipient, GMAIL_ADDRESS, GMAIL_APP_PASSWORD]): st.error("Please enter a recipient and configure email credentials.")
                    else:
                        with st.spinner("Sending photo via email..."):
                            try:
                                msg = EmailMessage(); msg['Subject'] = "Photo from Orion Dashboard"; msg['From'] = GMAIL_ADDRESS; msg['To'] = recipient
                                msg.set_content("A photo captured from the Streamlit app!"); msg.add_attachment(img_file_buffer.getvalue(), maintype='image', subtype='png', filename='capture.png')
                                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s: s.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD); s.send_message(msg)
                                st.success("Photo sent successfully!")
                            except Exception as e: st.error(f"Failed to send email: {e}")
    with st.expander("🔴 Record a Video Clip (Advanced)"):
        st.write("This feature uses `streamlit-webrtc` to record a video clip from your webcam.")
        if 'recorder' not in st.session_state: st.session_state.recorder = None
        ctx = webrtc_streamer(key="video-recorder", video_processor_factory=VideoRecorder, media_stream_constraints={"video": True, "audio": True}, rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
        if ctx.video_processor:
            if not ctx.video_processor.recording:
                if st.button("Start Recording"):
                    st.session_state.recorder = ctx.video_processor
                    st.session_state.recorder.start()
            else:
                if st.button("Stop Recording"):
                    if st.session_state.recorder:
                        st.session_state.recorder.stop()
                        st.rerun()
        if os.path.exists(output_video_path):
             try:
                with open(output_video_path, "rb") as f:
                    st.download_button("Download Recorded Video", f, file_name="recorded_video.mp4")
             except FileNotFoundError: pass
    with st.expander("📍 Find Your Location (IP & Precise)"):
        st.write("Find your location using your IP Address or more precise Browser Geolocation.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Find My IP Location"):
                with st.spinner("Finding location based on IP..."):
                    try:
                        ip_r = requests.get('https://api.ipify.org?format=json').json(); ip = ip_r['ip']
                        loc_r = requests.get(f'http://ip-api.com/json/{ip}').json()
                        st.text("Results:"); st.json(loc_r)
                        if loc_r.get('lat') and loc_r.get('lon'): st.map(pd.DataFrame({'lat': [loc_r['lat']], 'lon': [loc_r['lon']]}))
                    except Exception as e: st.error(f"Could not fetch IP information: {e}")
        with col2:
            st.write("Find My Precise Location:")
            location = streamlit_geolocation()
            if location and location['latitude']:
                st.success(f"Precise location found!")
                st.map(pd.DataFrame({'lat': [location['latitude']], 'lon': [location['longitude']]}), zoom=15)
            else:
                st.info("Browser may ask for permission to get your precise location.")
    with st.expander("🗺️ Show Route on Map"):
        st.write("Enter an origin and destination to plot a route on the map.")
        if 'origin' not in st.session_state: st.session_state.origin = "Jaipur Railway Station"
        col1, col2 = st.columns([3, 1])
        with col1:
            origin_text = st.text_input("Route Origin:", st.session_state.origin, key="origin_input")
        with col2:
            st.write("_or use your location_")
            if st.button("⌖ Find My Location"):
                with st.spinner("Getting your precise location..."):
                    location = streamlit_geolocation()
                    if location and location.get('latitude'):
                        address = get_address_from_coords(location['latitude'], location['longitude'])
                        st.session_state.origin = address
                        st.rerun()
                    else:
                        st.warning("Could not get location. Please grant permission.")
        destination_text = st.text_input("Route Destination:", "Hawa Mahal, Jaipur")
        if st.button("Plot Route"):
            if not GOOGLE_MAPS_API_KEY: st.error("Please configure your Google Maps API Key.")
            elif not origin_text or not destination_text: st.warning("Please enter an origin and destination.")
            else:
                origin_encoded = quote_plus(origin_text); destination_encoded = quote_plus(destination_text)
                maps_url = f"https://www.google.com/maps/embed/v1/directions?key={GOOGLE_MAPS_API_KEY}&origin={origin_encoded}&destination={destination_encoded}"
                st.components.v1.iframe(maps_url, height=500)

def show_linux_docker_page():
    st.title("🐧 Linux & Docker Control Panel")
    st.markdown(f"Live controls for your RHEL 9 server at `{RHEL_HOST}`.")
    st.divider()
    st.subheader("System Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Check Disk Space"):
            with st.spinner("Executing `df -h`..."):
                output, errors = execute_ssh_command("df -h")
                if errors: st.error(errors)
                else: st.text("Disk Space:"); st.code(output, language='bash')
    with col2:
        if st.button("Check Memory Usage"):
            with st.spinner("Executing `free -h`..."):
                output, errors = execute_ssh_command("free -h")
                if errors: st.error(errors)
                else: st.text("Memory Usage:"); st.code(output, language='bash')
    with col3:
         if st.button("List Top Processes"):
            with st.spinner("Executing `ps aux | head -n 10`..."):
                output, errors = execute_ssh_command("ps aux | head -n 10")
                if errors: st.error(errors)
                else: st.text("Top 10 Processes:"); st.code(output, language='bash')
    st.divider()
    st.subheader("Docker Container Management")
    if st.button("List All Docker Containers"):
        with st.spinner("Executing `docker ps -a`..."):
            output, errors = execute_ssh_command("docker ps -a")
            if errors: st.error(errors)
            else: st.text("All Containers:"); st.code(output, language='bash')
    st.markdown("---")
    st.subheader("Manage a Specific Container")
    container_name = st.text_input("Enter Container Name or ID", placeholder="e.g., my-flask-app")
    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("✅ Start Container"):
            if container_name:
                command = f"docker start {container_name}"
                with st.spinner(f"Executing `{command}`..."):
                    output, errors = execute_ssh_command(command)
                    if errors: st.error(errors)
                    else: st.success(f"Command sent successfully!"); st.code(output, language='bash')
            else:
                st.warning("Please enter a container name.")
    with colB:
        if st.button("🛑 Stop Container"):
            if container_name:
                command = f"docker stop {container_name}"
                with st.spinner(f"Executing `{command}`..."):
                    output, errors = execute_ssh_command(command)
                    if errors: st.error(errors)
                    else: st.warning(f"Command sent successfully!"); st.code(output, language='bash')
            else:
                st.warning("Please enter a container name.")
    with colC:
        if st.button("❌ Remove Container"):
            if container_name:
                command = f"docker rm {container_name}"
                with st.spinner(f"Executing `{command}`..."):
                    output, errors = execute_ssh_command(command)
                    if errors: st.error(errors)
                    else: st.error(f"Command sent successfully!"); st.code(output, language='bash')
            else:
                st.warning("Please enter a container name.")
    st.divider()
    st.subheader("Interactive Web Terminal")
    st.warning("🚨 DANGER: You are logged in as root. Commands can make permanent changes to your server.")
    custom_command = st.text_input("Enter any command to execute on the RHEL 9 server:", placeholder="e.g., ls -l /root/docker_projects")
    if st.button("Run Command"):
        if custom_command:
            with st.spinner(f"Executing `{custom_command}`..."):
                output, errors = execute_ssh_command(custom_command)
                st.markdown("### Command Output:")
                if errors:
                    st.error("Errors:"); st.code(errors, language='bash')
                else:
                    st.success("Standard Output:"); st.code(output, language='bash')
        else:
            st.warning("Please enter a command to run.")

def show_aws_cloud_page():
    st.title("☁️ AWS Cloud Controls")
    st.markdown(f"Managing EC2 instances in region `{AWS_REGION}`.")
    st.divider()
    st.subheader("Launch a New EC2 Instance")
    if st.button(f"🚀 Launch New {'t3.micro'} Instance"):
        with st.spinner("Sending launch request to AWS..."):
            instance_id, error = launch_ec2_instance()
            if error: st.error(f"Error launching instance: {error}")
            else:
                st.success(f"Instance launch initiated successfully! New Instance ID: `{instance_id}`")
                st.cache_data.clear()
    st.divider()
    st.subheader("Manage Existing Instances")
    if st.button("🔄 Refresh Instance List"):
        st.cache_data.clear()
    with st.spinner("Fetching instance data from AWS..."):
        instances_df = list_ec2_instances()
    if not instances_df.empty:
        st.dataframe(instances_df, use_container_width=True)
        st.markdown("---")
        st.subheader("Terminate an Instance")
        running_instances = instances_df[instances_df['State'].isin(['pending', 'running'])]
        instance_to_terminate = st.selectbox("Select a running instance to terminate:", options=running_instances['Instance ID'].tolist(), index=None, placeholder="Choose an instance...")
        if st.button("❌ Terminate Selected Instance", type="primary"):
            if instance_to_terminate:
                with st.spinner(f"Sending termination request for `{instance_to_terminate}`..."):
                    result, error = terminate_ec2_instance(instance_to_terminate)
                    if error: st.error(f"Error terminating instance: {error}")
                    else:
                        st.warning(result)
                        st.cache_data.clear()
            else:
                st.warning("Please select an instance from the dropdown to terminate.")
    else:
        st.info("No running or pending EC2 instances found in this region.")

def show_ml_hub_page():
    st.title("🤖 Machine Learning Hub")
    st.markdown("Use our trained models to make real-time predictions.")
    model_choice = st.selectbox("Select a Model:", ["Score Prediction", "Salary Prediction", "Titanic Survival Prediction"])
    st.divider()
    if model_choice == "Score Prediction":
        st.subheader("Predict Student Score")
        model = load_scores_model()
        hours = st.slider("Hours Studied:", min_value=0.0, max_value=10.0, value=5.0, step=0.25)
        if st.button("Predict Score"):
            prediction = model.predict(pd.DataFrame({'Hours': [hours]}))
            st.success(f"Predicted Score: **{prediction[0]:.2f}%**")
    elif model_choice == "Salary Prediction":
        st.subheader("Predict Employee Salary")
        model = load_salary_model()
        experience = st.slider("Years of Experience:", min_value=0.0, max_value=20.0, value=5.0, step=0.5)
        if st.button("Predict Salary"):
            prediction = model.predict(pd.DataFrame({'Years of Experience': [experience]}))
            st.success(f"Predicted Salary: **${prediction[0]:,.2f}**")
    elif model_choice == "Titanic Survival Prediction":
        st.subheader("Predict Titanic Passenger Survival")
        pipeline = load_titanic_model()
        st.write("Enter passenger details:")
        col1, col2, col3 = st.columns(3)
        with col1:
            pclass = st.selectbox("Passenger Class (Pclass):", [1, 2, 3])
            sex = st.radio("Sex:", ["male", "female"])
            sibsp = st.number_input("Siblings/Spouses Aboard (SibSp):", min_value=0, value=0)
        with col2:
            age = st.number_input("Age:", min_value=0, value=30)
            parch = st.number_input("Parents/Children Aboard (Parch):", min_value=0, value=0)
            fare = st.number_input("Fare ($):", min_value=0.0, value=50.0, step=10.0)
        with col3:
            embarked = st.selectbox("Port of Embarkation (Embarked):", ["S", "C", "Q"])
        if st.button("Predict Survival"):
            input_data = pd.DataFrame({ 'Pclass': [pclass], 'Age': [age], 'SibSp': [sibsp], 'Parch': [parch], 'Fare': [fare], 'Sex': [sex], 'Embarked': [embarked] })
            prediction = pipeline.predict(input_data)
            prediction_proba = pipeline.predict_proba(input_data)
            if prediction[0] == 1:
                st.success(f"✅ Predicts **SURVIVAL** (Probability: {prediction_proba[0][1]*100:.2f}%)")
            else:
                st.error(f"❌ Predicts **NO SURVIVAL** (Probability of Survival: {prediction_proba[0][1]*100:.2f}%)")

def show_agentic_ai_page():
    st.title("🧠 Agentic AI Automation")
    st.markdown("Interact with intelligent AI agents that can use tools to solve problems.")
    agent_choice = st.selectbox("Select an Agent:", ["Math Agent", "Search Agent", "File System Agent", "Text Summarizer Agent", "SQL Database Agent"])
    st.divider()
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)
    if agent_choice == "Math Agent":
        st.subheader("🔢 Math Agent")
        st.info("This agent uses a specialized math chain to solve word problems.")
        question = st.text_area("Enter your math question:", "If a car travels at 120 km/h for 3.5 hours, how far does it go?", key="math_q")
        if st.button("Run Math Agent"):
            if not question: st.warning("Please enter a math question.")
            else:
                with st.spinner("Agent is calculating..."):
                    try:
                        math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)
                        response = math_chain.invoke(question)
                        st.subheader("Final Answer:"); st.success(response['answer'])
                        with st.expander("Show Thought Process"): st.write(response)
                    except Exception as e: st.error(f"An error occurred: {e}")
    elif agent_choice == "Search Agent":
        st.subheader("🔍 Live Search Agent")
        st.info("This agent can search the internet to answer questions about current events.")
        question = st.text_area("Enter your search query:", "What is the latest news about the Mars rover?", key="search_q")
        if st.button("Run Search Agent"):
            with st.spinner("Agent is searching the web..."):
                tools = load_tools(["serpapi"], llm=llm)
                prompt = hub.pull("hwchase17/react")
                agent = create_react_agent(llm, tools, prompt)
                agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
                string_io = io.StringIO()
                with contextlib.redirect_stdout(string_io):
                    response = agent_executor.invoke({"input": question})
                thought_process = string_io.getvalue()
                st.subheader("Final Answer:"); st.success(response['output'])
                with st.expander("Show Thought Process"): st.code(thought_process)
    elif agent_choice == "File System Agent":
        st.subheader("📁 Local File System Agent")
        st.info("This agent can list files and read their content from the dashboard's directory.")
        question = st.text_area("Ask about the files:", "What files are in the current directory?", key="fs_q")
        if st.button("Run File System Agent"):
            with st.spinner("Agent is accessing the file system..."):
                tools = [ListDirectoryTool(), ReadFileTool()]
                prompt = hub.pull("hwchase17/react")
                agent = create_react_agent(llm, tools, prompt)
                agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
                string_io = io.StringIO()
                with contextlib.redirect_stdout(string_io):
                    response = agent_executor.invoke({"input": question})
                thought_process = string_io.getvalue()
                st.subheader("Final Answer:"); st.success(response['output'])
                with st.expander("Show Thought Process"): st.code(thought_process)
    elif agent_choice == "Text Summarizer Agent":
        st.subheader("✍️ Text Summarizer Agent")
        st.info("This agent can condense long pieces of text into a short summary.")
        text_to_summarize = st.text_area("Paste the text you want to summarize:", "Jupiter is the fifth planet from the Sun...", height=200, key="sum_q")
        if st.button("Summarize Text"):
            with st.spinner("Agent is summarizing..."):
                docs = [Document(page_content=text_to_summarize)]
                chain = load_summarize_chain(llm, chain_type="map_reduce")
                response = chain.invoke(docs)
                st.subheader("Summary:"); st.success(response['output_text'])
    elif agent_choice == "SQL Database Agent":
        st.subheader("🗃️ SQL Database Agent")
        st.info("This agent can answer questions by querying the `company_database.db` file.")
        if not os.path.exists("company_database.db"):
            st.error("Error: `company_database.db` not found. Please ensure it is in the same folder as the dashboard.")
        else:
            question = st.text_area("Ask a question about the employee data:", "How many employees are in the Marketing department?", key="sql_q")
            if st.button("Run SQL Agent"):
                with st.spinner("Agent is querying the database..."):
                    db = SQLDatabase.from_uri("sqlite:///company_database.db")
                    db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)
                    string_io = io.StringIO()
                    with contextlib.redirect_stdout(string_io):
                        response = db_chain.invoke(question)
                    thought_process = string_io.getvalue()
                    st.subheader("Final Answer:"); st.success(response['result'])
                    with st.expander("Show Thought Process (including SQL Query)"): st.code(thought_process)

# =====================================================================================
# --- Main App Router ---
# =====================================================================================
if "page" not in st.session_state:
    st.session_state.page = "Home"
st.sidebar.title("Smart Orion Dashboard")
page_options = ["Home", "Python Automation", "Web & Mapping Tools", "Linux & Docker Controls", "AWS Cloud Controls", "Machine Learning Hub", "Agentic AI Automation"]
current_page_index = page_options.index(st.session_state.page)
page_choice = st.sidebar.radio("Navigate", page_options, index=current_page_index)
if page_choice != st.session_state.page:
    st.session_state.page = page_choice
    st.rerun()

# Router
if st.session_state.page == "Home":
    show_home_page()
elif st.session_state.page == "Python Automation":
    show_python_automation_page()
elif st.session_state.page == "Web & Mapping Tools":
    show_web_and_mapping_page()
elif st.session_state.page == "Linux & Docker Controls":
    show_linux_docker_page()
elif st.session_state.page == "AWS Cloud Controls":
    show_aws_cloud_page()
elif st.session_state.page == "Machine Learning Hub":
    show_ml_hub_page()
elif st.session_state.page == "Agentic AI Automation":
    show_agentic_ai_page()
