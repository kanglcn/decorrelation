# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/API/plot.ipynb.

# %% auto 0
__all__ = ['profile_plot', 'raster', 'raster_stack', 'points', 'points_stack', 'bg_alpha']

# %% ../nbs/API/plot.ipynb 3
import numpy as np
import pandas as pd
import dask.dataframe as dd
from typing import Union

import holoviews as hv
import holoviews.operation.datashader as hd
import datashader as ds
from scipy.interpolate import griddata

def profile_plot(start_point:tuple(lon,lat),end_point:tuple(lon,lat),
                 num:int, # number of points to be sampled. 
                 lon_data:np.ndarry, lat_data:np.ndarry, data:np.ndarry):
    '''Plot the profile based on the coordinate of start_point and end_point'''
    profile_array = np.zeros((num,data.shape[1]))
    lon1, lat1 = start_point
    lon2, lat2 = end_point
    
    # Calculate increments for longitude and latitude
    lon_increment = (lon2 - lon1) / (num - 1)
    lat_increment = (lat2 - lat1) / (num - 1)
    
    # Generate interpolated points
    interpolated_points = [(lon1 + i * lon_increment, lat1 + i * lat_increment) 
                           for i in range(num)]
    for i, point in enumerate(interpolated_points):
        profile_array[i,:] = griddata((lon_data,lat_data),data, point, method='linear')
               
    return profile_array

# %% ../nbs/API/plot.ipynb 11
def raster(p:np.ndarray, # data to be plot, shape (n,m)
           kdims:list,# name of coordinates (x, y)
           pdim:str, # name of data to be plotted
           bounds:tuple=None, # extent of the raster, (x0, y0, x1 and y1), (0,0,m,n) )by default
           prange:tuple=None, # range of data to be plotted, it is interactively adjusted by default
           aggregator=ds.first, # aggregator for data rasterization
           use_hover:bool=True, # use hover to show data
):
    '''Interative visulization of a raster image.
    '''
    if prange is None: prange = (None, None)
    # if extents is None: extents = (None, None, None, None)
    # if bounds is None: bounds = (0, 0, p.shape[1], p.shape[0])
    if bounds is None: bounds = (0, p.shape[0], p.shape[1], 0)
    ## many problem to be solved:
    ##  1. the integer tiks should be at the center of pixel, but not
    ##  2. What does the bounds mean? center of the pixel or upper left of the pixel
    ##  3. The place of the inspect point is not at the center of the pixel
    ## now, no pixel-wise accurate rendering.
    vdims = [hv.Dimension(pdim,range=prange)]
    plot = hv.Image(p[::-1,:],bounds=bounds, kdims=kdims, vdims=vdims)
    plot = hd.rasterize(plot,aggregator=aggregator(),vdim_prefix='')
    if use_hover:
        highlight = hd.inspect_points(plot).opts(marker='o',size=10,tools=['hover'])
        plot = plot*highlight
    return plot

# %% ../nbs/API/plot.ipynb 16
def raster_stack(p:np.ndarray, # data to be plot, shape (n,m,l)
                 kdims:list,# name of coordinates (x, y)
                 tdim:str, # name of coordiantes (t,)
                 pdim:str, # name of data to be plotted
                 bounds:tuple=None, # extent of the raster, (x0, y0, x1 and y1), (0,0,m,n) )by default
                 t:list=None, # t coordinate of the plot, len: l, list of string. ['0','1',...] by default
                 prange:tuple=None, # range of data to be plotted, it is interactively adjusted by default
                 aggregator=ds.first, # aggregator for data rasterization
                 use_hover:bool=True, # use hover to show data
                ):
    '''Interative visulization of a raster image.
    '''
    if prange is None: prange = (None, None)
    if bounds is None: bounds = (0, p.shape[0], p.shape[1], 0)
    if t is None: t = map(str, np.arange(p.shape[2]))
    vdims = [hv.Dimension(pdim,range=prange)]

    plot_stack = {}
    for i, date in enumerate(t):
        plot_stack[date] = hv.Image(p[::-1,:,i], bounds=bounds, kdims=kdims,vdims=vdims)

    hmap = hv.HoloMap(plot_stack, kdims=pdim)
    hmap = hd.rasterize(hmap, aggregator=aggregator(),vdim_prefix='')

    if use_hover:
        highlight = hd.inspect_points(hmap).opts(marker='o',size=10,tools=['hover'])
        hmap = hmap*highlight

    return hmap

