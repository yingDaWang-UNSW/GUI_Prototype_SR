# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 12:02:29 2020

@author: Leaf
"""

'''
2D/3D super resolution testing deployable source
'''
import multiprocessing
multiprocessing.freeze_support()
import glob
import numpy as np
import os
from sys import stdout
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
import tensorflow as tf
#import tensorlayer as tl
from gooey import GooeyParser
import scipy.misc
from sr3dModels import *
from sr2dModels import *
import argparse
import PIL
from PIL import Image
from tifffile import imsave
from tifffile import imread
import h5py
from scipy.io import netcdf
import pdb
import matplotlib.pyplot as plt
from gooey import Gooey
#TODO: add nc file reader, option for pseudo 3D, uploading to server, etc

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

        
def str2int(v):
    if v=='M':
        return v
    try:
        v = int(v)
    except:
        raise argparse.ArgumentTypeError('int value expected.')
    return v

def str2float(v):
    if v=='M':
        return v
    try:
        v = float(v)
    except:
        raise argparse.ArgumentTypeError('float value expected.')
    return v

##
# Module Flags
##

def argumentParser():
    '''
    parser = GooeyParser(description="Ying Da Wang, Ryan Armstrong, Peyman Mostaghimi")
    
    parser.add_argument('Input_Images', metavar='Input Images', help='Folder containing input images', widget="DirChooser")
    
    parser.add_argument('Input_Format', metavar='Input Format', type=str, choices=['.png', '.jpg', '.mat', '.nc', '.tif'])
    
    #parser.add_argument('Network_Weights', help="Name and location of the network weights", widget='FileChooser') 
    
    parser.add_argument('Scale_Factor', metavar='Scale Factor', type=str, choices=['4', '16', '64'], help='Upsampling factor (Future releases will support more options)')
    
    parser.add_argument('Output_Format', metavar='Output Format', type=str, choices=['.png', '.jpg', '.mat', '.nc', '.tif'])
    
    parser.add_argument('Bit_Depth', metavar='Bit Depth', type=str, choices=['uint8'], help='Bit depth of your input images  (Future releases will support more options)', default = 'uint8')

    parser.add_argument('Image_Dimension', metavar='Image Dimension', type=str, choices=['2D','3D'], help='Dimensions of input images')
    
    parser.add_argument('Use_CPU', metavar='Use CPU', type=str, choices=['yes', 'no'], help='Force the network to use the CPU (will default to CPU if no compatible GPU is detected)', default='yes')

    parser.add_argument('Use_GAN', metavar='Use GAN', type=str, choices=['yes', 'no'], help='Force the network to use the GAN (will default to GAN)', default='yes')

    '''
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--Input_Images', metavar = 'Input_Images', type=str, help='Folder containing input images')
    
    parser.add_argument('--Input_Format', metavar='Input_Format', type=str)
    
    #parser.add_argument('--Network_Weights', type=str, help="Name and location of the network weights") 
    
    parser.add_argument('--Scale_Factor', metavar = 'Scale_Factor', type=str, help='Upsampling factor (Future releases will support more options)')
        
    parser.add_argument('--Bit_Depth', metavar = 'Bit_Depth', type=str, help='Bit depth of your input images  (Future releases will support more options)')
    
    parser.add_argument('--Image_Dimension', metavar = 'Image_Dimension', type=str, help='Dimensions of input images')
    
    parser.add_argument('--Output_Format', metavar='Output_Format', type=str)
    
    parser.add_argument('--Use_CPU', metavar='Use_CPU', type=str, help='Force the network to use the CPU (will default to CPU if no compatible GPU is detected)')
    #parser.add_argument('--Use_CPU', type=str2bool, help='Force the network to use the CPU (will default to CPU if no compatible GPU is detected)')
    
    parser.add_argument('--Use_GAN', metavar='Use_GAN', type=str, help='Force the network to use the GAN (will default to GAN)')
    
    args = parser.parse_args()
    
    return args


#@Gooey(program_name='Super Resolution by Neural Networks', default_size=(700, 700), image_dir=".\image")

def main():
    args=argumentParser()
    #should be removed in the normal version
    args.Input_Format, args.Scale_Factor, args.Bit_Depth, args.Image_Dimension, args.Output_Format, args.Use_CPU, args.Use_GAN='.mat', '16', 'uint8', '3D', '.tif', 'yes', 'yes'
    flatFlag, restore, args.Input_Images, numBits = None, None, './srtestfolder/', 0.0
    
    cpuFlag=args.Use_CPU
    if cpuFlag == 'yes':
        cpuFlag=True
    else:
        cpuFlag=False
        
    
    ganFlag=args.Use_GAN
    if ganFlag== 'yes':
        ganFlag=True
    else:
        ganFlag=False
    datasetBitDepth=args.Bit_Depth
    dim=args.Image_Dimension
    '''
    TESTING
    '''
    
    # argument parsing
    #    if testFlag:
    #        ganFlag=False
    
    outputFlag = args.Output_Format
    Scale_Factor=str2int(args.Scale_Factor)
    numFilters=64
    activation='prelu'
    residual_blocks=16
    batchNorm=False
    if datasetBitDepth == 'uint8':
        numBits=127.5
    
    if dim=='2D':
        flatFlag=True
        if ganFlag:
            restore = './validatedCheckpoints/SRGAN2DRock.ckpt'
        else:
            restore = './validatedCheckpoints/SRCNN2DRock.ckpt'
    elif dim == '3D':
        flatFlag=False
        if ganFlag:
            restore = './validatedCheckpoints/SRCNN3DRock.ckpt'
        else:
            restore = './validatedCheckpoints/SRCNN3DRock.ckpt'
            #restore=args.Network_Weights
    
    
    # define the models
    if flatFlag:
        outputShape=[None, None, None, 3]#(1, Nx, Ny, 3)RGB
    else:
        outputShape=[None, None, None, None, 1]#(1, Nx, Ny, Nz, 1)
    # the ground truth image tensor
    t_target_image = tf.compat.v1.placeholder('float32',outputShape, name='t_HR_target_image')
    if flatFlag:# the generator is always fully convolutional
        inputShape=[None, None, None, 3]
    else:
        inputShape=[None, None, None, None, 1]
    inputTensor = tf.compat.v1.placeholder('float32',inputShape, name='t_LR_image_input_to_SR_generator')
    #TODO: add option for argument to handle different models
    # pass to the generator model
    if flatFlag: # 2D EDSR model (built on TL)
        net_gen = generator2D(inputTensor, Scale_Factor, residual_blocks, numFilters, 3, initKernelFactor=1, activation=activation, batchNorm=batchNorm, reuse=False)
        net_gen_data=net_gen
        net_gen=net_gen_data.outputs
    else: #3d models
        net_gen = generatorTF(inputTensor, 3, residual_blocks, 64, Scale_Factor, False, True)
          
    #g_vars = tl.layers.get_variables_with_name('SRGAN_g', True, True)
    
    g_vars = [var for var in tf.compat.v1.trainable_variables() if 'SRGAN_g' in var.name]
    # Resources
    if cpuFlag:
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    else:
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    config = tf.compat.v1.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    config.gpu_options.allow_growth = True
    config.gpu_options.per_process_gpu_memory_fraction = 1
    session = tf.compat.v1.Session(config=config)
    session.run(tf.initialize_all_variables())
    # load weights
    # pdb.set_trace()
    saver = tf.compat.v1.train.Saver(g_vars, max_to_keep = 10000)
    if restore is not None:
        saver.restore(session, restore)
    else:
        print('No Checkpoints Requested')
    outdir=args.Input_Images+'/srOutputs'
    os.makedirs(outdir, exist_ok=True)
    # detect the files within the folder % accept png, tiff, and nc files.
    files = glob.glob(os.path.join(args.Input_Images, '*'), recursive=True)
    
    for fname in files:
        if os.path.isfile(fname):
            print(fname)
            # find the extension
            folder, name = os.path.split(fname)
            name, ext = os.path.splitext(name)
            
            # load the file
            print('Loading File ' + fname)
            
            if ext == '.png' or ext == '.jpg':
                lr = np.array(Image.open(fname).convert('RGB'),dtype=datasetBitDepth)
                #if lr.mode != 'RGB':
                    #lr = lr.convert('RGB')
                #lr = np.array(lr, dtype=datasetBitDepth)# (Nx, Ny, 3 or 1), dtype = uint8
                if lr.shape[2]!=3 and lr.shape[2]==1:# 3 = RGB, 1 = Black&White
                    lr=np.concatenate((lr, lr, lr), 2)# just make all images in the same format       
                lr=np.expand_dims(lr,0)#2D sahpe = (1, )
                if not flatFlag:#3D
                    lr=np.expand_dims(lr,4)# shape = (, , , , 1)
                    print('WARNING: Attempting to super resolve a 2D image with 3D network')
                #lr = lr[:,0:100, 0:100, :]
            
            elif ext == '.mat':
    
                f = h5py.File(fname)
                for k, v in f.items():
                    lr = np.array(v)
                if lr.shape[-1]==3:#input could be 2D and 3D
                    lr=np.expand_dims(lr, 0)
                else:
                    lr=np.expand_dims(np.expand_dims(lr,3), 0)
            
            elif ext == '.nc':
                file2read = netcdf.NetCDFFile(fname,'r')
                temp = file2read.variables['tomo'] 
                lr=temp[:]
                file2read.close()
                lr=np.expand_dims(np.expand_dims(lr,3), 0)#2D and 3D
            
            elif ext == '.tif':
                lr = imread(fname)
                if lr.shape[-1]==3:#2D and 3D
                    lr=np.expand_dims(lr, 0)
                else:
                    lr=np.expand_dims(np.expand_dims(lr,3), 0)
            
            # run contrast adjustment
            if lr.max()>255 or lr.min()<0.0:
                
                lr = np.array(lr, dtype='float32')
                minVal=lr.min()
                maxVal=lr.max()
                nx=lr.shape[1]
                ny=lr.shape[2]
                truncMax=np.quantile(lr[:,int(nx*0.2):int(nx*0.8), int(ny*0.2):int(ny*0.8), :, :], 0.99)
                truncMin=np.quantile(lr[:,int(nx*0.2):int(nx*0.8), int(ny*0.2):int(ny*0.8), :, :], 0.01)
                print('WARNING: image is not within network bounds, performing automatic contrast adjustment (assuming inscribed cylinder) to ' + str(truncMax) +' - '+ str(truncMin))
                lr[lr<truncMin]=truncMin
                lr[lr>truncMax]=truncMax 
                
                lr = (lr - truncMin)/(truncMax-truncMin)*255
            # generate SR
            lr = np.array(lr, dtype='float32')
            print('Super Resolving File ' + fname)
            lr = (lr-numBits)/numBits
            if flatFlag and lr.shape[3]>3:
                print('Performing Pseudo Super Resolution on 3D image with 2D network')
                lr=np.transpose(lr,(0,3,2,1,4))
                temp=np.zeros((lr.shape[0],lr.shape[1]*Scale_Factor, lr.shape[2]*Scale_Factor, lr.shape[3], lr.shape[4]))
                
                for i in range(lr.shape[3]):
                    stdout.write("\rSuper Resolving Slice %d" % (i+1))
                    lrSlice=lr[:,:,:,i,:];
                    lrSlice=np.squeeze(lrSlice);
                    lrSlice=np.expand_dims(lrSlice,2)
                    lrSlice=np.expand_dims(np.concatenate((lrSlice, lrSlice, lrSlice), 2),0)
                    sr = session.run(net_gen, {inputTensor: lrSlice})
                    sr = (sr+1)*numBits
                    temp[:,:,:,i,:]=np.expand_dims(sr[:,:,:,0],3)
                stdout.flush()
                stdout.write("\n")
                temp=np.transpose(temp,(0,3,2,1,4))
                temp2=np.zeros((temp.shape[0],temp.shape[1], temp.shape[2]//Scale_Factor, temp.shape[3], temp.shape[4]))       
                for i in range(temp.shape[3]):
                    stdout.write("\rCompressing Slice %d" % (i+1))
                    compSlice=np.array(Image.fromarray(np.squeeze(temp[:,:,:,i,:])).resize((temp.shape[1], temp.shape[2]//Scale_Factor), PIL.Image.BICUBIC))
                    temp2[:,:,:,i]=np.expand_dims(np.expand_dims(compSlice,0),3)
                stdout.flush()
                stdout.write("\n")
                del temp
                temp2 = (temp2-numBits)/numBits
                sr3= np.zeros((lr.shape[0],lr.shape[1]*Scale_Factor, lr.shape[2]*Scale_Factor, lr.shape[3]*Scale_Factor, lr.shape[4]))
                for i in range(lr.shape[3]*Scale_Factor):
                    stdout.write("\rSuper Resolving Orthogonal Slice %d" % (i+1))
                    lrSlice=temp2[:,:,:,i,:];
                    lrSlice=np.squeeze(lrSlice);
                    lrSlice=np.expand_dims(lrSlice,2)
                    lrSlice=np.expand_dims(np.concatenate((lrSlice, lrSlice, lrSlice), 2),0)
                    sr = session.run(net_gen, {inputTensor: lrSlice})
                    sr = (sr+1)*numBits
                    sr3[:,:,:,i,:]=np.expand_dims(sr[:,:,:,0],3)
                stdout.flush()
                stdout.write("\n")
                sr=sr3
                del temp2
            
            elif not flatFlag and lr.shape[3]>3:
                print('Performing patch-based 3D super resolution')
                print(f'The shape of lower resolution is {lr.shape}')
                numsplitsX = Scale_Factor#16
                numsplitsY = Scale_Factor#16
                numsplitsZ = Scale_Factor#16
                
                #plt.figure(1)
                #plt.imshow(np.squeeze(lr)[:,:,0])
                
                lr = np.split(lr, numsplitsX, 1)
                lr = np.vstack(lr)
                
                lr = np.split(lr, numsplitsY, 2)
                lr = np.vstack(lr)
                
                lr = np.split(lr, numsplitsZ, 3)
                lr = np.vstack(lr)#(4096, 16, 16, 16, 1)
                
                lr_list = list(lr)
                for i in range(len(lr_list)):
                    tmp = np.expand_dims(lr_list[i], 0)#(1, 16, 16, 16, 1)
                    #pdb.set_trace()
                    #tmp = tmp.repeat(4, axis = 0).repeat(4, axis = 1).repeat(4, axis = 2)
                    sr = session.run(net_gen, {inputTensor: tmp})
                    sr = (sr+1)*numBits
                    lr_list[i] = sr
                sr = np.array(lr_list)#4096
                #print(sr.shape)
                sr = np.split(sr, numsplitsZ, 0)
                sr = np.concatenate(sr, 4)
                
                sr = np.split(sr, numsplitsY, 0)
                sr = np.concatenate(sr, 3)
                
                sr = np.split(sr, numsplitsX, 0)
                sr = np.concatenate(sr, 2)
                
                sr = np.squeeze(sr)
                
                #plt.figure(2)
                #plt.imshow(sr[:,:,0])
                
            else:
                if not flatFlag:
                    print('Performing True 3D super Resolution')
                    sr = session.run(net_gen, {inputTensor: lr})
                    sr = (sr+1)*numBits
                else:
                    print('Performing 2D super Resolution')
                    sr = session.run(net_gen, {inputTensor: lr})
                    sr = (sr+1)*numBits
            # save
            
            #output format convertion
            if outputFlag == '.png':
                #2D only
                #sr=sr.reshape(sr.shape[1],sr.shape[2], 3)
                sr = np.squeeze(sr)
                sr = sr.astype('uint8')
                sr = Image.fromarray(sr)
                sr.save(outdir + '/' + name + '-sr.png')
            
            elif outputFlag == '.jpg':
                #2D only
                sr = np.squeeze(sr)
                sr = sr.astype('uint8')
                sr = Image.fromarray(sr)
                sr.save(outdir + '/' + name + '-sr.jpg')
            
            elif outputFlag == '.mat':
                #for 2D and 3D
                #sr=sr.reshape(sr.shape[1],sr.shape[2], sr.shape[3])
                sr = np.squeeze(sr)
                matfile = h5py.File(outdir + '/' + name + '-sr.mat', 'w')
                matfile.create_dataset('data', data = sr)
            
            elif outputFlag == '.nc':
                #for 2D and 3D
                #sr=sr.reshape(sr.shape[1],sr.shape[2], sr.shape[3])
                sr = np.squeeze(sr)
                ncfile = netcdf.netcdf_file(outdir + '/' + name + '-sr.nc', 'w')
                ncfile.createDimension('sr', len(sr))
                #not very sure about the data type, uint8 maybe will be changed
                srvar = ncfile.createVariable('sr', 'uint8', ('sr',))
                ncfile.close()
            
            elif outputFlag == '.tif':
                #sr = sr.astype(datasetBitDepth)
                #sr = np.array(np.squeeze(sr.astype('int')))
                head, tail = os.path.split(fname)
                name, ext = os.path.splitext(tail)
                imsave(f'{outdir}/{name}-sr.tif', np.array(np.squeeze(sr.astype('int')), dtype=datasetBitDepth))
        else:
            continue
    
        
#        if flatFlag:    
#            pngs = glob.glob(os.path.join(args.Input_Images, '*.png'), recursive=True)
#            for path in pngs:
#                print('Super-resolve image ', path)
#                #pdb.set_trace()
#                if datasetBitDepth == 'uint8':
#                    lr = Image.open(path)
#                    if lr.mode != 'RGB':
#                        lr = lr.convert('RGB')
#                    lr = np.array(lr, dtype=datasetBitDepth)
#                lr_batch = np.zeros((1, lr.shape[0], lr.shape[1], 3), dtype=datasetBitDepth)
#                lr_batch[0] = lr
#                lr=lr_batch
#                #lr = lr[:,0:100, 0:100, :]
#                lr = (lr-numBits)/numBits
#                sr = session.run(net_gen, {inputTensor: lr})
#                sr = (sr+1)*numBits
#                #sr = sr.astype(datasetBitDepth)
#                #sr = np.array(np.squeeze(sr.astype('int')))
#                head, tail = os.path.split(path)
#                name, ext = os.path.splitext(tail)
#                imsave(f'{outdir}/{name}-sr.tif', np.array(np.squeeze(sr.astype('int')), dtype=datasetBitDepth))
#                # parse all checkpoints
#                
#                # for all checkpoints
#                
#                # load checkpoints
#                #saver.restore(session, restore)
#        else:
#        # load HR LR batches
#            #img=octave.load(args.Input_Images)
#            #img=img.bentHerrLR
#            mats = glob.glob(os.path.join(args.Input_Images, '*.mat'), recursive=True)
#            for path in mats:
#                arrays = {}
#                f = h5py.File(path)
#                for k, v in f.items():
#                    arrays[k] = np.array(v)
#                img=arrays['temp']
#                img=np.expand_dims(img, 0)
#                img=np.expand_dims(img, 4)
#                img=(img-numBits)/numBits
#                #img=img[:,0:100, 0:100, 0:100, :]
#                # predict values
#                superRes = session.run(net_gen, {inputTensor: img})
#                superRes=(superRes+1)*numBits
#                # compute metrics
#                
#                # save metrics and SR images
#                imsave(f'{args.Input_Images}-SR.tif', np.array(np.squeeze(superRes.astype('int')), dtype=datasetBitDepth))
        

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
