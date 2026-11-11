from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.core.text import LabelBase
from threading import Thread, Event
import time, requests, base64, json, re, hashlib, urllib.parse, xml.etree.ElementTree as ET
import urllib3
import arabic_reshaper
from bidi.algorithm import get_display

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# دالة إصلاح النص العربي
def ar(text):
    if not text:
        return text
    return get_display(arabic_reshaper.reshape(str(text)))

# تسجيل الخط العربي
LabelBase.register(name='Arabic', fn_regular='Amiri-Regular.ttf')

BASE_URL = "https://mab.etisalat.com.eg:11003"
DEVICE_ID = "b61c90c58c612671"
PLAN_IDS = {
    "Hekaya_XRP_MIX_Parent_7": ("حكاية ميكسات 270", "270"),
    "Hekaya_XRP_MIX_Parent_6": ("حكاية ميكسات 180", "180"),
}

class EtisalatAPI:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.current_dial = None
        self.email = None
        self.password = None
        self.base_headers = {
            "applicationVersion": "2", "applicationName": "MAB", "Accept": "text/xml",
            "Language": "ar", "APP-BuildNumber": "10744", "APP-Version": "36.1.0",
            "OS-Type": "Android", "OS-Version": "16", "APP-STORE": "GOOGLE",
            "C-Type": "WIFI", "Is-Corporate": "false", "User-Agent": "okhttp/5.0.0-alpha.11",
            "Content-Type": "text/xml; charset=UTF-8",
        }

    def _sign(self, url_path, body_xml):
        h = hashlib.sha256(f"{url_path}{DEVICE_ID}".encode()).hexdigest()
        u = hashlib.sha256(url_path.encode()).hexdigest()
        b = hashlib.sha256(body_xml.encode()).hexdigest() if body_xml else ""
        return h, u, b

    def login(self, email, password):
        self.email, self.password = email, password
        auth_b64 = base64.b64encode(f"{email}:{password}".encode()).decode()
        for attempt in range(3):
            headers = self.base_headers.copy()
            headers["Authorization"] = f"Basic {auth_b64}"
            login_xml = (
                "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
                f"<loginRequest><deviceId>{DEVICE_ID}</deviceId><firstLoginAttempt>true</firstLoginAttempt>"
                "<modelType>CPH2737</modelType><osVersion>16</osVersion>"
                f"<platform>Android</platform><udid>{DEVICE_ID}</udid></loginRequest>"
            )
            url_path = "/Saytar/rest/authentication/loginWithPlan"
            h, u, b = self._sign(url_path, login_xml)
            headers.update({"headerSignature": h, "urlSignature": u, "bodySignature": b})
            try:
                r = self.session.post(BASE_URL + url_path, headers=headers, data=login_xml, timeout=15)
                if r.status_code == 200 and "<status>true</status>" in r.text:
                    self.auth_token = r.headers.get("auth")
                    if self.auth_token:
                        self.base_headers["auth"] = f"Bearer {self.auth_token}"
                        try:
                            root = ET.fromstring(r.text)
                            d = root.find(".//dial")
                            self.current_dial = d.text if d is not None else None
                        except Exception: pass
                        return True
            except Exception: pass
            time.sleep(3)
        return False

    def get_status_and_child(self):
        xml_body = (
            "<dialAndLanguageRequest><segmentId>XRP</segmentId>"
            f"<subscriberNumber>{self.current_dial}</subscriberNumber>"
            "<language>1</language><shortCode>ALFTL</shortCode></dialAndLanguageRequest>"
        )
        enc = urllib.parse.quote(xml_body)
        url_path = f"/Saytar/rest/servicemanagement/getGenericConsumptionsV2?requestParam={enc}"
        headers = self.base_headers.copy()
        h, u, _ = self._sign(url_path, "")
        headers.update({"headerSignature": h, "urlSignature": u})
        try:
            r = self.session.get(BASE_URL + url_path, headers=headers, timeout=12)
            if r.status_code != 200: return None, 0, None
            text = r.text
            p_id = "Unknown"
            for key in PLAN_IDS:
                if key in text: p_id = key; break
            r_mix = 0
            vals = [int(float(m.group(1))) for m in re.finditer(r"<remainingValue>(.*?)</remainingValue>", text) if m.group(1).strip().replace('.','',1).isdigit()]
            if vals: r_mix = max(vals)
            child = None
            for m in re.finditer(r"<fafNumberList>.*?</fafNumberList>", text, re.S):
                for val in re.findall(r"<value>(.*?)</value>", m.group(0)):
                    if val.strip() and val.strip() != self.current_dial: child = val.strip(); break
            return p_id, r_mix, child
        except Exception: return None, 0, None

    def change_plan(self, plan_name, plan_id=""):
        url_path = "/Saytar/rest/HekayaPartial/migrate"
        xml_body = (
            "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
            "<migrateRequest><addonName></addonName><oMSRatePlan>true</oMSRatePlan>"
            "<operation>FULL_MIGRATE</operation>"
            f"<productName>{plan_name}</productName><ratePlanID>{plan_id}</ratePlanID>"
            f"<subscriberNumber>{self.current_dial}</subscriberNumber></migrateRequest>"
        )
        headers = self.base_headers.copy()
        h, u, b = self._sign(url_path, xml_body)
        headers.update({"headerSignature": h, "urlSignature": u, "bodySignature": b})
        try:
            r = self.session.post(BASE_URL + url_path, headers=headers, data=xml_body, timeout=15)
            return r.status_code == 200 and "<status>true</status>" in r.text
        except Exception: return False

    def transfer_mix(self, receiver, quota, product):
        url_path = "/Saytar/rest/services/newTransfer/v2"
        xml_body = (
            "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
            "<newFamilyTransferRequest><distribute>false</distribute>"
            f"<msisdn>{self.current_dial}</msisdn><productName>{product}</productName>"
            f"<quota>{int(quota)}</quota><receiverMsisdn>{receiver}</receiverMsisdn>"
            f"<senderMsisdn>{self.current_dial}</senderMsisdn><type>UNITS</type></newFamilyTransferRequest>"
        )
        headers = self.base_headers.copy()
        h, u, b = self._sign(url_path, xml_body)
        headers.update({"headerSignature": h, "urlSignature": u, "bodySignature": b})
        try:
            r = self.session.post(BASE_URL + url_path, headers=headers, data=xml_body, timeout=15)
            return r.status_code == 200 and "<status>true</status>" in r.text
        except Exception: return False

