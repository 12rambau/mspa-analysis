import os

from bqplot import *
import ipywidgets as widgets
import ipyvuetify as v
from sepal_ui import mapping as sm
from matplotlib.colors import ListedColormap, to_hex, to_rgba
from matplotlib import pyplot as plt
import rasterio as rio

from utils import parameter as pm

def fragmentationMap(raster, output):
    output.add_live_msg('Displaying results')
    
    map_ = sm.SepalMap()
    
    # read the raster 
    with rio.open(raster) as src:
        
        data = src.read()
        
        min_ = int(np.amin(data[0]))
        max_ = int(np.amax(data[0]))
        ct = src.colormap(1)
        
        #extract the corners coordinates
        min_lon =  src.bounds.left
        max_lat = src.bounds.top
        max_lon = src.bounds.right
        min_lat = src.bounds.bottom

    # extract a color map  
    color_map = []
    for i in range(min_, max_+1):
    
        #hide no-data: 
        if list(ct[i]) == pm.mspa_colors['no-data']:
            color_map.append([.0, .0, .0, .0])
        else:
            color_map.append([val/255 for val in list(ct[i])])

    color_map = ListedColormap(color_map, N=max_)

    #display a raster on the map
    map_.add_raster(raster, colormap=color_map, layer_name='framgmentation map');

    #add a legend 
    legend_keys = [index for index in pm.mspa_colors]
    legend_colors = [to_hex([val/255 for val in pm.mspa_colors[index]]) for index in pm.mspa_colors] 
    map_.add_legend(legend_keys=legend_keys, legend_colors=legend_colors, position='topleft')
    
    map_.set_center((max_lon+min_lon)/2,(max_lat + min_lat)/2)
    
    tl = (max_lat, min_lon)
    bl = (min_lat, min_lon)
    tr = (max_lat, max_lon)
    br = (min_lat, max_lon)
    
    map_.zoom_bounds(bounds=[tl, bl, tr, br])
    
    output.add_live_msg('Mspa process complete', 'success')
    
    return map_

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
    
def exportLegend(filename):
    
    #create a color list
    color_map = []
    for index in pm.mspa_colors: 
        color_map.append([val/255 for val in list(pm.mspa_colors[index])])

    columns = ['entry']
    rows = [' '*10 for index in pm.mspa_colors] #trick to see the first column
    cell_text = [[index] for index in pm.mspa_colors]

    fig, ax = plt.subplots(1,1)

    #remove the graph box
    ax.axis('tight')
    ax.axis('off')

    #set the tab title
    ax.set_title('Raster legend')

    #create the table
    the_table = ax.table(
        colColours=[to_rgba('lightgrey')],
        cellText=cell_text,
        rowLabels=rows,
        colWidths=[.4],
        rowColours=color_map,
        colLabels=columns,
        loc='center'
    )
    the_table.scale(1, 1.5)

    #save &close
    plt.savefig(filename)
    plt.close()
    
    return

