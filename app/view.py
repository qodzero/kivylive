import os
import sys

import kivy
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.lang import Builder, Parser, ParserException
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.codeinput import CodeInput
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.modalview import ModalView

import pickle
from app.storage.db import Database

kivy.require('1.4.2')

CATALOG_ROOT = os.path.dirname(__file__)

# Config.set('graphics', 'width', '1024')
# Config.set('graphics', 'height', '768')

'''List of classes that need to be instantiated in the factory from .kv files.
'''
CONTAINER_KVS = os.path.join(CATALOG_ROOT, 'container_kvs')
CONTAINER_CLASSES = [c[:-3] for c in os.listdir(CONTAINER_KVS)
    if c.endswith('.kv')]


class Container(BoxLayout):
    '''A container is essentially a class that loads its root from a known
    .kv file.

    The name of the .kv file is taken from the Container's class.
    We can't just use kv rules because the class may be edited
    in the interface and reloaded by the user.
    See :meth: change_kv where this happens.
    '''

    def __init__(self, **kwargs):
        super(Container, self).__init__(**kwargs)
        self.previous_text = open(self.kv_file).read()
        parser = Parser(content=self.previous_text)
        widget = Factory.get(parser.root.name)()
        Builder._apply_rule(widget, parser.root, parser.root)
        self.add_widget(widget)

    @property
    def kv_file(self):
        '''Get the name of the kv file, a lowercase version of the class
        name.
        '''

        return os.path.join(CONTAINER_KVS, self.__class__.__name__ + '.kv')


for class_name in CONTAINER_CLASSES:
    globals()[class_name] = type(class_name, (Container,), {})


class KivyRenderTextInput(CodeInput):
    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        is_osx = sys.platform == 'darwin'
        # Keycodes on OSX:
        ctrl, cmd = 64, 1024
        key, key_str = keycode

        if text and key not in (list(self.interesting_keys.keys()) + [27]):
            # This allows *either* ctrl *or* cmd, but not both.
            if modifiers == ['ctrl'] or (is_osx and modifiers == ['meta']):
                if key == ord('s'):
                    self.catalog.change_kv(True)
                    return

        return super(KivyRenderTextInput, self).keyboard_on_key_down(
            window, keycode, text, modifiers)


