# import the necessary packages
import os
import gc
from imutils import paths
import argparse
import cv2
import numpy as np
from osgeo import gdal, ogr, osr
import time
import easygui
import fnmatch
import sys
import re
import subprocess
import mmap
from multiprocessing import Pool
from multiprocessing import cpu_count
from timeit import default_timer as timer
import time
import subprocess
from tqdm import tqdm




def Gdal_Func(work_data):
    epsg = str(work_data[6])
    tif_out = str(work_data[4])
    vrt = str(work_data[5])
    X1=int(work_data[0])
    X2=int(work_data[1])
    X3=int(work_data[2])
    X4=int(work_data[3])
    gsd = str(work_data[7]/100)
         
    opt= gdal.WarpOptions(options=['TFW=YES','TILED=YES','BLOCKXSIZE=512'], format='GTiff', outputBounds=[X1,X2,X3,X4], xRes=gsd, yRes=gsd, dstSRS=epsg, multithread=True, resampleAlg=gdal.GRIORA_Bilinear)
    gdal.Warp(tif_out,vrt,options=opt)
    

   

def pool_handler(work):
    p = Pool(nbr_cpu)
    for _ in tqdm(p.imap_unordered(Gdal_Func, work), total=len(work)):
        pass

def striplist(l):
    return([x.strip() for x in l])

def cls():
    os.system('cls' if os.name=='nt' else 'clear')

def compLat_Long(degs, mins, secs, comp_dir):
    return (degs + (mins / 60) + (secs / 3600)) * comp_dir

def mapcount(filename):
    f = open(filename, "r+")
    buf = mmap.mmap(f.fileno(), 0)
    lines = 0
    readline = buf.readline
    while readline():
        lines += 1
    return lines-1


def getSignOf(chifre):
    if chifre >= 0:
        return 1
    else:
        return -1



def update_progress(progress):
    barLength = 30 # Modify this to change the length of the progress bar
    
    block = int(round(barLength*progress))
    text = "\rPercent: [{0}] {1}% ".format( "#"*block + "-"*(barLength-block), int(progress*100))
    sys.stdout.write(text)
    sys.stdout.flush()
    #print('\n')
 

def epsgtoepsg(EPSG_in, lon, lat, EPSG_out):


 InSR = osr.SpatialReference()
 InSR.ImportFromEPSG(EPSG_in)      
 OutSR = osr.SpatialReference()
 OutSR.ImportFromEPSG(EPSG_out)     

 Point = ogr.Geometry(ogr.wkbPoint)
 Point.AddPoint(lon,lat) # use your coordinates here
 Point.AssignSpatialReference(InSR)    # tell the point what coordinates it's in
 Point.TransformTo(OutSR)              # project it to the out spatial reference

 return (Point.GetX(),Point.GetY())

def time_elapsed(start):
       end = timer()
       hours, rem = divmod(end-start, 3600)
       minutes, seconds = divmod(rem, 60)
       print('Time elapsed (hh:mm:ss.ms) {:0>2}:{:0>2}:{:05.2f}'.format(int(hours),int(minutes),seconds))
   

