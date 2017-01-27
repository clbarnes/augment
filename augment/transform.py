import math
import numpy as np
import time
from scipy.ndimage.interpolation import map_coordinates, zoom
from scipy.ndimage.interpolation import geometric_transform

def rotate(point, angle):

    res = np.array(point)
    res[1] =  math.sin(angle)*point[2] + math.cos(angle)*point[1]
    res[2] = -math.sin(angle)*point[1] + math.cos(angle)*point[2]

    return res

def control_point_offsets_to_map(control_point_offsets, shape, interpolate_order=1):

    print("Creating dense offset map...")

    dims = len(shape)

    # upsample control points to shape of original image
    offsets = np.zeros((dims,) + shape)
    control_point_zoom = tuple(float(s)/c for s,c in zip(shape, control_point_offsets.shape[1:]))

    for d in range(dims):
        offsets[d] = zoom(control_point_offsets[d], zoom=control_point_zoom, mode='nearest', order=interpolate_order)

    return offsets

def create_identity_transformation(shape):

    axis_ranges = (np.arange(d, dtype=np.float) for d in shape)
    return np.meshgrid(*axis_ranges, indexing='ij')

def create_rotation_transformation(shape, angle):

    print("Creating rotation transformation with:")
    print("\tangle: " + str(angle))

    dims = len(shape)
    control_points = (2,)*dims

    # map control points to world coordinates
    control_point_scaling_factor = tuple(float(s-1) for s in shape)

    # rotate control points
    center = np.array([0.5*(d-1) for d in shape])

    control_point_offsets = np.zeros((dims,) + control_points, dtype=np.float)
    for control_point in np.ndindex(control_points):

        point = np.array(control_point)*control_point_scaling_factor
        center_offset = np.array([p-c for c,p in zip(center, point)])
        rotated_offset = rotate(center_offset, angle)
        displacement = rotated_offset - center_offset
        control_point_offsets[(slice(None),) + control_point] += displacement

    return control_point_offsets_to_map(control_point_offsets, shape)

def create_elastic_transformation(shape, control_point_spacing = 100, jitter_sigma = 10.0, subsample = 1):

    dims = len(shape)
    subsample_shape = tuple(s/subsample for s in shape)

    assert tuple(s*subsample for s in subsample_shape) == shape, "shape components %s must be multiples of subsample size %d"%(str(shape), subsample)

    try:
        spacing = tuple((d for d in control_point_spacing))
    except:
        spacing = (control_point_spacing,)*dims
    try:
        sigmas = [ s for s in jitter_sigma ]
    except:
        sigmas = [jitter_sigma]*dims

    control_points = tuple(
            max(1,int(round(float(shape[d])/spacing[d])))
            for d in range(len(shape))
    )

    print("Creating elastic transformation with:")
    print("\tcontrol points per axis: " + str(control_points))
    print("\taxis jitter sigmas     : " + str(sigmas))

    # jitter control points
    control_point_offsets = np.zeros((dims,) + control_points, dtype=np.float)
    for d in range(dims):
        if sigmas[d] > 0:
            control_point_offsets[d] = np.random.normal(scale=sigmas[d], size=control_points)

    offset_map = control_point_offsets_to_map(control_point_offsets, subsample_shape, interpolate_order=3)
    if subsample > 1:
        offset_map = control_point_offsets_to_map(offset_map, shape, interpolate_order=1)

    return offset_map

def apply_transformation(image, transformation, interpolate = True, outside_value = 0):

    print("Applying transformation...")
    order = 1 if interpolate == True else 0
    return map_coordinates(image, transformation, order=order, mode='constant', cval=outside_value)
