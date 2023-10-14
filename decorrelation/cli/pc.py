# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/CLI/pc.ipynb.

# %% auto 0
__all__ = ['de_ras2pc', 'console_de_ras2pc', 'de_pc2ras', 'console_de_pc2ras', 'de_pc_union', 'de_pc_intersect', 'de_pc_diff']

# %% ../../nbs/CLI/pc.ipynb 3
from itertools import product
import math
from typing import Union
import re

import zarr
import cupy as cp
import numpy as np
from matplotlib import pyplot as plt
import colorcet

import dask
from dask import array as da
from dask import delayed
from dask.distributed import Client, LocalCluster

from ..pc import pc2ras
from .utils.logging import get_logger, log_args

from fastcore.script import call_parse, Param

# %% ../../nbs/CLI/pc.ipynb 4
@log_args
def de_ras2pc(idx:str, # point cloud index
              ras:str|list, # path (in string) or list of path for raster data
              pc:str|list, # output, path (in string) or list of path for point cloud data
              pc_chunk_size:int=None, # output point chunk size, same as input idx by default
              hd_chunk_size:tuple|list=None, # output high dimension chunk size, tuple or list of tuple, same as input raster data by default
              log:str=None, # log file. Default: no log file
):
    '''Convert raster data to point cloud data'''
    # I find there is no need to set this hd_chunk_size, generally we do not need it
    logger = get_logger(logfile=log)

    idx_zarr = zarr.open(idx,mode='r')
    logger.zarr_info(idx,idx_zarr)
    assert idx_zarr.ndim == 2, "idx dimentation is not 2."
    if not pc_chunk_size:
        pc_chunk_size = idx_zarr.chunks[1]
        logger.info('no input pc_chunk_size, use pc_chunk_size as input idx')
    logger.info(f'pc_chunk_size: {pc_chunk_size}')

    logger.info('loading idx into memory.')
    idx = zarr.open(idx,mode='r')[:]
    n_pc = idx.shape[1]

    if isinstance(ras,str):
        assert isinstance(pc,str)
        ras_list = [ras]
        pc_list = [pc]
        if hd_chunk_size is not None:
            assert isinstance(hd_chunk_size,tuple)
            hd_chunk_size_list = [hd_chunk_size]
        else:
            hd_chunk_size_list = [None]
    else:
        assert isinstance(ras,list)
        assert isinstance(pc,list)
        ras_list = ras
        pc_list = pc
        n_data = len(ras_list)
        if hd_chunk_size is not None:
            assert isinstance(hd_chunk_size,list)
            hd_chunk_size_list = hd_chunk_size
        else:
            hd_chunk_size_list = [None]*n_data

    logger.info('starting dask local cluster.')
    cluster = LocalCluster()
    client = Client(cluster)
    logger.info('dask local cluster started.')

    _pc_list = ()
    for ras_path, pc_path, hd_chunk_size in zip(ras_list,pc_list,hd_chunk_size_list):
        logger.info(f'start to slice on {ras_path}')
        ras_zarr = zarr.open(ras_path,'r')
        logger.zarr_info(ras_path, ras_zarr)
        if hd_chunk_size is None:
            logger.info(f'hd_chunk_size not setted. Use the one from {ras_path}.')
            hd_chunk_size = ras_zarr.chunks[2:]
        logger.info(f'hd_chunk_size: {hd_chunk_size}.')

        ras = da.from_zarr(ras_path,chunks=(*ras_zarr.chunks[:2],*hd_chunk_size))
        logger.darr_info('ras',ras)

        with dask.config.set(**{'array.slicing.split_large_chunks': False}):
            pc = ras.reshape(-1,*ras.shape[2:])[np.ravel_multi_index((idx[0],idx[1]),dims=ras.shape[:2])]
        
        logger.darr_info('pc', pc)
        logger.info('rechunk pc data:')
        pc = pc.rechunk((pc_chunk_size,*pc.chunksize[1:]))
        logger.darr_info('pc', pc)
        _pc = pc.to_zarr(pc_path,overwrite=True,compute=False)
        logger.info(f'saving to {pc_path}.')
        _pc_list += (_pc,)
    
    logger.info('computing graph setted. doing all the computing.')
    da.compute(*_pc_list)

    logger.info('computing finished.')
    cluster.close()
    logger.info('dask cluster closed.')

