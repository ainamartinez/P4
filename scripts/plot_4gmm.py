#! /usr/bin/env python3

import struct

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from docopt import docopt
import numpy as np
from scipy.stats import multivariate_normal as gauss

import matplotlib
import glob
matplotlib.use('TKAgg')

def read_gmm(fileGMM):
    '''
       Reads the weights, means and convariances from a GMM
       stored using format "UPC: GMM V 2.0"
    '''

    header = b'UPC: GMM V 2.0\x00'

    try:
        with open(fileGMM, 'rb') as fpGmm:
            headIn = fpGmm.read(15)
    
            if headIn != header:
                print(f'ERROR: {fileGMM} is not a valid GMM file')
                exit(-1)

            numMix = struct.unpack('@I', fpGmm.read(4))[0]
            weights = np.array(struct.unpack(f'@{numMix}f', fpGmm.read(numMix * 4)))

            (numMix, numCof) = struct.unpack('@II', fpGmm.read(2 * 4))
            means = struct.unpack(f'@{numMix * numCof}f', fpGmm.read(numMix * numCof * 4))
            means = np.array(means).reshape(numMix, numCof)

            (numMix, numCof) = struct.unpack('@II', fpGmm.read(2 * 4))
            invStd = struct.unpack(f'@{numMix * numCof}f', fpGmm.read(numMix * numCof * 4))
            covs = np.array(invStd).reshape(numMix, numCof) ** -2

            return weights, means, covs
    except:
        raise Exception(f'Error al leer el fichero {fileGMM}')


def read_fmatrix(fileFM):
    '''
       Reads an fmatrix from a file
    '''
    try:
        with open(fileFM, 'rb') as fpFM:
            (numFrm, numCof) = struct.unpack('@II', fpFM.read(2 * 4))
            data = struct.unpack(f'@{numFrm * numCof}f', fpFM.read(numFrm * numCof * 4))
            data = np.array(data).reshape(numFrm, numCof)

            return data
    except:
        raise Exception(f'Error al leer el fichero {fileFM}')


def pdfGMM(X, weights, means, covs):
    '''
       Returns the probability density function (PDF) of a population X
       given a Gaussian Mixture Model (GMM) defined by its weights,
       means and covariances.
    '''

    pdf = np.zeros(len(X))
    for mix, weight in enumerate(weights):
        try:
            pdf += weight * gauss.pdf(X, mean=means[mix], cov=covs[mix])
        except:
            raise Exception(f'Error al calcular la mezcla {mix} del GMM')

    return pdf

def limsGMM(means, covs, fStd=3):
    '''
       Returns the maximum and minimum values of the mean plus/minus fStd
       times the standard deviation for a set of Gaussians defined by their
       means and convariances.
    '''

    numMix = len(means)

    min_ = means[0][:]
    max_ = means[0][:]

    for mix in range(numMix):
        min_ = np.min((min_, means[mix] - fStd * covs[mix] ** 0.5), axis=0)
        max_ = np.max((max_, means[mix] + fStd * covs[mix] ** 0.5), axis=0)

    margin = max(max_ - min_)

    return min_, max_