# %% ../nbs/API/plot.ipynb 23
def points(data:Union[pd.DataFrame,dd.DataFrame], # dataset to be plot
           kdims:list,# colomn name of Mercator coordinate in dataframe
           pdim:str, # column name of data to be plotted in dataframe
           prange:tuple=None, # range of data to be plotted, it is interactively adjusted by default
           aggregator=ds.first, # aggregator for data rasterization
           use_hover:bool=True, # use hover to show data
           vdims:list=None, # column name of data showed on hover except kdims and pdim. These two are always showed.
           google_earth:bool=False, # if use google earth imagery as the background
           ):
    '''Interative visulization of a point cloud image.
    '''
    if prange is None: prange = (None, None)
    if vdims is None: vdims = []
    if pdim in vdims: vdims.remove(pdim)
    vdims = [hv.Dimension(pdim,range=prange)] + vdims
    points = hv.Points(data,kdims=kdims, vdims=vdims)
    points = hd.rasterize(points,aggregator=aggregator(pdim),vdim_prefix='')
    points = hd.dynspread(points, max_px=5, threshold=0.2)
    if use_hover:
        highlight = hd.inspect_points(points).opts(marker='o',size=10,tools=['hover'])
        points = points*highlight
    if google_earth:
        geo_bg = hv.Tiles('https://mt1.google.com/vt/lyrs=s&x={X}&y={Y}&z={Z}',name='GoogleMapsImagery')
        points = geo_bg*points
    return points

# %% ../nbs/API/plot.ipynb 35
def points_stack(data:Union[pd.DataFrame,dd.DataFrame], # common data in all plots
                 kdims:list,# colomn name of Mercator coordinate in dataframe
                 pdata:Union[pd.DataFrame,dd.DataFrame], # data to be plotted as color
                 pdim:str, # label of pdata
                 prange:tuple=None, # range of pdata, it is interactively adjusted by default
                 aggregator=ds.first, # aggregator for data rasterization
                 use_hover:bool=True, # use hover to show other column
                 vdims:list=None, # column name of data showed on hover except kdims which are always showed.
                 google_earth:bool=False, # if use google earth imagery as the background
                ):
    '''Interative visulization of a stack of point cloud images.
    '''
    if prange is None: prange = (None, None)
    if vdims is None: vdims = []
    if pdim in vdims: vdims.remove(pdim)
    vdims = [hv.Dimension(pdim,range=prange)] + vdims

    plot_stack = {}
    for (name, column) in pdata.items():
        _data = data.copy(deep=False)
        _data[pdim] = column
        plot_stack[name] = hv.Points(_data,kdims=kdims,vdims=vdims)

    hmap = hv.HoloMap(plot_stack, kdims=pdim)
    hmap = hd.rasterize(hmap, aggregator=aggregator(pdim),vdim_prefix='')
    hmap = hd.dynspread(hmap, max_px=5, threshold=0.2)

    if use_hover:
        highlight = hd.inspect_points(hmap).opts(marker='o',size=10,tools=['hover'])
        hmap = hmap*highlight
    if google_earth:
        geo_bg = hv.Tiles('https://mt1.google.com/vt/lyrs=s&x={X}&y={Y}&z={Z}',name='GoogleMapsImagery')
        hmap = geo_bg*hmap
    return hmap

# %% ../nbs/API/plot.ipynb 50
def bg_alpha(pwr):
    _pwr = np.power(pwr,0.35)
    cv = _pwr.mean()*2.5
    v = (_pwr.clip(0., cv))/cv
    return v
