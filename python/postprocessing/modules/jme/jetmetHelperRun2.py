#!/usr/bin/env python
import os, sys
import subprocess

from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetUncertainties import *
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.fatJetUncertainties import *

# JEC dict
jecTagsMC = { '2016'   : 'Summer16_07Aug2017_V11_MC', 
              '2017'   : 'Fall17_17Nov2017_V32_MC',
              '2018'   : 'Autumn18_V19_MC',
              'UL2017' : 'Summer19UL17_V5_MC',
              'UL2018' : 'Summer19UL18_V5_MC',
            }

jecTagsFastSim = { '2016' : 'Spring16_25nsFastSimV1_MC',
                   '2017' : 'Fall17_FastSimV1_MC',
                   '2018' : 'Autumn18_FastSimV1_MC',
                 }

archiveTagsDATA = { '2016'   : 'Summer16_07Aug2017_V11_DATA',
                    '2017'   : 'Fall17_17Nov2017_V32_DATA',
                    '2018'   : 'Autumn18_V19_DATA',
                    'UL2017' : 'Summer19UL17_V5_DATA', 
                    'UL2018' : 'Summer19UL18_V5_DATA'
                  }

jecTagsDATA = { '2016B'   : 'Summer16_07Aug2017BCD_V11_DATA',
                '2016C'   : 'Summer16_07Aug2017BCD_V11_DATA',
                '2016D'   : 'Summer16_07Aug2017BCD_V11_DATA',
                '2016E'   : 'Summer16_07Aug2017EF_V11_DATA',
                '2016F'   : 'Summer16_07Aug2017EF_V11_DATA',
                '2016G'   : 'Summer16_07Aug2017GH_V11_DATA',
                '2016H'   : 'Summer16_07Aug2017GH_V11_DATA',
                '2017B'   : 'Fall17_17Nov2017B_V32_DATA',
                '2017C'   : 'Fall17_17Nov2017C_V32_DATA',
                '2017D'   : 'Fall17_17Nov2017DE_V32_DATA',
                '2017E'   : 'Fall17_17Nov2017DE_V32_DATA',
                '2017F'   : 'Fall17_17Nov2017F_V32_DATA',
                '2018A'   : 'Autumn18_RunA_V19_DATA',
                '2018B'   : 'Autumn18_RunB_V19_DATA',
                '2018C'   : 'Autumn18_RunC_V19_DATA',
                '2018D'   : 'Autumn18_RunD_V19_DATA',
                'UL2017B' : 'Summer19UL17_RunB_V5_DATA',
                'UL2017C' : 'Summer19UL17_RunC_V5_DATA',
                'UL2017D' : 'Summer19UL17_RunD_V5_DATA',
                'UL2017E' : 'Summer19UL17_RunE_V5_DATA',
                'UL2017F' : 'Summer19UL17_RunF_V5_DATA',
                'UL2018A' : 'Summer19UL18_RunA_V5_DATA',
                'UL2018B' : 'Summer19UL18_RunB_V5_DATA',
                'UL2018C' : 'Summer19UL18_RunC_V5_DATA',
                'UL2018D' : 'Summer19UL18_RunD_V5_DATA',
              }

jerTagsMC = { '2016'   : 'Summer16_25nsV1_MC',
              '2017'   : 'Fall17_V3_MC',
              '2018'   : 'Autumn18_V7b_MC',
              'UL2017' : 'Summer19UL17_JRV2_MC',
              'UL2018' : 'Summer19UL18_JRV2_MC',
            }

#jet mass resolution: https://twiki.cern.ch/twiki/bin/view/CMS/JetWtagging
#nominal, up, down
jmrValues = { '2016'   : [1.0, 1.2, 0.8],
              '2017'   : [1.09, 1.14, 1.04],
              '2018'   : [1.09, 1.14, 1.04], # Use 2017 values for 2018 until 2018 are released
              'UL2017' : [1.00, 1.00, 1.00], # placeholder
              'UL2018': [1.00, 1.00, 1.00],  # placeholder
            }

