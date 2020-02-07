#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
**********************************************************
*
* SpectraLearnPredict2
* Perform Machine Learning on Spectroscopy Data.
*
* Uses: Deep Neural Networks, TensorFlow, SVM, PCA, K-Means
*
* By: Nicola Ferralis <feranick@hotmail.com>
*
***********************************************************
'''

import matplotlib
if matplotlib.get_backend() == 'TkAgg':
    matplotlib.use('Agg')

import numpy as np
import sys, os.path, getopt, glob, csv
import random, time, configparser, os
from os.path import exists, splitext
from os import rename
from datetime import datetime, date

from .slp_config import *
from .slp_preprocess import *
from .slp_dnntf import *
from .slp_tf import *
from .slp_keras import *
from .slp_nn import *
from .slp_svm import *
from .slp_pca import *
from .slp_kmeans import *

#**********************************************
''' Learn and Predict - File'''
#**********************************************
def LearnPredictFile(learnFile, sampleFile):
    ''' Open and process training data '''
    En, Cl, A, YnormXind = readLearnFile(learnFile)

    learnFileRoot = os.path.splitext(learnFile)[0]

    ''' Run PCA '''
    if pcaDef.runPCA == True:
        runPCA(En, Cl, A, YnormXind, pcaDef.numPCAcomponents)

    ''' Open prediction file '''
    R, Rx = readPredFile(sampleFile)

    ''' Preprocess prediction data '''
    A, Cl, En, Aorig = preProcessNormLearningData(A, En, Cl, YnormXind, 0)
    R, Rorig = preProcessNormPredData(R, Rx, En, YnormXind, 0)
    
    ''' Run Neural Network - TensorFlow'''
    if dnntfDef.runDNNTF == True:
        dnntfDef.alwaysImprove = False
        if dnntfDef.runSkflowDNNTF == False:
            clf_dnntf, le_dnntf  = trainDNNTF(A, Cl, A, Cl, learnFileRoot)
            predDNNTF(clf_dnntf, le_dnntf, R, Cl)
        else:
            clf_dnntf, le_dnntf  = trainDNNTF2(A, Cl, A, Cl, learnFileRoot)
            predDNNTF2(clf_dnntf, le_dnntf, R, Cl)
    
    ''' Run Neural Network - sklearn'''
    if nnDef.runNN == True:
        clf_nn, le_nn = trainNN(A, Cl, A, Cl, learnFileRoot)
        predNN(clf_nn, A, Cl, R, le_nn)

    ''' Run Support Vector Machines '''
    if svmDef.runSVM == True:
        clf_svm, le_svm = trainSVM(A, Cl, A, Cl, learnFileRoot)
        predSVM(clf_svm, A, Cl, R, le_svm)

    ''' Tensorflow '''
    if tfDef.runTF == True:
        trainTF(A, Cl, A, Cl, learnFileRoot)
        predTF(A, Cl, R, learnFileRoot)
    
    ''' Keras '''
    if kerasDef.runKeras == True:
        model_keras, le_keras  = trainKeras(En, A, Cl, A, Cl, learnFileRoot)
        predKeras(model_keras, le_keras, R, Cl)

    ''' Plot Training Data '''
    if plotDef.createTrainingDataPlot == True:
        plotTrainData(A, En, R, plotDef.plotAllSpectra, learnFileRoot)

    ''' Run K-Means '''
    if kmDef.runKM == True:
        runKMmain(A, Cl, En, R, Aorig, Rorig)

#**********************************************
''' Train and accuracy'''
#**********************************************
def trainAccuracy(learnFile, testFile):
    ''' Open and process training data '''

    En, Cl, A, YnormXind = readLearnFile(learnFile)
    
    if preprocDef.subsetCrossValid == True:
        print(" Cross-validation training using: ",str(preprocDef.percentCrossValid*100),
              "% of training file as test subset")

        A, Cl, A_test, Cl_test = formatSubset(A, Cl, preprocDef.percentCrossValid)
        En_test = En
        print(" Number of training spectra = " + str(len(A)))
        print(" Number of evaluation spectra = " + str(len(A_test)) + "\n")
    else:
        print(" Cross-validation training using: provided test subset (",testFile,")\n")
        En_test, Cl_test, A_test, YnormXind2 = readLearnFile(testFile)
    
    learnFileRoot = os.path.splitext(learnFile)[0]
    
    ''' Plot Training Data - Raw '''
    if plotDef.createTrainingDataPlot == True:
        plotTrainData(A, En, A_test, plotDef.plotAllSpectra, learnFileRoot+"_raw")
    
    ''' Preprocess prediction data '''
    A, Cl, En, Aorig = preProcessNormLearningData(A, En, Cl, YnormXind, 0)
    A_test, Cl_test, En_test, Aorig_test = preProcessNormLearningData(A_test, En_test, Cl_test, YnormXind, 0)
    
    ''' Run Neural Network - TensorFlow'''
    if dnntfDef.runDNNTF == True:
        if dnntfDef.runSkflowDNNTF == False:
            clf_dnntf, le_dnntf  = trainDNNTF(A, Cl, A_test, Cl_test, learnFileRoot)
        else:
            clf_dnntf, le_dnntf  = trainDNNTF2(A, Cl, A_test, Cl_test, learnFileRoot)
            
    if kerasDef.runKeras == True:
        model_keras, le_keras = trainKeras(En, A, Cl, A_test, Cl_test, learnFileRoot)

    ''' Run Neural Network - sklearn'''
    if nnDef.runNN == True:
        clf_nn, le_nn = trainNN(A, Cl, A_test, Cl_test, learnFileRoot)
    
    ''' Run Support Vector Machines '''
    if svmDef.runSVM == True:
        clf_svm, le_svm = trainSVM(A, Cl, A_test, Cl_test, learnFileRoot)
    
    ''' Tensorflow '''
    if tfDef.runTF == True:
        trainTF(A, Cl, A_test, Cl_test, learnFileRoot)
    
    ''' Plot Training Data - Normalized'''
    if plotDef.createTrainingDataPlot == True:
        plotTrainData(A, En, A_test, plotDef.plotAllSpectra, learnFileRoot+"_norm")

#**********************************************
''' Process - Batch'''
#**********************************************
def LearnPredictBatch(learnFile):
    summary_filename = 'summary' + str(datetime.now().strftime('_%Y-%m-%d_%H-%M-%S.csv'))
    makeHeaderSummary(summary_filename, learnFile)
    ''' Open and process training data '''
    En, Cl, A, YnormXind = readLearnFile(learnFile)
    A, Cl, En, Aorig = preProcessNormLearningData(A, En, Cl, YnormXind, 0)
    
    if sysDef.multiProc == True:
        import multiprocessing as mp
        p = mp.Pool(sysDef.numCores)
        for f in glob.glob('*.txt'):
            if (f != learnFile):
                p.apply_async(processSingleBatch, args=(f, En, Cl, A, Aorig, YnormXind, summary_filename, learnFile))
        p.close()
        p.join()
    else:
        for f in glob.glob('*.txt'):
            if (f != learnFile):
                processSingleBatch(f, En, Cl, A, Aorig, YnormXind, summary_filename, learnFile)

def processSingleBatch(f, En, Cl, A, Aorig, YnormXind, summary_filename, learnFile):
    print(' Processing file: \033[1m' + f + '\033[0m\n')
    R, Rx = readPredFile(f)
    summaryFile = [f]
    ''' Preprocess prediction data '''
    R, Rorig = preProcessNormPredData(R, Rx, En, YnormXind, 0)

    learnFileRoot = os.path.splitext(learnFile)[0]
    
    ''' Run Neural Network - TensorFlow'''
    if dnntfDef.runDNNTF == True:
        if dnntfDef.runSkflowDNNTF == False:
            clf_dnntf, le_dnntf  = trainDNNTF(A, Cl, A, Cl, learnFileRoot)
            dnntfPred, dnntfProb = predDNNTF(clf_dnntf, le_dnntf, R, Cl)
        else:
            clf_dnntf, le_dnntf  = trainDNNTF2(A, Cl, A, Cl, learnFileRoot)
            dnntfPred, dnntfProb = predDNNTF2(clf_dnntf, le_dnntf, R, Cl)
        summaryFile.extend([dnntfPred, dnntfProb])
        dnntfDef.alwaysRetrain = False
        
    ''' Run Keras'''
    if kerasDef.runKeras == True:
        model, le_keras  = trainKeras(En, A, Cl, A, Cl, learnFileRoot)
        kerasPred, kerasProb = predKeras(model_keras, le_keras, R, Cl)
        summaryFile.extend([kerasPred, kerasProb])
    
    ''' Run Neural Network - sklearn'''
    if nnDef.runNN == True:
        clf_nn, le_nn = trainNN(A, Cl, A, Cl, learnFileRoot)
        nnPred, nnProb = predNN(clf_nn, A, Cl, R, le_nn)
        summaryFile.extend([nnPred, nnProb])
        nnDef.alwaysRetrain = False

    ''' Run Support Vector Machines '''
    if svmDef.runSVM == True:
        clf_svm, le_svm = trainSVM(A, Cl, A, Cl, learnFileRoot)
        svmPred, svmProb = predSVM(clf_svm, A, Cl, En, R, le_svm)
        summaryFile.extend([svmPred, svmProb])
        svmDef.alwaysRetrain = False

    ''' Tensorflow '''
    if tfDef.runTF == True:
        trainTF(A, Cl, A, Cl, learnFileRoot)
        tfPred, tfProb = predTF(A, Cl, R, learnFileRoot)
        summaryFile.extend([tfPred, tfProb, tfAccur])
        tfDef.tfalwaysRetrain = False

    ''' Run K-Means '''
    if kmDef.runKM == True:
        kmDef.plotKM = False
        kmPred = runKMmain(A, Cl, En, R, Aorig, Rorig)
        summaryFile.extend([kmPred])

    with open(summary_filename, "a") as sum_file:
        csv_out=csv.writer(sum_file)
        csv_out.writerow(summaryFile)
        sum_file.close()

#**********************************************
''' Learn and Predict - Maps'''
#**********************************************
def LearnPredictMap(learnFile, mapFile):
    ''' Open and process training data '''
    En, Cl, A, YnormXind = readLearnFile(learnFile)

    learnFileRoot = os.path.splitext(learnFile)[0]

    ''' Open prediction map '''
    X, Y, R, Rx = readPredMap(mapFile)
    type = 0
    i = 0;
    svmPred = nnPred = tfPred = kmPred = np.empty([X.shape[0]])
    A, Cl, En, Aorig = preProcessNormLearningData(A, En, Cl, YnormXind, type)
    print(' Processing map...' )
    
    if nnDef.runNN == True:
        clf_nn, le_nn = trainNN(A, Cl, A, Cl, learnFileRoot)

    if dnntfDef.runDNNTF == True:
        if dnntfDef.runSkflowDNNTF == False:
            clf_dnntf, le_dnntf  = trainDNNTF(A, Cl, A, Cl, learnFileRoot)
        else:
            clf_dnntf, le_dnntf  = trainDNNTF2(A, Cl, A, Cl, learnFileRoot)

    if kerasDef.runKeras == True:
        model_keras, le_keras  = trainKeras(En, A, Cl, A, Cl, learnFileRoot)

    if svmDef.runSVM == True:
        clf_svm, le_svm = trainSVM(A, Cl, A, Cl, learnFileRoot)

    for r in R[:]:
        r, rorig = preProcessNormPredData(r, Rx, En, YnormXind, type)
        type = 1
        
        ''' Run Neural Network - TensorFlow'''
        if dnntfDef.runDNNTF == True:
            if dnntfDef.runSkflowDNNTF == False:
                dnntfPred[i], temp = predDNNTF(cl_dnntf, le_dnntf, r, Cl)
            else:
                dnntfPred[i], temp = predDNNTF2(cl_dnntf, le_dnntf, r, Cl)
            
            saveMap(mapFile, 'DNN-TF', 'HC', dnntfPred[i], X[i], Y[i], True)
            dnnDef.alwaysRetrain = False
            
        if dnntfDef.runKeras == True:
            kerasPred[i], temp = predKeras(model_keras, le_keras, r, Cl)
            saveMap(mapFile, 'Keras', 'HC', kerasPred[i], X[i], Y[i], True)

        ''' Run Neural Network - sklearn'''
        if nnDef.runNN == True:
            nnPred[i], temp = predNN(clf_nn, A, Cl, r, le_nn)
            saveMap(mapFile, 'NN', 'HC', nnPred[i], X[i], Y[i], True)
            nnDef.alwaysRetrain = False
        
        ''' Run Support Vector Machines '''
        if svmDef.runSVM == True:
            svmPred[i], temp = predSVM(clf_svm, A, Cl, En, r, le_svm)
            saveMap(mapFile, 'svm', 'HC', svmPred[i], X[i], Y[i], True)
            svmDef.alwaysRetrain = False

        ''' Tensorflow '''
        if tfDef.runTF == True:
            trainTF(A, Cl, A, Cl, learnFileRoot)
            tfPred, temp = predTF(A, Cl, r, learnFileRoot)
            saveMap(mapFile, 'TF', 'HC', tfPred[i], X[i], Y[i], True)
            tfDef.alwaysRetrain = False

        ''' Run K-Means '''
        if kmDef.runKM == True:
            kmDef.plotKM = False
            kmPred[i] = runKMmain(A, Cl, En, r, Aorig, rorig)
            saveMap(mapFile, 'KM', 'HC', kmPred[i], X[i], Y[i], True)
        i+=1

    if dnntfDef.plotMap == True and dnntfDef.runDNNTF == True:
        plotMaps(X, Y, dnntfPred, 'Deep Neural networks - tensorFlow')
    if nnDef.plotMap == True and nnDef.runNN == True:
        plotMaps(X, Y, nnPred, 'Deep Neural networks - sklearn')
    if svmDef.plotMap == True and svmDef.runSVM == True:
        plotMaps(X, Y, svmPred, 'SVM')
    if tfDef.plotMap == True and tfDef.runTF == True:
        plotMaps(X, Y, tfPred, 'TensorFlow')
    if kmDef.plotMap == True and kmDef.runKM == True:
        plotMaps(X, Y, kmPred, 'K-Means Prediction')

