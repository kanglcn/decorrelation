# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/API/pc.ipynb.

# %% auto 0
__all__ = ['pc_mask', 'pc2ras', 'pc_union', 'pc_intersect', 'pc_diff']

# %% ../nbs/API/pc.ipynb 4
import cupy as cp
import numpy as np
from typing import Union
from cupy._sorting.search import _exists_kernel
import geopandas as gpd
from shapely.geometry import Point

def pc_mask(lon:np.ndarray, lat:np.ndarray, kml):
    '''mask the points in a polygon with kml file'''
    polys = gpd.read_file(kml, driver='rw')
    point_geometries = [Point(xy) for xy in zip(lon,lat)]
    geo_points = gpd.GeoSeries(point_geometries)
    mask = geo_points.within(polys.loc[0, 'geometry'])
    return mask

# %% ../nbs/API/pc.ipynb 5
def pc2ras(idx:Union[np.ndarray,cp.ndarray], # idx array
           pc_data:Union[np.ndarray,cp.ndarray], # data, 1D or more
           shape:tuple, # image shape
):
    '''convert sparse data to raster, filled with nan'''
    xp = cp.get_array_module(pc_data)
    raster = xp.empty((*shape,*pc_data.shape[1:]),dtype=pc_data.dtype)
    raster[:] = xp.nan
    raster[idx[0],idx[1]] = pc_data
    return raster

# %% ../nbs/API/pc.ipynb 7
def _ras_dims(idx1:Union[np.ndarray,cp.ndarray], # int array, index of the first point cloud
              idx2:Union[np.ndarray,cp.ndarray], # int array, index of the second point cloud
             )->tuple: # the shape of the original raster image
    '''Get the shape of the original raster image from two index, the shape could be smaller than the truth but it doesn't matter.'''
    xp = cp.get_array_module(idx1)
    dims_az = max(int(idx1[0,-1]),int(idx2[0,-1]))+1
    dims_r = max(int(xp.max(idx1[1,:])),int(xp.max(idx2[1,:])))+1
    return (dims_az,dims_r)

# %% ../nbs/API/pc.ipynb 8
def pc_union(idx1:Union[np.ndarray,cp.ndarray], # int array, index of the first point cloud
             idx2:Union[np.ndarray,cp.ndarray], # int array, index of the second point cloud
            )->tuple: # the union index `idx`; index of the point in output union index that originally in the first point cloud `inv_iidx`; index of the point in output union index that only exist in the second point cloud `inv_iidx2`; index of the point in the second input index that are not in the first input point cloud
    '''Get the union of two point cloud dataset. For points at their intersection, pc_data1 rather than pc_data2 is copied to the result pc_data.'''
    # this function is modified from np.unique

    xp = cp.get_array_module(idx1)
    dims = _ras_dims(idx1,idx2)

    idx = xp.concatenate((idx1,idx2),axis=-1)
    n1 = idx1.shape[1]; n2 = idx2.shape[1]
    
    idx_1d = xp.ravel_multi_index(idx,dims=dims) # automatically the returned 1d index is in int64
    iidx = xp.argsort(idx_1d,kind='stable') # test shows argsort is faster than lexsort, that is why use ravel and unravel index
    idx_1d = idx_1d[iidx]

    inv_iidx = xp.empty_like(iidx)
    inv_iidx[iidx] = xp.arange(iidx.shape[0]) # idea taken from https://stackoverflow.com/questions/2483696/undo-or-reverse-argsort-python

    mask = xp.empty(idx_1d.shape, dtype=bool)
    mask[:1] = True
    mask[1:] = idx_1d[1:] != idx_1d[:-1]
    
    idx_1d = idx_1d[mask]
    
    _mask = mask[inv_iidx] # the mask in the original cat order
    mask1 = _mask[:n1]
    mask2 = _mask[n1:]
    
    imask = xp.cumsum(mask) - 1
    inv_iidx = xp.empty(mask.shape, dtype=np.int64)
    inv_iidx[iidx] = imask # inverse the mapping
    inv_iidx = inv_iidx[_mask]
    
    idx = xp.stack(xp.unravel_index(idx_1d,dims)).astype(idx1.dtype)
   
    return idx, inv_iidx[:n1], inv_iidx[n1:], *xp.where(mask2)

# %% ../nbs/API/pc.ipynb 15
def pc_intersect(idx1:Union[np.ndarray,cp.ndarray], # int array, index of the first point cloud
                 idx2:Union[np.ndarray,cp.ndarray], # int array, index of the second point cloud
                 # the intersect index `idx`,
                 # index of the point in first point cloud index that also exist in the second point cloud,
                 # index of the point in second point cloud index that also exist in the first point cloud
                )->tuple:
    '''Get the intersection of two point cloud dataset.'''
    # Here I do not write the core function by myself since cupy have a different implementation of intersect1d

    xp = cp.get_array_module(idx1)
    dims = _ras_dims(idx1,idx2)

    idx1_1d = xp.ravel_multi_index(idx1,dims=dims) # automatically the returned 1d index is in int64
    idx2_1d = xp.ravel_multi_index(idx2,dims=dims) # automatically the returned 1d index is in int64

    idx, iidx1, iidx2 = xp.intersect1d(idx1_1d,idx2_1d,assume_unique=True,return_indices=True)
    idx = xp.stack(xp.unravel_index(idx,dims)).astype(idx1.dtype)

    return idx, iidx1, iidx2

# %% ../nbs/API/pc.ipynb 17
def pc_diff(idx1:Union[np.ndarray,cp.ndarray], # int array, index of the first point cloud
            idx2:Union[np.ndarray,cp.ndarray], # int array, index of the second point cloud
            # the diff index `idx`,
            # index of the point in first point cloud index that do not exist in the second point cloud,
           )->tuple:
    '''Get the point cloud in `idx1` that are not in `idx2`.'''

    xp = cp.get_array_module(idx1)
    dims = _ras_dims(idx1,idx2)

    idx1_1d = xp.ravel_multi_index(idx1,dims=dims) # automatically the returned 1d index is in int64
    idx2_1d = xp.ravel_multi_index(idx2,dims=dims) # automatically the returned 1d index is in int64
    
    mask = xp.in1d(idx1_1d, idx2_1d, assume_unique=True, invert=True)
    idx = idx1_1d[mask]

    idx = xp.stack(xp.unravel_index(idx,dims)).astype(idx1.dtype)
    return idx, xp.where(mask)[0]