class RunnerApp(App):
    def build(self):
        Window.clearcolor = get_color_from_hex('#121212')
        self.layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        header = BoxLayout(orientation='vertical', size_hint_y=None, height=80)
        header.add_widget(Label(text="MOSTAFA MAHMOUD", font_size='22sp', bold=True, color=get_color_from_hex('#00FFCC')))
        header.add_widget(Label(text="WhatsApp: 01015946905 | FB: /mostafa7ot", font_size='12sp', color=get_color_from_hex('#AAAAAA')))
        self.layout.add_widget(header)
        
        self.email_primary = TextInput(hint_text=ar('إيميل الأونر'), font_name='Arabic', multiline=False, size_hint_y=None, height=45, background_color=get_color_from_hex('#333333'), foreground_color=get_color_from_hex('#FFFFFF'))
        self.password_primary = TextInput(hint_text=ar('باسورد الأونر'), font_name='Arabic', password=True, multiline=False, size_hint_y=None, height=45, background_color=get_color_from_hex('#333333'), foreground_color=get_color_from_hex('#FFFFFF'))
        self.email_secondary = TextInput(hint_text=ar('إيميل الفرد'), font_name='Arabic', multiline=False, size_hint_y=None, height=45, background_color=get_color_from_hex('#333333'), foreground_color=get_color_from_hex('#FFFFFF'))
        self.password_secondary = TextInput(hint_text=ar('باسورد الفرد'), font_name='Arabic', password=True, multiline=False, size_hint_y=None, height=45, background_color=get_color_from_hex('#333333'), foreground_color=get_color_from_hex('#FFFFFF'))
        self.target = TextInput(hint_text=ar('الهدف (ميكسات)'), font_name='Arabic', input_filter='int', multiline=False, size_hint_y=None, height=45, background_color=get_color_from_hex('#333333'), foreground_color=get_color_from_hex('#FFFFFF'))
        
        for widget in [self.email_primary, self.password_primary, self.email_secondary, self.password_secondary, self.target]:
            self.layout.add_widget(widget)

        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        self.start_btn = Button(text=ar('بدء التشغيل'), font_name='Arabic', background_color=get_color_from_hex('#00CC66'), bold=True)
        self.stop_btn = Button(text=ar('إيقاف'), font_name='Arabic', background_color=get_color_from_hex('#CC0000'), bold=True)
        self.start_btn.bind(on_press=self.start_bot)
        self.stop_btn.bind(on_press=self.stop_bot)
        btn_layout.add_widget(self.start_btn)
        btn_layout.add_widget(self.stop_btn)
        self.layout.add_widget(btn_layout)

        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=20)
        self.layout.add_widget(self.progress)

        self.scroll_view = ScrollView()
        self.log_label = Label(text='', font_name='Arabic', size_hint_y=None, height=0, halign='left', valign='top', color=get_color_from_hex('#00FFCC'))
        self.log_label.bind(size=self._update_log_label)
        self.scroll_view.add_widget(self.log_label)
        self.layout.add_widget(self.scroll_view)

        self.layout.add_widget(Label(text="Developed by MOSTAFA MAHMOUD 🔥", font_name='Arabic', font_size='14sp', bold=True, color=get_color_from_hex('#FF9900'), size_hint_y=None, height=30))

        self.stop_event = Event()
        self.worker_thread = None
        return self.layout

    def _update_log_label(self, instance, value):
        self.log_label.text_size = (instance.width - 10, None)
        self.log_label.height = max(instance.height, self.log_label.texture_size[1])

    def start_bot(self, instance):
        if self.worker_thread and self.worker_thread.is_alive(): return
        self.stop_event.clear()
        self.progress.value = 0
        self.log_label.text = ''
        self.worker_thread = Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self._log(ar('▶ بدء التشغيل...'))

    def stop_bot(self, instance):
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop_event.set()
            self._log(ar('⏹ تم إرسال إشارة الإيقاف...'))

    def _worker_loop(self):
        try:
            email1 = self.email_primary.text.strip()
            pass1 = self.password_primary.text.strip()
            email2 = self.email_secondary.text.strip()
            pass2 = self.password_secondary.text.strip()
            target_val = int(self.target.text) if self.target.text.isdigit() else 50000
            self._log(ar('🔐 جاري تسجيل الدخول...'))
            owner = EtisalatAPI()
            if not owner.login(email1, pass1):
                self._log(ar('❌ فشل تسجيل دخول الأونر.'))
                return
            self._log(ar(f'✅ الأونر: {owner.current_dial}'))
            child = EtisalatAPI()
            if not child.login(email2, pass2):
                self._log(ar('❌ فشل تسجيل دخول الفرد.'))
                return
            self._log(ar(f'✅ الفرد: {child.current_dial}'))
            cycle = 0
            while not self.stop_event.is_set():
                cycle += 1
                plan_id, mix_amount, child_num = owner.get_status_and_child()
                if mix_amount is None: mix_amount = 0
                self._update_progress(min(100, int((mix_amount / target_val) * 100)))
                self._log(ar(f'🔄 الدورة {cycle} | ميكس الأونر: {mix_amount:,} / {target_val:,}'))
                if mix_amount >= target_val:
                    self._log(ar(f'🎉 مبروك! تم الوصول للهدف: {mix_amount:,}'))
                    return
                if mix_amount > 0:
                    self._log(ar(f'💸 تحويل {mix_amount:,} للفرد...'))
                    owner.transfer_mix(child.current_dial, mix_amount, plan_id)
                    time.sleep(3)
                if "Parent_7" in str(plan_id):
                    self._log(ar("🔄 تغيير الباقة إلى 180..."))
                    owner.change_plan("Hekaya_XRP_MIX_Parent_6", "951")
                else:
                    self._log(ar("🔄 تغيير الباقة إلى 270..."))
                    owner.change_plan("Hekaya_XRP_MIX_Parent_7", "")
                for _ in range(60):
                    if self.stop_event.is_set(): return
                    time.sleep(1)
                _, child_mix, _ = child.get_status_and_child()
                if child_mix and child_mix > 0:
                    self._log(ar(f'💸 تحويل {child_mix:,} من الفرد للأونر...'))
                    child.transfer_mix(owner.current_dial, child_mix, "Hekaya_XRP_MIX_Child_1")
                time.sleep(5)
        except Exception as e:
            self._log(ar(f'❌ خطأ: {str(e)}'))

    @mainthread
    def _update_progress(self, value):
        self.progress.value = value

    @mainthread
    def _log(self, message):
        self.log_label.text += message + '\n'
        Clock.schedule_once(lambda dt: setattr(self.scroll_view, 'scroll_y', 0), 0.1)

if __name__ == '__main__':
    RunnerApp().run()