# %% ../../nbs/CLI/pc.ipynb 5
@call_parse
def console_de_ras2pc(idx:str, # point cloud index
                      ras:Param(type=str,required=True,nargs='+',help='one or more path for raster data')=None,
                      pc:Param(type=str,required=True,nargs='+',help='output, one or more path for point cloud data')=None,
                      pc_chunk_size:int=None, # output point chunk size, same as input idx by default
                      hd_chunk_size:Param(type=str,nargs='+',help='''output high dimension chunk size,
                      each size should be wrapped in quotation marks and size in each dimension are seperated with ",",
                      same as input raster data by default''')=None,
                      log:str=None, # log file. Default: no log file
):
    '''Convert raster data to point cloud data'''
    if hd_chunk_size is not None:
        hd_chunk_size_ = []
        for size in hd_chunk_size:
            if len(size) == 0:
                size = ()
            else:
                size = size.split(',')
                size = tuple([int(i) for i in size])
            hd_chunk_size_.append(size)
    else:
        hd_chunk_size_ = None

    if len(ras)==1:
        ras = ras[0]
        pc = pc[0]
        if hd_chunk_size_ is not None:
            hd_chunk_size_ = hd_chunk_size_[0]

    de_ras2pc(idx,ras,pc,pc_chunk_size,hd_chunk_size_,log)

# %% ../../nbs/CLI/pc.ipynb 10
@log_args
def de_pc2ras(idx:str, # point cloud index
              pc:str|list, # path (in string) or list of path for point cloud data
              ras:str|list, # output, path (in string) or list of path for raster data
              shape:tuple, # shape of one image (nlines,width)
              az_chunk_size:int=None, # output azimuth chunk size, only one chunk by default
              log:str=None, # log file. Default: no log file
):
    '''Convert point cloud data to raster data, filled with nan'''
    # I find there is no need to set this hd_chunk_size, generally we do not need it
    logger = get_logger(logfile=log)

    idx_zarr = zarr.open(idx,mode='r')
    logger.info('idx dataset shape: '+str(idx_zarr.shape))
    logger.info('idx dataset chunks: '+str(idx_zarr.chunks))
    assert idx_zarr.ndim == 2, "idx dimentation is not 2."
    if not az_chunk_size:
        az_chunk_size = shape[0]
        logger.info('no input az_chunk_size, use only one chunk.')
    logger.info(f'az_chunk_size: {az_chunk_size}')

    logger.info('loading idx into memory.')
    idx = zarr.open(idx,mode='r')[:]
    n_pc = idx.shape[1]
    
    if isinstance(pc,str):
        assert isinstance(ras,str)
        pc_list = [pc]
        ras_list = [ras]
    else:
        assert isinstance(pc,list)
        assert isinstance(ras,list)
        pc_list = pc
        ras_list = ras
        n_data = len(pc_list)

    logger.info('starting dask local cluster.')
    cluster = LocalCluster()
    client = Client(cluster)
    logger.info('dask local cluster started.')

    _ras_list = ()

    for ras_path, pc_path in zip(ras_list,pc_list):
        logger.info(f'start to work on {pc_path}')
        pc_zarr = zarr.open(pc_path,'r')
        logger.zarr_info(pc_path,pc_zarr)
        
        pc = da.from_zarr(pc_path)
        logger.darr_info('pc', pc)
        ras = da.empty((shape[0]*shape[1],*pc.shape[1:]),chunks = (az_chunk_size*shape[1],*pc_zarr.chunks[1:]), dtype=pc.dtype)
        ras[:] = np.nan
        ras[np.ravel_multi_index((idx[0],idx[1]),dims=shape)] = pc
        ras = ras.reshape(*shape,*pc.shape[1:])
        logger.info('create ras dask array')
        logger.darr_info('ras', ras)
        _ras = ras.to_zarr(ras_path,overwrite=True,compute=False)
        _ras_list += (_ras,)

    logger.info('computing graph setted. doing all the computing.')
    da.compute(*_ras_list)

    logger.info('computing finished.')
    cluster.close()
    logger.info('dask cluster closed.')

