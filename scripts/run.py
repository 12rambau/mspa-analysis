import os
import psutil
from sepal_ui.scripts import utils as su
from utils import messages as ms
import rasterio as rio
import numpy as np
from pathlib import Path
from utils import parameter as pm
import subprocess
import gdal
import osr
import shutil
from distutils import dir_util

def validate_file(file, output):
    
    #check that the file exist
    if not os.path.isfile(file):
        su.displayIO(output, ms.WRONG_FILE.format(file), 'error')
        return None
    
    #check that the file is a tif 
    if not file.lower().endswith(('.tif', '.tiff')):
        su.displayIO(output, ms.WRONG_FILE_TYPE.format(file), 'error')
        return None
    
    #check the file size 
    if  os.path.getsize(file) > psutil.virtual_memory()[1]/2: #available memory
        su.displayIO(output, ms.TOO_BIG, 'error')
        return None
    
    #readt the file 
    with rio.open(file) as src:
        info = src.read(1, masked=True)

    #extract the frequency of each value 
    array = np.array(info.ravel())
    values = np.unique(array)
    
    return values

def set_bin_map(raster, values, forest, nforest, output):
    """ transfor the raster into a binary map
    (2) for all the bands in forest
    (1) for all the bands in non forest 
    (0) for the rest 
    """
    
    filename = Path(raster).stem
    
    bin_map = pm.getResultDir() + filename + '_bin_map.tif'
    
    if os.path.isfile(bin_map):
        su.displayIO(output, ms.BIN_MAP_READY, 'success')
        return bin_map
    
    calc = ''
    for index, val in enumerate(values):
        if val in forest: 
            calc += '(A=={})*2'.format(val)
        elif val in nforest:
            calc += '(A=={})*1'.format(val)
        else:
            calc += '(A=={})*0'.format(val)
        
        #add "+" for every val but the last one
        if index < (len(values)-1): #start at O
            calc += '+'
            
    print(calc)
            
    #create the command 
    command = [
        'gdal_calc.py',
        '-A', raster,
        '--co', '"COMPRESS=LZW"',
        '--outfile={}'.format(bin_map),
        '--calc="{}"'.format(calc),
        '--type="Byte"'
    ]
    
    print(command)
    
    #launch the process
    kwargs = {
            'args' : command,
            'stdout' : subprocess.PIPE,
            'stderr' : subprocess.PIPE,
            'universal_newlines' : True
        }
    
    with subprocess.Popen(**kwargs) as p:
        for line in p.stdout:
            su.displayIO(output, line)
            
    su.displayIO(output, ms.END_BIN_MAP)
    
    return bin_map

def mspa_analysis(bin_map, params, output):

    #extract filename
    filename = Path(bin_map).stem.replace('_bin_map','')
    
    #remove the stats parameter for naming 
    params_name = '_'.join(params[:-1])
    
    su.displayIO(output, ms.RUN_MSPA.format(' '.join(params)))
    
    #check if file already exist
    mspa_map_proj = pm.getResultDir() + filename + '_{}_mspa_map.tif'.format(params_name)
    
    mspa_stat = pm.getResultDir() + filename + '_{}_mspa_stat.txt'.format(params_name)
    
    if os.path.isfile(mspa_map_proj):
        su.displayIO(output, ms.MSPA_MAP_READY, 'success')
    else:
        
        #get the init file proj system 
        src = gdal.Open(bin_map)
        proj = osr.SpatialReference(wkt=src.GetProjection())
        src = None
    
        #copy the script folder in tmp 
        dir_util.copy_tree(pm.getMspaDir(), pm.getTmpMspaDir())
        #will work when we'll use python 3.8
        #shutil.copytree(pm.getMspaDir(), pm.getTmpMspaDir(), dirs_exist_ok=True)
    
        #create the 3 new tmp dir
        mspa_input_dir = pm.create_folder(pm.getTmpMspaDir() + 'input') + '/'
        mspa_output_dir = pm.create_folder(pm.getTmpMspaDir() + 'output') + '/'
        mspa_tmp_dir = pm.create_folder(pm.getTmpMspaDir() + 'tmp') + '/' 
    
        #copy the bin_map to input_dir
        bin_tmp_map = mspa_input_dir + 'input.tif'
        shutil.copyfile(bin_map, bin_tmp_map)
    
        #create the parameter file     
        with open(mspa_input_dir + 'mspa-parameters.txt',"w+") as file:
            file.write(' '.join(params))
            file.close()
        
        #change mspa mod 
        command = ['chmod', '755', pm.getTmpMspaDir() + 'mspa_lin64']
        os.system(' '.join(command))
    
        #launch the process
        command = ['bash', 'sepal_mspa']
        kwargs = {
            'args' : command,
            'cwd' : pm.getTmpMspaDir(),
            'stdout' : subprocess.PIPE,
            'stderr' : subprocess.PIPE,
            'universal_newlines' : True
        }
        with subprocess.Popen(**kwargs) as p:
            for line in p.stdout:
                su.displayIO(output, line)
    
        #copy result tif file in gfc 
        mspa_tmp_map = mspa_output_dir + 'input_' + params_name + '.tif'
        mspa_map = pm.getResultDir() + filename + '_{}_mspa_map_tmp.tif'.format(params_name)
    
        shutil.copyfile(mspa_tmp_map, mspa_map)
    
        #add projection
        options = gdal.TranslateOptions(outputSRS=proj)
        gdal.Translate(mspa_map_proj, mspa_map, options=options)
    
        #copy result txt file in gfc
        mspa_tmp_stat = mspa_output_dir + 'input_{}_stat.txt'.format(params_name)
        shutil.copyfile(mspa_tmp_stat, mspa_stat)
        
        su.displayIO(output, 'Mspa map complete', alert_type='success') 
        
        ###################### end of mspa process
    
    #flush tmp directory
    shutil.rmtree(pm.getTmpMspaDir())
    
    #delete tmp map
    os.remove(mspa_tmp_map)
    
    #create the output 
    table = mmr.getTable(mspa_stat)
    fragmentation_map = mmr.fragmentationMap(mspa_map_proj, output)
    paths = [mspa_stat, mspa_map_proj]
    
    ######################################
    #####     create the layout        ###
    ######################################
    
    #create the links
    gfc_download_txt = wf.DownloadBtn('MSPA stats in .txt', path=paths[0])
    gfc_download_tif = wf.DownloadBtn('MSPA raster in .tif', path=paths[1])
    
    #create the partial layout 
    partial_layout = v.Layout(
        Row=True,
        align_center=True,
        class_='pa-0 mt-5', 
        children=[
            v.Flex(xs12=True, md4=True, class_='pa-0', children=[table]),
            v.Flex(xs12=True, md8=True, class_='pa-0', children=[fragmentation_map])
        ]
    )
    
    #create the display
    children = [ 
        v.Layout(Row=True, children=[
            gfc_download_txt,
            gfc_download_tif,
        ]),
        partial_layout
    ]
    
    
    return children
            
            
    