import sys, requests, pickle
import logging
from lxml import html, etree
import cssutils
from colour import Color

main_url = 'https://www.mvg.de'

to_init = True

css_url = None

type_dict = {
    "walk": dict(icon="icons/walk.svg", color='#ffffff', background='')
}

line_dict = {
    '': dict(background='', color='')
}

image_url = None

css_file_string = None

css_rules_filtered = []

def init():
    global to_init
    global type_dict
    global line_dict
    if to_init:
        type_dict = load_obj('type_dict')
        line_dict = load_obj('line_dict')
        to_init = False

def get_css_string():
    global css_file_string
    if css_file_string is None:
        resp = requests.get(main_url)
        page = html.fromstring(resp.text)
        for css_path in page.xpath('//link[@rel="stylesheet"][@type="text/css"]/@href'):
            if not 'bundle' in css_path:
                continue
            global css_url
            css_url = main_url + css_path
            css_url = css_url[:css_url.rfind("/") + 1]
            css_resp = requests.get(main_url + css_path)
            if css_resp.status_code != 200:
                raise Exception("CSS file could not be loaded")
            css_file_string = css_resp.text
            filter_css_rule()
    return css_file_string

def filter_css_rule():
    cssutils.log.setLevel(logging.CRITICAL)
    global css_rules_filtered
    sheet = cssutils.parseString(get_css_string())
    for rule in sheet:
        if rule.type == rule.STYLE_RULE and ('transport-number' in rule.selectorText or 'transport-type' in rule.selectorText):
            css_rules_filtered.append(rule)

def treat_background(background_prop):
    properties = {}
    if 'url(' in background_prop:
        properties['icon'] = background_prop[background_prop.index('(')+1: background_prop.index(')')]
        get_image(properties['icon'])
        properties['icon'] = properties['icon'][properties['icon'].rfind('/')+1:]
    for part in background_prop.split():
        if check_color(part):  
            properties['background'] = part
    return properties


def check_color(color):
    try:
        # Converting 'deep sky blue' to 'deepskyblue'
        color = color.replace(" ", "")
        Color(color)
        # if everything goes fine then return True
        return True
    except ValueError: # The color code was not found
        return False



def get_selector_property(qselector, qproperty, pvalue=''):
    global css_file_string
    if css_file_string is None:
        get_css_string()
    values = []
    qselector = '.' + qselector
    for rule in css_rules_filtered:
        if (qselector + ' ' in rule.selectorText or rule.selectorText.endswith(qselector)):
            if qproperty in rule.style:
                value = rule.style[qproperty]
                if pvalue in value:
                    values.append(value)
    return None if len(values) == 0 else values[-1]



def get_image(rel_path):
    resp = requests.get(css_url + rel_path)
    with open('icons/' + rel_path[rel_path.rfind('/')+1:], 'w') as svg:
        svg.write(resp.text)
        svg.close()

def load_type_style(typee):
    type_style = {}
    icon_style = get_selector_property(typee, 'background', 'url(' )
    #type_style['icon'] = icon_style[icon_style.index('(')+1: icon_style.index(')')]
    #get_image(type_style['icon'])
    #type_style['icon'] = type_style['icon'][type_style['icon'].rfind('/')+1:]
    #type_style['background'] = icon_style.split()[-1]
    type_style.update(treat_background(icon_style))
    color = get_selector_property(typee, 'color')
    if color != None:
        type_style['color'] = color
    return type_style

def load_line_style(line):
    line_style = {}
    background = get_selector_property(line, 'background')
    color = get_selector_property(line, 'color')
    if background != None:
        line_style.update(treat_background(background))
    if color != None:
        line_style['color'] = get_selector_property(line, 'color')
    return line_style

def get_line_style(line):
    init()
    if not line in line_dict:
        line_dict[line] = load_line_style(line)
        save_obj(line_dict, 'line_dict')
    return line_dict[line].copy()

def get_type_style(typee):
    init()
    if not typee in type_dict:
        type_dict[typee] = load_type_style(typee)
        save_obj(type_dict, 'type_dict')
    return type_dict[typee].copy()

def save_obj(obj, name ):
    with open('obj/'+ name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name ):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)

def get_style(typee, line):
    style = get_type_style(typee)
    style.update(get_line_style(line))
    return style

def get_css_style(typee, line):
    if typee == 's' or typee == 'u' or typee == 't':
        line = typee + line
    return get_style(typee, line)


                
def main(argv):
    if len(argv) % 2 == 0:
        print("Error:    No, or pairs of two types and lines should be provided")
        exit()
    for i in range(0, len(argv)):
        if i % 2 == 0:
            continue
        print(str(argv[i]) + " "+ str(argv[i + 1]) + " " + str(get_style(argv[i], argv[i + 1])))

if __name__ == "__main__":
    main(sys.argv)