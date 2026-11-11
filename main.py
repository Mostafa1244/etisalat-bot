# CRASH_HANDLER_ADDED
import traceback
from kivy.app import App
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.core.window import Window

try:
    import app_core
    # إذا كان الكود الأصلي لا يبدأ تلقائياً بسبب تغير __name__، نقوم بتشغيل كلاس App الموجود فيه
    for obj_name in dir(app_core):
        obj = getattr(app_core, obj_name)
        if isinstance(obj, type) and issubclass(obj, App) and obj is not App:
            if __name__ == '__main__':
                obj().run()
            break
except Exception:
    err_msg = traceback.format_exc()
    class CrashApp(App):
        def build(self):
            Window.clearcolor = (0.15, 0, 0, 1)
            sv = ScrollView( do_scroll_x=False )
            lbl = Label(
                text="⚠️ Crash Traceback:\n\n" + err_msg,
                size_hint_y=None,
                padding=(20, 20),
                color=(1, 0.8, 0.8, 1),
                font_size='13sp'
            )
            lbl.bind(
                width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None)),
                texture_size=lambda *x: lbl.setter('height')(lbl, lbl.texture_size[1])
            )
            sv.add_widget(lbl)
            return sv
    if __name__ == '__main__':
        CrashApp().run()
