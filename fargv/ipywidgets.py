import re


# we want to raise an exception when using the ipywidgets functions instead of import time
try:
    import ipywidgets
    from IPython.display import display
except ImportError:
    ipywidgets = None
    display = None


class FargvIpywidget:
    def __init__(self, key, value):
        self.key = key
        descr = key.split("_")
        self.descr = " ".join([i[0].upper()+i[1:] for i in descr])
        self.default_value = value
        self.root_widget, self.value_widget = self.create_widgets()
        self.value_widget.set_value(value)

    @property
    def description(self):
        res = self.key.split("_")
        return " ".join([i[0].upper()+i[1:] for i in res])
    
    @property
    def value(self):
        return self.value_widget.value

    @property
    def key(self):
        return self.key

    def create_widgets(self):
        raise NotImplementedError
    
    def set_value(self, value):
        self.value_widget.value = value

    def get_value(self):
        return self.value_widget.value
    
        

class FargvIpywidgetBool(FargvIpywidget):
    def __init__(self, key, value):
        super().__init__(key, value)
    
    def create_widgets(self):
        checkbox = ipywidgets.Checkbox(value=self.default_value, description=self.description, default=self.default_value)
        hbox = ipywidgets.HBox([ipywidgets.Label(value=self.descr), checkbox])
        return hbox, checkbox


class FargvIpywidgetText(FargvIpywidget):
    def __init__(self, key, value):
        super().__init__(key, value)
    
    def create_widgets(self):
        textbox = ipywidgets.Text(value=self.default_value, description=self.description, default=self.default_value)
        hbox = ipywidgets.HBox([ipywidgets.Label(value=self.descr), textbox])
        return hbox, textbox


class FargvIpywidgetInt(FargvIpywidget):
    def __init__(self, key, value):
        super().__init__(key, value)
    
    def create_widgets(self):
        textbox = ipywidgets.Text(value=str(self.default_value), description=self.description, default=self.default_value)
        validation_message = ipywidgets.HTML()
        textbox_re = r"^[0-9]+$"
        wrong_message = f'<span style="color: red;">Expecting an Integer</span>'
        correct_message = f'<span style="color: black;">Integer</span>'

        def validate_textbox(change):
            textbox_value = change['new']
            # Perform validation logic
            if re.match(textbox_re, textbox_value):
                validation_message.value = correct_message
            else:
                validation_message.value = wrong_message
        
        textbox.observe(validate_textbox, 'value')
        hbox = ipywidgets.HBox([ipywidgets.Label(value=self.descr), textbox, validation_message])
        return hbox, textbox


class FargvIpywidgetFloat(FargvIpywidget):
    def __init__(self, key, value):
        super().__init__(key, value)
    
    def create_widgets(self):
        textbox = ipywidgets.Text(value=str(self.default_value), description=self.description, default=self.default_value)
        validation_message = ipywidgets.HTML()
        textbox_re = r"^[0-9]+(\.[0-9]+)?$"
        wrong_message = f'<span style="color: red;">Expecting a Float</span>'
        correct_message = f'<span style="color: black;">Float</span>'

        def validate_textbox(change):
            textbox_value = change['new']
            # Perform validation logic
            if re.match(textbox_re, textbox_value):
                validation_message.value = correct_message
            else:
                validation_message.value = wrong_message
        
        textbox.observe(validate_textbox, 'value')
        hbox = ipywidgets.HBox([ipywidgets.Label(value=self.descr), textbox, validation_message])
        return hbox, textbox
        

def parse_ipywidget(p:dict):
    keys2widgets={}
    for k, v in p.items():
        if isinstance(v, bool):
            keys2widgets[k] = FargvIpywidgetBool(k, v)
        elif isinstance(v, int):
            keys2widgets[k] = FargvIpywidgetInt(k, v)
        elif isinstance(v, float):
            keys2widgets[k] = FargvIpywidgetFloat(k, v)
        elif isinstance(v, str):
            keys2widgets[k] = FargvIpywidgetText(k, v)
    
    class IpywidgetParser:
        def __init__(self, keys2widgets):
            self.keys2widgets = keys2widgets
            self.root_widget = ipywidgets.VBox([v.root_widget for v in self.widgets.values()])
            display(self.root_widget)
        
        def __getitem__(self, key):
            return self.keys2widgets[key].get_value()
        
    for k, v in keys2widgets.items():
        setattr(IpywidgetParser, k, property(lambda self: self.keys2widgets[k].get_value()))
    
    return IpywidgetParser(keys2widgets)


def render_ipywidget(p:dict):
    if ipywidgets is None:
        raise ImportError("ipywidgets and or IPython is not installed")
    widgets = []
    for key, value in p.items():
        descr = key.split("_")
        descr = " ".join([i[0].upper()+i[1:] for i in descr])
        if isinstance(value, bool):            
            widgets.append(ipywidgets.Checkbox(value=value, description=key, default=value))
        
        elif isinstance(value, int) or isinstance(value, float) or isinstance(value, str):

            textbox = ipywidgets.Text(value=str(value), description=descr)
            validation_message = ipywidgets.HTML()

            if isinstance(value, str):
                textbox_re = r"^.*$"
                validator = lambda change: re.match(textbox_re, change['new'])
                wrong_message = f'<span style="color: red;">Expecting a String</span>'
                correct_message = f'<span style="color: black;">String</span>'
            elif isinstance(value, int):
                textbox_re = r"^[0-9]+$"
                wrong_message = f'<span style="color: red;">Expecting an Integer</span>'
                correct_message = f'<span style="color: black;">Integer</span>'
            elif isinstance(value, float):
                textbox_re = r"^[0-9]+(\.[0-9]+)?$"
                wrong_message = f'<span style="color: red;">Expecting a Float</span>'
                correct_message = f'<span style="color: black;">Float</span>'



            def validate_textbox(change):
                textbox_value = change['new']
                # Perform validation logic
                if re.match(textbox_re, textbox_value):
                    validation_message.value = correct_message
                else:
                    validation_message.value = wrong_message
            
            textbox.observe(validate_textbox, 'value')
            widgets.append(ipywidgets.VBox([ipywidgets.Label(value=descr), textbox, validation_message]))
    display(ipywidgets.VBox(widgets))