# %% ../../nbs/CLI/pc.ipynb 11
@call_parse
def console_de_pc2ras(idx:str, # point cloud index
                      pc:Param(type=str,required=True,nargs='+',help='one or more path for point cloud data')=None,
                      ras:Param(type=str,required=True,nargs='+',help='output, one or more path for raster data')=None,
                      shape:Param(type=str,required=True,help='shape of one image "nlines,width"')=None,
                      az_chunk_size:int=None, # output azimuth chunk size, only one chunk by default
                      log:str=None, # log file. Default: no log file
):
    '''Convert point cloud data to raster data'''
    if len(ras)==1:
        ras = ras[0]
        pc = pc[0]
    
    shape = shape.split(',')
    shape = [int(i) for i in shape]
    shape=tuple(shape)

    de_pc2ras(idx,pc,ras,shape,az_chunk_size,log)

# %% ../../nbs/CLI/pc.ipynb 16
@log_args
def de_pc_union(idx1:str, # index of the first point cloud
                idx2:str, # index of the second point cloud
                idx:str, # output, index of the union point cloud
                pc1:str|list=None, # path (in string) or list of path for the first point cloud data
                pc2:str|list=None, # path (in string) or list of path for the second point cloud data
                pc:str|list=None, #output, path (in string) or list of path for the union point cloud data
                pc_chunk_size:int=None, # chunk size in output data,optional
                n_pc_chunk:int=None, # number of chunk in output data, optional, only one chunk if both pc_chunk_size and n_pc_chunk are not set.
                log:str=None, # log file. Default: no log file
):
    '''Get the union of two point cloud dataset. For points at their intersection, pc_data1 rather than pc_data2 is copied to the result pc_data.'''
    # I find there is no need to set this hd_chunk_size, generally we do not need it
    logger = get_logger(logfile=log)

    idx_zarr = zarr.open(idx,mode='r')
    logger.info('idx dataset shape: '+str(idx_zarr.shape))
    logger.info('idx dataset chunks: '+str(idx_zarr.chunks))
    assert idx_zarr.ndim == 2, "idx dimentation is not 2."
    if not az_chunk_size:
        az_chunk_size = shape[0]
        logger.info('no input az_chunk_size, use only one chunk.')
    logger.info(f'az_chunk_size: {az_chunk_size}')

    logger.info('loading idx into memory.')
    idx = idx_zarr[:]
    n_pc = idx.shape[1]
    
    if isinstance(pc,str):
        assert isinstance(ras,str)
        pc_list = [pc]
        ras_list = [ras]
    else:
        assert isinstance(pc,list)
        assert isinstance(ras,list)
        pc_list = pc
        ras_list = ras
        n_data = len(pc_list)

    for ras_path, pc_path in zip(ras_list,pc_list):
        pc_zarr = zarr.open(pc_path,'r')
        logger.info(f'{pc_path} dataset shape: '+str(pc_zarr.shape))
        logger.info(f'{pc_path} dataset chunks: '+str(pc_zarr.chunks))

        logger.info(f'loading {pc_path} into memory.')
        pc_data = pc_zarr[:]

        logger.info(f'open {ras_path} zarr in write mode.')
        ras_zarr = zarr.open(ras_path,'w',shape=(*shape,*pc_data.shape[1:]),dtype=pc_data.dtype,chunks=(az_chunk_size,shape[1],*pc_zarr.chunks[1:]))
        logger.info(f'{ras_path} dataset shape: '+str(ras_zarr.shape))
        logger.info(f'{ras_path} dataset chunks: '+str(ras_zarr.chunks))
        logger.info(f'write to {ras_path}.')
        ras_zarr[:] = pc2ras(idx,pc_data,shape)
        logger.info(f'write data to {ras_path} done.')

