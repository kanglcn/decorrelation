# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/CLI/utils/dask.ipynb.

# %% auto 0
__all__ = ['pad_internal', 'get_cuda_cluster', 'get_pc_chunk_size']

# %% ../../../nbs/CLI/utils/dask.ipynb 3
from dask import array as da
import numpy as np
import os
import math
from .appconfig import get_config

# %% ../../../nbs/CLI/utils/dask.ipynb 4
def _pad_chunks(original_chunks, axes):
    """Get new chunks for array with block padding."""
    # this function is adapt from https://github.com/dask/dask/blob/main/dask/array/overlap.py#L17
    chunks = []
    for i, bds in enumerate(original_chunks):
        depth = axes.get(i, 0)
        if isinstance(depth, tuple):
            left_depth = depth[0]
            right_depth = depth[1]
        else:
            left_depth = depth
            right_depth = depth
        
        chunk = []
        for bd in bds:
            chunk.append(left_depth+bd+right_depth)
        chunks.append(chunk)
    return chunks

# %% ../../../nbs/CLI/utils/dask.ipynb 5
def pad_internal(arr:da.array,
                 depth:dict=None):
    '''Pad zero between block boundaries, currently one pad zero are supported'''
    chunks = _pad_chunks(arr.chunks,axes=depth)

    depth_len = len(depth)
    pad_arg = [None]*depth_len
    slice_arg = [None]*depth_len
    for i in range(depth_len):
        if isinstance(depth[i],tuple):
            pad_arg[i] = depth[i]
            left_slice = depth[i][0]
            if depth[i][1] == 0:
                right_slice = None
            else:
                right_slice = -depth[i][-1]
            slice_arg[i] = slice(left_slice,right_slice)
        else:
            pad_arg[i] = (depth[i],depth[i])
            left_slice = depth[i]
            if depth[i] == 0:
                right_slice = None
            else:
                right_slice = -depth[i]
            slice_arg[i] = slice(left_slice,right_slice)
    pad_arg = tuple(pad_arg)
    slice_arg = tuple(slice_arg)
    arr_out = da.map_blocks(np.pad,arr,pad_arg,chunks=chunks)

    return arr_out[slice_arg]

# %% ../../../nbs/CLI/utils/dask.ipynb 6
def get_cuda_cluster():
    from dask.distributed import Client
    from dask_cuda import LocalCUDACluster
    config = get_config()
    
    visible_gpus = config.get('visible_gpus')
    if visible_gpus is None:
        n_gpu = len(os.environ['CUDA_VISIBLE_DEVICES'].split(','))
    else:
        n_gpu = len(visible_gpus)
    n_cpu = config.get('n_cpu')
    threads_per_worker = math.floor(n_cpu/n_gpu)
    cluster = LocalCUDACluster(CUDA_VISIBLE_DEVICES=config.get('visible_gpus'),threads_per_worker=threads_per_worker)
    client = Client(cluster)
    return cluster, client

# %% ../../../nbs/CLI/utils/dask.ipynb 7
def get_pc_chunk_size(az_chunk_size,pc_size,pc_chunk_size=None,n_pc_chunk=None,logger=None):
    '''automatically determine pc_chunk_size, n_pc_chunk.
    '''
    if pc_chunk_size is None:
        if n_pc_chunk is None:
            pc_chunk_size = az_chunk_size
            logger.info(f'set pc_chunk_size as az_chunk_size: {az_chunk_size}')
        else:
            logger.info(f'got n_pc_chunk: {n_pc_chunk}')
            pc_chunk_size = math.ceil(pc_size/pt_n_chunk)
            logger.info(f'set pc_chunk_size as: {pc_chunk_size}')
    else:
        logger.info(f'got pc_chunk_size: {pc_chunk_size}')
    return pc_chunk_size