if __name__ == '__main__':

 dirphoto = easygui.diropenbox(msg=None, title="Selectionez le dossier des orthos à decouper et translater", default=None )
 list = fnmatch.filter(os.listdir(dirphoto), '*.tif')
 total_con=len(list)
 D1 = str(total_con)
 msg = str(total_con) +" orthos voulez-vous continuer?"
 title = "Merci de confirmer"
 if easygui.ynbox(msg, title, ('Yes', 'No')): # show a Continue/Cancel dialog
     pass # user chose Continue else: # user chose Cancel
 else:
     exit(0)

 x = [os.path.join(r,file) for r,d,f in os.walk(dirphoto) for file in f if file.endswith(".tif")]
 dirmosaic = easygui.diropenbox(msg=None, title="Selectionez le dossier de sortie (sur un autre volume svp)", default=None )
 
 cl=0
 ci=0
 cls()

 nbr_cpu = cpu_count()

 cpu_in = easygui.integerbox(msg='Vous avez %i cores, combien souhaitez-vous en allouer?' %nbr_cpu, title='Cores CPU', default=2, lowerbound=2, upperbound=nbr_cpu-2, image=None, root=None)

 

 eps_in = easygui.integerbox(msg='Entrez le code EPSG des orthos originalles', title='Code EPSG', default=3946, lowerbound=0, upperbound=99999, image=None, root=None)
 source = osr.SpatialReference()
 error = source.ImportFromEPSG(eps_in)
 if error==0:
  pass
 else:
   easygui.msgbox("Le code EPSG n'est pas valide, l'application va se fermer!!")
   sys.exit(0)
 
 eps_out = easygui.integerbox(msg='Entrez le code EPSG des orthos en sorties', title='Code EPSG', default=2154, lowerbound=0, upperbound=99999, image=None, root=None)
 source = osr.SpatialReference()
 error = source.ImportFromEPSG(eps_out)
 if error==0:
  pass
 else:
   easygui.msgbox("Le code EPSG n'est pas valide, l'application va se fermer!!")
   sys.exit(0)

 
 cut_shp = easygui.fileopenbox(msg='Selectionez le fichier shp (polygone englobant) en code EPSG:%i de l\'emprise des orthos en sorties' %eps_out, title='Shp',default=dirmosaic+'\\*.shp', filetypes=['*.shp'])
 driver = ogr.GetDriverByName('ESRI Shapefile')
 dataSource = driver.Open(cut_shp, 0)
 # Check to see if shapefile is found.
 if dataSource is None:
    easygui.msgbox("Impossible d\'ouvrir %s l'application va se fermer!!!"%cut_shp)
    sys.exit(0)
 else:
    layer = dataSource.GetLayer()
    featureCount = layer.GetFeatureCount()
    spatialRef = layer.GetSpatialRef()
    epsg_shp = (spatialRef.GetAuthorityCode(None))

    if str(epsg_shp) != str(eps_out):
       easygui.msgbox('Attention ce shp n\'est pas de la même projection aue votre ortho en sortie l\'application va se fermer!!!')
       sys.exit(0)
 
    if featureCount>1:
        easygui.msgbox('Attention ce shp contient plus de 1 polygone l\'application va se fermer!!!')
        sys.exit(0)
    else:
        for feature in layer:
             geom = feature.GetGeometryRef()
             Wkt  = geom.ExportToWkt()
             geo = geom.GetGeometryName()
             if geo == 'POLYGON':
                pass
             else:
                easygui.msgbox('Attention ce shp n\'est pas un polygone, l\'application va se fermer!!!')
                sys.exit(0)


 ortho_res = easygui.integerbox(msg='Entrez le GSD en centimètre ', title='GSD', default=5, lowerbound=1, upperbound=1000, image=None, root=None)

 ortho_size = easygui.integerbox(msg='Entrez la taille de la dalle en mètres', title='Taille de la dalle', default=200, lowerbound=100, upperbound=10000, image=None, root=None)

 
 epsgin = "EPSG:" + str(eps_in)
 epsgout = "EPSG:" + str(eps_out)
 
 print('creation du fichier vrt, patientez...')
 vrt_options = gdal.BuildVRTOptions(resampleAlg='cubic', outputSRS=epsgin)
 mon_vrt = dirphoto+'\cutline.vrt'
 
 gdal.BuildVRT(mon_vrt,x, options=vrt_options)
 #gdal.BuildVRT(mon_vrt,x)
 #rast_obj = gdal.BuildVRT('/vsimem/inmem.vrt',x,options=vrt_options)
 
 rast_obj = gdal.Open(mon_vrt)
 
 
 ulx, xres, xskew, uly, yskew, yres  = rast_obj.GetGeoTransform() 
 

 ncols = rast_obj.RasterXSize
 nrows = rast_obj.RasterYSize
 del rast_obj
 x1 = ulx
 y1 = uly - (xres*nrows)
 x2 = ulx + (xres*ncols)
 y2 = uly
  

 x1_t0,y1_t0 = epsgtoepsg(eps_in,x1, y1,eps_out)
 x2_t0,y2_t0 = epsgtoepsg(eps_in,x2, y2,eps_out)
 
 x1_t0 = int(x1_t0 /ortho_size)*ortho_size
 y1_t0 = int(y1_t0 /ortho_size)*ortho_size
 x2_t0 = int(x2_t0 /ortho_size)*ortho_size+ortho_size
 y2_t0 = int(y2_t0 /ortho_size)*ortho_size+ortho_size
 print(x1_t0,y1_t0,x2_t0,y2_t0)
 xdalles = int((x2_t0-x1_t0)/ortho_size)
 ydalles = int((y2_t0-y1_t0)/ortho_size)
 total_dalles = int(xdalles*ydalles)
 


 cls()
 print('Creation de la liste des dalles pour le traitement sur %i cores'%cpu_in)
 time.sleep(1) 
 cls()
 #####################################################
 Photos = np.empty((total_dalles, 8), dtype=object)
 #####################################################

 num = 0

 for i in range(0, xdalles-1): 
   x_t = x1_t0+(i*ortho_size)
   X1=str(int(x_t))
   X2=str(int(x_t+ortho_size))
   for ii in range(0, ydalles-1):
      ci  += 1
            
      y_t = y1_t0+(ii*ortho_size)
      Y1=str(int(y_t))
      Y2=str(int(y_t+ortho_size))



   
      layer.SetSpatialFilterRect(float(X1),float(Y1),float(X2),float(Y2))
      num = layer.GetFeatureCount()
      if num > 0:
         tif_out = dirmosaic+'\\'+str(X1[:5])+'_'+str(Y2[:6])+'.tif'

         Photos[cl,0] = X1
         Photos[cl,1] = Y1
         Photos[cl,2] = X2
         Photos[cl,3] = Y2
         Photos[cl,4] = tif_out
         Photos[cl,5] = mon_vrt
         Photos[cl,6] = epsgout
         Photos[cl,7] = ortho_res
         cl  += 1
         
       


      num = 0
      layer.SetSpatialFilter(None)
      update_progress(ci/total_dalles)
 
 
 
       
          
 
 result = Photos[:cl]

 cls()
 print('Demarage de GdalWarp sur : '+ str(len(result)) +' photos soyez patient...')
 time.sleep(2)  
 pool_handler(result)
 exit(0)
 cls()
 print('Fin')
