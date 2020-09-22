import os

from bqplot import *
import ipywidgets as widgets
import ipyvuetify as v

from utils import parameter as pm

def fragmentationMap(path, output):
    # TODO before I found how to display tif as interactive maps I use a simple ipywidget
    output.add_live_msg('Displaying results') 
    with open(path, 'rb') as f:
        raw_image = f.read()
    output.add_live_msg('Image read')
    output.add_live_msg('Creating the widget')
    ipyimage = widgets.Image(value=raw_image, format='tif')
    
    output.add_live_msg('Mspa process complete', 'success')
    
    return ipyimage

def getTable(stat_file):
    
    list_ = ['Core', 'Islet', 'Perforation', 'Edge', 'Loop', 'Bridge', 'Branch']
    
    #create the header
    headers = [
        {'text': 'MSPA-class', 'align': 'start', 'value': 'class'},
        {'text': 'Proportion (%)', 'value': 'prop' }
    ]
    
    #open and read the file 
    with open(stat_file, "r") as f:
        text = f.read()
    
    #split lines
    text = text.split('\n')
    
    #identify values of interes and creat the item array 
    items = []
    for value in list_:
        for line in text:
            if line.startswith(value):
                val = '{:.2f}'.format(float(line.split(':')[1][:-2]))
                items.append({'class':value, 'prop':val})
    
    
    table = v.DataTable(
        class_='ma-3',
        headers=headers,
        items=items,
        disable_filtering=True,
        disable_sort=True,
        hide_default_footer=True
    )
    
    return table
    