class Catalog(BoxLayout):
    '''Catalog of widgets. This is the root widget of the app. It contains
    a tabbed pain of widgets that can be displayed and a textbox where .kv
    language files for widgets being demoed can be edited.

    The entire interface for the Catalog is defined in kivycatalog.kv,
    although individual containers are defined in the container_kvs
    directory.

    To add a container to the catalog,
    first create the .kv file in container_kvs
    The name of the file (sans .kv) will be the name of the widget available
    inside the kivycatalog.kv
    Finally modify kivycatalog.kv to add an AccordionItem
    to hold the new widget.
    Follow the examples in kivycatalog.kv to ensure the item
    has an appropriate id and the class has been referenced.

    You do not need to edit any python code, just .kv language files!
    '''
    language_box = ObjectProperty()
    screen_manager = ObjectProperty()
    _change_kv_ev = None

    def __init__(self, **kwargs):
        self._previously_parsed_text = ''
        super(Catalog, self).__init__(**kwargs)
        self.show_kv(None, 'New UI')
        self.carousel = None

        self.db = Database()

        all_kvs = self.db.get_kvs()

        print(len(all_kvs))
        for kv in all_kvs:
            kv = pickle.loads(kv[0])
            name = kv.rsplit(os.path.sep,1)[1].rsplit('.',1)[0]

            self.ids.recents.values.append(name)

    def replace_kv(self, *args):
        inst, val = args
        target = None

        if val == 'New UI':
            target = os.path.join(CONTAINER_KVS, 'PlaygroundContainer.kv')
        else:
            all_kvs = self.db.get_kvs()
            for kv in all_kvs:
                path = pickle.loads(kv[0])
                name = path.rsplit(os.path.sep,1)[1].rsplit('.',1)[0]
                if name == val:
                    # TODO - Allow duplicate names
                    target = path
                    break

        if target:
            try:
                with open(target, 'rb') as file:
                    self.language_box.text = file.read().decode('utf8')
                if self._change_kv_ev is not None:
                    self._change_kv_ev.cancel()

                if val == 'New UI':
                    self.ids.ui_name.text = 'Untitled*'
                else:
                    self.ids.ui_name.text = target

                self.change_kv()
                # reset undo/redo history
                self.language_box.reset_undo()

            except Exception as e:
                self.show_error(e)


    def show_kv(self, instance, value):
        '''Called when an a item is selected, we need to show the .kv language
        file associated with the newly revealed container.'''

        self.screen_manager.current = value

        child = self.screen_manager.current_screen.children[0]
        with open(child.kv_file, 'rb') as file:
            self.language_box.text = file.read().decode('utf8')
        if self._change_kv_ev is not None:
            self._change_kv_ev.cancel()
        self.change_kv()
        # reset undo/redo history
        self.language_box.reset_undo()

    def schedule_reload(self):
        if self.auto_reload:
            txt = self.language_box.text
            child = self.screen_manager.current_screen.children[0]
            if txt == child.previous_text:
                return
            child.previous_text = txt
            if self._change_kv_ev is not None:
                self._change_kv_ev.cancel()
            if self._change_kv_ev is None:
                self._change_kv_ev = Clock.create_trigger(self.change_kv, .5)
            self._change_kv_ev()

    def change_kv(self, *largs):
        '''Called when the update button is clicked. Needs to update the
        interface for the currently active kv widget, if there is one based
        on the kv file the user entered. If there is an error in their kv
        syntax, show a nice popup.'''

        txt = self.language_box.text
        kv_container = self.screen_manager.current_screen.children[0]
        try:
            parser = Parser(content=txt)
            kv_container.clear_widgets()
            widget = Factory.get(parser.root.name)()
            Builder._apply_rule(widget, parser.root, parser.root)
            kv_container.add_widget(widget)

            name = self.ids.ui_name.text
            if name == 'Untitled*':
                m = ModalView(size_hint=[.6,.7])
                box = BoxLayout(orientation='vertical')
                m.add_widget(box)

                # Function to get user's current home directory
                from os.path import expanduser
                users_home = expanduser('~')
                user_home_dir = os.path.join(users_home,'Desktop')
                try:
                    os.mkdir(os.path.join(user_home_dir,'KivyEditor'))
                    user_home_dir = os.path.join(user_home_dir, 'KivyEditor')
                except FileExistsError:
                    user_home_dir = os.path.join(user_home_dir, 'KivyEditor')
                    pass

                name_box = BoxLayout(size_hint_y=.1)
                fc = FileChooserListView(size_hint_y=.9,filters=['*kv'],rootpath=user_home_dir)

                box.add_widget(name_box)
                box.add_widget(fc)

                tinput = TextInput(multiline=False, size_hint_x=.8)
                submit = Button(text='Save', background_color=[1,1,1,1], background_normal='', color=[0,0,0,1], size_hint_x=.2)

                tinput.bind(on_text_validate=lambda x: self.update_name(os.path.join(fc.path, tinput.text), m))
                submit.bind(on_release=lambda x: self.update_name(os.path.join(fc.path, tinput.text), m))

                name_box.add_widget(tinput)
                name_box.add_widget(submit)
                m.open()

            else:
                save_path = name
                dump = pickle.dumps(save_path)
                all = self.db.get_kvs()
                kvs = [x[0] for x in all]

                if dump not in kvs:
                    self.db.add_kv(dump)
                    
                with open(save_path, 'w') as f:
                    f.write(txt)

        except (SyntaxError, ParserException) as e:
            self.show_error(e)
        except Exception as e:
            self.show_error(e)

    def update_name(self, name: str, modal):
        """Update the name of the current file

        Parameters
        ----------
        name : str
            the name of  the file to save

        modal: :class kivy.uix.modalview.ModalView
            An instance of the kivy modalview containing the name data

        Returns
        -------
        None

        """
        modal.dismiss()
        if not name.endswith('.kv'):
            name = '.'.join([name, 'kv'])

        ui_name = self.ids.ui_name
        ui_name.text = name
        new_sp_val = name.rsplit(os.path.sep,1)[1].rsplit('.',1)[0]
        self.ids.recents.values.append(new_sp_val)
        self.ids.recents.text = new_sp_val
        self.change_kv()

    def show_error(self, e):
        self.info_label.text = str(e).encode('utf-8')
        self.anim = Animation(top=190.0, opacity=1, d=2, t='in_back') +\
            Animation(top=190.0, d=3) +\
            Animation(top=0, opacity=0, d=2)
        self.anim.start(self.info_label)
