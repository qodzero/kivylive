
from .view import Catalog
try:
    from kivymd.app import MDApp
    class MainApp(MDApp):
        def build(self):
            return Catalog()
except:
    from kivy.app import App

    class MainApp(App):
        def build(self):
            return Catalog()