# %% ../../nbs/CLI/pc.ipynb 17
@log_args
def de_pc_intersect(idx:str, # point cloud index
              pc:str|list, # path (in string) or list of path for point cloud data
              ras:str|list, # output, path (in string) or list of path for raster data
              shape:tuple, # shape of one image (nlines,width)
              az_chunk_size:int=None, # output azimuth chunk size, only one chunk by default
              log:str=None, # log file. Default: no log file
):
    '''Convert point cloud data to raster data, filled with nan'''
    # I find there is no need to set this hd_chunk_size, generally we do not need it
    logger = get_logger(logfile=log)

    idx_zarr = zarr.open(idx,mode='r')
    logger.info('idx dataset shape: '+str(idx_zarr.shape))
    logger.info('idx dataset chunks: '+str(idx_zarr.chunks))
    assert idx_zarr.ndim == 2, "idx dimentation is not 2."
    if not az_chunk_size:
        az_chunk_size = shape[0]
        logger.info('no input az_chunk_size, use only one chunk.')
    logger.info(f'az_chunk_size: {az_chunk_size}')

    logger.info('loading idx into memory.')
    idx = zarr.open(idx,mode='r')[:]
    n_pc = idx.shape[1]
    
    if isinstance(pc,str):
        assert isinstance(ras,str)
        pc_list = [pc]
        ras_list = [ras]
    else:
        assert isinstance(pc,list)
        assert isinstance(ras,list)
        pc_list = pc
        ras_list = ras
        n_data = len(pc_list)

    for ras_path, pc_path in zip(ras_list,pc_list):
        pc_zarr = zarr.open(pc_path,'r')
        logger.info(f'{pc_path} dataset shape: '+str(pc_zarr.shape))
        logger.info(f'{pc_path} dataset chunks: '+str(pc_zarr.chunks))

        logger.info(f'loading {pc_path} into memory.')
        pc_data = pc_zarr[:]

        logger.info(f'open {ras_path} zarr in write mode.')
        ras_zarr = zarr.open(ras_path,'w',shape=(*shape,*pc_data.shape[1:]),dtype=pc_data.dtype,chunks=(az_chunk_size,shape[1],*pc_zarr.chunks[1:]))
        logger.info(f'{ras_path} dataset shape: '+str(ras_zarr.shape))
        logger.info(f'{ras_path} dataset chunks: '+str(ras_zarr.chunks))
        logger.info(f'write to {ras_path}.')
        ras_zarr[:] = pc2ras(idx,pc_data,shape)
        logger.info(f'write data to {ras_path} done.')

# %% ../../nbs/CLI/pc.ipynb 18
@log_args
def de_pc_diff(idx:str, # point cloud index
              pc:str|list, # path (in string) or list of path for point cloud data
              ras:str|list, # output, path (in string) or list of path for raster data
              shape:tuple, # shape of one image (nlines,width)
              az_chunk_size:int=None, # output azimuth chunk size, only one chunk by default
              log:str=None, # log file. Default: no log file
):
    '''Convert point cloud data to raster data, filled with nan'''
    # I find there is no need to set this hd_chunk_size, generally we do not need it
    logger = get_logger(logfile=log)

    idx_zarr = zarr.open(idx,mode='r')
    logger.info('idx dataset shape: '+str(idx_zarr.shape))
    logger.info('idx dataset chunks: '+str(idx_zarr.chunks))
    assert idx_zarr.ndim == 2, "idx dimentation is not 2."
    if not az_chunk_size:
        az_chunk_size = shape[0]
        logger.info('no input az_chunk_size, use only one chunk.')
    logger.info(f'az_chunk_size: {az_chunk_size}')

    logger.info('loading idx into memory.')
    idx = zarr.open(idx,mode='r')[:]
    n_pc = idx.shape[1]
    
    if isinstance(pc,str):
        assert isinstance(ras,str)
        pc_list = [pc]
        ras_list = [ras]
    else:
        assert isinstance(pc,list)
        assert isinstance(ras,list)
        pc_list = pc
        ras_list = ras
        n_data = len(pc_list)

    for ras_path, pc_path in zip(ras_list,pc_list):
        pc_zarr = zarr.open(pc_path,'r')
        logger.info(f'{pc_path} dataset shape: '+str(pc_zarr.shape))
        logger.info(f'{pc_path} dataset chunks: '+str(pc_zarr.chunks))

        logger.info(f'loading {pc_path} into memory.')
        pc_data = pc_zarr[:]

        logger.info(f'open {ras_path} zarr in write mode.')
        ras_zarr = zarr.open(ras_path,'w',shape=(*shape,*pc_data.shape[1:]),dtype=pc_data.dtype,chunks=(az_chunk_size,shape[1],*pc_zarr.chunks[1:]))
        logger.info(f'{ras_path} dataset shape: '+str(ras_zarr.shape))
        logger.info(f'{ras_path} dataset chunks: '+str(ras_zarr.chunks))
        logger.info(f'write to {ras_path}.')
        ras_zarr[:] = pc2ras(idx,pc_data,shape)
        logger.info(f'write data to {ras_path} done.')
