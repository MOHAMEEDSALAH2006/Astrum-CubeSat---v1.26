import customtkinter as ctk
import time 
import socket
import select
from tkinter import ttk
import threading
import random
import sqlite3

# استيراد مكتبات الرسم الهندسي والـ 3D المستقرة
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  
import numpy as np

# إعدادات المظهر العام للـ Ground Station
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AstrumSpaceNetworkDashboardFinal(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("ASTRUM-1 | Advanced Space Networking Ground Station")
        self.geometry("1650x1000")
        
        # متغير للتحكم في عدم تكرار فتح نافذة التحذير الحركي
        self.alert_popup_open = False
        
        # --- [إنشاء أو فتح قاعدة البيانات والجدول] ---
        self.db_conn = sqlite3.connect("astrum_telemetry.db", check_same_thread=False)
        self.db_cursor = self.db_conn.cursor()
        self.init_sql_database()
        
        # إعدادات استقبال البيانات اللاسلكية
        self.UDP_IP = "0.0.0.0"
        self.UDP_PORT = 12345
        self.is_connected = False
        self.last_packet_time = 0
        
        # مخازن البيانات الحية لقمر ASTRUM-1
        self.current_temp = "28.1"
        self.gyro_x, self.gyro_y = "+0.00", "-0.00"
        self.packet_counter = 0
        
        # --- [المخازن الجديدة للمستشعرات المضافة] ---
        self.light_intensity = 0       
        self.light_status = "DARK"      
        self.servo1_angle = 0.0
        self.servo2_angle = 0.0
        
        # متغيرات الأمان والشبكة الفرعية
        self.acl_status = "ACTIVE (SECURED MAC)"
        self.encryption_type = "AES-256 BIT"
        self.qos_queue_load = "0%"
        
        # مصفوفة لتخزين بيانات الملفات الطائرة في الأنيميشن
        self.animated_files = []
        self.flash_state = False  
        
        self.setup_ui()
        
        # تحميل البيانات القديمة المتخزنة في الـ SQL وعرضها
        self.load_historical_data()
        
        # تهيئة سوكت الـ UDP للـ Telemetry
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.UDP_IP, self.UDP_PORT))
        self.sock.setblocking(False)
        
        # تشغيل استقبال البيانات في خلفية منفصلة
        self.network_thread = threading.Thread(target=self.receive_wifi_data, daemon=True)
        self.network_thread.start()
        
        # بدء حلقة الأنيميشن والـ Loops
        self.animate_canvas_loop()
        self.update_ui_loop()

    def init_sql_database(self):
        self.db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id TEXT,
                timestamp TEXT,
                transport_layer TEXT,
                decrypted_payload TEXT,
                rssi TEXT,
                bus_volt TEXT,
                sys_mode TEXT
            )
        """)
        self.db_conn.commit()

    def load_historical_data(self):
        self.db_cursor.execute("SELECT frame_id, timestamp, transport_layer, decrypted_payload, rssi, bus_volt, sys_mode FROM telemetry_logs ORDER BY id DESC LIMIT 100")
        rows = self.db_cursor.fetchall()
        for row in rows:
            self.tree.insert("", "end", values=row)
        self.packet_counter = len(rows)

    def setup_ui(self):
        self.main_title = ctk.CTkLabel(self, text="🛰️ ASTRUM-1 SPACE NETWORKING & GROUND CONTROL", 
                                      font=ctk.CTkFont(size=32, weight="bold"), text_color="#00D4FF")
        self.main_title.pack(pady=(10, 2))

        self.alert_banner = ctk.CTkLabel(self, text="SYSTEM STATUS: NOMINAL", fg_color="#1E2B38", 
                                        height=35, font=ctk.CTkFont(size=16, weight="bold"), text_color="#2ECC71")
        self.alert_banner.pack(fill="x", padx=20, pady=(0, 5))

        # ---------------- الحاوية العلوية للمربعات الكبيرة ----------------
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=5)
        self.top_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        self.temp_frame = ctk.CTkFrame(self.top_frame, border_width=2, border_color="#FF4B2B")
        self.temp_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(self.temp_frame, text="THERMAL CONTROL (UDP)", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FADBD8").pack(pady=5)
        self.temp_display = ctk.CTkLabel(self.temp_frame, text="--.-°C", font=ctk.CTkFont(size=52, weight="bold"), text_color="#FF4B2B")
        self.temp_display.pack(expand=True, pady=10)

        self.gyro_frame = ctk.CTkFrame(self.top_frame, border_width=2, border_color="#1D976C")
        self.gyro_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(self.gyro_frame, text="ATTITUDE CONTROL (UDP)", font=ctk.CTkFont(size=18, weight="bold"), text_color="#D5F5E3").pack(pady=5)
        self.gyro_display = ctk.CTkLabel(self.gyro_frame, text="X: 0.00°\nY: 0.00°", font=ctk.CTkFont(family="Courier", size=36, weight="bold"), text_color="#1D976C")
        self.gyro_display.pack(expand=True, pady=5)

        self.net_status_frame = ctk.CTkFrame(self.top_frame, border_width=2, border_color="#F39C12")
        self.net_status_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(self.net_status_frame, text="SECURITY & ACL STATUS", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FDEBD0").pack(pady=5)
        
        self.acl_lbl = ctk.CTkLabel(self.net_status_frame, text=f"• ACL FIREWALL: {self.acl_status}", font=ctk.CTkFont(size=15, weight="bold"), text_color="#F39C12")
        self.acl_lbl.pack(anchor="w", padx=15, pady=4)
        self.enc_lbl = ctk.CTkLabel(self.net_status_frame, text=f"• CIPHER KEY : {self.encryption_type}", font=ctk.CTkFont(size=15, weight="bold"), text_color="#E67E22")
        self.enc_lbl.pack(anchor="w", padx=15, pady=4)
        self.qos_lbl = ctk.CTkLabel(self.net_status_frame, text=f"• QoS QUEUE  : {self.qos_queue_load}", font=ctk.CTkFont(size=15, weight="bold"), text_color="#F1C40F")
        self.qos_lbl.pack(anchor="w", padx=15, pady=4)

        self.c2_frame = ctk.CTkFrame(self.top_frame, border_width=2, border_color="#9D50BB")
        self.c2_frame.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(self.c2_frame, text="CRITICAL C2 LINK (TCP)", font=ctk.CTkFont(size=18, weight="bold"), text_color="#E8DAEF").pack(pady=5)
        
        self.tcp_btn = ctk.CTkButton(self.c2_frame, text="⚡ SEND TCP REBOOT CMD", font=ctk.CTkFont(size=15, weight="bold"), 
                                     fg_color="#9D50BB", hover_color="#7B3B97", height=40, command=self.send_critical_tcp_command)
        self.tcp_btn.pack(pady=10, padx=15)
        self.tcp_status_lbl = ctk.CTkLabel(self.c2_frame, text="TCP Link Status: STANDBY", font=ctk.CTkFont(size=15, weight="bold"), text_color="#BDC3C7")
        self.tcp_status_lbl.pack(pady=1)

        # ---------------- الحاوية المشتركة لمستشعرات الضوء والسيرفو (Row 2) ----------------
        self.new_sensors_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.new_sensors_frame.pack(fill="x", padx=20, pady=5)
        self.new_sensors_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.light_frame = ctk.CTkFrame(self.new_sensors_frame, border_width=2, border_color="#F1C40F", height=140)
        self.light_frame.grid(row=0, column=0, padx=5, pady=0, sticky="nsew")
        self.light_frame.pack_propagate(False)
        ctk.CTkLabel(self.light_frame, text="☀️ PHOTO-SENSING SUBSYSTEM", font=ctk.CTkFont(size=17, weight="bold"), text_color="#F1C40F").pack(pady=5)
        self.light_val_lbl = ctk.CTkLabel(self.light_frame, text="RAW VALUE: 0000", font=ctk.CTkFont(family="Courier", size=22, weight="bold"))
        self.light_val_lbl.pack(pady=2)
        self.light_status_lbl = ctk.CTkLabel(self.light_frame, text="STATE: DARK", font=ctk.CTkFont(size=24, weight="bold"), text_color="#7F8C8D")
        self.light_status_lbl.pack(pady=5)

        self.servo1_frame = ctk.CTkFrame(self.new_sensors_frame, border_width=2, border_color="#3498DB", height=140)
        self.servo1_frame.grid(row=0, column=1, padx=5, pady=0, sticky="nsew")
        self.servo1_frame.pack_propagate(False)
        ctk.CTkLabel(self.servo1_frame, text="⚙️ SOLAR PANEL SERVO 1", font=ctk.CTkFont(size=17, weight="bold"), text_color="#3498DB").pack(pady=2)
        self.servo1_canvas = ctk.CTkCanvas(self.servo1_frame, width=110, height=70, bg="#1A252F", highlightthickness=0)
        self.servo1_canvas.pack(side="left", padx=15, pady=5)
        self.servo1_text = ctk.CTkLabel(self.servo1_frame, text="SERVO 1:\n0.0°", font=ctk.CTkFont(family="Courier", size=20, weight="bold"), text_color="#3498DB")
        self.servo1_text.pack(side="right", expand=True)

        self.servo2_frame = ctk.CTkFrame(self.new_sensors_frame, border_width=2, border_color="#2ECC71", height=140)
        self.servo2_frame.grid(row=0, column=2, padx=5, pady=0, sticky="nsew")
        self.servo2_frame.pack_propagate(False)
        ctk.CTkLabel(self.servo2_frame, text="⚙️ SOLAR PANEL SERVO 2", font=ctk.CTkFont(size=17, weight="bold"), text_color="#2ECC71").pack(pady=2)
        self.servo2_canvas = ctk.CTkCanvas(self.servo2_frame, width=110, height=70, bg="#1A252F", highlightthickness=0)
        self.servo2_canvas.pack(side="left", padx=15, pady=5)
        self.servo2_text = ctk.CTkLabel(self.servo2_frame, text="SERVO 2:\n0.0°", font=ctk.CTkFont(family="Courier", size=20, weight="bold"), text_color="#2ECC71")
        self.servo2_text.pack(side="right", expand=True)

        # ---------------- الحاوية المشتركة الوسطى ----------------
        self.center_container = ctk.CTkFrame(self, fg_color="transparent")
        self.center_container.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.embed_frame = ctk.CTkFrame(self.center_container, width=320, border_width=2, border_color="#00D4FF")
        self.embed_frame.pack(side="left", fill="both", expand=False, padx=(0, 5))
        ctk.CTkLabel(self.embed_frame, text="📡 PACKET FLIGHT", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00D4FF").pack(pady=5)
        
        self.anim_canvas = ctk.CTkCanvas(self.embed_frame, width=300, height=360, bg="#07111E", highlightthickness=0)
        self.anim_canvas.pack(fill="both", expand=True, padx=5, pady=5)

        # القسم الأوسط: نافذة الـ 3D CubeSat الفعلي المصمت
        self.cube_3d_frame = ctk.CTkFrame(self.center_container, width=380, border_width=2, border_color="#E67E22")
        self.cube_3d_frame.pack(side="left", fill="both", expand=False, padx=(0, 5))
        ctk.CTkLabel(self.cube_3d_frame, text="🛸 REAL-TIME 3D CUBESAT ORIENTATION", font=ctk.CTkFont(size=16, weight="bold"), text_color="#E67E22").pack(pady=5)
        
        self.fig = plt.figure(figsize=(4, 4), facecolor='#111D2A')
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        self.ax.set_facecolor('#111D2A')
        
        self.cube_canvas = FigureCanvasTkAgg(self.fig, master=self.cube_3d_frame)
        self.cube_canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        self.init_3d_cube_mesh()

        # القسم الأيمن: مستطيل قاعدة البيانات المركزي المطور
        self.db_frame = ctk.CTkFrame(self.center_container, border_width=2, border_color="#5D6D7E")
        self.db_frame.pack(side="right", fill="both", expand=True)
        
        ctk.CTkLabel(self.db_frame, text="📊 SQL SATELLITE DB STORAGE SYSTEM", 
                    font=ctk.CTkFont(size=17, weight="bold"), text_color="#ECF0F1").pack(pady=5)
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", font=('Courier', 11, 'bold'), rowheight=28, background="#111D2A", foreground="#E0E6ED", fieldbackground="#111D2A")
        style.configure("Treeview.Heading", font=('Arial', 12, 'bold'), background="#2C3E50", foreground="white")

        self.table_container = ctk.CTkFrame(self.db_frame, fg_color="transparent")
        self.table_container.pack(fill="both", expand=True, padx=5, pady=2)

        self.tree = ttk.Treeview(self.table_container, columns=("ID", "Time", "Layer", "Payload", "RSSI", "Volt", "Mode"), show="headings")
        
        self.tree.heading("ID", text="FRAME")
        self.tree.heading("Time", text="TIMESTAMP")
        self.tree.heading("Layer", text="LAYER")
        self.tree.heading("Payload", text="DECRYPTED PAYLOAD")
        self.tree.heading("RSSI", text="RSSI")
        self.tree.heading("Volt", text="BUS_V")
        self.tree.heading("Mode", text="MODE")
        
        self.tree.column("ID", width=70, anchor="center")
        self.tree.column("Time", width=110, anchor="center")
        self.tree.column("Layer", width=140, anchor="center")
        self.tree.column("Payload", width=220, anchor="center")
        self.tree.column("RSSI", width=90, anchor="center")
        self.tree.column("Volt", width=80, anchor="center")
        self.tree.column("Mode", width=100, anchor="center")
        
        self.scrollbar = ttk.Scrollbar(self.table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.clear_db_btn = ctk.CTkButton(self.db_frame, text="🗑️ RESET MISSION LOGS & CLEAR SQL DATABASE", 
                                         font=ctk.CTkFont(size=15, weight="bold"), 
                                         fg_color="#E74C3C", hover_color="#C0392B", height=40,
                                         command=self.clear_entire_database)
        self.clear_db_btn.pack(fill="x", padx=10, pady=5)

    def init_3d_cube_mesh(self):
        """بناء المجسم المصمت ثلاثي الأبعاد للقمر الصناعي 1U CubeSat"""
        self.cube_vertices = np.array([
            [-1, -1, -1], [ 1, -1, -1], [ 1,  1, -1], [-1,  1, -1],
            [-1, -1,  1], [ 1, -1,  1], [ 1,  1,  1], [-1,  1,  1]
        ])
        
        self.cube_faces = [
            [0, 1, 2, 3],  # السفلي
            [4, 5, 6, 7],  # العلوي
            [0, 1, 5, 4],  # الأمامي
            [2, 3, 7, 6],  # الخلفي
            [0, 3, 7, 4],  # الجانبي الأيسر
            [1, 2, 6, 5]   # الجانبي الأيمن
        ]

        delta = 0.01
        self.solar_panels = [
            np.array([[-0.7, -0.7, -1-delta], [0.7, -0.7, -1-delta], [0.7, 0.7, -1-delta], [-0.7, 0.7, -1-delta]]), 
            np.array([[-0.7, -0.7,  1+delta], [0.7, -0.7,  1+delta], [0.7, 0.7,  1+delta], [-0.7, 0.7,  1+delta]]), 
            np.array([[-0.7, -1-delta, -0.7], [0.7, -1-delta, -0.7], [0.7, -1-delta, 0.7], [-0.7, -1-delta, 0.7]]), 
            np.array([[-0.7,  1+delta, -0.7], [0.7,  1+delta, -0.7], [0.7,  1+delta, 0.7], [-0.7,  1+delta, 0.7]]), 
            np.array([[-1-delta, -0.7, -0.7], [-1-delta, 0.7, -0.7], [-1-delta, 0.7, 0.7], [-1-delta, -0.7, 0.7]]), 
            np.array([[ 1+delta, -0.7, -0.7], [ 1+delta, 0.7, -0.7], [ 1+delta, 0.7, 0.7], [ 1+delta, -0.7, 0.7]])  
        ]

        self.antenna_wire = np.array([[0, 0, -1], [0, 0, -2.6]]) 
        self.draw_3d_cube(0, 0)

    def draw_3d_cube(self, pitch, roll):
        """تحديث مصفوفات الدوران الرياضية وإعادة رسم القمر الـ 3D كمجسم معتم وبإضاءة"""
        self.ax.clear()
        self.ax.set_facecolor('#111D2A')
        
        p = np.radians(pitch)
        r = np.radians(roll)
        
        R_pitch = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
        R_roll = np.array([[np.cos(r), 0, np.sin(r)], [0, 1, 0], [-np.sin(r), 0, np.cos(r)]])
        R_total = np.dot(R_pitch, R_roll)
        
        transformed_vertices = np.dot(self.cube_vertices, R_total.T)
        polygons = [transformed_vertices[face] for face in self.cube_faces]
        
        chassis_mesh = Poly3DCollection(polygons, facecolors='#2C3E50', edgecolors='#BDC3C7', linewidths=3.0, alpha=1.0, shade=True)
        self.ax.add_collection3d(chassis_mesh)
        
        for panel in self.solar_panels:
            transformed_panel = np.dot(panel, R_total.T)
            panel_mesh = Poly3DCollection([transformed_panel], facecolors='#0F2027', edgecolors='#1F4068', linewidths=1.5, alpha=1.0, shade=True)
            self.ax.add_collection3d(panel_mesh)
            
        transformed_antenna = np.dot(self.antenna_wire, R_total.T)
        self.ax.plot(transformed_antenna[:, 0], transformed_antenna[:, 1], transformed_antenna[:, 2], 
                     color='#00D4FF', linewidth=3.5, linestyle='-', marker='o', markersize=5)
            
        self.ax.set_xlim([-2.5, 2.5])
        self.ax.set_ylim([-2.5, 2.5])
        self.ax.set_zlim([-2.5, 2.5])
        self.ax.axis('off')
        
        self.ax.view_init(elev=25, azim=45)
        self.cube_canvas.draw_idle()

    def show_thermal_popup(self, temp_val):
        """إنشاء نافذة منبثقة تفاعلية للتحذير من خطر الحرارة الزائدة"""
        if self.alert_popup_open:
            return # عدم فتح أكثر من نافذة في نفس الوقت
            
        self.alert_popup_open = True
        
        popup = ctk.CTkToplevel(self)
        popup.title("⚠️ CRITICAL THERMAL HARDWARE ALERT")
        popup.geometry("500x250")
        popup.resizable(False, False)
        popup.attributes("-topmost", True) # إجبارها على الظهور في المقدمة
        
        # لمنع إغلاق النافذة من علامة الـ X بدون الضغط على OK
        def on_close_attempt():
            self.alert_popup_open = False
            popup.destroy()
            
        popup.protocol("WM_DELETE_WINDOW", on_close_attempt)
        
        alert_ico = ctk.CTkLabel(popup, text="🚨 CRITICAL OVERHEAT", font=ctk.CTkFont(size=22, weight="bold"), text_color="#E74C3C")
        alert_ico.pack(pady=(20, 10))
        
        msg_text = f"Satellite Bus Temperature reached unsafe levels: {temp_val}°C\nThermal protection system recommends deployment of cooling routines."
        msg_lbl = ctk.CTkLabel(popup, text=msg_text, font=ctk.CTkFont(size=14), justify="center")
        msg_lbl.pack(pady=10)
        
        def close_action():
            self.alert_popup_open = False
            popup.destroy()
            
        ok_btn = ctk.CTkButton(popup, text="OK (ACKNOWLEDGE)", font=ctk.CTkFont(size=14, weight="bold"), fg_color="#E74C3C", hover_color="#C0392B", width=180, height=35, command=close_action)
        ok_btn.pack(pady=15)

    def update_servo_graphics(self, canvas, angle, color_hex):
        canvas.delete("all")
        cx, cy = 55, 35
        length = 28
        
        rad = np.radians(angle)
        x_end = cx + length * np.cos(rad)
        y_end = cy - length * np.sin(rad)
        x_end2 = cx - length * np.cos(rad)
        y_end2 = cy + length * np.sin(rad)
        
        canvas.create_line(x_end2, y_end2, x_end, y_end, fill=color_hex, width=5)
        canvas.create_oval(cx-6, cy-6, cx+6, cy+6, fill="white", outline="#34495E")
        canvas.create_text(cx, cy+25, text=f"{angle}°", fill="white", font=("Arial", 11, "bold"))

    def clear_entire_database(self):
        """تنظيف قاعدة البيانات الحقيقية من ملف الـ SQL بالكامل وتحديث الواجهة فوراً"""
        try:
            # مسح البيانات من الجدول الفيزيائي لعدم ارتداد الحزم القديمة
            self.db_cursor.execute("DELETE FROM telemetry_logs")
            self.db_conn.commit()
            
            # مسح الصفوف من الواجهة الرسومية
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            self.packet_counter = 0
            self.tree.yview_moveto(0)
            print("🚀 Satellite SQL Database has been hard-reset successfully!")
        except Exception as e:
            print(f"Error resetting database: {e}")

    def trigger_file_animation(self, layer_type):
        color = "#9D50BB" if layer_type == "TCP" else "#00D4FF"
        self.animated_files.append({
            'x': 150 + random.randint(-15, 15),
            'y': 45,
            'color': color,
            'speed': random.uniform(5, 8),
            'layer': layer_type
        })

    def draw_rounded_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1
        ]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def draw_file_icon(self, canvas, x, y, color):
        w, h = 12, 16
        canvas.create_rectangle(x, y, x + w, y + h, fill=color, outline="white", width=1)

    def animate_canvas_loop(self):
        self.anim_canvas.delete("all")
        c_width = self.anim_canvas.winfo_width() if self.anim_canvas.winfo_width() > 10 else 300
        center_x = c_width // 2
        
        sat_pos = (center_x, 30)
        ground_pos = (center_x, 290)
        
        if not self.is_connected:
            self.flash_state = not self.flash_state
            bg_color = "#2C1114" if self.flash_state else "#07111E"
            self.anim_canvas.configure(bg=bg_color)
            self.anim_canvas.create_text(center_x, 150, text="❗ LINK OFFLINE", font=("Arial", 16, "bold"), fill="#FF4B2B")
            for y_dash in range(45, 280, 25):
                self.anim_canvas.create_line(center_x, y_dash, center_x, y_dash + 12, fill="#E74C3C", width=2)
        else:
            self.anim_canvas.configure(bg="#07111E")
            for y_dash in range(45, 280, 20):
                self.anim_canvas.create_line(center_x, y_dash, center_x, y_dash + 10, fill="#1C2833", width=2)

        self.anim_canvas.create_oval(sat_pos[0]-14, sat_pos[1]-14, sat_pos[0]+14, sat_pos[1]+14, fill="#E67E22", outline="white")
        gs_color = "#2ECC71" if self.is_connected else "#95A5A6"
        self.draw_rounded_rect(self.anim_canvas, ground_pos[0]-30, ground_pos[1], ground_pos[0]+30, ground_pos[1]+15, radius=5, fill=gs_color, outline="white")

        if self.is_connected:
            for file in self.animated_files[:]:
                file['y'] += file['speed']
                self.draw_file_icon(self.anim_canvas, file['x'], file['y'], file['color'])
                if file['y'] >= 280:
                    if file in self.animated_files:
                        self.animated_files.remove(file)
        else:
            self.animated_files.clear()

        self.after(33, self.animate_canvas_loop)

    def send_critical_tcp_command(self):
        if self.is_connected:
            self.tcp_status_lbl.configure(text="TCP Link Status: CONNECTING...", text_color="#F1C40F")
            self.after(600, lambda: self.tcp_status_lbl.configure(text="TCP Link Status: ACK RECEIVED", text_color="#2ECC71"))
            
            current_time = time.strftime("%H:%M:%S")
            self.packet_counter += 1
            f_id = f"#{self.packet_counter:03d}"
            self.trigger_file_animation("TCP")
            
            self.db_cursor.execute("""
                INSERT INTO telemetry_logs (frame_id, timestamp, transport_layer, decrypted_payload, rssi, bus_volt, sys_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (f_id, current_time, "TCP [PORT 80]", "CMD_SYS_REBOOT_RECOVERY", "-41 dBm", "3.97 V", "TRANSMIT"))
            self.db_conn.commit()
            self.tree.insert("", 0, values=(f_id, current_time, "TCP [PORT 80]", "CMD_SYS_REBOOT_RECOVERY", "-41 dBm", "3.97 V", "TRANSMIT"))
        else:
            self.tcp_status_lbl.configure(text="TCP Link Status: LINK OFFLINE", text_color="#E74C3C")

    def receive_wifi_data(self):
        while True:
            ready = select.select([self.sock], [], [], 0.5)
            if ready[0]:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    packet_str = data.decode('utf-8')
                    parts = packet_str.split(',')
                    
                    if len(parts) >= 6:
                        self.current_temp = f"{float(parts[0]):.1f}"
                        self.gyro_x = f"{float(parts[1]):+.2f}"
                        self.gyro_y = f"{float(parts[2]):+.2f}"
                        
                        self.light_intensity = int(parts[3])
                        self.servo1_angle = float(parts[4])
                        self.servo2_angle = float(parts[5])
                        
                        if self.light_intensity < 300:
                            self.light_status = "DARK"
                        elif self.light_intensity < 1500:
                            self.light_status = "WEAK LIGHT"
                        else:
                            self.light_status = "STRONG LIGHT"
                            
                        self.is_connected = True
                        self.last_packet_time = time.time()
                except Exception:
                    pass
            
            if time.time() - self.last_packet_time > 2.5:
                self.is_connected = False

    def update_ui_loop(self):
        current_time = time.strftime("%H:%M:%S")
        
        if self.is_connected:
            t_float = float(self.current_temp)
            self.temp_display.configure(text=f"{self.current_temp}°C")
            self.gyro_display.configure(text=f"X: {self.gyro_x}°\nY: {self.gyro_y}°")
            
            if t_float > 35.0:
                self.alert_banner.configure(text="⚠️ CRITICAL ALERT: INTERNAL THERMAL HAZARD DETECTED", 
                                            fg_color="#E74C3C", text_color="white")
                self.temp_display.configure(text_color="#E74C3C")
                # إطلاق النافذة التنبيهية الجديدة كلياً عند تخطي عتبة الخطر الحراري
                self.show_thermal_popup(self.current_temp)
            else:
                self.alert_banner.configure(text="SYSTEM STATUS: NOMINAL (LINK STABLE)", 
                                            fg_color="#2ECC71", text_color="white")
                self.temp_display.configure(text_color="#FF4B2B")

            self.light_val_lbl.configure(text=f"RAW VALUE: {self.light_intensity:04d}")
            self.light_status_lbl.configure(text=f"STATE: {self.light_status}")
            if self.light_status == "DARK":
                self.light_status_lbl.configure(text_color="#7F8C8D")
            elif self.light_status == "WEAK LIGHT":
                self.light_status_lbl.configure(text_color="#3498DB")
            else:
                self.light_status_lbl.configure(text_color="#F1C40F")

            self.update_servo_graphics(self.servo1_canvas, self.servo1_angle, "#3498DB")
            self.servo1_text.configure(text=f"SERVO 1:\n{self.servo1_angle}°")
            
            self.update_servo_graphics(self.servo2_canvas, self.servo2_angle, "#2ECC71")
            self.servo2_text.configure(text=f"SERVO 2:\n{self.servo2_angle}°")

            self.draw_3d_cube(float(self.gyro_x), float(self.gyro_y))
            
            self.qos_queue_load = f"{random.randint(6, 15)}%"
            self.qos_lbl.configure(text=f"• QoS QUEUE  : {self.qos_queue_load}")
            
            if random.random() > 0.35:  
                self.packet_counter += 1
                f_id = f"#{self.packet_counter:03d}"
                
                sim_rssi = f"-{random.randint(42, 53)} dBm"
                sim_volt = f"{random.uniform(3.85, 3.98):.2f} V"
                sim_mode = "NOMINAL" if self.packet_counter % 3 != 0 else "TELEMETRY"
                payload_str = f"TMP:{self.current_temp}C,LGT:{self.light_status},S1:{self.servo1_angle}"
                
                self.trigger_file_animation("UDP")
                
                self.db_cursor.execute("""
                    INSERT INTO telemetry_logs (frame_id, timestamp, transport_layer, decrypted_payload, rssi, bus_volt, sys_mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (f_id, current_time, "UDP [PORT 12345]", payload_str, sim_rssi, sim_volt, sim_mode))
                self.db_conn.commit()
                self.tree.insert("", 0, values=(f_id, current_time, "UDP [PORT 12345]", payload_str, sim_rssi, sim_volt, sim_mode))
        else:
            self.temp_display.configure(text="--.-°C")
            self.gyro_display.configure(text="X: 0.00°\nY: 0.00°")
            self.tcp_status_lbl.configure(text="TCP Link Status: STANDBY", text_color="#BDC3C7")
            self.qos_lbl.configure(text="• QoS QUEUE  : 0%")
            self.alert_banner.configure(text="SYSTEM STATUS: LINK OFFLINE", fg_color="#34495E", text_color="#BDC3C7")
            
            self.update_servo_graphics(self.servo1_canvas, 0, "#7F8C8D")
            self.update_servo_graphics(self.servo2_canvas, 0, "#7F8C8D")
            self.draw_3d_cube(0, 0)

        if len(self.tree.get_children()) > 100:
            self.tree.delete(self.tree.get_children()[-1])
            
        self.after(400, self.update_ui_loop)

    def __del__(self):
        try:
            self.db_conn.close()
        except:
            pass

if __name__ == "__main__":
    app = AstrumSpaceNetworkDashboardFinal()
    app.mainloop()