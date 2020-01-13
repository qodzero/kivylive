
from .view import Catalog
from kivy.app import App

class MainApp(App):
    def build(self):
        return Catalog()