def plotGMM(fileGMM, xDim, yDim, percents, colorGmm, pathFeat, colorFeat=None, limits=None, subplot=111):
    weights, means, covs = read_gmm(fileGMM)

    ax = plt.subplot(subplot)
    filesFeat = glob.glob(f'{pathFeat}*')
    if filesFeat:
        feats = np.ndarray((0, 2))
        for fileFeat in filesFeat:
            feat = read_fmatrix(fileFeat)
            feat = np.stack((feat[..., xDim], feat[..., yDim]), axis=-1)
            feats = np.concatenate((feats, feat))

        ax.scatter(feats[:, 0], feats[:, 1], .05, color=colorFeat)

    means = np.stack((means[..., xDim], means[..., yDim]), axis=-1)
    covs = np.stack((covs[..., xDim], covs[..., yDim]), axis=-1)

    if not limits:
        min_, max_ = limsGMM(means, covs)
        limits = (min_[0], max_[0], min_[1], max_[1])
    else:
        min_, max_ = (limits[0], limits[2]), (limits[1], limits[3])

    # Fijamos el número de muestras de manera que el valor esperado de muestras
    # en el percentil más estrecho sea 1000. Calculamos el más estrecho como el
    # valor mínimo de p*(1-p)

    numSmp = int(np.ceil(np.max(1000 / (percents * (1 - percents))) ** 0.5))

    x = np.linspace(min_[0], max_[0], numSmp)
    y = np.linspace(min_[1], max_[1], numSmp)
    X, Y = np.meshgrid(x, y)

    XX = np.array([X.ravel(), Y.ravel()]).T

    Z = pdfGMM(XX, weights, means, covs)
    Z /= sum(Z)
    Zsort = np.sort(Z)
    Zacum = Zsort.cumsum()
    levels = [Zsort[np.where(Zacum > 1 - percent)[0][0]] for percent in percents]

    Z = Z.reshape(X.shape)

    style = {'colors': [colorGmm] * len(percents), 'linestyles': ['dotted', 'solid']}

    CS = ax.contour(X, Y, Z, levels=levels, **style)
    fmt = {levels[i]: f'{percents[i]:.0%}' for i in range(len(levels))}
    ax.clabel(CS, inline=1, fontsize=14, fmt=fmt)
    
    fileGMM_id = fileGMM[-10:-4]
    filesFeat_id = filesFeat[0][-20:-14] if filesFeat else None

    plt.title(f'GMM:{fileGMM_id}, LOC:{filesFeat_id}')
    plt.axis('tight')
    plt.axis(limits)

def extractPaths(fileGMM, fileGMM2):
    file1_id = fileGMM[-10:-4]
    file2_id = fileGMM2[-10:-4]

    pathGMM1 = f'work/gmm/mfcc/{file1_id}.gmm'
    pathGMM2 = f'work/gmm/mfcc/{file2_id}.gmm'
    pathFeat1 = f'work/mfcc/BLOCK{file1_id[-3:-1]}/{file1_id}/SA{file1_id[-3:]}S'
    pathFeat2 = f'work/mfcc/BLOCK{file2_id[-3:-1]}/{file2_id}/SA{file2_id[-3:]}S'

    return pathGMM1, pathGMM2, pathFeat1, pathFeat2

########################################################################################################
# Main Program
########################################################################################################

USAGE='''
Draws the regions in space covered with a certain probability by a GMM.

Usage:
    plotGMM [--help|-h] [options] <file-gmm> <file-gmm2>

Options:
    --xDim INT, -x INT               'x' dimension to use from GMM and feature vectors [default: 0]
    --yDim INT, -y INT               'y' dimension to use from GMM and feature vectors [default: 1]
    --percents FLOAT..., -p FLOAT...  Percentages covered by the regions [default: 90,50]
    --colorGMM1 STR, -g STR           Color of the first model/poblation we want to compare[default: red] 
    --colorGMM2 STR, -f STR           Color of the second model/poblation we want to compare  [default: red]
    --limits xyLimits -l xyLimits     xyLimits are the four values xMin,xMax,yMin,yMax [default: auto]

    --help, -h                        Shows this message

Arguments:
    <file-gmm>    File with the Gaussian mixture model to be plotted and compared
    <file-gmm2>   File with the Gaussian mixture model to be plotted and compared
'''

if __name__ == '__main__':
    args = docopt(USAGE)

    fileGMM = args['<file-gmm>']
    fileGMM2 = args['<file-gmm2>']
    xDim = int(args['--xDim'])
    yDim = int(args['--yDim'])
    percents = args['--percents']
    if percents:
        percents = percents.split(',')
        percents = np.array([float(percent) / 100 for percent in percents])
    color1 = args['--colorGMM1']
    color2 = args['--colorGMM2']
    limits = args['--limits']
    if limits != 'auto':
        limits = [float(limit) for limit in limits.split(',')]
        if len(limits) != 4:
            print('ERROR: xyLimits must be four comma-separated values')
            exit(1)
    else:
        limits = None

    pathGMM1, pathGMM2, pathFeat1, pathFeat2 = extractPaths(fileGMM, fileGMM2)

    plotGMM(pathGMM1, xDim, yDim, percents, color1, pathFeat1, color1, limits, 221)
    plotGMM(pathGMM1, xDim, yDim, percents, color1, pathFeat2, color2, limits, 222)
    plotGMM(pathGMM2, xDim, yDim, percents, color2, pathFeat2, color2, limits, 223)
    plotGMM(pathGMM2, xDim, yDim, percents, color2, pathFeat1, color1, limits, 224)

    plt.show()