#jet mass scale
#W-tagging PUPPI softdrop JMS values: https://twiki.cern.ch/twiki/bin/view/CMS/JetWtagging
#2016 values 
jmsValues = { '2016'   : [1.00, 0.9906, 1.0094], # nominal, down, up
              '2017'   : [0.982, 0.978, 0.986],
              '2018'   : [0.982, 0.978, 0.986], # Use 2017 values for 2018 until 2018 are released
              'UL2017' : [1.000, 1.000, 1.000], # placeholder
              'UL2018' : [1.000, 1.000, 1.000], # placeholder
            }

def createJMECorrector(isMC=True, dataYear=2016, runPeriod="B", jesUncert="Total", jetType="AK4PFchs", noGroom=False, metBranchName="MET", applySmearing=True, isFastSim=False, applyHEMfix=False, splitJER=False, isUL=True):
    
    dataYear = str(dataYear)

    if isMC and not isFastSim:
        if isUL:
            jecTag_ = jecTagsMC['UL{}'.format(dataYear)]
            jerTag_ = jerTagsMC['UL{}'.format(dataYear)] 
        else:
            jecTag_ = jecTagsMC[dataYear]
            jerTag_ = jerTagsMC[dataYear]
    elif isMC and isFastSim:
        jecTag_ = jecTagsFastSim[dataYear]
    else:
        if isUL:
            jecTag_ = jecTagsDATA['UL{}'.format(dataYear + runPeriod)]
            jerTag_ = jerTagsMC['UL{}'.format(dataYear)] 
        else:
            jecTag_ = jecTagsDATA[dataYear + runPeriod]
            jerTag_ = jerTagsMC[dataYear]

    jmeUncert_ = [x for x in jesUncert.split(",")]

    jmrValues_ = jmrValues[dataYear]

    jmsValues_ = jmsValues[dataYear]

    if isUL:
        archiveTag_ = archiveTagsDATA['UL' + dataYear]
    else:
        archiveTag_ = archiveTagsDATA[dataYear]
  
    met_ = metBranchName
    
    print 'JEC=', jecTag_, '\t JER=', jerTag_
    print 'MET branch=', met_

    jmeCorrections = None
    #jme corrections

    if 'AK4' in jetType:
      if isMC:
          jmeCorrections = lambda : jetmetUncertaintiesProducer(era=dataYear,                      globalTag=jecTag_, jesUncertainties=jmeUncert_, jerTag=jerTag_, jetType=jetType, metBranchName=met_, applySmearing=applySmearing, applyHEMfix=applyHEMfix, splitJER=splitJER)
      else:
          jmeCorrections = lambda : jetmetUncertaintiesProducer(era=dataYear, archive=archiveTag_, globalTag=jecTag_, jesUncertainties=jmeUncert_, jerTag=jerTag_, jetType=jetType, metBranchName=met_, isData=True)
    # no MET variations calculated
    else:
      if isMC:
          jmeCorrections = lambda : fatJetUncertaintiesProducer(era=dataYear,                      globalTag=jecTag_, jesUncertainties=jmeUncert_, jetType=jetType, jerTag=jerTag_, jmrVals=jmrValues_, jmsVals=jmsValues_, applySmearing=applySmearing, applyHEMfix=applyHEMfix, splitJER=splitJER, isUL=isUL)
      else:
          jmeCorrections = lambda : fatJetUncertaintiesProducer(era=dataYear, archive=archiveTag_, globalTag=jecTag_, jesUncertainties=jmeUncert_, jetType=jetType, jerTag=jerTag_, jmrVals=jmrValues_, jmsVals=jmsValues_, isData=True, isUL=isUL)

    return jmeCorrections


###In the main postprocessor script, user has to call the function,
###e.g for 2016
#jmeCorrections = createJMECorrector(False, "2016", "B", "Total", True, "AK4PFchs", False)
#include jmeCorrections() in the list of modules to run.
###
